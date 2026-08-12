"""La puente lleva lo que dice la norma de CADA titulación, no la de la dueña (encargo 2.4, barrido).

Revision: 0003
Padre: 0002

EL CASO QUE LO ABRIÓ, y la familia que había detrás. En el selector, el módulo transversal 0373
aparecía para un alumno de ASIR con curso "1.º" — que es el curso que le da la **orden de currículo
de DAW**, porque la fila de esa asignatura vive bajo DAW (se carga una vez y se alcanza por la
puente). Se tapó nulando el curso, y ese arreglo estaba incompleto: **el nombre y las horas viajaban
igual**. El 0373 se llama "Lenguajes de marcas y sistemas de gestión de información" en el RD
405/2023 de DAW y "Lenguajes de Marcas y Sistemas de Gestión de Información" en el RD 1629/2009 de
ASIR, y las horas salen de una orden de currículo que ASIR no tiene. Un alumno de ASIR estaba
leyendo la redacción de una norma que no le aplica.

**El criterio general, que es lo que de verdad se arregla aquí: por la puente solo viaja lo que la
norma de QUIEN PREGUNTA respalda.** Y la forma de que eso no dependa de que alguien se acuerde es
ponerlo en el modelo de datos: los hechos que dependen de la titulación viven en la fila de la
puente, que es exactamente la fila que representa "este módulo, visto desde este título".

`asignaturas` sigue con el nombre y el curso de su titulación dueña, que son correctos para ella y
son los que usa la carga. Lo que el selector enseña sale de aquí.
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE titulacion_asignaturas
            ADD COLUMN nombre text,
            ADD COLUMN curso smallint,
            ADD COLUMN horas int,
            ADD COLUMN norma text
    """)
    # Todas admiten NULL a propósito y es la misma regla del `curso` de la 0001: DAM y ASIR no
    # tienen orden de currículo en el corpus, así que su curso y sus horas NO CONSTAN. Un NOT NULL
    # aquí obligaría a inventarse el dato, que es justo el fallo que esta migración corrige.


def downgrade():
    op.execute("""
        ALTER TABLE titulacion_asignaturas
            DROP COLUMN IF EXISTS nombre,
            DROP COLUMN IF EXISTS curso,
            DROP COLUMN IF EXISTS horas,
            DROP COLUMN IF EXISTS norma
    """)
