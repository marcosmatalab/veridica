"""El reparador del manifiesto de `fusionar.py`, visto en las dos direcciones.

Un reparador que repara de más es la puerta poniéndose verde sola (la regla de `verificar_oro`:
un verificador que sabe reescribir lo que verifica no verifica nada). Aquí lo único autorreparable
tras un merge limpio es el `HASH DISTINTO` —contenido fusionado que nadie hasheó—; todo lo demás
se mira a mano, y estos tests anclan esa frontera.
"""
import importlib.util
import pathlib

RUTA = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "fusionar.py"


def _modulo():
    spec = importlib.util.spec_from_file_location("fusionar", RUTA)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SALIDA_TIPICA = """HASH DISTINTO: corpus/COBERTURA.md
  esperado 6fa1f4330a9855e28e1b8933ea152c33e93f956947193f9dabe4839a3f58fb64
  obtenido 314403a47bec5ad8f6e799b40c72c06d2c74427a4c1b8fb89557fe14e4bfdb70
disco=2414 manifiesto=2414 hashes=2414 en 1.1s
ocurrencias=1 en 1 de 4 clases sin_manifiesto=0 sin_fichero=0 hash_distinto=1 ruta_duplicada=0
"""


def test_saca_los_hash_distintos_y_solo_esos():
    m = _modulo()
    assert m.ficheros_con_hash_distinto(SALIDA_TIPICA) == ["corpus/COBERTURA.md"]
    assert m.ficheros_con_hash_distinto("ocurrencias=0 en 0 de 4 clases") == []
    # los hashes de las lineas "esperado/obtenido" no son rutas y no pueden colarse
    assert all("esperado" not in r for r in m.ficheros_con_hash_distinto(SALIDA_TIPICA))


def test_lo_que_NO_es_un_hash_viejo_no_se_autorrepara():
    """La direccion en que el reparador tiene que NEGARSE: un fichero que falta o una ruta duplicada
    no es un hash desactualizado, y recalcular ahi seria taparlo."""
    m = _modulo()
    con_falta = SALIDA_TIPICA + "SIN FICHERO: corpus/borrado.md\n"
    assert m.hay_hallazgos_no_reparables(con_falta)
    assert m.hay_hallazgos_no_reparables("RUTA DUPLICADA: corpus/x.md\n")
    assert m.hay_hallazgos_no_reparables("SIN MANIFIESTO: corpus/nuevo.md\n")
    assert not m.hay_hallazgos_no_reparables(SALIDA_TIPICA)
