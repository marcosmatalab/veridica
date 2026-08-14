# Evidencia: la traza completa (encargo 2.5), y las dos correcciones al 4.6 que salieron al construirla

- **Fecha:** 14 de agosto de 2026
- **Encargo:** 2.5, movido detrás de la fase 4 el 13/08 con su motivo escrito
- **Rama:** `traza-completa`

## 1. El criterio de cierre, cláusula a cláusula

El enunciado dice literal: *«`GET /trazas/{id}` reconstruye todo. Verificación: para una consulta
cualquiera, la traza responde a "qué se recuperó, qué se afirmó, qué veredicto tuvo cada afirmación,
cuánto costó cada etapa"»*. Son **cuatro preguntas**, y la respuesta tiene **cuatro claves con esos
nombres** para que el criterio se compruebe leyendo en vez de interpretando.

| cláusula | dónde se cumple | comprobado |
|---|---|---|
| `GET /trazas/{id}` | `app/api/trazas.py` | consulta real 392, HTTP 200 (§3) |
| qué se recuperó | `que_se_recupero` | 6 fragmentos con sus ids, pool, confianza y enlace para abrir cada uno |
| qué se afirmó | `que_se_afirmo` | 4 afirmaciones con tipo, cita, apoyo y `fragmento_en_contexto` |
| qué veredicto tuvo cada afirmación | `que_veredicto_tuvo_cada_afirmacion` | veredicto **y firma del instrumento**, con reparto partido por firma |
| cuánto costó cada etapa | `cuanto_costo_cada_etapa` | 9 marcas medidas, TTFT 3.028 ms, total 3.963 ms, 0,000667 EUR |
| *para una consulta cualquiera* | camino real | consulta nueva contra el proveedor, no un caso plantado (§3) |

**Lo que el endpoint NO hace, y es una decisión:** no recalcula nada. Un veredicto recomputado hoy
sobre una respuesta de la semana pasada usaría los umbrales de hoy — sería una medida de otra
configuración con aspecto de registro histórico, el error viajando en el sumando dentro de la propia
vitrina. La traza lee y junta; nada más.

## 2. Las dos correcciones al 4.6, que solo aparecieron al ir a construir

El 4.6 cerró con tres umbrales SIN CALIBRAR y un motivo escrito para cada uno. Dos de esos motivos
**eran inexactos**, y la inexactitud solo se vio al abrir la base para barrer:

| umbral | lo que dijo el 4.6 | lo que hay de verdad |
|---|---|---|
| `SOLAPE_MINIMO` (4.5) | *«la prosa no se persiste — sin denominador no hay barrido»* | **el denominador SÍ estaba** (204 respuestas con frases emitidas y huérfanas contadas). Lo que faltaba era el **valor**: el solape de cada frase. Con solo el de las huérfanas, el umbral se puede **bajar** con datos pero no **subir**, porque de las emitidas no se guardaba cuánto solapaban |
| ritmo (3.4bis) | *«el ritmo por consulta no se persiste»* | **330 de 391 respuestas lo llevan**. Pero el campo guardado es el ritmo de la **última ventana**, y el umbral pregunta por el **peor momento**: dos preguntas distintas en el mismo número |

**Las dos son la misma familia** —un contador contestando a la pregunta con la que se escribió, no a
la que se le hace después— y ninguna se veía desde fuera: el 4.6 miró si el dato existía, no si el
dato contestaba. Desde este encargo se persisten los dos que faltaban:

- `cobertura.solapes`: una fila por frase juzgada con `{solape, emitida, corta}`. **`corta` separa el
  pase POR DISEÑO** (frases de menos de tres palabras de contenido pasan siempre: podar *"Vale."*
  sería el falso negativo por construcción) del pase por solape. Sin esa marca, el barrido contaría
  como aprobados unos pases que el umbral nunca decidió.
- `ritmo.minimo_observado`: el peor ritmo visto en toda la consulta, anotado **antes** de decidir si
  se corta — si se anotara después del corte, las consultas que el vigilante mata no dejarían su
  peor momento en ninguna parte y la muestra volvería a estar elegida por el éxito.

**Los dos umbrales siguen SIN CALIBRAR**, y su procedencia lo dice con el diagnóstico corregido: lo
que faltaba ya no falta, pero el barrido necesita consultas nuevas que traigan el dato. Se calibran
cuando haya n, no antes.

