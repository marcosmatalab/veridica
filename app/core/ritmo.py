"""El vigilante de ritmo del flujo: corta una generación que se ha vuelto lenta a media respuesta.

EL FALLO QUE ESTO EXISTE PARA CAZAR, medido el 13 de agosto de 2026 con n=20
(`docs/evidencia/2026-08-13-concurrencia.md`): **dos de veinte consultas tardaron 63 y 68 segundos**,
y las dos **arrancaron perfectamente** —317 y 314 ms hasta el primer token, igual que una normal—.
Lo que se hundió fue el **ritmo**: generaron a **4 y 11 tokens/s** contra los ~105 de una consulta
sana. O sea que ninguna vigilancia del arranque las habría visto: el TTFT del proveedor estaba bien.

**Por qué es lo más urgente del proyecto y no una mejora:** con esa tasa observada (2 de 20 = 10 %),
una sesión de ocho preguntas tiene **57 % de probabilidad** de comerse al menos una congelación de un
minuto delante del cliente (1 − 0,9⁸). No es un caso raro: es más probable que no.

CÓMO SE MIDE, Y POR QUÉ ASÍ:

- **Se cuentan trozos con texto sobre una ventana móvil**, no el total desde el principio. Una media
  global se contamina con el arranque y, peor, **tarda cada vez más en reaccionar**: a los 30 s de
  generación buena, treinta segundos malos solo bajan la media a la mitad. La ventana olvida.
- **Los primeros tokens no se juzgan** (`GRACIA`). El arranque tiene su propia física —el primer
  trozo llega tras el TTFT y luego el ritmo sube— y medir ahí daría falsos positivos justo en la
  parte que en las dos consultas malas estaba SANA.
- **Un trozo con texto se cuenta como un token.** Es una aproximación y se dice: el proveedor manda
  normalmente un token por trozo, pero puede agrupar. Si agrupara, el ritmo medido saldría más bajo
  que el real y el vigilante cortaría de más; por eso el umbral está en un tercio del ritmo sano y
  no pegado a él.

UMBRAL Y VENTANA VAN **DECLARADOS SIN CALIBRAR**, igual que el 0,80 del NLI y los márgenes de
`confianza_recuperacion`, **con su calibración apuntada al encargo 4.6**. Salen de la medida
—~105 tokens/s sano, 4 y 11 en las malas— y de elegir el punto que separa esos dos grupos con el
mayor margen posible, que es todo lo que se puede hacer con dos casos malos.
"""
import time
from collections import deque

#: Tokens que no se juzgan, para no confundir el arranque con una avería.
#:
#: **ES DELIBERADAMENTE PEQUEÑO, y la primera versión lo tenía en 24, que era un error de los que se
#: ven al escribir el test:** una gracia contada en TOKENS se convierte en una gracia contada en
#: SEGUNDOS cuanto más lento va el flujo, que es justo al revés de lo que hace falta. A 4 tokens/s
#: —el peor caso medido— esperar 24 tokens son **6 segundos**, o sea más que el presupuesto entero
#: de la consulta: el vigilante habría llegado tarde exactamente en el caso que existe para cazar.
#: Con 8, ese mismo flujo se corta a los ~2,2 s. Quien protege contra juzgar el arranque no es este
#: número, es la VENTANA: el arranque de un flujo sano es rápido, no lento.
GRACIA = 8

#: Ventana móvil. Bastante corta para reaccionar en segundos y bastante larga para no disparar con
#: un hueco de red de medio segundo.
VENTANA_S = 2.0

#: Un TERCIO del ritmo sano medido (~105 tokens/s). Las dos consultas malas iban a 4 y 11, así que
#: 35 las caza con holgura y deja un factor 3 de margen antes de tocar a una sana.
RITMO_MINIMO = 35.0

#: LA ASIMETRÍA QUE JUSTIFICA INCLINARSE A CORTAR, dicha para que nadie la "arregle" luego subiendo
#: la gracia: un falso positivo cuesta **~2 segundos** —se corta y se vuelve a pedir, y el reintento
#: va anunciado en pantalla—; un falso negativo cuesta **~60 segundos de pantalla congelada delante
#: del cliente**. Treinta veces más. Con esa relación, el punto de equilibrio no está en el medio, y
#: por eso este vigilante prefiere equivocarse cortando.


class RitmoCaido(RuntimeError):
    """La generación se ha vuelto demasiado lenta para llegar a tiempo. Es TRANSITORIO: el proveedor
    responde, solo que a un ritmo que no sirve. Se corta y se vuelve a pedir."""

    def __init__(self, ritmo: float, minimo: float):
        super().__init__(f"ritmo de generacion caido: {ritmo:.1f} tokens/s por debajo del minimo "
                         f"de {minimo:.0f}; se corta y se reintenta")
        self.ritmo = ritmo
        self.minimo = minimo


