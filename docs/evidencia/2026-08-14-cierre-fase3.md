# Evidencia: cierre de la fase 3 sobre el conjunto oro corregido

- **Fecha:** 14 de agosto de 2026
- **Encargos:** 3.1, 3.2, 3.3 (re-corridos), 3.4 y 3.5 (cerrados)
- **Conjunto:** oro corregido — **94 pares (19 `busqueda`, 75 `lectura`)**; el diff del propietario
  aplicado en el commit `2e0dbdc` **más `oro-063→18` en segunda tanda el mismo día** (la línea que
  faltaba en la transcripción del diff, cazada sumando: la historia, en el .md del conjunto);
  `verificar_oro` en verde **antes de cada corrida** (regla del 3.5)
- **Corridas:** `corridas_eval` ids **26-31**, con el arnés commiteado (`98e9899`) y el conjunto
  con los 54 movimientos. Trazabilidad de las dos tandas anteriores: las 20-25 corrieron el mismo
  arnés sobre el conjunto con 53 movimientos —al re-medirse con el 54º, **ningún recall se movió ni
  una décima** y solo el nDCG@5 cambió en la tercera decimal (el par movido cambió de puesto dentro
  de la cabeza, no de dentro/fuera)—; las 14-19 fueron la primera pasada con el árbol sin commitear,
  con métricas idénticas a las 20-25 (comprobado con un `=` de jsonb, quitando el tiempo por
  consulta).
- **Configuración:** la misma de las corridas del 13/08 donde existía (léxica y vectorial k=20;
  fusión k_rrf=60), más las dos configuraciones de fusión que el cierre necesitaba (abajo).

## 1. Los dos números, antes y después, con el tamaño al lado

La regla se escribió al decidir la corrección: *si el conjunto se corrige, se reportan los dos
números*. `recall@6` y `recall@20`, global y partido:

| vía | corrida | `@6` antes (n=100) | `@6` después (n=94) | `@6` `lectura` desp. | `@20` antes | `@20` después |
|---|---|---:|---:|---:|---:|---:|
| Léxica (3.1) | 26 | 39,0 % | **27,7 %** | 22,7 % | 61,0 % | **48,9 %** |
| Vectorial (3.2) | 27 | 73,0 % | **60,6 %** | 58,7 % | 82,0 % | **76,6 %** |
| Fusión 1:1, k=20 (3.3) | 28 | 62,0 % | **46,8 %** | 44,0 % | 80,0 % | **71,3 %** |
| Fusión 10:1, pool 30 | 29 | 72,0 % | **60,6 %** | 58,7 % | 82,0 % | **74,5 %** |

(El "antes" de la fila 10:1 sale de la única corrida a 10:1 del 13/08, que se hizo **a pool 40**;
sus `@6` y `@20` son los de aquella corrida, y el techo comparable del pool 30 de entonces es el del
recuento del mismo día — **87,7 %** en `lectura`, no el 88,9 % del corte a 30 de aquel pool 40. Lo
cazó la pasada adversarial; el README queda corregido con el 87,7.)

Y el `nDCG@5` (métrica nueva del arnés, sonda validada en rojo antes de usarla), después:

| vía | global | `busqueda` | `lectura` |
|---|---:|---:|---:|
| Léxica | 0,155 | 0,251 | 0,131 |
| Vectorial | 0,441 | 0,557 | 0,412 |
| Fusión 10:1, orden de la fusión | 0,406 | 0,484 | 0,386 |
| Fusión 10:1 + reordenador (top 6) | 0,405 | 0,531 | 0,373 |

**Los números BAJARON al corregir la vara, y la explicación se miró caso a caso, no se supuso.**
Los pares mal anclados apuntaban al fragmento del **encabezado** de su sección (nueve, directamente
al índice del documento), y ese fragmento es justo el que la búsqueda trae con facilidad: los
títulos comparten términos con la pregunta. O sea que el conjunto roto **regalaba aciertos con el
mismo mecanismo con el que se etiquetó mal**. La dirección del cambio quedó declarada como incierta
el 13; salió hacia abajo, y se publica con la misma letra que si hubiera salido hacia arriba.

## 2. La divergencia que apareció midiendo: los pesos 10:1 no estaban cableados

El 3.3 decidió fusión **10:1** (13/08, con su tabla). Producción llamaba a `recuperar()` **sin
`pesos`**, o sea fusionaba a **1:1**: la decisión existía en la guía y en la evidencia, y no en el
código — la familia de `VERSION_PROMPT` y del `timeout_lectura`. Medida la diferencia sobre el
conjunto corregido (corridas 29 y 30), en `lectura`:

| pesos | `recall@6` | techo del pool 30 |
|---|---:|---:|
| 1:1 (lo cableado) | 42,7 % | 74,7 % |
| **10:1 (lo decidido)** | **58,7 %** | **81,3 %** |

**El cableado que faltaba costaba 16 puntos de cabeza y 6,6 de techo.** Arreglado en este mismo
cierre: `PESOS_FUSION` en `recuperacion.py`, pasado explícito por `consulta.py`.
`PESOS_POR_DEFECTO` no se toca (constante compartida de `fusionar` y sus tests).

## 3. El criterio del reordenador, ejecutado (cierre del 3.4)

La fórmula se escribió el 13, antes de tener número: *listón = fusión_sola + (techo − fusión_sola)
/ 2*, en `recall@6` sobre `lectura`. Con las entradas del conjunto corregido (fusión 10:1, pool 30;
corridas 29 y 31):

