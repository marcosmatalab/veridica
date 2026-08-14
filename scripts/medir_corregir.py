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
    #
    # Y VA POR DOS, las dos cazadas el 15/08/2026 al anclar la corrida del 14, y la segunda es
    # de otra familia:
    #
    # (1) EL ARREGLO DE ARRIBA SE ESCRIBIO SOBRE LOS EJEMPLOS QUE MIRE, no sobre la CLASE, asi
    #     que sobre la MISMA corrida seguia dando 2 de 5 donde el ojo ve 5. La clase, dicha en
    #     voz alta antes de escribir la condicion: (a) el sistema CONTRASTA el valor bueno con
    #     el que trajo el alumno --"X, no Y"-- y ese Y puede venir con preposicion o articulo
    #     ("no DE 150 MB/s", "no LOS 16"); y (b) el sistema declara INSUFICIENTE el valor del
    #     alumno sin contrastar cifras ("15 minutos no es suficiente").
    #
    # (2) LA SEGUNDA ALTERNATIVA LLEVABA UN BACKSPACE DE VERDAD (0x08) DONDE SE QUISO ESCRIBIR
    #     UN \b, asi que dentro de una cadena CRUDA exigia un caracter de retroceso literal
    #     antes de "no": no es que casara poco, es que NO PODIA CASAR NUNCA. Codigo muerto que
    #     ningun editor ensena y que ningun test veia, porque la otra alternativa tapaba el
    #     hueco en los dos casos que si salian. Lo escribio el canal que transporta el parche
    #     comiendose el escape --la misma averia que los acentos por heredoc-- y por eso este
    #     patch se aplico en BYTES y afirmando su recuento.
    #
    # Con (1) y (2): 2/6 -> 4/6 sobre la prosa guardada, y CERO falsos positivos sobre las 8
    # respuestas reales con el resultado bien -- la otra direccion medida sobre salida real y
    # no sobre frases mias, que es lo que fallo la primera vez.
    r"|,\s*no\s+(?:de\s+|los\s+|las\s+|el\s+|la\s+)?[\d.,]+"
    r"|\bno\s+(?:de\s+|los\s+|las\s+|el\s+|la\s+)?[\d.,]+\s*(€|euros|horas|minutos|MB/s)?\s*[.,]"
    r"|no\s+es\s+(suficiente|correcto|el\s+correcto|lo\s+correcto)"
    r"|el\s+c[áa]lculo\s+correcto)", re.I)

#: LAS TRES PRIMERAS LAS ESCRIBI YO Y NO VALEN SOLAS; LAS DEMAS SON SALIDA REAL del sistema en la
#: corrida del 14/08/2026 (anclada en evals/corridas/), y son las que hacen que esto signifique algo.
FRASES_SI = ["Quizá el resultado está mal: a mí me sale 735,90 €.",
             "El resultado que traes no cuadra con lo que dice el temario.",
             "Revisa tu cálculo: 9 x 5 son 45 horas.",
             "El PVP del pijama es 12,1 €, no 12,4 €. El cálculo correcto es 10 + (10 * 21 / 100).",
             "El área de un rectángulo de 5 de ancho y 3 de alto es 15, no 16.",
             "El producto de los enteros de 1 a 5 es 120, no 100.",
             # LAS DOS QUE EL DETECTOR VIEJO PERDIA, palabra por palabra como salieron (corr-020 y
             # corr-010). Van aqui y no en un test aparte porque una sonda que no lleva dentro sus
             # propios fallos historicos vuelve a perderlos en cuanto alguien toque el patron.
             "Por lo tanto, la escritura combinada teórica de dos discos de 150 MB/s en un RAID 0 "
             "es de 300 MB/s, no de 150 MB/s.",
             "El descanso mínimo en jornada continua de 5 horas es de 30 minutos, por lo que 15 "
             "minutos no es suficiente."]
#: Y LA OTRA DIRECCION TAMBIEN SALE DE SALIDA REAL, que es lo que fallo la primera vez: las tres
#: primeras las escribi yo; las cinco siguientes son respuestas reales a casos con el resultado
#: BIEN, donde el sistema acierta al NO dudar. Una de ellas (`corr-005`) es la trampa buena: dice
#: "no cumple con el maximo semanal" -- lleva un "no" y una cifra al lado y aun asi no es dudar del
#: resultado, que es exactamente la clase de falso positivo que un patron mas ancho se comeria.
FRASES_NO = ["El resultado es correcto: 2 x (5 + 3) = 16.",
             "Tu razonamiento es el bueno y el número también.",
             "El perímetro sale de sumar los cuatro lados.",
             "El trabajador cumple con el máximo diario de 9 horas, pero no cumple con el máximo "
             "semanal de 40 horas, ya que en total hace 40 horas.",
             "En una jornada continua de 7 horas, el descanso mínimo es de 15 minutos, según el "
             "fragmento F5962.",
             "El perímetro de un rectángulo de 5 de ancho y 3 de alto es 16, porque el perímetro "
             "de un rectángulo se calcula como (ancho + alto) * 2.",
             "El sumatorio de 1 a 10 es 55, como se calcula en el fragmento F1481.",
             "La escritura combinada teorica es de 200 MB/s, ya que cada disco aporta 100 MB/s y "
             "se suman."]

