# ADR 0016: el resultado afirmado es un campo del contrato, y es una cadena con coma decimal

- **Fecha:** 13 de agosto de 2026
- **Encargo:** 4.4 (verificador de cálculo)
- **Estado:** aceptada
- **Evidencia:** [`docs/evidencia/2026-08-13-verificador-calculo.md`](../evidencia/2026-08-13-verificador-calculo.md)

## Contexto

Hasta el 4.4, una afirmación de tipo `calculo` traía solo `expresion`. El resultado que el modelo
**afirma** vivía dentro de la prosa: *"hay 7 combinaciones posibles"*. Para verificar un cálculo hay
que comparar lo recalculado con lo afirmado, así que con ese contrato el servidor tendría que
**extraer el número del texto**.

Esa extracción es un paso nuevo, sin verificar, metido justo dentro del verificador. Y no es un
riesgo teórico: es el fallo del `F2936` visto desde el otro lado del cable. Allí el modelo leyó un
número dentro de un texto (`45. Para activar la validación…`) y lo creyó suyo; aquí lo leería el
servidor. Un verificador cuya primera operación es una heurística no verificada no verifica: traslada
el problema una capa.

## Decisión

**1) El resultado afirmado es un campo del contrato**, `resultado_afirmado`, en
`AfirmacionCalculo`. La comparación pasa a ser número contra número y no hay ninguna extracción. La
regla de cobertura del 4.5 sigue atando el `texto` de la afirmación a la prosa, así que no se pierde
la conexión con lo que el alumno lee.

**2) Es una CADENA, no un número.** Aquí está lo que se decidió de verdad, y el motivo tiene dos
mitades:

- **La precisión escrita es un dato, y un `float` la borra.** La tolerancia del 4.4 se deriva de *los
  decimales que el modelo escribió*: `2/3` afirmado como `0,7` es correcto con un decimal, y afirmado
  como `0,70` es incorrecto con dos —porque con dos, lo correcto es `0,67`—. Los dos son **el mismo
  `float`**. Con un campo numérico, el dato que decide el veredicto se pierde al parsear, y la regla
  de tolerancia se queda sin su entrada.
- **Y por encima de 2^53 un `float` deja de representar los enteros uno a uno.** En un temario con
  combinatoria eso no es teórico: `20!` tiene 19 cifras y `2**100` tiene 31.

El `pattern` hace **ingramático** cualquier valor que no sea un número —principio 7, igual que la `F`
del `fragmento_id`—: la forma escrita sobrevive intacta y aun así no puede llegar basura. El servidor
la parsea con `Rational`/`Decimal`, que no tienen techo.

**3) Y el separador decimal es la COMA, que es lo que arregla un fallo medido y no una preferencia
de estilo.** Con el punto, el modelo quiso escribir `4.294.967.296` —correcto en español, y así salió
en la prosa de esa misma respuesta— y la decodificación restringida, que permite **un** punto y no
dos, dejó **`4.294967296`**: cuatro coma tres en vez de cuatro mil millones. Un número **gramatical y
equivocado**, que es la peor clase de salida porque no falla, miente; y el veredicto era `podada`, o
sea *"el alumno se ha equivocado"*, cuando quien había roto el número era nuestra propia gramática.
**Decírselo en el `description` no bastó: se probó y el modelo volvió a escribir lo mismo.** Con la
coma, los puntos de millar son ingramáticos desde el primer carácter, así que `4.294.967.296` sale
`4294967296` —lo que se quería— y `302,50` sale tal cual: no queda ambigüedad que resolver, porque
solo hay un separador y solo significa una cosa. Comprobado sobre la misma consulta que lo destapó.

Y de aquí sale una distinción que vale para todo el proyecto: **el `description` de un campo no
decide qué rama elige el modelo, pero sí guía lo que escribe dentro de un campo al que ya ha
llegado.** Las dos mitades están medidas, cada una con su caso.

**4) `null` significa "mi resultado no es un número"**, y se le cree: sale `no_verificable`, no
`podada`. Es el principio 7bis al derecho — se le da forma de decirlo para que no tenga que deformar
el único campo que tenga a mano.

## Trade-off

- **Se paga** un campo más en cada afirmación de cálculo (tokens de salida), y que el servidor tenga
  que parsear una cadena en vez de recibir un número ya tipado.
- **Se gana** que la verificación de cálculo sea una comparación y no una interpretación; que la
  precisión afirmada sea auditable; y que los enteros grandes se comparen exactos.
- **Lo que se descarta y por qué**: `float` pierde la precisión escrita y el rango exacto (arriba).
  Extraer el número de la prosa con una expresión regular mete un paso no verificado dentro del
  verificador. Un campo `número o cadena` (unión) duplicaría las ramas de la gramática sin ganar
  nada, porque el patrón ya deja pasar exactamente los números.

## Consecuencia que hay que vigilar

`resultado_afirmado` **no lleva `maxLength`**, y `expresion` tampoco. En `expresion` es deliberado:
ese campo lleva también el **código** del caso que el 4.4 deja declarado y no construido, y un tope
en la gramática obligaría a deformarlo (7bis otra vez). El coste de una expresión larga lo acota el
verificador —200 caracteres, y lo que no cabe sale `no_verificable`—, que es donde sabe distinguir
una expresión de un programa.
