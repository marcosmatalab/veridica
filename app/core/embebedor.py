"""El embebedor de la CONSULTA (encargo 3.2). Mismo modelo y misma revisión que el corpus.

**ESTE MÓDULO EXISTE PARA IMPEDIR UNA ASIMETRÍA** (principio 8). Un vector de consulta calculado con
otro modelo, otra revisión, otra precisión o sin normalizar **sigue siendo un vector de 1024
dimensiones perfectamente válido**: la base lo acepta, la consulta corre, no hay error en ningún
sitio y los resultados salen peor sin que nadie sepa por qué. Es el fallo silencioso más caro de
esta fase, y por eso el anclaje no se comprueba "cuando alguien se acuerde": se comprueba al cargar
y, si no coincide, esto no arranca.

Lo anclado sale de `corpus/medidas-ingesta.json`, que escribió la ingesta del 1.5 —modelo, revisión,
dimensión, precisión, normalización y longitud máxima—, y **no se reescribe aquí**: copiarlo a mano
sería crear una segunda fuente de verdad que se separa de la primera en cuanto alguien re-embeba.

COSTE MEDIDO en la máquina donde corre la demo, y por eso la carga es al ARRANCAR y no perezosa:
carga 1,7 s en CPU y 2,3 s en GPU; una consulta, **68 ms en CPU** y 14 ms en GPU. Con la carga
perezosa, esos ~2 s los pagaría la primera consulta de la sesión, delante del cliente.
"""
import json
import os
import time

MEDIDAS = "corpus/medidas-ingesta.json"


class AnclajeRoto(RuntimeError):
    """El modelo disponible no es el que embebió el corpus. No se sigue."""


def anclaje(ruta: str = MEDIDAS) -> dict:
    with open(ruta, encoding="utf-8") as f:
        m = json.load(f)
    return {"modelo": m["modelo"], "revision": m["revision"], "dimension": m["dimension"],
            "normalizados": m["normalizados"], "largo_maximo": m["largo_maximo"],
            "precision_ingesta": m["precision"], "dispositivo_ingesta": m["dispositivo"]}


class Embebedor:
    """Carga BGE-M3 una vez por proceso y embebe consultas sueltas."""

    def __init__(self, dispositivo: str | None = None, ruta_medidas: str = MEDIDAS):
        import torch
        from sentence_transformers import SentenceTransformer

        self.anclaje = anclaje(ruta_medidas)
        self.dispositivo = dispositivo or os.environ.get("EMBEBEDOR_DISPOSITIVO") or (
            "cuda" if torch.cuda.is_available() else "cpu")
        # La PRECISION no se hereda de la ingesta: alli fue fp16 porque corria en GPU, y fp16 en CPU
        # es mas lento que fp32 sin ganar nada. La diferencia numerica entre las dos esta muy por
        # debajo de la distancia entre vecinos, asi que no rompe la simetria que importa; lo que si
        # la romperia -otro modelo, otra revision, sin normalizar- se comprueba abajo.
        dtype = torch.float16 if self.dispositivo == "cuda" else torch.float32
        t0 = time.perf_counter()
        self.modelo = SentenceTransformer(self.anclaje["modelo"], revision=self.anclaje["revision"],
                                          device=self.dispositivo, model_kwargs={"dtype": dtype})
        self.segundos_carga = time.perf_counter() - t0
        self._comprobar()

    def _comprobar(self) -> None:
        """La comprobación que hace que este módulo valga para algo. Sin ella, el anclaje sería un
        comentario."""
        import numpy as np
        vector = self.embeber("comprobacion de anclaje")
        if len(vector) != self.anclaje["dimension"]:
            raise AnclajeRoto(f"el modelo devuelve {len(vector)} dimensiones y el corpus se embebio "
                              f"con {self.anclaje['dimension']}: los vectores no son comparables")
        norma = float(np.linalg.norm(vector))
        if self.anclaje["normalizados"] and abs(norma - 1.0) > 1e-3:
            raise AnclajeRoto(f"la consulta sale con norma {norma:.4f} y el corpus esta normalizado:"
                              f" la distancia coseno no significaria lo mismo en los dos lados")

    def embeber(self, texto: str) -> list:
        return self.modelo.encode([texto], normalize_embeddings=self.anclaje["normalizados"])[0]

    def estado(self) -> dict:
        return {"modelo": self.anclaje["modelo"], "revision": self.anclaje["revision"][:12],
                "dispositivo": self.dispositivo, "dimension": self.anclaje["dimension"],
                "segundos_carga": round(self.segundos_carga, 1)}
