#!/usr/bin/env python3
"""Cuenta los `calculo` reales cuyos operandos NO están en su fuente (14 de agosto de 2026).

    DATABASE_URL=... python scripts/medir_operandos.py

EL RECÁLCULO COMPRUEBA LA OPERACIÓN, NO LOS OPERANDOS: un operando inventado con aritmética
correcta sale `verificada`, y ese es el modo de fallo más probable de un modelo de lenguaje.
Atar los operandos al temario es una verificación nueva, declarada y no construida; este script
es el CONTADOR que decide si se justifica, corrido hacia atrás sobre lo que ya hay en la base.

DENOMINADOR DECLARADO: todas las afirmaciones `tipo='calculo'` con `expresion` en su detalle,
estén como estén de verificadas. Las que no tienen expresión se cuentan aparte, no se omiten en
silencio. FUENTES admitidas por afirmación: el texto del fragmento que cita (si cita), la
pregunta del alumno, y los resultados (afirmado y recalculado) de las afirmaciones `calculo`
anteriores de la misma respuesta — la misma regla que el contador vivo de `consulta.py`, y es a
propósito: el retroactivo y el vivo tienen que contar lo mismo o sus números no se pueden juntar.

Los casos se imprimen UNO A UNO además del total: un agregado disuelve la estructura que señala
la causa, y aquí la pregunta es precisamente cuáles cifras se inventa.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                      # noqa: E402

from app.core.verificador_calculo import operandos_sin_fuente       # noqa: E402

CONSULTA = """
SELECT a.id, a.respuesta_id, a.fragmento_id,
       a.detalle->>'expresion'                            AS expresion,
       a.detalle->'verificacion'->>'resultado_afirmado'   AS resultado,
       a.detalle->'verificacion'->>'recalculado'          AS recalculado,
       a.detalle->'verificacion'->>'veredicto'            AS veredicto,
       f.texto                                            AS fragmento,
       c.texto                                            AS pregunta
  FROM afirmaciones a
  JOIN respuestas r ON r.id = a.respuesta_id
  JOIN consultas  c ON c.id = r.consulta_id
  LEFT JOIN fragmentos f ON f.id = a.fragmento_id
 WHERE a.tipo = 'calculo'
 ORDER BY a.respuesta_id, a.id
"""


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute(CONSULTA)
        filas = cur.fetchall()

    sin_expresion, con_hallazgo, ocurrencias, examinadas = 0, 0, 0, 0
    previos = collections.defaultdict(list)      # respuesta_id -> resultados anteriores
    for (_id, respuesta, _frag, expresion, resultado, recalculado, veredicto,
         fragmento, pregunta) in filas:
        if not (expresion or "").strip():
            sin_expresion += 1
            continue
        examinadas += 1
        faltan = operandos_sin_fuente(expresion, [fragmento or "", pregunta or "",
                                                  *previos[respuesta]])
        previos[respuesta] += [str(resultado or ""), str(recalculado or "")]
        if faltan:
            con_hallazgo += 1
            ocurrencias += len(faltan)
            print(f"resp {respuesta} afirmacion {_id} [{veredicto}] "
                  f"{'sin fragmento citado | ' if not fragmento else ''}"
                  f"expresion: {expresion[:60]:60s} SIN FUENTE: {', '.join(faltan)}")

    print(f"\ndenominador: {examinadas} calculo con expresion "
          f"(+{sin_expresion} sin expresion, contados aparte)")
    if examinadas:
        print(f"hallazgos: {con_hallazgo} afirmaciones con algun operando sin fuente "
              f"({100 * con_hallazgo / examinadas:.1f} %)")
    print(f"ocurrencias: {ocurrencias} operandos sin fuente en total "
          f"(hallazgos y ocurrencias, por separado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
