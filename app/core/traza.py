"""Persistencia de la traza de una consulta (encargo 2.2, tablas de la migración 0002).

Una respuesta sin traza no es una respuesta de este sistema: la observabilidad del proyecto -y el
registro que pide el AI Act- se reconstruye desde `consultas` + `respuestas` + `afirmaciones`. Por
eso el endpoint escribe siempre, y por eso el TTFT que se mide se GUARDA: una latencia medida que no
se guarda en ningún sitio es una latencia que nadie podrá comparar con la de la semana que viene.

Dos implementaciones con la misma interfaz. `TrazaPostgres` es la de verdad. `TrazaEnMemoria` es la
de los tests, y existe para que el test del SSE pruebe **el endpoint** y no la disponibilidad de una
base: en CI no hay Postgres y el corpus tampoco está (ADR 0001, mismo criterio).
"""
import json
import os

from app.core.conexion import conectar


class TrazaEnMemoria:
    def __init__(self):
        self.consultas, self.respuestas, self.afirmaciones = [], [], []

    def abrir_consulta(self, **campos) -> int:
        self.consultas.append(campos)
        return len(self.consultas)

    def cerrar_respuesta(self, consulta_id: int, afirmaciones: list, **campos) -> int:
        self.respuestas.append({"consulta_id": consulta_id, **campos})
        self.afirmaciones.extend(afirmaciones)
        return len(self.respuestas)


class TrazaPostgres:
    def __init__(self, url: str):
        self.url = url

    def abrir_consulta(self, texto: str, asignatura_id: int | None, modo: str,
                       usuario_id: str | None) -> int:
        with conectar(self.url) as con, con.cursor() as cur:
            cur.execute(
                "INSERT INTO consultas (usuario_id, modo, asignatura_id, texto, version_corpus,"
                " version_prompt) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (usuario_id, modo, asignatura_id, texto,
                 os.environ.get("VERSION_CORPUS", "sin-declarar"),
                 os.environ.get("VERSION_PROMPT", "sin-declarar")))
            return cur.fetchone()[0]

    def cerrar_respuesta(self, consulta_id: int, afirmaciones: list, modelo: str,
                         ttft_ms: int | None, total_ms: int, tokens_entrada: int,
                         tokens_salida: int, coste_eur: float | None, etapas: dict,
                         abstencion: bool) -> int:
        with conectar(self.url) as con, con.cursor() as cur:
            cur.execute(
                "INSERT INTO respuestas (consulta_id, modelo, ttft_ms, total_ms, tokens_entrada,"
                " tokens_salida, coste_eur, etapas, abstencion)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (consulta_id, modelo, ttft_ms, total_ms, tokens_entrada, tokens_salida, coste_eur,
                 json.dumps(etapas, ensure_ascii=False), abstencion))
            respuesta_id = cur.fetchone()[0]
            for a in afirmaciones:
                cur.execute(
                    "INSERT INTO afirmaciones (respuesta_id, tipo, texto, fragmento_id, veredicto,"
                    " detalle) VALUES (%s,%s,%s,%s,%s,%s)",
                    (respuesta_id, a["tipo"], a["texto"], a.get("fragmento_id"), a["veredicto"],
                     json.dumps(a.get("detalle") or {}, ensure_ascii=False)))
            return respuesta_id
