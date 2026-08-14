# Verificador literal (encargo 4.2): el barrido de normalización, y el 42 % que no cita

**13 de agosto de 2026.** `scripts/barrer_normalizacion.py` sobre las citas que ya había en la traza.
No gasta: todo es SQL local y comparación de cadenas.

## El denominador, declarado, y con los que no llegaron a compararse dentro

| | |
|---|---:|
| **Citas literales emitidas (denominador)** | **337** |
| Podadas por procedencia fabricada, **sin llegar a comparar** | **9** (2,7 %) |
| Comparables | 328 |
| Longitud de la cita | mediana **98**, min 8, máx **445** |

**Los 9 se cuentan y no desaparecen**, que es la regla escrita esta misma tarde: reportar sobre las
comparables haría que **cada poda subiera el porcentaje de aciertos**.

**Y esos 9 son un hallazgo por sí solos: el modelo cita fragmentos que no estuvieron en su
contexto.** No es hipotético: la puerta de `fragmento_en_contexto` no es una precaución teórica,
está parando algo que ocurre.

### Qué eran los nueve, que es donde el porcentaje se convierte en un arreglo

**Primero, la cuenta honesta: 9 OCURRENCIAS, 3 HALLAZGOS.** Las 337 citas salen de repetir las
mismas ~20 preguntas en varias corridas, así que las ocurrencias están infladas por repetición y el
2,7 % es una **tasa de ocurrencia**, no de casos distintos. Regla de la casa aplicada a mi propia
medida.

Los tres, leídos uno a uno:

| Caso | Veces | `fragmento_id` | Qué era de verdad |
|---|---:|---:|---|
| **A** | 4 | **45** | el número de una **pregunta de test** dentro del fragmento |
| **B** | 4 | **23** | ídem |
| **C** | 1 | **0** | el modelo intentando **abstenerse** |

**Los casos A y B son la misma avería, y está confirmada leyendo el corpus.** El fragmento 2936 —que
sí estaba en el contexto— contiene literalmente:

```
    C) Bean Validation (Hibernate Validator)
    D) MockMvc

45. Para activar la validación de un formulario en un método POST del Co…
```

Y la cita del modelo fue *"Para activar la validación de un formulario en un método POST del
Controller…"* con `fragmento_id: 45`. **Cogió el número que prefijaba la frase que estaba citando.**
Idéntico en B: el fragmento 2496 tiene `23. ¿Qué anotación debe usar un componente…`.

**No es una invención: es una confusión de referencias.** El modelo no se sacó un id de la nada —los
ids reales rondan los 2.500 y él escribió 45—; leyó *"esto es el 45"* en el texto y lo creyó. El
corpus tiene 223 fragmentos de tipo `enunciado_ejercicio`, todos numerados, así que la superficie de
este fallo es grande y conocida.

**Arreglo propuesto y NO construido** (decisión, no despiste): darle al modelo un identificador
**no confundible con una enumeración** —`F2936` en vez de `2936`—, que sigue siendo el id real con un
prefijo y por tanto **no introduce ninguna traducción**, que es lo que el 2.2 quería evitar. Cuesta
un cambio en el contexto, otro en el esquema y re-medir. Va con su número: cerraría **8 de las 9
ocurrencias y 2 de los 3 casos**.

**El caso C es otra cosa y apunta a otro sitio.** La cita era *"No se puede responder con los
fragmentos proporcionados."* con `fragmento_id: 0`. Eso no es una procedencia fabricada: es el modelo
**queriendo abstenerse** y no teniendo cómo, porque una afirmación `literal` exige `fragmento_id: int`
y no hay forma de decir "ninguno". Puso un 0 como quien pone un hueco. **Es un agujero del contrato,
no un fallo del modelo**, y su sitio es el **4.5** (política de respuesta), donde vive la abstención.
La puerta lo cazó igualmente, que es lo que tenía que pasar.

## El barrido: cada paso tiene que ganarse la entrada

