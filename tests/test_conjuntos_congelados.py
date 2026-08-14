"""Los tres conjuntos del 4.0/5.x están CONGELADOS: se corren, no se ajustan al resultado.

El sha anclado es la versión mecánica de esa promesa (el del 5.3 se congeló igual, con su sha en la
evidencia): cambiar un byte pone esto en rojo, y un cambio legítimo del propietario se hace
actualizando el sha AQUÍ, en un commit que lo declare. La estructura también se ancla: cada caso
lleva su `por_que`, y cada conjunto lleva DOS controles en dirección contraria — sin ellos, un
sistema que se abstuviera siempre o que sospechara de todo sacaría pleno.
"""
import hashlib
import json
import pathlib

CASOS = pathlib.Path(__file__).resolve().parents[1] / "evals" / "casos"

CONGELADOS = {
    "fuga_de_solucion": ("bae6feb19b8fb56dc53e559956a7fa9d9f79aea37643bd9336e883d51ba0d5a5",
                         12, "legitimo_no_es_fuga"),
    "fuera_de_temario": ("48b54aa7bac4423b1cb8965b1212bde25e1353c3a89621cade17eca409fd4063",
                         10, "legitimo_no_es_fuera"),
    "premisas_falsas": ("c269a3141ae721d0bcfbf08573560a9366126ad4bcdc4412b5a698df793e2139",
                        10, "legitimo_no_es_falsa"),
}

#: EL CUARTO CONJUNTO CONGELADO, QUE LLEVABA DESDE EL 14/08 CONGELADO **SOLO EN PROSA** (15/08/2026).
#:
#: Su evidencia dice dos veces *"congelado antes de correr ni un caso: sha256 f3c6848b…"* y
#: *"el conjunto no se tocó, comprobado antes de volver a correr"* — y **ningún test lo comprobaba**:
#: la promesa vivía en un documento que alguien tenía que acordarse de leer. Es exactamente la regla
#: de la casa sobre las reglas escritas: si se puede saltar, se salta, y el arreglo es un paso del
#: procedimiento y no un párrafo.
#:
#: **Y AL ANCLARLO SALIÓ POR QUÉ NADIE LO HABÍA NOTADO: el sha publicado no reproduce.** El fichero
#: en disco da `894f880e…` y el publicado es `f3c6848b…`. **El contenido está intacto**, y se
#: demuestra en una línea: `sha256(contenido con CRLF) == f3c6848b…` exacto. O sea que el sha
#: publicado hashea **los finales de línea de una copia de trabajo**, no el fichero del repo —con
#: `core.autocrlf=input`, git guarda LF y la copia de Windows podía tener CRLF—. **Un hash que
#: cambia según por dónde pasó el fichero no ancla el contenido: ancla el transporte**, que es la
#: misma familia que el canal comiéndose un escape. Se ancla el de LF, que es el que el repo guarda
#: y el que cualquiera puede reproducir; el viejo queda escrito arriba en vez de borrado.
#:
#: Su estructura NO es la de los otros tres —no lleva `familia` ni `por_que`— y por eso va aparte
#: en vez de forzarse dentro del diccionario: **sus dos controles en dirección contraria son los 10
#: casos con el resultado BIEN**, que existen para que un sistema que dudara de todo no saque pleno.
CONGELADO_5_3 = ("corregir_desde_resultado",
                 "894f880e877a9977e28bbcc829846a78e349e015df2f5935ea572b92cf0f5cf7", 20)
SHA_PUBLICADO_CON_CRLF = "f3c6848b7a2f447f9bae96b77bc53646742f2944741e7efd7ca1c56cbf8674fe"


def _casos(nombre):
    ruta = CASOS / f"{nombre}.jsonl"
    return ruta, [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_los_tres_conjuntos_estan_congelados_byte_a_byte():
    for nombre, (sha, _, _) in CONGELADOS.items():
        ruta, _ = _casos(nombre)
        assert hashlib.sha256(ruta.read_bytes()).hexdigest() == sha, \
            f"{nombre} ha cambiado: un conjunto congelado no se ajusta al resultado"


def test_el_conjunto_del_5_3_tambien_esta_congelado_byte_a_byte():
    """La promesa que llevaba un día viviendo solo en un documento."""
    nombre, sha, _ = CONGELADO_5_3
    ruta, _casos_ = _casos(nombre)
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == sha, \
        f"{nombre} ha cambiado: un conjunto congelado no se ajusta al resultado"


def test_el_sha_publicado_del_5_3_era_el_del_CRLF_y_el_contenido_es_el_MISMO():
    """**LA CORRECCIÓN SE DECLARA, NO SE BORRA**, y aquí además se puede demostrar en una línea.

    Que el sha publicado no reproduzca admite dos lecturas —*"tocaron el conjunto"* y *"hasheamos
    otra cosa"*— y son muy distintas: la primera invalidaría los números del 5.3 enteros. Este test
    decide entre las dos **con el dato**, no con la memoria: si el contenido normalizado a CRLF da
    exactamente el sha publicado, el fichero es byte a byte el que se congeló y lo que cambió fue
    el transporte. Y queda anclado, para que nadie tenga que volver a preguntárselo."""
    nombre, _, _ = CONGELADO_5_3
    ruta, _casos_ = _casos(nombre)
    crudo = ruta.read_bytes()
    con_crlf = crudo.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    assert hashlib.sha256(con_crlf).hexdigest() == SHA_PUBLICADO_CON_CRLF, \
        ("el contenido NO coincide ni siquiera normalizando finales de linea: entonces si que "
         "tocaron el conjunto congelado y los numeros del 5.3 hay que re-derivarlos")


def test_el_5_3_lleva_sus_20_casos_y_sus_controles_en_direccion_contraria():
    """Sus controles no son una familia aparte: son la mitad del conjunto. 10 con el resultado mal
    (¿lo dice?) y 10 con el resultado bien (¿se calla?). Sin la segunda mitad, un sistema que
    dudara de todo sacaría pleno — que es la misma razón por la que los otros tres llevan dos."""
    nombre, _, n = CONGELADO_5_3
    _, casos = _casos(nombre)
    assert len(casos) == n, f"{nombre}: {len(casos)} casos y se declararon {n}"
    mal = [c for c in casos if not c["resultado_es_correcto"]]
    bien = [c for c in casos if c["resultado_es_correcto"]]
    assert len(mal) == 10 and len(bien) == 10, \
        "el conjunto dejo de estar partido por la mitad: la mitad buena ES el control"
    assert all(c.get("resultado_correcto") for c in casos), \
        "un caso sin su resultado bueno no permite corregir la correccion"
    assert {c["subconjunto"] for c in casos} == {"real", "redactado"}, \
        "el sesgo declarado se vuelve medido separando extraido de redactado (diseno del 3.1)"


def test_cada_caso_lleva_su_por_que_y_cada_conjunto_sus_dos_controles():
    for nombre, (_, n, familia_control) in CONGELADOS.items():
        _, casos = _casos(nombre)
        assert len(casos) == n, f"{nombre}: {len(casos)} casos y se declararon {n}"
        assert all((c.get("por_que") or "").strip() for c in casos), f"{nombre}: caso sin por_que"
        controles = [c for c in casos if c["familia"] == familia_control]
        assert len(controles) == 2, \
            f"{nombre}: {len(controles)} controles; sin los dos, abstenerse siempre saca pleno"
