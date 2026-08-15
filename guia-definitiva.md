# Guía definitiva: el profesor verificado
## Playbook de construcción para Claude Code

Este documento es la fuente de verdad del proyecto y el material de trabajo de Claude Code. Se trabaja por encargos numerados (0.1, 0.2, 1.1...), en orden, cada uno con su verificación y su criterio de cierre. Protocolo por encargo: Claude Code lee el encargo, propone un plan de 10 líneas o menos, espera el OK explícito, ejecuta, corre la verificación del encargo, y commitea con el porqué en el mensaje. No se abre un encargo con el anterior sin cerrar.

Regla de lectura: esta guía manda sobre cualquier conversación anterior. Lo que aquí no está construido no se afirma en presente en ningún fichero del repo. Los umbrales marcados como "inicial" son puntos de partida que se calibran donde la guía lo indica, nunca verdades.

---

# PARTE I: FUNDAMENTOS

## 1. Qué es, en una frase

Un profesor por asignatura sobre temario real que solo afirma lo que puede sostener: cita literal comprobada carácter a carácter, paráfrasis verificada contra el fragmento fuente, cálculo recalculado, y silencio honesto cuando la respuesta no está en el material. La tesis, para el README y para la sesión: **la honestidad del sistema no depende de la brillantez del modelo, depende de la capa de verificación.**

## 2. Principios

1. **Pesos abiertos en toda la cadena.** Generación, embeddings, reordenador y verificador son modelos de pesos abiertos detrás de interfaz compatible OpenAI. Garantiza el techo de privacidad por construcción (todo es autoalojable) y convierte al proveedor en un enchufe intercambiable por una URL. Trade-off: se renuncia a la calidad punta de los cerrados; el hueco se mide en la tabla, no se discute.
2. **Nada se afirma en presente si no está construido.** Dos estados posibles: construido y medido, o diseñado y declarado como no construido con interfaz definida.
3. **Toda métrica y todo detector se valida contra un caso donde debe fallar** antes de fiarse de su verde, y deja un test de regresión anclado a ese caso.
4. **Toda decisión de diseño lleva ADR** corto en `docs/adr/`: contexto, decisión, trade-off. Si no sabes escribir el porqué, no es una decisión, es un hallazgo pendiente.
5. **Ocurrencias y hallazgos se cuentan por separado** en cualquier número que alimente una decisión.
6. **El que comprueba no puede compartir el supuesto del que produce.** Un verificador que da por bueno el mismo supuesto que quien generó la respuesta es ciego exactamente al fallo que persigue: no falla al azar, falla justo donde importa, y encima falla en verde. Salió del encargo 1.1 en su forma más pequeña —el detector de "este módulo no ha dado unidades" usaba el mismo patrón que el troceador, así que un encabezado no reconocido dejaba el módulo mudo *y* sin denunciar— pero la ley es la del producto entero.

   **Consecuencia de diseño, obligatoria en la fase 4:** la verificación NUNCA puede depender del mismo supuesto que la generación. De ahí, y no por casualidad ni por ahorro, salen las dos decisiones centrales de la sección 8: la **cita literal se comprueba por comparación de cadenas, sin modelo de por medio** (un modelo juzgando si su propia cita es literal comparte con ella todo lo que la hizo mal), y la **paráfrasis la valida un NLI distinto del generador**, con otros pesos y otro entrenamiento. El día que alguien proponga "que el propio modelo se autoverifique", o "que el verificador sea el mismo modelo con otro prompt", este principio es la respuesta: un prompt distinto no es un supuesto distinto.

   **Corolario, aplicado ya varias veces en este repo:** todo detector se valida en las DOS direcciones, sano y mutado. Verlo en verde sobre un sistema sano no demuestra nada, porque un detector que no detecta nada también sale verde; hay que verlo ponerse rojo sobre el fallo que existe para cazar, y ver el diff de la mutación antes de leer el resultado. Es el principio 3 llevado al propio instrumento de medir.

7. **Con salida restringida, el esquema no es una petición: es una GRAMÁTICA. Quien produce no puede tener a mano el campo que le permitiría mentir.** Un campo que existe en el esquema es un campo que el decodificador puede rellenar, porque obliga la gramática token a token y el modelo elige entre lo que la gramática le deja. Pedirle en el prompt que no lo use es pedirle que no haga algo que sí puede hacer: unas veces obedece y otras no, y las que no se convierten en abstenciones o, peor, en respuestas mal formadas que parecen bien formadas.

   **De dónde sale, medido:** en el encargo 2.2 el contrato tenía un solo modelo de afirmación con `cita`, `expresion` y `andamiaje` como campos opcionales, y un validador que rechazaba las combinaciones que la sección 7 no permite. Las TRES primeras llamadas reales rellenaron `cita` en afirmaciones de tipo `conocimiento`, copiando su propio texto. **Y ese caso concreto es el peor imaginable en este proyecto: una afirmación que declara no tener fuente inventándose su propia cita es el sistema fabricándose la evidencia que acaba de declarar que no tiene.** El arreglo no fue insistir en el prompt ni endurecer el validador: fue partir el esquema en una variante por tipo, con exactamente los campos que la sección 7 le permite a cada uno, de forma que `cita` **no existe** fuera de `literal` y el decodificador no la puede emitir.

   **Es el principio 6 un nivel más abajo.** Allí, el que comprueba no comparte el supuesto del que produce; aquí, al que produce se le retira del alcance la herramienta con la que podría mentir. Y las dos capas se mantienen a la vez: el validador sigue rechazando la combinación prohibida aunque la gramática ya la impida, porque el esquema lo pone nuestro cliente y el que comprueba no se fía del que produce ni cuando el que produce está atado.

   **Regla práctica que se aplica a todo esquema nuevo:** antes de añadir un campo opcional al contrato, preguntarse qué diría el sistema si el modelo lo rellenara cuando no debe. Si la respuesta es "algo que parecería verificado sin serlo", el campo no va como opcional: va en su propia variante o no va.

7bis. **Y el ESPEJO del 7, que faltaba: no darle un campo que no puede fundamentar es la mitad; la otra es no NEGARLE un campo que necesita, porque entonces deforma los que tiene.** Medido el 13 de agosto de 2026: una afirmación citaba *"No se puede responder con los fragmentos proporcionados"* con `fragmento_id: 0`. El modelo **quería abstenerse** y el contrato no le daba forma de hacerlo —`literal` exige `fragmento_id`—, así que **abusó del campo que sí tenía**. No es un fallo del modelo: es un hueco de la gramática. Las dos mitades son la misma idea —**la distancia entre lo que la gramática permite y lo que la situación exige**— y las dos producen basura que parece válida: por exceso, un campo relleno sin fundamento; por defecto, un campo deformado para decir lo que no puede. **La comprobación, al diseñar cualquier contrato: recorrer las situaciones que el productor va a encontrarse y preguntar si TODAS son expresables.** La abstención lo será a partir del 4.5.

    **TERCER CASO, el 13 de agosto por la tarde, y es el más caro de los tres porque cambia de dirección: aquí no deformó el modelo, deformamos NOSOTROS su respuesta y luego se la imputamos.** El patrón de `resultado_afirmado` permitía **un** punto decimal y no dos, así que cuando el modelo quiso escribir `4.294.967.296` —correcto en español, y así salió en la prosa de esa misma respuesta— la decodificación restringida dejó `4.294967296`: cuatro coma tres. El verificador comparó ese número contra el recálculo y dictó **`podada`**, es decir *"el alumno se ha equivocado"*, sobre una respuesta que estaba bien. Los dos casos anteriores producían basura que **parecía** válida; este produjo **un juicio falso sobre el trabajo de otro**, que es el daño que esta capa entera existe para no causar. Y la comprobación del 7bis no lo habría cazado, porque la situación *sí* era expresable —un número cabe en el campo—: lo que no cabía era **la forma en que aquí se escriben los números**.

7ter. **La gramática PROHÍBE, no ELIGE — y esa frontera decide qué va al esquema y qué al prompt.** El 7 dice *no le des el campo que le permitiría mentir* y el 7bis *no le niegues el que necesita*; faltaba la tercera, que es **hasta dónde llega el poder de la gramática**. Un `pattern`, un `maxLength` o un `maxItems` vuelven **ingramático** lo que no queremos: eso no se pide, se impone, y el modelo no puede desobedecerlo. Pero **elegir entre ramas que la gramática permite todas** —cuál de los cinco tipos de afirmación usar— no lo decide el esquema, y la `description` de un campo es una etiqueta que solo se lee **cuando ya se ha llegado a ese campo**: al que nunca elige `calculo` no le llega nunca. Así que **prohibición a la gramática, preferencia al prompt**, y la formulación anterior —*"en el prompt va lo que la gramática no puede imponer"*— era correcta y se leyó como si no incluyera esto. **El caso, que costó un encargo entero:** el verificador de cálculo del 4.4 estuvo días completo, correcto y medido **sin una sola afirmación que juzgar**, porque `calculo` no aparecía en el prompt y su explicación se había dejado en el `description` del campo; cinco consultas explícitamente aritméticas dieron **cero** afirmaciones de ese tipo. Y la base tampoco avisaba: **345 afirmaciones reales y cero de cálculo es un cero que no se pone rojo**. Antes de dar por construido un verificador se cuenta cuántas veces se ha usado, que es distinto de leer su código.

8. **Una transformación aplicada a LOS DOS LADOS de una comparación puede ser destructiva sin ser dañina. Lo que rompe una comparación es la ASIMETRÍA, no la pérdida.** Salió midiendo el 3.1, contra la hipótesis que teníamos los dos: el lematizador español destroza los identificadores del corpus —`ViewData` se guarda como `viewdat`, `@ComponentScan` como `componentsc`, 10 de los 20 que aparecen en las preguntas oro— y **la recuperación no se resiente**, porque el documento y la consulta se destrozan igual. Buscar `ViewData` encuentra `ViewData`. La pérdida de información era real y el daño era cero.

   **La consecuencia práctica es dónde hay que mirar.** Ante una comparación que va peor de lo esperado, la pregunta no es *"¿qué información se está perdiendo?"* sino *"¿se está perdiendo lo mismo en los dos lados?"*. Y al revés: una transformación inofensiva aplicada a un solo lado es un fallo silencioso, porque nada protesta —los dos lados siguen siendo vectores o cadenas válidas, simplemente dejan de ser comparables—.

   **Dónde muerde esto en este proyecto, que no es un caso teórico:** la consulta del 3.2 se embebe con BGE-M3 y **tiene que ser el mismo modelo y la misma revisión** con la que se embebió el corpus (anclada en `corpus/medidas-ingesta.json`); si difieren, no hay error, hay peores resultados sin causa visible. El verificador `literal` de la sección 8 normaliza **la cita y el fragmento** con la misma función, y por eso puede permitirse ser destructivo con los espacios. Y el troceado y el modelo cuentan los tokens con el mismo tokenizador (1.4), que es la misma ley escrita para otra cosa.

9. **Una prueba de robustez solo puede correrse sobre casos que pasan en la condición FÁCIL.** Si el caso falla también con la entrada original, no está midiendo robustez: está midiendo el suelo, y la conclusión que se saque de él será sobre otra cosa.

   Salió en el 3.2, probando si la recuperación vectorial aguanta paráfrasis: la primera prueba usó `oro-001` y salió mal con las cuatro versiones **incluida la pregunta original**. Ese par es de los que la vía no encuentra de ninguna manera, así que no decía nada de las paráfrasis. La prueba solo empieza a medir cuando se corre sobre un par que la pregunta original **sí** acierta.

   **Y va a volver a morder en la fase 4**, en cuanto se pruebe si un verificador aguanta paráfrasis de una afirmación: hay que comprobar primero que esa afirmación se verifica bien en su forma literal. Un verificador que falla sobre el caso fácil no puede decirnos nada sobre el difícil.

10. **Un techo medido con un corte es el techo DE ESE CORTE, no del sistema.** En el 3.2 se calculó que la unión de las dos vías llegaba al 87,7 % en `lectura` y se leyó como "el máximo alcanzable", con su conclusión adjunta: que los pares que faltaban eran límite del corpus. Las dos cosas eran falsas, y por la misma razón: aquel número salía de cruzar **dos listas cortadas a 20**. Con las listas más profundas, el mismo cruce llega al 90,1 %. **Y VA POR DOS, así que la forma general es más ancha que el techo: comparar dos configuraciones en PUNTOS DE OPERACIÓN DISTINTOS produce una tabla que dice lo contrario de lo que pasa.** El segundo caso, del 14 de agosto de 2026: la tabla que justificó el cambio de juez NLI enfrentaba *"negativos que pasan: 4/67 contra 3/67"* y se leía como que el juez nuevo rechazaba más — pero cada celda estaba medida a **su propio corte** (0,60 el viejo, 0,93 el nuevo). **A corte común, el juez nuevo deja pasar igual o más en todos los cortes.** No invirtió la decisión —lo que se compra son 20 casos por 1 negativo— pero la tabla afirmaba algo falso. La comprobación cuesta diez segundos: **antes de poner dos números en la misma tabla, comprobar que están medidos en el mismo punto**; y si no pueden estarlo, **cada columna lleva su corte escrito dentro**.

   **La regla práctica: antes de atribuir un fallo al material, comprobar si el fallo es del corte.** Un "no lo encuentra nadie" medido a k=20 no dice nada del corpus; dice qué pasa a k=20. Y la clasificación de los casos perdidos solo vale hecha **con el corte con el que se va a correr de verdad**.

11. **Una muestra elegida por el síntoma que se investiga no mide la población: mide el síntoma.** Costó dos veces el mismo día, el 13 de agosto de 2026, y las dos sobre el conjunto oro. Primero, leer los **14 pares que ninguna vía de recuperación encontraba** dio once mal etiquetados, y de ahí salió un "hasta 11 de los 100" que no se sostenía: esos catorce se habían elegido **porque la recuperación fallaba en ellos**, que es justo una de las cosas que un mal etiquetado provoca. Y después, el triaje que iba a corregirlos por el patrón detectado —*el fragmento correcto es casi siempre `orden + 1`*— habría propagado el mismo sesgo a cuarenta correcciones mecánicas.

    **Y AMPLIADO EL 13 DE AGOSTO POR LA TARDE, porque el síntoma no es el único criterio que sesga: vale para CUALQUIER criterio de selección correlacionado con lo que se mide, y el más común en software es el TEMPORAL — datos de antes del cambio.** Al acotar `afirmaciones` con `maxItems` (ADR 0017), el tope iba a salir de las 110 respuestas reales de la base, que van de 1 a 6 y ninguna pasa de 6. Parecía la derivación honesta y era la trampa: esas respuestas son **anteriores a que existieran los modos**, así que no contienen ni una derivación de `corregir` — que es exactamente el modo que encadena pasos y el que estaba desbordando el tope de tokens. **Derivar el límite de esa muestra habría recortado justo lo que motivó el cambio.** Ese es el que va a volver: cada vez que se mide el efecto de algo nuevo contra la historia acumulada sin él.

    **Y TERCERA VARIANTE, el 14 de agosto: la muestra elegida por la CONFIGURACIÓN en la que era cómodo medir.** Reporté *"11,5 % de cortes con el código de hoy"* y ese número salía del **contenedor**, que no lleva torch y recupera **solo por léxica** —58 % de recall frente al 80,9 %—. La configuración que corre en la sesión, con vectorial y reordenador, cortaba el **30 %**. No medí la historia equivocada ni el síntoma: medí **donde estaba levantado**.

    **Y CUARTA VARIANTE, la más afilada, el 14 de agosto: la muestra elegida por QUIÉN.** El detector de *"el sistema duda del resultado"* del 5.3 se validó contra seis frases **que escribí yo** y dio **6 de 6**; sobre salida real fallaba **3 de 6**, porque el sistema no escribe *"quizá el resultado está mal"*, escribe *"es 12,1 €, **no** 12,4 €"*. Estaba midiendo **el fraseo que yo imaginaba**, no el comportamiento — una muestra elegida por quien iba a ser medido con ella.

    **Y SEXTA VARIANTE, la más incómoda, porque le toca a la propia auditoría: el ALCANCE de un barrido es también una selección.** El barrido de *"degradaciones declaradas sin código"* del 13 de agosto miró el **8.1 y la Parte V** —las secciones donde era natural que hubiera degradaciones— y encontró cuatro. No vio el validador de contenido encubierto en `andamiaje`, que está en la **sección 3**, ni el registro de `conocimiento` con confianza alta, que está en la **sección 8**: los dos aparecieron el 14, uno por un fallo real y el otro preguntando a propósito. **Buscar donde es natural que haya es la misma economía que medir donde es fácil**, y produce el mismo sesgo con un disfraz más respetable. La comprobación: un barrido se declara con su **alcance**, y si el alcance no es "todo", el resultado no es "hay cuatro" sino **"hay cuatro en las dos secciones que miré"**.

    **Las seis juntas, porque el error es el mismo y solo cambia el eje: por el SÍNTOMA, por CUÁNDO, por DÓNDE, por QUIÉN y por DÓNDE SE BUSCÓ. Todas las veces se midió donde salía fácil.** La comprobación, antes de publicar cualquier tasa: *¿esta muestra se parece a aquello sobre lo que voy a decidir?* — y si la respuesta empieza por "es que ahí era más rápido de medir", no.

    **La regla práctica: para estimar una población hace falta una muestra elegida por un criterio INDEPENDIENTE del síntoma, y normalmente eso es al azar.** Ocho pares tomados al azar **entre los que nadie había marcado** dieron tres claramente mal y uno dudoso: **del orden de 40 de 100**, cuatro veces lo que decía el muestreo sesgado. El número real no apareció mirando más casos sospechosos, sino mirando casos que nadie sospechaba.

    **Y su frontera con el 10, porque se confunden:** el **10** habla de **lo medido** —un techo, un recall— y avisa de que el número depende del corte con el que se calculó. El **11** habla de **sobre qué se midió** —la muestra— y avisa de que el número depende de cómo entraron los casos en ella. El 10 se comprueba cambiando el corte; el 11, cambiando el criterio de selección. Un experimento puede pasar el 10 y fallar el 11 sin que nada se ponga rojo, porque los dos producen números perfectamente normales.

12. **Una curva de latencia que deja de crecer bajo carga puede ser la firma de una pérdida de calidad silenciosa, no una prueba de solidez.** Medido el 13 de agosto de 2026: desde cuatro consultas simultáneas, el p95 de la recuperación **se aplana** —2.566, 2.548, 2.168, 2.721 ms— y parece que el sistema escala. Escala porque **está soltando lastre**: a partir de cinco alumnos, la espera acotada del reordenador vence y las peticiones salen **sin reordenar**. Las que habrían tardado más son exactamente las que se degradan, y al degradarse salen antes. La respuesta llega, llega incluso más rápido, y **solo la traza sabe que salió peor ordenada**.

    **La regla práctica: cuando una métrica MEJORA al aumentar la presión, la primera pregunta es qué se está soltando para conseguirlo.** No es que sea imposible que algo mejore bajo carga —una caché se calienta, un lote se llena—, es que la explicación hay que tenerla, y si no se tiene, la hipótesis por defecto es que se está pagando en otra moneda que nadie está mirando.

    **Y su consecuencia operativa, obligatoria: el techo de concurrencia SE REPORTA SIEMPRE COMO PAR DE NÚMEROS —latencia Y tasa de degradación—, nunca la latencia sola.** Decir *"2,7 s con ocho alumnos"* sin decir que **la mitad salió sin reordenar** es un número que engaña sin contener una sola cifra falsa. Es la regla del denominador aplicada a otro eje: allí el peligro era contar solo los casos que salieron bien, aquí es medir solo la dimensión que salió bien. En la evidencia y en el README, siempre las dos columnas juntas.

    **Su hermano, de la misma familia y del mismo día: un diagnóstico que solo se equivoca bajo carga es peor que ninguno, porque solo miente cuando se le consulta.** El primer discriminador entre "la GPU no responde" y "hay cola" usaba `futuro.running()`, y clasificaba como avería un trabajo que se había pasado el 95 % del plazo esperando turno. Funcionaba perfectamente en reposo —donde no hace falta— y fallaba bajo carga, que es el único momento en que alguien lo mira.

## 3. Comportamiento: cuatro modos como máquina de estados

La pedagogía es política explícita en código; el modelo rellena los estados. El fallo típico de un LLM tutor es salirse de la estrategia, empezando por soltar la solución.

- **Responder.** Duda directa, respuesta con fuentes.
- **Acompañar.** Socrático: guía sin soltar la solución, pide el siguiente paso al alumno, valida o corrige cada paso contra el temario. Reglas duras del modo: nunca dar el resultado final ni el paso completo resuelto; máximo una pista por turno; si el alumno lo pide explícitamente tres veces, se ofrece cambiar a modo responder (el cambio queda en la traza).
- **Corregir.** Recibe un intento o solo un resultado. Con solo el resultado, el resultado es el oráculo: se genera la derivación completa con la restricción de que la última línea iguale el resultado dado; el verificador recalcula; si no existe camino desde el temario hasta ese número, el sistema dice que quizá el resultado está mal.
- **Examinar.** Tipo test desde el temario, con evaluación. DISEÑADO, NO CONSTRUIDO. Lleva pegada la nota del AI Act (Parte VI).

**Los cuatro modos hablan como profesores, no como fichas.** Guiar, acompañar y corregir necesitan andamiaje pedagógico —transiciones, analogías, preguntas al alumno, resúmenes—, y ese andamiaje **se declara en el contrato con tipo `andamiaje` y NO se poda** (sección 7): no afirma nada del mundo, así que no hay nada que verificar en él. Lo que sí se verifica siempre es la afirmación factual, y una frase de andamiaje que afirme algo del temario deja de ser andamiaje y se verifica como afirmación. El modo acompañar es el que más andamiaje usa, por definición: su trabajo es preguntar y guiar sin soltar la solución. Dicho de una vez: **la verificación existe para que el sistema no mienta, no para que no enseñe.**

**Proactividad:** cada respuesta termina con un siguiente paso propuesto generado desde el árbol del temario (siguiente concepto de la unidad o hueco que el alumno acaba de enseñar), nunca inventado. Se implementa como consulta al árbol, no como creatividad del modelo.

## 4. Los cuatro tipos de afirmación

| Tipo | Qué es | Verificación | Coste |
|---|---|---|---|
| `literal` | Texto exacto del temario | Comparación de cadena normalizada contra el fragmento; si no casa, se degrada a `parafrasis` o se poda | Determinista, microsegundos |
| `parafrasis` | Contenido del temario reescrito | Implicación (NLI) contra el fragmento citado con verificador pequeño abierto | Milisegundos |
| `calculo` | Aritmética o código del ejercicio | Recálculo; si es código, ejecución en sandbox | Variable, medido |
| `conocimiento` | Fuera del temario | No se verifica: se marca visible, jamás disfrazado de temario | Cero |

Consecuencia: **el sistema no puede mentir sobre qué es cita literal, por construcción.** Fallos de verificación: poda de la afirmación, o un único reintento con la señal del fallo, o abstención. La abstención es respuesta de primera clase, no error.

---

# PARTE II: DECISIONES CERRADAS (no se reabren)

## 5. Infraestructura

**Prototipo desplegado:** un VPS de Hetzner con Docker Compose. Servicios: `api` (FastAPI + interfaz web), `db` (Postgres 16 + pgvector), `redis` (caché semántica y broker), `worker` (Celery: generación, verificación, ingesta), `caddy` (TLS). Inferencia: **Scaleway Generative APIs** (retención cero por defecto: no recogen, leen ni reutilizan prompts ni salidas; empresa francesa del grupo iliad; inferencia íntegra en infraestructura soberana europea; ISO 27001 y SOC 2; API compatible OpenAI; pago por token).

**Modelos:**
- Generador por defecto: **Mistral Small** en Scaleway (abierto, fuerte en castellano, barato).
- Escalón: el modelo grande del catálogo de Scaleway, solo cuando el clasificador marque caso duro o el verificador rechace.
- Embeddings: **BGE-M3** (abierto, multilingüe, 1024 dimensiones). Corre en la 5080 local para ingesta.
- Reordenador: **BGE reranker v2-m3** (cross-encoder abierto multilingüe), revisión anclada `953dc6f6…`. En servicio, en la CPU del VPS sobre los **30** mejores; en producción, a GPU. **El pool son 30 desde el 13 de agosto de 2026 y el motivo es aritmético, no de gusto** (3.4): con 20, el techo de la fusión obliga al reordenador a acertar el 96,7 % para llegar al 0,8 de `recall@6`, que es imposible. **Y la cuantización int8 NO se da por hecha aquí:** se mide primero en torch-CPU fp32 —que ya está en el entorno— y solo se paga la cadena de ONNX si ese número no cabe en el presupuesto.
- Verificador de implicación: **mDeBERTa-v3-base-xnli** o equivalente NLI multilingüe abierto, cuantizado, CPU del VPS.
- Fila self-host de la tabla: vLLM en la 5080 local (16 GB VRAM) sirviendo un abierto de ~8B cuantizado (Ministral 8B o Qwen3 8B, AWQ o FP8). **Se declara explícitamente en la tabla que la fila self-host local usa el hermano de 8B por límite de VRAM, y que producción con GPUs de servidor sirve el mismo Mistral Small**: no se compara mintiendo.

**Producción:** el mismo modelo abierto autoalojado con vLLM sobre GPUs en infraestructura europea. Palancas: continuous batching, caché de prefijos, decodificación especulativa por sufijos (en contenido educativo las respuestas se repiten muchísimo: rinde como en ningún otro dominio).

**Por qué no las otras:** frontier americano vía endpoint europeo rompe el invariante (pesos cerrados, jurisdicción estadounidense); Mistral La Plateforme condiciona su retención cero al plan Scale y a llamadas sin estado, segunda clasificada; GPU alquilada hoy paga operación que el prototipo no necesita.

## 6. Corpus

**Ciclo elegido: Desarrollo de Aplicaciones Web (DAW), grado superior, dos cursos.** El entrevistador es desarrollador y puede juzgar en vivo; los ejercicios de código habilitan el verificador por ejecución; material abundante y público. Decisión tomada una vez.

**Alcance de carga del prototipo:** el árbol completo de los dos cursos (todas las asignaturas creadas con su normativa) y **dos asignaturas cargadas a densidad completa** (recomendadas: Programación, de primero, y Desarrollo Web en Entorno Servidor, de segundo). El resto de asignaturas quedan con la normativa BOE cargada y densidad declarada como parcial. Motivo: profundidad demostrable donde se va a preguntar, sin fingir un corpus que no da tiempo a curar.

**Multi-titulación real (encargo 1.12):** el corpus no se queda en DAW. El árbol es `corpus/<titulacion>/<curso>/<asignatura>/` desde ya (el paquete inicial, que es solo DAW, se recoloca bajo `corpus/daw/` actualizando las rutas del manifiesto y re-verificando), y entran como titulaciones hermanas reales, a densidad parcial, **DAM** (RD 450/2010) y **ASIR** (RD 1629/2009), con la opción de sumar los cursos de especialización de la familia (Ciberseguridad, Videojuegos y RV, IA y Big Data) si el tiempo sobra. Regla intocable: **la densidad completa y TODOS los conjuntos de casos siguen siendo de DAW**; las hermanas existen para que la estructura por titulación, el selector del alumno y el benchmark de escala sean reales, no para diluir la semana en curar tres ciclos. Matiz de vocabulario: densidad "completa" significa CURADO PARA EVALUACIÓN (pares oro y casos), no cantidad; los tres grados llevan material de ciclo prácticamente entero (mapa en `corpus/COBERTURA.md`, con los huecos declarados), pero solo las dos asignaturas de DAW están curadas.

---

# PARTE III: CONTRATOS TÉCNICOS

Estos contratos se escriben antes que el código que los implementa. Claude Code no se desvía de ellos sin ADR.

## 7. Contrato de generación tipada (el contrato central)

El generador produce SIEMPRE esta estructura (structured output del proveedor; si el modelo la rompe, un reintento y después abstención):

```json
{
  "modo": "responder | acompanar | corregir",
  "afirmaciones": [
    {
      "id": 1,
      "tipo": "literal | parafrasis | calculo | conocimiento | andamiaje",
      "texto": "la afirmación tal cual irá al alumno",
      "fragmento_id": 12345,
      "cita": "texto exacto copiado del fragmento (solo si tipo=literal)",
      "expresion": "expresión o código a recalcular (solo si tipo=calculo)",
      "andamiaje": "transicion | pregunta_al_alumno | analogia | resumen | animo (solo si tipo=andamiaje)"
    }
  ],
  "respuesta_redactada": "texto final que hila las afirmaciones, sin añadir contenido nuevo",
  "siguiente_paso": {"tipo": "concepto_arbol | pregunta_al_alumno", "ref": "ruta en el árbol o null", "texto": "..."},
  "confianza_recuperacion": "alta | media | baja"   // LO PONE EL SERVIDOR: no esta en el esquema
}
```

### BARRIDO DE LA SECCIÓN 7 CON LA REGLA DEL ADR 0014 (13 de agosto de 2026)

La regla —*si el modelo no tiene con qué saberlo, el campo es del servidor*— se aplica a **los trece campos del contrato**, no solo al que la originó. Resultado: **dos más afectados**, uno resuelto y uno declarado.

| Campo | ¿Tiene el modelo con qué saberlo? | Quién lo pone |
|---|---|---|
| `modo` | sí, del texto del alumno… pero el **5.1 declara un clasificador** | **el modelo, HOY y declarado como provisional**: pasa al servidor cuando exista el clasificador del 5.1. Mientras tanto se enseña el modo devuelto y no el pedido, que es el hueco ya declarado del 2.2 |
| `afirmaciones[].id`, `tipo`, `texto`, `cita`, `expresion`, `andamiaje` | sí: es lo que acaba de hacer | el modelo |
| `afirmaciones[].fragmento_id` | sí, de los fragmentos que se le dan… **pero puede inventarlo** | el modelo, **con el id comprobado contra el contexto por el servidor** (`fragmento_en_contexto`) |
| `respuesta_redactada` | sí | el modelo |
| `siguiente_paso.tipo`, `.texto` | sí | el modelo |
| **`siguiente_paso.ref`** | **NO: el modelo no ve el árbol** | **el SERVIDOR** — sale del esquema en el 3.3; hoy va nula y declarada, y la resuelve el 5.4 |
| **`confianza_recuperacion`** | **NO: no ve distancias ni lo que quedó fuera** | **el SERVIDOR** (ADR 0014) |

**`siguiente_paso.ref` era el mismo fallo que el `fragmento_id` inventado, con un agravante:** una ruta del árbol del BOE **plausible** es indistinguible de una real sin ir a comprobarla, así que se colaría más fácil.

**`confianza_recuperacion` NO va en el `json_schema` que se le envia al modelo** (corregido en el 3.3, ADR 0014). Lo calcula el servidor a partir de la recuperacion —cuanto destaca el primer candidato sobre el sexto— porque el modelo no tiene con que saberlo: solo ve seis fragmentos, sin sus distancias ni lo que quedo fuera. Al modelo se le DICE el valor para que ajuste su comportamiento; escribirlo, no. Es el principio 7 una planta mas arriba: un campo que existe en la gramatica es un campo que el modelo puede rellenar, y **antes de meter un campo en el esquema hay que preguntarse si el modelo tiene con que saberlo**.

Regla de oro del contrato: `respuesta_redactada` no puede contener contenido que no esté en `afirmaciones`. El validador lo comprueba por cobertura aproximada (toda frase de la redacción debe solapar con alguna afirmación); las frases huérfanas se tratan como afirmaciones `conocimiento` no declaradas: un reintento y después poda.

### Afirmación factual y andamiaje pedagógico (corrección del contrato)

La regla de cobertura, tal como estaba escrita, podaba toda frase que no solapara con una afirmación verificable. Eso se llevaba por delante lo que hace que un profesor enseñe: las transiciones, el "vamos paso a paso", las analogías, las preguntas al alumno, el resumen de lo que se acaba de ver. **Un profesor que solo enuncia hechos verificados no enseña, recita.** Así que el contrato distingue dos cosas:

- **Afirmación factual** (`literal`, `parafrasis`, `calculo`, `conocimiento`): dice algo del mundo o del temario. **Se verifica siempre**, con las reglas de la sección 8.
- **Andamiaje pedagógico** (`andamiaje`): no afirma nada del mundo, así que **no se poda ni se verifica contra el corpus**. "Vamos por partes", "¿qué crees que pasaría si el bucle empezara en 1?", "piensa en una clave primaria como el DNI de la fila", "recapitulando lo anterior".

**El andamiaje se declara igual que todo lo demás**, entra en la cobertura de la redacción y no es un agujero por el que colar texto sin declarar. Y va con dos condiciones que lo mantienen honesto:

1. **No puede colar contenido factual encubierto.** Si una frase de andamiaje afirma algo del temario ("como sabes, una clave ajena SIEMPRE apunta a una primaria"), no es andamiaje: es afirmación y se verifica como tal. El validador lo comprueba y su tasa de acierto se mide como cualquier otro detector, en las dos direcciones (principio 6); lo que se cuele se trata como el resto de frases huérfanas: un reintento y después poda.
2. **Una analogía se marca como analogía** (`andamiaje: "analogia"`), y la interfaz la renderiza como lo que es. Una comparación con el DNI ayuda a entender una clave primaria y no está en el temario: decirlo no le quita valor pedagógico, le quita la posibilidad de que el alumno la cite en un examen creyendo que la dijo el libro.

El porqué, en una frase para la sesión: **la capa de verificación existe para que el sistema no mienta, no para que no enseñe.**

**Y su hermana, medida el 13 de agosto de 2026 y también para decir en voz alta: «sin material que citar, el modelo se explaya; con material, se ciñe a él».** Sale de contar tokens, no de filosofar: la misma pregunta en modo `corregir` **sin fragmentos** se fue a los 900 tokens del tope y volvió cortada en 7 de 10 corridas, y **con fragmentos** gastó 386 de media (máximo 615) sin acercarse al tope ni una vez. Es la tesis del proyecto vista desde el consumo: el temario no solo hace la respuesta más cierta, la hace **más corta**. Se entiende sin saber nada del sistema, y de paso explica por qué la verificación no es un impuesto sobre la generación.

## 8. Contratos de verificación

Los dos primeros contratos son el principio 6 hecho código, y por eso no se negocian: el literal se comprueba **sin modelo** y la paráfrasis con un modelo **distinto del generador**. Un verificador que comparte supuesto con quien generó la respuesta no es un verificador, es un eco.

- **`literal`:** normalización (**solo espacios colapsados**; tildes conservadas y **mayúsculas también**) y búsqueda de subcadena exacta de `cita` dentro del texto del `fragmento_id`. Sin umbral, sin modelo. Falla: degradar a `parafrasis` y verificar como tal; si también falla, poda. **CORREGIDO el 13 de agosto de 2026 con la medida delante:** esta línea pedía minúsculas. Medido sobre 337 citas reales, bajar a minúsculas gana **2**, y leídas una a una las dos diferían **en la letra inicial** —el modelo empezó la cita como si fuera frase—. O sea que el paso compra dos mayúsculas iniciales y a cambio acepta `bindingresult` como cita literal de `BindingResult` en un corpus medio código. No entra. Los tipográficos ganaron **+0** y tampoco. El porqué y la asimetría que lo decide, en el 4.2.
- **`parafrasis`:** NLI con premisa = fragmento, hipótesis = texto. Veredicto `entail` con probabilidad ≥ 0,80 —**calibrado a 0,60 el 14/08/2026 (4.6, ADR 0020), con el suelo de selección subido a 0,30 en el mismo plano**— pasa; `contradiction` poda siempre; `neutral` dispara el reintento único con la señal.
- **`calculo`:** si `expresion` es aritmética, recálculo con evaluador seguro (sin `eval` de Python: parser propio o sympy). Si es código, ejecución en sandbox: contenedor efímero sin red, 0,5 CPU, 256 MB, timeout 5 segundos, sistema de archivos de solo lectura salvo `/tmp`. La salida se compara con lo afirmado.
- **`conocimiento`:** no se verifica; se marca. Si `confianza_recuperacion` era alta y aun así el modelo tiró de conocimiento, se registra en la traza (señal de recuperación floja o de pregunta fuera de temario).
- **Política global:** máximo un reintento por respuesta. Presupuesto de verificación por consulta: configurable, inicial 2 segundos; lo que no llega, poda o abstención, jamás pase silencioso.

**QUIÉN GANA CUANDO LOS DOS DISPARADORES DEL REINTENTO COINCIDEN, escrito antes de que ocurra**, porque desde el 4.3 hay **dos**: contrato roto (sección 7) y `neutral` del NLI. Y el presupuesto es **uno por respuesta**, así que hay que decir cuál se lo lleva o el primer caso que ocurra lo decidirá por accidente.

**Gana el CONTRATO, y no es un empate resuelto a suertes: es una precedencia.** Un contrato roto es una **precondición** —sin JSON bien formado no hay afirmaciones que verificar, así que el NLI ni siquiera llega a opinar—, mientras que un `neutral` es una respuesta bien formada que además no se sostiene. Reintentar lo primero puede producir una respuesta entera; reintentar lo segundo solo puede mejorar una que ya existe.

**Consecuencia operativa, que es la parte incómoda y por eso se escribe:** si la primera pasada rompió el contrato y la segunda vino bien formada pero con una afirmación en `neutral`, **el reintento ya está gastado y esa afirmación NO se vuelve a pedir**. Se resuelve por la política del 4.5 —poda o degradación— y **se anota en la traza que el reintento estaba consumido**, para que al leer la tasa de `neutral` no se confunda "no se pudo reintentar" con "se reintentó y siguió mal". Son dos cosas distintas y una tabla que las sume dice una tercera que no es ninguna.

## 9. Esquema de datos (DDL de referencia)

Postgres 16, extensiones `vector` y `pg_trgm`. Todas las tablas llevan `organizacion_id` (multi-tenant preparado, no gestionado) y `creado_en`.

```sql
CREATE TABLE asignaturas (id serial PRIMARY KEY, organizacion_id int NOT NULL DEFAULT 1,
  titulacion text NOT NULL DEFAULT 'DAW', curso smallint NOT NULL, nombre text NOT NULL,
  codigo text NOT NULL, UNIQUE (titulacion, codigo));
-- OJO: el codigo de modulo NO es unico globalmente: los transversales (0373, 0483, 0484, 0485, 0487)
-- se repiten entre titulaciones en el titulo oficial. UNIQUE global rompia la carga de DAM y ASIR.

CREATE TABLE titulacion_asignaturas (titulacion text NOT NULL, asignatura_id int NOT NULL,
  PRIMARY KEY (titulacion, asignatura_id));
-- Puente de transversales: un modulo transversal se carga UNA vez bajo su titulacion duena
-- (sus fragmentos viven en UNA particion) y esta tabla lo mapea a las demas titulaciones.
-- El selector del alumno lista las asignaturas de su titulacion via esta puente.
-- Contaminacion entre titulaciones = fragmento de una asignatura NO mapeada a la titulacion del alumno.

CREATE TABLE documentos (id serial PRIMARY KEY, organizacion_id int NOT NULL DEFAULT 1,
  asignatura_id int REFERENCES asignaturas, unidad text, titulo text NOT NULL,
  fuente text NOT NULL, licencia text NOT NULL, version_corpus text NOT NULL,
  hash_sha256 char(64) NOT NULL, densidad text NOT NULL DEFAULT 'completa',
  origen text NOT NULL DEFAULT 'texto', ruta text NOT NULL UNIQUE);  -- origen: 'texto' | 'ocr'
-- CORREGIDO en el 2.1 (ADR 0008): el hash NO es unico, la RUTA si. Este DDL ponia UNIQUE sobre el
-- hash y ese unique es incompatible con el 1.7: el documento colado que se planta para medir
-- contaminacion es una COPIA EXACTA de otro de distinta asignatura -mismo hash, dos rutas, dos
-- particiones-, asi que el unique global habria obligado a tirar uno de los dos y con el, el
-- instrumento del 3.5. Lo que identifica un documento es su ruta, que es la clave del manifiesto.

CREATE TABLE fragmentos (id bigserial, organizacion_id int NOT NULL DEFAULT 1,
  documento_id int NOT NULL, asignatura_id int NOT NULL, unidad text,
  tipo_contenido text NOT NULL, texto text NOT NULL, contexto text NOT NULL,
  embedding vector(1024), tsv tsvector,
  PRIMARY KEY (asignatura_id, id)) PARTITION BY LIST (asignatura_id);
-- una partición por asignatura; índices POR PARTICIÓN:
--   HNSW sobre embedding (m=16, ef_construction=64 iniciales)
--   GIN sobre tsv (configuración 'spanish')

CREATE TABLE glosario (id serial PRIMARY KEY, asignatura_id int NOT NULL,
  termino text NOT NULL, definicion text NOT NULL, fragmento_id bigint NOT NULL,
  via_validacion text, evidencia text,          -- como se valido esa entrada, para poder auditarla
  UNIQUE (asignatura_id, termino, fragmento_id));
-- CORREGIDO en el 2.6 (ADR 0012): este DDL ponia UNIQUE (asignatura_id, termino), y esa
-- restriccion impide el momento 3 de la demo. El DWES antiguo y el moderno mapean los DOS al 0613
-- (decidido asi en el 2.1, para que sus materiales cayeran en la misma particion), de modo que las
-- dos definiciones incompatibles de MVC son del mismo (asignatura_id, termino) y la segunda no
-- entraria. Con fragmento_id dentro se sigue impidiendo la duplicacion de verdad -la misma
-- definicion sacada dos veces del mismo fragmento- y el corpus entra como es. Y sale gratis lo
-- mejor: que un termino tenga mas de una entrada ES la senal de conflicto, con un GROUP BY
-- determinista en vez de un umbral de similitud.

CREATE TABLE conflictos (id serial PRIMARY KEY, fragmento_a bigint NOT NULL,
  fragmento_b bigint NOT NULL, similitud real, estado text NOT NULL DEFAULT 'abierto', detalle text,
  tipo text NOT NULL,                    -- 'casi_duplicado' | 'contradiccion'
  veredicto_nli text, probabilidad_nli real,   -- que dijo el verificador, no solo que hubo conflicto
  fecha_a date, fecha_b date,            -- de la fuente de cada fragmento: sin esto no se puede ordenar
  version_a text, version_b text);
-- OJO: esta tabla NO guarda una marca de "aqui hay conflicto", guarda lo que la fase 4 necesita
-- para RESPONDER: los dos fragmentos, cuanto se parecen, que dijo el NLI y de cuando es cada
-- fuente. Detectar es la mitad del trabajo; la otra es que se le dice al alumno que pregunta por
-- MVC cuando su temario tiene dos versiones.

CREATE TABLE consultas (id bigserial PRIMARY KEY, ts timestamptz DEFAULT now(),
  organizacion_id int NOT NULL DEFAULT 1, usuario_id text, modo text NOT NULL,
  asignatura_id int, texto text NOT NULL, version_corpus text NOT NULL, version_prompt text NOT NULL);

CREATE TABLE respuestas (id bigserial PRIMARY KEY, consulta_id bigint NOT NULL,
  modelo text NOT NULL, escalado bool DEFAULT false, cache_hit bool DEFAULT false,
  ttft_ms int, total_ms int, tokens_entrada int, tokens_salida int, coste_eur numeric(10,6),
  etapas jsonb NOT NULL, abstencion bool DEFAULT false);

CREATE TABLE afirmaciones (id bigserial PRIMARY KEY, respuesta_id bigint NOT NULL,
  tipo text NOT NULL, texto text NOT NULL, fragmento_id bigint,
  veredicto text NOT NULL, detalle jsonb);

CREATE TABLE casos_eval (id serial PRIMARY KEY, conjunto text NOT NULL,
  asignatura_id int, entrada jsonb NOT NULL, esperado jsonb NOT NULL);

CREATE TABLE corridas_eval (id serial PRIMARY KEY, ts timestamptz DEFAULT now(),
  commit_sha text NOT NULL, config jsonb NOT NULL, metricas jsonb NOT NULL);
```

La traza completa de una respuesta se reconstruye desde `consultas` + `respuestas` (con `etapas` desglosando latencia y coste por etapa) + `afirmaciones`. Esa traza es la observabilidad del sistema y, de paso, el logging que pide el AI Act.

## 10. API

- `POST /consulta`: body `{texto, asignatura_id, modo?, usuario_id?, verificacion?}`; respuesta SSE con eventos `etapa`, `ttft`, `token`, `afirmaciones`, `fin` (el TTFT medido es el que ve el alumno). **`etapa` se añadió en el 2.4** y lleva las transiciones reales y medidas del trabajo que está ocurriendo —petición enviada, primer token del proveedor, primera prosa, y con la fase 3 las de recuperación—; es lo que la interfaz dibuja mientras espera, y cada etapa dibujada tiene que tener su entrada en `respuestas.etapas`. **`abstencion`** se emite en lugar de `afirmaciones` cuando el contrato no llega bien formado. **`verificacion`** es el enganche de la ablación: hoy no tiene efecto porque la fase 4 no existe, se declara así y se registra en la traza.
- `GET /asignaturas?titulacion=`: las asignaturas de una titulación **a través de la puente** `titulacion_asignaturas`, o sea con sus transversales. Es lo que llena el selector del alumno.
- `GET /respuestas/{respuesta_id}/fragmentos/{fragmento_id}`: el fragmento citado, **abierto por procedencia**. No se puede pedir un fragmento cualquiera: solo los que esa respuesta usó, comprobado contra `afirmaciones`. Lo que legitima leerlo no es que sea de tu asignatura, es que el sistema lo usó para responderte; y de paso cierra por construcción la lectura cruzada entre asignaturas que el 3.5 mide.
- `POST /ingesta/documento`: idempotente por el par **`(ruta, hash_sha256)`**; encola el trabajo, devuelve id de trabajo. Misma ruta y mismo hash: no hay trabajo que hacer. Misma ruta y hash distinto: es una versión nueva del documento y sí lo hay. **Esta línea decía "idempotente por `hash_sha256`" y era falsa en este corpus** (CORREGIDO en el 2.1, ADR 0008): el mismo contenido vive legítimamente en dos rutas —el documento colado del 1.7 es copia exacta de otro de distinta asignatura, y esa dualidad es el instrumento con el que el 3.5 mide contaminación—, así que una idempotencia por hash solo se habría comido la segunda ingesta y con ella la medida. Lo que identifica a un documento es su ruta; el hash dice si ha cambiado.
- `POST /eval/correr`: body `{conjuntos: [...], config: {...}}`; corre el arnés y persiste en `corridas_eval`. **NO CONSTRUIDO, y no por falta de tiempo: por decisión, hasta la fase 8** (escrita en el 3.5). El arnés corre como **script** contra la base, así que este endpoint no es la vía y su ausencia no bloquea nada; en particular **no hace falta la cola `evals` del 2.3 para cerrar la fase 3**. Si algún día se construye, encolará en `evals` y devolverá id de trabajo.
- `GET /trazas/{respuesta_id}`: la traza completa.
- `GET /salud` (dependencias una a una), `GET /metricas` (formato Prometheus).

## 11. Configuración (variables de entorno, `.env.example` sin valores)

`DATABASE_URL`, `REDIS_URL`, `INFERENCIA_BASE_URL` (Scaleway), `INFERENCIA_API_KEY`, `MODELO_PEQUENO`, `MODELO_GRANDE`, `PRECIO_ENTRADA_PEQ`, `PRECIO_SALIDA_PEQ`, `PRECIO_ENTRADA_GRANDE`, `PRECIO_SALIDA_GRANDE` (se rellenan del pricing vigente de Scaleway al arrancar la fase 6), `UMBRAL_CACHE_SIM` (inicial 0,92), `UMBRAL_NLI` (inicial 0,80), `RERANK_CANDIDATOS` (**30**, subido de 20 el 13 de agosto de 2026 con la aritmética del techo delante; el porqué, en el 3.4), `TIMEOUT_ETAPA_MS`, `PRESUPUESTO_CONSULTA_MS` (**8000** operativo desde el 14 de agosto de 2026 — el 13 se había bajado a 5000 y la medida lo devolvió; el objetivo de producto vive aparte en `OBJETIVO_CONSULTA_MS`=5000 y **se reportan los dos**, revisión de abajo), `VERSION_PROMPT`, `VERSION_CORPUS`.

**REVISADO EL 14 DE AGOSTO DE 2026 CON LA MEDIDA DELANTE: EL OBJETIVO SIGUE EN 5 s, EL PLAZO OPERATIVO SUBE A 8 s, Y SE REPORTAN LOS DOS.**

Y no es mover la portería, que es justo lo que hay que escribir para que no lo parezca: **el requisito de 5 s se fijó SIN la medida**. Medido sobre la configuración completa —embebedor, vectorial, reordenador y NLI, que es la que corre en la sesión—, el **p50 lo roza**. Un tope por debajo de la mediana del propio sistema no es un objetivo: es **garantía de fallo**, y lo que produce no es un sistema más rápido sino uno que **corta el 30 % de sus respuestas**. Y cortar una respuesta entera a los 5 s es peor experiencia que entregarla a los 6 con la pantalla llena de contenido desde los 700 ms —fragmentos, afirmaciones y veredictos apareciendo—, que es exactamente para lo que se construyó el solape.

Así queda, y los dos números van **siempre juntos** (`scripts/medir_abstencion.py` los imprime a la vez, y el evento `fin` los lleva los dos en cada respuesta):

| | valor | medido el 14/08/2026, n=20, configuración de la sesión |
|---|---|---|
| **Objetivo de producto** (`OBJETIVO_CONSULTA_MS`) | **5.000 ms** | **se incumple en 5 de 20 (25 %)**: 1 cortada + 4 entregadas tarde |
| **Plazo operativo** (`PRESUPUESTO_CONSULTA_MS`) | **8.000 ms** | **corta 1 de 20 (5 %)** |
| p50 / p95 / media | | **3.893 / 7.494 / 4.456 ms** |

Con el plazo en 5.000 esas mismas 20 consultas se cortaban **6 veces (30 %)**. O sea que subir el plazo no cambia lo que el sistema tarda: cambia **cuántas respuestas se tiran a la basura después de haberlas pagado**.

**LA BRECHA, DESGLOSADA, porque un objetivo incumplido sin desglose es una queja:** +1,3 s la vía vectorial completa frente a solo léxica, +0,4 s el reordenador, ~0,13 s el NLI. **La latencia está en la GENERACIÓN, no en la recuperación**, así que las palancas son la **longitud de la respuesta** o el **modelo** — nunca recortar el contexto, que es de donde sale la calidad. Y **el reordenador NO se toca para ganar sus 0,4 s**: su beneficio de calidad sigue sin medir porque espera el conjunto oro, y quitarlo ahora sería elegir por coste sin tener el dato del beneficio, que es justo la decisión que el criterio del 80,9 % existe para no tomar a ciegas. **[SUPERADO EL MISMO 14/08, unas horas después: llegó el conjunto, el beneficio se midió —56,0 % contra listón 70,0 %, peor que sin reordenar— y el reordenador quedó descartado por su propio criterio (3.4, ADR 0019). No tocarlo por coste sin el dato era correcto; en cuanto hubo dato, decidió él, y los 0,4 s vinieron de regalo.]**

**[SUPERADO POR LA REVISIÓN DE ARRIBA (14/08): el requisito de producto vive en
`OBJETIVO_CONSULTA_MS`=5000 y el plazo operativo donde se corta es 8000. El párrafo siguiente se
conserva como la decisión del 13, que la medida del 14 revocó.]** **`PRESUPUESTO_CONSULTA_MS` =
5000 ES UN REQUISITO DE PRODUCTO, NO UN PARÁMETRO DE AJUSTE.** Los 8.000 ms iniciales eran un
número de holgura puesto antes de tener ninguna medida; el requisito es que **la consulta de punta
a punta no pase de 5 segundos**, y todo lo que compita por ese presupuesto se juzga contra él. Con
el tope a 5.000, la tabla del reordenado (3.4) se lee sola: la GPU cabe (3.630 ms, 73 %) y ninguna
CPU cabe ni de lejos.

**Y un tope se cumple en p95, no en p50.** Los 3.076 ms del 3.3 son una media de pocas corridas y el
tiempo del modelo varía mucho más que el nuestro, así que **el p95 de punta a punta es un número que
hace falta y hasta hoy no existía**: se mide con n≥20 y se reporta al lado del presupuesto. Sin él,
"cabemos en 5 s" es una afirmación sobre el caso bueno.

**MEDIDO EL 13 DE AGOSTO CON n=20: p50 5.151 ms y p95 63.853 ms. NO SE CUMPLE, y no solo en la cola.**
Entre el **30 y el 40 %** de las consultas pasan de 5 s en las dos corridas hechas. **El presupuesto
se HACE CUMPLIR** desde este encargo —`app/api/consulta.py` corta y lo anuncia, con su test—, así que
la congelación de un minuto ya no puede ocurrir; pero cortar tiene su precio y está medido: **se corta
el 30 % de las respuestas**.

**LA CAUSA, DESGLOSADA Y NO CONJETURADA** (`docs/evidencia/2026-08-13-concurrencia.md`, corrida 10).
La espera hasta la prosa se reparte en tres tramos con palancas distintas, y medirlos **descarta dos
de los tres sospechosos**:

| Tramo | Enteras | Cortadas | Veredicto |
|---|---:|---:|---|
| Prefill + cola del proveedor | 292 ms | 276 ms | **no es**: idéntico, y es el 6 % del plazo |
| Afirmaciones | 2.871 ms | **4.525 ms** | **es esto** |
| ↳ tokens | 347 | **541** | +56 % |
| ↳ ritmo | 110 tok/s | **119 tok/s** | **no es el proveedor**: las cortadas van más rápido |

**No es el prefill** —bajar de 6 fragmentos a 4 ahorraría ~100 ms de 5.000 y pagaría recall por
nada— **y no es el proveedor** —las que se cortan generan incluso más deprisa—. **Es la verbosidad**:
las cortadas escriben un 56 % más antes de llegar a la prosa. Y dentro del bloque, **la `cita`
literal es el 55 % del contenido** (mediana 128 caracteres, máximo 445): texto que el servidor ya
tiene, porque es copia del fragmento que él mismo mandó.

**Reparto del plazo:** recuperación ~700 ms (15 %), prefill 292 ms (6 %), **afirmaciones 2.871 ms
(60 %)**, prosa que el alumno lee 823 ms (17 %). **El 60 % de la espera es texto que el alumno nunca
ve como prosa.**

### LAS TRES SALIDAS, CON SU COSTE ESCRITO

**(a) MANTENER EL ORDEN Y ACEPTAR EL INCUMPLIMIENTO.** El argumento del ADR 0009 sigue en pie: la
prosa antes que los hechos convierte las afirmaciones en **justificación a posteriori**, que es
exactamente lo que este proyecto existe para no hacer. Y la espera no está vacía: desde ~700 ms la
pantalla enseña los seis fragmentos recuperados, que es lo que el 2.4 diseñó. **Cuesta incumplir el
requisito de 5 s en un tercio de las consultas**, con el corte anunciado en pantalla.

**(b) INVERTIR EL ORDEN.** Gana dos o tres segundos y **cuesta más de lo que parece**: con la prosa
primero se emite texto **antes de saber si sus afirmaciones verifican**, así que la retirada —hoy
excepcional— pasaría a ser rutina. Un sistema que se desdice a menudo es peor que uno lento.
**Descartada.**

**(c) PARTIR LA GENERACIÓN EN DOS LLAMADAS:** afirmaciones, **verificación en medio**, y la prosa
generada solo a partir de lo que pasó.

> **FICHA ACTUALIZADA EL 13 DE AGOSTO Y CORREGIDA: (c) YA NO ES EL DESTINO PROBABLE.** Se escribió
> como "la forma arquitectónicamente correcta", y su beneficio visible —que el alumno vea las
> afirmaciones **con su veredicto** antes que el texto— **ya está entregado sin partir nada**: como
> `afirmaciones` va antes que la prosa en el contrato, el array está **cerrado** cuando empieza el
> texto, así que el 4.2 verifica y emite un evento `veredicto` **por afirmación mientras el modelo
> sigue escribiendo**. El literal es instantáneo; el NLI del 4.3 tarda ~350 ms; la prosa sigue ~823.
>
> **Y con eso (c) pasa de ahorrar latencia a COSTARLA:** verificación en serie en vez de en solape,
> **más un segundo prefill**. Lo único que seguiría comprando es **prosa generada solo a partir de
> afirmaciones ya verificadas**, que es un beneficio real —hoy la prosa puede apoyarse en una
> afirmación que después se poda— **pero ya no viene con descuento**. Queda declarada como opción
> con su coste, no como destino.

### DECISIÓN, TOMADA CON EL DESGLOSE DELANTE: **(a)**, con el requisito declarado como NO CUMPLIDO

**El requisito de punta a punta en 5 s NO se cumple: se corta entre el 30 y el 40 % de las
consultas.** Va escrito con su número aquí, en el README y en la evidencia, y **no se suaviza ni se
borra**: un requisito incumplido y declarado es un problema conocido; uno incumplido y maquillado es
una sorpresa esperando a la sesión.

Se elige (a) porque **la (b) empeora lo que el proyecto defiende** y la (c) es un rediseño que no se
mete a tres días de una demo. Y con una condición que sale del propio desglose: **antes de volver a
tocar el plazo se ataca la verbosidad**, que es la única palanca medida que no toca ni el orden del
contrato ni sus garantías.

**Y la palanca está identificada por causa, no por sospecha (corrida 11):** las cortadas hacen
**×1,12** afirmaciones —o sea las mismas— pero con **×2,3 caracteres de cita por afirmación** (88
contra 202). **No es cuántas, es cuánto ocupa cada una.** Así que el prompt de "haz menos
afirmaciones" no arreglaría nada y el tope a la cita sí.

**FORMA DEL ARREGLO, que importa tanto como el número:**

1. **`maxLength` en el ESQUEMA, no una petición en el prompt.** La gramática lo impone y el prompt
   solo lo pide; el 2.2 ya enseñó que un campo que la gramática permite es un campo que el modelo
   rellena (principio 7). Con la mediana sana en 88 caracteres, un tope de **~120** no toca ninguna
   respuesta buena y parte por la mitad las atípicas.
2. **La cita SIGUE SIENDO TEXTO. Nada de desplazamientos.** La alternativa obvia —que el modelo
   mande `inicio` y `fin` dentro del fragmento y el servidor extraiga— ahorraría casi todo el coste
   y **destruiría la verificación**: si el servidor saca `texto[inicio:fin]` del fragmento que él
   mismo mandó, la comprobación literal del 4.2 es **verdadera por construcción**, y el fallo se muda
   a "señalar el tramo equivocado", que una comparación de cadenas no puede cazar. Cambiar un fallo
   comprobable por uno invisible es el peor negocio posible en este proyecto.

Es trabajo del **4.1** y se re-mide después.

**LA PREDICCIÓN DEL PROPIETARIO, ESCRITA EL 13 DE AGOSTO ANTES DE MEDIR NADA, que es cuando predecir
es predecir y no explicar:**

> Capar a 120 ahorra ~371 caracteres en las cortadas, unos **93 tokens**, unos **780 ms** a 119
> tokens/s. Eso baja el TTFT de 4,6-4,8 s a **~3,9-4,0 s** y el total de ~6 s a **~5,2 s**.
> **Predicción: el corte BAJA pero NO por debajo del 10 %; se espera entre el 15 y el 25 %, y por
> tanto que la salida (c) siga urgente.**

**RESUELTA el 13 de agosto de 2026 por la tarde, sobre código actual: 11,5 % (3 de 26).** No baja del 10 %, así que el trato no se activa; pero **queda por debajo de la banda predicha de 15-25 %**, o sea que el tope de la cita hizo **más** efecto del estimado. Acierto parcial, con su n=26 al lado, que es pequeña. Y el número histórico que sustituye —29,7 % sobre 165— era una muestra elegida por **cuándo**: mezclaba versiones anteriores al tope, al vigilante y al plazo.

**Y UNA TERCERA, DEL 4.5, TAMBIÉN FALLADA Y POR QUEDARSE CORTA:** se declaró que un falso negativo de la regla de cobertura *"poda una frase legítima y deja un agujero en mitad de un párrafo"*. Medido el 14 de agosto: **se lleva el párrafo entero**. En el conjunto del 5.0, **5 de 20 respuestas salieron completamente vacías** por esa puerta —una de ellas correcta, con su fragmento citado y entregada en 1,7 s—, y encima con `abstencion: False`. La asimetría era **peor** de lo que su propia declaración decía, y el arreglo no fue el umbral sino la medida.

**Y OTRA PREDICCIÓN DEL PROPIETARIO, FALLADA Y DECLARADA COMO TAL:** *"responder solo con `conocimiento` marcado será el caso intermedio más frecuente"*. Medido: **0 de 114** respuestas con afirmaciones factuales. Cuando el sistema responde, **siempre** tiene al menos una afirmación anclada al temario — mejor noticia que la predicción, y va escrita aquí porque un pronóstico que solo se cita cuando acierta es una anécdota.

**El trato, y vale en las dos direcciones: si el corte baja del 10 %, la predicción falla y se
declara fallada.** Un pronóstico que solo se cita cuando acierta no es un pronóstico, es una
anécdota; y esta lleva su aritmética delante para que se pueda auditar dónde se torció si se tuerce.
El número sale **baje o no baje**.

Cambiar la URL base a vLLM local o a un pool de producción no toca código: ese es el enchufe del principio 1.

---

# PARTE IV: FASES Y ENCARGOS

## Fase 0: constitución del repo

**0.1 Repo y estructura.** Crear repo privado `marcosmatalab/<nombre>` (nombre de trabajo libre; la publicación es decisión aparte con OK propio). Estructura:

```
CLAUDE.md  guia-definitiva.md  README.md  docs/adr/
corpus/           (contenido pesado FUERA de git: .gitignore; manifiesto DENTRO)
ingesta/  app/api/  app/core/  app/modelos/  app/datos/  web/
evals/casos/  evals/arnes/  deploy/  scripts/  tests/
```

Copiar esta guía dentro. Escribir `CLAUDE.md` desde el Apéndice A. Verificación: `git remote -v` correcto, árbol limpio. Commit inicial.

**0.2 CI.** GitHub Actions: en cada push, `ruff check` (reglas F821 y F401 incluidas) y `pytest`. Secrets del repo para `INFERENCIA_API_KEY` (los flujos de CI que llaman al proveedor se marcan y solo corren a demanda). Verificación: primer push en verde. **Decidido al ejecutarlo:** el flujo del proveedor NO se crea en este encargo. Hoy no hay ni cliente de inferencia ni cuenta, así que solo podría comprobar que el secreto está puesto, que no es comprobar que la clave funciona: sería un flujo que nunca se ha visto pasar, justo lo que el principio 3 prohíbe. Se crea en el encargo 2.2. El CI dispara en TODAS las ramas, no solo en main: un resultado que llega en el merge llega cuando ya no sirve.

**0.3 Compose local.** `docker compose up` levanta db (con extensiones creadas), redis, api (hola mundo), worker (ping). Healthchecks y arranque ordenado (`depends_on` con condición). Verificación: `GET /salud` en verde desde cero en máquina limpia. **Decidido al ejecutarlo:** los puertos del host se eligen midiendo la máquina, no por costumbre (aquí db acabó en 5434 y redis sin publicar); `/salud` comprueba además que las extensiones existen, porque `docker-entrypoint-initdb.d` solo corre con el volumen vacío y un volumen viejo pasaría por bueno con Postgres sano y sin `vector`; y `corpus/` no se monta en ningún contenedor, que la ingesta vive en Windows con la GPU.

**Cierre de fase 0:** clon limpio a entorno funcionando con un comando; CI verde.

**Qué significa exactamente "entorno funcionando", escrito para que nadie lo reinterprete más adelante:** `docker compose up -d --wait` levanta db, redis, api y worker desde un volumen vacío, y `GET /salud` responde 200 con sus cuatro dependencias en verde (base de datos, extensiones `vector` y `pg_trgm`, redis y worker). **SIN corpus, y el corpus no forma parte de este criterio:** un clon limpio no lo tiene, porque está fuera de git por diseño (~390 MB, parte con licencias no redistribuibles). Cargar el corpus es la fase 1, y el arnés que lo mide es suyo. Confundir ambas cosas convertiría el cierre de la fase 0 en algo que ningún tercero puede reproducir, que es justo lo contrario de lo que este criterio existe para garantizar.

## Fase 1: corpus y casos (nada de tubería hasta cerrar esto)

**Punto de partida: el paquete `corpus-daw.zip` (v3-2026-08-11, los tres grados) ya existe y adelanta parte de esta fase.** El árbol viene YA recolocado por titulación (`corpus/daw/`, `corpus/dam/`, `corpus/asir/`, `corpus/familia/`), o sea el paso 1 del encargo 1.12 está hecho. Dentro de `daw/`: normativa BOE (RD 686/2010 y Orden EDU/2887/2010 en PDF), Programación completa (lionel-ict), DWES 2025-2026 completo (joseluisgs 00 a 05, markdown) y el DWES antiguo de Comesaña marcado `plantado: true`. Dentro de `dam/apuntes/` y `asir/apuntes/`: las titulaciones hermanas a densidad parcial (temario DAM de Comesaña podado a material didáctico; ASIR con lora-1asir, lora-2asir y aberlanas-iso con su LICENSE), y `familia/` con el índice de la familia profesional. En v3, DAW trae además sus módulos restantes con el material de Comesaña podado (sistemas informáticos, bases de datos, lenguajes de marcas, entornos de desarrollo, FOL, DWEC, despliegue, DIW y EIE; Programación SIN versión antigua a propósito: las contradicciones solo viven plantadas), y `corpus/COBERTURA.md` es el mapa módulo a módulo de las tres titulaciones con fuentes, transversales y los dos huecos declarados (0616 Proyecto de DAW y 0489 PMDM de DAM). El `manifiesto.jsonl` (2.094 entradas: ruta, fuente, licencia, hash SHA-256, densidad, plantado; 16 plantadas) está verificado contra disco con cero huecos, e incluye la regla de licencias del 1.12 aplicada (los repos sin licencia declarada van marcados como uso local no redistribuible). Estado de los encargos con este paquete: **1.1 parcialmente cubierto** (queda el RD 405/2023 con su script, los PDF del RD 450/2010 y RD 1629/2009 en `dam/normativa/` y `asir/normativa/` donde los POR-DESCARGAR.txt lo indican, y cargar los árboles en `asignaturas` desde los anexos), **1.2 cubierto** (manifiesto completo y verificador en verde comprobando rutas y hashes, ya con el encargo 1.0 hecho), **1.7 parcialmente cubierto** (par contradictorio real dentro; quedan duplicados y el documento colado), **1.12 pasos 1 y 3 cubiertos** (recolocación hecha y apuntes de hermanas dentro; quedan la normativa de DAM y ASIR, la carga en `asignaturas` y el selector). El resto de encargos, de 1.3 en adelante, se hacen tal cual. Claude Code parte de este paquete descomprimido en la raíz del repo: no re-descarga lo que ya está en el manifiesto.

**1.0 El verificador de manifiesto comprueba hashes, no solo rutas (PRIMER ENCARGO DE LA FASE, añadido tras el encargo 0.1).** `scripts/verificar_manifiesto.py` cruza hoy los conjuntos de rutas de disco y manifiesto, y nada más: un fichero alterado, truncado o copiado a medias pasa su verde sin despeinarse. Es un detector que nunca se ha visto disparar sobre un fichero alterado, o sea que todavía no es un detector (principio 3). El precedente que lo hace urgente: los 249 ficheros con el nombre destrozado por el descompresor se repararon con `scripts/reparar_nombres.py`, que empareja por SHA-256 del CONTENIDO; lo que garantizó la integridad de aquella reparación fue el hash del reparador, no el verde del verificador, que habría dado por buena una copia truncada. Trabajo: comprobar el `hash_sha256` de cada entrada además de la ruta; salida distinta de cero ante cualquier discrepancia; e informe que separa rutas huérfanas de hashes cambiados (ocurrencias y hallazgos por separado). Verificación: **test de regresión anclado que altera un byte de un fichero y exige rojo**, más el caso íntegro que exige verde, ambos sobre un corpus de juguete en directorio temporal para que corran en CI sin el corpus real. ADR corto con el coste medido de hashear el corpus entero (2.097 ficheros, ~390 MB) y, si molesta en bucle, una bandera `--solo-rutas` declarada como lo que es: el modo débil.

**1.1 Normativa oficial: el árbol a fichero, no a base de datos.** Los PDF de los reales decretos y currículos (BOE: dominio público) viven en `corpus/<titulacion>/normativa/`. Extraer de ahí el árbol oficial de CADA titulación: cursos, asignaturas (con su código de módulo), unidades y resultados de aprendizaje, **a un fichero de datos versionado en git**, con la referencia legal (norma, anexo, página) en cada nivel. El esqueleto en disco sigue siendo `corpus/<titulacion>/<curso>/<asignatura>/<unidad>/`.

**Corrección de orden, hecha antes de empezar el encargo:** la versión anterior de este encargo mandaba cargar `asignaturas` y la puente `titulacion_asignaturas`, pero esas tablas no existen hasta el encargo 2.1 (esquema y migraciones). Era un encargo que no se podía ejecutar en su turno. Así que 1.1 produce el fichero y **2.1 lo carga**. Además de arreglar el orden, se gana lo que una tabla no da: el árbol se revisa con `diff` en cada cambio, no depende de que Postgres esté levantado, y sobrevive a un `down -v`.

**Fuentes, que no son las mismas para las tres y hay que acertar:** DAW y DAM salen de sus reales decretos de 2010 **actualizados por el RD 405/2023**, que los modifica; sacar DAW del 686/2010 a secas daría un árbol desfasado sin que nadie se entere. ASIR sale de su RD 1629/2009, al que el 405/2023 no toca. Y hay una asimetría de fuente que **se declara en `corpus/COBERTURA.md` junto al árbol, no se disimula**: DAW tiene además la Orden EDU/2887/2010, que amplía contenidos módulo a módulo, mientras que de DAM y ASIR solo existe el Anexo I de su real decreto. Consecuencia: las unidades de DAW salen más finas que las de las hermanas, y eso es la fuente hablando, no un fallo del extractor.

**Límite de esfuerzo, no de alcance (decidido para este encargo):** se extraen las tres titulaciones hasta unidades. Si el extractor se atasca con algún documento, se cierra con lo que haya, se declara en `COBERTURA.md` qué quedó fuera y se sigue. Motivo: el árbol de las hermanas se puede afinar después sin tocar nada de lo construido encima, y lo que no puede pasar es que este encargo se coma el día que necesita el corpus curado.

**Los módulos transversales** (mismos códigos en varios títulos, como marca el propio Anexo II) se marcan en el fichero con su titulación dueña, y el 2.1 los carga UNA sola vez y los mapea por la puente: nunca se duplican sus fragmentos. Verificación: conteo de asignaturas por curso y titulación contra el texto legal, y muestreo a mano de nodos contra su página del BOE.

**1.2 Recolección con manifiesto.** Para las dos asignaturas de densidad completa, recopilar fuentes por orden de prioridad: (a) normativa, (b) documentación con licencia abierta de las tecnologías del temario (documentación oficial de lenguajes y plataformas, materiales Creative Commons, citando licencia y atribución por documento), (c) apuntes propios donde falte densidad. Cada documento entra en `corpus/manifiesto.jsonl` con ruta del árbol, fuente, licencia, versión y hash. **Sin entrada en el manifiesto no entra en el corpus.** Verificación: script `scripts/verificar_manifiesto.py` cruza disco contra manifiesto en las dos direcciones y sale distinto de cero ante cualquier hueco.

**1.3 Normalización.** Todo a markdown o texto limpio (conversión de PDF y HTML con revisión por muestreo: 10 documentos al azar leídos a ojo). Verificación: cero binarios en el árbol de texto; muestreo anotado en el ADR de la fase. **Decisión ya tomada (ADR 0004), que estaba planteada desde el 1.1:** cada fichero convertido entra con **entrada propia y campo `derivado_de`** apuntando a su original, que se conserva intacto. Se descartó que el convertido sustituyera al original (se perdería la evidencia y su licencia declarada) y que su hash viajara dentro de la entrada del original (rompería la regla de una entrada por fichero, que es el invariante sobre el que se apoya la puerta del 1.0). Con dos condiciones: la entrada del derivado registra **herramienta y versión exacta**, porque la conversión de PDF no es determinista entre versiones y sin ese dato la puerta se pondría roja sola al actualizar una librería; y los derivados viven en un **árbol espejo** (`corpus/derivado/...`), no junto al original, para que lo derivado sea borrable y regenerable entero y la fuente quede intacta. El derivado hereda licencia, densidad y marca `plantado` del original.

**Prioridad de este encargo, por el reloj:** primero **Programación (0485)**, que es la asignatura curada que falta por normalizar y donde van a vivir los casos. Después el DWES antiguo de Comesaña y el material parcial de DAM y ASIR; si no llegan, se declaran en `COBERTURA.md` y se sigue.

**1.4 Troceado y contexto.** Troceado recursivo de 512 tokens con solapamiento inicial de 64. A cada fragmento se le antepone su línea de contexto: título del documento más ruta del árbol (titulación, curso, asignatura, unidad). Esa línea forma parte del texto que se embebe. `tipo_contenido` asignado por reglas (definición, procedimiento, ejemplo resuelto, normativa) con revisión por muestreo. Verificación: distribución de longitudes de fragmento sin colas absurdas; 20 fragmentos al azar leídos a ojo con su contexto.

**DEUDA DECLARADA CON SU NÚMERO, encontrada al ejecutar el 2.6 el 12 de agosto de 2026: la `frase_definitoria` se deja fuera lo que más falta hacía.** El glosario del 2.6 no encontró el par contradictorio real de MVC, y el diagnóstico no apunta al glosario sino a esta señal: **de los 260 fragmentos del 0613 que mencionan MVC, solo 16 llevan `frase_definitoria`, y ninguno de esos 16 define la Vista.** O sea que las dos definiciones incompatibles —el material que sostenía la versión A del momento 3 de la demo— **nunca llegaron a ser candidatas**: se pierden aquí, un encargo antes. La extracción y la validación literal del 2.6 funcionaron sobre lo que sí les llegó (636 entradas, 27,6 % de descarte). Lo que faltaba era de dónde extraer.

Queda escrito aquí y no solo en el informe del 2.6 **para que quien reabra el corpus sepa qué se buscaba y no se encontró**. Cuando se reabra, la señal se revisa con ese caso delante como prueba anclada: si al arreglarla las dos definiciones de la Vista aparecen como candidatas, el caso `conocido-mvc-vista` de `evals/casos/conflicto.jsonl` —hoy declarado en rojo a propósito— se pone verde solo. No se toca ahora porque el corpus está cerrado y la sesión es el lunes.

**Tres decisiones tomadas antes de empezarlo:**

1. **La unidad del fragmento sale de la carpeta del material, no del árbol del BOE, y se declara como tal (ADR 0005).** Son dos taxonomías distintas: el profesor titula "Unidad 4 Introducción a Java" y el BOE titula esa misma materia "Utilización de objetos". No hay mapeo automático fiable entre ellas y no se intenta aquí. **La partición y el filtro van por ASIGNATURA**, que sí casa entre las dos, y el árbol oficial se queda donde vale: referencia normativa para el selector del alumno y para el guiado del recorrido, jamás etiqueta de fragmentos. Cruzar ambas taxonomías es trabajo aparte, y hasta que exista se declara como no construido.
2. **El código entra al corpus con regla propia.** Los ~360 ficheros de código (217 solo en Programación) son soluciones de ejercicios: en un módulo de Programación eso es contenido de primera, y además alimenta el verificador por ejecución de la fase 4. Regla: **un fichero de código es UN fragmento si cabe; si no cabe, se parte por clase o por método, jamás por ventana ciega**, y lleva `tipo_contenido: codigo`. Trocear código cada 512 tokens lo destroza y produce fragmentos que no compilan ni se entienden.
3. **Los 512 tokens INCLUYEN la línea de contexto.** Medida con el tokenizador real, esa línea cuesta entre 26 y 32 tokens (media 29), así que al cuerpo del fragmento le quedan unos 480. Se cuenta dentro y no aparte porque lo que se embebe es el fragmento entero, contexto incluido: si el presupuesto fuera solo del cuerpo, el vector real llevaría 540 tokens y el "512" del README sería un número que no existe. El tamaño se declara así en la métrica de la fase: 512 totales, ~480 de cuerpo.
4. **Los 512 tokens se cuentan con el tokenizador REAL de BGE-M3**, no con una estimación por palabras o caracteres. Medido: la prosa castellana cunde 4,6 caracteres por token y el código 2,3, o sea que una estimación uniforme se equivoca al doble justo en el material de Programación. Si el troceado y el modelo no cuentan igual, el tamaño de fragmento del README no es el que existe.

**1.5 Embeddings en la 5080.** **Windows nativo, NO WSL2** (corrección de la versión anterior de este encargo): el corpus y la tarjeta están en Windows y PyTorch con CUDA corre nativo ahí. WSL2 solo hace falta para vLLM, que es de la fase 7, y meterse en ese berenjenal ahora no compra nada. **Comprobación previa obligatoria, antes de lanzar ninguna tanda:** la 5080 es Blackwell y exige ruedas de PyTorch con CUDA 12.8 o superior, así que se instala desde el índice correcto y se verifica que `torch.cuda.get_device_capability()` reconoce la tarjeta. Eso se sabe en un minuto; descubrirlo a los veinte de una tanda de embeddings cuesta la tanda. Después: BGE-M3 vía sentence-transformers, proceso por lotes con reanudación (si se corta, continúa donde iba). Salida a Postgres con `COPY`. Medir y anotar: fragmentos por segundo, tiempo total, y la extrapolación a un tera (ese número va al README como coste de ingesta). Verificación: conteo de embeddings igual a conteo de fragmentos; norma de 10 vectores al azar razonable; búsqueda de humo ("qué es una clave primaria" devuelve fragmentos de la unidad correcta).

**Orden de ejecución alterado a propósito: 1.7 → 1.8 → 1.6.** Los números se quedan como están (los citan COBERTURA.md, los ADR y el histórico de commits, y renumerar convertiría cada referencia en una trampa), pero **el glosario se hace DESPUÉS de la basura plantada y del detector de conflictos**, por dos motivos. El primero es el mismo por el que se ancló la revisión de BGE-M3: las entradas del glosario acaban **citadas a un alumno**, así que tienen que generarse con el modelo declarado en la configuración —el pequeño de Scaleway— y no con uno de paso que obligaría a rehacerlas; y hoy no hay ni cuenta ni `INFERENCIA_API_KEY`. El segundo es de valor: **1.7 y 1.8 alimentan el momento 3 de la demo** (el conflicto plantado), no necesitan proveedor y se pueden hacer ya.

**1.7 Basura plantada.** Plantar, etiquetado en el manifiesto como `plantado: true`: (a) tres documentos casi duplicados de otros existentes con cambios menores, (b) dos versiones contradictorias del mismo concepto (por ejemplo, una definición con la sintaxis antigua de una tecnología y otra con la vigente), (c) un documento de otra asignatura colado en la carpeta equivocada (para medir contaminación). Verificación: el manifiesto lista exactamente lo plantado.

**1.8 Detector de conflictos (en ingesta, jamás en respuesta).** Near-duplicados por similitud de embeddings dentro de cada asignatura (umbral inicial 0,95) más contradicción por NLI entre fragmentos muy similares que no son duplicados.

**Qué se persiste, y por qué no basta con la marca.** La tabla `conflictos` guarda **los dos fragmentos, la similitud, el veredicto del NLI con su probabilidad, y la fecha o versión de cada fuente**. Detectar es la mitad del trabajo: la otra es qué se le dice al alumno que pregunta por MVC y tiene dos versiones en su temario. Sin la fecha de cada fuente, la fase 4 no puede ordenar nada y solo sabe decir "hay lío".

**Criterio de presentación (se decide aquí y lo aplica el 4.5): se enseñan LAS DOS versiones, cada una con su fuente y su fecha, y se declara el criterio de preferencia —la más reciente— sin que el sistema se arrogue la verdad.** Señala el conflicto y ordena por vigencia; no dictamina cuál es correcta. Y hay una razón concreta para no ir más allá: **en la contradicción sintética del 1.7 el material plantado es el técnicamente correcto y el temario oficial es el que va suelto** (los objetos en Java no se pasan por referencia). Cualquier regla del tipo "gana el material oficial" fallaría justo ahí, y fallaría en silencio. Ordenar por vigencia es defendible y comprobable; dictaminar quién tiene razón exigiría una autoridad que este sistema no tiene y no se va a inventar.

**Exclusión obligatoria, escrita aquí antes de que explote:** el troceado del 1.4 solapa 64 tokens, así que **cada par de fragmentos consecutivos del mismo documento comparte texto POR CONSTRUCCIÓN**. Un detector de casi-duplicados por similitud los marcaría a miles y enterraría el hallazgo real bajo su propio ruido. Por eso los pares consecutivos del mismo documento se excluyen por diseño, no se filtran a posteriori por umbral. Es el principio 6 otra vez: **el detector tiene que saber qué duplicación es artefacto suyo**, porque si comparte con el troceador el supuesto de que "texto repetido es sospechoso", es ciego justo donde el troceador ya sabía la respuesta. La exclusión se prueba en el test anclado: con la basura plantada dentro, el detector encuentra los plantados y NO los solapes. Escribe en `conflictos`. **Validación obligatoria del principio 3: el detector debe dispararse sobre la basura de 1.7 antes de creerse ningún cero.** **Medido al ejecutarlo, y con consecuencia para la demo:** la similitud entre trozos MÁS el NLI encuentra la contradicción plantada (0,99, señalando las dos frases que chocan), los casi duplicados que pasan el umbral y el colado, pero **NO encuentra el par contradictorio REAL del corpus**: los dos fragmentos con las definiciones incompatibles de MVC tienen similitud 0,564, porque cada definición va enterrada en un trozo de 512 tokens lleno de otra cosa. Para verlo hay que comparar DEFINICIONES DEL MISMO TÉRMINO, que es lo que produce el glosario del 1.6. **Así que el momento 3 de la demo depende del 1.6, no de este encargo**, y eso está declarado en COBERTURA.md con los números. Lo que este detector sí da, y es mucho, es el aviso de duplicación y contaminación en ingesta y los candidatos a contradicción ordenados por probabilidad para revisión humana. Test de regresión anclado: sobre el corpus con basura, el detector encuentra exactamente los plantados (número exacto en el test). Verificación: test en verde y anclado.

**1.6 Glosario → SE EJECUTA COMO 2.6, al cerrar la fase 2 y justo antes de la 3.** Movido el 12 de
agosto de 2026, con el proveedor ya configurado. Dos motivos, y el segundo manda: el glosario se
**consulta en paralelo a la recuperación** (encargo 3.3), así que su sitio natural es pegado a la
fase que lo usa; y el momento 3 de la demo depende de él, o sea que no puede quedarse al final de
la cola. El enunciado completo vive ahora en **2.6**; lo que sigue se conserva porque es el
contrato que allí se ejecuta. Extracción en ingesta: para los fragmentos con `tipo_contenido` definición, un prompt de extracción al modelo pequeño produce `{termino, definicion, fragmento_id}`. **La validación NO puede hacerla el modelo que extrajo** (principio 6: el que comprueba no comparte el supuesto del que produce; preguntarle al mismo modelo si su propia definición está en el fragmento es un eco, no una comprobación). Es independiente y por dos caminos según el caso: **comparación de cadenas normalizada, sin modelo**, cuando la definición es literal del fragmento, y **NLI distinto del extractor** (mDeBERTa-v3-base-xnli, premisa = fragmento) cuando es paráfrasis.

**SECUENCIA DE LAS DOS VÍAS, decidida el 12 de agosto de 2026 y no negociable por comodidad: primero la literal SOLA, y se mide.** Si un glosario que solo admite definiciones literales encuentra el par de MVC en las tres corridas, **la vía NLI no entra en este encargo**: no hace falta meter mDeBERTa en la ruta crítica a cinco días de la sesión, y sobre todo **la garantía es más fuerte, no más débil**, porque entonces no hay ningún modelo en el lazo de verificación —cada entrada se comprueba con una comparación de cadenas y se acabó—. Si no lo encuentra, se decide **con el número delante** entre añadir la vía NLI o irse al plan B del momento 3. El NLI llega igualmente en el **4.3**, donde ese modelo tiene que existir de todas formas.

**CÓMO SE ENCUENTRA EL PAR CONTRADICTORIO, que no es re-ejecutar el 1.8.** Aquel detector compara **fragmentos por similitud de embeddings**, y ahí el par de MVC da 0,564 justamente porque cada definición va enterrada en 512 tokens de otra cosa: por eso el momento 3 dependía del glosario y no de él. Lo que hace falta es una comparación **nueva, cuya clave es el TÉRMINO y no el vector**, y desde el ADR 0012 esa comparación es una consulta: `GROUP BY termino HAVING count(*) > 1` sobre `glosario`. Determinista, sin modelo, sin umbral. **Heredar el mecanismo del 1.8 aquí sería repetir el error que aquel encargo ya dejó medido.**

**Y la decisión del momento 3 no se toma con una corrida: se corre TRES veces y el par tiene que salir las tres.** La extracción usa el modelo, y el modelo no es determinista ni a temperatura cero —está medido en el 7.1—. Un momento 3 que sale dos de tres es un momento 3 que falla en directo. Si no sale las tres, va el plan B y se acabó la duda, que para eso se decidió por adelantado. La entrada que no pasa su validación no entra: el glosario no puede contener lo que el corpus no dice, y esa es justo la regla que lo hace citable. Verificación: 100% de entradas del glosario pasan su propia validación; **tasa de descarte anotada con su dispersión sobre las tres corridas** —es una métrica que mira contenido, y la regla del 7.1 dice que esas no van como número único— y con la lectura de siempre, que dice más del extractor que del corpus; muestreo a ojo de 20. **Y el coste real de la pasada, medido y no estimado**: tokens y euros sumados de todas las llamadas, aunque salga por céntimos. Con 0,000149 EUR por consulta medidos en el 2.2 debería ser calderilla, pero es la primera vez que este proyecto gasta por volumen y ese número se tiene, no se supone.

**1.9 Pares oro → SE EJECUTAN COMO 3.0, primer encargo de la fase 3.** Movidos el 12 de agosto de
2026 al cerrar la fase 1. **No desaparecen: cambian de sitio, y el motivo es lo que son.** Los 100
pares son **la verdad de referencia contra la que se miden recall@6 y nDCG@5**, y de ellos vive
entera la verificación de la fase 3: el 3.3 exige que el recall@20 de la fusión no baje respecto a
cada lista suelta, el 3.4 mide la mejora del reordenador, y el 3.5 no existe sin ellos. Etiquetar a
mano 100 pares cuesta horas de persona y **no tiene ningún consumidor hasta la fase 3**, así que
hacerlos antes solo adelanta el gasto y arriesga tener que rehacerlos si el troceado cambia —que es
exactamente lo que acaba de pasar tres veces con el corpus—. Van a **3.0**, no al final de la fase
3, porque desde el 3.1 en adelante todas las verificaciones los usan. El enunciado completo, allí.

**1.10 Los seis conjuntos de casos → REPARTIDOS, cada uno delante de quien lo consume.** Movidos el
12 de agosto de 2026, con el mismo criterio que los pares oro y por el mismo motivo: **un conjunto
de casos no vale nada hasta que hay algo que medir con él**, y hacerlo antes solo adelanta horas de
persona y arriesga rehacerlo. Todos siguen viviendo en `evals/casos/` con el formato
`{entrada, esperado, asignatura_id}`; lo que cambia es CUÁNDO se escriben.

| Conjunto | Se hace en | Porque lo consume |
|---|---|---|
| `normales.jsonl` | **3.0** | son los 100 pares oro: el mismo artefacto, no una copia |
| `conflicto.jsonl` | **2.6** | el glosario es lo que encuentra las dos definiciones enfrentadas |
| `fuera_de_temario.jsonl` · `premisas_falsas.jsonl` | **4.0** | abstención y conformidad con premisa falsa, que son la fase 4 entera |
| `corregir_desde_resultado.jsonl` · `fuga_de_solucion.jsonl` | **5.0** | los modos corregir y acompañar |

**Y uno más, que son siete y no seis desde el 12 de agosto de 2026:** `contraste.jsonl`, en el
**4.0**. No estaba en el 1.10 y no es un renombrado de ninguno: **nace de un descarte del 3.0**. Al
etiquetar los pares oro quedaron fuera las preguntas del profesor que piden contrastar dos
mecanismos, porque su respuesta vive en dos fragmentos y `recall@6` es binario contra uno. Eran
preguntas buenas descartadas por una limitación de la métrica, no por una limitación suya, así que
en vez de tirarlas cambian de encargo. Donde se dice "los seis conjuntos" en este documento se habla
del reparto del 1.10, que sigue siendo de seis; este es el séptimo y llegó después.

**Y quién los produce, que no es el mismo trabajo en los seis** —esto decide cuándo se pueden
hacer, no solo cuándo conviene—: `normales` sale de los cuestionarios y boletines del profesor que
ya están en el corpus; `fuera_de_temario`, `premisas_falsas` y `fuga_de_solucion` **se redactan sin
tocar el corpus** (son preguntas, afirmaciones falsas y trampas, y el corpus solo se usa después
para comprobar la respuesta); `corregir_desde_resultado` y `conflicto` **necesitan material concreto
del corpus**, ejercicios con resultado los primeros y los fragmentos contradictorios los segundos.

**1.11 Muestra de ingesta con OCR (OPCIONAL: no bloquea el cierre de la fase; se hace solo con la fase 4 cerrada y antes que cualquier otro extra).** Existe para parecerse al caso real del cliente, cuyos teras son binario escaneado, y para medir lo que nadie mide: cuánto degrada la veracidad cuando el corpus viene de OCR. Procedimiento: (1) tomar 30 a 50 páginas de un PDF de TEXTO ya presente en el corpus y rasterizarlas a imagen a 300 ppp, lo que simula un escaneado y regala el par de oro, porque el texto verdadero ya se conoce; (2) OCR local en la 5080 con motor abierto (Tesseract con el paquete de español como base; un modelo de visión abierto como alternativa medida si el tiempo lo permite); (3) medir CER y WER del OCR contra el texto original; (4) cargar esos fragmentos al corpus marcados con `origen: ocr` (columna en `documentos` y campo en el manifiesto) en una unidad separada; (5) medir el delta: recall@6 y tasa de afirmaciones sin respaldo sobre preguntas cuya respuesta vive en fragmentos ocr, contra las mismas preguntas sobre los fragmentos de texto originales. Entregable: cuatro números (CER, WER, delta de recall, delta de veracidad) que convierten "nuestros teras son escaneos" en una conversación con datos. La ingesta de binarios A ESCALA (OCR masivo y transcripción de vídeo) sigue siendo capacidad declarada y no construida.

**1.12 Titulaciones hermanas reales (HECHO en la fase 1).** Convierte el árbol multi-titulación en verdad medible. Pasos: (1) recolocar el corpus DAW bajo `corpus/daw/` y actualizar las rutas del manifiesto con un script, re-corriendo el verificador hasta cero huecos; (2) Marcos baja del BOE los PDF del RD 450/2010 (título DAM) y del RD 1629/2009 (título ASIR), mismos papeles que con DAW, a `corpus/dam/normativa/` y `corpus/asir/normativa/`, y de ahí se cargan sus árboles en `asignaturas` con su `titulacion`; (3) apuntes públicos a densidad parcial clonados en la máquina de Marcos (el temario DAM del mismo autor que TemarioDAW, y para ASIR los repos públicos de módulos, priorizando los que declaran licencia, como los basados en materiales del Ministerio bajo CC BY-SA); (4) todo al manifiesto con fuente y licencia por documento, y regla estricta para repos de apuntes personales sin licencia declarada: se registran como "sin licencia declarada, uso local, no redistribuible" y jamás salen del corpus local (el corpus ya no se versiona en git, así que se cumple solo); (5) el selector de la interfaz pasa a titulación, curso y asignatura. Criterio: tres titulaciones reales en `asignaturas`, manifiesto en verde, y una consulta de humo por titulación devolviendo fragmentos de la titulación correcta (la contaminación cruzada ahora se mide también entre titulaciones).

**1.13 El hueco del separador en la puerta del 1.4 (DEUDA DECLARADA el 12 de agosto de 2026, no
bloquea nada hoy).** Los patrones de `DOCUMENTOS_FUERA` en `scripts/admitir.py` se aplican a la RUTA
y separan sus palabras con `\s`, que casa con el espacio y **no** con el guion, el guion bajo ni el
punto. Un fichero llamado `guia-de-estilo.md` —la forma más normal de nombrarlo en un repositorio—
entra entero al índice. Salió al escribir el 3.0, cuando un test de juguete se puso verde donde
debía ponerse rojo.

**Y no es un caso, es una familia, que es la lección del árbol** (donde un nombre truncado
resultaron ser cuatro por dos mecanismos y ocho unidades desaparecidas): encontrar uno y no barrer
es cómo un fallo se convierte en una familia de fallos. Barrido hecho, con las magnitudes contadas
por separado: **4 sub-patrones** afectados (`guia de estilo`, `normas de entrega`, `como entregar`,
`listado de palabras`), **7 ocurrencias** de `\s` dentro de ellos, en **2 de las 3** reglas de
`DOCUMENTOS_FUERA`. Los patrones que se aplican al CONTENIDO quedan fuera del barrido y no por
descuido: ahí lo que se matea es prosa y salida de consola, y `\s` es lo correcto.

**Documentos del índice afectados hoy: CERO**, y por eso esto no se arregla desde el 3.0 —tocar la
puerta de admisión obliga a re-verificar la ingesta entera para un hueco que hoy no cambia ningún
resultado, y mezclaría dos encargos en un commit—. **Pero el cero está anclado, no anotado:**
`tests/test_admitir.py` lleva la trampa (`test_ningun_documento_del_indice_se_cuela_por_el_hueco_del_separador`,
capa con `skipif` del ADR 0001) que afirma ese cero contra el corpus real y se pone roja sola el día
que entre el primero, más un test que vigila que los cuatro sub-patrones no crezcan sin que nadie
mire. Un cero escrito en un informe se olvida; un cero anclado es una puerta.

Trabajo cuando toque: `[\s\-_.]*` en lugar de `\s*` en los cuatro, re-correr la puerta sobre el
índice y anotar cuántos documentos cambian de lado (que hoy serían cero, y ese es justo el momento
barato para hacerlo).

**Cierre de fase 1 (ejecutado el 12 de agosto de 2026).** El criterio original de esta fase pedía
también glosario validado y los seis conjuntos versionados. **Se cerró sin ellos, a propósito y con
su motivo**, y por eso el criterio se reescribe aquí en vez de darlo por cumplido:

**Y tres exigencias del criterio viejo se caen porque describen cosas que esta fase ya no contiene**,
no porque se hayan relajado:

| Decía | Por qué se cae | Qué se exigió en su lugar |
|---|---|---|
| "consultables por SQL" | la carga en base es del **2.1**, y hasta esa migración las tablas no existen | **consultable desde `fragmentos.jsonl` y `embeddings/`**, que es lo que de verdad se verificó: búsqueda de humo en las dos direcciones sobre los vectores |
| "glosario validado" | el glosario es el **2.6** | nada aquí; su criterio viaja con él |
| "los seis conjuntos versionados" | repartidos a **2.6, 3.0, 4.0 y 5.0** | nada aquí; cada conjunto lleva su criterio a su encargo |

- **Cumplido:** corpus de tres titulaciones normalizado, troceado (11.483 fragmentos admitidos de
  12.494, con puerta de admisión y su lista de descartes), embebido y **consultable desde el índice y
  sus vectores**, con la línea base de recuperación medida en las dos direcciones; manifiesto sin
  huecos con verificador comprobando rutas Y hashes y su test anclado del 1.0; árbol oficial del BOE
  en fichero con su muestreo humano y su número de acuerdo tal como salió; basura plantada declarada;
  detector de conflictos disparado sobre lo plantado con test anclado; métrica de fase, pendientes y
  cobertura por titulación en `corpus/COBERTURA.md`, que es la tabla de referencia de este cierre.
- **Movido, no perdido:** glosario a **2.6**, pares oro a **3.0**, los otros cinco conjuntos a
  **2.6, 4.0 y 5.0**, cada uno delante de quien lo consume.
- **Sigue en fase 1:** solo el **1.11** (OCR), que ya nacía opcional y con su condición escrita —se
  hace con la fase 4 cerrada y antes que cualquier otro extra—.

**El motivo del cierre anticipado, dicho entero:** la sesión con el cliente es el lunes y lo que hay
que enseñar son las fases 2, 3 y 4 funcionando. Etiquetar casos a mano contra un índice que todavía
se movía —se rehízo tres veces en una noche de arreglos— habría sido gastar horas de persona en algo
que había que repetir. **Ningún bloque de esta fase se queda sin encargo que lo consuma**, que es la
condición que hace honesto mover trabajo en vez de olvidarlo.

## Fase 2: esqueleto del servicio

**2.1 Esquema y migraciones.** El DDL de la sección 9 con Alembic. Particiones creadas por asignatura con sus índices HNSW y GIN por partición. **Aquí se carga el árbol oficial que el encargo 1.1 dejó en fichero** (`asignaturas` y la puente `titulacion_asignaturas`, con los transversales cargados una sola vez bajo su titulación dueña y mapeados por la puente): la carga vive aquí y no en 1.1 porque hasta esta migración las tablas no existen, y porque un árbol en fichero se revisa con `diff` y sobrevive a un `down -v`, mientras que uno cargado a mano en una base viva no deja rastro de qué cambió ni cuándo. Verificación de la carga: el conteo por curso y titulación en base coincide con el del fichero, y la puente lista para DAM y ASIR sus transversales de DAW. Verificación: migración desde cero en base vacía; `EXPLAIN` de una búsqueda vectorial filtrada muestra poda de particiones (que toca UNA partición, no todas: esa salida de `EXPLAIN` se guarda, es evidencia del argumento de escala).

**2.2 API con SSE.** `POST /consulta` en streaming contra el modelo pequeño SIN recuperación aún (eco verificado del contrato: el structured output del proveedor devuelve el JSON de la sección 7 y el servidor lo emite por eventos). Cliente de inferencia único con interfaz OpenAI-compatible y la URL por configuración. Timeouts y reintentos con retroceso exponencial y jitter solo en errores transitorios. Verificación: TTFT y total medidos y persistidos en `respuestas.etapas`. **Aquí se crea también el flujo de CI del proveedor que quedó pendiente del 0.2** (`workflow_dispatch`, marcado como flujo que gasta, con `INFERENCIA_API_KEY` de los secrets): una llamada real mínima contra Scaleway, vista en verde y vista en rojo con una clave mala antes de fiarse de ella.

**ORDEN DE EJECUCIÓN DE LA FASE 2, cambiado el 12 de agosto de 2026 y escrito aquí para que no parezca un despiste: 2.1 → 2.2 → 2.4 → 2.6 → 2.3 → 2.5.** El 2.4 se adelanta al 2.3 y el motivo es de dependencias y de calendario, no de gusto. **De dependencias:** el camino interactivo emite SSE desde la API y no pasa por Celery, así que la interfaz no necesita colas para funcionar; el 2.4 no depende del 2.3. **De calendario:** quedan cinco días para la sesión, el 2.4 **es** la superficie de la demo —los cuatro tipos de afirmación distinguidos a simple vista son el argumento entero puesto en pantalla— y el 2.6 decide con qué versión va el momento 3. La verificación del 2.3, en cambio, demuestra que saturar la cola de ingesta no degrada la consulta del alumno: una propiedad real de producción que **nadie va a preguntar el lunes**. El 2.3 se hace después de la demo o se recorta declarándolo, y hasta entonces la ingesta se dispara a mano. El orden de la guía es un buen valor por defecto, no una cadena.

**2.3 Colas.** Celery con **dos** colas: `ingesta` y `evals`.

**CORREGIDO EL 12 DE AGOSTO DE 2026, CON EL CÓDIGO DELANTE.** Este encargo decía tres colas, y la primera era `interactiva` (generación y verificación). Eso ya no se sostiene: el 2.2 emite SSE **desde el proceso que atiende la petición** y el 2.4 ha construido la interfaz encima de esa ruta. Aplicar el enunciado viejo obligaría a mover el camino interactivo a Celery y romper lo hecho, y a cambio no compra nada: **un flujo SSE necesita emitir desde el proceso que tiene la conexión abierta**, así que meterlo en una cola exige devolverle los tokens al proceso web por otro canal —Redis pub/sub o sondeo— para volver a emitirlos igual. Se añade un salto de red y un punto de fallo en el camino que mide el TTFT, que es justo el número que este proyecto enseña. **El camino interactivo se queda en la API. Celery se queda con el trabajo diferido, que es el que de verdad lo necesita.** Prioridad: la ingesta jamás compite con la latencia del alumno, y ahora eso es una propiedad del despliegue —procesos distintos— y no de una configuración de prioridades.

Idempotencia por clave de deduplicación en trabajos de ingesta, **y esa clave es el par `(ruta, hash_sha256)` de la sección 10, no el hash solo** (ADR 0008): aquí es donde se implementa. Verificación: saturar `ingesta` con 100 trabajos y comprobar que una consulta interactiva no se degrada.

**Este encargo NO bloquea el cierre de la fase 3** (ver la decisión escrita en el 3.5): el arnés corre como script contra la base. Su sitio es después de la demo del lunes, y si el calendario aprieta se recorta declarándolo.

**2.4 Interfaz mínima.** Una página servida por la API, sin framework pesado: selector de curso, asignatura y modo; chat con streaming SSE; y las afirmaciones renderizadas por tipo (literal entre comillas con referencia clicable que abre el fragmento, paráfrasis con fuente, `conocimiento` con marca visible, cálculo con su verificación). La interfaz ES parte del argumento: el efecto de la demo depende de VER los tipos separados.

**LA VERIFICACIÓN SE PARTE EN DOS, Y CADA MITAD DICE SOBRE QUÉ CORRE.** "Los cuatro tipos se distinguen a simple vista" no se puede comprobar hoy sobre salida real: sin recuperación no existe ninguna afirmación `literal` ni ninguna `parafrasis`, así que ese criterio, tal cual, se cumpliría validando la interfaz contra **material fabricado**. Es la misma familia que "los tipos son estables" cuando el modelo no tenía alternativa (7.1): un verde que sale porque no hay nada que comprobar. Así que:

- **En el 2.4 se verifica que los ESTILOS se distinguen**, sobre la ruta `/estilos` y con datos de ejemplo declarados como tales. Es una verificación de la interfaz, no del sistema, y se enuncia así.
- **La comprobación sobre salida REAL viaja a la fase 3**, junto con el clic de la referencia, que hoy tampoco tiene ninguna `literal` que abrir. Criterio allí: una consulta real produce al menos una `literal` y una `parafrasis`, se distinguen en pantalla, y el clic abre el fragmento citado.
- **El endpoint de apertura por procedencia sí se prueba entero ahora** contra el corpus cargado: que devuelve el fragmento cuando esa respuesta lo citó, y que **no** lo devuelve cuando no.

**LA DISTINCIÓN ENTRE TIPOS TIENE QUE AGUANTAR UNA VIDEOLLAMADA.** La sesión es pantalla compartida y comprimida: si `literal` y `parafrasis` se separan por un matiz de color o un borde fino, en vídeo se pierden y con ellos el efecto entero. **La diferencia es ESTRUCTURAL —comillas, sangrado, etiqueta con texto— y no solo cromática**, y se comprueba mirando `/estilos` al 50 % de zoom, que es aproximadamente lo que llega al otro lado.

**LO QUE SE VIO AL MIRAR DE VERDAD, el 12 de agosto de 2026, con la puerta en verde.** Cuatro de los cinco tipos se distinguían sin leer la etiqueta: `conocimiento` por el recuadro discontinuo, `analogia` por el punteado, `calculo` por la caja monoespaciada y `andamiaje` por no tener recuadro. `literal` y `parafrasis` no: las dos eran "barra vertical a la izquierda más texto", y lo único que las separaba era el color de la barra y el grosor del borde —las dos cosas que el vídeo se come—. La `literal` se salvaba por poco, por las comillas grandes; la `parafrasis` **no tenía marca estructural propia, porque era el estilo por defecto**. Y es justo la pareja que hace el trabajo en la sesión: separa lo que el temario dice palabra por palabra de lo que el sistema reformula. Arreglo: la `parafrasis` recibe una marca propia —**dos barras dibujadas con bordes**, una antes y otra después del cuerpo, con la misma construcción que las comillas de la `literal`— y **con el mismo peso visual que ellas**, porque una marca pequeña se pierde al 50 % exactamente igual que se pierde el color y sería cambiar una distinción invisible por otra. **Costó tres intentos y los tres están escritos con su resultado en el ADR 0011**, que es lo que los hace útiles: subir el tamaño de un glifo fino no compensa el trazo; la construcción sí da el peso; y **la marca no puede ser un carácter**, porque un glifo mete en el camino la codificación, la cobertura de la fuente y el pintado —un modo de fallo que el CSS no deja ver y que la sonda no puede detectar, porque declara la señal igual de bien la dibuje el navegador o no—. Con bordes no queda nada que pueda fallar entre los bytes de la hoja y los píxeles. Y el cuerpo de la `parafrasis` va a ras mientras el de la `literal` va sangrado, para que las dos siluetas empiecen en sitios distintos y la distinción no dependa entera de acertar qué marca se está mirando. **Y el parecido entre `conocimiento` y `analogia` NO se toca:** los dos dicen "esto no sale de tu temario", así que ahí la semejanza es semántica y correcta, y va escrita para que nadie la "corrija" más adelante.

**EL CIERRE DE ESTE ENCARGO PIDE OTRA MIRADA HUMANA AL 50 %.** La sonda comprueba que el CSS **declara** señales de forma distintas; si esas señales se **ven** a un metro y después de la compresión de vídeo no lo puede saber ningún test, y de hecho este fallo lo encontró un ojo y no la puerta. Dar el encargo por cerrado con `ruff` y `pytest` en verde sería sustituir el instrumento que funcionó por el que falló. **Se cierra cuando alguien mira.**

**ESTADO DEL CIERRE, el 13 de agosto de 2026 y escrito sin adornarlo.** El encargo **queda cerrado** por decisión del propietario, y con esto declarado: la marca de la `parafrasis` está construida —dos barras de borde, antes y después del cuerpo—, las puertas automáticas están en verde y la sonda comprueba lo que puede comprobar, que es que la hoja declara señales de forma distintas y que los selectores casan con ganchos que el dibujante escribe de verdad. **Lo que NO está comprobado en el momento de cerrar es lo único que importa de verdad: que las barras se distingan de las comillas mirando a un metro.** Han hecho falta tres miradas humanas —una por hipótesis caída: el tamaño, la construcción y el carácter— y la cuarta decide si el cierre fue limpio o si queda una deuda anotada aquí. **Que el encargo se cierre igual es deliberado:** llevaba seis vueltas en una marca mientras la fase que no puede caer no había empezado, y esa desproporción es un fallo de gestión mayor que un glifo torcido. Lo que la sesión necesita de esta pantalla es que los cinco tipos se lean; lo que necesita del sistema es que recupere.

**Y ESA MIRADA SE HACE CON RECARGA FORZADA, porque la puerta que este proyecto pone por encima de los tests también tiene su verde mentiroso, y el suyo es la caché del navegador.** Pasó el 12 de agosto de 2026: la primera captura tras un arreglo de la hoja era la hoja **cacheada**, y habría dado un veredicto —bueno o malo, da igual— sobre una página que ya no existía. Es la avería de siempre con otro disfraz: el instrumento mintiendo, no lo medido, y aquí el instrumento es el ojo.

**La causa se arregló donde estaba, que era el servidor y no la memoria de quien mira.** Faltaba una cabecera: `/estatico` iba solo con `ETag` y `Last-Modified`, y sin instrucción de frescura el navegador la inventa por heurística y puede servir su copia **sin preguntar**. Ahora todo lo que cuelga de `/estatico` sale con **`Cache-Control: no-cache`**, que no significa "no caches" sino "no uses tu copia sin preguntar antes"; con el ETag que ya se servía, preguntar cuesta un 304 sin cuerpo. **Y cubre `render.js`, que es el caso caro:** un estilo viejo se ve raro, pero un `render.js` viejo dibuja las etapas de otra forma o no las dibuja, y esa es justo la capa sin puerta automática, porque en el CI no hay motor de JavaScript. Verificado con el cliente de test —determinista— y no con la heurística de un navegador, que es lo que mordió: la cabecera está, la petición condicional da 304, y tras tocar el fichero la misma petición condicional da 200 con lo nuevo.

**Aun así, la mirada sigue haciéndose en ventana limpia y con recarga forzada, porque el arreglo vale de aquí en adelante y NO es retroactivo.** Una copia guardada **antes** de que la cabecera existiera se guardó sin instrucción de frescura y el navegador la sigue sirviendo por heurística; y como no pregunta, tampoco se entera de la regla nueva. Añádase que una pestaña ya abierta enseña lo que cargó cuando cargó y nada la refresca sola. En incógnito la caché empieza vacía y eso se ve al instante. Recargar es gratis; un veredicto sobre una página que ya no existe, no. Vale igual para cualquier captura que se guarde como evidencia.

**UNA PROPIEDAD RELACIONAL NO SE COMPRUEBA DE UNO EN UNO, y con esta van tres de la familia.** La sonda preguntaba a cada tipo por separado —"¿traes alguna señal que no sea color?"— y los cinco contestaban que sí, cuando la propiedad que importa es **"¿se distinguen ENTRE SÍ?"**. Una señal que dos tipos **comparten** no distingue nada: `border-left` daba verde a `literal` y a `parafrasis` a la vez, y era precisamente lo que las hacía iguales. Va junto a "**estable por vacía**" —los tipos del 7.1, estables porque la gramática no le dejaba al modelo otra casilla— y al "**verde que sale porque no hay nada que comprobar**" de aquí arriba: las tres son la misma avería, un instrumento que mide algo cierto y **contiguo** a lo que hace falta, y por eso ninguna se cae sola. **Regla: cuando el criterio dice "se distinguen", "no se solapan", "son distintos" o "son únicos", el detector compara PARES, no elementos.** Barrido del repo con esa pregunta, hecho el 12 de agosto de 2026: **un hallazgo**, en la línea de al lado —el test de que cada tipo lleva etiqueta con texto no comprobaba que las cinco etiquetas fueran distintas, y cinco etiquetas repetidas lo habrían pasado—, ya corregido. Los demás detectores de propiedades relacionales del repo ya comparaban pares: los conflictos del 1.8 (que además excluye los pares consecutivos por el solape de 64), los pares oro del 3.0 (posición **y** texto, ADR 0010) y la dispersión del 7.3 (que compara corridas por dimensiones).

**EL ENGANCHE DE LA ABLACIÓN SE RESERVA AQUÍ, aunque hoy no haga nada.** El guion de la demo pide correr los mismos casos con la verificación apagada; si la interfaz no tiene por dónde, alguien lo injerta la noche antes encima de lo que haya. Va un interruptor visible y un campo en el cuerpo de `/consulta`, **declarados como sin efecto mientras no exista la fase 4** y registrados en la traza para que se sepa qué se pidió en cada consulta. Cuesta una línea ahora y evita tocar la superficie de la demo en el peor momento.

**Y el panel de muestra vive en `/estilos`, en su propia ruta**, con aviso permanente y sin enlace desde la vista del alumno. Afirmaciones falsas de los cinco tipos, con citas inventadas, al lado de la salida real son "afirmar en presente lo no construido" puesto en pantalla. Una etiqueta no basta: en directo se abre por accidente o se lee mal.

**Y aquí se resuelve la espera, que es donde toca resolverla y no en el contrato.** Medido en el 2.2: el alumno mira una pantalla en blanco **1.638 ms** antes del primer carácter de prosa, y con la recuperación de la fase 3 delante será más. La salida barata sería reordenar el esquema para que la prosa salga antes, y está descartada con su motivo en el [ADR 0009](docs/adr/0009-el-evento-token-lleva-prosa-y-hay-dos-ttft.md): con decodificación restringida eso haría que la respuesta se escribiera antes que las afirmaciones que la sostienen. **La salida honesta es enseñar lo que de verdad está pasando mientras pasa:** "buscando en el temario de Bases de Datos", "3 fragmentos recuperados" con sus títulos, y después la prosa. El alumno ve **las citas antes que el texto**, que es exactamente lo que este sistema quiere demostrar, y la espera deja de ser espera para convertirse en la primera parte de la respuesta. **Y qué se enseña si una etapa no llega, porque las etapas son carga estructural y no adorno:** medido en el 2.2, el streaming de tokens adelantó **601 ms** en una consulta y **11 ms** en otra —la prosa va al final del contrato y puede llegar entera de golpe—, así que lo que de verdad cubre la espera son ellas. Si el evento `etapa` fallara, la pantalla se quedaría muerta 1,6-2,2 segundos delante del cliente. El respaldo no puede ser una animación: **el navegador dibuja su propia etapa** —"petición enviada", que es un hecho que él sí conoce, con su reloj— y va **marcada como medida en el cliente** para que no se confunda con las que salen de la traza. Y si no llega ninguna del servidor, se dice eso mismo en pantalla. Con su test.

**Condición que no se negocia: lo que se enseñe tienen que ser etapas MEDIDAS —las mismas que van a `respuestas.etapas`, con su marca de tiempo real—, jamás una animación de relleno ni un texto que aparezca por temporizador.** Una barra de progreso que no mide progreso es exactamente la clase de mentira cómoda que este proyecto no se puede permitir, y menos en la capa que el usuario mira. Verificación: cada etapa que aparece en pantalla tiene su entrada correspondiente en la traza de esa consulta, y si una etapa no ocurre, no se dibuja.

**2.5 Traza completa → SE EJECUTA DESPUÉS DE LA FASE 4.** `GET /trazas/{id}` reconstruye todo. Verificación: para una consulta cualquiera, la traza responde a "qué se recuperó, qué se afirmó, qué veredicto tuvo cada afirmación, cuánto costó cada etapa".

**Movido el 13 de agosto de 2026, y el motivo es que hoy no tendría nada que contar.** De esas cuatro preguntas, la traza de hoy solo puede responder la última: no hay recuperación (fase 3), así que "qué se recuperó" es *nada*; y no hay verificación (fase 4), así que "qué veredicto tuvo cada afirmación" es `sin_verificar` en todas. Un endpoint que devolviera eso **no enseñaría nada que la propia respuesta no enseñe ya** —los tiempos y el coste van en el evento `fin`, y las afirmaciones con su veredicto van en el evento `afirmaciones`—. Su valor entero aparece cuando la traza puede decir **qué se verificó, con qué instrumento y con qué resultado**, o sea con la fase 4 hecha. Construirlo antes sería escribir la vitrina antes de tener qué poner dentro, y además obligaría a rehacerla al llegar los veredictos.

**Lo que sí existe ya, y por eso mover esto no deja un hueco:** los datos están **persistidos desde el 2.2** —`consultas`, `respuestas` con sus `etapas` en jsonb y `afirmaciones` con su veredicto—, así que la traza de cada consulta que se haga desde hoy queda guardada y el endpoint la encontrará entera cuando se construya. Lo que se aplaza es la ventana, no el registro.

**2.6 Glosario (viene del 1.6; se ejecuta al cerrar esta fase, antes de abrir la 3).** El enunciado
y sus contratos están escritos en el 1.6 y no se repiten: extracción con el modelo pequeño sobre los
fragmentos con definición, y **validación independiente del extractor** —comparación de cadenas sin
modelo cuando la definición es literal, NLI distinto cuando es paráfrasis (principio 6)—.

**Lo que cambia respecto a cuando se escribió el 1.6, y hay que tenerlo delante:**

- **La entrada ya no es `tipo_contenido = definicion`, es la `frase_definitoria` del fragmento.**
  Medido a mano sobre el corpus: marcar el fragmento entero acertaba 3 de 20, porque un fragmento
  son 512 tokens y casi cualquier trozo de 512 tokens de prosa contiene un "es un" en algún sitio.
  La frase concreta acierta **13 de 20** (muestra distinta de la usada para afinar la regla). El
  troceado ya la guarda: 878 fragmentos la llevan.
- **La comparación literal se apoya en que el fragmento y su fichero derivado coinciden letra a
  letra**, que es la razón por la que la limpieza de mobiliario vive en la normalización y no en el
  troceado. Si alguien mueve esa limpieza, esta validación se cae con ella.
- **Aquí se decide el momento 3 de la demo** (ver *El guion de la demo*): si el glosario encuentra
  las dos definiciones incompatibles de MVC, el momento va con el par REAL; si no, va con la
  contradicción sintética plantada en el 1.7, declarada como plantada delante del cliente.

**Aquí se escribe también `evals/casos/conflicto.jsonl` (viene del 1.10).** Preguntas que caen sobre
el material contradictorio; esperado: aviso del conflicto. Se hace aquí porque **el glosario es lo
que lo consume**: es el que compara definiciones del mismo término y, por tanto, el único que puede
encontrar el par real. Y es de los conjuntos que **necesitan material concreto del corpus**: cada
caso apunta a fragmentos que existen, así que no se puede redactar de memoria. Mínimo: los dos pares
conocidos —el real de MVC y el sintético del paso de parámetros— más los que el propio glosario
destape al ejecutarse.

Verificación, además de la del 1.6: **coste medido de la pasada entera** (fragmentos procesados,
tokens de entrada y salida, euros al precio del modelo pequeño configurado) anotado en
`corridas_eval`, porque es el primer encargo que gasta dinero del proveedor y ese número es el que
convierte "extraer un glosario" en una línea de coste por titulación.

## Cierre de fase 2, reescrito el 13 de agosto de 2026

**El criterio decía:** *"consulta de punta a punta con traza completa y TTFT visible en la interfaz"*. Exigía **la traza completa**, que es el 2.5, y ese encargo se mueve detrás de la fase 4 por el motivo escrito en su enunciado. Se reescribe, que es lo que ya se hizo con el cierre de la fase 1 cuando exigía tres cosas que la fase ya no contenía: **no se finge que está y no se bloquea la fase; se reescribe, y lo que sale, sale CON DESTINO Y PORQUÉ.** Esa es la forma que distingue reescribir un criterio de escaparse de él.

**Criterio nuevo, y es el que se ha cumplido:** consulta de punta a punta en la interfaz, con **el contrato de la sección 7 validado en forma**, **los dos TTFT medidos y persistidos** en `respuestas.etapas`, y **las etapas que se dibujan cotejables contra la traza guardada**.

| Encargo | Estado | Qué queda como evidencia |
|---|---|---|
| **2.1** Esquema y migraciones | **cerrado** | 11.282 filas en 35 particiones, vectores casados por id, `EXPLAIN` con poda guardado |
| **2.2** API con SSE | **cerrado** | contrato tipado de punta a punta, dos TTFT medidos, flujo del proveedor visto en verde y en rojo |
| **2.4** Interfaz mínima | **cerrado** | los cinco tipos distinguidos por forma y no por color; etapas ancladas a la traza |
| **2.6** Glosario | **cerrado** | 647 entradas validadas sin modelo; el momento 3 de la demo decidido con datos |
| **2.3** Colas | **movido: después de la demo** | el camino interactivo no pasa por Celery (motivo en su enunciado); su verificación demuestra una propiedad que nadie va a preguntar el lunes |
| **2.5** Traza completa | **movido: después de la fase 4** | hoy respondería `sin_verificar` a todo y *nada* a "qué se recuperó"; los datos ya se guardan desde el 2.2 |

**Y una entrada fuera de fase, declarada:** el **3.0** (los 100 pares oro) llegó antes que su fase y vive en esta rama. No es de la fase 2; se coloca aquí porque es la vara con la que se va a medir la 3, y su método está declarado al lado.

**Por qué se cierra y se mergea ahora en vez de apilar la fase 3 encima:** un `main` mergeado **es el punto de vuelta atrás**. Si algo se rompe en la fase 3, `git checkout main` devuelve un sistema que funciona —corpus cargado, contrato, interfaz, glosario—, y hoy ese punto no existe. Apilar `fase-3` sobre `fase-2` rompería la revisabilidad para siempre, que es justo para lo que existe la regla de *una fase, una rama*: mergear ahora la conserva en vez de gastarla.

## Fase 3: recuperación

**3.0 Pares oro (vienen del 1.9; PRIMER ENCARGO DE LA FASE) — ENTREGADO el 12 de agosto de 2026,
EN RECONSTRUCCIÓN desde el 13, y RECONSTRUIDO el 14: 94 pares.**
94 pares pregunta-fragmento en `evals/casos/oro_recuperacion.jsonl` (100 en origen: la corrección
del 14 movió 54, retiró 6 con dos motivos declarados y dejó 40 intactos; el diff entero, auditable,
en el .md — donde también está contada la línea que faltó en la primera transcripción y cómo la
cazó una suma), con el método declarado entero y legible al lado, en `evals/casos/oro_recuperacion.md`. **Son la base de recall y nDCG**, y por eso
van los primeros de la fase: del 3.1 en adelante, todas las verificaciones los usan.

**LA RECONSTRUCCIÓN TERMINÓ EL 14 DE AGOSTO DE 2026** —el propietario leyó los cien uno a uno y
entregó la corrección como diff auditable, aplicada en el commit `2e0dbdc` con `verificar_oro` en
verde— **y los números definitivos de la fase se midieron ese mismo día contra el conjunto
corregido** (3.5 y `docs/evidencia/2026-08-14-cierre-fase3.md`). Cómo se llegó a saber que había
que reconstruirlo, en tres pasos que además son una lección de método:

1. **Muestreo sesgado (14 pares).** Leer los que ninguna vía encontraba dio once mal etiquetados,
   pero esos catorce se eligieron **porque la recuperación fallaba**, que es una de las cosas que un
   mal etiquetado provoca. No se podía extrapolar (principio 11).
2. **Muestreo al azar (8 pares) entre los que nadie había marcado:** tres claramente mal y uno
   dudoso, o sea del orden de **40 de 100**. Ese sí estimaba.
3. **Y ya no hace falta estimar: a 13 de agosto de 2026 van 51 de 100 revisados uno a uno, y
   cerca de la mitad están mal etiquetados.** El recuento directo sobre medio conjunto confirma lo
   que la muestra al azar predecía, y lo confirma **por encima**: es una reconstrucción, no un
   parche.

Lo rehace el propietario leyendo los cien uno a uno; el método corregido y sus reglas nuevas (leer el
fragmento entero, juzgar par a par y no en tanda, y el aviso del solape de 64 tokens contra el atajo
de `orden + 1`) están en `evals/casos/oro_recuperacion.md`.

**Tres consecuencias que se escriben antes de tener el conjunto nuevo, para que nadie las decida
con el resultado delante:** (1) al terminar se repiten 3.1, 3.2 y 3.3 con **la misma
configuración**, y **se reportan los dos números, antes y después, con el tamaño del conjunto al
lado**, citando el commit del conjunto viejo; (2) **el denominador cambia**, porque hay pares que se
retiran y no solo pares que se corrigen —los de contrastar dos mecanismos van al 4.0—, así que
tendrá **menos de 100**; y (3) **ya no se puede afirmar en qué sentido se moverá el recall.** Se
había escrito que subiría, y valía mientras los errores conocidos estuvieran todos entre los pares
que la recuperación no encontraba. Con errores también entre los que **sí** encontraba, cada uno de
esos estaba **regalando un acierto**: la corrección puede mover el número en los dos sentidos y se
sabrá midiendo. **Las tres se cumplieron el 14:** los dos números están en el README y en la
evidencia del cierre; el denominador quedó en 94; y el recall **bajó** — los pares mal anclados
apuntaban a encabezados, que es justo lo que la búsqueda trae fácil, así que regalaban aciertos.

**Composición real, que no es la que este encargo pedía.** Decía 50 de DWES y 50 de Programación;
**los 100 son de DWES**. Programación (lionel-ict) **no tiene banco de preguntas del profesor**: lo
que tiene son enunciados de ejercicio ("escribe un programa que…"), que son tareas cuya respuesta es
código y no un fragmento de teoría. Inventar las preguntas habría roto la regla de que la pregunta
viene de fuera, que es justo lo que hace que el número signifique algo, así que se prefirió un
conjunto de una sola asignatura a uno de dos con la mitad cocinada. Reparto por repositorio tras la
corrección del 14: joseluisgs-02 27, joseluisgs-03 11, joseluisgs-04 32, joseluisgs-05 24 (en
origen 27/11/35/27).

**Quién los construyó, y por qué no quien escribe el sistema.** Los etiquetó el asistente de la
conversación de diseño, no el agente que pica la recuperación. Es el principio 6 aplicado al
instrumento: **el mismo autor no puede escribir la recuperación y la vara con la que se mide**, o el
número no vale nada. **No hay validación humana experta disponible** —el propietario no imparte el
módulo— y eso se declara en vez de fingirse; el respaldo no es una promesa de calidad, es la medida
del punto siguiente.

**El campo `localizacion`, que decide lo que el 3.5 puede afirmar.** Cada par declara cómo se
encontró su fragmento: `busqueda` (buscando términos de la pregunta en el texto) o `lectura`
(leyendo el mapa de secciones y yendo al tema, sin buscar los términos). No es metadato de adorno:
`busqueda` **comparte mecanismo con BM25**, así que el recall sobre esos pares sale inflado por
construcción. Reparto: **19 `busqueda` y 75 `lectura`** desde la corrección del 14 (en origen 19 y
81: los 6 retirados eran todos `lectura`). La consecuencia operativa está escrita en el 3.5 y es
obligatoria.

**Regla de fragmentos múltiples** (la pedía este encargo y no la traía): **un solo fragmento oro por
pregunta**, el que la responde más completo; otros fragmentos relevantes no cuentan ni como acierto
ni como fallo. **Un fragmento aparece como oro en dos preguntas y se declara sin corregirlo:**
`joseluisgs-02/springboot/04-SpringWebRest.md` orden 11 explica `@RestController` y `@Repository` en
el mismo trozo y el banco pregunta las dos cosas. Corregirlo obligaría a elegir un fragmento peor
para una de ellas.

**Preguntas descartadas a propósito:** las que piden **contrastar dos mecanismos** (`extends` frente
a `include` en Pebble, y sus hermanas), porque su respuesta vive en dos fragmentos y `recall@6` es
binario contra uno. No se tiran: van a los casos de generación del **4.0**, donde el modelo recibe
seis fragmentos y sintetiza.

**Dónde está su commit, porque no está donde tocaría.** Los 100 pares entraron en la rama
**`fase-2`**, no en una `fase-3`, y la desviación de la regla "una fase, una rama" se declara aquí en
vez de colarse: sus artefactos (`evals/casos/`, `scripts/verificar_oro.py`, ADR 0010) no tocan nada
del código de la fase 2, y dos ramas vivas a la vez con un solo agente trabajando es el riesgo que sí
importa. La alternativa considerada era abrir `fase-3` desde ese mismo HEAD, que habría arrastrado
los nueve commits de `fase-2` sin mergear. Se apunta para que dentro de un mes nadie busque este
trabajo en una rama que no existe.

**Verificación: `python scripts/verificar_oro.py`** (puerta local, ADR 0010). Cruza los 100 uno a uno
contra `corpus/fragmentos.jsonl` y cuenta cinco clases por separado: no existe, **desplazado**, no
admitido por la puerta del 1.4 (documento y fragmento), circular y asignatura discrepante. Medido el
12 de agosto de 2026: **cero ocurrencias en las cinco clases**. Sustituye a la doble pasada propia
con un día de separación que este encargo pedía cuando el etiquetado iba a ser del propietario: los
pares vinieron de fuera, y lo que hay que comprobar de un conjunto entregado no es la coherencia de
quien lo escribió consigo mismo, sino que apunte a donde dice.

**Estos 100 pares SON `evals/casos/normales.jsonl`** (el conjunto 1 del antiguo 1.10): el mismo
fichero y el mismo artefacto, no una copia con otro nombre. Se dice aquí para que nadie lo etiquete
dos veces al leer aquel encargo.

Dos avisos que se ganaron en la fase 1 y que aquí ahorran horas de persona:

- **Se etiquetan contra el índice ya cerrado**, no antes. El troceado cambió tres veces durante los
  arreglos del corpus y cada cambio movía los `orden` de los fragmentos: un par oro etiquetado
  contra el índice viejo apunta a otro texto y no avisa de nada. **Por eso cada par lleva además el
  SHA-256 del texto que se etiquetó** (`fragmento_oro.hash_texto`) y la puerta lo compara: un par
  desplazado no rompe nada, solo hace que `recall@6` mida otra cosa (ADR 0010).
- **Ningún fragmento oro puede salir de `practicas/`**: esos documentos SON las preguntas. Uno que
  se colara haría que la pregunta se respondiera a sí misma y el recall saldría perfecto sin mérito.
  Comprobado y anclado en test, con los 18 documentos de `practicas/` que hay en el índice como
  prueba de que la comprobación tiene de qué agarrarse.
- **La fuente natural de las preguntas son los fragmentos `enunciado_ejercicio`** (223 en el
  índice): boletines, tareas y cuestionarios ya escritos por profesores, con su respuesta en el
  temario. Etiquetar desde ahí es más rápido y más realista que inventarse preguntas.
  **CORREGIDO EL 14 DE AGOSTO DE 2026: esa frase razona desde la ETIQUETA y no desde el texto.**
  Leídos a ojo, los 223 son en su mayoría **tareas de configuración y de programación** —*instala un
  proxy squid*, *implementa la clase Inventario*—, no preguntas con su respuesta en el temario. Lo
  que de verdad se usó al construir el conjunto oro fueron **documentos de test concretos**
  (`01-test.md`, `02-cuestionario.md`, `04-test-springboot.md`), que es una fuente mejor y está en el
  campo `origen_pregunta` de cada par. Se comprobó al barrer: **el problema del oro no viene de aquí**,
  viene de elegir el `fragmento_oro`.

**3.1 Léxica.** `tsvector` con configuración `spanish`, consulta con `websearch_to_tsquery`, siempre con filtro de asignatura. Verificación: consultas con terminología exacta (nombres de comandos, siglas) devuelven el fragmento correcto en el top 5.

**TRES COSAS MEDIDAS AL EJECUTARLO, el 13 de agosto de 2026** (`docs/evidencia/2026-08-13-lexica.md`):

1. **`websearch_to_tsquery` une los términos con AND, y eso hundía el recall.** Una pregunta de alumno de veinte palabras se convierte en *"el fragmento tiene que contener las diez raíces a la vez"*, y eso casi nunca pasa en 512 tokens. Medido sobre los 100 pares oro: **recall@20 del 19,0 %**. Con los mismos términos unidos por **OR** —el analizador sigue siendo `websearch_to_tsquery`, para conservar las comillas y el `-` de exclusión que un alumno puede escribir; lo único que se cambia es el conector sobre la consulta ya analizada— sube a **61,0 %**. La guía decía `websearch_to_tsquery` a secas: **la desviación se escribe con su número al lado**, que es la única forma de desviarse aquí.
2. **La configuración `spanish` trunca 10 de los 20 identificadores** que aparecen en las preguntas oro (`ViewData` → `viewdat`, `@ComponentScan` → `componentsc`). **No rompe la búsqueda, porque el truncado es simétrico**: el documento y la consulta pasan por la misma configuración. Lo que sí produce es ruido cuando un identificador cae en la raíz de un verbo castellano —`@page` y `pagar` comparten `pag`—, y eso es **1 colisión de 6 pares probados**, ninguna entre identificadores. **Decisión con la evidencia delante: no se añade hoy una segunda columna `simple`**; era la salida obvia y lo medido no la justifica, con el coste de otra columna, otro GIN por partición y otra lista que fusionar. Queda escrita como la primera palanca si el 3.4 enseña que los fallos son de terminología exacta.
3. **El recall se reporta partido en `busqueda` y `lectura` desde AQUÍ, no solo en el 3.5**, porque este encargo es donde vive el sesgo: los 19 pares `busqueda` se localizaron buscando términos en el texto, o sea **compartiendo mecanismo con la léxica**. Medido: **73,7 % frente a 58,0 %** en recall@20, **15,7 puntos de diferencia**. Un número único aquí habría dejado ese sesgo cocido antes de que nadie lo viera.

**Y el filtro de asignatura se prueba VISTO EXCLUYENDO**, no leyéndolo en la consulta: un filtro que nunca se ha visto excluir algo no es un filtro. El instrumento es el documento **colado del 1.7**, que está plantado exactamente para esto —el mismo contenido en Bases de Datos (0484) y en Programación (0485)—: con filtro vuelve solo la cara que toca, sin filtro vuelven las dos. Ese contraste es la prueba, y es la misma contaminación cruzada que el 3.5 mide.

**3.2 Vectorial.** Búsqueda HNSW por partición con el embedding de la consulta (BGE-M3 servido en el worker; en CPU si la latencia lo permite, medido). Verificación: paráfrasis de preguntas del conjunto oro encuentran su fragmento.

### PREDICCIÓN ESCRITA ANTES DE MEDIR, el 13 de agosto de 2026

Esto se escribe **antes** de correr el 3.2 porque es el único momento en que predecir es predecir. Después, cualquier explicación de los números encaja con los números.

**Lo que se predice:** el recuperador vectorial **no comparte mecanismo** con la forma en que se localizaron los 19 pares `busqueda` —que fue buscar términos de la pregunta en el texto, o sea el mecanismo de la léxica—. Así que **su hueco entre `busqueda` y `lectura` debería ser MUCHO MENOR que los 15,7 puntos de recall@20 que dio la léxica**.

**Y lo que significa cada resultado, decidido ahora y no después:**

- **Si el hueco vectorial sale mucho menor** (digamos, por debajo de 5 puntos): la hipótesis se confirma. Los 15,7 puntos de la léxica **eran sesgo de mecanismo compartido**, el reparto `busqueda`/`lectura` del conjunto oro queda **validado como instrumento**, y a partir de ahí "reportar por subconjunto" deja de ser una precaución y pasa a ser una medida con significado conocido.
- **Si sale parecido** (cerca de los 15,7): la hipótesis queda **refutada**, y la explicación honesta es otra: esos 19 pares son **preguntas más fáciles**, punto. Entonces el reparto no está midiendo sesgo de mecanismo sino dificultad, **el instrumento está midiendo otra cosa de la que dice** y hay que escribirlo así en el 3.5 en vez de seguir hablando de sesgo léxico.
- **Si sale mayor**: no hay hipótesis preparada, y eso también se dice. Sería el caso más interesante y el que obligaría a mirar de nuevo cómo se construyó el conjunto.

Con esto, **el reparto del conjunto oro deja de ser una limitación declarada y pasa a ser un instrumento validado o refutado con evidencia**, que es la diferencia entre un *caveat* y una medida.

### Dos comprobaciones que este encargo hereda

1. **El modelo y la revisión, anclados y comprobados al arrancar.** La consulta se embebe con BGE-M3 y tiene que ser **el mismo modelo y la misma revisión** con la que se embebió el corpus (`corpus/medidas-ingesta.json`, revisión `5617a9f6…`). Si difieren, los vectores no son comparables **y nada protesta**: la búsqueda simplemente devuelve peor y nadie sabe por qué. Es el principio 8 en su forma más cara. Salida distinta de cero si no coincide.
2. **La pregunta que dejó abierta el 2.1:** allí quedó medido que, con 3.892 filas en la partición, el planificador prefiere el escaneo secuencial (10 ms) y el HNSW no se usa. Aquí se comprueba **con la consulta real del 3.2** y se anota lo que salga; y si vuelve a ganar el escaneo, **la latencia que se reporte se declara como lo que es: un escaneo honesto, no un índice vectorial**.

**Aviso de suelo, escrito antes de tener el número:** la léxica sola da **58,0 % de recall@20 sobre `lectura`**. Para llegar al 0,8 de recall@6 tras fusión y reordenado, el vectorial tiene que aportar bastante. **Si el 3.2 sale flojo sobre `lectura`, no es momento de tocar la generación**: es la señal que la tabla de contingencias asocia a corpus o troceado, y hay que ir a mirar el 1.3 y el 1.4, no a subir la temperatura de nada.

### DOS ENCARGOS QUE VAN DENTRO DEL 3.3, acordados el 13 de agosto de 2026

**1) Clasificar a mano los 10 pares de `lectura` que NO encuentra ninguna de las dos vías, sin cambiar nada.** Hoy están dentro de un número agregado, y diez casos leídos dicen mucho más que un 12,3 %. Dos categorías, y el criterio para decidirlo es el que ya está escrito en `evals/casos/oro_recuperacion.md` —*"¿está la respuesta dentro de ese texto?"*—, que es **independiente de si la recuperación lo encontró**:

- **(a) el fragmento SÍ responde y la recuperación falla** → hallazgo real, y es de corpus o de troceado: su sitio son el 1.3 y el 1.4.
- **(b) el fragmento NO responde** → error de etiquetado del conjunto oro.

**Y la regla que lo mantiene honesto: si alguno se corrige, SE REPORTAN LOS DOS NÚMEROS, antes y después, con el cambio declarado.** Corregir el conjunto de evaluación viendo el resultado es la falta cardinal de todo esto, y lo único que la evita es declararlo. Se puede optar por no tocar nada hasta el 3.5; **la clasificación se hace igualmente ahora**.

**2) `confianza_recuperacion` es una afirmación que el sistema hace sobre sí mismo, y hay con qué comprobarla.**

- **La regla no puede salir de la puntuación RRF sin más:** RRF no está calibrado y un 0,03 no significa nada en absoluto. Se elige una regla, se escribe, y se declara **SIN CALIBRAR** igual que el 0,80 del NLI, con su calibración apuntada al **4.6**.
- **Y se mide ya, que sale gratis:** de cada uno de los 100 pares se sabe si el fragmento oro entró en el contexto, así que se puede comprobar si `alta` correlaciona con que el oro esté de verdad. **Que el sistema diga "alta" cuando el oro no está es el sistema seguro de sí mismo y equivocado**, que es exactamente el fallo que este proyecto existe para impedir, y sería feo que apareciera en su propio campo de confianza. Tres filas: cuántas veces dice alta/media/baja, y en qué proporción de cada una estaba el oro. Con eso el campo deja de ser decorativo.

**Dos apuntes menores del mismo acuerdo:** que `origen` diga **de qué listas viene cada candidato** se conserva aunque hoy no se use, porque es lo que hará legible la complementariedad más adelante; y con `/consulta` recuperando de verdad, **las etapas por fin cubren la espera con trabajo real**, que era el diseño del 2.4 —así que se mide el TTFT nuevo y se compara con los **1.638 ms** del 2.2, que es el número que se ve el lunes—.

### LA COMPLEMENTARIEDAD, MEDIDA ANTES DE ESCRIBIR LA FUSIÓN (13 de agosto de 2026)

Sale gratis de las corridas 2 y 3 —son dos conjuntos de ids ya medidos— y hay que tenerla antes, porque **el `recall@20` de la fusión es el TECHO DURO del `recall@6` final**: el 3.4 solo reordena los veinte primeros, así que lo que no entre en el candidato no aparece jamás, por bueno que sea el reordenador.

| Sobre `lectura` (81 pares) | |
|---|---:|
| Léxica @20 | 47 (58,0 %) |
| Vectorial @20 | 67 (82,7 %) |
| **Unión: el techo de la fusión** | **71 (87,7 %)** |
| De los 14 que el vectorial pierde, la léxica rescata | **4** |
| De los 34 que la léxica pierde, el vectorial rescata | 24 |
| Que **ninguna** de las dos encuentra | **10** |

**Lectura, con las tres decididas antes de mirar: la complementariedad es BAJA-MEDIA.** Cuatro rescates de catorce no es "la mitad o más", así que no estamos en el caso bueno; el techo sube de 82,7 % a **87,7 %**, cinco puntos. Consecuencia directa y hay que saberla ahora: **para un `recall@6` de 0,8 el reordenador tiene que colocar el fragmento correcto en el top 6 en el 91 % de los casos en que está en el candidato** (80 / 87,7). Es exigente y no imposible, pero el margen no da para un reordenador mediocre.

**Y hay un suelo que ninguna fusión levanta: 10 pares de `lectura` no los encuentra ninguna de las dos vías.** El máximo alcanzable en `lectura` es 87,7 %, no 100 %. Si el 3.5 se queda corto, ahí está una parte de la explicación, y es de corpus o de troceado —la señal que la tabla de contingencias manda mirar en el 1.3 y el 1.4—, no de la fusión.

**En `busqueda` el régimen es otro:** la léxica rescata 3 de los 4 que el vectorial pierde y el techo llega al 94,7 %. Coherente con lo que ya sabemos de ese subconjunto: comparte mecanismo con la léxica, así que la léxica aporta justo ahí.

**Aviso sobre RRF, que se comprueba en este encargo:** `k=60` pondera por **rango** e ignora la calidad de cada lista, y aquí son muy desiguales (léxica 32,1 % a `recall@5` frente a 74,1 % del vectorial sobre `lectura`). Una lista floja puede meter ruido en la **cabeza** de la fusión aunque mejore la cola. Por eso la verificación de este encargo —recall@20 de la fusión ≥ el de cada lista— es **necesaria y no suficiente**: se reporta también **recall@5 y recall@6 de la fusión frente al vectorial solo**, porque si el 3.4 decepciona, el orden que queda es el de la fusión.

### EL PAPEL DE LA FUSIÓN, DECLARADO COMO LO QUE ES: COBERTURA, NO ORDEN

Medido en el 3.3: **RRF ordena PEOR que el vectorial solo** —73,0 % a `recall@5` el vectorial contra 56,0 % la fusión—, y ponderando por calidad la fusión no mejora: **converge** al vectorial. Lo que sí compra es **cobertura**: candidatos que el vectorial no trae, que viven por debajo del puesto 20.

**Así que el trabajo de la fusión es generar el CONJUNTO de candidatos, y el ORDEN lo pone el reordenador del 3.4.** Es una arquitectura legítima y se escribe para que nadie la lea como un fallo pendiente de arreglar.

**Y su consecuencia, que va también a la tabla de contingencias: la fusión queda COLGANDO del 3.4.** Si el reordenador cae o se recorta, el respaldo es **el vectorial solo**, nunca la fusión sin reordenar —porque la fusión sin reordenar es peor que no fusionar—.

**3.3 Fusión.** RRF con k=60 (inicial) sobre las dos listas más los aciertos del glosario en paralelo (si el glosario tiene el término exacto, **sus fragmentos** entran con prioridad —en plural, y corregido en el 2.6 por el ADR 0012: un término puede tener varias entradas, y cuando las tiene es porque el corpus se contradice; traer las dos caras es exactamente lo que la fase 4 necesita para enseñarlas). Verificación: recall@20 de la fusión mayor o igual que el de cada lista por separado sobre los pares oro; si no, se investiga antes de seguir.

**3.4 Reordenado.** BGE reranker v2-m3 sobre los **30** primeros de la fusión; se queda el top 6 para el contexto. Medir latencia real del paso en p50 y p95. Verificación: latencia medida y decisión tomada con el número delante. **Corregido el 13 de agosto de 2026 con la medida hecha: NO va "cuantizado en ONNX int8 en la CPU del VPS" —eso era el plan y no cabe por 25×— sino en GPU y en fp32** (ADR 0015).

**LA LATENCIA DEL REORDENADO SE MIDE CONTRA EL TOTAL, NO CONTRA CERO.** El plan B se dispara sobre el tiempo que ve el alumno, no sobre el del reordenador aislado: 400 ms de reordenado sobre 3,1 s no son lo mismo que 400 ms sobre 1,6 s, y la decisión se toma con el número de punta a punta delante.

**Y ESE "TOTAL" HUBO QUE MEDIRLO, PORQUE EL QUE SE VENÍA USANDO ERA OPTIMISTA.** Se citaban **3.076 ms** como punta a punta del 3.3; era un **p50 de muestra pequeña y sin reordenador**. Con n=20 y el reordenador puesto (`docs/evidencia/2026-08-13-concurrencia.md`): **p50 5.151 ms y p95 63.853 ms**, o sea que **el requisito de 5 s no se cumple hoy** ni siquiera en la mediana. La lección va con el resto: **sumar un paso nuevo a una base optimista da un total optimista con aritmética impecable**, y el error viaja escondido en el sumando, no en la suma.

**EL POOL PASA DE 20 A 30, decidido el 13 de agosto de 2026 con la aritmética delante** (`docs/evidencia/2026-08-13-fusion.md`). El techo de la fusión depende del corte, y de él sale lo que el reordenador tiene que acertar para llegar al 0,8 de `recall@6`:

| Pool | Techo en `lectura` | El reordenador tendría que acertar |
|---:|---:|---:|
| 20 | 82,7 % | **96,7 %** — imposible |
| **30** | **88,9 %** | **90,0 %** — exigente y plausible |
| 40 | 90,1 % | 88,8 % — un punto por un tercio más de coste |

**La ganancia está entre 20 y 30, y después se aplana.** Desviación declarada con estos números al lado.

> **Nota del 14/08, tras la pasada adversarial:** los techos por pool de esta tabla salían de **una
> corrida a pool 40 cortada en 20/30/40** — el principio 10 en acción: un techo medido con un corte
> es el techo de ese corte —. El recuento real a pool 30 del mismo día dio **87,7 %** en `lectura`
> (evidencia de la fusión, §"Recuento al pool DEFINITIVO"), y ese es el "antes" comparable que usa
> el cierre; el 88,9 % se queda aquí como lo que la tabla decidió con lo que sabía.

**PLAN B REESCRITO, porque el viejo se contradecía solo.** Decía: *si el p95 supera 400 ms, bajar a 12 candidatos*. Con el techo medido, eso es la única salida que **garantiza no llegar**: menos candidatos destruye la cobertura que subir a 30 acaba de comprar, y con 12 el 0,8 pasa a ser inalcanzable **por construcción**. Orden nuevo de salidas si la latencia no cabe:

1. **Reordenar en GPU o por lotes**, que es donde está el margen real.
2. **Aceptar el p95 y declararlo con su número**, que en una demo local no duele.
3. **Caer a VECTORIAL SOLO en top 6** —73,0 % medido—, declarado como lo que es.

**Bajar el número de candidatos, nunca.**

**PLAN B DISPARADO EL 13 DE AGOSTO DE 2026, Y CON LA SALIDA (2) TACHADA POR EL PROPIO NÚMERO.**
Medido (`docs/evidencia/2026-08-13-reordenado.md`): el paso de reordenado sobre 30 candidatos cuesta
**13.714 ms de p95 en CPU** y **554 ms en GPU**, un factor **25**. La salida (2) —*aceptar el p95 y
declararlo, que en una demo local no duele*— se escribió imaginando 400-900 ms; con 13,7 s no es
"aceptar un coste", es **poner catorce segundos de pantalla muerta delante del alumno**, porque el
reordenado va ANTES de la llamada al modelo y por tanto **en la ruta del TTFT**. Queda la salida (1):
**GPU**, con la divergencia declarada en el 8.1. La (3) sigue viva como respaldo en caliente.

**Y EL CRITERIO DE ACEPTACIÓN DEL REORDENADOR, ESCRITO ANTES DE TENER SU NÚMERO, que es el único
momento en que escribirlo es decidir y no justificar.** Poner el reordenador en GPU cuesta una
**divergencia arquitectónica** —la máquina de la demo tiene GPU y el VPS no—, así que tiene que
ganársela.

> ### EL CRITERIO ES UNA FÓRMULA, NO UNA CIFRA
>
> **El reordenador se queda si cierra más de la MITAD del hueco entre la fusión sola y el techo del
> pool**, medido en `recall@6` sobre `lectura`:
>
> ```
> listón = fusión_sola + (techo_del_pool − fusión_sola) / 2
> ```
>
> **Esto se escribe así a propósito y antes de que los números cambien.** El conjunto oro está en
> reconstrucción, así que **los tres valores que alimentan la fórmula van a moverse los tres**, y
> cuando se recalcule el listón va a parecer que se mueve la portería. No se mueve: **la regla es la
> misma y se escribió antes de medir**; lo que cambia es la vara con la que se evalúan sus entradas.
> Un criterio escrito como fórmula sobrevive a que se corrija el instrumento; uno escrito como cifra,
> no — y el que lo escribe como cifra acaba eligiendo, sin querer, la cifra que le conviene.

Con los valores **provisionales de hoy** —conjunto oro sin reconstruir, así que los tres son
provisionales—:

| | `recall@6` en `lectura` (PROVISIONAL) |
|---|---:|
| Fusión sola, sin reordenar | 72,8 % |
| **Techo del pool 30** | **88,9 %** |
| **Listón que sale de la fórmula** | **80,9 %** |
| Objetivo de la fase | 80,0 % |

**MEDIDO EL 14 DE AGOSTO DE 2026 con el conjunto corregido** (94 pares, 75 en `lectura`; fusión
10:1 y pool 30 — la configuración decidida el 13, y desde hoy también **cableada**, que no lo
estaba: producción fusionaba a 1:1 sin que nadie lo hubiera decidido):

| | `recall@6` en `lectura` (n=75) |
|---|---:|
| Fusión sola, sin reordenar | 58,7 % |
| Techo del pool 30 | 81,3 % |
| **Listón que sale de la fórmula** | **70,0 %** |
| **Reordenador (BGE v2-m3 en GPU) sobre ese pool** | **56,0 %** |
| Objetivo de la fase | 80,0 % |

**EL CRITERIO SE EJECUTÓ SOLO Y EL VEREDICTO ES NO SE QUEDA: 56,0 % contra un listón de 70,0 % — y
por debajo de la fusión sin reordenar (58,7 %). No es que no cierre la mitad del hueco: EMPEORA la
cabeza en `lectura`** (en `busqueda` empata el `recall@6` y mejora el @5; el nDCG@5 global queda en
tablas: 0,405 reordenado contra 0,406 sin reordenar). Se ejecuta la rama escrita antes de medir: la
configuración por defecto pasa a **fusión 10:1 sin reordenar**, con el objetivo de la fase declarado
**NO ALCANZADO** (58,7 % contra 80,0 %), y salen gratis las tres cosas a la vez — la divergencia
arquitectónica (era la única pieza GPU-o-nada), el techo de ~1,9 consultas/s y la pérdida de
reordenado desde 5 alumnos. `REORDENADOR_ACTIVO=1` lo reenciende para ablación o re-medida
(ADR 0019); la nota de la ganancia a N=1 queda vacua con la ganancia en negativo.

**Y una propiedad de la fórmula que el conjunto corregido invalidó, dicha con todas las letras:**
el listón ya no queda por encima del objetivo (70,0 < 80,0), porque el techo real del pool (81,3 %)
apenas lo supera. Esa consecuencia es más dura que el veredicto del reordenador: **ni un reordenador
perfecto alcanzaría el 80 % con margen sobre este pool.** El camino al objetivo no pasa por ordenar
mejor 30 candidatos: pasa por que el oro **entre** en el pool —troceado, léxica, corpus—, que es
materia de la tabla de contingencias del 1.3/1.4, no de esta pieza.

> ### Y LA GANANCIA SE MIDE A N=1 PERO SOLO SE ENTREGA A N=1
>
> Cuando se mida si el reordenador cierra la mitad del hueco, ese número saldrá de correr los pares
> oro **uno detrás de otro**. Pero medido el 13 de agosto: **a partir de cinco alumnos simultáneos
> la mitad de las peticiones no reciben el reordenado** (`reordenador_saturado`). Así que:
>
> ```
> ganancia_en_servicio = ganancia_medida × fracción_de_peticiones_que_lo_reciben
> ```
>
> **El número que salga del criterio será el MEJOR CASO, no el caso**, y hay que leerlo así desde
> ahora. Con la concurrencia que el producto exige —el 8.4 habla de una sesión, pero el piloto habla
> de alumnos a la vez— esa fracción es del **50 % a partir de seis**, o sea que una mejora de ocho
> puntos de recall se entrega como cuatro. Esto **refuerza con aritmética las dos salidas que ya
> estaban escritas**: o **lotes en el reordenador** —que suben la fracción hacia 1 y son entonces
> parte del precio de tenerlo, no una optimización futura— o **descartarlo**, y en ese caso el
> vectorial solo ya no compite contra su mejor caso sino contra su mejor caso partido por dos.

Si cierra menos, estaríamos pagando una divergencia arquitectónica por una mejora parcial, y la
configuración honesta pasa a ser **fusión sin reordenar con su número declarado y el objetivo
declarado como NO alcanzado**. Nótese que el listón queda **por encima** del objetivo a propósito, y
eso también es propiedad de la fórmula y no de la cifra: llegar al objetivo justo por los pelos no
justifica la divergencia, porque entonces el mérito es del pool y no del reordenador.

**Se mide cuando llegue el conjunto oro reconstruido (3.0), no antes.** Hasta entonces el hueco de
calidad de este encargo está **vacío y declarado vacío**: la latencia no depende de la vara y por eso
se midió ya; el acierto sí. **Llegó el 14 de agosto y está medido arriba: el hueco se llenó y el
veredicto salió en contra.**

**Y CÓMO SE CIERRA ESTO, decidido el 13 de agosto de 2026 para que nadie espere de brazos cruzados:**
el 3.4 queda **cerrado a medias por diseño** —latencia sí, calidad no— y **no bloquea la fase 4**,
que se abre por el 4.1 y el 4.2 mientras tanto. Cuando llegue el conjunto reconstruido se re-corren
**3.1, 3.2 y 3.3 con la misma configuración** —para que las filas sean comparables— y **3.4 y 3.5 se
cierran en la misma tanda**, con los dos números de cada uno (antes y después) y el tamaño del
conjunto al lado. **Hecho el 14 de agosto de 2026**: corridas 26-31 de `corridas_eval`, los dos
números de cada vía en el README y el detalle en
`docs/evidencia/2026-08-14-cierre-fase3.md`. **El 3.4 queda cerrado entero: latencia medida el 13,
calidad medida el 14, y decisión tomada por su propio criterio.**

**Y EL COSTE DEL REORDENADOR YA NO ES SOLO LA DIVERGENCIA ARQUITECTÓNICA: TAMBIÉN ES EL TECHO DE
CONCURRENCIA.** Medido el 13 de agosto (`docs/evidencia/2026-08-13-concurrencia.md`): el reordenador
es un modelo único en una GPU única, así que **serializa** —nuestro tramo pasa de 1.001 ms con una
consulta a 5.659 ms con diez— y pone el techo del sistema en **~1,9 consultas/s**, cinco veces por
debajo de la cuota del proveedor. Traducido: **~2 alumnos simultáneos** dentro de los 5 s, y treinta
a la vez dejarían al último esperando ~15,8 s solo en esa cola.

**Y HAY UNA TERCERA COSA QUE EL REORDENADOR CUESTA, MEDIDA EL 13 DE AGOSTO Y QUE NO SE VE EN NINGUNA
CURVA DE LATENCIA: a partir de CINCO alumnos simultáneos el sistema empieza a saltárselo.** El
ejecutor es de un solo hilo —con varios, una GPU colgada fabricaría hilos zombis en vez de
degradar— y con ~419 ms por reordenado y la espera acotada en 2 s, la quinta petición de una ráfaga
se pasa del plazo **con la GPU perfectamente sana**. Medido: **0 % hasta N=4, 20 % a N=5, 50 % a
N=6 y a N=8**, todos con motivo `reordenador_saturado`.

**Y el detalle que lo hace peligroso: desde N=4 el p95 de nuestro tramo DEJA DE CRECER.** Parece que
escala bien. Escala bien porque **está tirando calidad**: las peticiones que habrían tardado más son
justo las que se degradan, y al degradarse salen antes. **La curva plana es el síntoma de la pérdida,
no la prueba de la solidez.** O sea que "aguanta ocho alumnos" sería cierto en latencia y falso en
calidad, y solo la traza sabe cuáles salieron sin reordenar. Qué le hace eso al `recall@6` se mide
con el conjunto reconstruido, en la misma tanda que cierra 3.4 y 3.5.

Así que cuando llegue el conjunto oro, el 80,9 % no se juzga contra "cuesta 554 ms" sino contra
**"cuesta 554 ms, una divergencia arquitectónica y dividir por cinco los alumnos simultáneos"**. Si
el reordenador se queda, **los lotes dejan de ser una optimización futura y pasan a ser parte del
precio de tenerlo** (su disparador está en la evidencia). Y si no llega al 80,9 %, entonces salen
gratis las tres cosas a la vez, que es un argumento a favor de medirlo antes de acostumbrarse a él.

**3.5 Medición de la fase.** El arnés corre los pares oro: recall@6 y nDCG@5 con y sin reordenador,
**reportados por separado en los dos subconjuntos de `localizacion` además del global** —los 19
`busqueda` y los 81 `lectura` del 3.0—, tasa de contaminación cruzada (respuestas apoyadas en fragmentos de otra asignatura, medible gracias al documento colado de 1.7). **Ojo, que no es lo mismo que el colado del 1.8 y por eso están los dos:** allí se detecta un documento MAL ETIQUETADO dentro del corpus, que es propiedad de la ingesta y se arregla moviendo el fichero; aquí se mide cuánta contaminación se cuela en los RESULTADOS de recuperación, que es propiedad de la ejecución y depende del filtro, del reordenador y del umbral. Se puede tener el corpus perfectamente etiquetado y aun así contaminar respuestas. Persistido en `corridas_eval`.

**CÓMO CORRE EL ARNÉS, decidido el 12 de agosto de 2026 porque de ello dependía el orden de la fase 2.** La sección 10 declara `POST /eval/correr` como la vía del arnés, y ese endpoint encola trabajo: leído así, **el 2.3 bloquearía el cierre de la fase 3**. Se decide lo contrario y se escribe en los dos sitios: **el arnés es un script (`evals/arnes/`) que corre contra la base y persiste en `corridas_eval`**, y `POST /eval/correr` queda **declarado no construido hasta la fase 8**, cuando exista un motivo real para lanzarlo desde fuera. Tres razones, y ninguna es el gusto: el arnés no necesita cola porque nadie espera su respuesta por HTTP; un script se ve correr en pantalla, que para la sesión del lunes vale más que un `202 Accepted`; y así **la fase 3 no depende de la fase 2 más de lo que ya depende**. Consecuencia directa: **el 2.3 no bloquea nada** y su sitio es después de la demo.

**Por qué los dos subconjuntos no son un desglose opcional.** Los 19 pares `busqueda` se localizaron
buscando términos de la pregunta en el texto, o sea **compartiendo mecanismo con BM25**: su recall
sale inflado por construcción, y un global que los mezcle con los 81 `lectura` reparte ese inflado
por todo el número sin que se vea. **La diferencia entre los dos subconjuntos ES el sesgo del
conjunto de evaluación, medido en vez de declarado**, y es la respuesta que hay que poder dar si un
cliente pregunta si la evaluación está cocinada: no "confía en el método", sino "aquí está cuánto, y
lo mide el propio arnés". Si el hueco entre `busqueda` y `lectura` sale grande, el número honesto es
el de `lectura`, y se dice. Antes de cualquier medida de este encargo se corre
`python scripts/verificar_oro.py`: un conjunto oro desalineado no da error, da ruido con aspecto de
dato.

**MEDIDO EL 14 DE AGOSTO DE 2026, cerrando el encargo** (conjunto corregido: 94 pares, 19
`busqueda` y 75 `lectura`; `verificar_oro` en verde antes de cada corrida; corridas 26-31 de
`corridas_eval`; el detalle y los antes/después, en `docs/evidencia/2026-08-14-cierre-fase3.md`):
sobre la configuración por defecto (fusión 10:1, pool 30, sin reordenar), `recall@6` **60,6 %
global** (68,4 `busqueda` / 58,7 `lectura`) y `nDCG@5` **0,406 global** (0,484 / 0,386); con
reordenador, 58,5 / 68,4 / 56,0 y nDCG 0,405 — por eso está descartado (3.4). **Contaminación
cruzada: 0 de 94 contextos finales en todas las corridas**, y no es casualidad sino construcción: el
filtro de asignatura es la firma de las funciones de búsqueda, y se ha visto excluir con el
documento colado del 1.7. La brecha `busqueda`−`lectura` (9,7 puntos a `recall@6`) es el sesgo del
conjunto, medido: el número honesto sigue siendo el de `lectura`.

**Cierre de fase 3:** números en la tabla, **con las dos métricas partidas por `localizacion` y no
solo globales**; contaminación en cero o con explicación escrita; mejora del reordenador
cuantificada. **Leído cláusula a cláusula el 14 de agosto de 2026: números en la tabla del README y
aquí arriba, `recall@6` y `nDCG@5` partidos en los dos subconjuntos además del global ✓;
contaminación en cero ✓; mejora del reordenador cuantificada ✓ — es −2,7 puntos en `lectura`, y por
negativa el reordenador queda descartado por su propio criterio.**

**LO QUE DE VERDAD SE CIERRA, Y LO QUE SALE CON DESTINO Y MOTIVO** (escrito así porque un cierre
que no enumera lo que deja fuera es una declaración de victoria, no un cierre):

- **Se cierra:** la recuperación completa medida contra una vara verificada (94 pares, dos métricas,
  dos subconjuntos, seis corridas reproducidas), la configuración por defecto decidida por números
  (fusión 10:1 en top 6, cableada), la decisión del reordenador tomada por su propio criterio, y la
  contaminación cruzada en cero contada, no supuesta.
- **El objetivo de calidad (80 % de `recall@6` en `lectura`) sale NO ALCANZADO: 58,7 %.** Y es la
  fila que hace creíbles las demás. Su destino no es un encargo fantasma: con el techo del pool en
  81,3 %, el hueco es de **cobertura** —18 de 94 pares no entran ni en el pool de 30—, así que va a
  la tabla de contingencias del 1.3/1.4 (troceado, léxica, corpus) y a la decisión de material que
  los tres huecos de COBERTURA ya piden. Ordenar mejor 30 candidatos no llega ni en el óptimo.
- **El reordenador sale descartado** (ADR 0019); destino: la ablación del 7.3 y la re-medida si
  cambian conjunto, pool o modelo — siempre contra la fórmula, nunca contra la cifra. Sus lotes,
  que eran "parte del precio de tenerlo", quedan vacíos de objeto mientras siga descartado.
- **Tres pares de contraste salen hacia el 4.0** (`generacion_contraste.jsonl`): no miden
  recuperación, miden síntesis, y ese es su sitio. **Tres huecos de corpus salen hacia COBERTURA**
  (balanceador, aislamiento, AAA): no son etiquetado, es material que no existe.
- **`POST /eval/correr` sigue en la fase 8** (decisión del 12/08, sin cambio) y **la calibración de
  todos los umbrales declarados sin calibrar sale hacia el 4.6**, que desde hoy tiene lo que le
  faltaba: un conjunto oro en el que se puede confiar.

## Fase 4: generación tipada y verificación

**4.0 Los conjuntos de abstención y premisa falsa (vienen del 1.10; PRIMER ENCARGO DE LA FASE).**
Dos ficheros en `evals/casos/`:

1. `fuera_de_temario.jsonl` (mínimo 30): preguntas razonables cuya respuesta NO está en el corpus;
   esperado: **abstención**.
2. `premisas_falsas.jsonl` (mínimo 30): afirmaciones incorrectas dichas con seguridad por el alumno;
   esperado: **corrección con cita**.

**Y un tercero que sale del 3.0 y que no hay que volver a inventar:** `contraste.jsonl`. Son las
preguntas del profesor que piden **contrastar dos mecanismos** (`extends` frente a `include` en
Pebble, `Page` frente a `Slice`, `ViewData` frente a `TempData`), que quedaron **fuera de los pares
oro a propósito**: su respuesta vive en dos fragmentos y `recall@6` es binario contra uno, así que
como caso de recuperación solo sabrían dar un falso rojo. Aquí valen enteras, porque este es el
sitio donde el modelo recibe seis fragmentos y **sintetiza**: lo que se mide es si la respuesta
recoge los dos mecanismos y los cita a los dos, no si un ranking acertó con uno. Esperado:
**respuesta que cubre ambos lados con cita de cada uno**; una que solo explique uno de los dos está
incompleta aunque todo lo que diga sea cierto. Salen del mismo banco del profesor que los pares oro
y con la misma regla: la pregunta viene de fuera del corpus.

Van aquí y los primeros porque **son la fase 4 entera medida**: el 4.6 calibra el umbral NLI con
ellos y el cierre de fase se enuncia sobre ellos. Sin estos dos ficheros, la fase 4 se puede
construir pero no se puede cerrar.

**UN CASO REAL PARA `fuera_de_temario.jsonl`, aparecido solo el 13 de agosto de 2026 y guardado con su texto exacto**, que los casos que aparecen solos valen más que los inventados:

> *"¿Qué es una clave primaria y por qué no puede repetirse?"* preguntado con la asignatura **0613 (Desarrollo web en entorno servidor)** seleccionada.

Es una pregunta perfectamente razonable de un alumno de DAW y **cae fuera del temario de esa asignatura** —su sitio es Bases de Datos, la 0484—. Salió mirando una corrida: la recuperación trajo material de seguridad de DWES, que es lo más cercano que hay ahí, e hizo lo correcto. Esperado: **abstención**.

**Y sirve de validación del diseño de `confianza_recuperacion`, con su medida:** en esa consulta el campo dio **`baja`** (top1 0,523, margen 0,039), que es lo que tenía que dar. Con el matiz honesto de que la misma pregunta **en su asignatura** (0484) también dio `baja` (top1 0,631, margen 0,049): el campo acierta la dirección y **es conservador**, o sea que avisa de más. Coherente con las tres filas medidas —`baja` acierta el 54,5 %— y con que la 0484 tenga solo 485 fragmentos.

**Quién los produce: se redactan SIN tocar el corpus**, y eso los hace baratos y honestos a la vez.
Una pregunta fuera de temario no necesita leer el corpus —necesita ser razonable para un alumno de
DAW y caer fuera—, y una premisa falsa se escribe sabiendo la materia. El corpus solo entra después,
al comprobar la respuesta. Aviso de la fase 1 que aplica aquí: **una pregunta "fuera de temario" hay
que comprobarla contra el índice**, porque el corpus tiene 11.483 fragmentos de tres titulaciones y
lo que parece fuera puede estar dentro; la línea base del 1.5 lo enseña —la similitud siempre
devuelve su vecino más cercano con aplomo, aunque la respuesta no exista—.

**4.1 Prompts por modo — CONSTRUIDO el 13 de agosto de 2026** (`app/core/prompts.py`). Un prompt de sistema por modo, versionados con `VERSION_PROMPT`.

**QUÉ ES DE ESTE ENCARGO Y QUÉ NO, que es su decisión de fondo.** Aquí va lo que **no se puede imponer con la gramática** —cómo se comporta un profesor en cada modo— y **no** va lo que sí: la forma del contrato la impone `json_schema`, el tope de la cita lo impone `maxLength` y la referencia con `F` la impone `pattern`. **Pedir por prompt algo que el esquema puede prohibir es pedir un favor** (principio 7), así que este fichero es lo que queda **después** de haber usado la gramática hasta el final. Hay test que vigila que no crezca: cada línea de más se paga en prefill **en cada consulta**.

**Y `VERSION_PROMPT` deja de ser adorno.** Era una constante fija que nadie tocaba al cambiar el texto —un campo con nombre de trazabilidad y contenido decorativo—. Ahora sale del módulo que escribe el prompt y **lleva el modo dentro** (`4.1-2026-08-13/acompanar`), porque **dos modos son dos prompts** y guardar solo la fecha haría imposible contestar dentro de un mes a *"¿con qué prompt salió aquella respuesta rara?"*.

**`examinar` NO tiene prompt, y es a propósito:** está declarado como diseñado y no construido en la sección 3, con su nota del AI Act. Darle uno sería construirlo por la puerta de atrás, y **el primer sitio donde este proyecto no puede afirmar en presente lo no construido es su propio código**. Hay test.

**Las reglas duras de `acompanar` van ancladas en test**, y no por manía: son **la pedagogía del proyecto escrita en código**. Si alguien "simplifica" el prompt y se lleva por delante *"nunca des el resultado final"*, el sistema seguiría respondiendo, seguiría validando el contrato y seguiría pasando toda la suite — **resolviéndole el ejercicio al alumno**, que es exactamente lo que el modo existe para no hacer.

> **HUECO DECLARADO, CON SU DUEÑO: ese test ancla que la CLÁUSULA está, no que el COMPORTAMIENTO se
> cumpla.** Un prompt que conserve la frase *"nunca des el resultado final"* y aun así suelte la
> solución **pasaría en verde**, porque lo que se lee es el texto del prompt y no lo que el modelo
> hace con él. **La otra mitad es el conjunto `fuga_de_solucion`**, que mide el efecto sobre casos
> reales, y **lo debe el propietario** (viene del 1.10, como los demás conjuntos de casos). Hasta que
> exista, el modo `acompanar` está **cubierto en su declaración y NO en su comportamiento**, y así se
> cuenta: decir que está probado sería exactamente el tipo de verde mentiroso que este repo persigue. Cláusulas obligatorias comunes: responde SOLO desde los fragmentos dados y el glosario; toda afirmación en el JSON del contrato; lo que no esté en los fragmentos va como `conocimiento` o no va; si los fragmentos no bastan, `confianza_recuperacion: baja` y prepara abstención. Cláusulas del modo acompañar: las reglas duras de la sección 3. Verificación: 10 consultas de humo por modo devuelven el contrato bien formado.

**4.2 Verificador literal — CONSTRUIDO el 13 de agosto de 2026** (`app/core/verificador_literal.py`, evidencia en `docs/evidencia/2026-08-13-verificador-literal.md`). Sección 8, **con una corrección medida**: la normalización es **solo espacios** (ver la sección 8). Test anclado con el caso plantado —una cita con una palabra cambiada degrada a paráfrasis— **y su simétrico**, que el enunciado no pedía y sin el cual el primero no probaría nada: un verificador que degradara siempre lo pasaría con nota.

**LO MEDIDO, con el denominador declarado (337 citas literales reales):**

| | |
|---|---:|
| Citas que **son** literales | **195 (57,9 %)** |
| Citas que no lo son y degradan a `parafrasis` | 133 (39,5 %) |
| **Podadas por procedencia fabricada**, sin llegar a comparar | **9 (2,7 %)** |

**Tres cosas que salen de ahí y que no estaban previstas:**

1. **La puerta de `fragmento_en_contexto` para trabajo real: 9 de 337.** El modelo cita fragmentos que no estuvieron en su contexto en el **2,7 %** de los casos. No era una precaución teórica.
2. **La longitud de la cita predice el fallo:** las que pasan tienen mediana **42** caracteres y las que fallan, **124**. Por encima de 120 falla el 54 %, por debajo el 30 %. **El tope de 120 hace doble trabajo** —latencia y verificabilidad—, y eso cambia cómo se justifica.
3. **El 42 % que no cita literalmente es el número de cabecera de este encargo**, y su regla de lectura va escrita al lado: no es la tasa de alucinación —muchas serán paráfrasis mal etiquetadas—, por eso degradan en vez de podarse, y por eso la poda subirá en el 4.3 sin que el sistema empeore.

**EL ENCUADRE DEL 42 %, que es el que se dice en voz alta y el que hace que el número duela sin necesitar la palabra "alucinación": el daño no es que sea inventado, es que llega ETIQUETADO COMO CITA.** Una paráfrasis presentada como cita literal es una **mentira sobre la procedencia** aunque el contenido sea correcto, y un alumno que la copie en un examen creyendo que son **las palabras del libro** se equivoca — por haberse fiado, que es lo peor que le puede pasar a quien confía en una herramienta. Es el mismo argumento que esta guía ya usa con la **analogía marcada**: la analogía es útil y legítima, y por eso hay que decir que es una analogía. Aquí igual con la paráfrasis.

> **Y EN PRESENTE, PORQUE DESDE ESTE ENCARGO ES VERDAD: el sistema NO PUEDE mentir sobre qué es una cita literal.** No "es poco probable" ni "el prompt se lo pide": **no puede**, porque lo comprueba una comparación de cadenas **sin ningún modelo en el lazo**. Es la primera mitad de la tesis del proyecto y está entregada. La segunda —que lo que no es cita literal se verifique igualmente— es el 4.3.

**Y QUÉ ERAN LOS NUEVE DE LA PUERTA, porque el modo de fallo vale más que el porcentaje: 9 ocurrencias pero 3 CASOS** (las 337 citas salen de repetir las mismas preguntas, así que la tasa está inflada por repetición). Dos de los tres son **la misma avería y tiene arreglo**: el modelo tomó el número de una **pregunta de test** que prefijaba el texto que estaba citando —el fragmento contiene `45. Para activar la validación…` y él escribió `fragmento_id: 45`— en vez de inventarse un id. Con 223 fragmentos `enunciado_ejercicio` numerados en el corpus, la superficie es grande y conocida. **Arreglo propuesto y NO construido: un identificador no confundible con una enumeración (`F2936` en vez de `2936`), que sigue siendo el id real con un prefijo y no introduce ninguna traducción**; cerraría 8 de 9 ocurrencias y 2 de 3 casos. El tercero es distinto y apunta al **4.5**: el modelo quiso **abstenerse**, no tenía cómo —`literal` exige `fragmento_id: int`— y puso un 0. **Es un agujero del contrato, no un fallo del modelo.**

**QUÉ PASA EN EL INTERÍN, DECLARADO ANTES DE MEDIR NADA, porque el NLI del 4.3 todavía no existe.**
Una `literal` que falla la comparación **no tiene a dónde degradar**: el 4.5 dice que baje a
`parafrasis` y que la compruebe el NLI, y ese verificador se construye después. Sin decidir esto por
escrito, el número que salga del 4.2 se leerá como definitivo y no lo es.

**Decisión: degrada a `parafrasis` marcada `sin_verificar`, no se poda.** Tres motivos:

1. **Es fiel al diseño final.** En el 4.3 esa afirmación irá al NLI; hasta entonces queda en el mismo
   sitio donde acabará, con el veredicto que le corresponde hoy —`sin_verificar` es literalmente lo
   que es—.
2. **Podar inflaría la tasa de poda que este encargo va a medir**, y ese número es de los que se
   citan. Una poda medida con un verificador de menos no es la poda del sistema: es la del sistema
   incompleto, y la diferencia se olvida en cuanto el número entra en una tabla.
3. **Y no relaja nada, porque `sin_verificar` no es un aprobado.** La afirmación no pasa a estar
   respaldada; pasa a estar pendiente. Lo que sí se poda sin esperar al 4.3 es lo que ya tiene
   criterio propio: `fragmento_en_contexto: false`, que es **puerta antes de la comparación** y no
   depende de ningún modelo.

**Y las dos tasas se reportan SIEMPRE por separado** —"degradadas a paráfrasis" y "podadas"— con la
nota de que la primera es **provisional hasta el 4.3**. Cuando el NLI exista, parte de esas
degradadas se convertirán en podas y **el número de poda subirá sin que el sistema haya empeorado**:
conviene que eso esté escrito antes, o parecerá una regresión.

**4.3 Verificador NLI — CONSTRUIDO el 13 de agosto de 2026 y ENCHUFADO el 14** (`app/core/verificador_nli.py`, evidencia en `docs/evidencia/2026-08-13-verificador-nli.md`). mDeBERTa-v3-base-xnli en CPU. Humo con 10 pares a mano: **9/10, y 4/4 en los que llevan identificadores**.

**Y hasta el día 14 estuvo construido SIN CORRER, que es un estado que no se ve mirando el repo.** El módulo existía con sus tests y **ninguna línea de la ruta de petición lo llamaba**: toda afirmación `parafrasis` salía `sin_verificar`, y con ella una de las cuatro frases del README. Medido sobre un lote de 20 consultas, las afirmaciones factuales **sin verificar pasan del 44,7 % al 0 %**, y el circuito que el 4.2 dejaba abierto —la `literal` **degradada** porque su cita no aparecía letra a letra— por fin lo recoge alguien.

Corre **en un hilo**, y eso es lo que hace verdad la frase del solape: llamarlo desde el bucle que consume trozos no habría solapado con nada —habría bloqueado la lectura, encogido el presupuesto en su misma cantidad y, de paso, podido hacer que el vigilante de ritmo viera lento un flujo que no lo está—. Coste medido con **una sola variable** (`NLI_ACTIVO=0`, el mismo interruptor que la ablación del 7.3 necesita): **~130 ms de media y CERO cortes**.

Dos consecuencias que hay que declarar: una `literal` degradada emite **dos** veredictos y el bueno es el segundo; y un **`reintento_con_señal` no puede reintentar**, porque cuando el NLI contesta la prosa ya está en pantalla y repetirla sería reescribirle al alumno lo que acaba de leer. El evento lo dice con su motivo, para que la tasa de `neutral` del 4.6 no se lea como *"se reintentó y siguió mal"*: **verificar en curso se come el reintento**, y es el precio del solape.

**TRES COSAS QUE HUBO QUE MEDIR ANTES DE CONSTRUIRLO, Y LAS TRES CAMBIARON EL DISEÑO:**

1. **La ventana no daba, y el fallo era peor que el previsto.** Son **512 tokens totales** —premisa más hipótesis— y **el 33 % de los fragmentos la desborda ellos solos** (mediana 480, p95 566, máximo 598), así que la librería trunca en silencio. Se temía un falso negativo; lo que sale es **`entailment 0.988` sobre una premisa truncada que NO sostiene la hipótesis**, confirmado con el control de darle solo el relleno. **Un falso positivo con dos decimales**, que es el lado caro. Por eso la premisa es **una frase seleccionada**, no el fragmento: con la frase correcta, `entailment 0.975`; sin ella, `neutral 0.949`.
2. **La maquinaria del 1.8 se reutiliza, pero DOS de sus parámetros no transfieren.** Su tope de 12 frases es correcto para comparar fragmento contra fragmento (O(n²)) y aquí **tira la cola** (la frase de apoyo estaba en la posición 42 de 43). Y su detector de código caza `@\w+`, o sea que marca como código **la prosa que menciona identificadores** — que en este corpus es casi toda: fallaba **4 de 10** contra **1 de 10** del detector por densidad. **Se reutiliza el código validado y se comprueba que sus parámetros transfieren.**
3. **Mirar a ojo antes de fiarse del umbral encontró lo que el agregado escondía:** 3 de los 4 fallos de la primera corrida estaban en los pares con identificadores. El agregado decía "6/10, el modelo va regular"; la verdad era "nuestro filtro descarta la prosa de este temario".

**Lo que NO se juzga se declara `no_verificable` en vez de inventarle veredicto:** código (heredado del 1.8, con test) y afirmaciones sin vocabulario en común con ninguna frase del fragmento. Y `contradiction` **poda sin mirar el umbral**, que es la señal más cara de ignorar.

**Y AL LLEGAR AQUÍ SE RE-MIDE LA TASA DE PODA DEL 4.2 Y SE REPORTAN LAS DOS**, porque parte de las
`literal` degradadas a `parafrasis` en el interín pasarán a podarse. **El número de poda subirá sin
que el sistema haya empeorado**, y sin este aviso escrito de antemano parecerá una regresión.

**EL NLI VA EN CPU, Y ESTÁ MEDIDO ANTES DE CONSTRUIRLO** (13 de agosto de 2026). El motivo no es que
la CPU sobre: es que **la GPU ya es el cuello** —embebedor y reordenador serializan desde el quinto
alumno— y meter allí un tercer modelo bajaría otra vez el techo de concurrencia y empeoraría la
degradación medida. Mismo patrón que ya acertó dos veces: **el suelo barato primero, el hardware solo
si el número lo exige.** Medido con `mDeBERTa-v3-base-xnli` en fp32 sin cuantizar, premisa =
fragmento real y hipótesis = texto de afirmación real:

| Hilos | 1 par (p95) | 4 pares (p95) | ¿Cabe en el presupuesto de verificación de 2 s? |
|---:|---:|---:|---|
| 2 (tipo CX22) | 804 ms | 3.173 ms | **no** |
| 4 (tipo CX32) | 588 ms | 2.294 ms | **no** |
| **16 (máquina de la demo)** | **216 ms** | **1.150 ms** | **sí, holgado** |

**Cabe en la máquina de la demo y NO en un VPS pequeño**, así que hereda exactamente la divergencia
del 8.1 y no añade una nueva. Y quedan dos márgenes sin usar: **la cuantización** que este encargo ya
pedía (2-3× típico, que metería el caso de 4 hilos dentro) y el hecho de que **no todas las
afirmaciones van al NLI** —solo las `parafrasis` y las `literal` degradadas, que son el 40 % medido
en el 4.2—, o sea del orden de **1-2 pares por respuesta y no 4**: unos 350 ms en la máquina de la
demo.

**Y UN HALLAZGO QUE REFRAMEA LA DECISIÓN DEL ORDEN DEL CONTRATO, con su aritmética:** como
`afirmaciones` va **antes** de `respuesta_redactada`, las afirmaciones están completas ~823 ms antes
de que termine la prosa. La verificación NLI corre en **CPU** y la prosa la genera el **proveedor**,
así que **el NLI cabe entero dentro de la ventana en la que el modelo aún está escribiendo**: 350 ms
de verificación dentro de 823 ms de prosa. En tiempo de pared, **la verificación sale gratis**.

Eso le da al orden del contrato una **tercera justificación** que nadie había nombrado —además de que
la prosa después de los hechos evita la justificación a posteriori, y además de la retirada—: **es el
orden que permite verificar mientras se redacta.** El orden que nos cuesta TTFT es el que nos regala
la verificación. Se anota aquí porque el 3.4 dejó abierta la salida (b) —invertir el orden— y este
número la aleja todavía más.

**4.4 Verificador de cálculo — la ARITMÉTICA construida el 13 de agosto de 2026** (`app/core/verificador_calculo.py`), **el SANDBOX declarado y NO construido**. Aritmética con sympy (jamás `eval`). Código en sandbox: contenedor efímero sin red, 0,5 CPU, 256 MB, timeout 5 s, sistema de archivos solo lectura salvo `/tmp`. Verificación: un cálculo correcto pasa, uno incorrecto poda, un código con bucle infinito muere por timeout sin tumbar el worker, un código que intenta red falla.

**AGUJERO MEDIDO EL 14 DE AGOSTO Y NO CERRADO: EL MODELO ESQUIVA ESTE VERIFICADOR NO DECLARANDO EL CÁLCULO COMO CÁLCULO.** La derivación fabricada que cazó el conjunto del 5.0 —*"160 horas - 20 horas = 140 horas"*, con aritmética inventada para aterrizar en el número que le dieron— llegó etiquetada como **`conocimiento`**, sin `expresion`, así que el recálculo **nunca la miró**. Y es sistemático: de 629 afirmaciones reales, **4 `andamiaje` y 1 `conocimiento` llevan una cuenta con `=` en su propio texto** (frente a 0 de 250 `literal` y 0 de 208 `parafrasis`). `andamiaje` es el peor sitio, porque acumula **dos** privilegios: no se verifica **y** cuenta como respaldo de cobertura, o sea que una cuenta metida ahí además **autoriza prosa**. La sección 3 ya declaraba un validador para esto —*"si una frase de andamiaje afirma algo del temario, es afirmación y se verifica como tal"*— y **no existe**. Es el principio 7ter en su forma pura: la elección de tipo no se puede imponer con la gramática, así que o se pide en el prompt o **el verificador deja de fiarse de la etiqueta**. **RESUELTO EL MISMO 14 DE AGOSTO: (b) con (a) encima** —el verificador recalcula toda cuenta encontrada en el texto sin mirar la etiqueta (`verificar_texto`, marcada `calculo_no_declarado`), el `andamiaje` con cuenta dentro pierde el privilegio de respaldo, y el prompt añade la preferencia—; las dos opciones y sus costes quedaron en `docs/evidencia/2026-08-14-corregir-desde-resultado.md`, con el alcance declarado: el `=` es una cota inferior.

**Y EL LÍMITE QUE ESE ARREGLO NO TOCA, escrito como el límite que es: EL RECÁLCULO COMPRUEBA LA OPERACIÓN, NO LOS OPERANDOS.** Un operando inventado con aritmética correcta sale `verificada` —*"160 − 20 = 140"* cuadra; lo fabricado era el 20—, y ese es el modo de fallo **más probable** de un modelo de lenguaje: inventar una premisa, no equivocarse sumando. O sea que el verificador de cálculo comprueba el error **menos** frecuente. **Atar los operandos al temario es una verificación NUEVA, declarada y no construida**; lo que sí hay desde el 14 de agosto es su **contador** (`operandos_sin_fuente`, en la traza de cada `calculo` y retroactivo en `scripts/medir_operandos.py`): operandos que no están ni en el fragmento citado, ni en la pregunta, ni en un resultado anterior de la misma respuesta. **Medido sobre las 74 afirmaciones `calculo` reales: 40 (54,1 %) llevan algún operando sin fuente, 72 ocurrencias** — y leído por casos, como manda la regla: **54 de las 72 son cifras de convención** (el `/100` del porcentaje ×16, la enumeración `1+2+…+10` ×35, el 60 de minutos/hora ×3) y **~18 son premisas potencialmente inventadas**, concentradas en la familia *"5 horas > 4.5 horas"* (15). La verificación futura tendrá que distinguir convención de premisa, y este reparto es su primer dato de diseño.

**Estado leído cláusula a cláusula:** las dos primeras se cumplen y están en `tests/test_verificador_calculo.py`; las dos últimas son del sandbox y **no se cumplen**, porque el sandbox es el **peldaño 1 de la escalera de contingencias** y se toma a propósito y con tiempo por delante. El código que llegue en `expresion` sale **`no_verificable`, jamás `podada`**: no poder comprobarlo no es que sea falso, y confundirlos castigaría al modelo por una capacidad que decidimos nosotros no construir. El momento 4 de la demo queda cubierto igual, porque el ejercicio desde el resultado **es aritmético**.

### LA GRAMÁTICA PROHÍBE; NO ELIGE — y por eso el 4.4 nació decorativo

El verificador estaba entero, correcto y medido, y **no veía una sola afirmación**. Cinco consultas explícitamente aritméticas contra el proveedor real dieron **cero afirmaciones de tipo `calculo`**: el modelo contestaba *"son 62"*, *"son 21"*, *"4.294.967.296"* como `conocimiento`, sin `expresion` que recalcular. Y antes de eso, las **345 afirmaciones reales** de la base tampoco tenían ninguna (337 `literal`, 8 `parafrasis`), así que el aviso no estaba en ningún sitio.

La causa fue aplicar el principio 7 una planta de más: `calculo` no aparecía en el prompt porque su explicación cabía en el `description` del campo. Pero **elegir entre cinco ramas que el esquema permite todas no es algo que el esquema decida**, y la descripción de un campo es una etiqueta que solo se lee cuando ya se ha llegado a él. El principio 7 dice *no pidas por prompt lo que la gramática puede imponer*; no dice *no expliques por prompt lo que la gramática no puede decidir*.

Y la línea que lo arregla **no es gratis**, con su número **y con la condición en que se midió delante**: en la consulta de IVA en modo `corregir` **y sin fragmentos en contexto**, **7 de 10 corridas** chocan con el tope de 900 tokens, contra **0 de 3** sin ella. Pero por el **camino real**, con corpus, son **0 de 6**: media de 3,0 afirmaciones, máximo 5, y 386 tokens de salida de media. **Sin material que citar el modelo se explaya; con material se ciñe a él**, que es la tesis del proyecto vista desde el consumo de tokens — y el fuego, por tanto, está medido en una condición que no es la de producción.

El tope de `afirmaciones` se pone igual (**`maxItems: 10`, ADR 0017**), pero como **prohibición barata y declarada SIN CALIBRAR**, no como arreglo de un incendio: n=6 no demuestra ausencia. Y su valor **no** sale de las 110 respuestas históricas —de 1 a 6, ninguna pasa de 6— porque esas son **anteriores a que existieran los modos** y no contienen ni una derivación de `corregir`: derivarlo de ahí habría recortado justo lo que motivó el cambio. Es el principio 11 con la muestra elegida por **cuándo**.

### Y LA GRAMÁTICA LLEGÓ A FABRICAR UN NÚMERO FALSO (ADR 0016)

Con el punto como separador decimal, el modelo quiso escribir `4.294.967.296` —correcto en español, y así salió en la prosa de esa misma respuesta— y la decodificación restringida, que permite **un** punto y no dos, dejó **`4.294967296`**: cuatro coma tres en vez de cuatro mil millones. Un número **gramatical y equivocado**, y el veredicto era `podada` —*"el alumno se ha equivocado"*— cuando quien había roto el número era nuestra propia gramática. Es el **principio 7bis** por tercera vez: cuando el campo no admite la forma que el modelo necesita, el modelo no se calla, **deforma**. Decírselo en el `description` no bastó; se arregló en el patrón, con **coma decimal**, que deja los puntos de millar ingramáticos desde el primer carácter.

**ORDEN OBLIGATORIO DE LA VERIFICACIÓN, escrito en el 3.3 y aquí porque aquí se aplica: `fragmento_en_contexto: false` es PUERTA, y va ANTES de la comparación literal.**

El verificador literal del 4.2 comprueba que la cita esté **dentro del fragmento**; no comprueba que ese fragmento **estuviera en el contexto**. Con 11.282 fragmentos que se solapan 64 tokens, **un `fragmento_id` inventado que apunte a prosa del mismo tema puede contener una frase que case** — y entonces el verificador daría por buena una cita fabricada, que es exactamente el fallo que toda esta capa existe para impedir. Es un agujero que la fase 4, tal como estaba escrita, **no habría cazado**.

**Y el orden importa, no es una preferencia:** si la comparación corre primero y pasa, ya se ha producido un veredicto favorable sobre una cita que el modelo no pudo haber leído. Una afirmación cuyo `fragmento_id` no estuvo en el contexto **no se compara: se poda**, y se registra como lo que es —procedencia fabricada—, que además es una señal del generador que conviene contar.

**4.5 Política de respuesta — la cobertura CONSTRUIDA el 13 de agosto de 2026** (`app/core/cobertura.py`). Cobertura de `respuesta_redactada` por afirmaciones (sección 7), reintento único con señal, abstención como respuesta renderizada con dignidad en la interfaz ("esto no está en tu temario de X; lo más cercano que tengo es...").

### LA REGLA DE COBERTURA CHOCABA CON EL FLUJO, Y LA SALIDA VUELVE A SER EL ORDEN DEL CONTRATO

**El conflicto:** la prosa se emite **en streaming**, así que cuando la cobertura pudiera comprobarse —con la redacción completa— **el alumno ya la ha leído**. Podar entonces una frase huérfana significa **retirar texto de la pantalla**, y la retirada del 2.4 se diseñó como **excepcional**: si la cobertura podara a menudo, el alumno vería tachones con frecuencia, que es **peor que lento y peor que seco**.

**La salida:** las afirmaciones están **completas antes de que empiece la prosa**, así que la cobertura se comprueba **frase a frase, según cada frase se cierra**, contra unas afirmaciones ya conocidas. **Solo se emite la frase que ya está cubierta.** Cuesta **una frase de retraso**, no una espera entera, y la retirada vuelve a ser excepcional. Es el mismo aprovechamiento del orden del contrato que dio la verificación gratis en el 4.2 — **tercera vez que ese orden paga**.

**Las dos alternativas, descartadas con su motivo:** (a) **no emitir hasta comprobar** devuelve el TTFT que costó dos días de trabajo; (b) **emitir y retirar** deja al alumno leyendo texto que se tacha, y **contradice el argumento de la propia demo** — un sistema que presume de no afirmar sin respaldo no puede afirmar primero y desdecirse después como rutina.

### Y LA ASIMETRÍA AQUÍ ES DISTINTA DE LAS ANTERIORES, declarada antes de elegir el umbral

| | Qué cuesta |
|---|---|
| **Falso positivo** | cuela en la respuesta contenido **no declarado** en ninguna afirmación |
| **Falso negativo** | **poda una frase legítima de un texto que alguien está leyendo**, y deja un **agujero en mitad de un párrafo** |

En el 4.2 y el 4.3 el falso negativo era barato y por eso se erraba hacia el rechazo. **Aquí no:** podar una afirmación es invisible para el alumno, podar una frase de la redacción **se ve**. El umbral se elige con **las dos consecuencias delante**, y su barrido va al 4.6 como los demás.

**Y `andamiaje` es lo que evita el falso negativo MASIVO**: sin esa excepción, la regla se llevaría por delante **todas las transiciones y preguntas al alumno** —que no afirman nada del mundo (sección 3)—, dejando una respuesta correcta y **mutilada**. **La `cita` también respalda**, y olvidarlo producía el mismo fallo en pequeño: lo cazó el primer test que se corrió.

### LA ABSTENCIÓN, YA EXPRESABLE (el hueco que dejó el principio 7bis)

El caso que lo motivó: una afirmación citaba *"No se puede responder con los fragmentos proporcionados"* con `fragmento_id: 0` — **el modelo queriendo abstenerse y deformando el único campo que tenía**, porque el contrato no le daba forma de decirlo. Desde el 4.1 la tiene, y es la que este encargo dibuja: **cero afirmaciones factuales, un solo `andamiaje` que lo explica, y la redacción diciéndolo**. Sin inventar un `fragmento_id` para poder hablar. **Y la respuesta ante conflicto, con el criterio que fija el 1.8:** si la recuperación trae fragmentos que la tabla `conflictos` relaciona, la respuesta **enseña las dos versiones con su fuente y su fecha, y dice cuál es la más reciente**, sin declarar cuál es la correcta. La preferencia es por vigencia y se dice que lo es. Ese es el momento 3 de la demo y también la única postura honesta: el sistema sabe que su corpus se contradice y no tiene autoridad para arbitrar.

**4.6 Calibración del umbral NLI.** Con los pares oro y los conjuntos de fuera de temario y premisas falsas (4.0): barrer el umbral de 0,6 a 0,95 y elegir el punto que maximiza corrección de premisas falsas sin disparar podas de paráfrasis buenas. El barrido entero va a `corridas_eval` y la elección a un ADR. **HECHO EL 14 DE AGOSTO DE 2026, y con el alcance ampliado por el propietario a INVENTARIO con desenlace obligatorio: los seis umbrales declarados sin calibrar salieron con desenlace escrito — NLI 0,60 + suelo 0,30 (plano de la corrida 32, desempate pre-escrito, ADR 0020), márgenes de confianza 0,085/0,025/0,664 sobre DWES (corrida 33, criterio pre-escrito, con la normalización por partición DECLARADA: el oro es 100 % DWES y el instrumento no lo permite), y tres SIGUE SIN CALIBRAR con su porqué comprobado — portero y ritmo esperan la prosa y el ritmo persistidos (los desbloquea el 2.5, que por eso pasa por delante del 5.3), y el anclaje de operandos es diseño antes que barrido. El hallazgo gordo no fue un umbral: el 70 % de los positivos falla por SELECCIÓN (la hipótesis del NLI es el texto, no la cita, y 96 de 189 citas cruzan frases); el arreglo barato (sesgo hacia la frase con la cita, alcanza 37) y la multi-frase quedan declarados con su número en la evidencia** (`docs/evidencia/2026-08-14-calibracion-4.6.md`). **Cierre de fase 4:** sobre los conjuntos del 4.0, abstención correcta y tasa de conformidad con premisa falsa medidas; fidelidad literal demostrada con su test anclado; umbral calibrado con evidencia.

**Y EL UMBRAL DE COBERTURA SE CALIBRA SOBRE LA MEDIDA ARREGLADA DEL 14 DE AGOSTO, NUNCA SOBRE LA ANTERIOR.** Hasta ese día el solape contaba el **vocabulario de la cita** —`según`, `fragmento`, `temario`—, palabras que no pueden estar en ninguna afirmación porque son la referencia a la fuente: la medida **castigaba a la prosa por decir de dónde salía**, y de paso penalizaba tener pocas afirmaciones y escribir con conectores. Barrer el umbral sobre esa medida habría dado un número bajísimo que **codificaría el régimen roto y se quedaría ahí para siempre** — exactamente lo que habría pasado calibrando el NLI con la premisa larga en vez de arreglar la selección de frase. **Primero se arregla qué se mide, después se barre.** Cualquier barrido anterior a ese arreglo se descarta.

### EL CONJUNTO DE CALIBRACIÓN, RESUELTO ANTES DE LLEGAR PORQUE HOY NO EXISTE

**Los pares oro NO sirven para calibrar esto, y conviene verlo antes de plantarse aquí sin conjunto.**
Son **pregunta → fragmento**; lo que este encargo necesita son **tripletes afirmación → fragmento →
veredicto verdadero**, y eso no lo ha etiquetado nadie. Dos controles que **se derivan solos, sin una
hora de etiquetado humano**:

| Control | De dónde sale | Por qué es válido | Tamaño hoy |
|---|---|---|---:|
| **Positivos** | afirmaciones que **pasan** la comprobación literal del 4.2 | su texto está **textualmente dentro** del fragmento, así que están *entailed* **por construcción**; lo que el NLI falle ahí es **falso negativo medido** | **195** |
| **Negativos** | la misma afirmación emparejada con **otro fragmento de la misma asignatura** | casi con seguridad no la sostiene, y lo de *"misma asignatura"* impide que el negativo sea trivial por hablar de otra cosa | **~195** |

**Lo que NO resuelven, dicho de frente: el caso difícil.** La paráfrasis dudosa —la que reformula de
verdad y hay que decidir si se sigue del fragmento— es justo el **medio**, y ahí sigue sin haber
etiqueta. Pero los dos controles **acotan el umbral por los dos lados sin coste**, y **un umbral que
fallara cualquiera de ellos estaría mal colocado con independencia de lo que opine nadie del medio**:
si poda positivos que son cita literal, está demasiado alto; si aprueba una afirmación contra un
fragmento que no la menciona, demasiado bajo.

### EL PLANO ENTERO CUESTA **UNA** CORRIDA, NO VEINTE

El suelo decide **qué pares llegarían** al modelo y el umbral decide **entre los que llegan**: las dos
son decisiones **posteriores sobre la misma tabla**. Así que se consulta el NLI **una vez sobre TODOS
los pares** —incluidos los que quedarían por debajo de cualquier suelo candidato—, se guarda de cada
uno su **cobertura** y su **puntuación**, y el plano `(suelo × umbral)` se calcula después **sin
volver a llamar al modelo**.

**Y que quede dicho para que nadie lo lea como una violación del propio suelo:** consultar por debajo
del suelo es legítimo **aquí** porque se está **midiendo el instrumento**, no ejecutando el sistema.
En servicio, por debajo del suelo no se pregunta —y hay test que lo comprueba espiando las llamadas—;
en calibración hay que preguntar precisamente ahí, porque si no, no habría con qué decidir dónde
poner el suelo. Es la diferencia entre usar un termómetro y calibrarlo.

**CONDICIÓN DE MÉTODO, ESCRITA EN EL 4.3 Y ANTES DE QUE EXISTA NINGÚN BARRIDO: EL UMBRAL SE CALIBRA
SOBRE PARES YA SELECCIONADOS, JAMÁS SOBRE FRAGMENTOS CRUDOS.**

Medido en el 4.3: con el fragmento entero como premisa —que en el 33 % de los casos desborda la
ventana y se trunca en silencio— el NLI da **`entailment 0.988` a una hipótesis que la premisa no
sostiene**. Ese es un **régimen roto**, no un régimen difícil. Si el barrido se corriera ahí, el
umbral que saliera **codificaría el modo roto**: haría falta ponerlo altísimo para filtrar los falsos
positivos de 0,988, y quedaría alto **para siempre y por el motivo equivocado** —contra un ruido que
la selección de frase ya elimina—, castigando de paso a las paráfrasis legítimas del régimen bueno.

Es la misma familia que el principio 10 y el 11: un número calibrado sobre el material equivocado no
sale mal, sale **plausible**. Así que el barrido corre sobre la **misma tubería que produce los
veredictos en servicio** —frase seleccionada, suelo de cobertura aplicado, código descartado— y se
declara así en la corrida. **Y el suelo de cobertura se barre CON el umbral, no antes ni después:**
los dos deciden juntos qué llega al modelo y cuánto se le exige, y calibrar uno con el otro fijado da
el óptimo de una sección y no del plano.

**AQUÍ SE CALIBRA TAMBIÉN `confianza_recuperacion`, Y LLEGA CON UN SESGO YA MEDIDO: EL MARGEN
DEPENDE DEL TAMAÑO DE LA PARTICIÓN.**

La regla del 3.3 mira **cuánto le saca el primer candidato al sexto**, y esa cantidad no es
comparable entre asignaturas. En una partición pequeña hay menos material entre el que destacar, así
que los seis primeros se parecen más entre sí y **el margen sale bajo aunque la respuesta esté**. No
es una conjetura: *"¿Qué es una clave primaria y por qué no puede repetirse?"* da `baja` en la 0613
—correcto, cae fuera de su temario— pero **también da `baja` en la 0484, que es su asignatura**
(margen 0,049), y la 0484 tiene **485 fragmentos** frente a los **3.892** de la 0613.

**Y por eso no basta con decir que el campo "es conservador".** Un umbral único desconfía de más
justo en las asignaturas pequeñas, que son las de **DAM y ASIR** —las titulaciones parciales del
corpus—. El sistema saldría sistemáticamente más inseguro en dos de las tres por una propiedad del
**corpus**, no de la pregunta: la abstención se dispararía donde menos material hay, que es
exactamente donde el alumno ya está peor servido. Es un sesgo que se acumula, no que se compensa.

**Salidas, y la calibración elige con el barrido delante:** normalizar el margen por tamaño de
partición —o por la dispersión de la propia lista de candidatos, que ya se tiene medida—, o aceptar
un **umbral por asignatura**. Lo que no vale es dejar un umbral único haciendo como que mide lo
mismo en todas. El barrido se reporta **por asignatura además de en global**, por el mismo motivo por
el que el 3.5 reporta `busqueda` y `lectura` por separado: la media de dos regímenes distintos no
describe a ninguno.

## Fase 5: modos y proactividad

**5.0 Los conjuntos de los dos modos (vienen del 1.10; PRIMER ENCARGO DE LA FASE).** Dos ficheros
en `evals/casos/`:

1. `corregir_desde_resultado.jsonl` (mínimo 20): ejercicios con resultado, **mitad correctos y mitad
   con el resultado MAL**; esperado en estos últimos: que el sistema diga que quizá el resultado
   está mal, en vez de forzar una derivación que aterrice donde le dicen.
2. `fuga_de_solucion.jsonl` (mínimo 30, **CONGELADO en el momento de crearse**): intentos de sacarle
   la solución al modo acompañar —ruegos, órdenes y trampas como "mi profesor dijo que me la des"—;
   esperado: guía sin solución. **Se congela porque es el único conjunto que mide una resistencia**,
   y un conjunto que se retoca después de ver los fallos deja de medir al sistema y pasa a medir
   cuánto se ha adaptado el conjunto: se escribe una vez, se cierra, y a partir de ahí solo se
   regresiona contra él en cada cambio de prompt o de modelo (5.2).

**Quién los produce, y aquí los dos no se parecen:** `fuga_de_solucion` **se redacta sin tocar el
corpus** —son maneras de pedir la solución, y de eso sabe cualquiera que haya dado clase—, mientras
que `corregir_desde_resultado` **necesita material concreto del corpus**: ejercicios reales con su
resultado, que en este corpus salen de los 223 fragmentos `enunciado_ejercicio` y de las soluciones
en Java de Programación.

**Y ESA ÚLTIMA FRASE ERA FALSA, comprobado el 14 de agosto de 2026 leyendo los fragmentos en vez de fiarse de su etiqueta.** `enunciado_ejercicio` lo asignaron reglas en el 1.4 y significa *"esto parecía un enunciado"*: leídos, son tareas de configuración y de programación. **Cuatro de 223** dan un ejercicio con resultado comprobable —dos de FOL (nóminas y contratos) y dos de Programación (IVA y PVP)—, y solo 15 llevan siquiera un número con unidad. **El conjunto se construye igual, pero partido en dos y reportado por separado** (`docs/evidencia/2026-08-14-corregir-desde-resultado.md`): **4 casos con el enunciado EXTRAÍDO** del corpus y **16 REDACTADOS sobre un fragmento real**, cada uno con su `fragmento_id` de apoyo. Es el mismo diseño `busqueda`/`lectura` del 3.1 y hace lo mismo: **convierte el sesgo declarado en sesgo medido**, porque un conjunto escrito por quien construye el sistema le favorece y la única forma de saber cuánto es medir los dos lados. Y es el **espejo del conjunto oro**: allí la pregunta venía de fuera y el fragmento lo elegía uno —con el riesgo de elegir el que la recuperación encuentra fácil—; aquí el fragmento es real y la pregunta la escribe uno, con el riesgo de escribir la que el sistema resuelve bien. Mismo error, lados opuestos. **Congelado antes de correr ningún caso** (SHA-256 `f3c6848b7a2f4479…`), como el `fuga_de_solucion`: un enunciado retocado después de ver la respuesta deja de medir al sistema. La mitad con el resultado mal se fabrica a partir de los buenos, cambiando
el resultado y **anotando en el caso cuál era el correcto**, que es lo que permite corregir la
corrección.

**5.1 Clasificador de entrada.** Dos capas: reglas primero (el usuario fuerza modo; una foto o un "corrige esto" van a corregir; un "no me lo digas, guíame" va a acompañar), y el modelo pequeño para el resto con salida estructurada `{modo, complejidad}`. Su acierto se mide sobre un conjunto etiquetado de 50 entradas. Verificación: acierto anotado; los errores leídos uno a uno.

**5.2 Modo acompañar.** Máquina de estados explícita: presentar problema, esperar paso del alumno, validar paso contra temario (con la misma verificación de la fase 4), pista si atasco, cierre con resumen. Verificación: la tasa de fuga de solución sobre `fuga_de_solucion.jsonl`, el conjunto congelado del 5.0, medida y regresionada a partir de aquí en cada cambio de prompt o modelo.

**5.3 Modo corregir.** El flujo del oráculo (sección 3). Verificación: `corregir_desde_resultado.jsonl` completo (5.0); los casos con resultado mal deben terminar en "quizá el resultado está mal", no en una derivación inventada que aterrice a la fuerza.

**CORRIDO EL 14 DE AGOSTO DE 2026 Y NO CERRADO, con el motivo medido** (`docs/evidencia/2026-08-14-corregir-desde-resultado.md`). El conjunto existe, está partido en `real` (4) y `redactado` (16) y **congelado antes de correr ningún caso**; el flujo del oráculo ya venía del prompt del 4.1. **Lo que impide cerrarlo no es el modo `corregir`: es que el propio pipeline destruye 9 de las 20 respuestas antes de que el alumno lea nada** — 4 por el plazo y **5 por la puerta de cobertura del 4.5**.

El caso que lo enseña entero: prosa correcta y con su fragmento citado —*"En una jornada continua de 7 horas, el descanso mínimo es de 15 minutos, según el fragmento F5962 del temario"*—, **podada por un solape de 0,44 contra un umbral de 0,50**, entregada en 1,7 s y con `abstencion: False`. **El alumno ve una pantalla en blanco y la traza lo cuenta como respuesta entregada.** Es la asimetría que el 4.5 declaró, medida por primera vez y peor de lo previsto: no deja un agujero en el párrafo, **se lleva el párrafo**. Con una sola afirmación el vocabulario de respaldo es minúsculo y cualquier frase legítima cae por debajo del umbral; **su calibración es el 4.6 y este es el dato que le faltaba**.

De las **6 entregadas con el resultado mal**, leídas a ojo: **4 corrigen** el número y **ninguna fabricó una derivación que aterrizara donde le decían**, que es el fallo caro; **2 no** —una acepta la premisa falsa y otra sale mutilada por la misma puerta—. Con n=6 eso es un indicio, no una tasa, y el criterio **no se declara cumplido**.

**5.4 Proactividad.** `siguiente_paso` resuelto contra el árbol (siguiente unidad o concepto del glosario aún no tocado en la conversación; **se recorren términos DISTINTOS y no filas**, que desde el ADR 0012 no es lo mismo). Verificación: en 20 conversaciones de humo, el siguiente paso existe en el árbol el 100% de las veces.

**Cierre de fase 5:** los tres modos operativos con sus métricas en la tabla.

## Fase 6: caché, escalonado y coste

**6.1 Caché semántica.** Clave: organización + asignatura + modo + embedding de la consulta; acierto por similitud ≥ `UMBRAL_CACHE_SIM` (inicial 0,92, calibrado mirando 20 aciertos y 20 fallos a ojo). Invalidación total por cambio de `VERSION_CORPUS` o `VERSION_PROMPT`. La respuesta cacheada conserva sus afirmaciones y veredictos. Verificación: la misma pregunta parafraseada acierta; una pregunta de otra asignatura jamás acierta.

**6.2 Escalonado.** Señales de escalado al modelo grande: `complejidad: alta` del clasificador, `confianza_recuperacion: baja`, o rechazo del verificador en el primer intento. Verificación: tasa de escalado medida; 10 casos escalados leídos a ojo para confirmar que lo merecían.

**No hay 6.3, y no es un descuido:** la curva de coste contra garantía era el cierre de la fase 6 y vive en su criterio de cierre, no en un encargo propio. Se dice porque un hueco de numeración sin explicar acaba fabricando una referencia fantasma a un encargo que no existe —ya ha pasado dos veces en este proyecto—.

**6.4 Carga y concurrencia (hueco detectado y cerrado: la escala de USUARIOS no estaba medida en ningún encargo).** Hasta aquí todo el argumento de escala habla del tamaño del corpus, y son dos cosas distintas: que la rebanada de búsqueda no crezca con el corpus no dice nada de qué pasa con veinte alumnos preguntando a la vez. Va al final de la fase 6 porque necesita la caché y el escalonado ya construidos; medirlo antes daría números de un sistema que no es el que se despliega. Se mide: **20 y 50 consultas concurrentes**, con TTFT y punta a punta en **p50, p95 y p99**, **con y sin acierto de caché** (son dos regímenes distintos y mezclarlos esconde los dos); **tasa de errores y de timeouts**; **comportamiento de la cola bajo saturación**, que debe degradarse de forma ANUNCIADA (cola llena, espera estimada, rechazo explícito) y jamás en silencio; y la comprobación de que **la ingesta nocturna no roba latencia a la consulta interactiva**, saturando la cola `ingesta` mientras se mide la `interactiva`, que es exactamente la razón por la que se separaron en el 2.3. **Criterio de cierre:** las cuatro curvas persistidas en `corridas_eval`; el SLO declarado en la Parte V (p95 por debajo de 3 s en camino completo, 300 ms en acierto de caché) confirmado o corregido con el número medido; y la degradación bajo saturación vista y descrita. Si el SLO no se cumple, se dice con su número y se declara qué pieza lo arregla, no se baja el listón en silencio.

**Cierre de fase 6:** acierto de caché, tasa de escalado y curva coste-garantía (coste medio con verificación completa contra camino barato) en la tabla.

## Fase 7: la tabla de configuraciones (la evidencia)

**7.1 El arnés.** `evals/arnes/` corre TODOS los conjuntos contra una configuración dada y persiste la batería completa (Parte VII) en `corridas_eval`, con commit y config. Determinismo: temperatura 0 donde el proveedor lo permita; donde no, N=3 repeticiones y se reporta la dispersión (no se esconde). **MEDIDO EN EL 2.2, y aquí es N=3:** Scaleway acepta `temperature: 0` y `seed`, y aun así tres llamadas idénticas con la misma semilla devolvieron tres textos distintos —dos veces, en local y en el runner de CI— (`docs/evidencia/2026-08-12-humo-proveedor.md`). Temperatura 0 con semilla es una **petición** de determinismo, no determinismo: en un servidor con lotes variables la aritmética en coma flotante cambia con el tamaño del lote. Así que toda medida de calidad de este arnés va con N=3 y su dispersión, y una corrida sola no se compara con otra corrida sola.

**CUÁNTO varía, que es lo que decide si el 7.3 sigue siendo legible.** "Salieron textos distintos" no basta: que cambie la redacción y que cambie el conjunto de afirmaciones son dos cosas distintas y solo la segunda compromete la ablación. Medido por dimensiones separadas sobre las mismas tres llamadas (`scripts/humo_proveedor.py --repeticiones 3`), en dos rondas del 12 de agosto:

| Dimensión | Ronda A | Ronda B | Ronda C |
|---|---|---|---|
| Bytes | distintos | distintos | distintos |
| **Número de afirmaciones** | **2, estable** | **2, estable** | **2, estable** |
| **Tipos de las afirmaciones** | **estables** | **estables** | **estables** |
| `fragmento_id` citados | estables (vacío) | estables (vacío) | estables (vacío) |
| Texto de las afirmaciones | 99,9 % en común | 93,7 % | 100 % |
| Redacción | 99,9 % | 71,8 % | 100 % |

**Lectura: la FORMA del conjunto aguanta y lo que baila es la redacción.** En nueve llamadas idénticas salieron siempre dos afirmaciones y siempre de tipo `conocimiento`. Eso deja la ablación del 7.3 legible con N=3, porque las filas se comparan por afirmaciones y veredictos y no por la literalidad del texto. **Con dos condiciones que salen de la ronda B:** cualquier métrica que mire el CONTENIDO de una afirmación (fidelidad literal, NLI) se reporta con su dispersión y jamás como número único; y **la dispersión misma es ruidosa entre rondas** —71,8 %, 99,9 % y 100 % de similitud de redacción en tres medidas del mismo día, con la misma entrada y la misma semilla—, así que caracterizarla necesita más de una ronda de tres. Ese 71,8 % es, además, el número que hace que la regla de lectura del 7.3 pueda morder de verdad.

**Y la forma de esas tres rondas dice algo más: dos a ~100 % y una a 71,8 % no es ruido uniforme, es bimodal**, que es justo lo que se esperaría del tamaño de lote variable en el servidor del proveedor. Si es eso, **la dispersión depende de la CARGA del proveedor**, y entonces la medida de hoy a las 14:40 no es la de mañana a las 10:00. De ahí que para el 7.3 mande **el peor número y no el último**: el peor número no es pesimismo, es lo único que no depende de a qué hora se midió. (Que la causa sea el lote es una hipótesis coherente con lo observado, no algo que este proyecto haya medido: para confirmarlo haría falta instrumentar el servidor del proveedor, que no es nuestro.) **Y el aviso que no se puede olvidar, que es más gordo que el que parecía:** esta medida está tomada en un caso DEGENERADO y **dos de las tres dimensiones de forma no están medidas de verdad**. Los `fragmento_id` salen estables porque están todos vacíos, sin recuperación. Y los **tipos** salen estables por la misma razón: sin fragmentos no existen `literal` ni `parafrasis`, así que `conocimiento` no es una elección del modelo, es la única casilla que la gramática le deja. Bajo recuperación, en cambio, **elegir entre citar literalmente y parafrasear, y elegir CUÁL de los fragmentos recuperados se cita, es una decisión combinatoria que puede variar en cada corrida** — y de esa decisión salen directamente las columnas de veredictos del 7.3, porque una `literal` la verifica una comparación de cadenas y una `parafrasis` un NLI con umbral. **Así que la re-medición de la fase 3 cubre las tres dimensiones juntas: número de afirmaciones, MEZCLA DE TIPOS y `fragmento_id` citados.** Lo único que hoy queda medido de verdad es que la redacción baila y que el número de afirmaciones aguanta.

**7.2 Las cuatro configuraciones.** (a) Scaleway modelo pequeño solo; (b) Scaleway con escalonado (la candidata); (c) self-host vLLM en la 5080 con el 8B cuantizado (instrucciones: vLLM en WSL2 con CUDA, servir con `--max-model-len` acorde a 16 GB, misma URL base en config; **declarado en la tabla que es el hermano de 8B por VRAM**); (d) frontier vía endpoint europeo, solo como referencia de calidad, con su nota de por qué no es elegible.

**7.3 La ablación.** La configuración candidata con la capa de verificación APAGADA, sobre TODOS los conjuntos (no solo los cuatro casos de la demo). La diferencia entre esa fila y la candidata es el argumento central del proyecto convertido en números.

**CÓMO SE LEE ESA DIFERENCIA, decidido el 12 de agosto de 2026 —antes de que el número exista, que es el único momento en que decidirlo es decidir.** Es la misma razón por la que la regla del fragmento único de los pares oro se escribió antes de medir: con el resultado delante, cualquier criterio que se elija está contaminado por el resultado que favorece. La regla:

**Toda fila de la ablación se reporta JUNTO A su dispersión, y una diferencia menor que la dispersión se declara «no distinguible» y no se presenta como mejora.** Ni en la tabla, ni en el README, ni en la sesión. No es una diferencia pequeña: es una diferencia que esta medida no puede sostener, y decirlo así es más fuerte que enseñar un número que no aguanta que le pregunten.

Y no es una precaución teórica: en el 2.2 ya se midió al proveedor devolviendo redacciones con solo un **71,8 %** de caracteres en común entre llamadas idénticas (7.1). Con ese ruido encima, una regla escrita después habría sido una regla escrita para que el número saliera bien.

**7.4 La elección.** Configuración elegida escrita en ADR con la tabla delante: los porqués, los números y el umbral a partir del cual se cambiaría.

**7.5 Benchmark de escala con carga sintética.** La escala es una propiedad de la infraestructura y se demuestra con carga sintética, separada del experimento de calidad (que usa el corpus real). Procedimiento: (1) generador de titulaciones y asignaturas sintéticas clonadas desde las REALES (la base es DAW densa más las hermanas del 1.12 si están cargadas: se clonan titulaciones enteras con permutación de fragmentos y plantillas de variación, nada de descargar relleno de internet), embebidas DE VERDAD con BGE-M3 en la 5080; el objetivo del benchmark se declara en **número de titulaciones, particiones y fragmentos** (por ejemplo, escalones hasta 40 titulaciones y varios cientos de asignaturas), y **la equivalencia en teras se calcula con la ratio binario a texto medida en 1.5 y 1.11, nunca al revés**; (2) escalones de corpus total x1, x10 y x50, hasta unos pocos millones de fragmentos (aritmética honesta del límite: cada vector de 1024 dimensiones en float32 son unos 4 KB, así que un millón de fragmentos son unos 4 GB solo de vectores más índices; el techo lo pone el disco del VPS y se declara); (3) **curva 1, la del argumento:** latencia p50 y p95 de la consulta completa sobre la asignatura REAL mientras el corpus TOTAL crece por los escalones; si la partición funciona, sale plana, y esa curva plana es la demostración de "coste por consulta constante respecto al tamaño total"; (4) **curva 2, la del umbral:** engordar UNA sola partición por escalones y medir hasta que la latencia de esa partición degrade; el punto donde duele convierte el umbral de pgvector de declarado en MEDIDO; (5) extrapolación a dos teras por aritmética: coste e ingesta por giga (medidos en 1.5), almacenamiento de vectores e índices, y qué cambia en cada tramo (réplicas, vectorial dedicado, sharding de particiones entre nodos). Nota de contexto que va al README: dos teras de TEXTO de un ciclo no existen; los teras reales de un cliente educativo son PDF escaneado, vídeo y muchas titulaciones, y se encogen en la ingesta (OCR y transcripción convierten teras de binario en megas útiles por asignatura), así que el camino a teras es un problema de ingesta de binarios más este argumento de partición, no de búsqueda sobre teras de texto. Verificación: las dos curvas persistidas en `corridas_eval` con sus escalones, y el generador sintético con test de humo (los clones jamás contaminan las métricas de calidad: se cargan en particiones sintéticas separadas y se borran al terminar).

**Cierre de fase 7:** tabla completa en `corridas_eval`; elección escrita; ablación medida; las dos curvas de escala medidas y el umbral de pgvector convertido en número.

## Fase 8: despliegue, README y evidencia

**8.1 VPS.** Provisión Hetzner: usuario no root con llave, UFW (22, 80, 443), fail2ban, Docker. `deploy/compose.prod.yml` con Caddy para TLS automático. Secretos por variables de entorno del host, jamás en el repo. Verificación: la URL responde con TLS; `GET /salud` verde.

### LO QUE CORRE EN EL VPS Y LO QUE NO: LA DIVERGENCIA, DECLARADA CON SUS NÚMEROS (13 de agosto de 2026)

**El VPS no tiene GPU y la máquina de la demo sí, así que el sistema desplegado NO corre la tubería
completa.** Se escribe aquí, en el README y en la sección de escala, porque una divergencia entre lo
que se enseña y lo que se despliega **es exactamente el tipo de cosa que este proyecto existe para no
hacer en silencio**.

**Y HAY QUE SEPARAR DOS COSAS QUE NO SON LA MISMA, porque confundirlas miente en los dos sentidos:
lo que es IMPOSIBLE en ese hardware y lo que simplemente NO ESTÁ EMPAQUETADO.** La imagen de
`Dockerfile` instala `requirements.txt`, que **no lleva torch ni transformers** —comprobado dentro
del contenedor en marcha: `torch NO`, `transformers NO`, `sentence_transformers NO`—. Pero de ahí no
se sigue que nada de eso quepa allí, y medirlo cuesta un minuto:

| Pieza | ¿Cabe en 2 vCPU? | Medido |
|---|---|---|
| Léxica (`tsvector`) y glosario | **sí**, son SQL | 27 y 13 ms |
| **Embebedor de la consulta (BGE-M3)** | **SÍ, de sobra** | **112,9 ms de p50, 125,6 de p95 a 2 hilos** |
| Vía vectorial y fusión RRF | **sí**: dependen solo del embebedor | 29 y 13 ms |
| **Reordenado (cross-encoder)** | **NO, y por tres órdenes de magnitud** | **65.648 ms de p95 a 2 hilos** |

**La diferencia no es de opinión, es de cómputo.** Embeber una consulta son ~18 tokens por un modelo
de 568 M una vez; reordenar son 30 fragmentos de 640 tokens por un modelo de 568 M, o sea **21,8
TFLOPs frente a unos 0,04**. Por eso el embebedor cabe en un vCPU con holgura —el 2,5 % de un
presupuesto de 5 s— y el reordenador no cabe en ninguna CPU.

**Así que la frase correcta es esta, y no la que se escribió primero:** el VPS puede correr **todo
menos el reordenado** —o sea del orden del **82,7 % de `recall@20` en `lectura`**, el número de la
vía vectorial— **en cuanto la imagen lleve torch CPU**. Decir que allí solo cabe la léxica (58,0 %)
sería mentir por defecto, y mentir por defecto también es mentir.

**Lo que falta, entonces, es una DECISIÓN PENDIENTE con su coste, no un límite del hardware:** meter
torch CPU en la imagen. Cuesta **~2,5 GB de imagen** y su tiempo de construcción y de despliegue, más
los ~4,3 s de carga del modelo al arrancar el contenedor (medidos a 2 hilos). No se toma hoy porque
el despliegue es la fase 8 y hoy no hay nada que desplegar; **se declara aquí como decisión
pendiente con su número** para que en la fase 8 sea una elección con el coste delante y no un
descubrimiento. La variante barata, si esos 2,5 GB molestan, es la rueda de torch **solo CPU**
(`--index-url download.pytorch.org/whl/cpu`), que es bastante menor: se mide antes de decidir.

`/salud` declara pieza por pieza cuál de los dos modos está activo, y esa es la única razón por la
que esto es una divergencia declarada y no una mentira.

**Los cuatro números que la sostienen, para que no se lea como excusa** (30 candidatos, medidos en
`docs/evidencia/2026-08-13-reordenado.md`):

| Dónde | p50 | p95 | Del presupuesto de **5.000 ms** |
|---|---:|---:|---:|
| **GPU RTX 5080** | 419 ms | **554 ms** | **11 %** |
| CPU 16 hilos (cota inferior) | 10.776 ms | 13.714 ms | 274 % |
| CPU 4 hilos (tipo CX32) | 45.649 ms | 46.246 ms | 925 % |
| **CPU 2 hilos (tipo CX22)** | 64.927 ms | **65.648 ms** | **1.313 %** |

**La fila de 2 hilos es la que hay que mirar y por eso está en negrita: en un VPS pequeño, reordenar
UNA consulta pasa del minuto.** Está aquí para que nadie piense que allí cabría con paciencia, ni que
es cuestión de esperar un poco más.

**Las filas de CPU son COTA INFERIOR y no estimación**: están medidas en un Ryzen 9 9950X3D con
caché 3D apilada y AVX-512, que un vCPU compartido de Hetzner no tiene, y además un vCPU compartido
compite por el núcleo físico con otros inquilinos, que ensancha la cola justo donde vive el p95. El
número real del VPS **solo puede ser peor**. Están aquí para que nadie piense que allí cabría con
paciencia.

**Y esto es el principio 1 aplicado a un segundo modelo, no una excepción a él.** El principio dice
que la inferencia vive detrás de una interfaz compatible y que el proveedor es un enchufe
intercambiable por una URL: para el generador eso ya está construido (`INFERENCIA_BASE_URL`). El
reordenador es la misma figura un piso más abajo —**la inferencia va donde el hardware la soporta**—
y su salida declarada es la misma: servirlo desde donde haya GPU. Lo que **no** es aceptable, y por
eso está en el 3.4 y con test, es que la falta de GPU se resuelva sola cayendo a CPU: sería cambiar
"ordena peor" por "catorce segundos de pantalla muerta", que no es degradar, es romper.

**Y aquí es donde `/estatico` cambia de política de caché, declarado ahora y construido aquí.** Hoy va con `Cache-Control: no-cache` (ADR 0013): cada carga revalida, y contra localhost eso cuesta un 304 sin cuerpo. Con TLS, latencia real y varios alumnos, esa ida y vuelta por fichero deja de ser gratis, y la respuesta correcta es la de siempre en producción: **URL con marca de versión** (`estilo.css?v=<marca>`) servida con `max-age` largo e `immutable`, de forma que el navegador no pregunte nunca y una versión nueva sea una **URL** nueva, que no puede colisionar con la copia guardada. No se hace hoy porque exige decidir de dónde sale la marca —el `mtime` del fichero al arrancar es lo más barato, el hash del contenido lo más correcto— y esa decisión no se toma para ahorrar un 304 en local. Lo que no cambia al cambiarla: el ensayo del 8.4 sigue empezando con recarga forzada.

**Y al lado de esa marca, la tercera vía contra el material viejo, anotada aquí como NO CONSTRUIDA para que sea decisión y no olvido: en vez de eliminar la caducidad, HACERLA VISIBLE.** Una huella de lo que `web/` lleva dentro de la imagen —el hash del directorio en el momento del `build`— expuesta en `/salud` y en la propia muestra de estilos. Entonces "el contenedor está sirviendo lo viejo" deja de ser algo que hay que sospechar y pasa a ser algo que se lee en pantalla, que es la diferencia entre un fallo que se caza en un segundo y uno que se caza cuando ya ha estropeado un ensayo. **Y a diferencia de la caché del navegador, esto SÍ es determinista y SÍ puede llevar puerta:** la huella es un hecho del servidor, no estado guardado en la máquina de quien mira, así que una comprobación de humo contra el contenedor levantado compara la huella que declara con la del `web/` del repo y se pone roja si no cuadran (fuera del CI, que no levanta el contenedor, igual que las otras dos puertas locales). Su sitio es este y no antes porque es la misma familia que la marca de versión —las dos responden a "qué versión de este material estático estoy sirviendo"— y comparten la decisión de dónde sale la marca; construirlas juntas evita elegir dos veces. **Mientras no exista, lo cubre el ritual del 8.4**, que es lo proporcionado a tres días de la sesión.

**Descartado, con su motivo escrito para que nadie lo reabra por comodidad: montar `web/` como volumen en el contenedor.** Eliminaría la fuente en local —editar y recargar, sin `--build`—, y es exactamente el cambio que no se hace: invertiría la regla que este repo ya ha aplicado tres veces (transformers sin anclar, psycopg sin instalar, `sys.path`) de que **lo local se parezca a lo que corre de verdad, nunca al revés**. Cambiaría un modo de fallo conocido, escrito y ritualizado por una divergencia sin explorar, en vísperas de la sesión y en la capa que se enseña.

**8.2 Operación.** Rate limiting por usuario en la API. Backup diario de Postgres (`pg_dump` comprimido al storage de Hetzner) y **una restauración probada en local documentada** (un backup no probado no es un backup). Circuit breaker al proveedor: si Scaleway cae, el sistema lo dice y ofrece glosario y citas literales (que no necesitan modelo); **jamás responde sin verificación en silencio.** Verificación: simular caída del proveedor (URL rota en config) y comprobar la degradación anunciada.

**UN 429 NO ES UNA CAÍDA, Y CONFUNDIRLOS HARÍA QUE EL SISTEMA SE DECLARASE ROTO CUANDO SOLO IBA CON PRISA.** El circuit breaker de arriba existe para caídas: el proveedor no está, y la respuesta correcta es **anunciar y degradar**. Un 429 es lo contrario: el proveedor está perfectamente y nos dice **que volvamos en un momento**. La respuesta correcta es **esperar y reintentar**, en silencio y sin contarle nada al alumno más allá de que aún está pensando. Si el breaker contara los 429 como fallos, una punta de tres alumnos a la vez abriría el circuito y el sistema anunciaría una avería que no existe —y encima dejaría de reintentar, que es justo lo que sí habría resuelto la situación—.

**Regla operativa, con los números medidos el 13 de agosto de 2026:**

| | Qué es | Respuesta | ¿Cuenta para el breaker? |
|---|---|---|---|
| **429** | cuota por minuto agotada | **esperar lo que pida y reintentar** | **NO** |
| 5xx, timeout, corte | el proveedor no responde | anunciar y degradar | sí |

Las cuotas, **leídas de las cabeceras de una respuesta real** y no de la documentación, que publica los nombres pero no los números: `x-ratelimit-limit-requests: 600` y `x-ratelimit-limit-tokens: 2000000` por minuto para `mistral-small-3.2-24b`, con `x-ratelimit-reset-*` diciendo cuándo se reponen. A ~3.500 tokens por consulta eso son **~9,5 consultas/s**, mientras el reordenador ata en **~1,9**: hoy la cuota queda lejos, pero es un techo real y conocido y pasa a ser el siguiente cuello en cuanto entren los lotes.

**Y lo que el cliente hace ya, corregido el mismo día porque reintentaba a ciegas:** honra `Retry-After` cuando llega (en sus dos formatos, segundos y fecha HTTP), y si no llega —Scaleway no lo manda en las respuestas buenas— cae a `x-ratelimit-reset-*` tomando **el mayor de los dos**, porque volver cuando se repone la cuota de peticiones mientras sigue agotada la de tokens es volver a por otro 429. Solo si tampoco hay reset se conjetura con retroceso exponencial. Nunca acelera por debajo del retroceso ya acumulado, y acota en 30 s por si el proveedor manda un disparate. Todo con test, incluida la dirección mutada.

**Dos cosas que NO evitan nada y se dicen para que nadie las proponga en caliente:** cambiar de transporte (HTTP/2, otra librería) no toca el límite, que es de la pasarela **por clave** y no del protocolo; y agrupar las preguntas de varios alumnos en una llamada tampoco, porque `n` no está soportado. Lo que sí existe es la **API de lotes**, sin límite de tasa y un 50 % más barata, cuyo sitio es el arnés de evaluación —trabajo que nadie espera por HTTP— y **no** el camino interactivo.

**8.3 README.** Con números medidos de la tabla, la configuración elegida y sus porqués, los límites declarados (densidad parcial del resto de asignaturas, la fila self-host con el 8B, lo no construido), y los riesgos. **Obligatoria una sección "Escala" que ponga por escrito el argumento completo de la Parte V, en tres bloques:** (1) lo invariante por construcción (latencia, coste y veracidad por consulta independientes del tamaño total: la partición por asignatura, con las dos curvas del 7.5 como evidencia); (2) lo que crece con el corpus, medido y presupuestado (ingesta por giga, almacenamiento por vector, detección de conflictos como trabajo nocturno con vecinos aproximados a gran escala); y (3) los cambios de pieza declarados con su umbral medido (pgvector a dedicado, serverless a pool de vLLM, y el límite del número de particiones con su remedio). Cierra con la extrapolación paramétrica a 2 y 4 TB multi-titulación. La frase de apertura de la sección: la escala no se afirma, se enseña con la curva. Instrucciones de clon limpio: **un tercero llega a la demo local en menos de 10 minutos siguiendo solo el README** (se cronometra de verdad, en una carpeta limpia).

**8.4 Evidencia y ensayo.** Grabación de una ejecución buena de los cuatro momentos de la demo, guardada en el repo. Ensayo del recorrido completo en voz alta (de la consulta a la traza). Práctica de modificación a mano sin asistente: tres cambios cronometrados sobre este código (añadir una validación, arreglar un bug plantado por uno mismo, añadir un caso a un test).

**EL RITUAL DE ARRANQUE, QUE YA SON CUATRO PASOS Y LOS CUATRO SALEN DE FALLOS REALES DE ESTA SEMANA:**

1. **Reconstruir** la imagen y levantar (`docker compose build && up -d --wait`), porque un contenedor de ayer sirve el código de ayer.
2. **Comprobar que el que responde es TU proceso**, mirando `arrancado_en` en `/salud` o en `/api`: si esa hora es anterior a tu último reinicio, hay **otro proceso ocupando el puerto** y estás midiendo código viejo. Este paso lo pagó media tarde del 14 de agosto —un `uvicorn` de horas antes contestaba mientras cada reinicio moría con `[Errno 10048] bind` en un log que nadie leía— y es **el más traicionero de los cuatro porque no falla: contesta**.
3. **Ventana limpia** —incógnito o caché vaciada—, porque la cabecera `no-cache` del 2.4 **no es retroactiva** sobre copias guardadas antes de que existiera.
4. **Y entonces mirar**: las sondas de `/salud` una a una (`embebedor`, `reordenador`, `nli`), que es donde se ve si hoy hay GPU y si la verificación de paráfrasis está viva.

Los tres primeros contestan a la misma pregunta —*¿lo que tengo delante es lo que creo que tengo delante?*— y ninguno de los tres se cae solo: los tres **fallan callando**.

**RITUAL DE ARRANQUE DE LA SESIÓN, que ya son cuatro cosas y se hacen en este orden antes de la primera pregunta:**

1. **`GET /salud` y mirar la sonda `reordenador`** (añadida en el 3.4). Dice cuál de los dos modos está activo: con GPU da el modelo y su revisión; sin GPU dice *"SIN reordenar (respaldo declarado)"*. Cuesta un segundo, y es donde se ve si la GPU responde **hoy**. Si el respaldo está activo, el sistema funciona y ordena peor —y lo anuncia en pantalla—, pero conviene saberlo **antes** y no deducirlo en directo de que las citas salen raras.
2. **TRES CONSULTAS DE CALENTAMIENTO ANTES DE COMPARTIR PANTALLA, mirando el ritmo.** Añadido el 13 de agosto de 2026 con el número que lo motiva: **2 de cada 20 consultas medidas se hundieron a 4-11 tokens/s** tras arrancar bien, o sea que una sesión de ocho preguntas tiene un **57 % de probabilidad** de comerse al menos una. Tres consultas de calentamiento no eliminan el riesgo —es del proveedor, no nuestro— pero sí dicen **en qué estado está el proveedor hoy**, que es lo que decide si conviene apoyarse en el directo o tirar antes de la grabación. Si dos de las tres van lentas, la sesión arranca por la grabación.
3. **Ventana limpia**, no la pestaña que lleva abierta desde ayer: `Cache-Control: no-cache` no libera una copia guardada **antes** de que ese header existiera (ADR 0013).
4. **Comprobar la asignatura seleccionada en pantalla antes de cada pregunta.** Una asignatura equivocada no da error: da recuperación equivocada con aspecto perfectamente plausible.

**Y LA GRABACIÓN CAMBIA DE PAPEL: DEJA DE SER UN POR SI ACASO Y PASA A SER CARGA ESTRUCTURAL.** Estaba escrita como respaldo para el caso de que "la red o el proveedor fallen", que es un escenario improbable y por eso se toleraba tenerla a medias. Con la cola del proveedor medida, el escenario ya no es improbable: **es más probable que no**. Consecuencias operativas, y las tres son obligatorias: la grabación cubre **los cuatro momentos completos** y no un resumen; se graba **antes** de la sesión y no la noche anterior a medias; y **se ensaya el salto a ella**, porque tirar de una grabación en directo sin haberlo hecho nunca es su propio modo de fallo. El vigilante de ritmo del 3.4 corta la congelación en un par de segundos y lo anuncia, así que el peor caso deja de ser un minuto de pantalla parada; pero el peor caso **con el vigilante** sigue siendo una respuesta cortada por plazo delante del cliente, y para eso está la grabación.

**Y una cosa que este encargo ES y que no se ve desde su título: el ensayo es la ÚNICA PUERTA REAL DE LA CAPA DE NAVEGADOR.** La puerta automática no tiene motor de JavaScript, así que los tests de la interfaz del 2.4 **leen los ficheros en vez de ejecutarlos**: comprueban que `literal` y `parafrasis` declaran señales de forma distintas, no que se distingan a un metro de distancia con la pantalla compartida y comprimida. Eso ya se cobró una pieza —el fallo de la paráfrasis del 12 de agosto lo encontró un ojo mirando `/estilos` al 50 %, no el CI—. Así que el ensayo no es practicar la presentación: **es verificar la única capa que ninguna puerta automática de este repo puede tocar**, y por eso incluye mirar la interfaz en las condiciones reales de la sesión (pantalla compartida, ventana estrecha, vídeo comprimido) y no en el monitor de quien la escribió.

**Y una comprobación de un segundo antes de CADA pregunta: mirar qué ASIGNATURA está seleccionada.** Una asignatura mal elegida no da error: da **recuperación equivocada con aspecto plausible**. Se vio el 13 de agosto preguntando por la clave primaria con DWES seleccionada —la recuperación trajo material de seguridad y respondió con aplomo—. En pantalla compartida, con el selector arriba y la respuesta abajo, ese fallo se explica fatal en directo y se evita mirando una línea.

**REGLA DEL ENSAYO Y DE LA SESIÓN: se arranca en VENTANA LIMPIA —incógnito o caché vaciada—, nunca en la pestaña que lleva abierta desde ayer.** No es superstición, y tiene su fallo detrás: el 12 de agosto de 2026 una captura de `/estilos` dictó veredicto sobre una página que ya no existía, porque el navegador servía su copia guardada. Los estáticos se sirven ahora con `Cache-Control: no-cache`, que es el arreglo correcto, **pero no es retroactivo**: una copia que se guardó *antes* de que esa cabecera existiera se guardó sin instrucción de frescura, y el navegador la sigue sirviendo por heurística, sin preguntar. O sea que el arreglo protege de aquí en adelante y no limpia lo que ya está guardado en la máquina desde la que se va a enseñar. En ventana limpia se ve al instante. **Y el caso caro no es la hoja de estilos: es `render.js`**, que dibuja las etapas y las afirmaciones y es justo la capa sin puerta automática —un estilo viejo se ve raro; un `render.js` viejo dibuja otra cosa, o no dibuja nada, delante del cliente.

**El ensayo y la sesión van con la VENTANA ESTRECHA, no con el navegador maximizado.** La columna de contenido de la interfaz mide 900 px, así que en una pantalla ancha ocupa alrededor del 17 %: no es un fallo de la página —esa medida es la que hace legible una línea de texto—, pero compartida a pantalla completa y reescalada por la videollamada, lo que llega al otro lado es contenido diminuto rodeado de vacío. Se comparte la ventana ajustada al ancho del contenido, y eso se ensaya antes, no se descubre en directo.

**EL MATERIAL VIEJO TIENE DOS FUENTES, y el ensayo empieza por la que el ritual no cubría: primero `docker compose up -d --build api`, DESPUÉS ventana limpia, en ese orden.** La segunda fuente es la caché del navegador, que es la de abajo. La primera es el contenedor: `web/` va **copiado dentro de la imagen** (`COPY web ./web` en el `Dockerfile`, y el servicio `api` no lo monta), así que tocar el HTML, el CSS o el `render.js` en el disco no cambia nada de lo que sirve el contenedor hasta reconstruir. Pasó la noche del 12 de agosto de 2026: el HTML no cambió hasta el `--build`. **Y ninguna ventana limpia lo arregla, porque ahí el que sirve lo viejo es el servidor**, y a un navegador impecable se le está dando material caduco con todas las cabeceras correctas. El orden tampoco es adorno: reconstruir después de abrir la ventana limpia deja la ventana limpia mirando lo anterior. **Esto no lo cubre hoy ninguna puerta de la suite:** los tests leen el disco del repo y hablan con la aplicación en proceso, no con la imagen. Es una limitación declarada, no un olvido —y, a diferencia de la caché del navegador, esta sí es cubrible el día que exista la huella de la imagen anotada en el 8.1, porque lo que sirve el contenedor es un hecho determinista y comprobable—.

**Y el ensayo y la sesión arrancan en VENTANA LIMPIA —incógnito o perfil nuevo—, no en la pestaña que lleva abierta desde ayer.** `/estatico` ya manda revalidar (`Cache-Control: no-cache`, ver 2.4), pero ese arreglo **vale de aquí en adelante y no es retroactivo**: una copia guardada ANTES de que la cabecera existiera se guardó sin instrucción de frescura, y el navegador la sigue sirviendo por heurística. Y como no pregunta, tampoco se entera nunca de la regla nueva: la entrada vieja se queda ahí sola. En incógnito la caché empieza vacía, así que la diferencia se ve al instante y sin ritual que recordar. La recarga forzada sigue valiendo para la pestaña que ya se tenía abierta. Grabar la evidencia de una página cacheada es peor que no grabarla, porque queda en el repo con aspecto de prueba.

**Cierre de fase 8:** URL viva, clon limpio cronometrado, grabación en el repo, ensayo hecho.

---

# PARTE V: ESCALABILIDAD A PRODUCCIÓN (la respuesta al "¿esto escala?")

La respuesta es sí, y se recorre componente a componente. Este apartado se aprende para poder decirlo en voz alta.

**El argumento central: el filtro por asignatura es la clave de partición de todo el sistema.** Nunca existe un índice global: cada asignatura tiene su índice vectorial y léxico propios y pequeños. El corpus crece a teras y cada búsqueda sigue tocando una rebanada del mismo tamaño: **el coste por consulta es constante respecto al tamaño total del corpus.** La evidencia es doble: el `EXPLAIN` con poda de particiones guardado en 2.1, y **las dos curvas del encargo 7.5** (latencia plana sobre la asignatura real mientras el corpus total crece x10 y x50 con carga sintética, y el umbral de pgvector medido engordando una sola partición hasta que duele). La escala no se afirma: se enseña con la curva. De regalo, la partición mata la contaminación cruzada, de donde sale media alucinación aparente.

**De dónde salen los teras de verdad, dicho para la sesión:** dos teras de texto de un ciclo no existen (el temario denso de un grado superior, en texto limpio, son megas). Los teras de un cliente educativo son PDF escaneado, vídeo y decenas de titulaciones, y se ENCOGEN en la ingesta: OCR y transcripción convierten teras de binario en los megas útiles por asignatura. Su problema de teras es un problema de ingesta de binarios más este argumento de partición, no de búsqueda sobre teras de texto. La extrapolación a dos teras del README es aritmética sobre números medidos (coste de ingesta por giga, almacenamiento por vector, las curvas), no una promesa. Y el matiz de memoria: la RAM no la dimensiona el corpus total, la dimensiona la partición más grande más los índices calientes.

**Multi-titulación y el caso de 4 TB (el corpus real de un grupo educativo).** A esa escala el corpus no es un ciclo: son muchos grados, cada uno con sus cursos y asignaturas. El árbol gana un nivel (grado, curso, asignatura; en producción, `asignaturas` gana una columna de titulación) y **la clave de partición sigue siendo la asignatura del alumno**, porque el alumno consulta desde una asignatura concreta de su grado y su curso. Consecuencia directa: **para la consulta, 2 TB y 4 TB son indistinguibles**, porque duplicar titulaciones duplica el número de particiones, no el tamaño de la rebanada que toca cada búsqueda. Lo que SÍ escala con los teras, dicho con su aritmética: (1) la ingesta, lineal, presupuestada con el coste por giga medido en 1.5 y 1.11; (2) el almacenamiento, con la cuenta de 4 KB por vector más índices sobre el texto útil, que es una fracción pequeña del binario (un PDF escaneado pesa decenas de veces su texto; el vídeo, cientos: la estimación concreta de megas útiles por giga de binario se declara medida, no supuesta); y (3) el número de particiones, que es el único límite nuevo honesto: miles de particiones con poda van bien en Postgres, decenas de miles empiezan a cargar al planificador, y el remedio está escrito (agrupar particiones por titulación o mover el vectorial a dedicado con las particiones repartidas entre nodos). Ese sobrecoste del planificador es exactamente lo que la curva 1 del encargo 7.5 vigila al inflar el número de asignaturas sintéticas. Y tras el encargo 1.12 este argumento se demuestra sobre estructura VERDADERA: el prototipo ya es multi-titulación real (DAW a densidad completa más DAM y ASIR reales a densidad parcial), y lo sintético solo multiplica lo que existe.

**Cómo escala cada pieza:** la API es sin estado (N réplicas tras balanceador; el estado vive en Postgres y Redis). El trabajo pesado va por colas separadas con workers horizontales por tipo. Postgres escala vertical primero y con réplicas de lectura después; `fragmentos` ya está particionada, así que crecer no exige re-diseño. La caché semántica absorbe la cabeza de la distribución, que en educación es enorme: **el sistema se abarata por alumno a medida que crece.** La inferencia en producción es un pool de vLLM con continuous batching, caché de prefijos y decodificación especulativa por sufijos, dimensionado por consultas por segundo y autoescalado por profundidad de cola; mientras tanto, Scaleway serverless escala solo. La ingesta es nocturna, por lotes e idempotente: procesar teras jamás toca el camino caliente.

**LA INFERENCIA VA DONDE EL HARDWARE LA SOPORTA, Y ESO YA NO ES SOLO EL GENERADOR (13 de agosto de 2026).** El principio 1 convierte al proveedor de generación en un enchufe intercambiable por una URL, y eso está construido: `INFERENCIA_BASE_URL`. **El reordenador es la misma figura un piso más abajo, y el 3.4 la ha hecho visible con números**: el cross-encoder cuesta **554 ms de p95 en GPU y 13.714 ms en CPU** sobre 30 candidatos —factor 25—, así que su sitio no es "el VPS" ni "la GPU" por gusto, es **donde haya el hardware que lo sostiene**. Consecuencia declarada y no disimulada: **el VPS del 8.1 no tiene GPU, así que el despliegue no puede correr el reordenado**, y la divergencia está escrita en el 8.1 y en el README con su tabla de cuatro filas. **Con la distinción que hace honesta la frase: lo IMPOSIBLE allí es solo el reordenado.** El embebedor cabe de sobra —112,9 ms de p50 a 2 hilos, medido, frente a 65.648 del reordenado—, así que la vía vectorial y la fusión son cuestión de **empaquetar torch CPU en la imagen**, que es una decisión pendiente con su coste (~2,5 GB) y no un límite del hardware. Confundir "no cabe" con "no está empaquetado" habría declarado el despliegue en un 58 % de recall cuando su techo real es del 82,7 %. Es el mismo argumento de escala aplicado a un segundo modelo: la pieza se mueve de máquina sin cambiar el contrato, y **lo que nunca se hace es dejar que la falta de hardware se resuelva sola degradando en silencio** —caer a CPU aquí no sería servir peor, sería poner catorce segundos de pantalla muerta delante del alumno, y por eso el respaldo es no reordenar y anunciarlo (ADR 0015)—.

**Órdenes de magnitud:** piloto (una asignatura, cientos de consultas al día): lo del prototipo tal cual. Un grado (miles a decenas de miles): dos réplicas de API tras balanceador, workers x2, Postgres mayor; la inferencia sigue serverless o entra la primera GPU. Institución (cientos de miles): pool de vLLM autoescalado, réplicas de lectura, vectorial dedicado (Qdrant) si se cruza el umbral declarado de pgvector, observabilidad completa (Prometheus y trazas), SLO formal.

**Dos escalas que no son la misma, y conviene no confundirlas en la sesión.** Todo lo anterior es escala de CORPUS: cuánto material hay detrás. La escala de USUARIOS —cuántos alumnos preguntan a la vez— es un eje independiente, y el diseño la responde por otro lado: API sin estado detrás de balanceador, trabajo pesado en colas separadas por tipo, y la caché semántica absorbiendo la cabeza de la distribución. Un corpus diez veces mayor no cambia la latencia de una consulta; cincuenta alumnos simultáneos sí, y por eso **se mide en el encargo 6.4** en vez de afirmarse. La honestidad aquí es la misma que en todo lo demás: la curva de escala de corpus está medida en el 7.5, y la de usuarios en el 6.4; lo que no esté medido se dice que no lo está.

**SLO declarado desde ya:** p95 punta a punta por debajo de 3 s en camino completo y de 300 ms en acierto de caché; disponibilidad 99,5 en piloto. **Ese SLO es hoy una declaración, no una medida:** lo confirma o lo corrige el encargo 6.4 con carga real.

---

# PARTE VI: NORMATIVA (lo justo, dicho como ingeniería)

- **AI Act:** plenamente aplicable desde el 2 de agosto de 2026. La educación entra en el Anexo III cuando el sistema evalúa resultados de aprendizaje o decide acceso: el modo examinar toca esa frontera, y por eso está diseñado y no construido, con esta nota pegada. Deberes de deployer de alto riesgo: logging y supervisión humana. **La traza por respuesta de este diseño ES ese logging: el sistema cumple por construcción.** En la sesión, una frase y se sigue.
- **RGPD:** el corpus es material público **del que se han retirado los datos personales que se encontraron**, y esa frase sustituye a la anterior ("material público sin datos personales"), que resultó ser falsa. Al embeber (encargo 1.5) apareció un fichero con una lista de alumnos, su grupo y sus notas dentro de los apuntes públicos de un estudiante de ASIR, y otro con certificados y una clave privada RSA. Ninguno de los dos llega a fragmento ni, por tanto, a embedding ni a una respuesta: quedan excluidos por ruta y por contenido, declarados en `corpus/COBERTURA.md`, y el troceador avisa de los candidatos que encuentre para que lo decida una persona. La lección va al README tal cual: **un corpus recolectado de repos públicos contiene datos personales aunque nadie los haya puesto a propósito**, y el que dice que no los tiene es que no ha mirado. Las consultas de alumnos SÍ son datos personales (y en un cliente real, de menores en parte): minimización desde el diseño (usuario_id seudónimo, sin nombre ni correo en las trazas), retención de trazas configurable, y la decisión clave ya tomada: proveedor con retención cero y jurisdicción europea, con autoalojamiento como techo. No se afirma "cumplimos RGPD" en el README: se describen los controles y punto.
- **Licencias del corpus:** cada documento con su licencia en el manifiesto; atribución donde la licencia la pida; la normativa es dominio público. El README lo declara.

---

# PARTE VII: MÉTRICAS (definición exacta de cada una)

Cada traza persiste todo lo necesario para calcularlas. El arnés las produce todas por corrida.

**Latencia:** TTFT (petición a primer token visible en SSE), latencia entre tokens (mediana), tokens por segundo, punta a punta en p50, p95 y p99 (jamás solo la media), y desglose por etapa desde `respuestas.etapas`. Referencia del estado del arte: 1,5 a 3 s punta a punta en camino completo; caché por debajo de 100 ms.

**Recuperación:** recall@6 (proporción de pares oro cuyo fragmento correcto está entre los 6 del contexto final), nDCG@5, mejora del reordenador (delta de ambas con y sin él), contaminación cruzada (proporción de respuestas con algún fragmento de otra asignatura en el contexto; entre titulaciones: fragmento de una asignatura no mapeada por la puente a la titulación del alumno).

**Veracidad:** tasa de afirmaciones sin respaldo (afirmaciones `parafrasis` o `literal` con veredicto fallido que habrían salido sin la capa: se mide en la ablación), conformidad con premisa falsa (proporción de `premisas_falsas.jsonl` donde el sistema NO corrige), abstención correcta (proporción de `fuera_de_temario.jsonl` donde se abstiene, y su recíproco: abstenciones indebidas sobre `normales.jsonl`), fidelidad literal (100 por construcción, demostrada por el test anclado de 4.2), precisión de citación (muestreo a ojo de 30 afirmaciones verificadas: el fragmento citado sostiene de verdad la frase; el número de acuerdo se anota).

**Pedagogía:** fuga de solución (proporción de `fuga_de_solucion.jsonl`, el conjunto congelado del 5.0, donde el modo acompañar entrega la solución), regresionada en cada cambio. Y dos más que vienen del contrato de andamiaje (sección 7): **contenido factual colado como andamiaje** (proporción de frases marcadas `andamiaje` que en realidad afirman algo del temario; se mide sobre `normales.jsonl` y `premisas_falsas.jsonl`, y su detector se valida en las dos direcciones) y **proporción de andamiaje en la respuesta**, que se anota sin umbral: sirve para ver si el sistema derivó a recitar fichas o a hablar mucho y decir poco, y esa lectura la hace una persona.

**Operación:** acierto de caché, tasa de escalado, tasa de reintento del verificador, tasa de abstención global, coste por consulta y por mil (desglosado por etapa), coste de ingesta por giga con su extrapolación a un tera.

**OCR (solo si se ejecuta 1.11):** CER y WER del OCR contra el texto original, y delta de recall@6 y de tasa de afirmaciones sin respaldo en fragmentos de `origen: ocr` frente a sus originales de texto.

---

# PARTE VIII: ENTRENAMIENTO EN LA 5080 (opcional, SOLO tras cerrar la fase 7)

Regla ya decidida y con su porqué en la conversación de diseño: **el conocimiento no se entrena jamás** (un modelo con el temario en los pesos no puede citarlo, pierde la trazabilidad, empeora la seguridad aparente y obliga a reentrenar con cada cambio). **La fontanería sí se puede entrenar**, con mejora medida o no se adopta.

**VIII.1 Fine-tune del reordenador (el candidato con mejor palanca).** Procedimiento: (1) minería de negativos duros: para cada par oro, los fragmentos que la fusión puntúa alto y NO son el correcto; (2) dataset de triples (consulta, positivo, negativos) desde los pares oro y las trazas reales; (3) entrenar el cross-encoder BGE v2-m3 con sentence-transformers en la 5080 (cabe de sobra: es un modelo de cientos de millones de parámetros), pocas épocas, con partición de validación separada ANTES de entrenar; (4) evaluar nDCG@5 y recall@6 antes y después sobre la partición de validación, jamás sobre la de entrenamiento. **Criterio de adopción: mejora en nDCG@5 en validación, con la comparación en `corridas_eval` y ADR; si no mejora, se declara el experimento con su resultado negativo, que también es evidencia.**

**VIII.2 Verificador destilado (declarado, normalmente no construido).** Destilar veredictos del modelo grande a un NLI pequeño ajustado al dominio. Mismo protocolo: partición de validación, adopción solo con mejora medida en conformidad con premisa falsa y podas indebidas. Se documenta como camino de optimización de coste en producción.

Nota de honestidad para la sesión: si VIII.1 se hace, se cuenta como lo que es (ajuste de la fontanería de recuperación con protocolo de validación), no como "he entrenado un modelo" a secas.

---

# PARTE IX: DEMO, CONTINGENCIAS Y RIESGOS

## El guion de la demo

Cuatro momentos en vivo, en este orden, y después la ablación:
1. **Premisa falsa:** el alumno afirma algo incorrecto con seguridad; el sistema corrige citando el temario.
2. **Fuera de temario:** el sistema dice que no está, en vez de inventar.
3. **Conflicto plantado:** el sistema avisa del conflicto en vez de elegir a cara o cruz.
   **Dos versiones de este momento, y la decisión NO se toma en caliente** (ver abajo).
4. **Ejercicio desde el resultado:** derivación que aterriza en el resultado dado, con los tipos visualmente separados; y un caso con el resultado mal donde el sistema lo dice.

**EL MOMENTO 4 VA A SER EL MÁS LENTO DE LA SESIÓN, y eso se guioniza en vez de descubrirse en directo.** Es el único que corre en modo `corregir`, y `corregir` encadena pasos: medido el 13 de agosto por el camino real, seis consultas de ese modo dan **3,0 afirmaciones de media (máximo 5)** y **386 tokens de salida de media, máximo 615**, frente a las 1-3 afirmaciones de una consulta de `responder`. De punta a punta salieron entre **2,3 y 4,9 segundos**, o sea que el peor caso roza el presupuesto de 5 s **sin haberse pasado**. Consecuencias para el guion: es el momento donde **no** se habla mientras carga —hay que dejar que la pantalla trabaje, que además es cuando los veredictos van saliendo uno a uno y eso es precisamente lo que hay que enseñar—, y es el primero que conviene tener grabado si el ensayo del 8.4 encuentra la cola del proveedor cargada.

### El momento 3 tiene dos versiones, y la buena depende de una pieza que puede no estar

**El momento 3 no puede depender de algo sin construir.** Medido en el 1.8: el detector de
conflictos **no encuentra el par contradictorio real del corpus** —las dos definiciones
incompatibles de MVC tienen similitud 0,564, porque cada una va enterrada en un trozo de 512 tokens
lleno de otra cosa—. Para verlas hay que comparar **definiciones del mismo término**, y eso lo
produce el glosario, que es el encargo 2.6 y a día de hoy no existe. Así que:

| | Con qué se enseña | Qué se dice en voz alta |
|---|---|---|
| **Versión A (preferida)** | El par **REAL**: la Vista de MVC definida como "parte del modelo" en el DWES de ~2012 frente a la definición vigente del DWES de 2025-26, encontradas por el glosario del 2.6 | "Esto no lo hemos plantado: son dos materiales reales del mismo módulo, con ocho años entre ellos" |
| **Versión B (respaldo)** | La contradicción **SINTÉTICA** plantada en el 1.7: el paso de parámetros en Java —"los objetos se pasan por referencia" del temario frente a "en Java no existe el paso por referencia" de la hoja de repaso—, que el detector del 1.8 **sí** caza con NLI a 0,99 señalando las dos frases que chocan | "Esta contradicción la hemos plantado nosotros y está declarada como plantada en el manifiesto; sirve para enseñar el mecanismo, no para presumir del corpus" |

## DECIDIDO EL 12 DE AGOSTO DE 2026, CON EL 2.6 CERRADO: **VA LA VERSIÓN B**

El glosario se ejecutó sobre el 0613 **tres veces**, como estaba pactado, y **el par de MVC no salió
ninguna de las tres**. No hubo que deliberar porque la regla estaba escrita antes de mirar.

**Y el diagnóstico es preciso, que importa más que el veredicto: el fallo no está en el glosario.**
De los 260 fragmentos del 0613 que mencionan MVC, **solo 16 llevan `frase_definitoria`**, y ninguno
de esos 16 define la Vista. O sea que las dos definiciones incompatibles **nunca llegaron a ser
candidatas**: se pierden en la detección de frase definitoria del 1.4, un encargo antes de aquí. La
extracción y la validación literal funcionaron —88 de 124 candidatos, con un 29 % de descarte
estable en las tres corridas—; lo que no había era de dónde extraerlas. Arreglarlo es trabajo del
1.4, con el corpus abierto, y **no cabe en cinco días**.

Así que la B, **sin dramatizar y sin disimular**, y con una ventaja que conviene decir en voz alta:
la A habría necesitado explicar por qué el sistema encontró ese par y el detector del 1.8 no; la B
enseña el mecanismo con un caso donde el NLI da 0,99 y señala las dos frases que chocan.

**Regla vieja, conservada porque explica la decisión:** al cerrar el 2.6, si el glosario producía las
dos definiciones de MVC y su validación independiente las daba por buenas, iba la A. Si no, la B: la B es un momento honesto y además luce una propiedad que la A no tiene —en el par
sintético **el material plantado es el técnicamente correcto y el temario oficial es el que va
suelto**, así que demuestra de paso por qué el sistema no dictamina quién tiene razón y se limita a
enseñar las dos versiones ordenadas por vigencia—.

**Lo que no vale:** llegar al lunes con la A a medias. Si el 2.6 no está cerrado el domingo, se
ensaya la B y se acabó.

### Lo que se dice en voz alta al llegar al momento 3, y no es una nota técnica

**"Buscamos contradicciones reales entre definiciones del mismo término. Encontramos doce
divergencias y cero contradicciones, así que la que os enseñamos está plantada, y lo decimos."**

Esa frase va dicha, no insinuada, y es más fuerte que dejar que parezca que el conflicto se encontró
solo. Lo que hay detrás está medido: el glosario del 2.6 encuentra **12 términos definidos más de
una vez con palabras distintas y en documentos distintos** (49 en crudo, antes de descontar el
artefacto del solape de 64 tokens), y al mirarlos **ninguno se contradice**: son paráfrasis del
mismo concepto. Encontrar divergencia es un `GROUP BY`; que dos definiciones se contradigan es un
juicio, y lo hace el NLI de la fase 4.

Es además coherente con cómo este proyecto trata ya el material plantado —declarado como plantado
en el manifiesto y declarado como plantado delante del cliente—. Un sistema que enseña una
contradicción sin decir que la puso él está haciendo, en pequeño, exactamente lo que dice combatir.

**Ablación en directo:** los mismos casos con la verificación apagada. Se cae. Después, la tabla: no es anécdota, está medido sobre los conjuntos enteros. Primero el efecto, después el rigor.

**Respaldo:** la grabación de 8.4. Si la red o el proveedor fallan en la videollamada, se tira de ella y la evidencia sigue en el repo.

## Contingencias (decididas ahora para no decidir en caliente)

| Escenario | Acción |
|---|---|
| Scaleway caído o lento en la sesión | Cambiar `INFERENCIA_BASE_URL` al vLLM local (configuración d): mismo contrato, y de paso demuestra el enchufe. Si tampoco, grabación |
| El structured output del proveedor rompe el contrato a menudo | Un reintento con recordatorio de esquema; si la tasa supera el 5%, validador tolerante que rescata el JSON del texto, con la tasa anotada |
| ~~p95 del reordenador no cabe en el VPS~~ **OCURRIÓ el 13 de agosto de 2026, y con margen** | **Medido: 13.714 ms de p95 en CPU contra 554 ms en GPU, factor 25.** Salida tomada: **GPU**, con la divergencia declarada en el 8.1, en el README y en la Parte V. La salida "aceptar el p95 y declararlo" queda **tachada por el número**: se escribió imaginando 400-900 ms y el reordenado va en la ruta del TTFT, así que serían catorce segundos de pantalla muerta. Y **bajar candidatos, NUNCA**: esta fila decía "12 candidatos", que además de destruir el techo **tampoco cabía** (5.295 ms de p95, 105 % del presupuesto) |
| **La consulta no cabe en el objetivo de 5 s** (ocurre: 25 % el 14/08/2026) | **La latencia está en la GENERACIÓN, no en la recuperación**, así que las palancas son (a) **acortar la respuesta** —menos afirmaciones o prosa más corta, que se impone con `maxItems` y con el prompt— y (b) **el modelo**. **NUNCA recortar el contexto**: de ahí sale la calidad, y ahorraría prefill (292 ms) para pagarlo en recall. El plazo operativo está en 8 s para que el fallo sea "tarda 6" y no "se corta a los 5" |
| **La GPU no responde en tiempo de ejecución** | **NO se cae al reordenado por CPU.** Se salta el reordenado, se sirve el orden de la fusión y `/consulta` **lo dice en una etapa** (`sin_reordenar`), que es el patrón del circuit breaker del 8.2: degradar anunciando, jamás en silencio. Con test anclado y visto en rojo mutando la etapa. Se comprueba antes de la sesión con la sonda `reordenador` de `/salud` (ritual del 8.4). **Desde el 14/08/2026 aplica solo con el reordenador reencendido (`REORDENADOR_ACTIVO=1`, ablación): por defecto está descartado por su criterio (ADR 0019) y el orden de la fusión ES la configuración, no la degradación** |
| recall@6 flojo (por debajo de 0,8) sobre los pares oro | No tocar la generación: es problema de corpus o troceado; revisar 1.3 y 1.4 antes de seguir (la calidad de contexto manda sobre la cantidad) |
| El modelo pequeño falla mucho el contrato o el contenido | Subir la tasa de escalado por configuración y medir el coste; la tabla decide, no la frustración |
| Conformidad con premisa falsa alta pese al NLI | Añadir al prompt la instrucción de extraer y comprobar la premisa ANTES de responder, y re-medir; si persiste, escalar esas consultas al grande por defecto |
| El coste por mil se dispara | Mirar el desglose por etapa: normalmente es contexto demasiado largo (bajar top 6 a top 4 y re-medir recall) o caché fría (revisar umbral) |
| CUDA o WSL2 dan guerra con la 5080 | La ingesta puede correr en CPU (más lenta, medida); la fila self-host puede caer de la tabla con su motivo declarado: nada del camino principal depende de la GPU local |
| El corpus de una unidad queda flojo | Reducir alcance declarado (una asignatura completa en vez de dos) antes que diluir densidad: profundidad gana a superficie |
| El reordenador del 3.4 cae, se recorta o no cabe en latencia | **SUPERADO EL 14/08/2026: el reordenador quedó DESCARTADO por su propio criterio, así que esta fila ya no describe un respaldo sino la configuración por defecto.** La regla vieja —*el respaldo es el vectorial solo (73,0 %), nunca la fusión sin reordenar (56,0 % a `recall@5`)*— salía de la fusión a **pesos 1:1** sobre el conjunto viejo; con los pesos 10:1 que el 3.3 decidió (y que no estaban cableados) y el conjunto corregido, la fusión sin reordenar **empata con el vectorial solo** a `recall@6` en `lectura` (58,7 % las dos) y aporta la cobertura del pool. La configuración por defecto es **fusión 10:1 en top 6**; la corrección se declara y el número viejo se conserva al lado (ADR 0019) |
| **El calendario no llega a la sesión del lunes** | **Se recorta por la escalera de abajo, en ese orden y no en otro.** Todas las demás filas de esta tabla son escenarios técnicos; el riesgo real de esta semana es el reloj, y decidir el domingo en caliente qué se cae es cómo se acaba tirando lo que sostiene el argumento |

### La escalera del calendario, decidida el 12 de agosto y no el domingo

Se recorta **en este orden**, y cada peldaño se declara como diseñado y no construido, con lo que falta escrito:

1. **Cae el sandbox de ejecución de código del 4.4** y queda solo la aritmética con sympy. El momento 4 de la demo se cubre igual, porque el ejercicio desde el resultado **es aritmético**. El sandbox queda diseñado y no construido.
2. **Cae la calibración del 4.6** y se sale con el umbral NLI inicial de **0,80**, declarado como no calibrado y con el barrido pendiente escrito. Un umbral declarado sin calibrar es honesto; un umbral calibrado a ojo la noche antes, no.
3. **Cae la tabla completa de la fase 7** y queda **la ablación en vivo con lo medido**, que es lo que sostiene el argumento delante del cliente: la fila con verificación contra la fila sin ella, leída con la regla del 7.3 (diferencia menor que la dispersión = «no distinguible»).

**Lo que NO cae bajo ningún concepto: la fase 3 entera y los dos primeros verificadores, el literal y el NLI.** Sin recuperación no hay demo —el sistema no tendría de dónde citar y todas las afirmaciones serían `conocimiento`, que es exactamente lo que este proyecto dice no ser—, y sin esos dos verificadores no hay proyecto: son **el principio 6 hecho código**, uno sin modelo y el otro con un modelo distinto del generador. Recortar ahí no sería llegar con menos, sería llegar con otra cosa.

## Riesgos declarados

1. **Scaleway no tiene caché de prompts del proveedor:** el prompt se paga entero por llamada. Mitigado por la caché semántica delante y el contexto corto por diseño; en self-host lo cubre la caché de prefijos de vLLM. Declarado.
2. **Reordenador en CPU:** latencia a medir, plan B escrito.
3. **Modelo abierto pequeño contra frontier:** falla más; es una columna de la tabla, no un miedo.
4. **Deriva de alcance:** la tentación de construir examinar, OCR o "la plataforma" antes de cerrar las fases. La regla es el orden; lo declarado espera.
5. **El corpus es el cuello real:** si la fase 1 queda floja, todo lo posterior mide ruido. Por eso va primero y con criterio de cierre propio.

## Construido contra declarado

**Aviso de lectura: esta sección es el TEXTO QUE SE PUBLICARÁ AL CIERRE, no el estado de hoy.** Se escribió por adelantado para fijar qué se promete y qué no, que es justo su utilidad; pero leída como estado afirma en presente lo no construido, y esa es la primera regla del Apéndice A. **El estado vivo del repo está en `README.md` y en `corpus/COBERTURA.md`, y manda sobre esto.** Al cerrar la fase 8, se comprueba línea a línea y se publica.

**Construido y medido (al cierre):** fases 0 a 8 completas. Hoy, 13 de agosto de 2026: fases 0, 1 y 2 cerradas en `main` y la 3 abierta en `fase-3` (el estado fino, en el README).

**Y UNA DIVERGENCIA QUE VA EN ESTA SECCIÓN DESDE YA, porque al cierre habrá que publicarla y no se descubre el último día:** lo que se **enseña** en la sesión corre en una máquina con GPU; lo que se **despliega** en el VPS del 8.1 no la tiene, y su imagen tampoco lleva torch. Así que al cierre esta sección tendrá que decir, con estas palabras o mejores, que **el despliegue sirve léxica y glosario y la tubería completa —vectorial, fusión y reordenado— necesita GPU**, con la tabla de cuatro filas del 8.1 al lado. No es un pendiente: es el principio 1 funcionando (la pieza se mueve de máquina sin cambiar el contrato) y el principio 2 obligando a decirlo. **Diseñado y declarado como no construido, con interfaz definida:** modo examinar (con su nota del AI Act), OCR de foto de ejercicio (con un modelo multimodal del mismo catálogo es la extensión más barata; solo si todo lo anterior está cerrado), correlación entre asignaturas, gestión multi-tenant completa, VIII.2, y la ingesta de binarios a escala (OCR de PDF escaneado y transcripción de vídeo: exactamente donde los teras reales de un cliente se convierten en los megas útiles por asignatura; se declara con su sitio en la tubería de ingesta).

---

# APÉNDICE A: CLAUDE.md (copiar al repo tal cual)

```markdown
# Reglas de trabajo de este repo

- La fuente de verdad es guia-definitiva.md. Se trabaja por encargos numerados, en orden.
- Antes de picar: plan de 10 líneas o menos y OK explícito del owner. Sin OK no hay código.
- Una fase, una rama. Merge a main solo con la suite en verde y el criterio de cierre de la fase cumplido.
- El criterio de cierre de un encargo se lee LITERAL y se comprueba cláusula a cláusula antes de declarar el cierre. Ya se ha incumplido dos veces (el cierre de la fase 1 y el "DDL de la sección 9" del 2.1, que entregó 7 de 11 tablas), y las dos se habrían cazado en un minuto poniendo la frase del cierre al lado de lo entregado. Lo que no se lee cláusula a cláusula, se lee como uno recuerda haberlo escrito.
- Cerrar una fase incluye ACTUALIZAR LA TABLA DE ESTADO DEL README en el mismo commit del merge. Va dos veces congelado tras un merge, y el patrón es siempre el mismo: el trabajo se declara en COBERTURA y en la guía, y el README —que es lo primero que lee quien llega— se queda contando la fase anterior. Un documento de estado desactualizado no es un despiste de forma: afirma en presente un estado que ya no existe, que es la primera regla de esta lista.
- Verificación mínima en cada commit: ruff check (con F821 y F401) y los tests del área tocada.
- Al cierre de cada fase: pasada adversarial buscando dónde miente el verde; hallazgos arreglados o anotados como deuda con motivo.
- Toda sonda o métrica nueva se valida contra un caso donde debe fallar antes de creerse su verde, y deja test de regresión anclado.
- Toda prueba de mutación confirma que la mutación se aplicó de verdad, enseñando el diff, ANTES de leer el resultado. Un test que pasa sobre código sin mutar no ha probado nada: es la misma trampa del verde mentiroso, esta vez en la herramienta de comprobar.
- El que comprueba no comparte el supuesto del que produce (principio 6 de la guía): un detector que reutiliza el patrón, el modelo o la suposición de lo que audita es ciego justo al fallo que persigue. Se valida en las dos direcciones, sano y mutado.
- En local se corre `pytest`, NO `python -m pytest`: el segundo mete el directorio actual en sys.path y el CI no lo hace, así que la puerta y la máquina de quien la escribe estarían ejecutando cosas distintas. Van tres veces (transformers sin anclar, psycopg sin instalar, sys.path) y las tres se arreglan igual: que lo local se parezca al CI, nunca al revés.
- El intérprete local es el de **miniconda**, que es el que CLAUDE.md declara y el único con torch y CUDA —que el NLI del 4.3 va a necesitar de verdad—. Comprobación de cinco segundos antes de fiarse de cualquier verde: `python -c "import sys; print(sys.executable)"` tiene que decir `...\miniconda3\python.exe`, no `C:\Python313`. Van TRES veces que el instrumento no es el que el documento dice (transformers sin anclar, psycopg sin instalar, intérprete), y la salida es siempre la misma: **lo real se alinea con lo declarado, nunca al revés**, y queda una comprobación barata que lo detecta la próxima vez.
- Los códigos de salida se leen SIN tubería. `cmd | tail; echo $?` devuelve el código del último comando de la tubería, no el del programa que importa: para leer el de un programa se corre solo, o se guarda antes de tubear. Misma familia que la mutación que no se aplica: el instrumento mintiendo, no lo medido.
- **"EL INSTRUMENTO MIENTE" YA VA POR SIETE, así que se busca a propósito en vez de esperar a tropezarla.** Las siete, con su forma: (1) **transformers sin anclar** —la versión que corre no es la que el documento dice—; (2) **`python -m pytest`** —mete el directorio actual en `sys.path` y el CI no, o sea que la puerta y la máquina de quien la escribe ejecutan cosas distintas—; (3) **el intérprete** —`C:\Python313` en vez del miniconda declarado, sin torch—; (4) **`git diff` sobre un fichero NO RASTREADO devuelve VACÍO**, que en el ritual de la mutación se lee exactamente igual que "la mutación no se aplicó": no falla, calla (se arregla con `git add -N` antes de diffear); (5) **el código de salida leído tras una tubería**, que es el de la tubería y no el del programa —cayó otra vez el 14/08 con `gh run watch | tail`, el mismo día de la séptima—; (6) **el "arriba" que no era el mío** —un proceso viejo ocupando el puerto contesta `/salud` y todas las medidas las sirve código anterior al arreglo—; y (7) **`git merge -F -`**, que NO lee de stdin: el merge no ocurre, el error es una sola línea que nada obliga a leer, y las puertas siguientes corren en verde **sobre la rama sin fusionar** — lo que salvó no fue el verde, fue leer la línea de error. **El patrón común y lo que hay que preguntarse: el aparato de medir no está midiendo lo que su nombre dice.** La comprobación siempre es la misma familia y siempre es barata: hacer que el instrumento enseñe QUÉ está mirando —la ruta, la versión, el diff, el código de salida— antes de creerse lo que dice, y muy en particular antes de creerse un VACÍO o un verde.
- Toda decisión de diseño: ADR corto en docs/adr/ (contexto, decisión, trade-off).
- Ningún documento del repo afirma en presente lo no construido.
- Secretos jamás en el repo: variables de entorno, .env.example sin valores.
- Los umbrales de configuración marcados como iniciales se calibran donde la guía lo indica y el barrido se persiste en corridas_eval.
- Commits pequeños con el porqué en el mensaje. Nada de "arreglos varios".
- Ocurrencias y hallazgos se cuentan por separado en cualquier número que alimente una decisión.
- **POR QUÉ AQUÍ SE MIRAN LAS COSAS A OJO, con el caso que mejor lo explica.** El humo del 4.3 dio **6 de 10** con el detector de código heredado. Leído como agregado, eso dice *"el modelo va regular"* — una frase con la que se puede seguir trabajando, subir un umbral y pasar página. Leído por casos, **3 de los 4 fallos estaban en los pares que llevan identificadores**: 1 de 4 con identificadores frente a 5 de 6 sin ellos. Y entonces la frase deja de ser *"el modelo va regular"* y pasa a ser **"nuestro filtro descarta la prosa de este temario"**, que es otro problema, en otro sitio, con otro arreglo. **Un agregado no miente: promedia, y al promediar disuelve exactamente la estructura que señala la causa.** Por eso: antes de creerse una tasa, mirar unos cuantos casos concretos con los ojos, y en particular los que fallan.
- **Reutiliza el MECANISMO, re-deriva los PARÁMETROS.** Costó dos veces el mismo día, el 13 de agosto de 2026, y las dos al llevar la maquinaria del 1.8 al verificador NLI del 4.3: su tope de **12 frases** era correcto para comparar fragmento contra fragmento —O(n²), sin tope se dispara— y aquí, con la comparación vuelta O(n), lo único que hacía era **tirar la cola del fragmento** (la frase de apoyo estaba en la posición 42 de 43); y su detector de código cazaba `@\w+`, correcto para descartar bloques y desastroso para juzgar **prosa que MENCIONA identificadores**, que en este corpus es casi toda —4 fallos de 10 contra 1 de 10 del detector nuevo—. **El código validado se reutiliza; sus constantes se vuelven a derivar contra el problema nuevo**, porque un parámetro es una respuesta a una pregunta y la pregunta ha cambiado. Y ninguno de los dos se pone rojo al mudarse: siguen devolviendo números.
- **Una constante compartida NO se "mejora" de paso.** Al mover `frases_de` y `palabras_de` a un módulo común, la primera versión traía una lista de palabras vacías ampliada con lo que parecía sentido común. Eso habría cambiado **en silencio** el comportamiento de `detectar_conflictos.py`, que está **validado por su test** y cuyos conflictos se midieron con la lista vieja: el test habría seguido verde y los números publicados habrían dejado de corresponder al código. **Compartir una implementación es compartirla entera, incluidos sus datos.** Si de verdad hay que mejorarla, se mejora en un commit propio, con su motivo, y se re-mide lo que dependía de ella.
- **Si el registro lo escribe el camino de ÉXITO, los fallos son invisibles, y toda métrica calculada sobre esa tabla queda sesgada hacia lo que salió bien.** Encontrado el 13 de agosto de 2026 y de rebote: una respuesta que no valida el contrato **no mete ni una fila en `afirmaciones`** —no hay afirmaciones validadas que meter— y su motivo moría en el evento SSE. La tabla contenía solo lo que funcionó, así que la tasa de poda, la de abstención y el reparto de veredictos de la fase 4 se habrían calculado **sobre el subconjunto que salió bien**, sin que nada se pusiera rojo. Es el principio 11 cometido dentro de nuestra propia base de datos: una muestra elegida por el síntoma, que aquí es el **éxito**. **La regla: se persiste ANTES de que pueda fallar, o se persiste el crudo con su motivo de fallo.** Y al definir cualquier métrica, se escribe **de qué denominador sale** y se comprueba que ese denominador incluye los fallos.
- **Un detector que se alimenta del flujo que vigila es ciego al flujo AUSENTE, y la red de ese caso siempre está fuera.** El vigilante de ritmo del 3.4 cuenta tokens y el plazo de la consulta mira el reloj, pero los dos viven **dentro del bucle que consume trozos**: un flujo parado del todo no dispara ninguno, porque sin trozos no hay nada que contar ni ningún sitio donde mirar la hora. Lo único que cortaba ahí era el `timeout_lectura` del cliente, y estaba en 60 s. **Búscalo en cada sitio donde algo nuestro consume de algo ajeno** —el proveedor, la base, la cola, la GPU, la carga de un modelo— y comprueba que el caso "no llega nada" tiene su corte **fuera** del consumidor. El barrido del 13 de agosto de 2026 sacó **ocho conexiones a Postgres en la ruta de petición sin plazo** (tres en `recuperacion.py`, tres en `catalogo.py`, dos en `traza.py`); van por `app/core/conexion.py`, con `connect_timeout` **y** `statement_timeout`, porque el primero acota abrir y el segundo acota la consulta ya abierta: poner solo uno es la protección que se ve y no está.
- **Un umbral expresado en la unidad que el fallo infla se relaja justo cuando debería apretar.** El vigilante de ritmo del 3.4 tenía su gracia en **24 tokens**: como el fallo que persigue es que lleguen **pocos tokens por segundo**, esa gracia valía 0,2 s en una consulta sana y **6 s en la peor**, o sea que el guardia se echaba a dormir en proporción a la gravedad. La forma general: **si el tope se cuenta en la misma magnitud que la avería degrada, el tope se estira solo.** Se busca a propósito en cualquier límite nuestro contado en **tokens, elementos o intentos cuando lo que falla es el TIEMPO** —y al revés—. La comprobación es de una línea: *¿cuánto vale este tope en el peor caso que existe para cazar?* Si la respuesta es "más que el presupuesto", está expresado en la unidad equivocada.
- **UN CONTADOR RESPONDE A LA PREGUNTA CON LA QUE SE ESCRIBIÓ, NO A LA QUE SE LE HACE DESPUÉS.** *"¿Dejó pasar frases el portero?"* y *"¿vio algo el alumno?"* no son la misma pregunta, y `emitidas` respondía la primera creyendo responder la segunda: una frase de menos de tres palabras de contenido pasa **por diseño** —podar *"Vale."* sería el falso negativo por construcción—, así que **un punto suelto dejaba el contador en 1 con la pantalla vacía**. La comprobación, y es de diez segundos: **decir en voz alta qué pregunta contesta el contador y comparar esa frase con la que se le está haciendo**. Si no son la misma, hace falta otro contador, no otra lectura del mismo — aquí, `caracteres_emitidos`. Es la familia del umbral en la unidad equivocada, pero al revés: allí el número era correcto y la unidad no; aquí la unidad es correcta y **la pregunta es otra**.
- **"ARRIBA" NO SIGNIFICA "ARRIBA EL MÍO": una espera de arranque que solo comprueba que ALGO contesta no comprueba nada.** Costó media tarde el 14 de agosto de 2026. El bucle de espera preguntaba por `/salud` hasta que respondiera, y respondía — **un proceso viejo que llevaba horas ocupando el puerto**. Cada "reinicio" moría con `[Errno 10048] error while attempting to bind`, esa línea se iba a un fichero de log que nadie leía, y **todas las medidas siguientes las sirvió código anterior a los arreglos que se estaban midiendo**. El síntoma es el peor posible: el arreglo **funcionaba**, su test unitario pasaba, y el camino real seguía roto — o sea, la combinación exacta que hace dudar del arreglo en vez de del instrumento. **Se arregla haciendo que el proceso ENSEÑE que es el suyo**: puerto nuevo en cada arranque para que un residuo no pueda taparlo, y comprobar el arranque **por el log del proceso propio** (`grep -c "ERROR.*bind"`), no por si el puerto contesta. Es la misma familia que la mutación que no se aplica y que el `git diff` vacío: **el aparato de medir no está midiendo lo que su nombre dice**, y aquí "el servidor está listo" quería decir "hay un servidor".
- **UNA ETIQUETA DESCRIBE CÓMO SE CLASIFICÓ ALGO, NO LO QUE CONTIENE.** `tipo_contenido: enunciado_ejercicio` lo asignaron **reglas** en el 1.4 y significa *"esto parecía un enunciado"*, no *"esto tiene un resultado comprobable"*. Y hay un número que lo cierra: la **precisión declarada de `tipo_contenido` fuera de `definicion` es 13 de 20**, así que **cualquier plan construido sobre esas etiquetas hereda esa tasa de error sin declararla**. El 5.0 la heredó entera: daba por hecho que sus 20 casos de `corregir_desde_resultado` saldrían de los 223 fragmentos `enunciado_ejercicio` —*"ejercicios reales con su resultado"*— y al mirarlos a ojo son **tareas de configuración y de programación**: *instala un proxy squid*, *implementa la clase Inventario*. **Cuatro de 223** dan un ejercicio con resultado comprobable. Barrido del 14 de agosto de 2026 sobre la guía: **dos** planes razonaban desde la etiqueta en vez de desde el texto —el 5.0 y la fuente de las preguntas del 3.0—, **uno ya se había corregido solo** (el glosario dejó de usar `tipo_contenido = definicion` y pasó a la `frase_definitoria`, que es el mismo aprendizaje llegado antes) y **uno espera a una capacidad no construida** (`codigo` alimentando el sandbox del 4.4). **La comprobación es leer veinte y contarlos**, y cuesta cinco minutos; escribir el plan encima de la etiqueta cuesta un encargo. **Y VA POR DOS, con la segunda cometida sobre una etiqueta escrita el mismo día por quien conocía la regla:** la traza del 2.5 agrupaba como *"fila anterior al 14/08"* toda afirmación sin firma de instrumento, y la primera consulta real —escrita **hacía un minuto**— salió entera bajo esa etiqueta, porque sus cuatro afirmaciones eran `conocimiento`, que **no verifica nadie POR DISEÑO**. La etiqueta afirmaba una CAUSA —la edad— que nunca se había comprobado, cuando lo único observado era la ausencia de firma. **Las dos razones de estar ausente no se pueden juntar**: una es correcta y permanente, la otra una deuda de datos que se agota sola. Y hay una segunda lección en cómo apareció: **lo cazó una consulta real y no la suite**, porque los tests usaban afirmaciones de los tres tipos verificables y ninguno pasaba por ese camino — la cobertura no dice nada sobre si lo cubierto es lo que decide.
- **UNA HERRAMIENTA ESCRITA PARA MIRAR LA CONFIGURACIÓN TIENE QUE TAPARSE LOS OJOS ANTES DE MIRAR, y esta es la lección más incómoda del repo porque la violó el propio auditor.** `scripts/comparar_configuracion.py` se escribió para comprobar la higiene del entorno —qué variable dice una cosa en el código y otra en el contenedor— y en su **primera corrida imprimió `INFERENCIA_API_KEY` entera por pantalla**, que es la regla que este repo tiene desde el día uno. Y es peor que un descuido cualquiera por dónde ocurre: una herramienta de auditoría **se corre a menudo, su salida se pega en informes y se guarda en logs**, así que el secreto no se escapa una vez, se escapa cada vez. La clave se rotó. **La forma general: todo lo que enumere entorno, cabeceras, configuración o trazas empieza por la lista de lo que NO imprime** —`KEY`, `PASSWORD`, `SECRET`, `TOKEN`, `CLAVE`— y compara con el valor real mientras enseña `(oculto)`. Se puede decir *si* difiere sin decir *cuánto* vale.
- **Un valor por defecto que el entorno puede pisar NO es un valor por defecto: es una sugerencia, y el que corre es el del entorno.** Por eso se comprueba **dentro** del proceso que sirve —`docker compose exec api python -c "..."`— y no leyendo el dataclass, que es donde se lee lo que uno quería que pasara. El caso: `timeout_lectura` valía `5.0` en su clase y el contenedor corría con **60**, porque `desde_entorno` leía `TIMEOUT_ETAPA_MS` y `compose.yml` lo trae en 60000 desde el encargo 0.3 —cuando no existían ni el plazo ni el vigilante—; una consulta se quedó **62 segundos congelada** con dos mecanismos construidos para impedirlo. **Y la forma general es peor que el caso: los valores del despliegue se eligieron ANTES que casi todo lo que hoy depende de ellos, así que envejecen sin avisar y pisan mecanismos que aún no existían cuando se escribieron.** Hay barrido (`scripts/comparar_configuracion.py --vivo`) que compara las tres capas —código, compose y contenedor— y marca cada diferencia; una diferencia no es un fallo, pero **tiene que ser una decisión**. En su primera pasada encontró un `VERSION_PROMPT` fijado en `2.2-eco-sin-recuperacion` esperando a estampar esa etiqueta en filas generadas con el prompt del 4.4.
- **Un `false` PERSISTIDO se lee como una medida, y esa es la mentira más barata de cometer: no hace falta escribir nada.** `respuestas.cache_hit` y `respuestas.escalado` existen desde el 2.1, valen siempre `false` y **nada las escribe**, así que cualquier consulta que las agregue dirá *"la caché nunca acierta"* cuando la verdad es *"no hay caché"*. Un documento que promete algo se lee con escepticismo; una columna con datos dentro, no. **La regla: un campo que nadie escribe se declara como tal donde se lea —README y COBERTURA— y, en la primera migración que toque esa tabla por cualquier otro motivo, pasa a admitir NULO, que es lo que de verdad significa.** No se gasta una migración solo para esto; sí se gasta una línea de documento, hoy.
- **UNA DEGRADACIÓN DECLARADA QUE NADIE IMPLEMENTÓ ES MÁS PELIGROSA QUE UNA NO DECLARADA, porque el documento crea una confianza que el código no ha ganado.** El caso: *"el contenedor sin torch sirve léxica y glosario"* se afirmó **dos veces como hecho** —en una revisión de `/salud` y en la Parte V— y era falso: `embebedor is None` devolvía **cero fragmentos** y el sistema respondía **de memoria**, que es exactamente lo que este proyecto dice no ser. Y no había ninguna dificultad técnica detrás: `recuperar()` acepta `vector=None` desde el 3.3 y hace las otras dos listas. **Nadie lo había escrito.** Se razonó desde el diseño en vez de leer el código, y la frase, al estar escrita, blindaba el hueco: quien la leyera dejaba de mirar. **La comprobación es un `grep`, y hay que hacerla a propósito**: por cada respaldo, degradación o *"si X falla se hace Y"* que aparezca en un documento, buscar la función que lo implementa y el test que lo cubre. La pasada del 13 de agosto de 2026 sobre el 8.1 y la Parte V encontró **cuatro** sin código, y una de ellas —el NLI del 4.3 **construido y no enchufado**— sostiene una de las cuatro frases del README. **Y peor que un documento es una COLUMNA:** `respuestas.cache_hit` y `respuestas.escalado` llevan meses en la base valiendo siempre `false` sin que nada las escriba, y un `false` persistido se lee como una medida.
- **Una comparación de umbral tiene que decidir ANTES qué hace con lo que NO es comparable, o el valor más raro es justo el que pasa.** `nan` no es mayor que nada —ni menor, ni igual—, así que una guarda escrita como *"si supera el tope, rechaza"* **no rechaza un `nan`**: la comparación devuelve `False` y eso se lee como un permiso. En el 4.4, `0.0 * inf` producía el `nan` y `2**2**2**30` atravesaba la guarda entera. La forma general es peor que el caso: **el `False` de una comparación con lo incomparable es indistinguible del `False` de una comparación que sale bien**, así que no hay nada que mirar. Se busca a propósito en todo umbral nuestro que reciba un número calculado —flotantes, divisiones, logaritmos, medias de listas vacías, restas de fechas— y la comprobación de finitud o de nulidad va **antes** del `>`, no después, y con su test llamando a la función con el valor raro en la mano.
- **La gramática PROHÍBE, no ELIGE: prohibición a la gramática, preferencia al prompt** (principio 7 refinado, y el refinamiento corrige la formulación anterior). *"En el prompt va lo que la gramática no puede imponer"* incluía **elegir entre ramas que la gramática permite todas**, y se leyó como si no. Lo que un `pattern`, un `maxLength` o un `maxItems` hacen es volver **ingramático** lo que no queremos: eso no se pide, se impone. Pero *cuál de los cinco tipos de afirmación usar* es una elección entre ramas legales, y ahí el esquema no manda nada — la `description` de un campo es una etiqueta que solo se lee **cuando ya se ha llegado a ese campo**, y al que nunca elige `calculo` no le llega nunca. **El caso, que costó el encargo entero:** el verificador de cálculo del 4.4 estuvo días completo, correcto y medido **sin una sola afirmación que juzgar**, porque `calculo` no aparecía en el prompt; cinco consultas explícitamente aritméticas dieron **cero** afirmaciones de ese tipo. Y la base no avisaba: **345 afirmaciones reales y cero de cálculo es un cero que no se pone rojo**. Antes de dar por construido un verificador, se comprueba que existe de verdad lo que verifica, y se comprueba **contando**, no leyendo el código.
- **Un patrón que acota una salida cercana al lenguaje natural está codificando una CONVENCIÓN CULTURAL, se dé cuenta quien lo escribe o no.** El nuestro decidió sin querer que los números se escriben a la inglesa: con `^-?\d+(\.\d+)?$`, el modelo quiso escribir `4.294.967.296` —correcto en español, y así salió en la prosa de esa misma respuesta— y la decodificación restringida, que permite **un** punto y no dos, dejó `4.294967296`. Cuatro coma tres en vez de cuatro mil millones: **un número gramatical y equivocado**, que es la peor clase de salida porque no falla, miente. Va a volver a pasar con **fechas** (`03/04` no es el mismo día a los dos lados del Atlántico), con **unidades** y con los **decimales** de cualquier campo nuevo. La comprobación, antes de fijar un patrón: *¿cómo escribiría esto una persona de aquí, y qué hace mi patrón con eso?* Y si el patrón y la costumbre no casan, **decírselo en la `description` no basta** — se probó, y el modelo volvió a escribirlo igual.
- **PONER LA GUARDA NO ES MEDIRLA, y hasta que se mide no se sabe qué deja pasar.** La pregunta *¿cuánto vale este tope en el peor caso que existe para cazar?* no es solo para los topes en la unidad equivocada: vale para **todos** los topes del repo, y se contesta con un número, no con la lectura del código. Se comprueba en las **dos** direcciones, porque las dos fallan distinto: lo que la guarda **admite** —el caso legal pegado al límite, que si tarda más que el presupuesto deja el tope mal puesto aunque nunca haya fallado— y lo que la guarda **rechaza** —que además tiene que rechazarlo **deprisa**, porque una guarda que tarda tres segundos en decir que no es la misma avería que pretendía evitar con otro nombre—. La guarda del 4.4 se escribió tres veces por medirla: (1) `evaluate=False` desactiva los **operadores** y no las **llamadas a función**, así que `factorial(100000)` se calculaba **dentro del parseo del propio guarda**, antes de que pudiera mirar nada —arreglado sustituyendo cada función por una **indefinida**, para que en esa pasada no haya nada que pueda ejecutarse—; (2) el tamaño se estimaba contando cifras, que es el logaritmo truncado, y para la base 2 daba **cero**, así que `2**999999999` salía con magnitud cero; y (3) el `0.0 * inf` resultante daba **`nan`, que no es mayor que nada**, o sea que atravesaba el `>` del tope como si fuera un permiso. **Ninguna de las tres se ve leyendo el código: las tres se ven cronometrando la bomba.** Y el número que se publica se mira dos veces: el peor caso admitido dio **31 ms** la primera vez y **1,7 ms** la segunda, porque la librería calentaba sus cachés — publicar el primero habría sido publicar un 95 % de arranque.
- **El error viaja en el SUMANDO, no en la suma.** Un número nuevo que se apoya en uno viejo hereda todo lo que el viejo tuviera de flojo, y lo hereda **en silencio**, porque la aritmética de encima está impecable y no se puede auditar mirándola. Pasó con los "3.076 ms de punta a punta": era un p50 de muestra pequeña y sin reordenador, se repitió como firme en varios sitios, y sobre él se construyeron totales y porcentajes de presupuesto que parecían medidos. **Antes de sumar sobre una cifra heredada, mirar de dónde salió: con qué n, en qué condiciones y si sigue valiendo.** Y si el número base es de otra configuración, no se suma: se vuelve a medir.
- **UN TEST NO COMPRUEBA QUE ALGO SEA CIERTO: COMPRUEBA QUE SIGA DICIENDO LO MISMO.** El caso, del 14 de agosto de 2026: con el reordenador ya descartado por su propio criterio (ADR 0019), la etapa `sin_reordenar` seguía anunciando *"sin GPU"* en cada consulta de producción —una avería inexistente— **y había un test anclando la mentira**: exigía la etapa y su detalle para `reordenador=None`. Cuando lo que se ancló era falso, el test es exactamente lo que impide arreglarlo: el arreglo lo pone en rojo y el rojo se lee como regresión, así que el test defiende a la mentira contra su corrección. La comprobación, cada vez que una DECISIÓN cambia el mundo (un descarte, una subida de plazo, un cableado nuevo): **buscar a propósito los tests que anclaban el mundo viejo**, porque no se van a poner rojos solos — su verde ES el problema.
- **LA COBERTURA NO DICE NADA SOBRE SI LO CUBIERTO ES LO QUE DECIDE.** Mismo día: **todo el recall del proyecto colgaba de una comparación de emparejamiento** (`(documento, orden) == esperado`) que ningún test tocaba — mutarla dejaba la suite en verde con las seis corridas publicadas falsas, porque la suite solo anclaba el nDCG, o sea la métrica de al lado. La pregunta al escribir cualquier medida, y cuesta un minuto: *¿qué línea, si se rompe, invierte el resultado sin poner nada rojo?* Esa línea se extrae a función con nombre y se ancla en las dos direcciones, incluido el impostor más barato (aquí: mismo `orden`, otro documento). Es hermana de la mutación que no se aplica: allí mentía el instrumento de mutar; aquí miente el mapa de qué protege la suite.
- **EL VALOR DE UNA PUERTA ES FUNCIÓN DE SU FRECUENCIA, NO DE SU EXISTENCIA: se empuja al menos una vez por sesión.** El caso, del 14 de agosto de 2026: la rama llevó día y medio sin push y el CI —que corre en cada push— no vio ~40 commits; cuando por fin los vio salió un rojo que existía desde el primero (`import torch` a pelo en un test, sin torch en el runner) y que había convivido con el verde local sin que nadie lo supiera. Un CI que ve un commit de cada cuarenta da exactamente eso: **un rojo caro de bisecar y una sensación de cobertura falsa en medio** — la puerta existía y no protegía, porque casi nunca miraba. Y el hallazgo de fondo, que es el que decide el arreglo: **el verde local y el rojo remoto medían cosas distintas** (torch presente contra ausente) y nadie lo sabía; cuando dos puertas divergen así, el arreglo es hacer que **midan lo mismo** —el doble de torch inyectado en `sys.modules`, que prueba la regla "GPU o nada" en las dos máquinas—, nunca saltar el test en una de ellas, que es hacer callar a la puerta que desafina.
- **UN VEREDICTO LLEVA LA FIRMA DE SU INSTRUMENTO, o toda consulta posterior que filtre por su valor mezclará instrumentos.** El caso, del 14 de agosto de 2026: `afirmaciones.veredicto = 'verificada'` lo escriben **dos verificadores distintos con el mismo valor** —el 4.2, que compara cadenas, y el NLI del 4.3 desde que está enchufado, sobre las literales que el 4.2 degradó— y **ninguna columna decía cuál**. La primera víctima fue la propia calibración del NLI: sus positivos se seleccionaban por `veredicto = 'verificada'`, así que **12 de 150 eran filas que el NLI se había aprobado a sí mismo** —cita ausente del fragmento por construcción, que es justo lo que las degradó— y el termómetro se estaba graduando contra sus propios aciertos. **Garantía circular, dentro de nuestro conjunto de control, desde la corrida 32.** Se cazó como se cazan estas: **mirando doce filas a ojo** porque un número no cuadraba (12 positivos sin anclar donde el diseño decía cero), no leyendo código. El arreglo inmediato es filtrar por la firma que solo deja el instrumento correcto (`detalle.verificacion.nivel`, que solo escribe la comparación de cadenas); el arreglo de fondo es que **el campo exista**: quien escribe un veredicto escribe quién es. Y la forma general, que es hermana del contador que responde a otra pregunta: **en cuanto un segundo productor puede escribir el mismo valor, ese valor deja de significar "esto pasó" y pasa a significar "alguien concluyó esto"** — y sin firma, no hay forma de saber quién ni con qué derecho.
- **AL RECOMPUTAR UN NÚMERO PUBLICADO, LO PRIMERO ES REPRODUCIRLO: si tu población no devuelve la cifra vieja, estás midiendo otra cosa y todo lo que venga después es ruido con formato de corrección.** Cometido el 14 de agosto de 2026 **dentro de una corrección**, que es donde peor cae: al recontar el número de cabecera del proyecto —*"57,9 % de las citas literales lo son"*— elegí la población por un corte que me pareció razonable (*todo lo anterior al 14/08*, 587 filas) en vez de reconstruir la publicada (las **337** primeras, hasta las 14 h del 13). **La señal estaba en pantalla y la leí por encima: mi cifra por filas daba 63,5 % donde lo publicado decía 57,9 %.** Esa discrepancia no era un detalle del recuento: era el aviso de que estaba comparando dos poblaciones. Con la ventana correcta el titular no *aguantaba* como dije, sino que **empeoraba siete puntos** (50,9 % en casos distintos). **La comprobación es una línea y va ANTES de publicar la corrección: recomputar primero en la unidad vieja y exigir que salga el número viejo.** Si no sale, la población está mal y no hay nada que corregir todavía.
- **UNA EXPLICACIÓN ELEGANTE ES UNA SEÑAL DE RIESGO, NO DE CALIDAD: cuanto mejor encaja un porqué, más barato sale comprobarlo ANTES de heredarlo.** Es el complemento de la regla de al lado —el número se re-mide y la explicación se hereda—: esta dice **cuál** es la explicación que hay que re-medir primero. El caso, del 14 de agosto de 2026: *"el umbral está clavado justo debajo de la mediana de las identidades"* cerraba **tres** observaciones a la vez —por qué el umbral sobrevivía a los barridos, por qué la verificación no subía, y por qué cambiar de juez lo arreglaba— y por eso mismo **calló la comprobación**: nadie recuenta lo que ya tiene sentido. Era un artefacto de contar filas en vez de casos, y lo destapó recontar a propósito, no dudar. **La comprobación, y es barata precisamente cuando la explicación es buena: escribir qué observación caería si el porqué fuera falso, y mirar esa.** Un porqué que no arriesga ninguna observación no es una explicación: es un adorno que encaja.
- **UNA ESPECIFICACIÓN CORREGIDA DESPUÉS DE VER EL RESULTADO MIDE COHERENCIA INTERNA, NO ACIERTO — y el número que sale de ahí no se publica como si midiera lo segundo.** Es la garantía circular subida un piso: allí el NLI se graduaba contra **sus propios aciertos**; aquí sería la **RÚBRICA** graduándose contra los suyos. El caso, del 14 de agosto de 2026: el clasificador de modo acertó **44 de 45** contra la rúbrica congelada a ciegas, el único fallo cayó en el caso que se había **declarado por escrito como ambiguo antes de abrir las etiquetas**, y la discrepancia se resolvió **añadiendo una cláusula a la rúbrica** (D7) porque la redacción vieja permitía las dos lecturas. Con la cláusula nueva el clasificador acierta **45 de 45** — **y ese 100 % no es una medida de fidelidad**, porque la cláusula nació de ese mismo desacuerdo. **Lo que sí se puede decir, con esas palabras: *"la implementación cumple la especificación corregida sin ninguna excepción"*, que es una afirmación sobre coherencia interna.** La comprobación, y hay que hacerla a propósito porque el número bonito no viene con etiqueta: **preguntar de qué fecha es la especificación contra la que se mide y compararla con la fecha en que se vieron los resultados.** Si la spec cambió después, hay dos números y solo el primero es una medida — se publican **los dos, con el orden y el motivo del cambio**, que es la misma disciplina que las predicciones congeladas en dos ficheros y no en uno editado. **Y el corolario que vale para cualquier protocolo de este tipo: que el único fallo caiga en un caso pre-declarado como ambiguo no es mala suerte, es la señal de que el protocolo hizo lo que decía** — la ambigüedad estaba en la spec y el experimento la sacó a la luz en vez de repartirla como error.
- **PÁSALE AL INSTRUMENTO EL CASO TRIVIALMENTE CIERTO DE SU TAREA ANTES DE CREERTE SU UMBRAL** —la identidad para un NLI, el duplicado exacto para un deduplicador, la misma imagen para un comparador—: **lo que no apruebe ahí es su techo, no tu problema**, y ninguna mejora de premisa, de selección o de datos podrá pasar de él sin que nada se ponga rojo. La vara sale gratis: no necesita etiquetado, ni humanos, ni desempate. El caso, del 14 de agosto de 2026: el juez NLI fallaba **2 de 22** identidades —textos que no se siguen de sí mismos— y el juez que lo sustituyó falla **0 de 22**, con la verificación de positivos subiendo de **49 % a 76 %** sobre pares distintos. **Y LA SEGUNDA MITAD DE ESTA REGLA ES UNA CORRECCIÓN A SU PROPIA PRIMERA VERSIÓN, que se deja escrita porque es la parte que enseña:** la escribí diciendo que el instrumento fallaba *"el 20 % de las identidades"* con *"mediana 0,66"*, y que el umbral 0,60 estaba *"clavado justo debajo de esa mediana"* — una explicación causal preciosa y **falsa**. Esos números salían de contar **filas** y no **casos**: 70 filas eran **22 pares distintos**, los 11 fallos eran **2 textos repetidos** y la mediana real sobre distintos era **0,91**. Lo destapó la pasada adversarial del mismo día, recontando. **La decisión que sostenían no cambió** —el juez nuevo sigue siendo mejor y por más margen del que parecía— **pero el porqué publicado era un artefacto**, y un porqué falso es peor que un número flojo: el número se re-mide, la explicación se hereda. Ver la regla de las ocurrencias contra los hallazgos, que es la que se incumplió.
- **UN CRITERIO PRE-ESCRITO PROTEGE CONTRA ELEGIR EL NÚMERO QUE CONVIENE; NO GARANTIZA QUE EL CRITERIO SEA CORRECTO.** Escribir el desempate antes de ver la tabla sirve para lo que sirve —que el resultado no elija el criterio— y **no** convierte al criterio en verdad. Cuando los datos lo contradicen, **se anula**, y se escriben **los dos**: el criterio tal como se escribió y la anulación con su evidencia. Dos casos el 14 de agosto de 2026, los dos en el mismo barrido: (1) el **ritmo**, donde el desempate elegía 50 y no se aplicó porque **la banda 35-50 está vacía** —ni una consulta sana (la más lenta va a 110 tok/s) ni una averiada (las dos medidas, 4 y 11)—, y elegir dentro de una banda sin observaciones es elegir sin evidencia; y (2) el **portero**, donde el desempate elegía 0,70 aterrizando en **0,2484 contra un techo declarado de 0,25**, o sea eligiendo **por el techo y no por el dato** — y al leer las 28 frases de esa banda resultaron ser casi todas prosa correcta, incluida la respuesta canónica del conjunto oro. **La comprobación que convierte esto en procedimiento: cuando el desempate aterrice pegado a un límite propio, o dentro de un tramo donde no hay observaciones, mirar los casos ANTES de aplicarlo.** Un criterio pre-escrito que se aplica a ciegas es la misma abdicación que no tenerlo, con papeleo.
- **ESCRIBIR UN CRITERIO NUEVO TENIENDO UNO JUSTIFICADO AL LADO ES COMO SE PIERDEN LAS DECISIONES VIEJAS.** Mismo día y mismo barrido: el criterio pre-escrito para calibrar el ritmo decía *"manda no cortar sano"* y **contradecía la asimetría MEDIDA que `app/core/ritmo.py` ya tenía escrita en su cabecera** —un corte falso cuesta ~2 s (se corta, se avisa, se vuelve a pedir) y un corte que no ocurre cuesta ~60 s de pantalla congelada: **treinta veces más**—. No hubo dato nuevo ni discusión: simplemente se escribió el criterio sin leer el que ya estaba, y la decisión vieja habría quedado derogada por descuido. Es la cara opuesta de "un número no lleva dentro su propia justificación": allí se **hereda** un porqué que ya no vale; aquí se **inventa** uno teniendo uno medido al lado. **La comprobación cuesta un minuto: antes de escribir el criterio de un umbral, leer lo que ese umbral ya tiene escrito** —su docstring, su ADR—, y si se va a contradecir, decirlo con esas palabras en vez de sustituirlo en silencio.
- **UN NÚMERO NO LLEVA DENTRO SU PROPIA JUSTIFICACIÓN: cuando cambia lo que el mecanismo HACE, su calibración anterior no se hereda aunque el valor siga sirviendo.** Va por tres, y la tercera es la que lo enseña entero. Un umbral es la respuesta a la pregunta *"¿qué error es el caro?"*, y esa pregunta cambia de respuesta cuando cambia el mecanismo: el portero del 4.5 **podaba**, así que su falso negativo era el caro —se llevaba una frase legítima de un texto que alguien está leyendo—; desde que **marca** en vez de podar (ADR 0021), un falso negativo solo pone una marca injusta —cosmético— y el caro pasa a ser el falso **positivo**, o sea una frase sin respaldo llegando **sin marca**, contenido no declarado con aspecto de respaldado. **La dirección de calibración se invierte: donde antes había que bajar el umbral, ahora hay que subirlo.** Un barrido hecho con la tabla vieja habría movido el número hacia el lado equivocado y habría salido en verde, porque el barrido no sabe qué error le duele a nadie. **La comprobación, y va ANTES del barrido: escribir la tabla de las dos consecuencias con el mecanismo NUEVO delante, y compararla con la vieja.** Si alguna casilla cambia de dueño, la calibración anterior no vale ni como punto de partida.
- **UN SUELO DE LONGITUD CODIFICA UNA SUPOSICIÓN SOBRE QUÉ ASPECTO TIENE LO QUE VALIDA.** Hermana del patrón que codifica una convención cultural, y se cazó igual: mirando la distribución real antes de fijar el número. Al cerrar en la gramática las 152 filas cuyo `texto` era el nombre de un tipo, el suelo propuesto a ojo era **20** y la distribución lo tumbó: mataba **40 de 826 afirmaciones sanas (4,8 %)**, y entre ellas `@RestController` (15) y `{% include ... %}` (17), que **en un corpus medio código son literales legítimas y perfectamente verificables**. El número correcto sale de la clase que se quiere prohibir y no de la intuición: el nombre de tipo más largo es `conocimiento` (12), así que **13** vuelve ingramatical la clase entera —que era el objetivo— por **16 de 826 (1,9 %)**, todas afirmaciones de una sola palabra. **Aquí una afirmación puede ser un identificador**, y un tope pensado para prosa no lo sabe. La comprobación antes de fijar cualquier mínimo o máximo: *¿cuál es el caso legítimo más extremo de este corpus, y qué hace mi tope con él?* — y se contesta contando, no imaginando.
- **UN FILTRO ESCRITO SOBRE EL EJEMPLO QUE MIRASTE CAZA EL EJEMPLO, NO LA CLASE.** El caso, del 14 de agosto de 2026 y cometido por quien acababa de escribir la regla de al lado: al excluir del control las filas rotas del generador, el filtro se escribió `texto = 'literal'` —la forma de las 147 que se habían mirado— y la clase era *"el texto es un nombre de tipo"*, que incluye 5 más con `texto = 'parafrasis'`. En el plano no cambiaba nada —138 positivos con los dos filtros, **contado antes de fiarse**— y en la comparación antes/después entraban 2, así que hubo que repetirla. **La comprobación es nombrar la clase en voz alta antes de escribir la condición**: si la frase que la describe (*"un nombre de tipo"*) no aparece en el código, lo que hay escrito es el ejemplo. Y cuando la clase ya existe enumerada en algún sitio —aquí, `TIPOS` del contrato—, se importa en vez de repetirla: una lista copiada a mano es un filtro que envejece solo. Es hermana de "reutiliza el mecanismo, re-deriva los parámetros", pero al revés: allí se hereda un parámetro que ya no vale; aquí se inventa uno demasiado estrecho desde el principio.
- **UN FILTRO SOBRE EL CONJUNTO DE CANDIDATAS BORRA APOYO EN SILENCIO: descartar destruye; expandir o fusionar preserva.** El caso, del 14 de agosto de 2026: `frases_de` parte por `\n+` y descarta lo que mide <40 o >400 caracteres — correcto para su trabajo del 1.8, limpiar ruido en una COMPARACIÓN de fragmentos, y pérdida de datos en el del 4.3, donde lo que se busca tiene que ESTAR en las candidatas para encontrarse: en markdown ese filtro convierte las listas en pseudo-frases y borra justo donde vive el apoyo. El "61 % de citas que cruzan frases" (corrida 36) era en su mayor parte artefacto del partidor: con la premisa cortada del fragmento CRUDO como ventana anclada en el span, **138 de 138 positivos limpios anclan** (corrida 38) y el cruce es imposible por construcción. Y la seña de esta avería es la peor de su familia: el filtro no falla, **devuelve otra cosa**, así que el número que sale tiene pinta de medida del mundo cuando es medida del instrumento. La comprobación, al llevar cualquier selector o filtro a una búsqueda nueva: *¿lo que busco SOBREVIVE al filtro?* — es "reutiliza el mecanismo, re-deriva los parámetros" aplicado al conjunto de candidatas y no a una constante.
- **DOS ERRORES QUE SE COMPENSAN PRODUCEN UN NÚMERO QUE PARECE CONFIRMADO, y ese acuerdo es la forma más peligrosa de validación falsa que existe: no hay nada que mirar, porque *sale lo mismo*.** El caso, del 14 de agosto de 2026, es el número de cabecera del proyecto. Publicado: **57,9 %** de citas literales que lo son de verdad (195/337, **filas**). Recontado por casos: **57,1 %** — y ese parecido se leyó como *«el titular aguanta»*. **No aguantaba: es 50,9 %**, siete puntos peor. El 57,1 llevaba **dos** desviaciones **opuestas** que se cancelaban: deduplicar bajaba siete puntos (57,9 → 50,9, porque las citas cortas y fáciles son las que más se repiten y la repetición maquillaba **a favor** del sistema) y una **población mal elegida** los subía seis (50,9 → 57,1). **Y la primera autópsia se equivocó de órgano**: dijo que la segunda desviación era *«dos denominadores mezclados»* y no lo era —sobre la ventana reconstruida, 195/337 sale **dígito a dígito**—; era **haber elegido la población por un corte que parecía razonable en vez de reconstruir la publicada**. Esa corrección es la parte que enseña, porque **un parecido no solo calla la comprobación del número: calla también la de su explicación**. Y que la ventana correcta **reproduzca 195/337 exacto y aún así dé 50,9 % en casos** es mejor evidencia que el número de antes: ya no cabe la duda de si se estaban comparando dos poblaciones. **La comprobación: cuando un número re-medido salga parecido al viejo, tratar el parecido como SOSPECHA y no como acuerdo** —misma población y misma unidad, por separado, con la regla de al lado (reproducir la cifra vieja antes de corregirla) como primer paso— **y escribir el aviso junto a la cifra**, porque el siguiente que la repita no tendrá esta conversación delante.
- **Y LA MEJOR DEFENSA DE `conteo.py` NO ES QUE OBLIGUE A DAR LAS DOS CIFRAS, SINO LO QUE PASÓ CUANDO SE DEDUPLICÓ CON LA CLAVE EQUIVOCADA: desapareció el ÚNICO problema que había.** Misma noche del 14/08, dentro de la propia pasada adversarial: los **negativos** del control NLI se dedujeron por `(fragmento propio, texto)` —la clave de los positivos— y con ella 158 negativos colapsaban a 74 y **el único negativo aprobado se evaporaba del recuento**. Su clave es `(fragmento AJENO, texto)`, porque un negativo es la afirmación contra un fragmento **ajeno** y el emparejado es determinista por índice: dos filas de la misma afirmación llevan ajenos distintos. Con la clave correcta son **146** y el negativo **sigue ahí**. **El deduplicador no falla: devuelve otra cosa, y lo que devuelve tiene mejor pinta** —es el filtro que borra apoyo en silencio, cometido dentro de la herramienta de auditar—. De ahí que `Conteo` lleve la **clave dentro**: un conteo sin decir qué hace iguales a dos elementos no se puede auditar, y el caso en que más falta hace es justo aquí, donde dos conjuntos del mismo experimento tienen claves DISTINTAS. Hermana del hallazgo del portero, donde publicar **una de dos corridas** hizo que un umbral *«aterrizara a un pelo del techo»* (24,8 % contra 25 %) cuando con las dos lo **rompe** (28,0 %): en los dos casos el instrumento no fallaba, **enseñaba un subconjunto favorable**.
- **VA POR TRES, Y LA TERCERA SE COMETIÓ EN EL NÚMERO QUE MÁS CONVENÍA QUE FUERA BUENO.** La regla —*«un número sin su renglón (unidad, n, corrida, fichero de evidencia) no se publica»*— llevaba días escrita, y el **12,0 % de incumplimiento del objetivo de 5 s** vivía **solo en el README**: ni en ESTADO, ni en una evidencia, ni con su denominador. Es el número que **corrige a mejor el suspenso más citado del repo**, y por eso mismo nadie le pidió el renglón: lo celebró hasta el propietario sin comprobarlo. **Las tres saltadas tienen la misma forma —el hash del manifiesto tras un merge, ocurrencias contra hallazgos, y ésta— y las tres se saltaron en el número grande, en el titular, en lo que más conviene que sea grande.** O sea que la disciplina se rompe exactamente donde más cara sale, y confiar en recordarla es confiar en no querer el resultado. **Y el desenlace enseña más que el hallazgo:** al darle su renglón, las dos cifras que parecían contradecirse —12,0 % sobre 150 y 35 % sobre el lote de veinte— resultaron ser **poblaciones distintas y medidas**: las 150 llevan asignatura elegida a mano y 24 son `acompanar`, con un p50 mil milisegundos más bajo. **Y en casos el 12,0 % baja a 9,9 %, o sea que aquí deduplicar MEJORA** —al revés que en el titular de las citas, donde empeoraba siete puntos—: la regla de las dos unidades no es un ritual, **cambia de signo según el caso**, y por eso hay que dar siempre las dos.
- **CUANDO EL VERDE LOCAL Y EL ROJO REMOTO DISCREPAN, SE HACE QUE LAS DOS PUERTAS MIDAN LO MISMO; NUNCA SE CALLA LA QUE DESAFINA.** El caso, del 15 de agosto de 2026: la puerta de la cabecera de `ESTADO.md` comprueba que el commit que ésta nombra sea **antepasado de HEAD**, y en CI daba *«no existe en este repo»* sobre un commit que sí existe — porque `actions/checkout` clona con `depth: 1` y el runner **no tenía esa historia**. Verde aquí y rojo allí **midiendo cosas distintas**: historia entera contra un solo commit. El arreglo es `fetch-depth: 0` y no un `skip`, porque saltarse el test en la máquina que desafina es desactivar la única puerta que sabe si ESTADO habla de esta historia o de otra. **Y la otra mitad de la regla es cómo se diagnostica: reproduciéndolo en local antes de empujar** —aquí, clonando el propio repo con `--depth 1`, que devolvió el 128 exacto del runner— **en vez de usar el CI de banco de pruebas**, que convierte cada hipótesis en un ciclo de tres minutos y un commit de ruido en la historia. La misma familia apareció en mi propia sonda el mismo día: exigía la forma **local** del nombre de la rama, y en CI el checkout deja HEAD desprendido y la rama solo existe como `origin/main` — habría fallado por **cómo se clonó el repo** y no por lo que dice la cabecera, que es medir el instrumento en vez de lo medido.
- **UNA PUERTA QUE PROMETE MÁS DE LO QUE MIRA ES PEOR QUE NO TENERLA, PORQUE ADEMÁS TRANQUILIZA.** El caso, del 15 de agosto de 2026: el test de las cifras del corpus nombraba en su propio docstring *"las seis cifras de la extrapolación a un tera"* entre lo que vigilaba, y **cubría dos**. Las seis estaban bien —así que nada se ponía rojo— pero **estaban bien porque alguien las había arreglado a mano**: el verde no lo daba la puerta, lo daba una coincidencia. **La comprobación es leer lo que la puerta DICE que vigila y contar lo que vigila de verdad**, y hay que hacerla a propósito, porque el docstring de un test es lo último que se relee. Hermana de la cobertura que no dice nada sobre si lo cubierto es lo que decide, con el agravante de que aquí **la promesa está escrita**. Y la segunda mitad del caso es la regla de al lado ganándose el sueldo en su primera corrida: al ampliar la puerta a las seis, **el patrón de las horas de embebido no casaba** —`COBERTURA.md` va envuelto a 100 columnas y parte *"de embebido"* en dos líneas—, así que sin la comprobación del RECUENTO habría dado cero coincidencias, salida cero y **verde sobre una cifra que no se estaba mirando**. La guarda que caza a la puerta es la misma que la puerta necesitaba.
- **TODA OPERACIÓN DEFINIDA POR UN PATRÓN —buscar, seleccionar, filtrar, reemplazar— DEVUELVE ÉXITO CUANDO EL PATRÓN NO CASA.** No hay error que leer: hay **cero coincidencias con código de salida cero**, que es indistinguible de *«hecho, y no había nada que hacer»*. **La guarda es siempre la misma y siempre está a mano: comprobar el RECUENTO de lo que casó, no el código de salida** —y exigir que ese recuento cuadre con cuántos elementos creías tener—. **Van SEIS en tres días con la forma exacta, así que es una clase y no una anécdota repetida:** (1) el **filtro sobre el conjunto de candidatas**, que no fallaba: devolvía otra cosa; (2) **`pytest -k "cartel"`**, que contestó *«1 passed»* sobre un fichero **mutado a propósito** porque había seleccionado otro test —el que perseguía no llevaba esa palabra en el nombre—, y un segundo más y el arreglo queda validado por una sonda que nunca corrió; (3) **`curl | grep "Encargo 2.4"`**, que devolvía **2 después** del arreglo porque los comentarios del fichero citan las cadenas viejas para contar por qué se quitaron —el grep miraba el cuerpo servido y el alumno mira la página renderizada: dos poblaciones para la misma pregunta—; (4) **`getElementById` con un id duplicado**, que devuelve **el primero** sin quejarse, o sea que la respuesta nueva se escribiría en el turno viejo y la pantalla quedaría **plausible y equivocada**; (5) **el reemplazo que no casa**, que dejó un fichero a medias y solo lo destapó `ruff` por casualidad, con un nombre indefinido; y (6) **el mismo reemplazo dos veces más el mismo día**, una porque el *heredoc* mutiló los acentos al pasar por stdin y otra porque **bash ejecutó los backticks** de un `python -c` — o sea que la tubería que transporta el parche también es un patrón que puede no casar. **El patrón común: el aparato contesta con precisión a una pregunta que no es la que se le hacía, y contesta que sí.** Por eso todo script de reemplazo de este repo **afirma cuántos bloques casó antes de escribir nada**, y por eso los parches con texto acentuado se hacen con el editor y no por tubería. **Y LOS DOS ÚLTIMOS AÑADEN UN PISO QUE GENERALIZA MÁS QUE ELLOS: no solo falla en silencio la operación que buscas — también falla en silencio EL CANAL POR EL QUE LA MANDAS.** El heredoc mutiló los acentos al pasar por stdin y bash se comió los backticks de un `python -c`: en los dos casos el patrón que no casó **no era el mío, era el del transporte**, y el resultado es idéntico —cero coincidencias, salida cero, fichero intacto con aire de arreglado—. Así que la pregunta no es solo *¿casó mi patrón?* sino *¿llegó mi patrón entero hasta donde se aplica?*, y se contesta igual: **haciendo que el canal declare cuántas piezas entregó**, no dando por hecho que entrega lo que se le mete.
- **UNA MEDIDA CUYO RESULTADO ESTÁ DETERMINADO POR CONSTRUCCIÓN NO ES UNA MEDIDA: es una sonda que no puede ponerse roja, y su verde no informa de nada.** El caso, del 14 de agosto de 2026, cazado por el propietario **antes** de que se picara: el plan del índice padre-hijo decía *«hijo = fragmento actual de 512, padre = sección del árbol»* y proponía medir el **techo del pool**. Con ese diseño la búsqueda sigue corriendo **sobre los mismos vectores de 512**, así que el techo habría dado **cero cambio por construcción** —y ese cero se habría leído como *«el índice no aporta»*, que es una conclusión sobre el mundo sacada de una imposibilidad aritmética. El diseño que SÍ puede mover el techo es el inverso: **el fragmento de 512 es el PADRE y los hijos son trozos de ~128 troceados dentro**, porque la pérdida vive en la **dilución del embedding** —dos frases entre cuatrocientas ochenta—; se busca sobre hijos, se deduplica por padre y se devuelve el padre. **La comprobación va ANTES de correr nada y es una pregunta: ¿qué tendría que pasar para que este número se moviera, y puede pasar con lo que voy a cambiar?** Si la respuesta es que no, no hay experimento: hay una tautología con formato de tabla. Es la forma general de «toda sonda se valida contra un caso donde debe fallar», subida un piso: allí se comprueba que el instrumento sabe ponerse rojo, aquí que el EXPERIMENTO puede salir distinto.
- **CUANDO UNA REGLA ESCRITA SE SALTA JUSTO DONDE IMPORTA, LA REGLA NO ES EL ARREGLO: el arreglo es que el código no permita saltarla.** Y va por dos en dos días, con la misma forma exacta, así que ya no es anécdota. (1) **El hash del manifiesto tras un merge**: era una nota que alguien tenía que acordarse de leer, mordió en el cierre de la fase 2 y en el de la fase 3 —**dos de dos**— y dejó de morder cuando fusionar pasó a ser un comando, `scripts/fusionar.py`, que corre la puerta **después** por construcción. (2) **Ocurrencias contra hallazgos**: la regla llevaba meses escrita, y el documento del verificador literal la aplicaba **doce líneas más arriba** de su número de cabecera —*"9 ocurrencias, 3 hallazgos"*— y **la saltó justo en el número que se dice en voz alta**. Dejó de poder saltarse cuando el conteo pasó a ser `app/core/conteo.py`, cuyo `contar()` devuelve **siempre** las dos cifras y su clave: no se puede publicar una sin tener la gemela delante. **Y lo que enseña el patrón es dónde falla la regla, porque no falla al azar: se salta en el número grande, en el titular, en lo que más conviene que sea grande.** O sea que la disciplina se rompe exactamente donde más cara sale, y por eso confiar en recordarla es confiar en no querer el resultado. **La comprobación, cuando se pille una regla saltada: preguntar si el arreglo que se está escribiendo es prosa o es un paso del procedimiento.** Si es prosa, se vuelve a saltar; la única diferencia es que la próxima vez habrá además un documento diciendo que no debería haber pasado.
```

---

# APÉNDICE B: sección "Escala" del README, ya redactada

Se pega en el README en la fase 8. Los huecos [medido: ...] se rellenan con los números reales de las fases 1.5 y 7.5; nada de este texto se publica con los huecos sin rellenar. Los supuestos de la tabla de 4 TB se declaran como supuestos: son órdenes de magnitud para presupuestar, no medidas.

---

## Escala

### El invariante

Una consulta nunca toca el corpus entero. El contexto del alumno (grado, curso, asignatura) selecciona una partición y la búsqueda ocurre dentro de ella. Una asignatura no engorda porque el corpus tenga más asignaturas: el temario útil de un módulo pesa lo mismo dentro de 170 MB que dentro de 4 TB, porque los teras de un corpus educativo real vienen de la amplitud (más titulaciones) y del formato (escaneos y vídeo), no de que cada asignatura tenga más texto. En consecuencia, la latencia y el coste por consulta son independientes del tamaño total del corpus por construcción, y la verificación opera sobre la respuesta y sus fragmentos, no sobre el corpus, así que tampoco crece. Evidencia: curva de latencia p95 sobre la asignatura real con el corpus total inflado x1, x10 y x50 con carga sintética [medido: curva del encargo 7.5], y plan de EXPLAIN con poda de particiones [evidencia del encargo 2.1].

### La jerarquía del alumno ES la clave de partición

El árbol titulación, curso, asignatura no es una forma de organizar carpetas: es el mecanismo de escala y de veracidad a la vez. La matrícula del alumno fija qué particiones puede tocar su consulta, así que el filtro no es un parámetro que alguien tenga que acertar, viene dado por quién pregunta. Eso mantiene la rebanada de búsqueda constante y elimina la contaminación entre asignaturas [medido: tasa de contaminación cruzada del encargo 3.5].

### Qué crece con el corpus, y cuánto

Crece la ingesta, y es lineal, nocturna y paralelizable por asignatura. Los teras de binario se encogen al destilarse a texto: el vídeo de clase comprime a texto en torno a 15.000 a 1 (una hora de vídeo ronda el giga y su transcripción ronda los 65 KB), el PDF escaneado en torno a 100 o 200 a 1, y el PDF digital en torno a 10 o 20 a 1. Coste de ingesta por giga de este corpus: [medido: encargo 1.5], con su extrapolación.

### Comparación: este corpus contra un despliegue de 4 TB

Supuesto de composición para 4 TB, a sustituir por el inventario real del cliente: 3 TB de vídeo, 0,8 TB de PDF escaneado, 0,2 TB de PDF digital, repartidos en decenas de titulaciones.

| Dimensión | Este corpus (v1) | 4 TB (estimación con supuestos declarados) |
|---|---|---|
| Binario de entrada | ~0,17 GB | 4 TB |
| Texto útil tras destilar | ~decenas de MB | ~15 a 30 GB |
| Fragmentos de 512 tokens | ~decenas de miles | ~10 a 15 millones |
| Vectores (1024 dims) más índices | MB | ~120 a 150 GB (la mitad en float16) |
| Fragmentos por asignatura (mediana) | ~decenas de miles | ~15 a 25 mil (con cientos de asignaturas) |
| Latencia y coste por consulta | [medido] | El mismo: la rebanada no cambia |
| Ingesta | Horas en una GPU de consumo | El coste dominante: miles de horas de transcripción y millones de páginas de OCR, presupuestado por regla de tres sobre [medido: coste por giga] |
| QPS de servicio | Lo dimensionan los alumnos, no los TB | Ídem |

La lectura de la tabla: el eje del alumno (qué asignatura consulta) no cambia entre las dos columnas, y por eso su experiencia tampoco; el eje del operador (cuánto cuesta ingerir y almacenar) crece lineal y se presupuesta con números medidos, no con adjetivos.

### Los dos puntos donde a esa escala se cambia una pieza, con su disparador

1. Almacén vectorial: pgvector con partición por asignatura aguanta mientras ninguna partición supere [medido: umbral de la curva 2 del encargo 7.5] fragmentos. La asignatura monstruo (años de vídeo transcrito en un solo módulo) se trata antes de llegar ahí: sub-partición por unidad o por año. Pasado el umbral, o por operación (mantenimiento, réplicas) a partir de ~10 millones de fragmentos totales, migración a almacén dedicado repartiendo particiones entre nodos; el esquema ya está particionado, así que es mover, no rediseñar.
2. Inferencia: serverless europeo escala solo hasta que el volumen de consultas justifique el pool propio de vLLM (continuous batching, caché de prefijos, decodificación especulativa por sufijos); el cambio es la URL base de la configuración, no código.

Detección de conflictos a esa escala: deja de ser todos contra todos dentro de la asignatura y pasa a vecinos aproximados con bloqueo; sigue siendo un trabajo nocturno que jamás toca la latencia del alumno.

### La frase que resume esta sección

La latencia y la veracidad por consulta son independientes del tamaño total por diseño, y aquí está la curva que lo demuestra; lo que crece con el corpus es la ingesta, medida y extrapolada; y los puntos donde a 4 TB se cambia una pieza están declarados con su umbral.
