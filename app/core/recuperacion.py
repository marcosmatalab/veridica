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


CONSULTA_VECTORIAL = """
SELECT f.id, f.asignatura_id, d.ruta, f.orden, f.unidad, f.texto,
       1 - (f.embedding <=> %(vector)s::vector) AS puntuacion
  FROM fragmentos f
  JOIN documentos d ON d.id = f.documento_id
 WHERE f.embedding IS NOT NULL
   {filtro}
 ORDER BY f.embedding <=> %(vector)s::vector
 LIMIT %(k)s
"""


def buscar_vectorial(url: str, asignatura_id: int, vector, k: int = CANDIDATOS_POR_DEFECTO,
                     sin_filtro: bool = False, forzar_escaneo: bool = False) -> list:
    """Los k vecinos más próximos por distancia coseno dentro de la asignatura.

    **Coseno y no otra**: es la que declara el índice HNSW que creó el 2.1 (`vector_cosine_ops`).
    Usar otra distancia no daría error: daría un orden distinto y el índice dejaría de servir, en
    silencio.

    `forzar_escaneo` apaga el índice para medir el recall EXACTO. No es un capricho: si el
    planificador elige el HNSW, lo que se mide es un recall **aproximado** —`ef_search` por defecto
    es 40—, y un recall flojo podría ser del índice y no del embedding. La regla de lectura está
    escrita antes de medir, en el enunciado del 3.2: si el plan enseña el índice y el recall
    decepciona, se repite con el escaneo forzado, y **la diferencia entre los dos números es el
    precio del aproximado, que es un dato y no un fallo**.
    """
    filtro = "" if sin_filtro else "AND f.asignatura_id = %(asignatura_id)s"
    literal = "[" + ",".join(f"{float(x):.7g}" for x in vector) + "]"
    with psycopg.connect(url) as con, con.cursor() as cur:
        if forzar_escaneo:
            cur.execute("SET LOCAL enable_indexscan=off")
            cur.execute("SET LOCAL enable_bitmapscan=off")
        cur.execute(CONSULTA_VECTORIAL.format(filtro=filtro),
                    {"vector": literal, "k": k, "asignatura_id": asignatura_id})
        return [Candidato(fragmento_id=fid, asignatura_id=aid, documento=ruta, orden=orden,
                          unidad=unidad, texto=txt, puntuacion=float(p), origen="vectorial")
                for fid, aid, ruta, orden, unidad, txt, p in cur.fetchall()]


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


# --- la tercera lista: el glosario del 2.6 --------------------------------------------------------

CONSULTA_GLOSARIO = """
SELECT g.termino, f.id, f.asignatura_id, d.ruta, f.orden, f.unidad, f.texto
  FROM glosario g
  JOIN fragmentos f ON f.id = g.fragmento_id AND f.asignatura_id = g.asignatura_id
  JOIN documentos d ON d.id = f.documento_id
 WHERE g.asignatura_id = %(asignatura_id)s
 ORDER BY length(g.termino) DESC, g.termino
"""


def buscar_glosario(url: str, asignatura_id: int, texto: str, k: int = CANDIDATOS_POR_DEFECTO) -> list:
    """Los fragmentos del glosario cuyo TÉRMINO aparece literalmente en la pregunta.

    Es la tercera lista de la fusión y no se parece a las otras dos: no puntúa por similitud ni por
    frecuencia, sino por **coincidencia exacta de un término definido**. Sin modelo y sin umbral.

    **En plural a propósito** (ADR 0012): un término puede tener varias entradas, y cuando las
    tiene es porque el corpus se contradice. Traer las dos caras es exactamente lo que la fase 4
    necesita para poder enseñarlas, así que aquí entran todas y no se elige una.

    El orden es por longitud del término descendente: si la pregunta dice "clave primaria", la
    entrada de `clave primaria` vale más que la de `clave`, que también casa y dice menos.
    """
    pregunta = f" {' '.join(texto.lower().split())} "
    candidatos, vistos = [], set()
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute(CONSULTA_GLOSARIO, {"asignatura_id": asignatura_id})
        for termino, fid, aid, ruta, orden, unidad, txt in cur.fetchall():
            if f" {termino.lower()} " not in pregunta or fid in vistos:
                continue
            vistos.add(fid)
            candidatos.append(Candidato(fragmento_id=fid, asignatura_id=aid, documento=ruta,
                                        orden=orden, unidad=unidad, texto=txt,
                                        puntuacion=float(len(termino)), origen="glosario"))
            if len(candidatos) >= k:
                break
    return candidatos


# --- la fusión ------------------------------------------------------------------------------------

K_RRF = 60


PESOS_POR_DEFECTO = {"vectorial": 1.0, "lexica": 1.0, "glosario": 1.0}


