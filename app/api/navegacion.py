"""Lo que la interfaz consulta además del chat (encargo 2.4): el selector y el fragmento citado."""
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/titulaciones")
def titulaciones(request: Request) -> dict:
    return {"titulaciones": request.app.state.catalogo.titulaciones()}


@router.get("/asignaturas")
def asignaturas(titulacion: str, request: Request) -> dict:
    """El selector del alumno. Sale de la puente, así que un alumno de ASIR ve sus módulos propios
    y también los transversales que viven bajo DAW."""
    filas = request.app.state.catalogo.asignaturas(titulacion)
    if not filas:
        raise HTTPException(404, f"ninguna asignatura para la titulacion '{titulacion}'")
    return {"titulacion": titulacion, "asignaturas": filas}


@router.get("/respuestas/{respuesta_id}/fragmentos/{fragmento_id}")
def fragmento(respuesta_id: int, fragmento_id: int, request: Request) -> dict:
    """El fragmento se abre POR PROCEDENCIA: solo si esa respuesta lo citó.

    El 404 de aquí no es "no existe": es "esa respuesta no cita ese fragmento", y son cosas
    distintas a propósito. Cambiar el id en la URL no abre el temario de otra asignatura.
    """
    datos = request.app.state.catalogo.fragmento_citado(respuesta_id, fragmento_id)
    if datos is None:
        raise HTTPException(404, f"la respuesta {respuesta_id} no cita el fragmento {fragmento_id}: "
                                 f"los fragmentos se abren por procedencia, no por id suelto")
    return datos
