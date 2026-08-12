# Evidencia: humo real del proveedor de inferencia

- **Fecha:** 2026-08-12
- **Encargo:** 2.2
- **Commit:** `9bb5f87`
- **Modelo:** `mistral-small-3.2-24b-instruct-2506` | temperatura `0.0` | seed `20260812` |
  `max_tokens` `900` | `response_format` en modo esquema (`json_schema`)

## Las llamadas (reales, pagadas)

| # | TTFT proveedor (ms) | TTFT prosa (ms) | total (ms) | tokens entrada | tokens salida | coste (EUR) | fin |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 212 | 1312 | 1967 | 113 | 274 | 0.000113 | stop |
| 2 | 199 | 1237 | 1931 | 113 | 280 | 0.000115 | stop |
| 3 | 173 | 1193 | 1860 | 113 | 280 | 0.000115 | stop |

**Coste total de esta corrida: 0.000343 EUR.** Se anota aunque sean céntimos: la contabilidad
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
| 5. Texto de las afirmaciones | 93.7 % en común |
| 6. Redacción | 71.8 % de caracteres en común |

Las tres primeras dimensiones son la **forma del conjunto**, que es lo que lee la ablación. Las dos
últimas son **redacción**. Se separan porque dos corridas pueden traer dos afirmaciones de tipo
`conocimiento` cada una y estar afirmando cosas distintas: sin la dimensión 5, eso pasaría por
estabilidad.

Y como los bytes difieren, dónde empiezan a hacerlo (posición 107):

```
A: ... 1,
      "texto": "Una clave primaria es un campo o conjunto de campos que iden...
B: ... 1,
      "texto": "Una clave primaria en una base de datos relacional es un cam...
```


**Lo que estos números deciden, que es lo que importa.** Que varíe la redacción y que varíe el
conjunto de afirmaciones no son la misma cosa, y solo lo segundo compromete el **7.3**: la ablación
compara la fila con verificación contra la fila sin ella, y si el conjunto de afirmaciones bailara
entre corridas idénticas, esa diferencia —el argumento central del proyecto— podría quedar por
debajo del ruido de medida.

**La forma del conjunto es estable —mismo número y mismos tipos— pero el texto de las afirmaciones varía (93.7 % en común).** Eso no rompe la ablación por sí solo, porque la fila con verificación y la fila sin ella se comparan por veredictos; pero sí obliga a que cualquier métrica que mire el CONTENIDO de una afirmación (fidelidad literal, NLI) se reporte con su dispersión y no como un número único.

**Aviso sobre la dimensión 4:** en el 2.2 no hay recuperación, así que `fragmento_id` es nulo en
todas las afirmaciones y su estabilidad aquí no significa nada. Esta medida hay que repetirla en la
fase 3, con recuperación de verdad, que es cuando citar o no citar el mismo fragmento empieza a ser
una diferencia real.

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
