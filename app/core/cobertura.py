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

## EL PORTERO **MARCA**, NO PODA (14 de agosto de 2026), Y ESO INVIERTE SU ASIMETRÍA

**La decisión, del propietario y con su argumento:** la promesa del proyecto es que nada llegue al
alumno **sin etiquetar**, y *marcar es etiquetar*. **Podar, además de dejar un agujero, oculta que
el modelo lo dijo**, que es menos honesto y encima peor de leer. Así que una frase por debajo del
umbral **se emite señalada** —*"esta frase no está respaldada por ninguna afirmación declarada"*— en
vez de desaparecer.

Lo que eso cambia, y es más que un detalle de interfaz:

1. **El defecto de experiencia se va a cero por construcción**: no hay respuesta comida, ni párrafo
   con salto, ni pantalla en blanco. El umbral deja de decidir **si** el alumno ve algo y pasa a
   decidir **cómo** lo ve.
2. **Y LA ASIMETRÍA SE DA LA VUELTA, que es lo que hay que escribir ANTES de re-calibrar:**

| | Cuando el portero PODABA (hasta el 14/08) | Ahora que MARCA |
|---|---|---|
| **Falso positivo** (frase sin respaldo que pasa) | contenido no declarado en la respuesta | **EL CARO**: contenido no declarado llegando al alumno **con aspecto de respaldado** |
| **Falso negativo** (frase legítima que no pasa) | **EL CARO**: se llevaba el párrafo entero, medido | cosmético: una marca injusta sobre una frase correcta |

**Consecuencia operativa, y por eso se escribe aquí y no después del barrido: la dirección de
calibración se INVIERTE.** Con el portero podando, el umbral había que bajarlo para no mutilar; con
el portero marcando, hay que **subirlo**, porque lo que ahora sale caro es dejar pasar sin marca.

**La regla general que sale de haberlo re-derivado tres veces (4.2, 4.3 y aquí): UN NÚMERO NO LLEVA
DENTRO SU PROPIA JUSTIFICACIÓN.** Cuando cambia lo que el mecanismo HACE, su calibración anterior no
se hereda aunque el valor siga sirviendo — porque lo que se calibró fue una respuesta a *"¿qué error
es el caro?"*, y esa pregunta acaba de cambiar de respuesta.

