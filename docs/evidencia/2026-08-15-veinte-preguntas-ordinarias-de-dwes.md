# Evidencia: veinte preguntas ORDINARIAS de DWES, corridas DOS veces y leídas a ojo

**Fecha:** 15 de agosto de 2026 · **Casos:** `evals/casos/veinte_ordinarias_dwes.jsonl` ·
**Corredor:** `scripts/correr_preguntas.py` · **Corridas:**
[`…-veinte-ordinarias-dwes.json`](../../evals/corridas/2026-08-15-veinte-ordinarias-dwes.json) (argmax)
y [`…-cascada.json`](../../evals/corridas/2026-08-15-veinte-ordinarias-dwes-cascada.json) (cascada).

**Configuración:** anfitrión (uvicorn en el 8010, torch + CUDA), fusión 10:1:1, pool 30, **sin
reordenador** (ADR 0019), NLI enchufado, `PRESUPUESTO_CONSULTA_MS = 8.000`,
`OBJETIVO_CONSULTA_MS = 5.000`. **Titulación DAW, SIN asignatura elegida y SIN modo pedido** — el
camino que va a correr el lunes cuando alguien escriba lo suyo.

## Por qué esta medida existe

**Todo lo medido en este repo está sobre conjuntos CURADOS:** los 94 pares oro, los congelados de
modos, las cuatro sugeridas, el conjunto de calibración del NLI. Nadie había mirado nunca **qué
contesta el sistema a una pregunta cualquiera**, y el lunes alguien va a escribir la suya. Estas
veinte son preguntas normales del temario de segundo de DWES —ni trampas ni casos límite—, repartidas
por las ocho unidades, con dos que traen un intento del alumno porque eso también es ordinario.

**Lo que se busca es SABER, no arreglar.** El prompt está medido y tocarlo a dos días de la sesión es
rehacer una calibración de madrugada. Sale lo que sale y se ensaya sabiéndolo.

## Por qué hay DOS corridas, y qué se aprende de tenerlas

Entre una y otra cambió **cómo se elige el módulo cuando el alumno no elige ninguno**: la primera
versión hacía un *argmax* sobre una búsqueda ancha de las trece asignaturas; el propietario la paró
—los márgenes de confianza del 4.6 se calibraron DENTRO de una asignatura— y se sustituyó por
**empezar en el módulo con más material del ciclo y dejar que la cascada haga el resto**.

**Y tener las dos es lo que impide leer el ruido como señal**, porque el modelo no es determinista:

| | argmax | cascada |
|---|---:|---:|
| Contestan bien y de forma útil (a ojo) | **11 / 20** | **12 / 20** |
| No contestan debiendo hacerlo | 7 / 20 | 7 / 20 |
| Contestan MAL (peor que no contestar) | 2 / 20 | 1 / 20 |
| Repiten la misma idea | 5 / 20 | 4 / 20 |
| p50 / p95 | 4.024 / 8.010 ms | **3.498** / 8.022 ms |
| Cortadas a los 8.000 ms | 2 / 20 | 4 / 20 |

**Ninguna de esas diferencias es una mejora demostrada**: las preguntas cortadas son **distintas** en
cada corrida (`ord-07`,`ord-10` frente a `ord-01`,`ord-06`,`ord-15`,`ord-18`), o sea que **el corte es
varianza del proveedor y no una propiedad de la pregunta**. Con n=20 y una tasa del 10-20 %, dos
corridas no distinguen 2 de 4. Lo único sistemático que sí cambió: **la cascada manda las veinte a
DWES**, que es el módulo correcto, mientras el argmax mandó siete a otro sitio y tres de ellas se
quedaron sin respuesta por eso.

## Lo que se repite en LAS DOS corridas, que es lo único de fiar

1. **`ord-16` (SOAP vs REST) degenera las dos veces.** Las mismas tres frases repetidas hasta agotar
   los 900 tokens del contrato, JSON cortado y abstención. El motivo lo dice el propio sistema: *"el
   modelo llegó al tope de 900 tokens: JSON cortado, que es la firma del bucle degenerado"*. **Es la
   pregunta que no hay que hacer el lunes**, y es una pregunta de examen perfectamente normal.
2. **`ord-20` contesta MAL las dos veces.** El alumno enseña `SELECT * FROM usuarios WHERE
   user='$u' AND pass='$p'` y pregunta si está bien. **Nunca menciona la inyección SQL**, que es la
   respuesta entera. En la primera corrida dice que el fallo son los nombres de las columnas; en la
   segunda propone otra consulta **igual de inyectable**. Y el sistema sabe la respuesta: `ord-08`
   explica bien las consultas preparadas. Lo que falla no es el material, es que no conecta el
   ejercicio con él.
3. **`ord-02` (LAMP) no contesta las dos veces**, con la misma frase: *"no está en los fragmentos que
   tiene; sí está en el temario, en la unidad 9.2.1"*. Es honesto y es un fallo de recuperación: el
   material existe y no se recupera.
