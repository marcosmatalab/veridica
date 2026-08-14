# ADR 0020: el umbral NLI (0,60) y el suelo de cobertura (0,30) salen del plano, con el desempate pre-escrito

- **Fecha:** 14 de agosto de 2026
- **Encargo:** 4.6
- **Estado:** aceptada
- **Evidencia:** [`docs/evidencia/2026-08-14-calibracion-4.6.md`](../evidencia/2026-08-14-calibracion-4.6.md), corrida **32** de `corridas_eval`

## Contexto

El 0,80 del NLI y el 0,20 del suelo estaban **declarados sin calibrar** desde su nacimiento. Los
controles se derivan sin etiquetado humano: **189 positivos** (afirmaciones `literal` que pasan el
4.2: *entailed* por su cita, por construcción) y **189 negativos** (la misma afirmación contra otro
fragmento de su asignatura, excluyendo el mismo documento —el solape de 64 tokens fabrica
casi-duplicados— y los **858 casi-duplicados que el 1.8 ya midió**; emparejado determinista). UNA
corrida por la tubería de servicio, guardando cobertura y puntuación; el plano (suelo × umbral) se
calcula después sin re-llamar.

## Decisión

**Suelo 0,30 y umbral 0,60**, el punto que el desempate **pre-escrito** eligió: cero negativos
aprobados manda (la asimetría del 4.2: el falso positivo es el caro); entre los factibles, máximos
positivos verificados; empate → umbral más bajo, luego suelo más bajo. El punto inicial (0,20/0,80)
**aprobaba un negativo** y verificaba 25 positivos contra 34.

Los positivos perdidos del punto elegido, **declarados**: 18 de 56 en el tramo de umbral (entail
por debajo de 0,60 o etiqueta no-entail sobre cita literal: falso negativo del modelo, medido).

## Trade-off

- **Se gana**: el falso positivo caro queda en cero sobre los controles, con 9 positivos
  verificados más que la configuración inicial.
- **Se paga**: 18 positivos de 56 siguen sin verificarse (van a `reintento`/poda del 4.5, no a
  mentira), y el n del tramo de umbral es **56**, no 189 — pequeño y declarado.
- **El límite que la calibración destapó y que NO es del umbral: 133 de 189 positivos (70 %)
  fallan por SELECCIÓN** — la frase elegida no contiene la cita (citas que cruzan frases, o el
  selector eligiendo otra). Separarlos fue corrección de método del propietario: sin ella, el
  barrido habría movido el umbral para compensar un problema de selección. La selección multi-frase
  o consciente de la cita queda **declarada y no construida**; es la palanca gorda, no el umbral.

## Consecuencia que hay que vigilar

El plano acota con controles **por construcción** (cita literal / fragmento ajeno); el caso difícil
—la paráfrasis dudosa del medio— sigue sin etiqueta, así que 0,60 es un umbral que **ningún control
contradice**, no uno óptimo sobre el medio. Si aparece un conjunto etiquetado del medio, se rebarre
contra la fórmula del desempate, no contra esta cifra.
