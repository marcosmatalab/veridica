# Verificador de cálculo (encargo 4.4) — 13 de agosto de 2026

Recálculo con sympy, jamás `eval`. Intérprete: miniconda (CPython 3.13.2), `sympy==1.14.0`, anclada
en `requirements.txt` a partir de hoy —estaba instalada **de rebote** en la máquina, que es la misma
avería que numpy y httpx: una dependencia que nadie declara es una versión que nadie eligió—.

Reproducción:

```bash
python scripts/medir_guarda_calculo.py    # la guarda: qué admite, qué rechaza y cuánto tarda
python scripts/humo_calculo.py            # llamada REAL al proveedor: gasta dinero
```

---

## 1. Lo que la guarda deja pasar, MEDIDO

Poner el tope no es medirlo. Los dos lados, porque los dos fallan distinto:

| | expresión | frío | **caliente** |
|---|---|---|---|
| Peor caso **admitido** | `sqrt(2)+sqrt(2)+…` (25 términos) | 26,31 ms | **2,34 ms** |
| Peor **rechazo** | `2**2**2**30` | 0,28 ms | **0,24 ms** |
| Caso de temario típico | `2^32 = 4294967296` | — | 0,2–0,5 ms |

Los **dos** números por caso, y no el que quede mejor: la primera medida del peor caso dio **31 ms**
y la segunda **1,7 ms**, porque sympy calienta cachés internas. Publicar la primera habría sido
publicar un 95 % de arranque de librería. El proceso de la API es largo, así que **el que decide es
el caliente**; el frío se paga una vez y también se dice.

Con el presupuesto de verificación de la sección 8 (2 s por consulta), el peor caso admitido es el
**0,12 %**. Los 24 casos de temario y las 9 bombas salen como deben (`medir_guarda_calculo.py`
devuelve 0).

### Los tres agujeros que solo se ven cronometrando

Ninguno se ve leyendo el código, y los tres estaban en la primera versión:

1. **`evaluate=False` desactiva los operadores, no las llamadas a función.** `factorial(100000)` se
   calculaba **dentro del parseo del propio guarda**, o sea antes de que el guarda pudiera mirar
   nada. Se vio porque la prueba se colgó; con un argumento algo menor habría devuelto un veredicto
   correcto y tarde, sin que nadie mirara. **Arreglo:** en la pasada del guarda, cada función se
   sustituye por una **indefinida** de sympy — no es una lista de funciones en las que se confía, es
   que ahí no hay nada que pueda ejecutarse.
2. **El tamaño se estimaba contando cifras**, que es el logaritmo truncado hacia abajo. Para la base
   2 daba **0**, y como la magnitud de una potencia es `log10(base) × exponente`, ese cero se
   multiplicaba: **`2**999999999` salía con magnitud cero** y la guarda lo daba por inofensivo.
3. **Y el `0.0 * inf` resultante daba `nan`, que no es mayor que nada.** Atravesaba el `>` del tope
   como si fuera un permiso. La comprobación devolvía `False` y parecía una autorización.

## 2. Los casos de temario, a ojo

24 de 24 dan lo esperado. Los que enseñan algo:

| expresión | afirmado | veredicto | por qué importa |
|---|---|---|---|
| `10/3` | `3,33` | verificada | la tolerancia sale de los **decimales escritos** |
| `10/3` | `3,3` | verificada | un decimal, y con un decimal es correcto |
| `10/3` | `3,5` | **podada** | y esto no lo es |
| `2/3` | `0,7` | verificada | **el caso que sostiene el ADR 0016** |
| `2/3` | `0,70` | **podada** | mismo `float`, distinto veredicto |
| `1/8` | `0,13` y `0,12` | verificada las dos | instituto y redondeo al par: dos convenciones correctas |
| `1/8` | `0,11` | podada | fuera del empate no hay manga ancha |
| `2**100` | 31 cifras exactas | verificada | por encima de 2^53 un `float` ya no vale |
| `10/0` | `5` | **no_verificable** | no es una poda: no hay número que comparar |
| `for i in range(10): print(i)` | `10` | **no_verificable** | el sandbox no está construido; no se castiga por eso |

