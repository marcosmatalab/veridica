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
alrededor de 1,2 s escribiendo la parte estructurada antes de llegar a la prosa. **Ese 1,2 s no es
un peaje: es el tiempo en el que el modelo se compromete con lo que va a afirmar antes de
redactarlo**, y la sección siguiente explica por qué no se recorta.

## La alternativa que parece obvia y NO es una palanca: reordenar el esquema

**Poner `respuesta_redactada` antes de `afirmaciones`.** Bajaría el TTFT del alumno de ~1.500 ms a
algo cercano a los ~300 del proveedor. Es la primera idea que se le ocurre a cualquiera que mire
estos números, y por eso hay que dejar escrito exactamente por qué no se hace.

**Con decodificación restringida, el orden del esquema no es una preferencia de formato: ES EL
ORDEN DE GENERACIÓN.** El decodificador obliga a la gramática token a token, así que el modelo
escribe los campos en el orden declarado, y cada campo se genera condicionado por lo que ya lleva
escrito. Con `afirmaciones` primero, la redacción se produce a partir de unos hechos que el modelo
ya se comprometió a sostener. **Invertido, el modelo escribe primero el texto que va a leer el
alumno y después rellena las afirmaciones que supuestamente lo sostienen.**

Eso no es un texto igual con las claves en otro sitio. Es una máquina distinta: las afirmaciones
dejan de ser aquello de lo que sale la respuesta y pasan a ser **justificación a posteriori de un
texto ya escrito**. Y una justificación a posteriori generada por el mismo que escribió el texto es,
palabra por palabra, el fallo que este proyecto existe para impedir: un sistema que decide qué decir
y luego busca con qué respaldarlo. La capa de verificación de la fase 4 seguiría comprobando esas
afirmaciones —y podrían pasar—, pero estaría comprobando el andamio, no el edificio.

**Así que no queda como palanca disponible con su precio: queda descartado.** El TTFT no es motivo
suficiente porque el TTFT no es el problema que este orden resuelve. Si alguien lo reabre, la
pregunta que tiene que contestar no es "¿cuánto ganamos de latencia?", es "¿aceptamos que la
respuesta se escriba antes que sus fundamentos?".

**Y el segundo y medio de pantalla en blanco es un problema real que se resuelve en otro sitio:** en
el **encargo 2.4**, enseñando las etapas reales mientras se espera —buscando en el temario, estos
fragmentos recuperados con su título— en vez de una barra girando. No es un truco de carga: es
trabajo que de verdad está ocurriendo, y de paso el alumno ve las **citas antes que el texto**, que
es justamente lo que este sistema quiere demostrar. La condición va escrita en el 2.4: lo que se
enseñe tienen que ser etapas medidas, jamás una animación de relleno.

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
