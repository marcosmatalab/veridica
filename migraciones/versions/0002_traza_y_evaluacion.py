"""Las cuatro tablas que el 2.1 se dejo del DDL de la seccion 9 (deuda declarada, saldada en el 2.2).

Revision: 0002
Padre: 0001

ESTO NO ES UNA AMPLIACION DEL ESQUEMA: es el resto del encargo 2.1. Aquel decia "el DDL de la
seccion 9 con Alembic" y la migracion 0001 creo 7 de las 11 tablas. Faltaban `respuestas`,
`afirmaciones`, `casos_eval` y `corridas_eval`, y el hueco no salio de ningun sitio raro: salio de
declarar el cierre por lo que uno recuerda haber hecho en vez de leer la frase del cierre clausula a
clausula. De ahi la regla nueva de CLAUDE.md.

Van aqui y no mas tarde porque la verificacion del 2.2 las necesita: el TTFT y el total se persisten
en `respuestas.etapas`, y una latencia medida que no se guarda en ningun sitio es una latencia que
nadie podra comparar con la de la semana que viene.

Dos apuntes de forma:

1. `afirmaciones.veredicto` es NOT NULL y en el 2.2 vale SIEMPRE 'sin_verificar'. No es un valor de
   relleno: es la unica respuesta honesta hasta la fase 4. El 2.2 comprueba la FORMA del contrato
   -que el JSON es el de la seccion 7-, no la VERDAD de lo que dice.
2. `afirmaciones.fragmento_id` no lleva clave ajena a `fragmentos` a proposito: `fragmentos` esta
   particionada y su primaria es (asignatura_id, id), asi que una ajena obligaria a arrastrar
   tambien la asignatura. Mismo criterio que `conflictos` en la 0001.
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE respuestas (
            id bigserial PRIMARY KEY,
            organizacion_id int NOT NULL DEFAULT 1,
            consulta_id bigint NOT NULL REFERENCES consultas ON DELETE CASCADE,
            modelo text NOT NULL,
            escalado bool NOT NULL DEFAULT false,
            cache_hit bool NOT NULL DEFAULT false,
            ttft_ms int,
            total_ms int,
            tokens_entrada int,
            tokens_salida int,
            coste_eur numeric(10,6),
            etapas jsonb NOT NULL,
            abstencion bool NOT NULL DEFAULT false,
            creado_en timestamptz NOT NULL DEFAULT now())
    """)
    # `ttft_ms` es el TTFT DEL ALUMNO -el primer caracter de prosa que aparece en pantalla-, que es
    # lo que pide la seccion 10 ("el TTFT medido es el que ve el alumno"). El otro TTFT, el del
    # primer token que manda el proveedor, vive en `etapas` con su nombre: con salida tipada los dos
    # numeros son distintos y guardar solo uno es perder justo el que explica al otro (ADR 0009).

    op.execute("""
        CREATE TABLE afirmaciones (
            id bigserial PRIMARY KEY,
            organizacion_id int NOT NULL DEFAULT 1,
            respuesta_id bigint NOT NULL REFERENCES respuestas ON DELETE CASCADE,
            tipo text NOT NULL,
            texto text NOT NULL,
            fragmento_id bigint,
            veredicto text NOT NULL,
            detalle jsonb,
            creado_en timestamptz NOT NULL DEFAULT now())
    """)

    op.execute("""
        CREATE TABLE casos_eval (
            id serial PRIMARY KEY,
            organizacion_id int NOT NULL DEFAULT 1,
            conjunto text NOT NULL,
            asignatura_id int REFERENCES asignaturas,
            entrada jsonb NOT NULL,
            esperado jsonb NOT NULL,
            creado_en timestamptz NOT NULL DEFAULT now())
    """)

    op.execute("""
        CREATE TABLE corridas_eval (
            id serial PRIMARY KEY,
            organizacion_id int NOT NULL DEFAULT 1,
            ts timestamptz NOT NULL DEFAULT now(),
            commit_sha text NOT NULL,
            config jsonb NOT NULL,
            metricas jsonb NOT NULL,
            creado_en timestamptz NOT NULL DEFAULT now())
    """)

    op.execute("CREATE INDEX respuestas_por_consulta ON respuestas (consulta_id)")
    op.execute("CREATE INDEX afirmaciones_por_respuesta ON afirmaciones (respuesta_id)")
    op.execute("CREATE INDEX casos_eval_por_conjunto ON casos_eval (conjunto)")


def downgrade():
    for tabla in ("corridas_eval", "casos_eval", "afirmaciones", "respuestas"):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")
