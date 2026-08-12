"""Recuperación léxica (encargo 3.1). La primera de las tres listas que el 3.3 fusionará.

INTERFAZ ÚNICA A PROPÓSITO: `buscar_lexico`, `buscar_vectorial` (3.2) y la fusión (3.3) devuelven
todas lo mismo —una lista de `Candidato` ordenada—, para que el llamador no tenga que cambiar cuando
lleguen las otras dos. Hoy solo existe la léxica y lo demás está declarado y no construido.

**EL FILTRO DE ASIGNATURA NO ES UN PARÁMETRO OPCIONAL: es la firma.** No hay forma de llamar a esta
función sin decir de qué asignatura se busca, y eso es deliberado. La contaminación entre asignaturas
—responderle a un alumno de Programación con material de Bases de Datos— es una de las cosas que el
3.5 mide, y la manera de que no ocurra por descuido no es acordarse de filtrar: es que no se pueda
no filtrar. `sin_filtro=True` existe **solo para el test que enseña al filtro haciendo su trabajo**,
y por eso se llama así de feo.

SOBRE LA CONFIGURACIÓN `spanish` Y LOS IDENTIFICADORES, medido antes de escribir esta consulta y no
heredado como supuesto (ver `docs/evidencia/2026-08-13-lexica.md`): el lematizador español trunca
**10 de los 20 identificadores** que aparecen en las preguntas de los pares oro —`ViewData` pasa a
`viewdat`, `@ComponentScan` a `componentsc`—. Que los trunque **no rompe la búsqueda**, porque el
documento y la consulta pasan por la misma configuración y el truncado es simétrico: buscar
`ViewData` encuentra `ViewData`. Lo que sí produce es **ruido en identificadores cortos que caen en
la misma raíz que un verbo castellano** —`@page` se convierte en `pag`, igual que `pagar`—. La
salida obvia sería una segunda columna con configuración `simple`; no se toma sin medir cuánto
cuesta ese ruido sobre los pares oro, que es lo que hace `scripts/medir_recuperacion.py`.
"""
from dataclasses import dataclass

import psycopg

CONFIGURACION = "spanish"
CANDIDATOS_POR_DEFECTO = 20


@dataclass
class Candidato:
    """Un fragmento recuperado, con de dónde salió y con qué puntuación."""

    fragmento_id: int
    asignatura_id: int
    documento: str
    orden: int
    unidad: str | None
    texto: str
    puntuacion: float
    origen: str = "lexica"


#: CÓMO SE ARMA LA CONSULTA, y es la decisión que decide el recall entero.
#:
#: `websearch_to_tsquery` une los términos con **AND**: una pregunta de alumno de veinte palabras se
#: convierte en "el fragmento tiene que contener las diez raíces a la vez", y eso casi nunca pasa en
#: 512 tokens. Medido sobre los 100 pares oro: **recall@20 del 19,0 %**. No es que la léxica sea
#: floja; es que se le estaba pidiendo una conjunción.
#:
#: Con los mismos términos unidos por **OR** —y el ranking decidiendo el orden, que es para lo que
#: está— el mismo conjunto sube a lo que dice la evidencia del encargo. Se conserva
#: `websearch_to_tsquery` como analizador, porque respeta comillas y el `-` de exclusión que un
#: alumno puede escribir; lo único que se cambia es el conector, sobre la consulta ya analizada.
#:
#: La guía escribía `websearch_to_tsquery` a secas: la desviación va con su número al lado, que es
#: la única forma de desviarse en este repo.
CONECTOR_OR = "replace(websearch_to_tsquery(%(configuracion)s, %(texto)s)::text, ' & ', ' | ')"

CONSULTA = f"""
SELECT f.id, f.asignatura_id, d.ruta, f.orden, f.unidad, f.texto,
       ts_rank_cd(f.tsv, consulta) AS puntuacion
  FROM fragmentos f
  JOIN documentos d ON d.id = f.documento_id,
       LATERAL (SELECT ({CONECTOR_OR})::tsquery AS consulta) AS q
 WHERE f.tsv @@ consulta
   {{filtro}}
 ORDER BY puntuacion DESC, f.id
 LIMIT %(k)s
"""

CONSULTA_AND = """
SELECT f.id, f.asignatura_id, d.ruta, f.orden, f.unidad, f.texto,
       ts_rank_cd(f.tsv, consulta) AS puntuacion
  FROM fragmentos f
  JOIN documentos d ON d.id = f.documento_id,
       websearch_to_tsquery(%(configuracion)s, %(texto)s) AS consulta
 WHERE f.tsv @@ consulta
   {filtro}
 ORDER BY puntuacion DESC, f.id
 LIMIT %(k)s
"""


def buscar_lexico(url: str, asignatura_id: int, texto: str, k: int = CANDIDATOS_POR_DEFECTO,
                  sin_filtro: bool = False, conjuncion: bool = False) -> list:
    """Los k fragmentos de esa asignatura que mejor casan con el texto, por BM25-ish de Postgres.

    `sin_filtro` es el modo del test que enseña al filtro excluyendo de verdad. En cualquier otro
    sitio, llamarlo así es un fallo.
    """
    filtro = "" if sin_filtro else "AND f.asignatura_id = %(asignatura_id)s"
    plantilla = CONSULTA_AND if conjuncion else CONSULTA
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute(plantilla.format(filtro=filtro),
                    {"configuracion": CONFIGURACION, "texto": texto, "k": k,
                     "asignatura_id": asignatura_id})
        return [Candidato(fragmento_id=fid, asignatura_id=aid, documento=ruta, orden=orden,
                          unidad=unidad, texto=txt, puntuacion=float(p))
                for fid, aid, ruta, orden, unidad, txt, p in cur.fetchall()]
