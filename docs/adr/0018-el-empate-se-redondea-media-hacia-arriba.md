# ADR 0018: el empate de redondeo se resuelve media hacia arriba, con una sola convención

- **Fecha:** 14 de agosto de 2026
- **Encargo:** 4.4 (verificador de cálculo), corrigiendo una decisión del 13 de agosto
- **Estado:** aceptada
- **Evidencia:** [`docs/evidencia/2026-08-14-corregir-desde-resultado.md`](../evidencia/2026-08-14-corregir-desde-resultado.md)

## Contexto

`comparar` aceptaba **las dos convenciones de redondeo** en el empate exacto: media hacia arriba
(`0,125 → 0,13`, la del instituto) y al par (`0,125 → 0,12`, la de IEEE 754). El argumento era no
castigar una convención legítima, y el caso que lo sostenía era `1/8`.

Lo que ese argumento no vio: **aceptar las dos convenciones es aceptar una banda más ancha que
cualquiera de ellas.** El caso que lo destapó, encontrado escribiendo un test el 14 de agosto:
`50 * 1,21 = 60` salía **verificada**, porque 60,5 redondeado al par a cero decimales es 60. Un
alumno que calcula el IVA de 50 euros y escribe 60 en vez de 60,5 (o 61) no está usando el redondeo
al par: está perdiendo medio euro, y el verificador se lo daba por bueno.

## Decisión

**Una sola convención: media hacia arriba (`ROUND_HALF_UP`).** Es la que usa un alumno con lápiz —el
usuario de este sistema— y es la **estricta** de las dos en el caso que importa: aquí el falso
positivo es el caro, porque una cuenta mal dada por verificada es exactamente la mentira que el
proyecto existe para impedir. Un falso negativo (podar un `0,12` legítimo) lo ve el alumno y se
puede discutir; un falso positivo no lo ve nadie.

## Trade-off

- **Se paga**: quien redondee al par (`1/8 → 0,12`) sale `podada` siendo una convención correcta en
  otros contextos. Se acepta con los ojos abiertos: en un temario de FP el redondeo que se enseña y
  se espera es media hacia arriba, y el caso solo existe en el empate exacto.
- **Se gana**: la banda de tolerancia vuelve a ser **una** convención y no la unión de dos, y
  `50 * 1,21 = 60` se poda, que es el veredicto verdadero.
- **Lo que se descarta**: mantener las dos y documentar el agujero. Se descartó porque el agujero no
  es teórico —lo produjo una cuenta de IVA de temario— y porque la asimetría de costes aquí es
  clara: el verificador prefiere equivocarse pidiendo precisión a equivocarse regalándola.

## Test anclado

`test_el_empate_se_redondea_MEDIA_HACIA_ARRIBA_y_solo_asi` ancla el caso exacto (`50 * 1,21` con
`60`, `61` y `60,5`) y el precio declarado (`1/8` con `0,12` podada).

## Consecuencia que hay que vigilar

**Dos filas persistidas quedan con el veredicto de la regla vieja, y se declaran en vez de
reescribirse:** `afirmaciones` ids **844** y **912** (`50 + (50 * 21 / 100)` afirmado como `60`)
llevan `veredicto='verificada'`, que con esta regla sería `podada`. Re-verificada la base entera
tras el cambio: son las únicas dos de 74. No se tocan —el veredicto es el registro de lo que el
sistema dijo entonces, y reescribir la historia es peor que declararla—, pero **cualquier métrica
del 4.6 calculada sobre veredictos históricos hereda dos falsas verificadas**, y tiene que saberlo.
Es la misma familia que `cache_hit`: un dato persistido se lee como una medida. (Hallazgo de la
pasada adversarial del 14/08.)
