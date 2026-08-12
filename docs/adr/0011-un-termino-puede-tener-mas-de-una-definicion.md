# ADR 0011: en `glosario`, un término puede tener más de una definición

- **Fecha:** 12 de agosto de 2026
- **Encargo:** 2.6 (la sección 9 de la guía se corrige aquí; también el 3.3 y el 5.4)
- **Estado:** aceptada

## Contexto

El DDL de la sección 9 declara `UNIQUE (asignatura_id, termino)` en `glosario`. Suena a higiene
básica —un término, una definición— y es exactamente la restricción que impide el momento 3 de la
demo.

**El DWES antiguo (Comesaña, ~2012) y el moderno (2025-26) mapean los DOS al módulo 0613**, y eso no
es un descuido del mapa del 2.1: se declaró así a propósito para que los dos materiales cayeran en
la misma partición y el detector pudiera compararlos. Consecuencia directa: **las dos definiciones
incompatibles de MVC son del mismo `(asignatura_id, termino)`**. Con el unique, la segunda la
rechaza la base, el glosario se queda con una sola y **el par contradictorio no existe**.

Es la misma familia que el ADR 0008: una restricción que obliga a tirar el dato que el proyecto
necesita medir está resolviendo el problema en el sitio equivocado. Allí era el documento colado del
1.7; aquí es la contradicción real que sostiene el momento 3.

## Decisión

**`UNIQUE (asignatura_id, termino, fragmento_id)`** en lugar de `UNIQUE (asignatura_id, termino)`.

Lo que se impide sigue impidiéndose: **la misma definición extraída dos veces del mismo fragmento**,
que sí es duplicación y no dice nada. Lo que se permite es lo que el corpus de verdad tiene: dos
materiales del mismo módulo definiendo el mismo término de forma distinta.

## Y lo que sale gratis, que es lo mejor de este cambio

**Que un término tenga más de una entrada ES la señal de conflicto.** El momento 3 deja de necesitar
una tubería de similitud y pasa a ser:

```sql
SELECT termino, count(*) FROM glosario WHERE asignatura_id = %s
 GROUP BY termino HAVING count(*) > 1;
```

**Determinista, sin modelo y sin umbral.** Comparado con lo que había —el detector del 1.8, que
compara fragmentos por similitud de embeddings y da **0,564** en el par MVC porque cada definición va
enterrada en 512 tokens de otra cosa—, esto no es una mejora de precisión: es otro mecanismo. La
clave de comparación pasa a ser **el término**, no el vector, que es justo lo que aquel encargo dejó
escrito que hacía falta.

Para la sesión importa además cómo se cuenta: "el sistema encontró una contradicción" con un
`GROUP BY` detrás se puede enseñar en pantalla y se puede reproducir delante de quien pregunte. Con
un umbral de similitud detrás, hay que pedir confianza.

## Qué más asumía una entrada por término, comprobado antes de firmar esto

| Dónde | Qué decía | Qué pasa con varias entradas |
|---|---|---|
| **3.3 Fusión** | "si el glosario tiene el término exacto, **su fragmento** entra con prioridad" | Entran **sus fragmentos**, en plural. No rompe nada y mejora: cuando un término está en conflicto, la recuperación trae las dos caras y la fase 4 puede enseñarlas. Se corrige la redacción del encargo |
| **5.4 Proactividad** | "concepto del glosario aún no tocado en la conversación" | Se recorren términos **distintos** (`SELECT DISTINCT termino`), no filas. Anotado en el encargo |
| **8.2 Degradación** | "ofrece glosario y citas literales" si el proveedor cae | No le afecta: enseñar dos definiciones de un término sin modelo de por medio es exactamente lo que se quiere en ese caso |

## Trade-off

Se pierde la garantía automática de "un término, una definición", que **nunca fue verdad en este
corpus** y cuya única función habría sido esconderlo. A cambio, el glosario refleja el material tal
como es y el conflicto se detecta con una consulta, no con un modelo.

El coste real es de interfaz, y se declara: cuando la fase 4 responda sobre un término con dos
entradas, tiene que **enseñar las dos con su fuente y su fecha y decir cuál es más reciente**, sin
arbitrar. Ya está escrito así en el 4.5, y ahora tiene de dónde salir.
