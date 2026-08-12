"""Esquema inicial: el DDL de la seccion 9 de la guia (encargo 2.1).

Revision: 0001
Padre: ninguno

Tres cosas que NO son gusto y por eso van comentadas donde se aplican:

1. `asignaturas` lleva UNIQUE (titulacion, codigo) y NO unique global: los cinco transversales
   (0373, 0483, 0484, 0485, 0487) se repiten entre titulos en el BOE, asi que un unique global
   habria roto la carga de DAM y ASIR en cuanto entrara la segunda titulacion.
2. `fragmentos` va particionada POR LISTA de asignatura_id, y su clave primaria es
   (asignatura_id, id): Postgres exige que la clave de particion este dentro de la primaria.
   Esa es la particion que hace que una consulta filtrada toque UNA particion y no todas, que es
   el argumento de escala entero.
3. Los indices HNSW y GIN se crean POR PARTICION y no sobre la tabla padre. Un indice declarado en
   el padre se propaga, pero crearlos por particion deja ver -y medir- el coste de cada uno, y
   permite reconstruir uno solo cuando una asignatura crece.
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute("""
        CREATE TABLE asignaturas (
            id serial PRIMARY KEY,
            organizacion_id int NOT NULL DEFAULT 1,
            titulacion text NOT NULL DEFAULT 'DAW',
            curso smallint,
            nombre text NOT NULL,
            codigo text NOT NULL,
            creado_en timestamptz NOT NULL DEFAULT now(),
            UNIQUE (titulacion, codigo))
    """)
    # `curso` acepta NULL a proposito, corrigiendo el DDL de referencia: el reparto en primero y
    # segundo lo fija la orden de curriculo y solo tenemos la de DAW, asi que DAM y ASIR van sin
    # curso y declarado (COBERTURA.md). Un NOT NULL aqui obligaria a inventarse el dato.

    op.execute("""
        CREATE TABLE titulacion_asignaturas (
            titulacion text NOT NULL,
            asignatura_id int NOT NULL REFERENCES asignaturas ON DELETE CASCADE,
            creado_en timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (titulacion, asignatura_id))
    """)

    op.execute("""
        CREATE TABLE documentos (
            id serial PRIMARY KEY,
            organizacion_id int NOT NULL DEFAULT 1,
            asignatura_id int REFERENCES asignaturas,
            unidad text,
            titulo text NOT NULL,
            fuente text NOT NULL,
            licencia text NOT NULL,
            version_corpus text NOT NULL,
            hash_sha256 char(64) NOT NULL,
            densidad text NOT NULL DEFAULT 'completa',
            origen text NOT NULL DEFAULT 'texto',
            ruta text NOT NULL UNIQUE,
            creado_en timestamptz NOT NULL DEFAULT now())
    """)
    # CORRECCION DEL DDL DE REFERENCIA, con su motivo (ADR 0008): la seccion 9 pone
    # `hash_sha256 UNIQUE`, y ese unique es incompatible con el encargo 1.7. El documento COLADO
    # que se planto para medir contaminacion es, por definicion, una COPIA EXACTA de un documento
    # de otra asignatura: mismo hash, dos rutas, dos particiones. Con el unique global, la carga
    # habria tenido que tirar uno de los dos y se habria llevado por delante el instrumento con el
    # que el 3.5 mide contaminacion cruzada. Lo que identifica a un documento es su RUTA -es la
    # clave del manifiesto, "una entrada por fichero"-, no su contenido. El hash se indexa para
    # poder buscar duplicados, que es lo util de verdad, pero no impone unicidad.
    op.execute("CREATE INDEX documentos_por_hash ON documentos (hash_sha256)")

    op.execute("""
        CREATE TABLE fragmentos (
            id bigserial,
            organizacion_id int NOT NULL DEFAULT 1,
            documento_id int NOT NULL REFERENCES documentos,
            asignatura_id int NOT NULL,
            unidad text,
            orden int NOT NULL,
            tipo_contenido text NOT NULL,
            texto text NOT NULL,
            contexto text NOT NULL,
            tokens int,
            embedding vector(1024),
            tsv tsvector,
            creado_en timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (asignatura_id, id)
        ) PARTITION BY LIST (asignatura_id)
    """)

    op.execute("""
        CREATE TABLE glosario (
            id serial PRIMARY KEY,
            organizacion_id int NOT NULL DEFAULT 1,
            asignatura_id int NOT NULL REFERENCES asignaturas,
            termino text NOT NULL,
            definicion text NOT NULL,
            fragmento_id bigint NOT NULL,
            creado_en timestamptz NOT NULL DEFAULT now(),
            UNIQUE (asignatura_id, termino))
    """)

    op.execute("""
        CREATE TABLE conflictos (
            id serial PRIMARY KEY,
            organizacion_id int NOT NULL DEFAULT 1,
            fragmento_a bigint NOT NULL,
            fragmento_b bigint NOT NULL,
            similitud real,
            estado text NOT NULL DEFAULT 'abierto',
            detalle text,
            tipo text NOT NULL,
            veredicto_nli text,
            probabilidad_nli real,
            fecha_a date,
            fecha_b date,
            version_a text,
            version_b text,
            creado_en timestamptz NOT NULL DEFAULT now())
    """)

    op.execute("""
        CREATE TABLE consultas (
            id bigserial PRIMARY KEY,
            ts timestamptz NOT NULL DEFAULT now(),
            organizacion_id int NOT NULL DEFAULT 1,
            usuario_id text,
            modo text NOT NULL,
            asignatura_id int,
            texto text NOT NULL,
            version_corpus text NOT NULL,
            version_prompt text NOT NULL,
            creado_en timestamptz NOT NULL DEFAULT now())
    """)

    op.execute("CREATE INDEX documentos_por_asignatura ON documentos (asignatura_id)")
    op.execute("CREATE INDEX conflictos_por_fragmento_a ON conflictos (fragmento_a)")
    op.execute("CREATE INDEX conflictos_por_fragmento_b ON conflictos (fragmento_b)")


def downgrade():
    for tabla in ("consultas", "conflictos", "glosario", "fragmentos", "documentos",
                  "titulacion_asignaturas", "asignaturas"):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")
