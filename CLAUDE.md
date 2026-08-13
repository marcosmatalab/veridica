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
- **"EL INSTRUMENTO MIENTE" YA VA POR CUATRO, así que se busca a propósito en vez de esperar a tropezarla.** Las cuatro, con su forma: (1) **transformers sin anclar** —la versión que corre no es la que el documento dice—; (2) **`python -m pytest`** —mete el directorio actual en `sys.path` y el CI no, o sea que la puerta y la máquina de quien la escribe ejecutan cosas distintas—; (3) **el intérprete** —`C:\Python313` en vez del miniconda declarado, sin torch—; y (4) **`git diff` sobre un fichero NO RASTREADO devuelve VACÍO**, que en el ritual de la mutación se lee exactamente igual que "la mutación no se aplicó" y por eso es la peor de las cuatro: no falla, calla. Se arregla con `git add -N` antes de diffear. **El patrón común y lo que hay que preguntarse: el aparato de medir no está midiendo lo que su nombre dice.** La comprobación siempre es la misma familia y siempre es barata: hacer que el instrumento enseñe QUÉ está mirando —la ruta, la versión, el diff, el código de salida— antes de creerse lo que dice, y muy en particular antes de creerse un VACÍO o un verde.
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
- **UNA DEGRADACIÓN DECLARADA QUE NADIE IMPLEMENTÓ ES MÁS PELIGROSA QUE UNA NO DECLARADA, porque el documento crea una confianza que el código no ha ganado.** El caso: *"el contenedor sin torch sirve léxica y glosario"* se afirmó **dos veces como hecho** —en una revisión de `/salud` y en la Parte V— y era falso: `embebedor is None` devolvía **cero fragmentos** y el sistema respondía **de memoria**, que es exactamente lo que este proyecto dice no ser. Y no había ninguna dificultad técnica detrás: `recuperar()` acepta `vector=None` desde el 3.3 y hace las otras dos listas. **Nadie lo había escrito.** Se razonó desde el diseño en vez de leer el código, y la frase, al estar escrita, blindaba el hueco: quien la leyera dejaba de mirar. **La comprobación es un `grep`, y hay que hacerla a propósito**: por cada respaldo, degradación o *"si X falla se hace Y"* que aparezca en un documento, buscar la función que lo implementa y el test que lo cubre. La pasada del 13 de agosto de 2026 sobre el 8.1 y la Parte V encontró **cuatro** sin código, y una de ellas —el NLI del 4.3 **construido y no enchufado**— sostiene una de las cuatro frases del README. **Y peor que un documento es una COLUMNA:** `respuestas.cache_hit` y `respuestas.escalado` llevan meses en la base valiendo siempre `false` sin que nada las escriba, y un `false` persistido se lee como una medida.
- **Una comparación de umbral tiene que decidir ANTES qué hace con lo que NO es comparable, o el valor más raro es justo el que pasa.** `nan` no es mayor que nada —ni menor, ni igual—, así que una guarda escrita como *"si supera el tope, rechaza"* **no rechaza un `nan`**: la comparación devuelve `False` y eso se lee como un permiso. En el 4.4, `0.0 * inf` producía el `nan` y `2**2**2**30` atravesaba la guarda entera. La forma general es peor que el caso: **el `False` de una comparación con lo incomparable es indistinguible del `False` de una comparación que sale bien**, así que no hay nada que mirar. Se busca a propósito en todo umbral nuestro que reciba un número calculado —flotantes, divisiones, logaritmos, medias de listas vacías, restas de fechas— y la comprobación de finitud o de nulidad va **antes** del `>`, no después, y con su test llamando a la función con el valor raro en la mano.
- **La gramática PROHÍBE, no ELIGE: prohibición a la gramática, preferencia al prompt** (principio 7 refinado, y el refinamiento corrige la formulación anterior). *"En el prompt va lo que la gramática no puede imponer"* incluía **elegir entre ramas que la gramática permite todas**, y se leyó como si no. Lo que un `pattern`, un `maxLength` o un `maxItems` hacen es volver **ingramático** lo que no queremos: eso no se pide, se impone. Pero *cuál de los cinco tipos de afirmación usar* es una elección entre ramas legales, y ahí el esquema no manda nada — la `description` de un campo es una etiqueta que solo se lee **cuando ya se ha llegado a ese campo**, y al que nunca elige `calculo` no le llega nunca. **El caso, que costó el encargo entero:** el verificador de cálculo del 4.4 estuvo días completo, correcto y medido **sin una sola afirmación que juzgar**, porque `calculo` no aparecía en el prompt; cinco consultas explícitamente aritméticas dieron **cero** afirmaciones de ese tipo. Y la base no avisaba: **345 afirmaciones reales y cero de cálculo es un cero que no se pone rojo**. Antes de dar por construido un verificador, se comprueba que existe de verdad lo que verifica, y se comprueba **contando**, no leyendo el código.
- **Un patrón que acota una salida cercana al lenguaje natural está codificando una CONVENCIÓN CULTURAL, se dé cuenta quien lo escribe o no.** El nuestro decidió sin querer que los números se escriben a la inglesa: con `^-?\d+(\.\d+)?$`, el modelo quiso escribir `4.294.967.296` —correcto en español, y así salió en la prosa de esa misma respuesta— y la decodificación restringida, que permite **un** punto y no dos, dejó `4.294967296`. Cuatro coma tres en vez de cuatro mil millones: **un número gramatical y equivocado**, que es la peor clase de salida porque no falla, miente. Va a volver a pasar con **fechas** (`03/04` no es el mismo día a los dos lados del Atlántico), con **unidades** y con los **decimales** de cualquier campo nuevo. La comprobación, antes de fijar un patrón: *¿cómo escribiría esto una persona de aquí, y qué hace mi patrón con eso?* Y si el patrón y la costumbre no casan, **decírselo en la `description` no basta** — se probó, y el modelo volvió a escribirlo igual.
- **PONER LA GUARDA NO ES MEDIRLA, y hasta que se mide no se sabe qué deja pasar.** La pregunta *¿cuánto vale este tope en el peor caso que existe para cazar?* no es solo para los topes en la unidad equivocada: vale para **todos** los topes del repo, y se contesta con un número, no con la lectura del código. Se comprueba en las **dos** direcciones, porque las dos fallan distinto: lo que la guarda **admite** —el caso legal pegado al límite, que si tarda más que el presupuesto deja el tope mal puesto aunque nunca haya fallado— y lo que la guarda **rechaza** —que además tiene que rechazarlo **deprisa**, porque una guarda que tarda tres segundos en decir que no es la misma avería que pretendía evitar con otro nombre—. La guarda del 4.4 se escribió tres veces por medirla: (1) `evaluate=False` desactiva los **operadores** y no las **llamadas a función**, así que `factorial(100000)` se calculaba **dentro del parseo del propio guarda**, antes de que pudiera mirar nada —arreglado sustituyendo cada función por una **indefinida**, para que en esa pasada no haya nada que pueda ejecutarse—; (2) el tamaño se estimaba contando cifras, que es el logaritmo truncado, y para la base 2 daba **cero**, así que `2**999999999` salía con magnitud cero; y (3) el `0.0 * inf` resultante daba **`nan`, que no es mayor que nada**, o sea que atravesaba el `>` del tope como si fuera un permiso. **Ninguna de las tres se ve leyendo el código: las tres se ven cronometrando la bomba.** Y el número que se publica se mira dos veces: el peor caso admitido dio **31 ms** la primera vez y **1,7 ms** la segunda, porque la librería calentaba sus cachés — publicar el primero habría sido publicar un 95 % de arranque.
- **El error viaja en el SUMANDO, no en la suma.** Un número nuevo que se apoya en uno viejo hereda todo lo que el viejo tuviera de flojo, y lo hereda **en silencio**, porque la aritmética de encima está impecable y no se puede auditar mirándola. Pasó con los "3.076 ms de punta a punta": era un p50 de muestra pequeña y sin reordenador, se repitió como firme en varios sitios, y sobre él se construyeron totales y porcentajes de presupuesto que parecían medidos. **Antes de sumar sobre una cifra heredada, mirar de dónde salió: con qué n, en qué condiciones y si sigue valiendo.** Y si el número base es de otra configuración, no se suma: se vuelve a medir.