## 3. La llamada real, que es donde se cayó la venda

**Antes de esto, la base tenía 345 afirmaciones reales y NI UNA de tipo `calculo`** (337 `literal`,
8 `parafrasis`). El verificador se había construido entero contra casos escritos por mí.

### Hallazgo 1: el verificador no veía una sola afirmación

Cinco consultas explícitamente aritméticas → **cero afirmaciones de tipo `calculo`**. El modelo
contestaba *"son 62"*, *"son 21"*, *"4.294.967.296"* como `conocimiento`, sin `expresion` que
recalcular. El 4.4 estaba completo, correcto, medido… y era decorativo.

**La causa era una decisión mía:** `calculo` no aparecía en el prompt, porque razoné que su
explicación cabía en el `description` del campo (principio 7). **La gramática PROHÍBE; no ELIGE.**
Elegir entre cinco ramas que el esquema permite todas no es algo que el esquema decida, y la
descripción de un campo es una etiqueta que solo se lee cuando ya se ha llegado al campo. El
principio 7 dice *no pidas por prompt lo que la gramática puede imponer*; no dice *no expliques por
prompt lo que la gramática no puede decidir*.

### Hallazgo 2: la línea del prompt tampoco es gratis, y su coste está medido

| | `calculo` emitidos | contratos rotos |
|---|---|---|
| sin la línea | 0 de 5 consultas | 0 |
| con la línea larga (con ejemplo y mención al `null`) | — | **4 de 5** |
| con la línea corta (la que queda) | 2 de 5 consultas | 1 de 5 |

Y sobre la consulta que rompe (IVA, modo `corregir`), A/B con una sola variable: **7 de 10 corridas
chocan con el tope de 900 tokens**, contra **0 de 3** sin la línea. Mirando los crudos, **la avería
no es un bucle**: las corridas que terminan gastan 471–641 tokens con 8 y 9 afirmaciones, o sea que
el tipo nuevo simplemente alarga la respuesta y `MAX_TOKENS_CONTRATO = 900` se queda corto.

**CONSTRUIDO DESPUÉS, y con dos correcciones encima** (ADR 0017, `maxItems: 10`):

1. **La condición de la medida faltaba.** Los 7 de 10 son **sin fragmentos en contexto**. Por el
   camino real, con corpus, el desbordamiento es **0 de 6** (máximo 615 tokens, 5 afirmaciones):
   *sin material que citar el modelo se explaya; con material se ciñe a él*. Ver
   [`2026-08-13-abstencion-y-corregir.md`](2026-08-13-abstencion-y-corregir.md).
2. **Y el valor casi sale de la muestra equivocada.** Las 110 respuestas históricas van de 1 a 6,
   pero son **anteriores a que existieran los modos**: no contienen ni una derivación de `corregir`,
   que es el modo que desborda. Derivar el tope de ahí habría recortado justo lo que motivó el
   cambio — el principio 11 con la muestra elegida por **cuándo** en vez de por el síntoma, que en
   software es la forma que más vuelve.

Así que 10 es **provisional y declarado sin calibrar**, y es una **prohibición barata**, no el parche
de un fuego visto arder en producción.

### Hallazgo 3: la gramática fabricó un número falso, y se le creyó

La consulta de IPv4 devolvió `resultado_afirmado = "4.294967296"`, y el verificador lo podó. Pero la
prosa de **esa misma respuesta** decía `4.294.967.296`, que es correcto: lo que había pasado es que
el patrón `^-?\d+(\.\d+)?$` permite **un** punto y no dos, así que la decodificación restringida
fundió los separadores de millar en un decimal. **Un número gramatical y equivocado** — cuatro coma
tres en vez de cuatro mil millones.

