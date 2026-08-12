"""La medida de dispersion entre corridas identicas (encargo 2.2, ampliada).

Esta funcion alimenta una decision: si el conjunto de afirmaciones baila entre corridas identicas,
la ablacion del 7.3 -la fila con verificacion contra la fila sin ella, que es el argumento central
del proyecto- puede quedar por debajo del ruido. O sea que es una sonda, y una sonda se valida
contra el caso en el que DEBE dispararse antes de creerse su verde.

Se prueba en las dos direcciones y por dimensiones separadas, porque el fallo que se persigue no es
"salieron textos distintos": es "salieron CONJUNTOS DE AFIRMACIONES distintos", que es otra cosa y
cuesta mucho mas.
"""
import json

from humo_proveedor import es_degenerado, medir_dispersion


def respuesta(afirmaciones, prosa="Una clave primaria identifica cada fila.") -> str:
    return json.dumps({
        "modo": "responder",
        "afirmaciones": afirmaciones,
        "respuesta_redactada": prosa,
        "siguiente_paso": {"tipo": "pregunta_al_alumno", "ref": None, "texto": "?"},
        "confianza_recuperacion": "baja",
    }, ensure_ascii=False)


def conocimiento(id_):
    return {"id": id_, "tipo": "conocimiento", "texto": f"hecho {id_}", "fragmento_id": None}


def literal(id_, fragmento):
    return {"id": id_, "tipo": "literal", "texto": f"cita {id_}", "fragmento_id": fragmento,
            "cita": "texto exacto del fragmento"}


def test_tres_respuestas_iguales_salen_estables_en_todo():
    d = medir_dispersion([respuesta([conocimiento(1)])] * 3)
    assert d["bytes_identicos"] and d["tipos_estables"] and d["fragmentos_estables"]
    assert d["n_afirmaciones"] == [1]
    assert d["similitud_prosa"] == 1.0


def test_si_solo_cambia_la_redaccion_el_conjunto_sigue_estable():
    """EL CASO QUE DECIDE. Si es este, la ablacion del 7.3 sigue siendo legible con N=3: lo que se
    compara son afirmaciones y veredictos, no la literalidad del texto."""
    d = medir_dispersion([respuesta([conocimiento(1)], "Identifica cada fila de la tabla."),
                          respuesta([conocimiento(1)], "Identifica cada fila de una tabla.")])
    assert not d["bytes_identicos"], "la mutacion no se aplico: los dos textos eran iguales"
    assert d["tipos_estables"] and d["n_afirmaciones"] == [1]
    assert 0.8 < d["similitud_prosa"] < 1.0


def test_si_cambia_el_numero_de_afirmaciones_la_sonda_lo_dice():
    d = medir_dispersion([respuesta([conocimiento(1)]),
                          respuesta([conocimiento(1), conocimiento(2)])])
    assert d["n_afirmaciones"] == [1, 2], "el numero varia y la sonda tiene que verlo"
    assert not d["tipos_estables"]


def test_si_cambian_los_tipos_con_el_mismo_numero_la_sonda_lo_dice():
    """El caso mas facil de que se cuele: dos afirmaciones en las dos corridas, pero una dice
    'literal' y la otra 'conocimiento'. Contando solo cuantas hay, esto pasaria por estable."""
    d = medir_dispersion([respuesta([conocimiento(1), literal(2, 7)]),
                          respuesta([conocimiento(1), conocimiento(2)])])
    assert d["n_afirmaciones"] == [2], "el numero es el mismo: por ahi no se caza"
    assert not d["tipos_estables"]


def test_dos_afirmaciones_del_mismo_tipo_que_dicen_cosas_distintas_no_pasan_por_estables():
    """El agujero mas fino de esta sonda, y por eso existe la dimension 5: numero igual, tipos
    iguales, fragmentos iguales... y las afirmaciones dicen otra cosa. Contando solo la forma del
    conjunto, esto se contaria como estabilidad."""
    a = respuesta([{"id": 1, "tipo": "conocimiento", "texto": "La clave primaria no admite nulos.",
                    "fragmento_id": None}])
    b = respuesta([{"id": 1, "tipo": "conocimiento", "texto": "Una tabla puede no tener clave.",
                    "fragmento_id": None}])
    d = medir_dispersion([a, b])
    assert d["n_afirmaciones"] == [1] and d["tipos_estables"] and d["fragmentos_estables"]
    assert d["similitud_afirmaciones"] < 0.7, "la dimension 5 tiene que ver que dicen otra cosa"


def test_el_primer_desvio_senala_donde_empiezan_a_diferir():
    """Un "bytes distintos" sin mas no dice si cambio una coma o media respuesta."""
    d = medir_dispersion([respuesta([conocimiento(1)], "identifica cada fila"),
                          respuesta([conocimiento(1)], "identifica cada FILA")])
    assert d["primer_desvio"] and "identifica cada" in d["primer_desvio"]["a"]
    assert medir_dispersion([respuesta([conocimiento(1)])] * 2)["primer_desvio"] is None


def test_si_cambian_los_fragmentos_citados_con_los_mismos_tipos_la_sonda_lo_dice():
    d = medir_dispersion([respuesta([literal(1, 7)]), respuesta([literal(1, 99)])])
    assert d["tipos_estables"], "los tipos son los mismos: por ahi tampoco"
    assert not d["fragmentos_estables"]
    assert d["fragmentos"] == [(7,), (99,)]


def test_sin_citas_ni_fragmentos_la_estabilidad_de_tipos_se_declara_degenerada():
    """Que los tipos salgan estables no significa nada si el modelo no tenia alternativa: sin
    recuperacion no existen 'literal' ni 'parafrasis'. Es una estabilidad de la gramatica, no del
    modelo, y venderla como estabilidad medida seria justo el verde mentiroso."""
    d = medir_dispersion([respuesta([conocimiento(1), conocimiento(2)])] * 3)
    assert d["tipos_estables"]
    assert es_degenerado(d), "estabilidad sin alternativa: hay que declararla degenerada"


def test_en_cuanto_hay_una_cita_real_la_medida_deja_de_ser_degenerada():
    """La otra direccion: con un 'literal' y su fragmento, el modelo SI eligio, y entonces la
    estabilidad de tipos es un dato."""
    d = medir_dispersion([respuesta([literal(1, 7)])] * 2)
    assert not es_degenerado(d)


def test_una_corrida_con_el_contrato_roto_no_cuenta_como_estable():
    """Un JSON roto no puede sumar a "todas iguales": seria un verde que sale de no haber mirado."""
    d = medir_dispersion([respuesta([conocimiento(1)]), "{esto no es JSON"])
    assert d["contratos_validos"] == 1
    assert not d["bytes_identicos"]