## 3. La consulta real, de punta a punta (respuesta 392)

Corrida contra el proveedor con el código de esta rama, en un proceso propio arrancado en un puerto
nuevo y confirmado **por su propio log** (`Application startup complete`), no por si el puerto
contestaba — la lección de la media tarde perdida con un uvicorn viejo.

```
fin: respuesta_id 392, ttft_prosa 3.028 ms, total 3.963 ms
     verificacion: {construido: true, solicitada_tiene_efecto: false}, traza: /trazas/392
recuperacion: 6 fragmentos, pool 30, confianza "media" (top1 0,6522, margen 0,055)
veredictos:   4 sin_verificar (las cuatro afirmaciones son `conocimiento`)
cobertura:    4 frases emitidas, 0 huérfanas, solapes 1,0 / 0,875 / 1,0 / 1,0
ritmo:        415 tokens, última ventana 146,0 tok/s, mínimo observado 142,5 tok/s
coste:        0,000667 EUR
```

## 4. Cuatro `false` persistidos que la vitrina iba a enseñar, y estaban mal

Construir la traza obligó a mirar lo que se guarda, y ahí aparecieron:

1. **`verificacion.construido: false` en las 391 respuestas de la base**, con el 4.2, el 4.3, el 4.4
   y el 4.5 corriendo en cada consulta desde el 4.4. Un `false` persistido se lee como una medida:
   cualquier consulta sobre esa columna diría *"aquí no se verificó nada"*. Corregido para las filas
   nuevas; **las viejas no se reescriben** —sería falsear el registro— y la traza las sirve con un
   `aviso_fila_vieja` que explica por qué dicen lo que dicen.
2. **El gemelo del evento `fin`**, que además decía *"no hay capa de verificación que apagar hasta la
   fase 4"*.
3. **`/api`** anunciaba `/trazas/{id}` como no construida (correcto hasta hoy) y avisaba de que *"toda
   afirmación viaja con veredicto sin_verificar"* (falso desde el 4.4). **Un aviso envejece igual que
   un documento, y este además se sirve por HTTP**: quien lo leyera dejaba de mirar.
4. **`confianza_recuperacion` decía `calibrado: false`** con sus umbrales ya calibrados en el 4.6
   (0,085 / 0,025 / 0,664, corrida 33): las constantes se movieron y la bandera no. Es el `false`
   persistido **al revés** —declarar sin calibrar lo que sí lo está— y se arregla con la misma regla:
   el número y su límite viajan juntos (aquí, medido solo sobre DWES).

## 5. Un fallo propio, cazado por la primera consulta real

La primera versión del reparto por instrumento etiquetaba como **«fila anterior al 14/08»** toda
afirmación sin firma. La consulta 392 —escrita hacía un minuto— salió entera bajo esa etiqueta,
porque sus cuatro afirmaciones eran `conocimiento`, que **no pasa por ningún verificador por
diseño**: es la escotilla declarada.

La etiqueta afirmaba una causa —la edad— que no había comprobado. Es la lección de la casa aplicada
a algo que yo mismo acababa de escribir: *una etiqueta describe cómo se clasificó algo, no lo que
contiene*. Ahora hay dos motivos separados —`sin verificador (tipo no verificable por diseño)` y
`sin_declarar (fila anterior al 14/08/2026)`— porque uno es correcto y permanente y el otro es una
deuda de datos que se agota sola; juntarlos sería otro contador contestando dos preguntas.

**Y lo enseñó el camino real, no la suite**: los tests usaban afirmaciones de los tres tipos
verificables, así que ninguno pasaba por ese camino. Queda anclado con su test.

## 6. Lo que este encargo NO cubre, dicho

- **El SQL de `leer_respuesta` no lo prueba el CI** (ADR 0001: allí no hay Postgres). Se ejerce por
  el endpoint real contra la base local, y su salida está en §3. El hueco es el mismo que el resto
  de la casa: declarado, no tapado con un test que no prueba lo que su nombre dice.
- **El interruptor `verificacion` de la petición sigue sin efecto.** Hoy la capa se apaga con
  `NLI_ACTIVO=0` en el proceso, y la ablación por petición es el 7.3. La traza lo dice con esas
  palabras (`solicitada_tiene_efecto: false`) en vez de callarlo.
- **Los dos umbrales del §2 siguen sin calibrar.** Lo que cambia es que ya existe el dato con el que
  se calibrarán.