## Puertas de calidad (encargo 0.2)

Las reglas de arriba son el Apéndice A de la guía, tal cual. Esto es la operativa concreta del repo.

**En CI** (`.github/workflows/ci.yml`, en push de cualquier rama y en PR), con las herramientas
ancladas en `requirements-dev.txt` y las reglas fijadas en `pyproject.toml`:

```bash
ruff check .    # reglas escritas en pyproject.toml: F401 y F821 dentro
pytest          # tests sobre corpus de juguete: no necesitan el corpus real
```

**En local** (esta NO corre en CI, porque el corpus está fuera de git y el runner no lo tiene; el
porqué y el trade-off, en [ADR 0001](docs/adr/0001-puerta-del-manifiesto-local-no-en-ci.md)):

```bash
python scripts/verificar_manifiesto.py   # rutas + SHA-256 de todas las entradas, ~1 s
```

**Cuándo se corre, que es tan importante como que exista:**

1. **Al abrir cualquier sesión que vaya a tocar el corpus**, antes de nada. Un fichero corrupto
   descubierto al principio cuesta un `git checkout`; descubierto tarde, contamina todo lo que se
   haya construido encima.
2. **Obligatoriamente antes de la ingesta del encargo 1.5**, sin excepción. Y el motivo NO es el
   coste de re-embeber, que está medido y son 58 segundos: es que no te enteras entonces. Te enteras
   semanas después, cuando las respuestas salen raras y no sabes si la culpa es del troceado, del
   reordenador o del modelo. La puerta cuesta un segundo; el fallo que evita cuesta una tarde y una
   investigación en falso.
