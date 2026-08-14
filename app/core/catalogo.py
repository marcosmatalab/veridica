"""Lo que la interfaz necesita leer de la base: el selector y el fragmento citado (encargo 2.4).

DOS COSAS Y UNA REGLA.

**El selector sale de la puente, no de una lista escrita a mano.** `titulacion_asignaturas` es donde
el 2.1 dejó los transversales mapeados a las tres titulaciones, así que un alumno de ASIR ve sus
módulos propios *y* el 0373, que se carga una sola vez bajo DAW. Es el primer sitio donde ese
trabajo se ve en pantalla, y también el sitio donde se rompería en silencio: una lista escrita a mano
seguiría pareciendo correcta el día que el árbol cambie.

**El fragmento se abre POR PROCEDENCIA.** `fragmento_citado(respuesta_id, fragmento_id)` devuelve el
fragmento solo si esa respuesta lo citó, comprobado contra `afirmaciones`. Lo que legitima leerlo no
es que sea de tu asignatura: es que **el sistema lo usó para responderte**. Y de paso cierra por
construcción la lectura cruzada entre asignaturas —cambiar un id en la URL no abre el temario de
otro módulo—, que es exactamente la contaminación que el 3.5 mide. Lo que NO cierra, y queda
declarado: no hay sesión de usuario todavía, así que quien tenga un `respuesta_id` puede leer los
fragmentos de esa respuesta. La autorización por usuario es de la fase 8, con `organizacion_id`, que
hoy está "preparado, no gestionado" (sección 9).
"""
from app.core.conexion import conectar


#: EL BARRIDO, campo a campo, de lo que el selector enseña de una asignatura alcanzada por la
#: puente. La regla: **por la puente solo viaja lo que la norma de QUIEN PREGUNTA respalda.**
#:
#: | Campo | ¿Estaba afectado? | Qué se hace |
#: |---|---|---|
#: | `codigo` | no | viaja: el código es el mismo en los tres títulos, y eso es lo que hace transversal a un módulo |
#: | `nombre` | **sí** | sale de la puente: "Lenguajes de marcas y sistemas de gestión de información" (RD 405/2023, DAW) frente a "Lenguajes de Marcas y Sistemas de Gestión de Información" (RD 1629/2009, ASIR) |
#: | `curso` | **sí** | sale de la puente, y es nulo en DAM y ASIR porque no hay orden de currículo suya |
#: | `horas` | **sí** | sale de la puente, nulo por lo mismo. Antes ni se exponía; exponerlo con el número de DAW habría sido el mismo fallo |
#: | `norma` | no existía | se añade: el nombre se acompaña de la norma que lo respalda, para que se pueda comprobar |
#: | `titulacion_duena` | no | viaja etiquetado como lo que es: dónde vive la fila, no de quién es el módulo |
#: | `fragmentos` | no | es un hecho de NUESTRO corpus, no de ninguna norma: no depende del título que pregunta |
#:
#: Tres campos afectados de siete. El primero (`curso`) se encontró mirando la pantalla; los otros
#: dos salieron de barrer, que es la lección de siempre: un caso encontrado y no barrido es una
#: familia esperando.
CAMPOS_DE_LA_NORMA_DE_QUIEN_PREGUNTA = ("nombre", "curso", "horas", "norma")


def fila_a_asignatura(fila: tuple, titulacion: str) -> dict:
    """Una fila de la puente, como la ve el selector. Los campos normativos salen de la puente."""
    identificador, codigo, duena, nombre, curso, horas, norma, fragmentos = fila
    return {"id": identificador, "codigo": codigo, "nombre": nombre, "curso": curso,
            "horas": horas, "norma": norma, "titulacion_duena": duena, "fragmentos": fragmentos,
            "transversal": duena != titulacion}


class CatalogoEnMemoria:
    """El de los tests: en CI no hay Postgres ni corpus (mismo criterio que el ADR 0001)."""

    def __init__(self, asignaturas=None, fragmentos=None):
        self._asignaturas = asignaturas or {}
        self._fragmentos = fragmentos or {}

    def titulaciones(self) -> list:
        return sorted(self._asignaturas)

    def asignaturas(self, titulacion: str) -> list:
        return list(self._asignaturas.get(titulacion, []))

    def fragmento_citado(self, respuesta_id: int, fragmento_id: int):
        return self._fragmentos.get((respuesta_id, fragmento_id))


class CatalogoPostgres:
    def __init__(self, url: str):
        self.url = url

    def titulaciones(self) -> list:
        with conectar(self.url) as con, con.cursor() as cur:
            cur.execute("SELECT DISTINCT titulacion FROM titulacion_asignaturas ORDER BY 1")
            return [f[0] for f in cur.fetchall()]

    def asignaturas(self, titulacion: str) -> list:
        """Las de esa titulación A TRAVÉS DE LA PUENTE. Sumar filas de `asignaturas` daría 13/9/13
        en vez de 13/14/14: los transversales viven en una sola fila bajo su titulación dueña.

        Los campos normativos —nombre, curso, horas, norma— salen de `titulacion_asignaturas` y no
        de `asignaturas`, que lleva los de la dueña. Ver el barrido de arriba.
        """
        with conectar(self.url) as con, con.cursor() as cur:
            cur.execute(
                "SELECT a.id, a.codigo, a.titulacion, t.nombre, t.curso, t.horas, t.norma,"
                "       (SELECT count(*) FROM fragmentos f WHERE f.asignatura_id = a.id)"
                "  FROM titulacion_asignaturas t JOIN asignaturas a ON a.id = t.asignatura_id"
                " WHERE t.titulacion = %s ORDER BY t.curso NULLS LAST, a.codigo", (titulacion,))
            return [fila_a_asignatura(f, titulacion) for f in cur.fetchall()]

    def fragmento_citado(self, respuesta_id: int, fragmento_id: int):
        with conectar(self.url) as con, con.cursor() as cur:
            cur.execute(
                "SELECT f.id, f.texto, f.contexto, f.unidad, f.tipo_contenido, d.ruta, d.titulo,"
                "       a.codigo, a.nombre"
                "  FROM afirmaciones af"
                "  JOIN fragmentos f ON f.id = af.fragmento_id"
                "  JOIN documentos d ON d.id = f.documento_id"
                "  JOIN asignaturas a ON a.id = f.asignatura_id"
                " WHERE af.respuesta_id = %s AND af.fragmento_id = %s LIMIT 1",
                (respuesta_id, fragmento_id))
            fila = cur.fetchone()
        if fila is None:
            return None
        campos = ("id", "texto", "contexto", "unidad", "tipo_contenido", "ruta", "documento",
                  "codigo", "asignatura")
        return dict(zip(campos, fila))
