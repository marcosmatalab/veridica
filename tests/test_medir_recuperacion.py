"""La sonda nueva del arnés del 3.5 —nDCG@5— vista fallar donde debe ANTES de creerse su verde.

Regla del repo: toda métrica nueva se valida contra un caso donde debe fallar, y deja test de
regresión anclado. Aquí el caso donde debe fallar es el oro ausente o fuera del corte: si eso no
da cero, el nDCG estaría premiando contextos que no contienen la respuesta.
"""
import importlib.util
import pathlib

RUTA = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "medir_recuperacion.py"


def _arnes():
    spec = importlib.util.spec_from_file_location("medir_recuperacion", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_ndcg_da_CERO_donde_debe_y_uno_donde_debe():
    m = _arnes()
    # la direccion en que la sonda tiene que FALLAR: oro ausente o fuera del corte -> 0, no un
    # numero amable
    assert m.ndcg_en_5(None) == 0.0
    assert m.ndcg_en_5(6) == 0.0
    # y la sana: primero es perfecto, y el descuento es el del logaritmo
    assert m.ndcg_en_5(1) == 1.0
    assert abs(m.ndcg_en_5(3) - 0.5) < 1e-9          # 1/log2(4)


def test_el_ndcg_ORDENA_las_posiciones_porque_para_eso_existe():
    """Si dos posiciones distintas puntuaran igual, la métrica no mediría orden y el reordenador
    parecería inútil por construcción — el verde mentiroso del instrumento."""
    m = _arnes()
    assert m.ndcg_en_5(1) > m.ndcg_en_5(2) > m.ndcg_en_5(3) > m.ndcg_en_5(5) > 0.0
