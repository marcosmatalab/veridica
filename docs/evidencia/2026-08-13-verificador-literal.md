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
contexto.** No es hipotético, no es un caso de laboratorio: pasa en el **2,7 %** de las citas reales.
La puerta de `fragmento_en_contexto` no es una precaución teórica — está parando algo que ocurre.

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

**195 de 337.** El **42 %** de las afirmaciones que el modelo declara `literal` **no aparecen
literalmente en su fragmento**. Es el número que este proyecto existe para producir, y es la primera
vez que se puede decir con una cifra en vez de con una intención.

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
