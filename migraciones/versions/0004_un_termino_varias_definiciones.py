"""Un término puede tener más de una definición en el glosario (encargo 2.6, ADR 0012).

Revision: 0004
Padre: 0003

El DDL de la sección 9 traía `UNIQUE (asignatura_id, termino)`, y esa restricción impide el momento
3 de la demo: el DWES antiguo y el moderno mapean los dos al 0613 —decidido así en el 2.1 para que
sus materiales cayeran en la misma partición y se pudieran comparar—, de modo que las dos
definiciones incompatibles de MVC son del mismo `(asignatura_id, termino)` y la segunda no entraría.

Se cambia a `UNIQUE (asignatura_id, termino, fragmento_id)`: se sigue impidiendo la duplicación de
verdad —la misma definición extraída dos veces del mismo fragmento— y se permite lo que el corpus
tiene. Y así **que un término tenga más de una entrada pasa a SER la señal de conflicto**, con un
GROUP BY determinista en vez de un umbral de similitud.

`fragmento_id` pasa a llevar índice: la consulta del conflicto agrupa por término, pero la traza va
al revés, del fragmento a sus entradas.
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE glosario DROP CONSTRAINT IF EXISTS glosario_asignatura_id_termino_key")
    op.execute("ALTER TABLE glosario ADD CONSTRAINT glosario_termino_por_fragmento"
               " UNIQUE (asignatura_id, termino, fragmento_id)")
    op.execute("CREATE INDEX IF NOT EXISTS glosario_por_termino ON glosario (asignatura_id, termino)")
    # Columnas que la validación del 2.6 necesita para que una entrada se pueda AUDITAR después, y
    # no solo aceptar ahora: cómo se validó (literal o NLI) y con qué evidencia.
    op.execute("""
        ALTER TABLE glosario
            ADD COLUMN IF NOT EXISTS via_validacion text,
            ADD COLUMN IF NOT EXISTS evidencia text
    """)


def downgrade():
    op.execute("ALTER TABLE glosario DROP CONSTRAINT IF EXISTS glosario_termino_por_fragmento")
    op.execute("DROP INDEX IF EXISTS glosario_por_termino")
    op.execute("ALTER TABLE glosario DROP COLUMN IF EXISTS via_validacion,"
               " DROP COLUMN IF EXISTS evidencia")
    op.execute("ALTER TABLE glosario ADD CONSTRAINT glosario_asignatura_id_termino_key"
               " UNIQUE (asignatura_id, termino)")
