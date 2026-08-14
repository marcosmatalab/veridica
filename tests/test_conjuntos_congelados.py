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


def _casos(nombre):
    ruta = CASOS / f"{nombre}.jsonl"
    return ruta, [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_los_tres_conjuntos_estan_congelados_byte_a_byte():
    for nombre, (sha, _, _) in CONGELADOS.items():
        ruta, _ = _casos(nombre)
        assert hashlib.sha256(ruta.read_bytes()).hexdigest() == sha, \
            f"{nombre} ha cambiado: un conjunto congelado no se ajusta al resultado"


def test_cada_caso_lleva_su_por_que_y_cada_conjunto_sus_dos_controles():
    for nombre, (_, n, familia_control) in CONGELADOS.items():
        _, casos = _casos(nombre)
        assert len(casos) == n, f"{nombre}: {len(casos)} casos y se declararon {n}"
        assert all((c.get("por_que") or "").strip() for c in casos), f"{nombre}: caso sin por_que"
        controles = [c for c in casos if c["familia"] == familia_control]
        assert len(controles) == 2, \
            f"{nombre}: {len(controles)} controles; sin los dos, abstenerse siempre saca pleno"
