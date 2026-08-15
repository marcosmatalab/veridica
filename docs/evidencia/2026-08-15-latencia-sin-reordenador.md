# Evidencia: la latencia de la configuración que corre, sin reordenador

**Fecha de la medida:** 15 de agosto de 2026 · **Población:** las **150 respuestas** que
`respuestas` guarda entre el **14/08 14:11 y el 15/08 02:12** · **Fuente:** `respuestas.total_ms` y
`respuestas.abstencion`, que escribe la propia API al cerrar cada respuesta.

**Configuración:** fusión 10:1:1, pool 30, **sin reordenador** ([ADR 0019](../adr/0019-el-reordenador-se-descarta-por-su-propio-criterio.md)),
NLI enchufado, `PRESUPUESTO_CONSULTA_MS = 8.000`, `OBJETIVO_CONSULTA_MS = 5.000`.

## Por qué existe este fichero

**El número estaba publicado en el README y en ningún sitio más.** Ni en ESTADO, ni en una evidencia,
ni con su denominador al lado — y es el número que corrige a mejor el suspenso más citado del
proyecto. La regla de este repo dice que un número sin su renglón (unidad, n, corrida, fichero de
evidencia) no se publica; éste llevaba horas publicado sin él. Esto es ese renglón.

## Lo primero: REPRODUCIR la cifra publicada

Antes de recomputar nada. Si la población elegida no devuelve el número viejo, se está midiendo otra
cosa y todo lo que venga después es ruido con formato de corrección.

| | Publicado en el README | Recomputado |
|---|---:|---:|
| n | 150 | **150** |
| p50 | 2.915 ms | **2.915 ms** |
| p95 | 7.733 ms | **7.733 ms** |
| Máximo | 8.031 ms | 8.030 ms |
| Pasan de 5 s | 18 · 12,0 % | **18 · 12,0 %** |
| Abstenciones | 10 · 6,7 % | **10 · 6,7 %** |

**Sale dígito a dígito** salvo el máximo, que difiere en **1 ms** por redondeo del flotante. El
número es sólido y lo que sigue se apoya en él sin sustituirlo.

> **Un detalle de método que hay que dejar escrito para que nadie lo "corrija" mañana:** el p50 de
> 2.915 sale de `percentile_cont` de Postgres, que **interpola** entre los dos valores centrales. Un
> percentil por rango más cercano —el que hace el corredor en Python— da **2.907** sobre exactamente
> los mismos datos. No es una discrepancia: son dos definiciones de mediana. El publicado es el
> interpolado.

## Las dos unidades, porque el titular alimenta una decisión

`contar()` sobre el texto de la pregunta: **71 casos distintos de 150 ocurrencias (×2,11)**.

| | Filas | **Casos distintos** |
|---|---:|---:|
| n | 150 | **71** |
| p50 | 2.907 ms | 2.973 ms |
| p95 | 7.761 ms | 7.117 ms |
| **Pasan del objetivo de 5 s** | **18 · 12,0 %** | **7 · 9,9 %** |
| Abstenciones | 10 · 6,7 % | 6 · 8,5 % |

*(Las cifras de la columna «Filas» son por rango más cercano, para que las dos columnas usen el mismo
método y sean comparables entre sí; por eso 2.907 y no 2.915.)*

**Deduplicar MEJORA el número** —de 12,0 % a 9,9 %—, que es la dirección contraria a la del titular
de las citas literales, donde deduplicar lo empeoraba siete puntos. El motivo es el mismo mecanismo
con el signo cambiado: allí se repetían las citas cortas y fáciles; aquí se repiten las preguntas
**lentas** (las cuatro más repetidas son las curadas y las congeladas, que se corrieron una y otra
vez). **Se publica la de filas, 12,0 %, porque es la que ya está publicada y la que reproduce**, y la
de casos va al lado para que nadie la descubra después como si fuera una corrección.

## DE QUÉ ESTÁ HECHA ESTA POBLACIÓN, medido y no advertido

Esto es lo que impide leer estos 150 como «lo que verá quien pregunte el lunes»:

| | |
|---|---:|
| Filas | 150 |
| **Preguntas distintas** | **71** (×2,11) |
| **Con asignatura elegida** | **150 de 150** |
| Sin asignatura elegida | **0** |

| Modo | n | p50 | pasan de 5 s |
|---|---:|---:|---:|
| `responder` | 124 | 3.046 ms | 16 |
| `acompanar` | **24** | **1.977 ms** | 2 |
| `corregir` | 2 | 3.343 ms | 0 |

**Tres cosas que hacen a esta muestra optimista respecto del camino del lunes**, y las tres son
hechos, no impresiones:

1. **Las 150 llevan asignatura elegida a mano.** El camino que corre el lunes **no la lleva**: el
   ciclo es lo único obligatorio desde el 15/08.
2. **24 de 150 son `acompanar`**, cuyo p50 es **1.069 ms más bajo** que el de `responder` — son
   andamiajes cortos, y tiran de la mediana hacia abajo.
3. **Es tráfico mezclado**: tests, scripts de medida y consultas a mano, con las preguntas curadas y
   congeladas repetidas hasta cinco veces cada una.

Por eso el lote controlado de veinte preguntas ordinarias da **35 %** de incumplimiento
([evidencia](2026-08-15-veinte-preguntas-ordinarias-de-dwes.md)) y no 12,0 %. **Las dos cifras son
verdad sobre su población y no se comparan entre sí.** La de 150 dice *"así ha ido el tráfico real de
estas doce horas"*; la de 20 dice *"así le irá a quien escriba la suya"*.

## Lo que ESTO SÍ sustituye, y lo que no

**Sustituye** al *"entre el 30 y el 40 % de las consultas no caben en 5 segundos"* de
[la medida del 13/08](2026-08-13-concurrencia.md), que se hizo **con el reordenador puesto** —una
configuración descartada el 14/08— y donde el p50 era **5.151 ms** y el p95 **63.853 ms**. Aquella
sigue siendo cierta de aquella configuración; **no describe lo que se sirve**.

**No sustituye** al lote controlado: son poblaciones distintas y las dos se publican con su n.

## Reproducirlo

```sql
SELECT count(*),
       percentile_cont(0.5)  WITHIN GROUP (ORDER BY total_ms) AS p50,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY total_ms) AS p95,
       count(*) FILTER (WHERE total_ms > 5000) AS pasan_de_5s,
       count(*) FILTER (WHERE abstencion)      AS abstenciones
  FROM respuestas
 WHERE creado_en >= TIMESTAMP '2026-08-14 14:11:00'
   AND creado_en <= TIMESTAMP '2026-08-15 02:12:00';
```
