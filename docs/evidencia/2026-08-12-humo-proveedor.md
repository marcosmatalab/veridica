# Evidencia: humo real del proveedor de inferencia

- **Fecha:** 2026-08-12
- **Encargo:** 2.2
- **Commit:** `cf026ad`
- **Modelo:** `mistral-small-3.2-24b-instruct-2506` | temperatura `0.0` | seed `20260812` |
  `max_tokens` `900` | `response_format` en modo esquema (`json_schema`)

## Las llamadas (reales, pagadas)

| # | TTFT proveedor (ms) | TTFT prosa (ms) | total (ms) | tokens entrada | tokens salida | coste (EUR) | fin |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 354 | 1507 | 2139 | 113 | 274 | 0.000113 | stop |
| 2 | 142 | 1466 | 2088 | 113 | 274 | 0.000113 | stop |
| 3 | 151 | 1257 | 2357 | 113 | 279 | 0.000115 | stop |

**Coste total de esta corrida: 0.000340 EUR.** Se anota aunque sean céntimos: la contabilidad
del 2.6 se construye sumando líneas como esta, y una que falte no se reconstruye después.

**Los dos TTFT no son el mismo número y por eso están los dos.** El del proveedor es el primer token
del JSON, que es `{`. El de la prosa es el primer carácter de `respuesta_redactada` que sale por el
evento `token`, o sea lo que ve el alumno. La diferencia entre los dos es lo que tarda el modelo en
escribir `modo` y `afirmaciones`, que en el contrato van antes de la redacción (ADR 0009).

## Determinismo con temperatura 0 y seed fijo

3 llamadas idénticas, comparadas byte a byte: **distintas**.

**Aplica la regla del 7.1**: temperatura 0 no basta aquí, así que toda medida de calidad va con N=3 repeticiones y se reporta la dispersión. Saberlo hoy evita medir ruido en la fase 7 creyendo que se mide el sistema.

## Hallazgos

Ninguno.

## Cómo se reproduce

```bash
python scripts/humo_proveedor.py --repeticiones 3 --evidencia docs/evidencia/2026-08-12-humo-proveedor.md
```

La clave sale de `INFERENCIA_API_KEY` (del `.env` en local, del secret del repositorio en CI) y no
aparece en este documento ni en la salida del script.
