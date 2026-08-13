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
- **Un umbral expresado en la unidad que el fallo infla se relaja justo cuando debería apretar.** El vigilante de ritmo del 3.4 tenía su gracia en **24 tokens**: como el fallo que persigue es que lleguen **pocos tokens por segundo**, esa gracia valía 0,2 s en una consulta sana y **6 s en la peor**, o sea que el guardia se echaba a dormir en proporción a la gravedad. La forma general: **si el tope se cuenta en la misma magnitud que la avería degrada, el tope se estira solo.** Se busca a propósito en cualquier límite nuestro contado en **tokens, elementos o intentos cuando lo que falla es el TIEMPO** —y al revés—. La comprobación es de una línea: *¿cuánto vale este tope en el peor caso que existe para cazar?* Si la respuesta es "más que el presupuesto", está expresado en la unidad equivocada.
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
