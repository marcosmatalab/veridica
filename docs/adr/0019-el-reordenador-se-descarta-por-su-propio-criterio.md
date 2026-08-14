# ADR 0019: el reordenador se descarta por su propio criterio, y la fusión se cablea a 10:1

- **Fecha:** 14 de agosto de 2026
- **Encargo:** 3.4 y 3.5 (cierre de la fase 3)
- **Estado:** aceptada
- **Evidencia:** [`docs/evidencia/2026-08-14-cierre-fase3.md`](../evidencia/2026-08-14-cierre-fase3.md)

## Contexto

El criterio de aceptación del reordenador se escribió el 13 de agosto **como fórmula y antes de
tener su número** — *se queda si cierra más de la mitad del hueco entre la fusión sola y el techo
del pool, en `recall@6` sobre `lectura`* — precisamente para que la decisión la tomara el número y
no quien lo midiera. Con el conjunto oro corregido (94 pares) llegaron las tres entradas de la
fórmula, y una divergencia previa: **los pesos 10:1 decididos en el 3.3 nunca se cablearon** —
producción fusionaba a 1:1 sin que nadie lo hubiera decidido.

## Decisión

**1) La fusión de producción pasa los pesos decididos** (`PESOS_FUSION`, 10:1:1). Medido en
`lectura`: techo del pool 30 **81,3 %** frente a 74,7 % a 1:1; `recall@6` **58,7 %** frente a
42,7 %. `PESOS_POR_DEFECTO` no se toca: es el defecto compartido de `fusionar` y de sus tests, y
una constante compartida no se "mejora" de paso.

**2) El reordenador queda DESCARTADO por defecto.** La fórmula da listón 70,0 % (= 58,7 +
(81,3 − 58,7)/2) y el reordenador dio **56,0 %**: no solo no cierra la mitad del hueco — queda
**por debajo de la fusión sin reordenar**. En `busqueda` empata el `recall@6`; el `nDCG@5` global
queda en tablas (0,405 contra 0,406). Se ejecuta la rama que la guía dejó escrita para este caso:
configuración por defecto **fusión 10:1 en top 6, sin reordenar**, objetivo de fase declarado
**no alcanzado** (58,7 % contra 80 %).

**3) El código NO se borra.** `app/core/reordenador.py`, sus tests y su degradación anunciada se
conservan; el interruptor invierte su sentido (`REORDENADOR_ACTIVO=1` lo reenciende) para la
ablación del 7.3 o para re-medirlo si cambian el conjunto, el pool o el modelo. El ADR 0015
("GPU o nada") sigue valiendo cuando está encendido.

## Trade-off

- **Se gana**, y todo medido: desaparece la única pieza GPU-o-nada (la divergencia
  demo-VPS del 8.1 se disuelve), el techo de concurrencia de ~1,9 consultas/s deja de aplicar, la
  pérdida de reordenado desde 5 alumnos simultáneos desaparece, y el paso de 554 ms (p95 GPU) sale
  de la ruta del TTFT.
- **Se paga**: se renuncia a la mejora de cabeza que un cross-encoder *podría* dar con otro pool u
  otro conjunto — hoy es negativa, y "hoy" está anclado a estas corridas (26-31 de `corridas_eval`).
- **Lo que se descarta**: mantenerlo encendido "por si acaso" (pagar divergencia + concurrencia por
  una mejora negativa), y también borrarlo (re-medirlo costaría reescribirlo; el interruptor cuesta
  una variable de entorno).

## Consecuencia que hay que vigilar

**El listón quedó por debajo del objetivo (70,0 < 80,0), y eso invalida una propiedad que la
fórmula tenía con el conjunto viejo.** El techo del pool (81,3 %) apenas supera el objetivo: ni un
reordenador perfecto lo alcanzaría con margen. Si alguien retoma el 80 %, el trabajo está en que el
oro **entre** en el pool (troceado, léxica, corpus — 18 de 94 pares fuera del pool entero), no en
reordenarlo. Cualquier re-medida del reordenador se hace contra la fórmula, no contra este número.