**Y `andamiaje` sigue contando como respaldo**: sin esa excepción, la regla marcaría **todas las
transiciones y preguntas al alumno** —que no afirman nada del mundo y por eso no hay nada que
verificar en ellas (sección 3)—, llenando de avisos una respuesta correcta. Marcar de más es barato,
pero marcar TODO es no marcar nada.
"""
import os

from app.core.frases import palabras_de
from app.core.verificador_calculo import cuenta_en_el_texto

#: Fracción de palabras de contenido de la frase que tienen que estar respaldadas por alguna
#: afirmación para emitirla **sin marca**.
#:
#: **DECLARADO SIN CALIBRAR**, y su barrido —el umbral #3 del 4.6— tiene ahora **dirección
#: contraria**: mientras el portero podaba, subirlo mutilaba respuestas y por eso no era "el lado
#: seguro"; desde que MARCA, el error caro es el falso positivo —una frase sin respaldo emitida sin
#: marca— y el lado seguro es **subirlo**. El valor 0,50 no se hereda de la etapa anterior: se
#: re-barre contra la pregunta nueva (ADR 0021).
SOLAPE_MINIMO = float(os.environ.get("COBERTURA_SOLAPE_MINIMO") or 0.50)

#: Frases más cortas que esto no se juzgan: *"Vamos por partes."* o *"¿Lo ves?"* no tienen
#: vocabulario suficiente para cubrirse, y podarlas sería el falso negativo por construcción.
MINIMO_PALABRAS = 3

#: EL VOCABULARIO DE LA CITA NO CUENTA PARA LA COBERTURA, Y ESTO ES UN ARREGLO DE MEDIDA, NO UN
#: AJUSTE DE UMBRAL.
#:
#: **El caso, medido el 14 de agosto de 2026 corriendo el conjunto del 5.0:** el modelo respondió
#: *"En una jornada continua de 7 horas, el descanso mínimo es de 15 minutos, **según el fragmento
#: F5962 del temario**"*. Correcta, con su procedencia dicha, entregada en 1,7 s — y **podada
#: entera**, con solape 0,44 contra 0,50. Lo que hundió el solape fueron `según`, `fragmento` y
#: `temario`: palabras que **no están en ninguna afirmación porque no pueden estarlo**, ya que son la
#: referencia a la fuente y no contenido.
#:
#: O sea que la medida **castigaba a la prosa por citar su procedencia**, que es exactamente el
#: comportamiento que este proyecto existe para premiar. Y de paso penalizaba dos cosas más: tener
#: **pocas** afirmaciones —el respaldo es más pequeño— y escribir con conectores.
#:
#: **Y lo que NO penalizaba es lo que la regla existe para cazar**: una frase que afirma algo que
#: ninguna afirmación dice. Por eso el arreglo no es bajar el umbral: es **sacar del cómputo el
#: vocabulario meta**. Es la misma lección del 4.3 con la selección de frase — el problema no era el
#: umbral, era **qué se estaba midiendo**.
#:
#: **Vive aquí y NO en `frases.py`, a propósito:** `VACIAS` es una constante compartida con
#: `detectar_conflictos.py`, cuyos números están medidos con esa lista; ampliarla de paso cambiaría
#: en silencio un comportamiento validado por su test y publicado con sus cifras.
META = {"según", "segun", "fragmento", "fragmentos", "temario", "indica", "indican", "dice",
        "dicen", "apartado", "apartados"}

FIN_DE_FRASE = ".!?\n"


class PorteroDeFrases:
    """Juzga la prosa **frase a frase** y la emite: entera si está respaldada, **marcada** si no.

    Se construye cuando el array de `afirmaciones` ya está cerrado —o sea, en el instante en que
    aparece el primer carácter de prosa— y a partir de ahí acumula caracteres hasta cerrar una
    frase y la juzga. **Desde el 14/08/2026 ninguna frase se retiene**: ver la cabecera.
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
            # UN ANDAMIAJE CON UNA CUENTA DENTRO NO ES ANDAMIAJE, ASI QUE NO RESPALDA.
            #
            # El agujero eran DOS privilegios acumulados, no uno: el `andamiaje` **no se verifica**
            # (por diseño, no afirma nada del mundo) **y ademas cuenta como respaldo** de esta regla.
            # Una cuenta metida ahi no solo esquivaba al verificador de calculo: encima **autorizaba
            # prosa**. Medido el 14/08/2026: 4 de 68 `andamiaje` reales llevaban una derivacion
            # entera dentro ("el numero de equipos utiles es 64 - 2 = 62").
            #
            # La seccion 3 ya lo decia -"si una frase de andamiaje afirma algo del temario, es
            # afirmacion y se verifica como tal"- y no habia codigo que lo hiciera.
            if a.get("tipo") == "andamiaje" and cuenta_en_el_texto(a.get("texto") or ""):
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
        #: EL SOLAPE DE CADA FRASE JUZGADA, Y NO SOLO EL DE LAS PODADAS. Sin esto, el umbral del
        #: 4.5 solo se puede BAJAR con datos —se ve qué huérfanas volverían— pero no SUBIR, porque
        #: de las emitidas no se guardaba su valor: el 4.6 lo declaró como "la prosa no se persiste"
        #: y al ir a construir el 2.5 resultó ser más fino, **el denominador estaba y faltaba el
        #: VALOR**. Cada entrada dice además si pasó por ser CORTA, que es un pase por diseño
        #: (podar *"Vale."* sería el falso negativo por construcción) y no una medida del solape:
        #: contarlas juntas volvería a mezclar dos preguntas en un contador.
        self.solapes = []
        #: CARACTERES VISIBLES emitidos, que NO es lo mismo que frases emitidas, y la diferencia
        #: escondió un fallo durante medio día. Una frase con menos de `MINIMO_PALABRAS` palabras de
        #: contenido pasa por diseño —podar *"Vale."* sería el falso negativo por construcción—, así
        #: que un punto suelto o un salto de línea **cuenta como frase emitida** y deja `emitidas`
        #: en 1 con la pantalla vacía. Cualquier comprobación de "¿se enseñó algo?" tiene que mirar
        #: ESTO y no el contador de frases.
        self.caracteres_emitidos = 0
        self.huerfanas = []

    def _cubierta(self, frase: str) -> tuple:
        """`(pasa, solape, corta)`. `corta` distingue el pase POR DISEÑO del pase por solape."""
        palabras = palabras_de(frase) - META
        if len(palabras) < MINIMO_PALABRAS:
            # Frase demasiado corta para juzgarla. Se deja pasar y se dice por qué: podar
            # *"Vamos por partes."* seria el falso negativo por construccion.
            return True, 1.0, True
        if not self.respaldo:
            return False, 0.0, False
        solape = len(palabras & self.respaldo) / len(palabras)
        return solape >= self.solape_minimo, solape, False

    def _anotar(self, solape: float, emitida: bool, corta: bool) -> None:
        """Una fila por frase juzgada. Es lo que el 4.6 necesita para barrer el umbral, y va aquí
        —en el juicio— y no en la rama que emite, para que ninguna frase se quede sin contar."""
        self.solapes.append({"solape": round(solape, 3), "emitida": emitida, "corta": corta})

    def _juzgar(self, frase: str) -> dict:
        """Juzga UNA frase y la devuelve como tramo listo para emitir. **Nunca la retiene.**

        El tramo lleva su veredicto dentro (`respaldada`) porque quien lo emite tiene que poder
        pintarlo distinto: la marca viaja con el texto, no en un contador aparte que la interfaz
        tendría que volver a casar con la frase.
        """
        cubierta, solape, corta = self._cubierta(frase)
        self._anotar(solape, cubierta, corta)
        self.emitidas += 1
        self.caracteres_emitidos += len(frase.strip())
        if not cubierta:
            self.huerfanas.append({"frase": frase.strip(), "solape": round(solape, 2)})
        return {"texto": frase, "respaldada": cubierta, "solape": round(solape, 2),
                "sin_juzgar_por_corta": corta}

    def alimentar(self, trozo: str) -> list:
        """Mete prosa nueva y devuelve los TRAMOS ya cerrados, cada uno con su marca.

        Devuelve una lista y no una cadena desde que el portero marca en vez de podar: la unidad de
        emisión dejó de ser "el texto que sobrevive" y pasó a ser "cada frase con su veredicto".
        Puede ser lista vacía si aún no se ha cerrado ninguna frase.
        """
        self._buffer += trozo
        tramos = []
        while True:
            corte = next((i for i, c in enumerate(self._buffer) if c in FIN_DE_FRASE), None)
            if corte is None:
                break
            frase, self._buffer = self._buffer[:corte + 1], self._buffer[corte + 1:]
            tramos.append(self._juzgar(frase))
        return tramos

    def cerrar(self) -> list:
        """Lo que quede sin punto final al acabar el flujo. Se juzga igual: una frase sin cerrar no
        es una excepción a la regla, solo es una frase que el modelo no terminó."""
        if not self._buffer.strip():
            self._buffer = ""
            return []
        frase, self._buffer = self._buffer, ""
        return [self._juzgar(frase)]

    def estado(self) -> dict:
        # `frases_marcadas` sustituye a `frases_huerfanas`, y el rename NO es cosmetico: mientras el
        # portero podaba, emitidas y huerfanas eran conjuntos DISJUNTOS y sumaban el total; ahora
        # las marcadas TAMBIEN se emiten, asi que quien sumara los dos contadores contaria de mas.
        # Un contador que cambia de significado sin cambiar de nombre es la averia mas barata de
        # dejar caer.
        return {"frases_emitidas": self.emitidas, "frases_marcadas": len(self.huerfanas),
                "marcadas": self.huerfanas[:5], "solape_minimo": self.solape_minimo,
                # TODOS los solapes, no una muestra: son tres números por frase y son EL dato que
                # el barrido del 4.6 necesita. `huerfanas` sigue recortado a 5 porque eso es para
                # MIRARLO en la traza, que es otra pregunta.
                "solapes": self.solapes,
                "calibrado": False,
                "calibracion": "4.6: SIGUE SIN CALIBRAR (evidencia 2026-08-14, umbral #3). Desde "
                               "el 2.5 se persiste el solape de CADA frase juzgada, que es lo que "
                               "faltaba para barrerlo: el denominador ya estaba"}