def fusionar(listas: dict, k_rrf: int = K_RRF, k: int = CANDIDATOS_POR_DEFECTO,
             pesos: dict | None = None) -> list:
    """RRF: cada lista aporta 1/(k_rrf + rango) y se suma. Devuelve los k mejores.

    **RRF PONDERA POR RANGO E IGNORA LA CALIDAD DE CADA LISTA**, y aquí son muy desiguales —la
    léxica acierta el 32,1 % a recall@5 sobre `lectura` y el vectorial el 74,1 %—. Eso significa que
    una lista floja puede meter ruido en la CABEZA de la fusión aunque mejore la cola, así que la
    verificación de este encargo no puede ser solo "recall@20 de la fusión ≥ el de cada lista": eso
    es necesario y no suficiente. Se mira también qué le pasa al @5 y al @6 frente al vectorial
    solo, porque si el reordenador del 3.4 decepciona, el orden que queda es este.

    `origen` conserva **de qué listas viene cada candidato**, aunque hoy no se use para decidir
    nada: es lo que hará legible la complementariedad más adelante.
    """
    pesos = pesos or PESOS_POR_DEFECTO
    puntos, por_id, procedencia = {}, {}, {}
    for nombre, lista in listas.items():
        peso = pesos.get(nombre, 1.0)
        for rango, candidato in enumerate(lista, 1):
            fid = candidato.fragmento_id
            puntos[fid] = puntos.get(fid, 0.0) + peso / (k_rrf + rango)
            procedencia.setdefault(fid, []).append(f"{nombre}#{rango}")
            por_id.setdefault(fid, candidato)
    orden = sorted(puntos, key=lambda fid: (-puntos[fid], fid))
    salida = []
    for fid in orden[:k]:
        base = por_id[fid]
        salida.append(Candidato(fragmento_id=fid, asignatura_id=base.asignatura_id,
                                documento=base.documento, orden=base.orden, unidad=base.unidad,
                                texto=base.texto, puntuacion=puntos[fid],
                                origen="+".join(procedencia[fid])))
    return salida


def recuperar(url: str, asignatura_id: int, texto: str, vector=None,
              k: int = CANDIDATOS_POR_DEFECTO, k_rrf: int = K_RRF, marcas: list | None = None,
              sin_filtro: bool = False, pesos: dict | None = None,
              con_glosario: bool = True) -> list:
    """La recuperación completa del 3.3: las tres listas y su fusión.

    `marcas` recoge las etapas REALES con su milisegundo, para que la interfaz pueda dibujarlas y la
    traza guardarlas. Es el mismo contrato del 2.4: lo que se dibuja tiene que haber ocurrido.
    """
    import time
    listas = {}
    t0 = time.perf_counter()

    def marcar(nombre, detalle):
        if marcas is not None:
            marcas.append({"nombre": nombre, "ms": round((time.perf_counter() - t0) * 1000, 1),
                           "detalle": detalle})

    listas["lexica"] = buscar_lexico(url, asignatura_id, texto, k=k, sin_filtro=sin_filtro)
    marcar("recuperacion_lexica", f"{len(listas['lexica'])} candidatos por palabras")
    if vector is not None:
        listas["vectorial"] = buscar_vectorial(url, asignatura_id, vector, k=k,
                                               sin_filtro=sin_filtro)
        marcar("recuperacion_vectorial", f"{len(listas['vectorial'])} candidatos por significado")
    if con_glosario:
        listas["glosario"] = buscar_glosario(url, asignatura_id, texto, k=k)
    if listas.get("glosario"):
        marcar("glosario", f"{len(listas['glosario'])} definiciones del temario")
    fusion = fusionar(listas, k_rrf=k_rrf, k=k, pesos=pesos)
    marcar("fusion", f"{len(fusion)} fragmentos, ordenados por RRF")
    return fusion


# --- confianza_recuperacion: una afirmación que el sistema hace sobre sí mismo --------------------

#: UMBRALES DECLARADOS **SIN CALIBRAR**, igual que el 0,80 del NLI, y con su calibración apuntada al
#: encargo 4.6. Salen de mirar la separación real sobre los 100 pares, no de elegir números redondos.
#:
#: QUÉ SEÑAL SE USA Y POR QUÉ NO OTRA. La puntuación RRF **no vale**: no está calibrada y un 0,03 no
#: significa nada en absoluto. La similitud coseno del primer candidato tampoco separa casi —medido:
#: con el oro en el contexto la mediana es 0,664 y sin él 0,642, distribuciones casi solapadas—. Lo
#: que sí separa es la **CONCENTRACIÓN de la cabeza**: cuánto le saca el primer candidato al sexto.
#: Cuando la respuesta está de verdad en el corpus, el primero destaca; cuando no está, los seis
#: primeros valen casi lo mismo, que es el sistema diciendo "hay muchas cosas parecidas y ninguna
#: encaja". Medido sobre los 100 pares: con margen ≥ 0,08 el oro está en el contexto el 83,3 % de
#: las veces; sin él, el 58,7 %.
MARGEN_ALTA = 0.08
MARGEN_MEDIA = 0.05
COSENO_MINIMO_ALTA = 0.66


def confianza_de(vectoriales: list) -> tuple:
    """Devuelve (nivel, detalle). El nivel es lo que viaja en el contrato de la sección 7.

    Se calcula sobre la lista VECTORIAL y no sobre la fusión a propósito: la puntuación vectorial es
    una distancia coseno entre vectores normalizados, o sea una magnitud con significado; la de la
    fusión es una suma de inversos de rangos, que no lo tiene.
    """
    if not vectoriales:
        return "baja", {"motivo": "no hay candidatos"}
    top1 = vectoriales[0].puntuacion
    sexto = vectoriales[min(5, len(vectoriales) - 1)].puntuacion
    margen = top1 - sexto
    detalle = {"top1": round(top1, 4), "margen_top1_top6": round(margen, 4),
               "umbrales": {"alta": MARGEN_ALTA, "media": MARGEN_MEDIA,
                            "coseno_alta": COSENO_MINIMO_ALTA},
               "calibrado": False, "calibracion": "encargo 4.6"}
    if margen >= MARGEN_ALTA and top1 >= COSENO_MINIMO_ALTA:
        return "alta", detalle
    if margen >= MARGEN_MEDIA:
        return "media", detalle
    return "baja", detalle
