# Evidencia: humo real del proveedor de inferencia

- **Fecha:** 2026-08-12
- **Encargo:** 2.2
- **Commit:** `a324d0d`
- **Modelo:** `mistral-small-3.2-24b-instruct-2506` | temperatura `0.0` | seed `20260812` |
  `max_tokens` `900` | `response_format` en modo esquema (`json_schema`)

## Las llamadas (reales, pagadas)

| # | TTFT proveedor (ms) | TTFT prosa (ms) | total (ms) | tokens entrada | tokens salida | coste (EUR) | fin |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 334 | 1638 | 2428 | 113 | 274 | 0.000113 | stop |
| 2 | 162 | 1465 | 2372 | 113 | 279 | 0.000115 | stop |
| 3 | 220 | 1491 | 2329 | 113 | 280 | 0.000115 | stop |

**Coste total de esta corrida: 0.000342 EUR.** Se anota aunque sean céntimos: la contabilidad
del 2.6 se construye sumando líneas como esta, y una que falte no se reconstruye después.

**Los dos TTFT no son el mismo número y por eso están los dos.** El del proveedor es el primer token
del JSON, que es `{`. El de la prosa es el primer carácter de `respuesta_redactada` que sale por el
evento `token`, o sea lo que ve el alumno. La diferencia entre los dos es lo que tarda el modelo en
escribir `modo` y `afirmaciones`, que en el contrato van antes de la redacción (ADR 0009).

## Determinismo con temperatura 0 y seed fijo: cuánto varía, y en qué

3 llamadas con la MISMA entrada, la MISMA semilla y
temperatura 0, comparadas por dimensiones separadas, porque no todas cuestan lo mismo:

| Dimensión | Resultado |
|---|---|
| 1. Bytes de la respuesta | **distintos** |
| 2. Número de afirmaciones | [2] — estable |
| 3. Tipos de las afirmaciones | estables: [['conocimiento', 'conocimiento']] |
| 4. `fragmento_id` citados | estables: [[]] |
| 5. Texto de las afirmaciones | 100.0 % en común |
| 6. Redacción | 100.0 % de caracteres en común |

Las tres primeras dimensiones son la **forma del conjunto**, que es lo que lee la ablación. Las dos
últimas son **redacción**. Se separan porque dos corridas pueden traer dos afirmaciones de tipo
`conocimiento` cada una y estar afirmando cosas distintas: sin la dimensión 5, eso pasaría por
estabilidad.

Y como los bytes difieren, dónde empiezan a hacerlo (posición 868):

```
A: ..."
  ,
  "siguiente_paso": {
    "ref": "siguiente"
  ,
    "texto": "Siguiente"
...
B: ..."
  ,
  "siguiente_paso": {
    "ref": "respuesta"
  ,
    "texto": "¿Hay algo m...
```


**Lo que estos números deciden, que es lo que importa.** Que varíe la redacción y que varíe el
conjunto de afirmaciones no son la misma cosa, y solo lo segundo compromete el **7.3**: la ablación
compara la fila con verificación contra la fila sin ella, y si el conjunto de afirmaciones bailara
entre corridas idénticas, esa diferencia —el argumento central del proyecto— podría quedar por
debajo del ruido de medida.

**El conjunto de afirmaciones es estable: mismo número, mismos tipos y prácticamente el mismo contenido.** Lo que varía es la redacción palabra a palabra, en el sitio que enseña el desvío de arriba. La ablación del 7.3 sigue siendo legible con N=3, porque lo que compara son afirmaciones y veredictos, no la literalidad del texto. **Con la salvedad de arriba: hoy la forma no se está poniendo a prueba**, porque el modelo no tiene alternativa que elegir. Que aguante aquí no predice que aguante con recuperación.

**AVISO: esta medida está tomada en un caso degenerado, y dos de las tres dimensiones de forma no
están medidas de verdad.** Sin recuperación no existen `literal` ni `parafrasis`, así que el tipo
`conocimiento` no es una elección del modelo: es la única casilla que le deja la gramática. Y
`fragmento_id` es nulo en todas. Bajo recuperación, elegir entre citar literalmente y parafrasear,
y elegir **cuál** de los fragmentos recuperados se cita, es una decisión combinatoria que puede
variar en cada corrida, y de ella salen directamente las columnas de veredictos del 7.3 —una
`literal` la verifica una comparación de cadenas y una `parafrasis` un NLI con umbral—. **La
re-medición de la fase 3 cubre las tres dimensiones juntas: número, mezcla de tipos y
`fragmento_id`.**

**Aplica la regla del 7.1**: temperatura 0 con semilla es una *petición* de determinismo, no
determinismo —en un servidor con lotes variables la aritmética en coma flotante cambia con el
tamaño del lote—, así que toda medida de calidad va con N=3 repeticiones y se reporta la
dispersión. Saberlo hoy evita medir ruido en la fase 7 creyendo que se mide el sistema.

## Hallazgos

Ninguno.

## Cómo se reproduce

```bash
python scripts/humo_proveedor.py --repeticiones 3 --evidencia docs/evidencia/2026-08-12-humo-proveedor.md
```

La clave sale de `INFERENCIA_API_KEY` (del `.env` en local, del secret del repositorio en CI) y no
aparece en este documento ni en la salida del script.