| | `recall@6` en `lectura` (n=75) |
|---|---:|
| Fusión sola | 58,7 % |
| Techo del pool 30 | 81,3 % |
| **Listón** | **70,0 %** |
| **Reordenador (BGE v2-m3, GPU, sobre ese pool)** | **56,0 %** |
| Objetivo de la fase | 80,0 % |

**Veredicto: NO SE QUEDA.** No es que no cierre la mitad del hueco: queda **por debajo de la fusión
sin reordenar** (−2,7 puntos). En `busqueda` empata el `recall@6` (68,4 %) y mejora el `@5`
(68,4 % contra 57,9 %); el `nDCG@5` global queda en tablas (0,405 contra 0,406). La mejora del
reordenador, cuantificada como pide el cierre de fase: **negativa en el subconjunto honesto**.

Se ejecuta la rama que la guía dejó escrita para este caso (ADR 0019): configuración por defecto
**fusión 10:1 en top 6, sin reordenar** (`REORDENADOR_ACTIVO` pasa a apagado por defecto; el código,
sus tests y su degradación anunciada se conservan para ablación), y el objetivo de la fase queda
declarado **NO alcanzado: 58,7 % contra 80 %**. Lo que el descarte devuelve, medido en su día: la
única pieza GPU-o-nada (divergencia demo-VPS disuelta), el techo de ~1,9 consultas/s, la pérdida de
reordenado desde 5 alumnos, y 554 ms de p95 fuera de la ruta del TTFT.

**Y la propiedad de la fórmula que el conjunto corregido invalidó, dicha:** el listón ya no queda
por encima del objetivo (70,0 < 80,0), porque el techo real apenas lo supera. **Ni un reordenador
perfecto alcanzaría el 80 % con margen sobre este pool.**

## 4. Dónde está el hueco de verdad: los fallos, mirados a ojo

**18 de 94 pares no entran ni en el pool de 30** (fusión 10:1). No son ruido de etiquetado —eso ya
se corrigió—: son preguntas conceptuales cuyo oro vive en secciones de contenido. Muestra (la lista
entera sale del arnés):

- `oro-054` — los cinco principios SOLID
- `oro-055` — qué es un test unitario y cómo se escribe con JUnit
- `oro-058` / `oro-059` — métodos HTTP y códigos de estado en una API REST
- `oro-041` — claims y `ClaimsPrincipal`
- `oro-100` — `using` con recursos
- `oro-013` / `oro-014` — los dos hallazgos reales de recuperación ya conocidos del 13/08, que
  siguen fuera

Otros **19** entran en el pool pero detrás del puesto 6 —17 `lectura` y 2 `busqueda`; `oro-068` en
el 7, `oro-030` en el 8, `oro-083` en el 9…— y con ellos la cuenta cierra: 57 en el top 6 + 19
detrás + 18 fuera = 94. (La primera versión de este párrafo decía "12", que era el largo del
listado truncado con el que se escribió, no el recuento: lo cazó la pasada adversarial contra la
corrida del pool 10:1, y se corrige declarándolo.) **El camino al 80 % es de cobertura y de cabeza de la
fusión —troceado, léxica, corpus—, no de reordenado**, y la tabla de contingencias del 1.3/1.4 es
su sitio.

## 5. Contaminación cruzada (cláusula del 3.5)

**0 de 94 contextos finales con algún fragmento de otra asignatura, en las seis corridas.** Y no es
casualidad sino construcción: el filtro de asignatura es la **firma** de las funciones de búsqueda
(no se puede llamar sin él), y se ha visto excluir de verdad con el documento colado del 1.7. El
arnés lo cuenta en cada corrida en vez de suponerlo.

## 6. El cierre, cláusula a cláusula

Del enunciado del cierre de fase 3 (*números en la tabla, con las dos métricas partidas por
`localizacion` y no solo globales; contaminación en cero o con explicación escrita; mejora del
reordenador cuantificada*):

| cláusula | estado |
|---|---|
| números en la tabla | ✓ README (tabla antes/después con n al lado) y guía 3.4/3.5 |
| dos métricas partidas por `localizacion` además del global | ✓ `recall@6` y `nDCG@5`, en §1 y en `corridas_eval` 26-31 |
| contaminación en cero o con explicación | ✓ cero, contada (§5) |
| mejora del reordenador cuantificada | ✓ **−2,7 puntos** en `lectura` @6; descartado por su criterio (§3) |

**Lo que queda abierto y declarado:** el objetivo de calidad (80 % `lectura` @6) **no alcanzado**
(58,7 %), con el techo del pool (81,3 %) señalando que es un problema de cobertura; y el 4.6 tiene
desde hoy el conjunto corregido para calibrar (`confianza_recuperacion`, umbral del NLI, plazos).

## Cómo se reproduce

```bash
python scripts/verificar_oro.py                                            # SIEMPRE antes de medir
DATABASE_URL=... python scripts/medir_recuperacion.py --via lexica --k 20
DATABASE_URL=... python scripts/medir_recuperacion.py --via vectorial --k 20
DATABASE_URL=... python scripts/medir_recuperacion.py --via fusion --k 20
DATABASE_URL=... python scripts/medir_recuperacion.py --via fusion --k 30 --peso-vectorial 10
DATABASE_URL=... python scripts/medir_recuperacion.py --via fusion --k 30
DATABASE_URL=... python scripts/medir_recuperacion.py --via fusion --k 30 --peso-vectorial 10 --reordenador
```

Las cinco primeras no gastan (SQL y GPU locales); la sexta usa la GPU para el cross-encoder. La
divergencia declarada que queda: el arnés vive en `scripts/` y no en `evals/arnes/` como escribió
el 3.5 — mismo script, otra carpeta; se deja donde están todos los `medir_*` del repo, y se dice.
