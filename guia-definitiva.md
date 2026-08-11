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

## 3. Comportamiento: cuatro modos como máquina de estados

La pedagogía es política explícita en código; el modelo rellena los estados. El fallo típico de un LLM tutor es salirse de la estrategia, empezando por soltar la solución.

- **Responder.** Duda directa, respuesta con fuentes.
- **Acompañar.** Socrático: guía sin soltar la solución, pide el siguiente paso al alumno, valida o corrige cada paso contra el temario. Reglas duras del modo: nunca dar el resultado final ni el paso completo resuelto; máximo una pista por turno; si el alumno lo pide explícitamente tres veces, se ofrece cambiar a modo responder (el cambio queda en la traza).
- **Corregir.** Recibe un intento o solo un resultado. Con solo el resultado, el resultado es el oráculo: se genera la derivación completa con la restricción de que la última línea iguale el resultado dado; el verificador recalcula; si no existe camino desde el temario hasta ese número, el sistema dice que quizá el resultado está mal.
- **Examinar.** Tipo test desde el temario, con evaluación. DISEÑADO, NO CONSTRUIDO. Lleva pegada la nota del AI Act (Parte VI).

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
- Reordenador: **BGE reranker v2-m3** (cross-encoder abierto multilingüe). En servicio, cuantizado en la CPU del VPS sobre los 20 mejores; en producción, a GPU.
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
      "tipo": "literal | parafrasis | calculo | conocimiento",
      "texto": "la afirmación tal cual irá al alumno",
      "fragmento_id": 12345,
      "cita": "texto exacto copiado del fragmento (solo si tipo=literal)",
      "expresion": "expresión o código a recalcular (solo si tipo=calculo)"
    }
  ],
  "respuesta_redactada": "texto final que hila las afirmaciones, sin añadir contenido nuevo",
  "siguiente_paso": {"tipo": "concepto_arbol | pregunta_al_alumno", "ref": "ruta en el árbol o null", "texto": "..."},
  "confianza_recuperacion": "alta | media | baja"
}
```

Regla de oro del contrato: `respuesta_redactada` no puede contener contenido que no esté en `afirmaciones`. El validador lo comprueba por cobertura aproximada (toda frase de la redacción debe solapar con alguna afirmación); las frases huérfanas se tratan como afirmaciones `conocimiento` no declaradas: un reintento y después poda.

## 8. Contratos de verificación

- **`literal`:** normalización (minúsculas, espacios colapsados, tildes conservadas) y búsqueda de subcadena exacta de `cita` dentro del texto del `fragmento_id`. Sin umbral, sin modelo. Falla: degradar a `parafrasis` y verificar como tal; si también falla, poda.
- **`parafrasis`:** NLI con premisa = fragmento, hipótesis = texto. Veredicto `entail` con probabilidad ≥ 0,80 (inicial, se calibra en el encargo 4.6 contra los pares oro) pasa; `contradiction` poda siempre; `neutral` dispara el reintento único con la señal.
- **`calculo`:** si `expresion` es aritmética, recálculo con evaluador seguro (sin `eval` de Python: parser propio o sympy). Si es código, ejecución en sandbox: contenedor efímero sin red, 0,5 CPU, 256 MB, timeout 5 segundos, sistema de archivos de solo lectura salvo `/tmp`. La salida se compara con lo afirmado.
- **`conocimiento`:** no se verifica; se marca. Si `confianza_recuperacion` era alta y aun así el modelo tiró de conocimiento, se registra en la traza (señal de recuperación floja o de pregunta fuera de temario).
- **Política global:** máximo un reintento por respuesta. Presupuesto de verificación por consulta: configurable, inicial 2 segundos; lo que no llega, poda o abstención, jamás pase silencioso.

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
  hash_sha256 char(64) NOT NULL UNIQUE, densidad text NOT NULL DEFAULT 'completa',
  origen text NOT NULL DEFAULT 'texto');  -- 'texto' | 'ocr'

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
  UNIQUE (asignatura_id, termino));

CREATE TABLE conflictos (id serial PRIMARY KEY, fragmento_a bigint NOT NULL,
  fragmento_b bigint NOT NULL, similitud real, estado text NOT NULL DEFAULT 'abierto', detalle text);

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

- `POST /consulta`: body `{texto, asignatura_id, modo?, usuario_id?}`; respuesta SSE con eventos `ttft`, `token`, `afirmaciones`, `fin` (el TTFT medido es el que ve el alumno).
- `POST /ingesta/documento`: idempotente por `hash_sha256`; encola el trabajo, devuelve id de trabajo.
- `POST /eval/correr`: body `{conjuntos: [...], config: {...}}`; corre el arnés y persiste en `corridas_eval`.
- `GET /trazas/{respuesta_id}`: la traza completa.
- `GET /salud` (dependencias una a una), `GET /metricas` (formato Prometheus).

## 11. Configuración (variables de entorno, `.env.example` sin valores)

`DATABASE_URL`, `REDIS_URL`, `INFERENCIA_BASE_URL` (Scaleway), `INFERENCIA_API_KEY`, `MODELO_PEQUENO`, `MODELO_GRANDE`, `PRECIO_ENTRADA_PEQ`, `PRECIO_SALIDA_PEQ`, `PRECIO_ENTRADA_GRANDE`, `PRECIO_SALIDA_GRANDE` (se rellenan del pricing vigente de Scaleway al arrancar la fase 6), `UMBRAL_CACHE_SIM` (inicial 0,92), `UMBRAL_NLI` (inicial 0,80), `RERANK_CANDIDATOS` (inicial 20), `TIMEOUT_ETAPA_MS`, `PRESUPUESTO_CONSULTA_MS` (inicial 8000), `VERSION_PROMPT`, `VERSION_CORPUS`.

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

**Punto de partida: el paquete `corpus-daw.zip` (v3-2026-08-11, los tres grados) ya existe y adelanta parte de esta fase.** El árbol viene YA recolocado por titulación (`corpus/daw/`, `corpus/dam/`, `corpus/asir/`, `corpus/familia/`), o sea el paso 1 del encargo 1.12 está hecho. Dentro de `daw/`: normativa BOE (RD 686/2010 y Orden EDU/2887/2010 en PDF), Programación completa (lionel-ict), DWES 2025-2026 completo (joseluisgs 00 a 05, markdown) y el DWES antiguo de Comesaña marcado `plantado: true`. Dentro de `dam/apuntes/` y `asir/apuntes/`: las titulaciones hermanas a densidad parcial (temario DAM de Comesaña podado a material didáctico; ASIR con lora-1asir, lora-2asir y aberlanas-iso con su LICENSE), y `familia/` con el índice de la familia profesional. En v3, DAW trae además sus módulos restantes con el material de Comesaña podado (sistemas informáticos, bases de datos, lenguajes de marcas, entornos de desarrollo, FOL, DWEC, despliegue, DIW y EIE; Programación SIN versión antigua a propósito: las contradicciones solo viven plantadas), y `corpus/COBERTURA.md` es el mapa módulo a módulo de las tres titulaciones con fuentes, transversales y los dos huecos declarados (0616 Proyecto de DAW y 0489 PMDM de DAM). El `manifiesto.jsonl` (2.094 entradas: ruta, fuente, licencia, hash SHA-256, densidad, plantado; 16 plantadas) está verificado contra disco con cero huecos, e incluye la regla de licencias del 1.12 aplicada (los repos sin licencia declarada van marcados como uso local no redistribuible). Estado de los encargos con este paquete: **1.1 parcialmente cubierto** (queda el RD 405/2023 con su script, los PDF del RD 450/2010 y RD 1629/2009 en `dam/normativa/` y `asir/normativa/` donde los POR-DESCARGAR.txt lo indican, y cargar los árboles en `asignaturas` desde los anexos), **1.2 cubierto a medias** (manifiesto completo y verificador en verde, pero ese verde solo cruza rutas: lo arregla el nuevo encargo 1.0), **1.7 parcialmente cubierto** (par contradictorio real dentro; quedan duplicados y el documento colado), **1.12 pasos 1 y 3 cubiertos** (recolocación hecha y apuntes de hermanas dentro; quedan la normativa de DAM y ASIR, la carga en `asignaturas` y el selector). El resto de encargos, de 1.3 en adelante, se hacen tal cual. Claude Code parte de este paquete descomprimido en la raíz del repo: no re-descarga lo que ya está en el manifiesto.

**1.0 El verificador de manifiesto comprueba hashes, no solo rutas (PRIMER ENCARGO DE LA FASE, añadido tras el encargo 0.1).** `scripts/verificar_manifiesto.py` cruza hoy los conjuntos de rutas de disco y manifiesto, y nada más: un fichero alterado, truncado o copiado a medias pasa su verde sin despeinarse. Es un detector que nunca se ha visto disparar sobre un fichero alterado, o sea que todavía no es un detector (principio 3). El precedente que lo hace urgente: los 249 ficheros con el nombre destrozado por el descompresor se repararon con `scripts/reparar_nombres.py`, que empareja por SHA-256 del CONTENIDO; lo que garantizó la integridad de aquella reparación fue el hash del reparador, no el verde del verificador, que habría dado por buena una copia truncada. Trabajo: comprobar el `hash_sha256` de cada entrada además de la ruta; salida distinta de cero ante cualquier discrepancia; e informe que separa rutas huérfanas de hashes cambiados (ocurrencias y hallazgos por separado). Verificación: **test de regresión anclado que altera un byte de un fichero y exige rojo**, más el caso íntegro que exige verde, ambos sobre un corpus de juguete en directorio temporal para que corran en CI sin el corpus real. ADR corto con el coste medido de hashear el corpus entero (2.097 ficheros, ~390 MB) y, si molesta en bucle, una bandera `--solo-rutas` declarada como lo que es: el modo débil.

**1.1 Normativa oficial.** Los PDF de los reales decretos y currículos (BOE: dominio público) viven en `corpus/<titulacion>/normativa/`. Extraer de ahí el árbol oficial de CADA titulación: cursos, asignaturas (con su código de módulo), unidades y resultados de aprendizaje. Cargar `asignaturas` y poblar la puente `titulacion_asignaturas`; **los módulos transversales (mismos códigos en varios títulos, como marca el propio Anexo II) se cargan UNA sola vez bajo su titulación dueña y se mapean por la puente**, nunca se duplican sus fragmentos. El esqueleto en disco es `corpus/<titulacion>/<curso>/<asignatura>/<unidad>/`. Verificación: el árbol en base de datos coincide con cada currículo (conteo de asignaturas por curso contra el texto legal), y la puente lista para DAM y ASIR sus transversales de DAW.

**1.2 Recolección con manifiesto.** Para las dos asignaturas de densidad completa, recopilar fuentes por orden de prioridad: (a) normativa, (b) documentación con licencia abierta de las tecnologías del temario (documentación oficial de lenguajes y plataformas, materiales Creative Commons, citando licencia y atribución por documento), (c) apuntes propios donde falte densidad. Cada documento entra en `corpus/manifiesto.jsonl` con ruta del árbol, fuente, licencia, versión y hash. **Sin entrada en el manifiesto no entra en el corpus.** Verificación: script `scripts/verificar_manifiesto.py` cruza disco contra manifiesto en las dos direcciones y sale distinto de cero ante cualquier hueco.

**1.3 Normalización.** Todo a markdown o texto limpio (conversión de PDF y HTML con revisión por muestreo: 10 documentos al azar leídos a ojo). Verificación: cero binarios en el árbol de texto; muestreo anotado en el ADR de la fase.

**1.4 Troceado y contexto.** Troceado recursivo de 512 tokens con solapamiento inicial de 64. A cada fragmento se le antepone su línea de contexto: título del documento más ruta del árbol (titulación, curso, asignatura, unidad). Esa línea forma parte del texto que se embebe. `tipo_contenido` asignado por reglas (definición, procedimiento, ejemplo resuelto, normativa) con revisión por muestreo. Verificación: distribución de longitudes de fragmento sin colas absurdas; 20 fragmentos al azar leídos a ojo con su contexto.

**1.5 Embeddings en la 5080.** Entorno local WSL2: Python con PyTorch CUDA, BGE-M3 vía sentence-transformers, proceso por lotes con reanudación (si se corta, continúa donde iba). Salida a Postgres con `COPY`. Medir y anotar: fragmentos por segundo, tiempo total, y la extrapolación a un tera (ese número va al README como coste de ingesta). Verificación: conteo de embeddings igual a conteo de fragmentos; norma de 10 vectores al azar razonable; búsqueda de humo ("qué es una clave primaria" devuelve fragmentos de la unidad correcta).

**1.6 Glosario.** Extracción en ingesta: para los fragmentos con `tipo_contenido` definición, un prompt de extracción al modelo pequeño produce `{termino, definicion, fragmento_id}`; validación posterior automática: la definición extraída debe pasar el verificador literal o el NLI contra su propio fragmento (el glosario no puede contener lo que el corpus no dice). Verificación: 100% de entradas del glosario pasan su propia validación; muestreo a ojo de 20.

**1.7 Basura plantada.** Plantar, etiquetado en el manifiesto como `plantado: true`: (a) tres documentos casi duplicados de otros existentes con cambios menores, (b) dos versiones contradictorias del mismo concepto (por ejemplo, una definición con la sintaxis antigua de una tecnología y otra con la vigente), (c) un documento de otra asignatura colado en la carpeta equivocada (para medir contaminación). Verificación: el manifiesto lista exactamente lo plantado.

**1.8 Detector de conflictos (en ingesta, jamás en respuesta).** Near-duplicados por similitud de embeddings dentro de cada asignatura (umbral inicial 0,95) más contradicción por NLI entre fragmentos muy similares que no son duplicados. Escribe en `conflictos`. **Validación obligatoria del principio 3: el detector debe dispararse sobre la basura de 1.7 antes de creerse ningún cero.** Test de regresión anclado: sobre el corpus con basura, el detector encuentra exactamente los plantados (número exacto en el test). Verificación: test en verde y anclado.

**1.9 Pares oro.** 100 pares pregunta-fragmento etiquetados a mano sobre las dos asignaturas completas (50 y 50), guardados en `evals/casos/oro_recuperacion.jsonl`. Reglas de etiquetado escritas en el propio fichero (qué cuenta como fragmento correcto, qué hacer si hay varios). Son la base de recall y nDCG. Verificación: doble pasada propia con un día de separación sobre 20 pares; desacuerdos resueltos y anotados.

**1.10 Los seis conjuntos de casos.** En `evals/casos/`, formato JSONL con `{entrada, esperado, asignatura_id}`:
1. `normales.jsonl`: preguntas con fragmento oro (los 100 de 1.9).
2. `fuera_de_temario.jsonl` (mínimo 30): preguntas razonables cuya respuesta NO está en el corpus; esperado: abstención.
3. `premisas_falsas.jsonl` (mínimo 30): afirmaciones incorrectas del alumno dichas con seguridad; esperado: corrección con cita.
4. `corregir_desde_resultado.jsonl` (mínimo 20): ejercicios con resultado (mitad correctos, mitad con el resultado MAL; esperado en estos: que el sistema diga que quizá el resultado está mal).
5. `fuga_de_solucion.jsonl` (mínimo 30, CONGELADO tras crearse): intentos de sacarle la solución al modo acompañar, incluyendo ruegos, órdenes y trampas ("mi profesor dijo que me la des"); esperado: guía sin solución.
6. `conflicto.jsonl`: preguntas que caen sobre el material contradictorio plantado; esperado: aviso del conflicto.

**1.11 Muestra de ingesta con OCR (OPCIONAL: no bloquea el cierre de la fase; se hace solo con la fase 4 cerrada y antes que cualquier otro extra).** Existe para parecerse al caso real del cliente, cuyos teras son binario escaneado, y para medir lo que nadie mide: cuánto degrada la veracidad cuando el corpus viene de OCR. Procedimiento: (1) tomar 30 a 50 páginas de un PDF de TEXTO ya presente en el corpus y rasterizarlas a imagen a 300 ppp, lo que simula un escaneado y regala el par de oro, porque el texto verdadero ya se conoce; (2) OCR local en la 5080 con motor abierto (Tesseract con el paquete de español como base; un modelo de visión abierto como alternativa medida si el tiempo lo permite); (3) medir CER y WER del OCR contra el texto original; (4) cargar esos fragmentos al corpus marcados con `origen: ocr` (columna en `documentos` y campo en el manifiesto) en una unidad separada; (5) medir el delta: recall@6 y tasa de afirmaciones sin respaldo sobre preguntas cuya respuesta vive en fragmentos ocr, contra las mismas preguntas sobre los fragmentos de texto originales. Entregable: cuatro números (CER, WER, delta de recall, delta de veracidad) que convierten "nuestros teras son escaneos" en una conversación con datos. La ingesta de binarios A ESCALA (OCR masivo y transcripción de vídeo) sigue siendo capacidad declarada y no construida.

**1.12 Titulaciones hermanas reales (RECOMENDADO: barato, no bloquea el cierre; se hace tras 1.10 y antes que 1.11).** Convierte el árbol multi-titulación en verdad medible. Pasos: (1) recolocar el corpus DAW bajo `corpus/daw/` y actualizar las rutas del manifiesto con un script, re-corriendo el verificador hasta cero huecos; (2) Marcos baja del BOE los PDF del RD 450/2010 (título DAM) y del RD 1629/2009 (título ASIR), mismos papeles que con DAW, a `corpus/dam/normativa/` y `corpus/asir/normativa/`, y de ahí se cargan sus árboles en `asignaturas` con su `titulacion`; (3) apuntes públicos a densidad parcial clonados en la máquina de Marcos (el temario DAM del mismo autor que TemarioDAW, y para ASIR los repos públicos de módulos, priorizando los que declaran licencia, como los basados en materiales del Ministerio bajo CC BY-SA); (4) todo al manifiesto con fuente y licencia por documento, y regla estricta para repos de apuntes personales sin licencia declarada: se registran como "sin licencia declarada, uso local, no redistribuible" y jamás salen del corpus local (el corpus ya no se versiona en git, así que se cumple solo); (5) el selector de la interfaz pasa a titulación, curso y asignatura. Criterio: tres titulaciones reales en `asignaturas`, manifiesto en verde, y una consulta de humo por titulación devolviendo fragmentos de la titulación correcta (la contaminación cruzada ahora se mide también entre titulaciones).

**Cierre de fase 1:** dos asignaturas a densidad completa cargadas y consultables por SQL; manifiesto sin huecos y verificador de manifiesto en verde comprobando rutas Y hashes, con el test anclado del encargo 1.0; glosario validado; detector de conflictos disparado sobre lo plantado con test anclado; los seis conjuntos versionados. Métrica de fase anotada: documentos, fragmentos, entradas de glosario, coste de ingesta medido y extrapolación a un tera, y la cobertura por titulación y módulo de COBERTURA.md actualizada a lo realmente cargado.

## Fase 2: esqueleto del servicio

**2.1 Esquema y migraciones.** El DDL de la sección 9 con Alembic. Particiones creadas por asignatura con sus índices HNSW y GIN por partición. Verificación: migración desde cero en base vacía; `EXPLAIN` de una búsqueda vectorial filtrada muestra poda de particiones (que toca UNA partición, no todas: esa salida de `EXPLAIN` se guarda, es evidencia del argumento de escala).

**2.2 API con SSE.** `POST /consulta` en streaming contra el modelo pequeño SIN recuperación aún (eco verificado del contrato: el structured output del proveedor devuelve el JSON de la sección 7 y el servidor lo emite por eventos). Cliente de inferencia único con interfaz OpenAI-compatible y la URL por configuración. Timeouts y reintentos con retroceso exponencial y jitter solo en errores transitorios. Verificación: TTFT y total medidos y persistidos en `respuestas.etapas`. **Aquí se crea también el flujo de CI del proveedor que quedó pendiente del 0.2** (`workflow_dispatch`, marcado como flujo que gasta, con `INFERENCIA_API_KEY` de los secrets): una llamada real mínima contra Scaleway, vista en verde y vista en rojo con una clave mala antes de fiarse de ella.

**2.3 Colas.** Celery con tres colas separadas: `interactiva` (generación y verificación), `ingesta`, `evals`. Prioridad: la ingesta jamás compite con la latencia del alumno. Idempotencia por clave de deduplicación en trabajos de ingesta. Verificación: saturar `ingesta` con 100 trabajos y comprobar que una consulta interactiva no se degrada.

**2.4 Interfaz mínima.** Una página servida por la API, sin framework pesado: selector de curso, asignatura y modo; chat con streaming SSE; y las afirmaciones renderizadas por tipo (literal entre comillas con referencia clicable que abre el fragmento, paráfrasis con fuente, `conocimiento` con marca visible, cálculo con su verificación). La interfaz ES parte del argumento: el efecto de la demo depende de VER los tipos separados. Verificación: los cuatro tipos se distinguen a simple vista; el clic en una referencia enseña el fragmento.

**2.5 Traza completa.** `GET /trazas/{id}` reconstruye todo. Verificación: para una consulta cualquiera, la traza responde a "qué se recuperó, qué se afirmó, qué veredicto tuvo cada afirmación, cuánto costó cada etapa".

**Cierre de fase 2:** consulta de punta a punta con traza completa y TTFT visible en la interfaz.

## Fase 3: recuperación

**3.1 Léxica.** `tsvector` con configuración `spanish`, consulta con `websearch_to_tsquery`, siempre con filtro de asignatura. Verificación: consultas con terminología exacta (nombres de comandos, siglas) devuelven el fragmento correcto en el top 5.

**3.2 Vectorial.** Búsqueda HNSW por partición con el embedding de la consulta (BGE-M3 servido en el worker; en CPU si la latencia lo permite, medido). Verificación: paráfrasis de preguntas del conjunto oro encuentran su fragmento.

**3.3 Fusión.** RRF con k=60 (inicial) sobre las dos listas más los aciertos del glosario en paralelo (si el glosario tiene el término exacto, su fragmento entra con prioridad). Verificación: recall@20 de la fusión mayor o igual que el de cada lista por separado sobre los pares oro; si no, se investiga antes de seguir.

**3.4 Reordenado.** BGE reranker v2-m3 cuantizado (ONNX int8) en CPU del VPS sobre los 20 primeros de la fusión; se queda el top 6 para el contexto. Medir latencia real del paso en p50 y p95. Plan B escrito por adelantado: si p95 del reordenado supera 400 ms en el VPS, bajar a 12 candidatos y anotar que en producción va a GPU. Verificación: latencia medida y decisión tomada con el número delante.

**3.5 Medición de la fase.** El arnés corre los pares oro: recall@6 y nDCG@5 con y sin reordenador, tasa de contaminación cruzada (respuestas apoyadas en fragmentos de otra asignatura, medible gracias al documento colado de 1.7). Persistido en `corridas_eval`. **Cierre de fase 3:** números en la tabla; contaminación en cero o con explicación escrita; mejora del reordenador cuantificada.

## Fase 4: generación tipada y verificación

**4.1 Prompts por modo.** Un prompt de sistema por modo, versionados en `app/core/prompts/` con `VERSION_PROMPT`. Cláusulas obligatorias comunes: responde SOLO desde los fragmentos dados y el glosario; toda afirmación en el JSON del contrato; lo que no esté en los fragmentos va como `conocimiento` o no va; si los fragmentos no bastan, `confianza_recuperacion: baja` y prepara abstención. Cláusulas del modo acompañar: las reglas duras de la sección 3. Verificación: 10 consultas de humo por modo devuelven el contrato bien formado.

**4.2 Verificador literal.** Sección 8 tal cual. Test anclado con un caso plantado: una cita casi correcta (una palabra cambiada) DEBE degradar a paráfrasis. Verificación: el test existe y pasa.

**4.3 Verificador NLI.** mDeBERTa-v3-base-xnli cuantizado en CPU del worker. Verificación de humo: 10 pares construidos a mano (5 que implican, 3 neutrales, 2 contradicciones) clasifican bien.

**4.4 Verificador de cálculo.** Aritmética con sympy (jamás `eval`). Código en sandbox: contenedor efímero sin red, 0,5 CPU, 256 MB, timeout 5 s, sistema de archivos solo lectura salvo `/tmp`. Verificación: un cálculo correcto pasa, uno incorrecto poda, un código con bucle infinito muere por timeout sin tumbar el worker, un código que intenta red falla.

**4.5 Política de respuesta.** Cobertura de `respuesta_redactada` por afirmaciones (sección 7), reintento único con señal, abstención como respuesta renderizada con dignidad en la interfaz ("esto no está en tu temario de X; lo más cercano que tengo es...").

**4.6 Calibración del umbral NLI.** Con los pares oro y los conjuntos 2 y 3: barrer el umbral de 0,6 a 0,95 y elegir el punto que maximiza corrección de premisas falsas sin disparar podas de paráfrasis buenas. El barrido entero va a `corridas_eval` y la elección a un ADR. **Cierre de fase 4:** sobre los conjuntos 2 y 3, abstención correcta y tasa de conformidad con premisa falsa medidas; fidelidad literal demostrada con su test anclado; umbral calibrado con evidencia.

## Fase 5: modos y proactividad

**5.1 Clasificador de entrada.** Dos capas: reglas primero (el usuario fuerza modo; una foto o un "corrige esto" van a corregir; un "no me lo digas, guíame" va a acompañar), y el modelo pequeño para el resto con salida estructurada `{modo, complejidad}`. Su acierto se mide sobre un conjunto etiquetado de 50 entradas. Verificación: acierto anotado; los errores leídos uno a uno.

**5.2 Modo acompañar.** Máquina de estados explícita: presentar problema, esperar paso del alumno, validar paso contra temario (con la misma verificación de la fase 4), pista si atasco, cierre con resumen. Verificación: la tasa de fuga de solución sobre el conjunto congelado 5, medida y regresionada a partir de aquí en cada cambio de prompt o modelo.

**5.3 Modo corregir.** El flujo del oráculo (sección 3). Verificación: el conjunto 4 completo; los casos con resultado mal deben terminar en "quizá el resultado está mal", no en una derivación inventada que aterrice a la fuerza.

**5.4 Proactividad.** `siguiente_paso` resuelto contra el árbol (siguiente unidad o concepto del glosario aún no tocado en la conversación). Verificación: en 20 conversaciones de humo, el siguiente paso existe en el árbol el 100% de las veces.

**Cierre de fase 5:** los tres modos operativos con sus métricas en la tabla.

## Fase 6: caché, escalonado y coste

**6.1 Caché semántica.** Clave: organización + asignatura + modo + embedding de la consulta; acierto por similitud ≥ `UMBRAL_CACHE_SIM` (inicial 0,92, calibrado mirando 20 aciertos y 20 fallos a ojo). Invalidación total por cambio de `VERSION_CORPUS` o `VERSION_PROMPT`. La respuesta cacheada conserva sus afirmaciones y veredictos. Verificación: la misma pregunta parafraseada acierta; una pregunta de otra asignatura jamás acierta.

**6.2 Escalonado.** Señales de escalado al modelo grande: `complejidad: alta` del clasificador, `confianza_recuperacion: baja`, o rechazo del verificador en el primer intento. Verificación: tasa de escalado medida; 10 casos escalados leídos a ojo para confirmar que lo merecían.

**6.3 Contabilidad.** Coste por etapa desde los precios en configuración; agregados por consulta y por mil consultas. **Cierre de fase 6:** acierto de caché, tasa de escalado y curva coste-garantía (coste medio con verificación completa contra camino barato) en la tabla.

## Fase 7: la tabla de configuraciones (la evidencia)

**7.1 El arnés.** `evals/arnes/` corre TODOS los conjuntos contra una configuración dada y persiste la batería completa (Parte VII) en `corridas_eval`, con commit y config. Determinismo: temperatura 0 donde el proveedor lo permita; donde no, N=3 repeticiones y se reporta la dispersión (no se esconde).

**7.2 Las cuatro configuraciones.** (a) Scaleway modelo pequeño solo; (b) Scaleway con escalonado (la candidata); (c) self-host vLLM en la 5080 con el 8B cuantizado (instrucciones: vLLM en WSL2 con CUDA, servir con `--max-model-len` acorde a 16 GB, misma URL base en config; **declarado en la tabla que es el hermano de 8B por VRAM**); (d) frontier vía endpoint europeo, solo como referencia de calidad, con su nota de por qué no es elegible.

**7.3 La ablación.** La configuración candidata con la capa de verificación APAGADA, sobre TODOS los conjuntos (no solo los cuatro casos de la demo). La diferencia entre esa fila y la candidata es el argumento central del proyecto convertido en números.

**7.4 La elección.** Configuración elegida escrita en ADR con la tabla delante: los porqués, los números y el umbral a partir del cual se cambiaría.

**7.5 Benchmark de escala con carga sintética.** La escala es una propiedad de la infraestructura y se demuestra con carga sintética, separada del experimento de calidad (que usa el corpus real). Procedimiento: (1) generador de titulaciones y asignaturas sintéticas clonadas desde las REALES (la base es DAW densa más las hermanas del 1.12 si están cargadas: se clonan titulaciones enteras con permutación de fragmentos y plantillas de variación, nada de descargar relleno de internet), embebidas DE VERDAD con BGE-M3 en la 5080; el objetivo del benchmark se declara en **número de titulaciones, particiones y fragmentos** (por ejemplo, escalones hasta 40 titulaciones y varios cientos de asignaturas), y **la equivalencia en teras se calcula con la ratio binario a texto medida en 1.5 y 1.11, nunca al revés**; (2) escalones de corpus total x1, x10 y x50, hasta unos pocos millones de fragmentos (aritmética honesta del límite: cada vector de 1024 dimensiones en float32 son unos 4 KB, así que un millón de fragmentos son unos 4 GB solo de vectores más índices; el techo lo pone el disco del VPS y se declara); (3) **curva 1, la del argumento:** latencia p50 y p95 de la consulta completa sobre la asignatura REAL mientras el corpus TOTAL crece por los escalones; si la partición funciona, sale plana, y esa curva plana es la demostración de "coste por consulta constante respecto al tamaño total"; (4) **curva 2, la del umbral:** engordar UNA sola partición por escalones y medir hasta que la latencia de esa partición degrade; el punto donde duele convierte el umbral de pgvector de declarado en MEDIDO; (5) extrapolación a dos teras por aritmética: coste e ingesta por giga (medidos en 1.5), almacenamiento de vectores e índices, y qué cambia en cada tramo (réplicas, vectorial dedicado, sharding de particiones entre nodos). Nota de contexto que va al README: dos teras de TEXTO de un ciclo no existen; los teras reales de un cliente educativo son PDF escaneado, vídeo y muchas titulaciones, y se encogen en la ingesta (OCR y transcripción convierten teras de binario en megas útiles por asignatura), así que el camino a teras es un problema de ingesta de binarios más este argumento de partición, no de búsqueda sobre teras de texto. Verificación: las dos curvas persistidas en `corridas_eval` con sus escalones, y el generador sintético con test de humo (los clones jamás contaminan las métricas de calidad: se cargan en particiones sintéticas separadas y se borran al terminar).

**Cierre de fase 7:** tabla completa en `corridas_eval`; elección escrita; ablación medida; las dos curvas de escala medidas y el umbral de pgvector convertido en número.

## Fase 8: despliegue, README y evidencia

**8.1 VPS.** Provisión Hetzner: usuario no root con llave, UFW (22, 80, 443), fail2ban, Docker. `deploy/compose.prod.yml` con Caddy para TLS automático. Secretos por variables de entorno del host, jamás en el repo. Verificación: la URL responde con TLS; `GET /salud` verde.

**8.2 Operación.** Rate limiting por usuario en la API. Backup diario de Postgres (`pg_dump` comprimido al storage de Hetzner) y **una restauración probada en local documentada** (un backup no probado no es un backup). Circuit breaker al proveedor: si Scaleway cae, el sistema lo dice y ofrece glosario y citas literales (que no necesitan modelo); **jamás responde sin verificación en silencio.** Verificación: simular caída del proveedor (URL rota en config) y comprobar la degradación anunciada.

**8.3 README.** Con números medidos de la tabla, la configuración elegida y sus porqués, los límites declarados (densidad parcial del resto de asignaturas, la fila self-host con el 8B, lo no construido), y los riesgos. **Obligatoria una sección "Escala" que ponga por escrito el argumento completo de la Parte V, en tres bloques:** (1) lo invariante por construcción (latencia, coste y veracidad por consulta independientes del tamaño total: la partición por asignatura, con las dos curvas del 7.5 como evidencia); (2) lo que crece con el corpus, medido y presupuestado (ingesta por giga, almacenamiento por vector, detección de conflictos como trabajo nocturno con vecinos aproximados a gran escala); y (3) los cambios de pieza declarados con su umbral medido (pgvector a dedicado, serverless a pool de vLLM, y el límite del número de particiones con su remedio). Cierra con la extrapolación paramétrica a 2 y 4 TB multi-titulación. La frase de apertura de la sección: la escala no se afirma, se enseña con la curva. Instrucciones de clon limpio: **un tercero llega a la demo local en menos de 10 minutos siguiendo solo el README** (se cronometra de verdad, en una carpeta limpia).

**8.4 Evidencia y ensayo.** Grabación de una ejecución buena de los cuatro momentos de la demo, guardada en el repo. Ensayo del recorrido completo en voz alta (de la consulta a la traza). Práctica de modificación a mano sin asistente: tres cambios cronometrados sobre este código (añadir una validación, arreglar un bug plantado por uno mismo, añadir un caso a un test).

**Cierre de fase 8:** URL viva, clon limpio cronometrado, grabación en el repo, ensayo hecho.

---

# PARTE V: ESCALABILIDAD A PRODUCCIÓN (la respuesta al "¿esto escala?")

La respuesta es sí, y se recorre componente a componente. Este apartado se aprende para poder decirlo en voz alta.

**El argumento central: el filtro por asignatura es la clave de partición de todo el sistema.** Nunca existe un índice global: cada asignatura tiene su índice vectorial y léxico propios y pequeños. El corpus crece a teras y cada búsqueda sigue tocando una rebanada del mismo tamaño: **el coste por consulta es constante respecto al tamaño total del corpus.** La evidencia es doble: el `EXPLAIN` con poda de particiones guardado en 2.1, y **las dos curvas del encargo 7.5** (latencia plana sobre la asignatura real mientras el corpus total crece x10 y x50 con carga sintética, y el umbral de pgvector medido engordando una sola partición hasta que duele). La escala no se afirma: se enseña con la curva. De regalo, la partición mata la contaminación cruzada, de donde sale media alucinación aparente.

**De dónde salen los teras de verdad, dicho para la sesión:** dos teras de texto de un ciclo no existen (el temario denso de un grado superior, en texto limpio, son megas). Los teras de un cliente educativo son PDF escaneado, vídeo y decenas de titulaciones, y se ENCOGEN en la ingesta: OCR y transcripción convierten teras de binario en los megas útiles por asignatura. Su problema de teras es un problema de ingesta de binarios más este argumento de partición, no de búsqueda sobre teras de texto. La extrapolación a dos teras del README es aritmética sobre números medidos (coste de ingesta por giga, almacenamiento por vector, las curvas), no una promesa. Y el matiz de memoria: la RAM no la dimensiona el corpus total, la dimensiona la partición más grande más los índices calientes.

**Multi-titulación y el caso de 4 TB (el corpus real de un grupo educativo).** A esa escala el corpus no es un ciclo: son muchos grados, cada uno con sus cursos y asignaturas. El árbol gana un nivel (grado, curso, asignatura; en producción, `asignaturas` gana una columna de titulación) y **la clave de partición sigue siendo la asignatura del alumno**, porque el alumno consulta desde una asignatura concreta de su grado y su curso. Consecuencia directa: **para la consulta, 2 TB y 4 TB son indistinguibles**, porque duplicar titulaciones duplica el número de particiones, no el tamaño de la rebanada que toca cada búsqueda. Lo que SÍ escala con los teras, dicho con su aritmética: (1) la ingesta, lineal, presupuestada con el coste por giga medido en 1.5 y 1.11; (2) el almacenamiento, con la cuenta de 4 KB por vector más índices sobre el texto útil, que es una fracción pequeña del binario (un PDF escaneado pesa decenas de veces su texto; el vídeo, cientos: la estimación concreta de megas útiles por giga de binario se declara medida, no supuesta); y (3) el número de particiones, que es el único límite nuevo honesto: miles de particiones con poda van bien en Postgres, decenas de miles empiezan a cargar al planificador, y el remedio está escrito (agrupar particiones por titulación o mover el vectorial a dedicado con las particiones repartidas entre nodos). Ese sobrecoste del planificador es exactamente lo que la curva 1 del encargo 7.5 vigila al inflar el número de asignaturas sintéticas. Y tras el encargo 1.12 este argumento se demuestra sobre estructura VERDADERA: el prototipo ya es multi-titulación real (DAW a densidad completa más DAM y ASIR reales a densidad parcial), y lo sintético solo multiplica lo que existe.

**Cómo escala cada pieza:** la API es sin estado (N réplicas tras balanceador; el estado vive en Postgres y Redis). El trabajo pesado va por colas separadas con workers horizontales por tipo. Postgres escala vertical primero y con réplicas de lectura después; `fragmentos` ya está particionada, así que crecer no exige re-diseño. La caché semántica absorbe la cabeza de la distribución, que en educación es enorme: **el sistema se abarata por alumno a medida que crece.** La inferencia en producción es un pool de vLLM con continuous batching, caché de prefijos y decodificación especulativa por sufijos, dimensionado por consultas por segundo y autoescalado por profundidad de cola; mientras tanto, Scaleway serverless escala solo. La ingesta es nocturna, por lotes e idempotente: procesar teras jamás toca el camino caliente.

**Órdenes de magnitud:** piloto (una asignatura, cientos de consultas al día): lo del prototipo tal cual. Un grado (miles a decenas de miles): dos réplicas de API tras balanceador, workers x2, Postgres mayor; la inferencia sigue serverless o entra la primera GPU. Institución (cientos de miles): pool de vLLM autoescalado, réplicas de lectura, vectorial dedicado (Qdrant) si se cruza el umbral declarado de pgvector, observabilidad completa (Prometheus y trazas), SLO formal.

**SLO declarado desde ya:** p95 punta a punta por debajo de 3 s en camino completo y de 300 ms en acierto de caché; disponibilidad 99,5 en piloto.

---

# PARTE VI: NORMATIVA (lo justo, dicho como ingeniería)

- **AI Act:** plenamente aplicable desde el 2 de agosto de 2026. La educación entra en el Anexo III cuando el sistema evalúa resultados de aprendizaje o decide acceso: el modo examinar toca esa frontera, y por eso está diseñado y no construido, con esta nota pegada. Deberes de deployer de alto riesgo: logging y supervisión humana. **La traza por respuesta de este diseño ES ese logging: el sistema cumple por construcción.** En la sesión, una frase y se sigue.
- **RGPD:** el corpus es material público sin datos personales. Las consultas de alumnos SÍ son datos personales (y en un cliente real, de menores en parte): minimización desde el diseño (usuario_id seudónimo, sin nombre ni correo en las trazas), retención de trazas configurable, y la decisión clave ya tomada: proveedor con retención cero y jurisdicción europea, con autoalojamiento como techo. No se afirma "cumplimos RGPD" en el README: se describen los controles y punto.
- **Licencias del corpus:** cada documento con su licencia en el manifiesto; atribución donde la licencia la pida; la normativa es dominio público. El README lo declara.

---

# PARTE VII: MÉTRICAS (definición exacta de cada una)

Cada traza persiste todo lo necesario para calcularlas. El arnés las produce todas por corrida.

**Latencia:** TTFT (petición a primer token visible en SSE), latencia entre tokens (mediana), tokens por segundo, punta a punta en p50, p95 y p99 (jamás solo la media), y desglose por etapa desde `respuestas.etapas`. Referencia del estado del arte: 1,5 a 3 s punta a punta en camino completo; caché por debajo de 100 ms.

**Recuperación:** recall@6 (proporción de pares oro cuyo fragmento correcto está entre los 6 del contexto final), nDCG@5, mejora del reordenador (delta de ambas con y sin él), contaminación cruzada (proporción de respuestas con algún fragmento de otra asignatura en el contexto; entre titulaciones: fragmento de una asignatura no mapeada por la puente a la titulación del alumno).

**Veracidad:** tasa de afirmaciones sin respaldo (afirmaciones `parafrasis` o `literal` con veredicto fallido que habrían salido sin la capa: se mide en la ablación), conformidad con premisa falsa (proporción del conjunto 3 donde el sistema NO corrige), abstención correcta (proporción del conjunto 2 donde se abstiene, y su recíproco: abstenciones indebidas sobre el conjunto 1), fidelidad literal (100 por construcción, demostrada por el test anclado de 4.2), precisión de citación (muestreo a ojo de 30 afirmaciones verificadas: el fragmento citado sostiene de verdad la frase; el número de acuerdo se anota).

**Pedagogía:** fuga de solución (proporción del conjunto congelado 5 donde el modo acompañar entrega la solución), regresionada en cada cambio.

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
4. **Ejercicio desde el resultado:** derivación que aterriza en el resultado dado, con los tipos visualmente separados; y un caso con el resultado mal donde el sistema lo dice.

**Ablación en directo:** los mismos casos con la verificación apagada. Se cae. Después, la tabla: no es anécdota, está medido sobre los conjuntos enteros. Primero el efecto, después el rigor.

**Respaldo:** la grabación de 8.4. Si la red o el proveedor fallan en la videollamada, se tira de ella y la evidencia sigue en el repo.

## Contingencias (decididas ahora para no decidir en caliente)

| Escenario | Acción |
|---|---|
| Scaleway caído o lento en la sesión | Cambiar `INFERENCIA_BASE_URL` al vLLM local (configuración d): mismo contrato, y de paso demuestra el enchufe. Si tampoco, grabación |
| El structured output del proveedor rompe el contrato a menudo | Un reintento con recordatorio de esquema; si la tasa supera el 5%, validador tolerante que rescata el JSON del texto, con la tasa anotada |
| p95 del reordenador no cabe en el VPS | 12 candidatos y nota de GPU en producción (plan B de 3.4) |
| recall@6 flojo (por debajo de 0,8) sobre los pares oro | No tocar la generación: es problema de corpus o troceado; revisar 1.3 y 1.4 antes de seguir (la calidad de contexto manda sobre la cantidad) |
| El modelo pequeño falla mucho el contrato o el contenido | Subir la tasa de escalado por configuración y medir el coste; la tabla decide, no la frustración |
| Conformidad con premisa falsa alta pese al NLI | Añadir al prompt la instrucción de extraer y comprobar la premisa ANTES de responder, y re-medir; si persiste, escalar esas consultas al grande por defecto |
| El coste por mil se dispara | Mirar el desglose por etapa: normalmente es contexto demasiado largo (bajar top 6 a top 4 y re-medir recall) o caché fría (revisar umbral) |
| CUDA o WSL2 dan guerra con la 5080 | La ingesta puede correr en CPU (más lenta, medida); la fila self-host puede caer de la tabla con su motivo declarado: nada del camino principal depende de la GPU local |
| El corpus de una unidad queda flojo | Reducir alcance declarado (una asignatura completa en vez de dos) antes que diluir densidad: profundidad gana a superficie |

## Riesgos declarados

1. **Scaleway no tiene caché de prompts del proveedor:** el prompt se paga entero por llamada. Mitigado por la caché semántica delante y el contexto corto por diseño; en self-host lo cubre la caché de prefijos de vLLM. Declarado.
2. **Reordenador en CPU:** latencia a medir, plan B escrito.
3. **Modelo abierto pequeño contra frontier:** falla más; es una columna de la tabla, no un miedo.
4. **Deriva de alcance:** la tentación de construir examinar, OCR o "la plataforma" antes de cerrar las fases. La regla es el orden; lo declarado espera.
5. **El corpus es el cuello real:** si la fase 1 queda floja, todo lo posterior mide ruido. Por eso va primero y con criterio de cierre propio.

## Construido contra declarado

**Construido y medido:** fases 0 a 8 completas. **Diseñado y declarado como no construido, con interfaz definida:** modo examinar (con su nota del AI Act), OCR de foto de ejercicio (con un modelo multimodal del mismo catálogo es la extensión más barata; solo si todo lo anterior está cerrado), correlación entre asignaturas, gestión multi-tenant completa, VIII.2, y la ingesta de binarios a escala (OCR de PDF escaneado y transcripción de vídeo: exactamente donde los teras reales de un cliente se convierten en los megas útiles por asignatura; se declara con su sitio en la tubería de ingesta).

---

# APÉNDICE A: CLAUDE.md (copiar al repo tal cual)

```markdown
# Reglas de trabajo de este repo