El veredicto era `podada`, es decir *"el alumno se ha equivocado"*, cuando quien había roto el número
era nuestra propia gramática. Es el 7bis otra vez: **cuando el campo no admite la forma que el modelo
necesita, el modelo no se calla, deforma**.

- Decírselo en el `description` **no bastó**: se probó y volvió a escribir lo mismo.
- Arreglado en el **patrón**: `^-?\d+(,\d+)?$`, coma decimal. Los puntos de millar quedan
  ingramáticos desde el primer carácter, así que `4.294.967.296` sale `4294967296` —lo que se
  quería— y `302,50` sale tal cual. Comprobado sobre la misma consulta: ahora llega `4294967296` y
  sale `verificada exacta`.
- Y **segunda cerradura** en el verificador: un `resultado_afirmado` que no case con el patrón sale
  `no_verificable` (`resultado_mal_formado`), no `podada`. Un campo mal formado es un error de
  transporte, no un juicio sobre quien responde, y el que comprueba no se fía del que produce.

### Hallazgo 4: el modelo escribe los números en español también en `expresion`

Las tres respuestas que calcularon con decimales escribieron `250 + 52,5`. La coma decimal se
convierte **solo si la expresión no tiene ni una letra**: sin nombres de función una coma no puede
separar argumentos, así que solo puede ser decimal. Con letras (`binomial(7,2)`) no se toca nada.
Regla exacta, no heurística.

### Las cinco expresiones reales, y todas verifican

| expresión | afirmado | veredicto |
|---|---|---|
| `2^32` | `4294967296` | verificada (exacta) |
| `64 - 2` | `62` | verificada (exacta) |
| `7! / (2! * (7-2)!)` | `21` | verificada (exacta) |
| `250 * (21 / 100)` | `52,5` | verificada |
| `250 + 52,5` | `302,5` | verificada |

Notación que el modelo usa y que no estaba prevista: **`!` factorial** y **`^` potencia**. Las dos
funcionan (`factorial_notation` y `convert_xor` de sympy). Longitud de `expresion`: **4 a 18
caracteres**, contra un tope de 200 — el tope no muerde nada real, que es lo que se le pide.

**Y una limitación que se ve en `64 - 2`:** el modelo ya había calculado `2^6` de cabeza y solo
expuso la resta. El recálculo comprueba lo que la afirmación **enseña**, no lo que el modelo pensó.
Verificar `64 - 2 = 62` no verifica que en una `/26` quepan 62 equipos.

## 4. Lo que NO entra, dicho como lo que es

El **sandbox de ejecución de código no está construido**: es el peldaño 1 de la escalera de
contingencias de la guía, y se toma a propósito y con tiempo por delante, no por que se acabe el
domingo. De las cuatro cláusulas del criterio del 4.4:

- ✅ *"un cálculo correcto pasa"*
- ✅ *"uno incorrecto poda"*
- ❌ *"un código con bucle infinito muere por timeout sin tumbar el worker"* — del sandbox
- ❌ *"un código que intenta red falla"* — del sandbox

El código que llegue en `expresion` sale **`no_verificable`**, jamás `podada`. El momento 4 de la
demo queda cubierto igual porque el ejercicio desde el resultado **es aritmético**.

Deuda declarada, además del sandbox:

- **El tope de 900 tokens** y su arreglo por `maxItems` (hallazgo 2).
- **Una coma decimal en una expresión CON letras** (`Mod(302,5, 2)`) sale `no_verificable`. No se
  adivina: sería exactamente la interpretación que este verificador no hace.
- **La aritmética es exacta, no IEEE 754.** Una afirmación *sobre* el error de coma flotante
  (`0.1+0.2` no es `0.3`, que es una lección real de un temario de programación) se podaría. Sin
  datos de que ocurra; anotado para el 4.6.
