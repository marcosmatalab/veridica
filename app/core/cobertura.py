"""La regla de cobertura del 4.5, aplicada **frase a frase mientras se escribe**.

## EL CONFLICTO QUE ESTE MÓDULO RESUELVE

La sección 7 exige que `respuesta_redactada` **no diga nada que no esté en las afirmaciones**. Pero
la prosa se emite **en streaming**, así que para cuando la redacción está completa y la cobertura se
puede comprobar, **el alumno ya la ha leído**. Podar entonces una frase huérfana significa **retirar
texto de la pantalla**, y el mecanismo de retirada del 2.4 se diseñó como **excepcional**: si la
cobertura podara a menudo, el alumno vería tachones con frecuencia, que es **peor que lento y peor
que seco**.

**La salida sale del orden del contrato, igual que la verificación gratis del 4.2: las afirmaciones
están COMPLETAS antes de que empiece la prosa.** Así que la cobertura no hay que esperarla al final:
se comprueba **frase a frase, según cada frase se cierra**, contra unas afirmaciones que ya se
conocen. **Solo se emite la frase que ya está cubierta.** Cuesta **una frase de retraso**, no una
espera entera, y la retirada vuelve a ser lo que debía ser: excepcional.

**Las dos alternativas, descartadas con su motivo para que consten:**

1. **No emitir hasta comprobar.** Devuelve el TTFT que costó dos días de trabajo: la prosa dejaría de
   salir según llega y el streaming volvería a ser adorno.
2. **Emitir y retirar.** Deja al alumno leyendo texto que se tacha, y **contradice el argumento de
   la propia demo**: un sistema que presume de no afirmar sin respaldo no puede afirmar primero y
   desdecirse después como rutina.

## LA ASIMETRÍA AQUÍ ES DISTINTA DE LAS ANTERIORES, Y HAY QUE DECLARARLO ANTES DE ELEGIR EL UMBRAL

En el 4.2 y en el 4.3 el falso positivo era el caro y el falso negativo salía barato —una cita
rechazada de más degrada a paráfrasis y sigue su camino—. **Aquí no.**

| | Qué cuesta |
|---|---|
| **Falso positivo** | cuela en la respuesta contenido **no declarado** en ninguna afirmación |
| **Falso negativo** | **poda una frase legítima de un texto que alguien está leyendo**, y deja un **agujero en mitad de un párrafo** |

Podar una afirmación es invisible para el alumno; podar una frase de la redacción **se ve**. Así que
el umbral se elige **con las dos consecuencias delante** y no por inercia de los encargos anteriores.

**Y `andamiaje` es justo lo que evita el falso negativo masivo**: sin esa excepción, la regla se
llevaría por delante **todas las transiciones y preguntas al alumno** —que no afirman nada del mundo
y por eso no hay nada que verificar en ellas (sección 3)—, dejando una respuesta correcta y
mutilada.
"""
import os

from app.core.frases import palabras_de

#: Fracción de palabras de contenido de la frase que tienen que estar respaldadas por alguna
#: afirmación. **DECLARADO SIN CALIBRAR**, con su barrido en el **4.6** y con la asimetría de arriba
#: como criterio: aquí subirlo NO es "el lado seguro", porque el falso negativo también se ve.
SOLAPE_MINIMO = float(os.environ.get("COBERTURA_SOLAPE_MINIMO") or 0.50)

#: Frases más cortas que esto no se juzgan: *"Vamos por partes."* o *"¿Lo ves?"* no tienen
#: vocabulario suficiente para cubrirse, y podarlas sería el falso negativo por construcción.
MINIMO_PALABRAS = 3

FIN_DE_FRASE = ".!?\n"


class PorteroDeFrases:
    """Deja pasar la prosa **frase a frase**, y solo la que está cubierta.

    Se construye cuando el array de `afirmaciones` ya está cerrado —o sea, en el instante en que
    aparece el primer carácter de prosa— y a partir de ahí acumula caracteres hasta cerrar una
    frase, la juzga, y la suelta o la retiene.
    """

    def __init__(self, afirmaciones: list, solape_minimo: float = SOLAPE_MINIMO):
        self.solape_minimo = solape_minimo
        # EL ANDAMIAJE CUENTA COMO RESPALDO. No afirma nada del mundo -por eso no se verifica- pero
        # SÍ está declarado en el contrato, que es lo que la regla de cobertura exige. Sin esto, la
        # regla se llevaria por delante todas las transiciones y preguntas al alumno.
        self.respaldo = set()
        for a in afirmaciones or []:
            if not isinstance(a, dict):
                continue
            self.respaldo |= palabras_de(a.get("texto") or "")
            # LA CITA TAMBIÉN ES RESPALDO, y olvidarla producía el falso negativo por construcción
            # que este módulo existe para evitar. Lo enseñó el primer test que se corrió: la prosa
            # *"la cookie lleva solo el id"* se podaba porque ninguna afirmación tenía la palabra
            # `cookie` en su `texto`... y sí la tenía en su `cita`, que es contenido **declarado en
            # el contrato y además verificado letra a letra** por el 4.2. Si algo puede respaldar
            # una frase, es precisamente lo que está comprobado contra el temario.
            self.respaldo |= palabras_de(a.get("cita") or "")
        self._buffer = ""
        self.emitidas = 0
        self.huerfanas = []

    def _cubierta(self, frase: str) -> tuple:
        palabras = palabras_de(frase)
        if len(palabras) < MINIMO_PALABRAS:
            # Frase demasiado corta para juzgarla. Se deja pasar y se dice por qué: podar
            # *"Vamos por partes."* seria el falso negativo por construccion.
            return True, 1.0
        if not self.respaldo:
            return False, 0.0
        solape = len(palabras & self.respaldo) / len(palabras)
        return solape >= self.solape_minimo, solape

    def alimentar(self, trozo: str) -> str:
        """Mete prosa nueva y devuelve lo que se puede emitir YA. Puede ser cadena vacía."""
        self._buffer += trozo
        salida = ""
        while True:
            corte = next((i for i, c in enumerate(self._buffer) if c in FIN_DE_FRASE), None)
            if corte is None:
                break
            frase, self._buffer = self._buffer[:corte + 1], self._buffer[corte + 1:]
            cubierta, solape = self._cubierta(frase)
            if cubierta:
                salida += frase
                self.emitidas += 1
            else:
                self.huerfanas.append({"frase": frase.strip(), "solape": round(solape, 2)})
        return salida

    def cerrar(self) -> str:
        """Lo que quede sin punto final al acabar el flujo. Se juzga igual: una frase sin cerrar no
        es una excepción a la regla, solo es una frase que el modelo no terminó."""
        if not self._buffer.strip():
            self._buffer = ""
            return ""
        frase, self._buffer = self._buffer, ""
        cubierta, solape = self._cubierta(frase)
        if cubierta:
            self.emitidas += 1
            return frase
        self.huerfanas.append({"frase": frase.strip(), "solape": round(solape, 2)})
        return ""

    def estado(self) -> dict:
        return {"frases_emitidas": self.emitidas, "frases_huerfanas": len(self.huerfanas),
                "huerfanas": self.huerfanas[:5], "solape_minimo": self.solape_minimo,
                "calibrado": False, "calibracion": "encargo 4.6"}
