# ADR 0009: el evento `token` lleva prosa, y por eso hay DOS TTFT

- **Fecha:** 12 de agosto de 2026
- **Encargo:** 2.2
- **Estado:** aceptada

## Contexto

La sección 10 dice que `/consulta` responde por SSE con eventos `ttft`, `token`, `afirmaciones` y
`fin`, y que **el TTFT medido es el que ve el alumno**. La sección 7 dice que el generador produce
un objeto JSON tipado. Las dos cosas a la vez abren un problema que ninguna de las dos menciona.

**Con salida tipada el modelo no emite prosa: emite un JSON.** El primer token que manda el
proveedor es `{`. O sea que hay dos tiempos distintos donde el proyecto tenía escrito uno:

| | Qué es | Quién lo ve |
|---|---|---|
| `ttft_proveedor_ms` | primer token del JSON | nadie: es una llave |
| `ttft_prosa_ms` | primer carácter de `respuesta_redactada` emitido por `token` | **el alumno** |

Y de ahí salían dos salidas malas, las dos silenciosas:

1. **Esperar al objeto entero, validarlo y emitir.** El TTFT del alumno pasa a ser igual al total y
   el streaming no compra nada: se paga la complejidad del SSE para tener una respuesta de golpe.
2. **Emitir el JSON crudo por `token`.** El alumno ve llaves, comillas y nombres de campo, y la
   interfaz tiene que limpiarlo por su cuenta, con lo cual el problema no se resuelve, se muda.

## Decisión

**Se emite SOLO la prosa, extraída del JSON parcial según llega** (`app/core/prosa_parcial.py`), y
`afirmaciones` se emite cuando el objeto cierra y valida en forma. **Se miden y se guardan los dos
TTFT**, con nombres distintos, en el evento `ttft`, en el `fin` y en `respuestas.etapas`. La columna
`respuestas.ttft_ms` guarda el de la prosa, que es el que manda la sección 10.

El extractor es un autómata carácter a carácter, no una expresión regular: `"respuesta_redactada"`
aparece también **dentro** de otros valores —una `cita` del temario, por ejemplo— y un buscador de
subcadenas emitiría como respuesta al alumno lo que no lo es. Hay test con esa trampa dentro de una
cita y dentro del `siguiente_paso`.

### Lo medido, que es lo que hace que esta decisión valga la pena

| | ms |
|---|---:|
| TTFT del proveedor | ~300 |
| TTFT de la prosa | ~1.500 |
| Total | ~2.300 |

**La prosa empieza a los 1,5 s y la respuesta acaba a los 2,3 s: el streaming adelanta unos 0,8 s
de los 2,3.** Menos de lo que adelantaría en texto libre, y con un motivo concreto: en el contrato
de la sección 7 las `afirmaciones` van ANTES de `respuesta_redactada`, así que el modelo se pasa
alrededor de 1,2 s escribiendo la parte estructurada antes de llegar a la prosa.

## Alternativa descartada, con su cuenta hecha

**Poner `respuesta_redactada` primero en el esquema.** Con salida restringida el modelo emite las
claves en el orden declarado, así que mover ese campo al principio bajaría el TTFT del alumno de
~1.500 ms a algo cercano a los ~300 del proveedor. Se descarta hoy porque **el orden del contrato
es el orden del razonamiento**: primero se declara lo que se afirma y después se redacta el texto
que lo hila. Invertirlo hace que el modelo escriba la prosa antes de haberse comprometido con las
afirmaciones, que es justo lo que este proyecto no quiere, y hacerlo *para que la demo parezca
rápida* es la peor razón posible para tocar un contrato.

Queda escrito como **palanca disponible con su precio**: si el TTFT llega a ser el problema, se
cambia el orden y se declara que la redacción ya no está condicionada por las afirmaciones. Es una
decisión de producto, no un ajuste.

## Trade-off, que es real y se asume con los ojos abiertos

**La prosa sale antes de que el objeto cierre y valide.** Si el JSON acaba roto después de haber
emitido texto, ese texto ya está en pantalla:

- El **reintento único** de la sección 7 ya no se puede usar: repetir la llamada le repetiría al
  alumno lo que acaba de leer. Se emite `abstencion` con `ya_habia_prosa_en_pantalla: true` y la
  interfaz retira lo emitido. El reintento queda para el caso en que aún no ha salido nada.
- El cliente de inferencia lleva la misma regla un piso más abajo: **reintenta los errores
  transitorios solo mientras no haya emitido**. Los dos casos tienen test.

Y una advertencia para la fase 4, que hereda esto: lo que sale por `token` es prosa **anterior a la
verificación**. Cuando exista el verificador, una afirmación podada llegará después de que su frase
ya se haya leído. Eso lo resuelve el 4.5 decidiendo qué hace la interfaz con lo podado; aquí solo se
deja dicho que el problema existe y de dónde viene.

## Lo que este endpoint NO hace, escrito donde no se pueda malinterpretar

`/consulta` comprueba la **forma** del contrato: que el JSON es el de la sección 7. **No comprueba
la verdad de nada.** Por eso cada afirmación sale y se guarda con `veredicto: "sin_verificar"`, y
por eso `afirmaciones.veredicto` es `NOT NULL` en la base: para que "validado" no se pueda leer como
"verificado". La verificación es la fase 4 (encargos 4.2 a 4.5) y es independiente por diseño, que
es el principio 6: aquí el que produce el texto es el proveedor, y el que comprueba somos nosotros;
en la fase 4, donde produciríamos nosotros, el verificador tendrá que venir de fuera.
