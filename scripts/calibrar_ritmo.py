#!/usr/bin/env python3
"""Calibración del vigilante de ritmo (4.6, umbral #5) sobre el PEOR momento de cada consulta.

    DATABASE_URL=... python scripts/calibrar_ritmo.py --corrida <id>

## LA PREGUNTA QUE EL UMBRAL HACE, Y EL CONTADOR QUE HAY QUE MIRAR

El vigilante corta cuando el ritmo baja de `RITMO_MINIMO` tokens/s **en una ventana de 2 s**. O sea
que pregunta *"¿bajó alguna vez de aquí?"*, y hasta el 2.5 la traza guardaba `tokens_por_segundo`
—el ritmo de la **última** ventana—, que contesta *"¿a qué ritmo iba al final?"*. Dos preguntas
distintas en el mismo número: por eso el 4.6 no pudo calibrarlo, y por eso desde el 2.5 se persiste
`minimo_observado`.

## EL CRITERIO, ESCRITO ANTES DE MIRAR LA TABLA

La asimetría de este umbral **no** ha cambiado (a diferencia del portero, ADR 0021), así que se
hereda con su motivo:

| error | qué cuesta |
|---|---|
| **falso positivo** — cortar una consulta sana | **el caro**: se tira una respuesta que iba a llegar, y el reintento paga otro prefill entero |
| **falso negativo** — no cortar una consulta hundida | el plazo de 8 s la corta igual, más tarde: se pierde tiempo, no la respuesta |

**CORRECCIÓN, ESCRITA AL LEER EL RESULTADO Y NO ANTES, porque es un error de este documento y no
del dato:** esta tabla **contradice la asimetría MEDIDA que `app/core/ritmo.py` ya tenía escrita** —
un corte falso cuesta **~2 s** (se corta, se avisa y se vuelve a pedir) y un corte que no ocurre
cuesta **~60 s de pantalla congelada** delante del cliente, o sea **treinta veces más**—. O sea que
la casilla cara es la de abajo y no la de arriba, y este criterio se escribió sin leer el que ya
estaba justificado con números. Se deja escrito en vez de corregirlo en silencio: el desempate de
abajo se aplicó tal cual, y **la decisión final está en el módulo**, con la banda vacía como motivo.

Con esa corrección, la regla que sigue —y que se aplicó— era:

1. El umbral tiene que quedar **por debajo del peor momento de TODA consulta sana observada**, con
   margen. Una sola consulta sana cortada ya es un falso positivo.
2. Con esa condición, se elige el **más alto** de los candidatos —cortar antes ahorra tiempo cuando
   la avería es real—, con un margen de seguridad del **30 %** por debajo del mínimo observado,
   declarado aquí y no ajustado después.
3. **Si el n de consultas sanas es pequeño, el desenlace legítimo es SIGUE SIN CALIBRAR.** Un
   umbral movido con cuatro consultas es un número con aspecto de medida.

`n` mínimo para mover el umbral, fijado antes: **30 consultas sanas**. Por debajo, se declara.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                        # noqa: E402

from app.core.ritmo import GRACIA, RITMO_MINIMO, VENTANA_S            # noqa: E402

MARGEN = 0.30
N_MINIMO = 30
CANDIDATOS = [10, 15, 20, 25, 30, 35, 40, 45, 50]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corrida", type=int, required=True)
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
    ritmos = metricas.get("ritmos") or []

    # SANA = la que NO se abstuvo. Una consulta cortada por el propio vigilante o por el plazo no
    # sirve para decir "aqui llega una consulta sana", que es la pregunta del umbral.
    sanas = [r for r in ritmos if not r.get("abstencion")]
    print(f"consultas con peor momento medido: {len(ritmos)} | sanas: {len(sanas)}")
    if not sanas:
        print("sin consultas sanas: no hay nada que calibrar")
        return 1

    peores = sorted(r["minimo_observado"] for r in sanas)
    n = len(peores)
    print("peor momento de cada consulta sana (tokens/s):")
    print(f"  min {peores[0]} | p10 {peores[max(0, n//10 - 1)]} | p25 {peores[max(0, n//4 - 1)]} | "
          f"mediana {peores[n//2]} | max {peores[-1]}")
    print(f"\numbral actual: {RITMO_MINIMO} tok/s en ventana de {VENTANA_S} s, gracia {GRACIA} tokens")
    for u in CANDIDATOS:
        cortadas = sum(1 for x in peores if x < u)
        print(f"  con umbral {u:>3}: cortaria {cortadas} de {n} consultas SANAS"
              + ("   <- falso positivo" if cortadas else ""))

    if n < N_MINIMO:
        print(f"\nDESENLACE: SIGUE SIN CALIBRAR. n={n} consultas sanas, por debajo del minimo de "
              f"{N_MINIMO} fijado antes de mirar. Se declara en vez de mover el umbral con una "
              f"muestra que no lo sostiene.")
        return 0

    techo = peores[0] * (1 - MARGEN)
    admisibles = [u for u in CANDIDATOS if u <= techo]
    print(f"\npeor momento MINIMO observado: {peores[0]} tok/s; con margen del {int(MARGEN*100)} % "
          f"el umbral no puede pasar de {techo:.1f}")
    if not admisibles:
        print("DESENLACE: ningun candidato cabe bajo el margen. El umbral actual ya corta sano o "
              "esta al borde: se declara y NO se sube.")
        return 0
    elegido = max(admisibles)
    print(f"ELEGIDO (desempate pre-escrito): {elegido} tok/s"
          + ("  (= el actual, y eso tambien es un resultado)" if elegido == RITMO_MINIMO else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
