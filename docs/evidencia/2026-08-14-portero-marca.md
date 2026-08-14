# Evidencia: el portero marca en vez de podar, y el nombre de tipo se vuelve ingramatical

- **Fecha:** 14 de agosto de 2026
- **Encargos:** 4.5 (revisado, [ADR 0021](../adr/0021-el-portero-marca-no-poda-y-eso-invierte-su-asimetria.md)) y 2.2 (contrato)
- **Rama:** `portero-marca`

## 1. El suelo de longitud: cómo se derivó el 13, y por qué el 20 estaba mal

**El problema:** 152 filas reales (15,6 % de `afirmaciones`) llevaban como `texto` el nombre de un
tipo. `texto: str` sin `min_length` lo hace **gramatical**, así que la decodificación restringida
podía emitirlo y ninguna capa posterior lo miraba.

**La medida, sobre las 826 afirmaciones sanas de la base** (excluidas las 152 rotas):

```
min 3 | p1 8 | p5 22 | p25 45 | mediana 75 | p95 217 | max 368
```

| suelo | rechaza (filas) | % | **casos** | **%** | qué mata |
|---|---:|---:|---:|---:|---|
| 13 | 16 | 1,9 % | **7 de 414** | **1,7 %** | `ext4`, `Actuator`, `Herencia`, `Multitarea`, `600` — afirmaciones de una palabra |
| 20 | 40 | 4,8 % | **11 de 414** | **2,7 %** | las de arriba **más `@RestController` (15) y `{% include ... %}` (17)** |

(Las 826 sanas son **414 casos distintos**; recuento del [barrido de filas contra
casos](2026-08-14-barrido-filas-vs-casos.md) §7. **El margen relativo entre 13 y 20 se estrecha de
×2,5 a ×1,6**, o sea que el argumento porcentual era el flojo — y no es el que decidió.)

**El 20 era la propuesta inicial y la distribución lo tumbó.** En un corpus medio código,
`@RestController` es una `literal` legítima y perfectamente verificable; un tope pensado para prosa
no lo sabe. El número correcto sale de **la clase que se quiere prohibir**: el nombre de tipo más
largo es `conocimiento` (12), así que **13** vuelve ingramatical la clase entera —el objetivo— y ni
un carácter más.

**Y la red detrás de la gramática**, porque el fallo no es *"el texto es corto"* sino *"el texto es
la etiqueta"*: el validador rechaza un `texto` cuyas palabras sean **todas** nombres de tipo
(`'literal literal'`, `'  parafrasis  '`), y al saltar dispara el reintento único de la sección 7.
La otra dirección está anclada: *"El cálculo de subredes usa la máscara"* menciona un nombre de tipo
y pasa, porque la red pide que **todas** las palabras lo sean.

## 2. El portero que marca: lo que el cambio compra, medido

Contadores de las **205 respuestas con portero** que hay en la base, escritas cuando el portero
**podaba** — **en las dos unidades**, porque esas 205 respuestas salen de **46 preguntas distintas**
(el arnés repite, ×4,46):

| | filas | **casos (pregunta distinta)** |
|---|---:|---:|
| respuestas con portero | 205 | **46** |
| frases juzgadas | **543** | **114** |
| frases **podadas** (desaparecían) | **133 (24,5 %)** | **27 (23,7 %)** |
| respuestas que perdían al menos una frase | **86 de 205 (42,0 %)** | **17 de 46 (37,0 %)** |
| respuestas que se quedaron **sin ninguna frase** (pantalla en blanco) | **32** | **8** |

**La tasa de poda es robusta al recuento** (24,5 % → 23,7 %) porque es una tasa **por frase**, y las
frases no se repiten aunque la pregunta sí. Lo que sí cambia de significado es el último renglón:
**32 es cuántas veces ocurrió la pantalla en blanco y 8 es a cuántas preguntas distintas les pasa**
— para dimensionar el daño en producción vale la segunda, y para dimensionar la frecuencia, la
primera. Recuento completo en el [barrido de filas contra
casos](2026-08-14-barrido-filas-vs-casos.md) §7.

**Todo eso pasa a cero por construcción**: desde el cambio, ninguna frase se pierde —hay un test que
ancla exactamente esa propiedad— y la que no está respaldada llega **marcada**.

**El camino real, comprobado con una consulta nueva (respuesta 393):** 4 frases, 1 marcada con
solape 0,429. La marcada es *«El identificador de sesión (SID) puede añadirse como parte de la URL
o almacenarse en cookies»* — **contenido legítimo que el portero viejo habría borrado**, dejando un
salto en mitad del párrafo.

## 3. La asimetría invertida, escrita ANTES del barrido

Está entera en el [ADR 0021](../adr/0021-el-portero-marca-no-poda-y-eso-invierte-su-asimetria.md).
En una línea: mientras podaba, el falso negativo era el caro —se llevaba una frase legítima de un
texto que alguien está leyendo—; ahora un falso negativo solo pone una marca injusta y **el caro es
el falso positivo**, una frase sin respaldo llegando **sin marca**. **La dirección de calibración se
invierte: hay que subir el umbral, no bajarlo.**

De ahí la regla que sube al Apéndice A: **un número no lleva dentro su propia justificación**. Lo
que se calibró fue una respuesta a *"¿qué error es el caro?"*, y esa pregunta acaba de cambiar de
respuesta.

## 4. La abstención se re-condiciona, no se retira (corrección del propietario)

Con el portero marcando, `sin_prosa_respaldada` ya no puede saltar por poda. **La tentación era
retirar la rama; se re-condiciona.** El caso de **prosa vacía** sigue existiendo —el modelo cumple
el contrato y no escribe redacción— y sin esa rama volvería la pantalla en blanco sin declarar, que
es el fallo que costó medio día encontrar. Cambia el disparador (`caracteres_emitidos == 0`), se
conserva la salida, y el test cubre el disparador nuevo.

El campo `por_cobertura` del evento pasa a `por_prosa_vacia`; el viejo se conserva con su valor y
con un aviso, porque hay corridas guardadas y un script que lo leen — pero **su nombre ya no dice lo
que significa**, y eso se declara donde se lee.

## 5. Las sondas, validadas con mutación

Las dos direcciones, con el diff enseñado antes de leer el resultado:

| mutación | qué se rompe | resultado |
|---|---|---|
| `respaldada: True` siempre (todo pasa sin marca) | el error **caro** de la asimetría nueva | **7 tests en rojo** |
| rama de prosa vacía retirada | la pantalla en blanco vuelve sin declarar | **1 test en rojo** |

Once tests anclaban el mundo "poda" y se movieron a propósito, cada uno con su motivo escrito
dentro: lo que protegían —el juicio de cobertura— se conserva; lo que afirmaban sobre la emisión
cambió.
