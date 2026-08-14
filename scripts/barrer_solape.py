#!/usr/bin/env python3
"""Barrido del umbral del portero (4.6, umbral #3) sobre los solapes recogidos.

    DATABASE_URL=... python scripts/barrer_solape.py --corrida <id>

## EL CRITERIO, ESCRITO ANTES DE MIRAR LA TABLA (y esa es su única utilidad)

**La asimetría está INVERTIDA desde el ADR 0021**, así que el desempate del 4.6 no se hereda: se
vuelve a derivar contra la pregunta nueva.

| error | qué cuesta AHORA |
|---|---|
| **falso positivo** — frase sin respaldo emitida SIN marca | **el caro**: contenido no declarado llegando al alumno con aspecto de respaldado |
| **falso negativo** — frase respaldada emitida CON marca | cosmético: una marca injusta; el alumno lee la frase igual |

**Regla de elección, en este orden y decidida ahora:**

1. **Manda no dejar pasar sin marca**, o sea maximizar el recall de las frases sin respaldo. Pero
   "sin respaldo" no tiene etiqueta humana en este conjunto, así que **no se puede medir
   directamente** y hay que decir cómo se aproxima en vez de fingir que se mide (ver abajo).
2. Entre los umbrales que **no disparan la marca en más del `TECHO_MARCADAS` de las frases**
   —porque marcar todo es no marcar nada—, gana el **más alto**: es el lado seguro de la asimetría
   nueva.
3. Empate → el umbral más bajo de los empatados, que es la configuración menos agresiva que
   consigue lo mismo.

**LO QUE ESTE BARRIDO NO PUEDE HACER, dicho antes de correrlo:** no hay conjunto etiquetado de
"frase respaldada / no respaldada" —haría falta leer a mano cada frase contra las afirmaciones de su
respuesta—, así que **esto NO mide precisión ni recall**. Mide la **tasa de marcado** en función del
umbral sobre prosa real, que es lo que decide si el mecanismo es usable, y deja el punto de
funcionamiento en el borde declarado. Cualquier cifra de precisión que saliera de aquí sería
inventada, y por eso no sale.

`TECHO_MARCADAS` se fija **antes** en 0,25: por encima de una frase marcada de cada cuatro, la marca
deja de distinguir y pasa a ser decoración. Es un juicio de producto, no una medida, y se declara
como tal.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                        # noqa: E402

from app.core.cobertura import SOLAPE_MINIMO                          # noqa: E402

#: Los candidatos. Se barre HACIA ARRIBA desde el valor actual, que es la direccion que el ADR 0021
#: obliga; se incluyen dos por debajo para que la tabla enseñe el otro lado y no solo el que gusta.
CANDIDATOS = [round(0.30 + 0.05 * i, 2) for i in range(13)]     # 0,30 .. 0,90

#: Juicio de PRODUCTO declarado antes de mirar: por encima de esto, la marca deja de distinguir.
TECHO_MARCADAS = 0.25


def celda(solapes: list, umbral: float) -> dict:
    """Qué haría el portero con este umbral sobre las frases ya medidas."""
    # LAS CORTAS NO CUENTAN: pasan POR DISEÑO y su solape es 1.0 por convencion, no por medida.
    # Meterlas dividiria el numerador y el denominador por lo mismo y haria bajar la tasa sin que
    # nada cambie -un contador contestando a otra pregunta-.
    juzgadas = [s for s in solapes if not s.get("corta")]
    marcadas = [s for s in juzgadas if s["solape"] < umbral]
    return {"juzgadas": len(juzgadas), "marcadas": len(marcadas),
            "tasa": round(len(marcadas) / len(juzgadas), 4) if juzgadas else None}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corrida", type=int, required=True,
                   help="id de corridas_eval con la recogida de solapes")
    a = p.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")

    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("SELECT metricas FROM corridas_eval WHERE id = %s", (a.corrida,))
        fila = cur.fetchone()
    if fila is None:
        print(f"no hay corrida {a.corrida}", file=sys.stderr)
        return 2
    metricas = fila[0] if isinstance(fila[0], dict) else json.loads(fila[0])
    solapes = metricas.get("solapes") or []
    if not solapes:
        print("la corrida no trae solapes", file=sys.stderr)
        return 2

    juzgadas = [s for s in solapes if not s.get("corta")]
    print(f"frases: {len(solapes)} | juzgadas por solape: {len(juzgadas)} | "
          f"pasaron por CORTAS: {len(solapes) - len(juzgadas)}")
    valores = sorted(s["solape"] for s in juzgadas)
    if valores:
        n = len(valores)
        print(f"solape: min {valores[0]} | p10 {valores[n//10]} | p25 {valores[n//4]} | "
              f"mediana {valores[n//2]} | p75 {valores[3*n//4]} | max {valores[-1]}")

    print(f"\numbral   marcadas/juzgadas   tasa   (techo declarado: {TECHO_MARCADAS})")
    plano = {}
    for u in CANDIDATOS:
        r = celda(solapes, u)
        plano[u] = r
        marca = "  <- actual" if abs(u - SOLAPE_MINIMO) < 1e-9 else ""
        aviso = "  DEMASIADAS" if r["tasa"] is not None and r["tasa"] > TECHO_MARCADAS else ""
        print(f"  {u:.2f}      {r['marcadas']:3}/{r['juzgadas']:<3}          "
              f"{r['tasa']}{marca}{aviso}")

    admisibles = {u: r for u, r in plano.items()
                  if r["tasa"] is not None and r["tasa"] <= TECHO_MARCADAS}
    if not admisibles:
        print("\nNINGUN umbral queda por debajo del techo: el criterio pre-escrito no elige, y eso "
              "se declara en vez de bajar el techo hasta que salga uno")
        return 1
    # El desempate PRE-ESCRITO: el mas alto que no pase del techo; empate -> el mas bajo de esos.
    elegido = max(admisibles)
    print(f"\nELEGIDO (desempate pre-escrito, direccion INVERTIDA por el ADR 0021): {elegido}")
    print(f"  {admisibles[elegido]}")
    print(f"  (actual {SOLAPE_MINIMO}: {plano.get(SOLAPE_MINIMO)})")
    print("\nLO QUE ESTE NUMERO NO DICE: no hay conjunto etiquetado de 'frase respaldada / no "
          "respaldada', asi que esto NO mide precision ni recall. Mide la tasa de marcado sobre "
          "prosa real y elige el borde declarado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
