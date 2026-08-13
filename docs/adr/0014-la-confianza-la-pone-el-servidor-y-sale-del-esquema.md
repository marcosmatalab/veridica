# ADR 0014: `confianza_recuperacion` la pone el servidor, así que sale del esquema

- **Fecha:** 13 de agosto de 2026
- **Encargo:** 3.3 (la sección 7 de la guía se corrige aquí)
- **Estado:** aceptada

## Contexto

El contrato de la sección 7 incluye `confianza_recuperacion` entre los campos que el modelo escribe.
Con la recuperación construida (3.3), ese campo pasó a calcularlo el **servidor**: mide cuánto
destaca el primer candidato sobre el sexto, que es un hecho de la recuperación y no de la
generación. El modelo no puede saberlo —solo ve seis fragmentos, sin sus distancias y sin lo que
quedó fuera—, así que pedirle ese dato es pedirle una opinión sobre un trabajo que no ha hecho.

La primera versión lo dejó **en el esquema** y el servidor lo sobrescribía después. Y eso es un
fallo de los que este repo ya tiene nombre puesto.

## Decisión

**`confianza_recuperacion` sale del `json_schema` que se le envía al modelo.** Sigue existiendo en
el contrato que SALE —viaja en el evento `afirmaciones`, en el `fin` y en la traza—, pero lo escribe
el servidor.

Al modelo se le sigue **diciendo** el valor, y para algo distinto: para que ajuste su comportamiento
—si la confianza es baja, que lo diga en la redacción en vez de rellenar—. Decírselo sirve; dejarle
escribirlo, no.

## Por qué, y es el principio 7 una planta más arriba

**Un campo que existe en la gramática es un campo que el modelo puede rellenar.** Esa es la lección
del 2.2, donde `cita` aparecía en afirmaciones de tipo `conocimiento` porque el esquema se lo
permitía, y se arregló partiendo el esquema en variantes en vez de insistir en el prompt. Aquí es lo
mismo un nivel por encima: no es un campo mal usado dentro de una variante, es un campo entero que
**no le corresponde al productor**.

Dejarlo en el esquema tenía dos costes, los dos reales:

1. **Se pagan tokens por una opinión que se descarta.** Salida tipada significa que el decodificador
   genera ese campo token a token, y luego el servidor lo tira.
2. **Deja una inconsistencia latente para quien lea el contrato.** Un campo que el modelo escribe y
   alguien sobrescribe después es una trampa esperando a que un cambio futuro invierta el orden y
   nadie se entere: el valor seguiría siendo válido y seguiría siendo el equivocado.

## Trade-off

El contrato de la sección 7 deja de ser una sola estructura: hay lo que **produce** el modelo y lo
que **emite** el servidor, y el segundo es el primero más los campos que el servidor sabe. Es un
concepto más que explicar, y se acepta porque la alternativa —que el productor rellene campos que no
puede conocer— es peor y ya se ha cobrado un fallo.

Y queda la regla generalizada para los campos que vengan: **antes de meter un campo en el esquema,
preguntarse si el modelo tiene con qué saberlo.** Si la respuesta es no, el campo es del servidor.
