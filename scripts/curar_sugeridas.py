#!/usr/bin/env python3
"""Comprueba las preguntas sugeridas del estado vacío CONTRA LA CONFIGURACIÓN QUE CORRE.

    python scripts/curar_sugeridas.py

**POR QUÉ ESTO EXISTE Y NO SE ELIGEN A OJO.** Las cuatro preguntas del estado vacío son lo primero
que ve quien llega, y son **curación declarada**: se eligen para que enseñen las cuatro cosas que el
sistema sabe hacer. Una pregunta curada que la recuperación **no encuentra** convierte la primera
pantalla en la peor demo posible — y eso no se sabe mirándola, se sabe corriéndola.

Sin argumentos corre la **recuperación real** (léxica + vectorial + glosario + fusión 10:1, con el
embebedor de verdad) y NO llama al proveedor: contesta *"¿la encuentra la configuración actual?"*,
que es una pregunta sobre la fase 3. Sale gratis.

Para la de **fuera de temario** la comprobación es la contraria y por eso va aparte: lo que tiene
que salir es confianza **baja** en su asignatura y que la cascada la encuentre en OTRA de la misma
titulación. Una que saliera con confianza alta no serviría para enseñar la cascada.

## `--real`, Y POR QUÉ HIZO FALTA: la comprobación barata no podía ver el fallo que importaba

La primera versión de este script sólo miraba la recuperación, y **con eso la sugerida estrella
pasó limpia**: confianza ALTA, margen 0,1638, el fragmento correcto el primero. Corrida de verdad
por el túnel, la respuesta salió **bien y con las tres afirmaciones declaradas `conocimiento`**, o
sea `sin_verificar` por diseño — *cero* veredictos en pantalla. La tarjeta prometía *"cita literal
comprobada y paráfrasis verificada"* y el primer clic del lunes habría enseñado justo lo contrario.

Es la trampa de siempre con otra cara: **una comprobación que no puede ponerse roja por el motivo
que importa**. Medía la fase 3 cuando lo que la pantalla promete es la fase 4. `--real` gasta una
llamada por sugerida (~0,00015 EUR) y mira **lo que el alumno va a ver**: cuántas afirmaciones
salen, de qué tipo y con qué veredicto.

    python scripts/curar_sugeridas.py --real --url http://127.0.0.1:8010
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.recuperacion import (PESOS_FUSION, buscar_vectorial,  # noqa: E402
                                   confianza_de, recuperar)

#: Los MISMOS que usa `/consulta`: la confianza se mide sobre la lista vectorial cortada a los
#: fragmentos que entran en el contexto, no sobre el pool entero. Medirla con otro corte daria otro
#: nivel — y entonces esta comprobacion no estaria comprobando lo que corre.
FRAGMENTOS_EN_CONTEXTO = 6

SUGERIDAS = pathlib.Path(__file__).resolve().parents[1] / "web" / "sugeridas.json"
BASE = os.environ.get("DATABASE_URL",
                      "postgresql://veridica:veridica_local@127.0.0.1:5434/veridica")


#: Los tipos que la capa de verificación SÍ juzga. `conocimiento` y `andamiaje` no se verifican
#: **por diseño** —no dicen salir del temario—, así que una respuesta hecha sólo de ellos es
#: legítima y **no enseña nada de lo que la pantalla promete**.
VERIFICABLES = ("literal", "parafrasis", "calculo")


def una_consulta(url: str, token: str, s: dict) -> dict:
    """Una consulta REAL por HTTP, y se leen las afirmaciones con su veredicto."""
    import httpx
    cuerpo = {"texto": s["texto"], "asignatura_id": s["asignatura_id"],
              "titulacion": s["titulacion"], "modo": s["modo"]}
    cabeceras = {"X-Veridica-Token": token} if token else {}
    prosa, afirmaciones, nombre = "", [], None
    with httpx.stream("POST", f"{url}/consulta", json=cuerpo, headers=cabeceras,
                      timeout=120.0) as r:
        for linea in r.iter_lines():
            if linea.startswith("event: "):
                nombre = linea[7:]
            elif linea.startswith("data: "):
                d = json.loads(linea[6:])
                if nombre == "token":
                    prosa += d["t"]
                elif nombre == "afirmaciones":
                    afirmaciones = d.get("afirmaciones") or []
    return {"prosa": prosa, "afirmaciones": afirmaciones}


def comprobar_de_verdad(url: str) -> int:
    """LO QUE EL ALUMNO VA A VER, que es lo que la tarjeta promete y no lo que la fase 3 encuentra."""
    token = os.environ.get("VERIDICA_TOKEN", "")
    fallos = 0
    for s in json.loads(SUGERIDAS.read_text(encoding="utf-8")):
        print("=" * 100)
        print(f"[{s['forma']}] {s['texto']}")
        print(f"   la tarjeta promete: {s['ensena']}")
        r = una_consulta(url, token, s)
        print(f"   prosa: {r['prosa'].strip()[:200]}")
        tipos = {}
        for a in r["afirmaciones"]:
            tipos[a["tipo"]] = tipos.get(a["tipo"], 0) + 1
            print(f"      {a['tipo']:<13} {str(a['veredicto']):<14} {str(a['texto'])[:62]}")
        verificables = sum(n for t, n in tipos.items() if t in VERIFICABLES)
        print(f"   -> {len(r['afirmaciones'])} afirmaciones, {verificables} de tipo verificable"
              f" {tipos}")
        # La de `corregir` no promete veredictos: promete que DUDA del resultado. Y la de fuera de
        # temario promete procedencia. Cada una se juzga por lo que su tarjeta dice.
        if s["forma"] in ("oro", "premisa_falsa"):
            ok = verificables >= 1
            print(f"   {'OK ' if ok else 'MAL'}  su tarjeta promete verificacion: hace falta al "
                  f"menos UNA afirmacion de tipo verificable")
        else:
            ok = bool(r["prosa"].strip())
            print(f"   {'OK ' if ok else 'MAL'}  hace falta que llegue prosa al alumno")
        fallos += not ok
    print("=" * 100)
    print(f"sugeridas que no ensenan lo que su tarjeta promete: {fallos}")
    return 1 if fallos else 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if "--real" in sys.argv:
        url = "http://127.0.0.1:8010"
        if "--url" in sys.argv:
            url = sys.argv[sys.argv.index("--url") + 1]
        return comprobar_de_verdad(url)
    from app.core.embebedor import Embebedor
    embebedor = Embebedor()
    sugeridas = json.loads(SUGERIDAS.read_text(encoding="utf-8"))
    fallos = 0

    for s in sugeridas:
        print("=" * 100)
        print(f"[{s['forma']}] {s['texto']}")
        print(f"   asignatura {s['asignatura_id']} · modo {s['modo']} · espera: {s['espera']}")
        vector = embebedor.embeber(s["texto"])
        fragmentos = recuperar(BASE, s["asignatura_id"], s["texto"], vector=vector,
                               pesos=PESOS_FUSION)
        nivel, detalle = confianza_de(
            buscar_vectorial(BASE, s["asignatura_id"], vector, k=FRAGMENTOS_EN_CONTEXTO))
        print(f"   -> {len(fragmentos)} fragmentos | confianza {nivel.upper()}"
              f" (top1 {detalle.get('top1')}, margen {detalle.get('margen_top1_top6')})")
        for f in fragmentos[:3]:
            print(f"      F{f.fragmento_id} · {(f.unidad or 'sin unidad')[:38]}"
                  f" · {f.texto[:74].strip()}")

        if s["espera"] == "confianza_baja_y_cascada":
            ok = nivel == "baja"
            print(f"   {'OK ' if ok else 'MAL'}  se espera confianza BAJA en su asignatura"
                  f" (para que se vea la cascada), y sale {nivel.upper()}")
        else:
            ok = bool(fragmentos) and nivel != "baja"
            print(f"   {'OK ' if ok else 'MAL'}  se espera que la recuperacion la encuentre"
                  f" con confianza media o alta")
        fallos += not ok

    print("=" * 100)
    print(f"sugeridas que NO cumplen lo que se espera de ellas: {fallos} de {len(sugeridas)}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