| Nivel | Pasan | Ganancia | Veredicto |
|---|---:|---:|---|
| crudo | 179/328 | — | — |
| **espacios** | **195/328** | **+16** | **ENTRA** |
| espacios + tipográficos | 195/328 | **+0** | **NO ENTRA** |
| espacios + tipográficos + minúsculas | 197/328 | +2 | **NO ENTRA** (ver abajo) |

**La regla que decide es la asimetría, no el empate:** cada paso de normalización cambia un falso
negativo por un falso positivo, y **en un verificador el falso positivo es el caro**. Una cita
rechazada de más degrada a `parafrasis` y la comprueba el NLI: coste acotado. Una aceptada de más es
una fabricación pasando por verificada: **coste sin fondo**. Con esa asimetría, **la carga de la
prueba la tiene cada paso que se añade**, y un paso que no demuestre que compra algo no entra.

### Los tipográficos: +0. No entran

Nada que discutir: con n=328 no demostraron ganancia.

### Las minúsculas: ganaban 2, y las dos leídas una a una lo cambian todo

**No se estimó: se leyeron.** Y las dos difieren en exactamente lo mismo:

```
CITA     : La información que se almacena en la sesión de un usuario...
FRAGMENTO: la información que se almacena en la sesión de un usuario...
DIFIEREN : [('L', 'l')]

CITA     : Los datos que el usuario escribió se pierden para siempre.
FRAGMENTO: los datos que el usuario escribió se pierden para siempre.
DIFIEREN : [('L', 'l')]
```

**La letra inicial**, porque el modelo empezó la cita como si fuera una frase. O sea que bajar **todo
el texto** a minúsculas —y con ello aceptar `bindingresult` como cita literal de `BindingResult` en
un corpus medio código— compra **dos mayúsculas iniciales**. Y esas dos no se pierden: degradan a
`parafrasis` y el NLI las verificará sin esfuerzo, porque **son la misma frase**. Coste acotado, que
es el lado barato de la asimetría.

**Esto corrige la sección 8 de la guía**, que pedía "minúsculas" en la normalización. Corregida con
la medida delante y con el caso concreto escrito.

**Y las tildes: de las 133 que fallan, CERO casarían solo quitando acentos.** O sea que conservarlas
no cuesta nada medible, y el argumento para conservarlas queda en pie sin oposición: si el modelo
pierde un acento es porque está **reescribiendo**, y esa diferencia es la señal.

## El hallazgo que no se buscaba: la longitud predice el fallo

| | n | Mediana | Citas > 120 car |
|---|---:|---:|---:|
| **Pasan** | 195 | **42 car** | 66 |
| **Fallan** | 133 | **124 car** | 78 |

**Tres veces más largas las que fallan.** Y por tramos: **por encima de 120 caracteres falla el
54 %; por debajo, el 30 %.** Una cita más larga tiene más superficie donde equivocarse.

**Consecuencia: el tope de 120 en el esquema hace DOBLE trabajo** —abarata la respuesta *y* la hace
más comprobable—, y eso cambia cómo se justifica: ya no es solo una medida de latencia con un efecto
colateral aceptable, es una medida que mejora las dos cosas que este encargo mide.

**Es correlación y no experimento, y se dice.** Podría ser que las citas largas sean largas
*porque* el modelo estaba parafraseando, en cuyo caso la longitud es síntoma y no causa. El
experimento —capar y re-medir— es la corrida que valida la predicción del propietario, y va después.

## EL NÚMERO DE CABECERA: solo el 57,9 % de las citas literales lo son