3. Antes de commitear cualquier cambio del corpus o del manifiesto.
4. **Después de cualquier merge que toque un fichero con entrada en el manifiesto**, y se recalcula
   su hash. Si las dos ramas editaron ese fichero, el contenido fusionado es un tercer contenido que
   **no hasheó ninguna de las dos**, así que la entrada queda desactualizada sin que nadie se haya
   equivocado. Lo descubrió el merge de la fase 2 con `corpus/COBERTURA.md`. Y ojo, que esta puerta
   es local (ADR 0001): el CI no la corre, así que un merge puede dejarla roja en silencio.

Códigos de salida: `0` sin hallazgos, `1` con hallazgos de integridad, `2` manifiesto ilegible o mal
formado (que no es lo mismo: un manifiesto roto no es un corpus roto).

**Segunda puerta local, la de los pares oro** (encargo 3.0; local por el mismo motivo y con el mismo
trade-off, en [ADR 0010](docs/adr/0010-el-par-oro-se-ancla-al-texto-no-a-la-posicion.md)):

```bash
python scripts/verificar_oro.py          # los 100 pares contra el índice, por posición Y por texto
```

**Cuándo se corre:**

1. **Obligatoriamente antes de cualquier medida del 3.5**, sin excepción, y por el mismo motivo que
   la puerta del manifiesto antes de la ingesta: **un conjunto oro desalineado no da error, da ruido
   con aspecto de dato.** No sale un rojo ni una excepción; salen un recall@6 y un nDCG@5 con la
   pinta de siempre que están midiendo si la recuperación encuentra párrafos que nadie eligió. Es la
   única avería de esta fase que no se nota mirando el resultado.
2. **Después de cualquier cambio de troceado, de normalización o de la puerta de admisión del 1.4.**
   Los tres mueven el `orden` o el texto de los fragmentos, y el `orden` es posicional: el par sigue
   apuntando a algo, solo que a otra cosa.
3. Antes de commitear cualquier cambio de `evals/casos/oro_recuperacion.jsonl`.

Códigos de salida: `0` sin hallazgos, `1` con hallazgos en los pares, `2` casos o índice ilegibles o
mal formados. El `2` importa aquí más que en la otra puerta: en CI el índice **falta siempre**, y "no
he podido leerlo" no puede disfrazarse de "los pares oro están mal". Este script **no repara**: un par
desplazado se vuelve a leer a mano, porque un verificador que sabe reescribir lo que verifica puede
ponerse verde solo.

Python 3.13 en las dos partes: local es CPython 3.13.2 (base de miniconda) y el CI corre 3.13.

## Entorno local (encargo 0.3)

```bash
docker compose up -d --wait   # db, redis, api y worker; el verde de --wait ES /salud en verde
docker compose down           # para los servicios y CONSERVA los datos
curl http://127.0.0.1:8000/salud
```

**`docker compose down -v` BORRA el volumen `datos-db`, y con él la base entera.** **Para reiniciar
servicios se usa `down` a secas**; el `-v` solo cuando se quiera una base vacía a propósito.

Con el número medido delante, y corrigiendo lo que este aviso decía antes ("horas de GPU"):
re-embeber el corpus entero son **65 segundos** en la 5080, o unos **70 minutos** en CPU
(198,9 fragmentos/s frente a 3,1; encargo 1.5). O sea que el coste de un `-v` no es la GPU: son los
vectores ya calculados que hay en `corpus/embeddings/` —que sobreviven, porque no viven en la base—
más rehacer la carga y los índices. Sigue sin hacerse a la ligera, pero por el motivo correcto.

Puertos del host, elegidos midiendo la máquina y no por costumbre: **db en 5434** (el 5432 se lo
queda el servicio `postgresql-x64-17`, instalado en modo automático, al reiniciar Windows; el 5433 y
el 6379 los tiene publicados el proyecto `fulkro-oss`), **api en 8000**, y **redis sin publicar**
porque nada fuera de la red de compose lo necesita. `corpus/` no se monta en ningún contenedor: la
ingesta corre en Windows para usar la GPU.