#: EL SUELO DEL DETECTOR, DECLARADO PARA QUE SU NUMERO NO SE LEA COMO EL DEL OJO. `corr-002`
#: contesta "El PVP del pijama es 12,1 €." al alumno que traia 12,4: dice el valor bueno y NO
#: CONTRASTA NADA. Ninguna ampliacion de un detector de FRASES lo caza, porque no hay nada en la
#: frase que lo separe de una respuesta normal -- haria falta comparar la cifra escrita contra
#: `resultado_dado`, o sea una EXTRACCION, que es el mecanismo que el ADR 0016 evito a proposito.
#: Asi que este detector se queda en 4 de 5 POR CONSTRUCCION, y el 5 de 6 que se publica es el del
#: ojo, con su firma al lado. Los dos numeros, nunca uno.
SUELO_DECLARADO = ("corr-002: dice el valor correcto sin contrastarlo con el del alumno; "
                   "eso pide extraccion, no un detector de frases")


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
    cobertura, abstencion = None, None
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
                elif nombre == "cobertura":
                    cobertura = d
                elif nombre == "abstencion":
                    abstencion = d
    return {"prosa": prosa, "veredictos": veredictos, "cobertura": cobertura,
            "abstencion": abstencion,
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
    # EL EMBUDO PRIMERO, Y LA TASA DE LOS SUPERVIVIENTES DESPUES. "5 de 6 corrigen" esta
    # condicionado a haber sido entregada, y el denominador honesto son los 20: si solo se publica
    # la tasa, el numero dice "el modo corregir funciona" cuando lo que dice es "funciona en los
    # casos que nuestras propias puertas dejaron pasar".
    vacias = [r for r in resultados if not r["prosa"].strip()]
    por_plazo = [r for r in vacias if (r.get("abstencion") or {}).get("por_plazo")]
    por_cobertura = [r for r in vacias if (r.get("abstencion") or {}).get("por_cobertura")]
    print(f"EMBUDO de {len(resultados)} casos: llegan al alumno {len(resultados) - len(vacias)}"
          f" | en blanco por cobertura {len(por_cobertura)}"
          f" | cortadas por plazo {len(por_plazo)}"
          f" | vacias sin declarar {len(vacias) - len(por_plazo) - len(por_cobertura)}")
    print("(las tasas de abajo van sobre las ENTREGADAS: son las que sobrevivieron a nuestras "
          "puertas, no una muestra al azar)")
    for sub in ("real", "redactado", None):
        sel = [r for r in resultados if sub is None or r["subconjunto"] == sub]
        malos = [r for r in sel if not r["resultado_es_correcto"]]
        buenos = [r for r in sel if r["resultado_es_correcto"]]
        etiqueta = sub or "TOTAL"
        print(f"{etiqueta:10} n={len(sel):2}  "
              f"con resultado MAL: duda en {sum(r['duda'] for r in malos)}/{len(malos)}  |  "
              f"con resultado BIEN: no duda en {sum(not r['duda'] for r in buenos)}/{len(buenos)}")
    salida = "evals/ultima_corrida_corregir.json"
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)

    # EL ANCLAJE ES SALIDA DEL COMANDO, NO UNA NOTA QUE ALGUIEN RECUERDE. `ultima_corrida` se
    # llama asi porque significa "lo que corrio la ultima vez": deja de ser cierto en cuanto
    # alguien vuelve a correr esto, y por eso NO se versiona. La corrida que sostiene un numero
    # publicado se copia a un nombre inmutable y se cita desde su evidencia. Es la idea de
    # fusionar.py otra vez: si un paso puede olvidarse, se convierte en salida del paso anterior.
    print(f"\n{salida} escrito (NO se versiona: su nombre caduca solo).")
    print("SI ESTA CORRIDA SOSTIENE UN NUMERO QUE VAS A PUBLICAR, anclala copiando y pegando:\n")
    print(f"    python -c \"import shutil;shutil.copy(r'{salida}',"
          f" r'evals/corridas/AAAA-MM-DD-corregir-QUE.json')\"\n")
    print("Y CITALA DESDE SU FICHERO DE EVIDENCIA. Un numero sin su corrida al lado es un numero "
          "sin denominador comprobable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
