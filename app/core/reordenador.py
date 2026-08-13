"""El reordenador del encargo 3.4: BGE reranker v2-m3 sobre los 30 candidatos de la fusión.

QUÉ HACE Y POR QUÉ HACE FALTA. La fusión del 3.3 **no ordena, cubre**: medido, RRF coloca peor que
el vectorial solo (56,0 % contra 73,0 % a `recall@5`), y lo que compra son candidatos que el
vectorial no traía. Así que el conjunto lo genera la fusión y **el orden lo pone este módulo**. Un
cross-encoder no compara dos vectores calculados por separado: mete la consulta y el fragmento
JUNTOS por el modelo, así que puede mirar si esta pregunta se responde con este texto en vez de si
los dos hablan de lo mismo. Es caro por eso, y por eso solo se le dan 30.

CONSECUENCIA DE ARQUITECTURA, ESCRITA PARA QUE NADIE LA LEA COMO OPCIONAL: **la fusión cuelga de
este módulo.** Si el reordenador cae o se recorta, el respaldo NO es la fusión sin reordenar —que
ordena peor que no fusionar—, sino el **vectorial solo en top 6**. Está en la tabla de contingencias.

EL `max_length` NO ES UN PARÁMETRO DE EFICIENCIA, ES UNA DECISIÓN DE FIDELIDAD. El truncado de un
cross-encoder **no es simétrico**: recorta el fragmento, no la pregunta. Y el 13 de agosto de 2026
aprendimos dónde vive la respuesta más veces de lo cómodo: `oro-001` se responde con la **última
línea** de su fragmento —el *Tip del Examinador*—. Un `max_length` corto no da un error ni una
puntuación rara; da una puntuación perfectamente normal calculada sobre un texto al que le falta
justo el final. Medido el reparto real del corpus (11.483 fragmentos): p50 481 tokens, p95 509,
p99 520, **máximo 6.913**. De ahí sale el 640 por defecto: cubre el 99 % entero con sitio para la
pregunta, y lo que quede fuera se cuenta y se declara en vez de suponerse pequeño.
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as EsperaAgotada

#: Revisión ANCLADA, comprobada al cargar. El motivo es el del embebedor y el principio 8: un
#: reordenador de otra revisión sigue devolviendo números perfectamente válidos entre 0 y 1, así que
#: una discrepancia no da error, da otro orden — y nadie sabría por qué el recall bajó.
MODELO = "BAAI/bge-reranker-v2-m3"
REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"

#: 30 candidatos, decidido con la aritmética del techo delante (3.4) y NO ajustable a la baja: con 20
#: el reordenador tendría que acertar el 96,7 % para llegar al 0,8 de `recall@6`, que es imposible.
CANDIDATOS = int(os.environ.get("RERANK_CANDIDATOS") or 30)

#: Los 6 que van al contexto del modelo generador.
TOP_CONTEXTO = 6

#: Cubre el p99 del corpus (520 tokens) más la pregunta. Ver el bloque de arriba: bajarlo recorta el
#: FINAL del fragmento, que es donde varias veces está la respuesta.
LARGO_MAXIMO = int(os.environ.get("RERANK_LARGO_MAXIMO") or 640)

#: Cuánto se espera a la GPU antes de rendirse y servir el orden de la fusión. El p95 medido son
#: 554 ms, así que 2 s deja casi cuatro veces de margen y sigue cabiendo de sobra en el presupuesto
#: de 5 s. No es un plazo para la GPU —a una GPU no se le puede poner plazo— sino para NOSOTROS.
ESPERA_MAXIMA_S = float(os.environ.get("RERANK_ESPERA_MAXIMA_S") or 2.0)

#: Qué fracción del plazo tiene que pasarse un trabajo ESPERANDO TURNO para que su fracaso se
#: atribuya a la carga y no al hardware. Un cuarto: por debajo de eso, arrancó prácticamente
#: enseguida y si aun así no terminó, el que no responde es la GPU.
FRACCION_COLA = float(os.environ.get("RERANK_FRACCION_COLA") or 0.25)


class AnclajeRoto(RuntimeError):
    """El reordenador disponible no es el anclado, o no ordena. No se sigue."""


class SinGPU(RuntimeError):
    """No hay GPU. En la ruta de petición esto NO autoriza a reordenar en CPU."""


def para_servicio(largo_maximo: int = LARGO_MAXIMO):
    """El reordenador de la ruta de petición: **GPU o nada, jamás CPU**. Medido, no opinado.

    | 30 candidatos | p50 | p95 | Del presupuesto de 5.000 ms |
    |---|---:|---:|---:|
    | CPU 16 hilos (9950X3D, cota inferior) | 10.776 ms | 13.714 ms | **274 %** |
    | GPU (RTX 5080) | 419 ms | 554 ms | 11 % |

    Un factor **25**, y el reordenado va ANTES de la llamada al modelo, o sea **en la ruta del
    TTFT**: caer a CPU no serían 13 s de total, serían 13 s de **pantalla muerta** añadidos a los
    2.267 ms de hoy. Deshace la fase 2.4 entera, que existió para matar 1,6 s de pantalla en blanco.

    Por eso el respaldo cuando no hay GPU **no es reordenar más despacio: es no reordenar**, servir
    el orden de la fusión y **decirlo en pantalla**. Es el patrón del circuit breaker del 8.2:
    degradar anunciando, jamás degradar en silencio — y aquí, además, degradar rápido es lo único
    que respeta al que espera.
    """
    import torch

    if not torch.cuda.is_available():
        raise SinGPU(
            "no hay GPU visible. El reordenado NO cae a CPU: son 13,7 s de p95 medidos (210 % del "
            "presupuesto) y van en la ruta del TTFT. Se sirve el orden de la fusión, anunciado")
    return Reordenador(dispositivo="cuda", largo_maximo=largo_maximo)


class Reordenador:
    """Carga el cross-encoder una vez por proceso y ordena candidatos contra una consulta.

    El dispositivo por defecto es **CPU** a propósito, y no es una limitación de la máquina de
    desarrollo: el destino declarado es la CPU del VPS (8.1), así que medir aquí en GPU daría un
    número que no se parece a producción. Quien quiera GPU lo pide explícitamente.
    """

    def __init__(self, dispositivo: str | None = None, largo_maximo: int = LARGO_MAXIMO,
                 hilos: int | None = None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.dispositivo = dispositivo or os.environ.get("REORDENADOR_DISPOSITIVO") or "cpu"
        self.largo_maximo = largo_maximo
        # Fijar hilos ANTES de cargar: torch los lee al construir sus pools internos.
        if hilos:
            torch.set_num_threads(hilos)
        self.hilos = torch.get_num_threads()

        t0 = time.perf_counter()
        self.tokenizador = AutoTokenizer.from_pretrained(MODELO, revision=REVISION)
        self.modelo = AutoModelForSequenceClassification.from_pretrained(
            MODELO, revision=REVISION, dtype=torch.float32)
        self.modelo.to(self.dispositivo)
        self.modelo.eval()
        self.segundos_carga = time.perf_counter() - t0
        # UN solo hilo a proposito: ver `reordenar_o_rendirse`. Con varios, una GPU colgada nos
        # dejaria fabricando hilos zombis, uno por peticion, en vez de degradar.
        self._ejecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="reordenador")
        self.rendiciones = 0
        self.rendiciones_por_gpu = 0      # el hardware no responde
        self.rendiciones_por_cola = 0     # el hardware va bien y hay carga: NO es una averia
        self._reloj_gpu = time.perf_counter
        self._comprobar()

    def _comprobar(self) -> None:
        """La comprobación que hace que el anclaje no sea un comentario, **en las dos direcciones**.

        Un cross-encoder mal cargado —otra cabeza, otros pesos, `num_labels` distinto— no falla:
        devuelve números. Así que no basta con ver que devuelve algo (dirección sana): hay que ver
        que **separa**, que es lo único que este módulo aporta. Si el par que responde no puntúa por
        encima del que no responde, este objeto no sirve para ordenar y no debe existir.
        """
        pega = "¿Dónde se almacenan los datos de la sesión en Spring Boot?"
        buena = "La sesión se almacena en el servidor; la cookie solo contiene el identificador."
        mala = "AutoMapper se configura creando un Profile que declara los mapeos entre entidades."
        puntos = self.puntuar(pega, [buena, mala])
        if len(puntos) != 2:
            raise AnclajeRoto(f"el reordenador devuelve {len(puntos)} puntuaciones para 2 pares")
        if not puntos[0] > puntos[1]:
            raise AnclajeRoto(
                f"el reordenador NO separa: el fragmento que responde puntúa {puntos[0]:.4f} y el "
                f"que no responde {puntos[1]:.4f}. Ordenar con esto sería barajar con ceremonia")
        self.margen_sonda = float(puntos[0] - puntos[1])

    def puntuar(self, consulta: str, textos: list) -> list:
        """Puntuación cruda del cross-encoder para cada (consulta, texto). Mayor es más relevante."""
        import torch

        if not textos:
            return []
        pares = [(consulta, t) for t in textos]
        with torch.no_grad():
            lote = self.tokenizador(
                [p[0] for p in pares], [p[1] for p in pares],
                padding=True, truncation="only_second", max_length=self.largo_maximo,
                return_tensors="pt").to(self.dispositivo)
            salida = self.modelo(**lote).logits.view(-1).float()
        return salida.cpu().tolist()

    def reordenar_o_rendirse(self, consulta: str, candidatos: list, top: int = TOP_CONTEXTO,
                             espera_s: float = ESPERA_MAXIMA_S) -> tuple:
        """Devuelve `(reordenados, motivo)`. Si no llega a tiempo: `(None, motivo)`. No lanza.

        **LA SATURACIÓN NO ES UNA AVERÍA Y NO PUEDE CONTARSE COMO TAL.** Con un solo hilo y ~419 ms
        por reordenado, la quinta petición simultánea de una ráfaga espera ~2.095 ms y se pasa del
        plazo **con la GPU perfectamente sana**: eso es cola, no fallo. El discriminante es si el
        trabajo llegó a **empezar** (`futuro.running()`), y de ahí salen los dos motivos distintos.

        **"NO CANCELABLE" NO ES "NO ACOTABLE", y esa distinción tapa el último punto de la ruta que
        podía colgarse sin límite.** Es verdad que una operación de GPU no se puede matar desde
        torch: no hay forma de interrumpir un kernel a medias. Pero de ahí no se sigue que haya que
        **esperarla para siempre**, que es lo que se hacía. La llamada se lanza en un hilo y la
        espera se acota sobre el futuro; al vencer, esta función se rinde y el que llama degrada
        saltando el reordenado —el respaldo que ya existe y que se anuncia en pantalla—.

        **EL RESIDUO, DECLARADO PORQUE ES REAL: el hilo queda colgado hasta que CUDA vuelva.** No se
        limpia, no se puede. Lo que se consigue es que **la petición no dependa de ello**: el alumno
        recibe su respuesta con el orden de la fusión en vez de quedarse mirando la pantalla. Y el
        ejecutor es de UN hilo a propósito, así que un segundo cuelgue no abre un segundo hilo: se
        encola detrás, vence su espera igual, y el sistema degrada en vez de fabricar hilos zombis
        mientras la GPU está caída.
        """
        if not candidatos:
            return [], None
        # El sello de ARRANQUE, que es lo que hace preciso el diagnostico. `futuro.running()` a
        # secas no basta: un trabajo que estuvo 1,9 s en la cola y arranco justo antes de que
        # venciera el plazo aparece como "corriendo" y se contaria como averia de GPU cuando fue
        # cola pura. Medido en la corrida 12, ese caso salia UNA vez en cada nivel de concurrencia,
        # o sea que inflaba la averia y desinflaba la saturacion justo donde importa distinguirlas.
        arranque: list = []

        def tarea():
            arranque.append(self._reloj_gpu())
            return self.reordenar(consulta, candidatos, top)

        pedido = self._reloj_gpu()
        futuro = self._ejecutor.submit(tarea)
        try:
            return futuro.result(timeout=espera_s), None
        except EsperaAgotada:
            # TRES AVERIAS DISTINTAS Y NO DOS, y la que las separa es si el trabajo llego a
            # EMPEZAR. Si el futuro sigue sin arrancar, es que hay otro delante en la cola del
            # unico hilo: el hardware va bien y lo que hay es CARGA. Si arranco y no termino, es
            # el hardware el que no responde. Confundirlas es diagnosticar mal, y con el circuit
            # breaker del 8.2 delante seria abrir el circuito por una punta de trafico -el mismo
            # error que ya se evito con los 429-.
            self.rendiciones += 1
            # LO QUE SEPARA LAS DOS AVERIAS ES CUANTO ESPERO EN COLA, no cuanto llego a correr.
            # Si arranco enseguida y aun asi no termino, el que no responde es el hardware. Si se
            # paso una parte apreciable del plazo esperando turno, lo que ato fue la CARGA -aunque
            # en el instante del vencimiento el trabajo estuviera ya corriendo, que es justo el caso
            # que `futuro.running()` a secas clasificaba mal-.
            if not arranque:
                self.rendiciones_por_cola += 1
                return None, "reordenador_saturado"
            espero_en_cola_s = arranque[0] - pedido
            if espero_en_cola_s > espera_s * FRACCION_COLA:
                self.rendiciones_por_cola += 1
                return None, "reordenador_saturado"
            self.rendiciones_por_gpu += 1
            return None, "gpu_no_contesta"

    def reordenar(self, consulta: str, candidatos: list, top: int = TOP_CONTEXTO) -> list:
        """Devuelve los `top` mejores candidatos, reordenados y con su puntuación sustituida.

        La puntuación que sale **no es la RRF de entrada**: es la del cross-encoder, y se sustituye
        en vez de acumularse para que nadie las sume por accidente —una es un rango fusionado sin
        calibrar y la otra un logit; sumarlas no significa nada—. `origen` se conserva, porque es lo
        que hace legible de qué lista vino cada superviviente.
        """
        if not candidatos:
            return []
        puntos = self.puntuar(consulta, [c.texto for c in candidatos])
        emparejados = sorted(zip(puntos, range(len(candidatos))), key=lambda p: -p[0])
        salida = []
        for punto, i in emparejados[:top]:
            c = candidatos[i]
            salida.append(type(c)(**{**c.__dict__, "puntuacion": float(punto)}))
        return salida

    def truncados(self, consulta: str, textos: list) -> int:
        """Cuántos de esos textos NO caben enteros en `largo_maximo`. Se cuenta, no se supone."""
        n = 0
        for t in textos:
            largo = len(self.tokenizador(consulta, t, truncation=False)["input_ids"])
            if largo > self.largo_maximo:
                n += 1
        return n

    def estado(self) -> dict:
        return {"modelo": MODELO, "revision": REVISION[:12], "dispositivo": self.dispositivo,
                "hilos": self.hilos, "largo_maximo": self.largo_maximo,
                "segundos_carga": round(self.segundos_carga, 1),
                "margen_sonda": round(self.margen_sonda, 3),
                "espera_maxima_s": ESPERA_MAXIMA_S, "rendiciones": self.rendiciones,
                "rendiciones_por_gpu": self.rendiciones_por_gpu,
                "rendiciones_por_cola": self.rendiciones_por_cola}
