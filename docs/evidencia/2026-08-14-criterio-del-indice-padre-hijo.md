# Criterio de entrada del índice padre-hijo, escrito ANTES de construirlo y ANTES de medir

- **Fecha:** 14 de agosto de 2026
- **Encargo:** paso 4 del plan del propietario (índice padre-hijo), **no construido todavía**
- **Estado de este documento:** es un **criterio pre-escrito**, no un resultado. Aquí no hay ningún
  número medido del índice porque el índice no existe.

## Por qué se escribe ahora y no cuando haya tabla

Es la disciplina de siempre —el desempate se escribe antes de ver el resultado—, con un motivo
extra: el propietario ya corrigió una vez la formulación de este criterio, y la corrección **es** el
contenido del documento. Escribirlo después habría sido escribirlo sabiendo lo que salió.

## EL CRITERIO, en las palabras del propietario

> **ENTRA si al menos 5 preguntas NETAS de 94 ganan fragmento relevante en el pool, Y las que lo
> PIERDEN son 2 o menos. Se reportan las tres cifras siempre: ganadas, perdidas y neta.**

## Por qué NO se enuncia en puntos porcentuales, que es lo que yo había escrito

Mi versión decía *"si el techo del pool sube menos de X puntos, no entra"*. Está mal, y por dos
motivos que se ven juntos:

1. **A n=94, cinco puntos entre dos proporciones son apenas un error estándar.** Un criterio escrito
   en puntos no distingue mejora de ruido: aprobaría un cambio que no ha hecho nada y rechazaría uno
   que sí, según de qué lado caiga el muestreo.
2. **La comparación es PAREADA** —las mismas 94 preguntas en las dos configuraciones— y eso es
   mucho más sensible que comparar dos proporciones sueltas. Contar **qué preguntas concretas
   cambian de estado** usa esa estructura; una diferencia de medias la tira.

## Y la condición que faltaba en mi versión: las PÉRDIDAS, contadas aparte

La segunda mitad del criterio es la que importa y no estaba: **si gana 8 y pierde 6, la neta dice
+2 y la verdad es que la recuperación se ha vuelto inestable.** Eso no es una mejora, es agitación,
y **con la neta sola no se ve** — es exactamente el agregado promediando y disolviendo la estructura
que señalaba la causa, una vez más.

Por eso **las tres cifras se reportan siempre**, incluso si el resultado es bueno: *ganadas*,
*perdidas*, *neta*. Un informe que solo publique la neta habrá escondido la mitad del hecho.

## Lo que este criterio decide y lo que no

- Decide si el índice padre-hijo **entra en la recuperación**.
- **No** decide nada sobre latencia, tamaño del índice ni coste de embebido: esos se miden y se
  declaran aparte, y pueden vetar por su cuenta.
- Se aplica sobre el **techo del pool** primero (¿está el fragmento relevante entre los candidatos?),
  porque si el techo no sube, lo demás no tiene de dónde ganar y el trabajo se para ahí.

## Orden, decidido por el propietario y por procedimiento

**Juez → ventana → índice.** No es prisa: es *se calibra sobre el instrumento arreglado, nunca sobre
el roto*. Construir el índice primero y cambiar el juez después obligaría a re-calibrar dos veces, y
la primera no habría valido.