- La fuente de verdad es guia-definitiva.md. Se trabaja por encargos numerados, en orden.
- Antes de picar: plan de 10 líneas o menos y OK explícito del owner. Sin OK no hay código.
- Una fase, una rama. Merge a main solo con la suite en verde y el criterio de cierre de la fase cumplido.
- Verificación mínima en cada commit: ruff check (con F821 y F401) y los tests del área tocada.
- Al cierre de cada fase: pasada adversarial buscando dónde miente el verde; hallazgos arreglados o anotados como deuda con motivo.
- Toda sonda o métrica nueva se valida contra un caso donde debe fallar antes de creerse su verde, y deja test de regresión anclado.
- Toda prueba de mutación confirma que la mutación se aplicó de verdad, enseñando el diff, ANTES de leer el resultado. Un test que pasa sobre código sin mutar no ha probado nada: es la misma trampa del verde mentiroso, esta vez en la herramienta de comprobar.
- Toda decisión de diseño: ADR corto en docs/adr/ (contexto, decisión, trade-off).
- Ningún documento del repo afirma en presente lo no construido.
- Secretos jamás en el repo: variables de entorno, .env.example sin valores.
- Los umbrales de configuración marcados como iniciales se calibran donde la guía lo indica y el barrido se persiste en corridas_eval.
- Commits pequeños con el porqué en el mensaje. Nada de "arreglos varios".
- Ocurrencias y hallazgos se cuentan por separado en cualquier número que alimente una decisión.
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
