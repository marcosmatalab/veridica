# Auditoría: qué degradaciones declaradas tienen código detrás — 13 de agosto de 2026

Sale de un error mío. Afirmé **dos veces como hecho** que el contenedor sin torch servía léxica y
glosario, y no era cierto: `embebedor is None` devolvía **cero fragmentos** y el sistema respondía de
memoria. Razoné desde el diseño en vez de leer el código, y la frase, al estar escrita, **blindaba el
hueco**: quien la leyera dejaba de mirar.

La lección va a las reglas: **una degradación declarada que nadie implementó es más peligrosa que una
no declarada, porque el documento crea una confianza que el código no ha ganado.** Y la comprobación
es un `grep`, así que aquí está hecha sobre el 8.1 y la Parte V.

## El recuento

| Declarado en la guía | ¿Código en la ruta? | Dónde |
|---|---|---|
| Sin reordenador → orden de la fusión, anunciado (ADR 0015) | **sí** | `reordenar_o_rendirse` + etapa `sin_reordenar` |
| Reordenador **saturado** ≠ averiado (tercer motivo) | **sí** | discriminador por espera en cola |
| Vigilante de ritmo sobre el flujo | **sí** | `ritmo.py`, enchufado en `_flujo` |
| Presupuesto como plazo real | **sí** | `PlazoAgotado` |
| Contrato roto → un reintento → abstención | **sí** | `_flujo` |
| Cobertura frase a frase | **sí** | `PorteroDeFrases` |
| Cita literal comprobada carácter a carácter | **sí** | 4.2, en el SSE |
| Cálculo recalculado | **sí** | 4.4, en el SSE |
| **Paráfrasis verificada por un NLI distinto del generador** | **NO** | `VerificadorNLI` existe, **con tests, y no lo llama nadie** |
| **Sin embebedor → léxica y glosario** | **NO → sí hoy** | escrito en `c30ca94`, seis meses después de declararlo |
| **Caché semántica que absorbe la cabeza de la distribución** | **NO** | no hay módulo; `cache_hit` siempre `false` |
| **Escalonado al modelo grande** (configuración candidata del 7.2) | **NO** | el parámetro `grande=` existe, la **decisión** no; `escalado` siempre `false` |
| Circuit breaker del proveedor | **no, y declarado** como encargo 8.2 | — |
| torch CPU en la imagen | **no, y declarado** con su coste (~2,5 GB) | — |

**Cuatro sin código**, y las dos primeras son las graves.

### La más grave: el NLI construido y no enchufado

El README abre con *"cita literal comprobada carácter a carácter, **paráfrasis verificada contra el
fragmento fuente**, cálculo recalculado"*. De esas tres, **la del medio no corre**:
`app/core/verificador_nli.py` está completo y probado desde el 4.3, y **ninguna línea de
`app/api/consulta.py` lo invoca**. Toda afirmación `parafrasis` —y toda `literal` degradada— sale
`sin_verificar`.

No es un descuido de una tarde: es que construir un componente y **enchufarlo** son dos trabajos, y
solo el primero deja rastro visible (un módulo, unos tests en verde). El segundo no se echa de menos
mirando el repo.

Corregido de momento el **mensaje**, que decía algo peor —*"el NLI del 4.3 (hoy no existe)"*—: existe,
y lo que pasa es otra cosa. Enchufarlo tiene coste (mDeBERTa son 279 M de parámetros en el proceso de
la API, y **el contenedor no lleva torch**, igual que con el embebedor), así que es una decisión con
dueño y no una línea que se añade de paso.

### Y peor que un documento es una COLUMNA

`respuestas.cache_hit` y `respuestas.escalado` existen en la base desde el 2.1 y valen **siempre
`false`**, porque nada las escribe. Un documento que promete algo se puede leer con escepticismo; **un
`false` persistido se lee como una medida**, y cualquier consulta que los agregue dirá "0 % de aciertos
de caché" en vez de "aquí no hay caché".

## Comprobación que queda

`grep` por cada respaldo declarado, buscando la función que lo implementa y el test que lo cubre. Es
barata y hay que hacerla **a propósito**: ninguna de las cuatro se cae sola, porque todas fallan
callando.
