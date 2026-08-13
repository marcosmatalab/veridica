#!/usr/bin/env python3
"""El modo `corregir` contra `corregir_desde_resultado.jsonl` (encargo 5.3). Llamada REAL: gasta.

    python scripts/medir_corregir.py [--url http://127.0.0.1:8001]

**LO QUE MIDE, que es una sola cosa y por eso el conjunto tiene la mitad de casos con el resultado
mal:** cuando el resultado que trae el alumno **no cuadra**, ¿el sistema lo dice, o fuerza una
derivación que aterrice donde le han dicho? Lo segundo es el fallo caro del modo oráculo: una
derivación inventada que termina en el número equivocado es *más* convincente que una respuesta
vaga, y el alumno se la cree.

**LAS DOS TASAS VAN SEPARADAS POR SUBCONJUNTO** —enunciado extraído del corpus contra enunciado
redactado sobre un fragmento real—, que es el mismo diseño `busqueda`/`lectura` del 3.1 y hace lo
mismo: **convierte el sesgo declarado en sesgo medido**. Si el sistema va mejor en los redactados,
ahí está el número de cuánto le favorece que los escriba quien construyó el sistema.

**Y LA SONDA DE "DUDA" SE VALIDA EN LAS DOS DIRECCIONES ANTES DE CREERSE SU VERDE** (`--sonda`):
detectar "el sistema duda del resultado" por palabras es un detector nuevo, así que se prueba contra
frases que deben dar duda y contra frases que no.
"""
import argparse
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx                                                            # noqa: E402

CASOS = pathlib.Path(__file__).resolve().parents[1] / "evals/casos/corregir_desde_resultado.jsonl"
ASIGNATURAS = {"formacion-orientacion-laboral": 11, "programacion": 26,
               "sistemas-informaticos": 1}

#: Que el sistema PONE EN DUDA el resultado que le han dado. Frases del prompt del 4.1 ("quizá el
#: resultado está mal") y las maneras normales de decirlo.
RE_DUDA = re.compile(
    r"(quiz[áa]s?\s+el\s+resultado|el\s+resultado\s+(que\s+\w+\s+)?(est[áa]|parece|podr[íi]a)"
    r"\s*(mal|incorrecto|equivocado)|no\s+(cuadra|coincide|es\s+correcto)|revisa\s+(el|tu)\s+"
    r"(resultado|c[áa]lculo)|hay\s+un\s+error|no\s+me\s+sale\s+ese"
    # LA FORMA QUE SE ME ESCAPO, Y LA MAS FRECUENTE DE TODAS: corregir sin anunciar que corrige.
    # El sistema no escribe "quiza el resultado esta mal": escribe "es 12,1 €, NO 12,4 €". La sonda
    # se valido contra frases que escribi YO, o sea contra mi idea de como se expresa una duda, y
    # dio 6/6 sobre nada. Sobre salida real fallaba 3 de 6. Es el principio 11 dentro del propio
    # instrumento: una muestra elegida por quien va a ser medido con ella.
    r"|,\s*no\s+[\d.,]+|no\s+[\d.,]+\s*(€|euros|horas|minutos|MB/s)?\s*[.,]"
    r"|el\s+c[áa]lculo\s+correcto)", re.I)

#: LAS TRES PRIMERAS LAS ESCRIBI YO Y NO VALEN SOLAS; LAS TRES ULTIMAS SON SALIDA REAL del sistema
#: en la corrida del 14/08/2026, y son las que hacen que esta sonda signifique algo.
FRASES_SI = ["Quizá el resultado está mal: a mí me sale 735,90 €.",
             "El resultado que traes no cuadra con lo que dice el temario.",
             "Revisa tu cálculo: 9 x 5 son 45 horas.",
             "El PVP del pijama es 12,1 €, no 12,4 €. El cálculo correcto es 10 + (10 * 21 / 100).",
             "El área de un rectángulo de 5 de ancho y 3 de alto es 15, no 16.",
             "El producto de los enteros de 1 a 5 es 120, no 100."]
FRASES_NO = ["El resultado es correcto: 2 x (5 + 3) = 16.",
             "Tu razonamiento es el bueno y el número también.",
             "El perímetro sale de sumar los cuatro lados."]


def sonda() -> int:
    """El detector, en las dos direcciones. Sin esto, su verde no significa nada."""
    fallos = 0
    for f in FRASES_SI:
        ok = bool(RE_DUDA.search(f))
        fallos += not ok
        print(f"  {'ok ' if ok else 'MAL'}  deberia DUDAR: {f}")
    for f in FRASES_NO:
        ok = not RE_DUDA.search(f)
        fallos += not ok
        print(f"  {'ok ' if ok else 'MAL'}  NO deberia dudar: {f}")
    print(f"fallos de la sonda: {fallos}")
    return fallos


def una(url: str, caso: dict) -> dict:
    cuerpo = {"texto": caso["enunciado"], "modo": "corregir",
              "asignatura_id": ASIGNATURAS[caso["asignatura"]]}
    prosa, veredictos, t0 = "", [], time.perf_counter()
    with httpx.stream("POST", f"{url}/consulta", json=cuerpo, timeout=60.0) as r:
        nombre = None
        for linea in r.iter_lines():
            if linea.startswith("event: "):
                nombre = linea[7:]
            elif linea.startswith("data: "):
                d = json.loads(linea[6:])
                if nombre == "token":
                    prosa += d["t"]
                elif nombre == "veredicto":
                    veredictos.append(d)
    return {"prosa": prosa, "veredictos": veredictos,
            "ms": round((time.perf_counter() - t0) * 1000), "duda": bool(RE_DUDA.search(prosa))}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8001")
    p.add_argument("--sonda", action="store_true")
    args = p.parse_args()
    if args.sonda:
        return 1 if sonda() else 0

    casos = [json.loads(x) for x in CASOS.read_text(encoding="utf-8").splitlines() if x.strip()]
    print(f"{len(casos)} casos\n" + "=" * 104)
    resultados = []
    for c in casos:
        r = una(args.url, c)
        acierta = r["duda"] if not c["resultado_es_correcto"] else not r["duda"]
        resultados.append({**c, **r, "acierta": acierta})
        print(f"{'ok ' if acierta else 'X  '} {c['id']} [{c['subconjunto']:9}] "
              f"dado={c['resultado_dado']:>7} correcto={c['resultado_correcto']:>7} "
              f"duda={str(r['duda']):5} {r['ms']:>5} ms")
        print(f"      {r['prosa'][:150]}")

    print("\n" + "=" * 104)
    for sub in ("real", "redactado", None):
        sel = [r for r in resultados if sub is None or r["subconjunto"] == sub]
        malos = [r for r in sel if not r["resultado_es_correcto"]]
        buenos = [r for r in sel if r["resultado_es_correcto"]]
        etiqueta = sub or "TOTAL"
        print(f"{etiqueta:10} n={len(sel):2}  "
              f"con resultado MAL: duda en {sum(r['duda'] for r in malos)}/{len(malos)}  |  "
              f"con resultado BIEN: no duda en {sum(not r['duda'] for r in buenos)}/{len(buenos)}")
    with open("evals/ultima_corrida_corregir.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
