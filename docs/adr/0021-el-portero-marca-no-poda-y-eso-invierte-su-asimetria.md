# ADR 0021: el portero de frases MARCA en vez de podar, y eso INVIERTE la asimetría de su umbral

- **Fecha:** 14 de agosto de 2026
- **Encargo:** 4.5 (revisado), con consecuencia directa sobre el umbral #3 del 4.6
- **Estado:** aceptada
- **Decisión del propietario**, con su argumento; aquí queda la consecuencia medida y lo que obliga

## Contexto

El portero del 4.5 comprueba, frase a frase mientras se escribe, que la prosa esté respaldada por
las afirmaciones declaradas. Hasta hoy, una frase por debajo de `SOLAPE_MINIMO` **se podaba**: no
llegaba al alumno. Eso producía tres defectos de experiencia —párrafo con salto, respuesta comida,
y en el límite pantalla en blanco— y obligó a añadir una abstención propia (`sin_prosa_respaldada`)
para que el caso extremo no se contara como respuesta entregada.

## Decisión

**La frase por debajo del umbral se emite SEÑALADA en lugar de desaparecer.** El evento `token`
viaja con `respaldada` y `solape`; la interfaz la pinta con marca visible **por forma** —símbolo,
subrayado ondulado y barra lateral— y no solo por color.

El argumento, del propietario y en sus términos: **la promesa del proyecto es que nada llegue al
alumno sin etiquetar, y marcar ES etiquetar. Podar, además de dejar un agujero, oculta que el
modelo lo dijo** — que es menos honesto y encima peor de leer.

## Trade-off

- **Se gana**: el defecto de experiencia se va a **cero por construcción** —ninguna frase se pierde,
  y hay un test que ancla exactamente eso—. El umbral deja de decidir **si** el alumno ve algo y
  pasa a decidir **cómo** lo ve; un umbral mal puesto ya no puede mutilar una respuesta.
- **Se paga**: el alumno lee texto no respaldado (señalado). Es el precio de no esconderlo, y es
  coherente con el resto de la casa: se declara lo que no se puede verificar en vez de retirarlo.
- **Y se paga una segunda vez, en el sitio menos obvio**: las marcas son ruido si son muchas. Marcar
  de más es barato, pero **marcar todo es no marcar nada**, así que el umbral sigue importando —
  solo que por otro motivo.

## LA CONSECUENCIA QUE HAY QUE ESCRIBIR ANTES DEL BARRIDO: LA ASIMETRÍA SE DA LA VUELTA

| | Cuando PODABA (hasta el 14/08) | Ahora que MARCA |
|---|---|---|
| **Falso positivo** — frase sin respaldo que pasa el umbral | contenido no declarado dentro de la respuesta | **EL CARO**: contenido no declarado llegando al alumno **con aspecto de respaldado** |
| **Falso negativo** — frase legítima por debajo del umbral | **EL CARO**: se llevaba la frase de un texto que alguien está leyendo, medido | cosmético: una marca injusta sobre una frase correcta |

**Consecuencia operativa: la dirección de calibración se INVIERTE.** Con el portero podando, el
0,50 no se podía subir sin mutilar más; con el portero marcando, **el lado seguro es subirlo**,
porque lo que ahora sale caro es dejar pasar sin marca. El barrido del umbral #3 del 4.6 se hace
con **esta** tabla delante, no con la del 4.5 original.

**Y el valor actual no se hereda.** 0,50 fue una respuesta a la pregunta *"¿cuánto puedo exigir sin
mutilar?"*, y la pregunta de hoy es *"¿cuánto puedo exigir sin dejar pasar sin marca?"*. Que el
número siga sirviendo, si sirve, hay que volver a demostrarlo.

## La regla general, que es la tercera vez que se paga

**UN NÚMERO NO LLEVA DENTRO SU PROPIA JUSTIFICACIÓN.** Cuando cambia lo que el mecanismo HACE, su
calibración anterior no se hereda aunque el valor siga sirviendo: lo que se calibró fue una
respuesta a *"¿qué error es el caro?"*, y esa pregunta acaba de cambiar de respuesta. Van tres —el
4.2 (falso positivo caro), el 4.3 heredándolo, y este dándole la vuelta— y por eso sube al
Apéndice A.

## Lo que NO se retira, y por qué

`sin_prosa_respaldada` **se re-condiciona en vez de retirarse** (corrección del propietario al
plan). Con el portero marcando, esa abstención ya no puede saltar por poda —no hay poda—, pero el
caso de **prosa vacía** sigue existiendo: el modelo cumple el contrato y no escribe redacción. Sin
esa rama, ese caso volvería a ser una pantalla en blanco sin declarar, que es el fallo que costó
medio día encontrar el 14/08. **Cambia el disparador (`caracteres_emitidos == 0`), se conserva la
salida**, y el test cubre el disparador nuevo.

El campo `por_cobertura` del evento de abstención pasa a llamarse `por_prosa_vacia`; el nombre
viejo se conserva un tiempo con su valor y con un aviso, porque hay corridas guardadas y un script
(`medir_corregir.py`) que lo leen — pero **su significado ya no es el que su nombre dice**, y eso
se declara donde se lee.