> ### ⚠ RECONTADO EL 14/08/2026 EN LAS DOS UNIDADES — y aguanta
>
> **El 57,9 % se calculó contando FILAS**, y este mismo documento avisaba doce líneas más arriba de
> que *"las 337 citas salen de repetir las mismas ~20 preguntas"*: la regla de ocurrencias contra
> hallazgos se aplicó al recuento de procedencias fabricadas (**9 ocurrencias, 3 hallazgos**) **y se
> saltó justo en el número de cabecera**. Se recuenta ahora, con el predicado del 4.2 recomputado
> —comparación de cadenas, nivel `espacios`— y con la **clave declarada: `fragmento_id` + cita
> normalizada**, que es el par exacto que el verificador compara.
>
> **Las dos causas, separadas y nunca sumadas:**
>
> | | filas | **casos distintos** |
> |---|---:|---:|
> | base anterior al 14/08 (587 filas / 211 casos) | 372/586 = **63,5 %** | 120/210 = **57,1 %** |
> | base de hoy (627 filas / 231 casos) | 392/626 = 62,6 % | 129/230 = **56,1 %** |
>
> - **Por deduplicar** (mismo conjunto, dos unidades): **63,5 % → 57,1 %**, seis puntos y medio. La
>   repetición inflaba el número **a favor** del sistema.
> - **Porque la base ha crecido** (misma unidad, dos conjuntos): **57,1 % → 56,1 %**, un punto.
>
> **El titular sobrevive: cuatro de cada diez citas declaradas literales no lo son.** De hecho, en
> casos distintos es **un poco peor** que lo publicado. Lo que cambia es que ahora el número dice de
> qué unidad habla.
>
> **Dos avisos para quien lo repita:** (1) el 57,9 % publicado dividía **195** —numerador de la tabla
> de 328 comparables— entre **337** —todas las emitidas—, así que mezclaba dos denominadores;
> (2) la población de 337 era una foto de un momento del 13/08 que no se puede reconstruir exacta, y
> por eso arriba se recuenta sobre *todo lo anterior al 14/08*: **el parecido entre el 57,9 % viejo y
> el 57,1 % nuevo es una coincidencia de dos poblaciones distintas, no una confirmación.**

**195 de 337.** El **42 %** de las afirmaciones que el modelo declara `literal` **no aparecen
literalmente en su fragmento**. Es el número que este proyecto existe para producir, y es la primera
vez que se puede decir con una cifra en vez de con una intención.

### EL DAÑO NO ES QUE SEA INVENTADO: ES QUE LLEGA ETIQUETADO COMO CITA

Este es el encuadre que hace que el número duela **sin necesitar la palabra "alucinación"**, y es el
que se dice en voz alta.

**Una paráfrasis presentada como cita literal es una mentira sobre la PROCEDENCIA, aunque el
contenido sea correcto.** Un alumno que la copie en un examen creyendo que son **las palabras del
libro** se equivoca —y se equivoca precisamente por haberse fiado, que es lo peor que le puede pasar
a alguien que confía en una herramienta—. El sistema le habría dado información cierta con una
etiqueta falsa, y la etiqueta es la mitad del producto: sin ella, esto es un buscador; con ella
mintiendo, es un buscador que además engaña sobre su propia fiabilidad.

Es exactamente el mismo argumento que la guía ya usa con la **analogía marcada**: una analogía es
útil y es legítima, y por eso hay que decir que es una analogía y no el temario. Aquí igual: una
paráfrasis es útil y es legítima —y probablemente correcta en la mayoría de esas 133—, y por eso hay
que decir que es una paráfrasis y no una cita.

> **Y en presente, porque desde este encargo es verdad: el sistema NO PUEDE mentir sobre qué es una
> cita literal.** No "es poco probable que mienta" ni "el prompt le pide que no mienta": **no puede**,
> porque lo comprueba una comparación de cadenas sin ningún modelo en el lazo. Es la primera mitad de
> la tesis del proyecto, y está entregada.

**Cómo hay que leerlo, escrito antes de que nadie lo cite suelto:**

- **No es la tasa de alucinación.** Muchas de esas 133 serán paráfrasis correctas mal etiquetadas
  como literales — el modelo reescribió en vez de copiar y llamó a eso citar.
- **Por eso hoy DEGRADAN y no se podan** (decisión del interín, declarada antes de medir): el NLI
  del 4.3 dirá cuáles se siguen del fragmento y cuáles no. **Hasta entonces quedan `sin_verificar`,
  que no es un aprobado: es un pendiente.**
- **Y el número de poda SUBIRÁ al llegar el 4.3** sin que el sistema haya empeorado, porque parte de
  estas degradadas pasarán a podarse. Avisado de antemano para que no parezca una regresión.

## Reproducir

```bash
DATABASE_URL=... python scripts/barrer_normalizacion.py
```
