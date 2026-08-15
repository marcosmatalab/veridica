# Rúbrica de clasificación de modo — ESCRITA ANTES DE LAS PREGUNTAS

Se aplica al **turno del alumno**, solo a su texto. No se adivina intención: se leen rasgos.

- **R1.** Si el turno **CONTIENE o DECLARA** un resultado, una respuesta o un intento del alumno → `corregir`.
  Aplica aunque esté redactado como pregunta ("¿está bien esto?") y aunque el intento no venga pegado,
  siempre que el turno afirme que existe ("esto que he hecho", "mi código").
- **R2.** Si el turno pide ayuda para **resolver un ejercicio concreto** y NO contiene ni declara intento → `acompanar`.
- **R3.** Si el turno pregunta por un **concepto, definición, diferencia o funcionamiento** → `responder`.

## ORDEN DE EVALUACIÓN — añadido el 14/08/2026, y es lo que faltaba

**Los desempates se evalúan ANTES que las reglas generales**, en este orden:

```
R1 (con D4 dentro)  →  D6  →  D2  →  R2 (con D3 dentro)  →  R3  →  D5
```

**Y la lección va aquí porque es del enunciado y no de la implementación:** esta rúbrica listaba
tres reglas y seis desempates **sin decir en qué orden se evalúan**, y la ambigüedad **solo apareció
al implementarla** — el ejemplo de D2 (*"es para el ejercicio 5"*) únicamente se cumple si D2 se
mira antes que R2, y con R2 delante salía `acompanar`, que es justo lo que D2 existe para impedir.
**Una rúbrica sin orden de evaluación no es una especificación: es una lista**, y dos personas que
la implementen pueden cumplirla entera y no coincidir.

## Desempates, escritos antes de etiquetar

- **D1.** Intento presente **y** pregunta de concepto → **`corregir`**. R1 gana: hay algo que evaluar,
  y evaluarlo no impide explicar.
- **D2.** "Cómo se hace X" **en general**, sin ejercicio concreto → **`responder`**. Un ejercicio mencionado
  como contexto ("es para el ejercicio 5") no lo convierte en `acompanar`.
- **D3.** Pide la solución de un ejercicio concreto sin traer intento → **`acompanar`**.
  Que pida la solución es asunto de la POLÍTICA DEL MODO, no del clasificador: `acompanar` ya sabe
  no darla. Clasificar como `responder` para poder soltarla sería usar el clasificador para esquivar
  la regla pedagógica.
- **D4.** El turno usa la palabra "corregir" pero **no hay intento** → **`acompanar`**. Manda el rasgo, no el verbo.
- **D5.** Ninguna señal de las tres → **`responder`**, por ser el modo menos intrusivo.
- **D6.** Pide que le EXAMINEN o que le pongan un ejercicio → el modo `examinar` está DISEÑADO Y NO
  CONSTRUIDO, así que cae a **`responder`** por D5, y el sistema debe decir que ese modo no existe.
- **D7.** *(Añadido el 14/08/2026, tras el desacuerdo de `modo-43`.)* **El intento cuenta cuando
  ESTÁ AQUÍ; no cuenta cuando LO ÚNICO QUE HAY está prometido para luego.** Un turno que solo
  anuncia un intento futuro (*"…y luego te enseño lo mío"*) **no** es `corregir`: el clasificador
  clasifica **este turno**, y en este turno no hay nada que evaluar. Sigue por R2/R3/D5 según pida.

  **La redacción es la segunda, y la primera se deja escrita porque es la que enseña.** Decía *"el
  intento existe y SE SOMETE AHORA"*, y llevada a código anulaba un intento **real** por el mero
  hecho de mencionar el futuro: *"Mira mi código, y **luego** te paso el siguiente ejercicio"*
  somete trabajo ya, y salía `responder`. El rasgo que discrimina el **caso mixto** no es *"se habla
  del futuro"* sino ***"lo único que hay está prometido"***: si alguna señal de intento aparece
  **antes** de la promesa, ese intento está aquí. Lo cazó el test de la dirección contraria, que es
  para lo que existen.

  **Por qué se añade y no se "aclara" R1 en silencio:** R1 decía *"aunque el intento no venga
  pegado, siempre que el turno afirme que existe"*, y esa redacción **permitía** la lectura
  contraria — la implementación la siguió y salió `corregir`. El desacuerdo estaba **declarado por
  escrito antes de abrir las etiquetas**, así que lo que se discutió fue la regla y no el gusto,
  que es exactamente para lo que la rúbrica se escribió antes. La regla se corrige; la lectura que
  la descubrió no era un error de lectura.
