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
        respuesta_id = len(self.respuestas)
        self.afirmaciones.extend([{**a, "respuesta_id": respuesta_id} for a in afirmaciones])
        return respuesta_id

    def leer_respuesta(self, respuesta_id: int) -> dict | None:
        if not 1 <= respuesta_id <= len(self.respuestas):
            return None
        r = dict(self.respuestas[respuesta_id - 1])
        consulta_id = r.get("consulta_id")
        c = (self.consultas[consulta_id - 1]
             if consulta_id and 1 <= consulta_id <= len(self.consultas) else {})
        return {"respuesta": {**r, "id": respuesta_id, "creada_en": None},
                "consulta": {**c, "id": consulta_id, "creada_en": None},
                "afirmaciones": [{**a, "id": i + 1} for i, a in enumerate(self.afirmaciones)
                                 if a.get("respuesta_id", respuesta_id) == respuesta_id]}


class TrazaPostgres:
    def __init__(self, url: str):
        self.url = url

    def abrir_consulta(self, texto: str, asignatura_id: int | None, modo: str,
                       usuario_id: str | None, version_prompt: str | None = None) -> int:
        with conectar(self.url) as con, con.cursor() as cur:
            cur.execute(
                "INSERT INTO consultas (usuario_id, modo, asignatura_id, texto, version_corpus,"
                " version_prompt) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (usuario_id, modo, asignatura_id, texto,
                 os.environ.get("VERSION_CORPUS", "sin-declarar"),
                 version_prompt or os.environ.get("VERSION_PROMPT", "sin-declarar")))
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

    def leer_respuesta(self, respuesta_id: int) -> dict | None:
        """Todo lo persistido de UNA respuesta, sin recalcular nada (encargo 2.5).

        **Lee y no deriva, a propósito.** La traza tiene que poder decir qué pasó *entonces*, y
        cualquier número que se recalculara aquí saldría del código de *hoy*: un veredicto
        recomputado con el umbral actual sobre una respuesta de la semana pasada sería una medida
        de otra configuración disfrazada de registro histórico. Lo único que este método hace es
        juntar las tres tablas.
        """
        with conectar(self.url) as con, con.cursor() as cur:
            cur.execute(
                "SELECT r.id, r.consulta_id, r.modelo, r.ttft_ms, r.total_ms, r.tokens_entrada,"
                "       r.tokens_salida, r.coste_eur, r.etapas, r.abstencion, r.creado_en,"
                "       r.cache_hit, r.escalado,"
                "       c.texto, c.modo, c.asignatura_id, c.usuario_id, c.version_prompt,"
                "       c.version_corpus, c.creado_en"
                "  FROM respuestas r JOIN consultas c ON c.id = r.consulta_id"
                " WHERE r.id = %s", (respuesta_id,))
            fila = cur.fetchone()
            if fila is None:
                return None
            cur.execute(
                "SELECT id, tipo, texto, fragmento_id, veredicto, detalle"
                "  FROM afirmaciones WHERE respuesta_id = %s ORDER BY id", (respuesta_id,))
            afirmaciones = [{"id": a[0], "tipo": a[1], "texto": a[2], "fragmento_id": a[3],
                             "veredicto": a[4], "detalle": a[5] or {}} for a in cur.fetchall()]
        return {
            "respuesta": {"id": fila[0], "consulta_id": fila[1], "modelo": fila[2],
                          "ttft_ms": fila[3], "total_ms": fila[4], "tokens_entrada": fila[5],
                          "tokens_salida": fila[6],
                          "coste_eur": float(fila[7]) if fila[7] is not None else None,
                          "etapas": fila[8] or {}, "abstencion": fila[9],
                          "creada_en": fila[10].isoformat() if fila[10] else None,
                          # Los dos campos que NADIE ESCRIBE. Salen crudos y su aviso lo pone el
                          # endpoint: es una propiedad del ESQUEMA, no de esta fila, y ponerlo aquí
                          # hacía que `TrazaEnMemoria` -la otra implementación de esta interfaz- lo
                          # perdiera en silencio. Una advertencia que depende de qué lector se use
                          # es una advertencia que un día no está.
                          "cache_hit": fila[11], "escalado": fila[12]},
            "consulta": {"id": fila[1], "texto": fila[13], "modo": fila[14],
                         "asignatura_id": fila[15], "usuario_id": fila[16],
                         "version_prompt": fila[17], "version_corpus": fila[18],
                         "creada_en": fila[19].isoformat() if fila[19] else None},
            "afirmaciones": afirmaciones,
        }