4. **`ord-11` (control de acceso) se corta a media frase las dos veces**, al llegar al tope de 900
   tokens del contrato. La prosa que sale es buena; termina en *"el navegador abre una"*.

## Y LO QUE VARÍA ENTRE CORRIDAS, que es lo más incómodo

**`ord-19` es el caso peligroso y sale distinto cada vez.** El alumno afirma algo falso —*"he puesto
que HTTP guarda el estado entre peticiones y que por eso funcionan las sesiones"*—:

- **argmax:** empieza bien (*"HTTP es un protocolo sin estado"*) y **termina dándole la razón**:
  *"Por lo tanto, tu afirmación de que HTTP guarda el estado entre peticiones **es correcta** en el
  contexto de que se utilizan mecanismos como cookies y sesiones"*. Un alumno que lea la última
  frase se va al examen con la idea falsa **confirmada por el sistema**.
- **cascada:** correcta. Dice que HTTP es sin estado y explica el mecanismo sin validar la premisa.

**No se puede decir que el segundo camino lo arregle: es la misma pregunta saliendo de dos maneras.**
Lo que sí se puede decir, y hay que decirlo con esas palabras: **el sistema falla de forma
intermitente justo en el caso que la sesión va a enseñar como su punto fuerte.**

Y hay algo peor que el error: en la corrida mala salieron **nueve afirmaciones y CERO frases
marcadas**, o sea que **la capa de verificación no tenía nada que objetar** — porque cada frase por
separado está respaldada por el temario y lo que falla es la **conclusión** que las une. **Esta
verificación comprueba afirmaciones, no razonamientos**, y este caso lo enseña mejor que ningún
documento.

## El prompt de `corregir` NO prohíbe explicar — comprobado corriendo, no leyendo

Era una de las tres condiciones del encargo del modo. Las cuatro líneas de `POR_MODO["corregir"]` no
llevan ninguna prohibición (a diferencia de `acompanar`, que tiene cuatro reglas duras con *"NUNCA"*),
y `ord-19` lo confirma **en el camino real**: clasificado `corregir` por `R1 + D1`, **corrige y
explica en el mismo turno** en las dos corridas. El desempate D1 —*"gana `corregir`: hay algo que
evaluar, y evaluarlo no impide explicar"*— funciona tal como está escrito. Que la conclusión sea a
veces errónea es otro problema, y está arriba.

## El clasificador de modo, en preguntas que no eran suyas

Idéntico en las dos corridas: **18 `responder`** (`R3` ×16, `D5` ×2, `D2` ×1) y **2 `corregir`**
(`R1` y `R1 + D1`), que son justo las dos que traen intento. **Cero desacuerdos con lo que yo habría
dicho leyéndolas.** Es su primer contacto con preguntas escritas **sin** la rúbrica delante.

## Latencia

| | argmax | cascada |
|---|---:|---:|
| p50 total | 4.024 ms | **3.498 ms** |
| p95 total | 8.010 ms | 8.022 ms |
| p50 del TTFT de prosa (lo que ve el alumno) | 2.645 ms | — |
| Por encima del **objetivo** de 5.000 ms | 7 / 20 = **35 %** | 7 / 20 = **35 %** |
| Cortadas por el **plazo** de 8.000 ms | 2 / 20 | 4 / 20 |

### ESTO NO BORRA EL SUSPENSO DEL README: LO CONFIRMA

La medida se hizo con la esperanza de que sí. El razonamiento era bueno —*"el objetivo de 5 s no
cumplido sale de medidas CON reordenador, y la única de la configuración real dio 2.315 ms"*— y **el
dato lo tumba**: en la configuración real, **el 35 % pasa de los 5 s en las dos corridas**. El p50 sí
cumple, así que la frase correcta tiene dos mitades y hay que decir las dos: **la mediana cumple, la
cola no.** La cifra vieja de 2.315 ms era **una consulta**, y una consulta no tiene p95.

**Y no se compara con el p50 de 2.858 ms del README**, que sale de 150 respuestas reales de la base:
**son dos poblaciones distintas** —aquélla incluye consultas con asignatura elegida, sugeridas y
pruebas cortas— y compararlas sería recomputar un número publicado sobre otra población. Cada una
lleva su n y su encuadre.

El paso de elegir módulo cuesta **0 consultas extra** desde la vuelta a la cascada (era 21,3 ms con
el argmax). **No es el problema**: el problema es la generación.

## Reproducirlo

```bash
python scripts/correr_preguntas.py evals/casos/veinte_ordinarias_dwes.jsonl \
    --titulacion daw --salida evals/corridas/2026-08-15-veinte-ordinarias-dwes-cascada.json
```

Las corridas guardan prosa, frases con su marca, afirmaciones con su veredicto, etapas con sus ms y
el fallo con su motivo, así que estas veinte se releen sin volver a gastar saldo.
