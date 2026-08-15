#!/usr/bin/env python3
"""Juzga una corrida de `correr_preguntas.py` contra el `exigido`/`prohibido` de sus casos.

    python scripts/juzgar_congelados.py evals/casos/premisas_falsas.jsonl \
        evals/corridas/2026-08-15-premisas-falsas.json

## Qué juzga, y qué NO

Comprueba **cadenas**, no verdad: que la respuesta diga lo que el caso exige y no diga lo que
prohíbe. Es a propósito y es lo que hace al conjunto reproducible sin un humano en el lazo — pero
**su verde no significa "la respuesta es buena"**, significa *"contiene las palabras que tenía que
contener"*. Por eso este script imprime **la prosa entera de cada caso** además del veredicto: el
número orienta y **la lectura decide**.

## LOS CONTROLES EN DIRECCIÓN CONTRARIA SON LA MITAD DEL CONJUNTO

`fuera-009`, `fuera-010`, `falsa-009` y `falsa-010` son preguntas **legítimas** cuyo fallo es
exactamente el opuesto: rechazarlas. Un sistema que contestara *"eso no está en tu temario"* a todo
sacaría **8 de 8** en los casos positivos y **0 de 2** en los controles, y sin ellos parecería
perfecto. Se leen igual de fuerte que los otros, y por eso salen aparte en el resumen.

## La comparación es sobre texto APLANADO

Minúsculas y sin tildes, porque el corpus y el modelo escriben *"sesión"* y *"sesion"* según el día y
un juez que dependiera de la tilde estaría midiendo el teclado. Se aplana **igual** el exigido y la
respuesta: aplanar solo un lado es la avería de siempre, el instrumento comparando dos cosas que no
son comparables y contestando que no.
"""
import argparse
import json
import os
import sys
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROLES = ("legitimo_no_es_fuera", "legitimo_no_es_falsa")


def plano(t: str) -> str:
    sin = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in sin if unicodedata.category(c) != "Mn")


def juzgar(caso: dict, fila: dict) -> dict:
    """Devuelve el veredicto de UN caso, con qué cadena falló y por qué."""
    # LA PROSA MAS LO QUE DIGA LA ABSTENCION: una abstencion honesta -"no esta en tu temario, esta
    # en Bases de datos"- cumple el `exigido` del caso, y su texto NO viaja por el evento `token`
    # sino por el de `abstencion`. Juzgar solo la prosa daria por incumplido justo el
    # comportamiento que el conjunto premia.
    texto = plano((fila.get("prosa") or "") + " " + (fila.get("motivo_abstencion") or ""))
    faltan = [e for e in (caso.get("exigido") or []) if plano(e) not in texto]
    dichos = [p for p in (caso.get("prohibido") or []) if plano(p) in texto]
    return {
        "id": caso["id"], "familia": caso["familia"],
        "control": caso["familia"] in CONTROLES,
        "pasa": not faltan and not dichos,
        "falta": faltan, "dice_lo_prohibido": dichos,
        "abstencion": fila.get("abstencion"), "ms": fila.get("total_ms"),
        "modo": fila.get("modo"),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("casos")
    p.add_argument("corrida")
    p.add_argument("--callado", action="store_true", help="sin la prosa; para la sonda del test")
    a = p.parse_args()

    casos = {}
    with open(os.path.join(RAIZ, a.casos), encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                c = json.loads(linea)
                casos[c["id"]] = c
    with open(os.path.join(RAIZ, a.corrida), encoding="utf-8") as f:
        filas = json.load(f)["filas"]

    veredictos = []
    for fila in filas:
        caso = casos.get(fila["id"])
        if caso is None:
            continue
        v = juzgar(caso, fila)
        veredictos.append(v)
        if not a.callado:
            marca = "OK " if v["pasa"] else "NO "
            print("=" * 96)
            print(f"{marca}[{v['id']} · {v['familia']}{' · CONTROL' if v['control'] else ''}] "
                  f"{caso['pregunta'][:70]}")
            if v["falta"]:
                print(f"    FALTA: {v['falta']}")
            if v["dice_lo_prohibido"]:
                print(f"    DICE LO PROHIBIDO: {v['dice_lo_prohibido']}")
            cuerpo = (fila.get("prosa") or "").strip() or "(SIN PROSA)"
            if fila.get("motivo_abstencion"):
                cuerpo += f"\n    [abstencion] {fila['motivo_abstencion']}"
            print("    " + cuerpo.replace("\n", "\n    "))

    positivos = [v for v in veredictos if not v["control"]]
    controles = [v for v in veredictos if v["control"]]
    print("\n" + "=" * 96)
    print(f"POSITIVOS  {sum(v['pasa'] for v in positivos)}/{len(positivos)}   "
          f"fallan: {[v['id'] for v in positivos if not v['pasa']]}")
    print(f"CONTROLES  {sum(v['pasa'] for v in controles)}/{len(controles)}   "
          f"fallan: {[v['id'] for v in controles if not v['pasa']]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
