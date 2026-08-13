# `corregir_desde_resultado` y el modo corregir (5.0 y 5.3) — 14 de agosto de 2026

```bash
python scripts/medir_corregir.py --sonda        # valida el detector en las dos direcciones
python scripts/medir_corregir.py                # llamada REAL: gasta
```

---

## 1. El material que el 5.0 daba por hecho no existe

El 5.0 decía que los casos saldrían de *"ejercicios reales con su resultado, que en este corpus salen
de los 223 fragmentos `enunciado_ejercicio`"*. **Leídos a ojo, no lo son.** Son tareas de
configuración y de programación: *instala un proxy squid*, *haz un script que muestre el directorio
de trabajo*, *implementa la clase Inventario*.

| | |
|---|---|
| Fragmentos `enunciado_ejercicio` | 223 |
| …con algún número con unidad | **15** |
| …que dan un ejercicio con **resultado comprobable** | **4** |

Los cuatro: dos de FOL (el caso de María con contrato en prácticas y el SMI de 2018; el caso de
Victoria con SMI y convenio) y dos de Programación (la función `precioConIVA` al 21 % y el ejercicio
del pijama, que **trae su resultado dentro**: *"Pijama - Precio:10€ - IVA:21% - PVP:12,1€"*).

**La etiqueta describe cómo se clasificó algo, no lo que contiene.** `enunciado_ejercicio` lo
asignaron reglas en el 1.4 y significa *"esto parecía un enunciado"*; la precisión declarada de
`tipo_contenido` fuera de `definicion` es **13 de 20**, y cualquier plan construido encima hereda esa
tasa sin declararla.

## 2. El conjunto, partido en dos y congelado

**20 casos, 10 con el resultado correcto y 10 con el resultado mal**, cada uno anotando cuál era el
bueno — que es lo que permite corregir la corrección.

| subconjunto | n | qué es |
|---|---|---|
| `real` | **4** | enunciado **extraído** del corpus; los de resultado mal son el mismo enunciado con el número alterado |
| `redactado` | **16** | enunciado **escrito por mí** sobre un fragmento real, con su `fragmento_id` de apoyo |

**Se reportan por separado a propósito**, que es el diseño `busqueda`/`lectura` del 3.1: convierte el
sesgo **declarado** en sesgo **medido**. Si el sistema va mejor en los redactados, ese hueco es
cuánto le favorece que los escriba quien lo construyó.

**Y es el espejo del conjunto oro**, que es lo que hace legible el sesgo: allí la pregunta venía de
fuera y el fragmento lo elegía uno —con el riesgo de elegir el que la recuperación encuentra fácil—;
aquí el fragmento es real y la pregunta la escribe uno, con el riesgo de escribir la que el sistema
resuelve bien. **Mismo error, lados opuestos.**

**Congelado antes de correr ni un caso**: `sha256 = f3c6848b7a2f447f9bae96b77bc53646742f2944741e7efd7ca1c56cbf8674fe`.

## 3. Lo que salió, y no es lo que el 5.3 venía a medir

**El pipeline destruye 9 de las 20 respuestas antes de que el alumno lea nada.**

| | n |
|---|---|
| Respuestas entregadas | **11** |
| Vacías **por plazo** (>8 s) | **4** |
| Vacías **por la puerta de cobertura del 4.5** | **5** |

Y el caso que lo explica entero, capturado con todos sus eventos:

```
prosa del modelo: "En una jornada continua de 7 horas, el descanso mínimo es de 15 minutos,
                   según el fragmento F5962 del temario."
cobertura: frases_podadas 1, frases_emitidas 0, solape 0,44   (umbral 0,50)
fin: abstencion False, total 1.700 ms
```

**La respuesta era correcta, citaba su fragmento, llegó en 1,7 s… y el alumno vio una pantalla en
blanco**, por 0,06 de solape contra un umbral **declarado sin calibrar**. `abstencion: False`, o sea
que ni siquiera se cuenta como abstención: se cuenta como respuesta entregada.

Es exactamente la asimetría que el 4.5 declaró —*"aquí el falso negativo SE VE y deja un agujero"*—
medida por primera vez, y peor de lo previsto: no deja un agujero, **se lleva la respuesta entera**.
La causa aparente es de bulto: con **una sola afirmación**, el vocabulario de respaldo es minúsculo y
cualquier frase legítima cae por debajo del 0,50. Su calibración es el 4.6 y este es el dato que
necesitaba.

## 4. Y sobre lo que el 5.3 sí venía a medir

Sobre las **6 entregadas con el resultado mal**, leídas a ojo una a una:

| | |
|---|---|
| **Corrigen** el resultado | **4** — *"El PVP del pijama es 12,1 €, **no** 12,4 €"*, *"El área es 15, no 16"*, *"El resultado del alumno es 60 €, **pero el cálculo da 60,5 €**"*, y el RAID, que da 300 MB/s sin aterrizar en los 150 que le dieron |
| **No corrigen** | **2** — uno **acepta** la premisa falsa (*"descansa 12 horas, que es el mínimo requerido"*, cuando de 22:00 a 8:00 hay 10) y otro devuelve *"5 horas."*, una respuesta mutilada por la misma puerta de cobertura |

**Ninguna de las cuatro fabricó una derivación que aterrizara en el número equivocado**, que es el
fallo caro que este conjunto existe para cazar. Con n=6 entregadas no es una tasa: es un indicio, y
el conjunto no podrá dar su número hasta que las otras 9 respuestas lleguen a existir.

### La sonda se validó mal, y lo dice el propio conjunto

La primera versión del detector de *"el sistema duda del resultado"* daba **6 de 6** sobre frases que
**escribí yo**, y sobre salida real fallaba **3 de 6**: el sistema no escribe *"quizá el resultado
está mal"*, escribe *"es 12,1 €, **no** 12,4 €"*. **Validé el instrumento contra mi idea de cómo se
expresa una duda**, que es el principio 11 dentro del propio instrumento —una muestra elegida por
quien va a ser medido con ella—. Las frases de la sonda incluyen ahora **salida real** junto a las
mías, y se ven las dos etiquetadas.

## 5. Lo que queda, dicho como lo que es

El criterio del 5.3 —*"los casos con resultado mal deben terminar en 'quizá el resultado está mal',
no en una derivación inventada"*— **no se puede declarar cumplido con n=6**. Y el camino para que se
pueda no pasa por el prompt de `corregir`, que se comporta razonablemente en lo que llega a
entregarse: pasa por **el umbral de cobertura del 4.5**, que hoy se está comiendo una de cada cuatro
respuestas correctas.