class VigilanteDeRitmo:
    """Cuenta tokens sobre una ventana móvil y dice si el ritmo se ha hundido.

    El reloj se inyecta para poder probarlo sin dormir: un test que necesita esperar dos segundos de
    verdad para comprobar una ventana de dos segundos es un test que nadie vuelve a correr.
    """

    def __init__(self, minimo: float = RITMO_MINIMO, ventana_s: float = VENTANA_S,
                 gracia: int = GRACIA, reloj=None):
        self.minimo = minimo
        self.ventana_s = ventana_s
        self.gracia = gracia
        # El reloj por defecto se resuelve al LLAMAR, no al importar. Con `reloj=time.perf_counter`
        # como valor por defecto, la funcion quedaba atada en tiempo de importacion y ninguna prueba
        # que sustituya el reloj podia alcanzarla: el vigilante seguia mirando el reloj de verdad y
        # los tests pasaban por otra razon que la que decian. Misma familia que el instrumento que
        # no mide lo que su nombre dice.
        self._reloj = reloj if reloj is not None else (lambda: time.perf_counter())
        self._marcas: deque = deque()
        self._inicio: float | None = None
        self.total = 0
        #: EL PEOR MOMENTO, que es lo que el umbral juzga. `estado()` guardaba `tokens_por_segundo`
        #: —el ritmo de la ÚLTIMA ventana— y eso contesta *"¿a qué ritmo iba al final?"*, mientras
        #: que el mínimo de 35 tok/s pregunta *"¿bajó alguna vez de aquí?"*. Dos preguntas
        #: distintas en el mismo número: para calibrar el umbral hace falta la distribución de
        #: ESTE. Añadido al construir el 2.5, cuando se fue a barrer y el dato no estaba.
        self.minimo_observado: float | None = None

    def anota(self) -> None:
        """Un trozo con texto. Se llama una vez por trozo, según llega."""
        ahora = self._reloj()
        if self._inicio is None:
            self._inicio = ahora
        self.total += 1
        self._marcas.append(ahora)

    def ritmo(self) -> float | None:
        """Tokens por segundo en la ventana, o None si aún no ha pasado una ventana entera.

        **None no es cero, y la diferencia importa:** al principio hay pocos datos, y devolver 0
        haría que el vigilante cortara toda consulta en su primer instante.

        El divisor es **la ventana**, no el hueco entre la primera y la última marca, y esa es la
        corrección que hizo falta: al podar lo viejo, ese hueco es siempre algo MENOR que la ventana,
        así que un "¿ya cabe una ventana entera?" comparado contra él **nunca daba que sí** y el
        vigilante no llegaba a mirar nunca. Con el divisor fijo, además, un flujo que se para del
        todo va viendo su ritmo bajar hacia cero en vez de quedarse congelado en el último valor.
        """
        ahora = self._reloj()
        if self._inicio is None or (ahora - self._inicio) < self.ventana_s:
            return None
        limite = ahora - self.ventana_s
        while self._marcas and self._marcas[0] < limite:
            self._marcas.popleft()
        return len(self._marcas) / self.ventana_s

    def comprobar(self) -> None:
        """Levanta `RitmoCaido` si procede. Se llama después de cada `anota`."""
        if self.total <= self.gracia:
            return
        r = self.ritmo()
        if r is None:
            return
        # Se anota ANTES de decidir: el peor momento de una consulta que se corta es justo el que
        # la corta, y si se anotara despues del `raise` no quedaria registrado ninguno de ellos —
        # la tabla volveria a contener solo lo que salio bien.
        if self.minimo_observado is None or r < self.minimo_observado:
            self.minimo_observado = r
        if r < self.minimo:
            raise RitmoCaido(r, self.minimo)

    def estado(self) -> dict:
        r = self.ritmo()
        return {"tokens": self.total,
                # ESTE es el ritmo de la ULTIMA ventana, no la media ni el peor: se deja con su
                # nombre y se le pone al lado el que el umbral necesita.
                "tokens_por_segundo": round(r, 1) if r is not None else None,
                "minimo_observado": (round(self.minimo_observado, 1)
                                     if self.minimo_observado is not None else None),
                "minimo": self.minimo, "ventana_s": self.ventana_s, "gracia": self.gracia,
                "calibrado": False,
                "calibracion": "4.6: SIGUE SIN CALIBRAR (evidencia 2026-08-14, umbral #5). "
                               "CORRECCION del 2.5: el ritmo por consulta SI se persistia (330 de "
                               "391 respuestas); lo que faltaba era el PEOR momento, que es lo que "
                               "el umbral juzga, y desde aqui se guarda"}
