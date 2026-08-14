#!/usr/bin/env python3
"""Reparto de veredictos por tipo de afirmación (encargo 4.4, al enchufar el NLI).

    python scripts/medir_veredictos.py

**LA PREGUNTA QUE CONTESTA:** ¿cuántas afirmaciones sale de verdad verificadas, y cuántas siguen
`sin_verificar`? Es el número que dice si la capa de verificación existe o solo está construida.

El denominador va escrito y por tipo, porque cada tipo tiene su instrumento y mezclarlos esconde
justo lo que interesa: una `parafrasis` `sin_verificar` significa "el NLI no la miró" y una
`conocimiento` `sin_verificar` significa "no se verifica por diseño", que no es lo mismo.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                          # noqa: E402

URL = os.environ.get("DATABASE_URL") or "postgresql://veridica:veridica_local@127.0.0.1:5434/veridica"
DESDE = sys.argv[1] if len(sys.argv) > 1 else "30 minutes"


def main() -> int:
    with psycopg.connect(URL, connect_timeout=5) as con, con.cursor() as cur:
        cur.execute("SET statement_timeout = '15s'")
        cur.execute("""
            SELECT a.tipo, a.veredicto, count(*)
              FROM afirmaciones a JOIN respuestas r ON r.id = a.respuesta_id
             WHERE r.creado_en > now() - %s::interval
             GROUP BY 1, 2 ORDER BY 1, 3 DESC
        """, (DESDE,))
        filas = cur.fetchall()
    if not filas:
        print(f"no hay afirmaciones en las ultimas {DESDE}")
        return 1

    por_tipo = {}
    for tipo, veredicto, n in filas:
        por_tipo.setdefault(tipo, {})[veredicto] = n
    print(f"afirmaciones de las ultimas {DESDE}\n")
    print(f"{'tipo':14} {'n':>4}  reparto de veredictos")
    print("-" * 78)
    total = sin_ver = 0
    for tipo, reparto in sorted(por_tipo.items()):
        n = sum(reparto.values())
        total += n
        sin_ver += reparto.get("sin_verificar", 0)
        detalle = "  ".join(f"{v}={c}" for v, c in sorted(reparto.items(), key=lambda x: -x[1]))
        print(f"{tipo:14} {n:>4}  {detalle}")
    print("-" * 78)
    factuales = {t: r for t, r in por_tipo.items() if t != "andamiaje"}
    nf = sum(sum(r.values()) for r in factuales.values())
    sinf = sum(r.get("sin_verificar", 0) for r in factuales.values())
    print(f"factuales (sin andamiaje): {nf}, de las cuales {sinf} sin_verificar "
          f"({100 * sinf / nf if nf else 0:.1f} %)")
    print(f"total con andamiaje: {total}, sin_verificar {sin_ver}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
