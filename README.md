# Veridica

Un profesor por asignatura sobre temario real que solo afirma lo que puede sostener: cita literal
comprobada carácter a carácter, paráfrasis verificada contra el fragmento fuente, cálculo recalculado
y silencio honesto cuando la respuesta no está en el material. La tesis del proyecto: **la honestidad
del sistema no depende de la brillantez del modelo, depende de la capa de verificación.**

> **README provisional.** El README definitivo, con los números medidos, la configuración elegida y
> la sección "Escala", lo produce el **encargo 8.3**. Hasta entonces este fichero solo declara el
> estado real del repo. Nada de lo que aquí no aparezca como construido lo está.

## Estado (12 de agosto de 2026)

**Fases 0 y 1 cerradas y en `main`.** Hay corpus ingerido, troceado, embebido y medido, con sus
puertas de calidad; no hay todavía recuperación, generación, verificación ni métricas de respuesta.
Lo que existe hoy:

| Qué | Dónde | Estado |
|---|---|---|
| Playbook y fuente de verdad | [guia-definitiva.md](guia-definitiva.md) | escrito |
| Reglas de trabajo | [CLAUDE.md](CLAUDE.md) | escritas |
| Corpus de las tres titulaciones (DAW, DAM, ASIR) | `corpus/` (fuera de git) | descargado, normalizado y en manifiesto |
| Manifiesto del corpus | [corpus/manifiesto.jsonl](corpus/manifiesto.jsonl) | **2.413 entradas** (2.106 originales + 307 derivados); verificador de rutas y hashes en verde (~1 s) |
| Árbol oficial del BOE de las tres titulaciones | [corpus/arbol_oficial.jsonl](corpus/arbol_oficial.jsonl) | 536 nodos con su referencia legal, y su muestreo humano |
| Índice de fragmentos | `corpus/fragmentos.jsonl` (fuera de git) | **11.483 fragmentos** de 512 tokens con su línea de contexto, tras la puerta de admisión |
| Embeddings | `corpus/embeddings/` (fuera de git) | **11.483 vectores** BGE-M3 con la revisión anclada; 58 s en la 5080 |
| Detector de conflictos en ingesta | [scripts/detectar_conflictos.py](scripts/detectar_conflictos.py) | corre y encuentra lo plantado; sus hallazgos y sus **no** hallazgos, declarados |
| Mapa de cobertura por módulo | [corpus/COBERTURA.md](corpus/COBERTURA.md) | escrito, con sus huecos y sus pendientes declarados |
| CI (ruff y pytest, todas las ramas) | [.github/workflows/ci.yml](.github/workflows/ci.yml) | en verde, y visto en rojo |
| Entorno local (db, redis, api, worker) | [compose.yml](compose.yml) | levanta y `/salud` en verde |
| API | [app/api/main.py](app/api/main.py) | `/`, `/salud` y `/consulta` |

**Fase 2 abierta en la rama `fase-2`, sin merge a `main` todavía.** Lo cerrado dentro de ella:

| Encargo | Qué | Estado |
|---|---|---|
| 2.1 | Esquema con Alembic, particiones por asignatura y el corpus cargado | **11.282 filas** en 35 particiones; `EXPLAIN` con poda de particiones guardado como [evidencia](docs/evidencia/2026-08-12-explain-poda-particiones.md) |
| 2.2 | `POST /consulta` en SSE con el contrato tipado de la sección 7 | funciona contra Scaleway: TTFT del alumno **1,6 s**, total **2,2 s**, 0,000149 EUR por consulta ([evidencia](docs/evidencia/2026-08-12-humo-proveedor.md)) |

**Y el encargo 3.0, que es de la fase 3 y llegó antes que su fase:** los 100 pares oro no los produce
este repo, se entregaron desde fuera —el mismo autor no puede escribir la recuperación y la vara con
la que se mide— y aquí solo se colocan y se verifican. Están en [evals/casos/](evals/casos/) con su
método declarado al lado: los 100 apuntan a fragmentos que existen y están admitidos, ninguno sale de
`practicas/`, y el reparto es **19 `busqueda` / 81 `lectura`**, que el 3.5 tiene que reportar por
separado. Nada de la fase 3 está construido todavía: esto es su vara de medir, no su recuperación.

`/consulta` comprueba la **forma** del contrato, no la verdad de lo que dice: no hay recuperación
(fase 3) ni verificación (fase 4), y cada afirmación viaja con `veredicto: "sin_verificar"`.

**Lo que la fase 1 dejó pendiente, con su nuevo sitio y no como olvido:** el glosario (encargo 2.6),
los pares oro (3.0) y los conjuntos de casos (2.6, 4.0 y 5.0), cada uno delante del encargo que lo
consume. La tabla completa está en [corpus/COBERTURA.md](corpus/COBERTURA.md).

Todo lo demás —recuperación, generación tipada, verificadores, arnés de evaluación, tabla de
configuraciones y despliegue— está **diseñado en la guía y no construido**. El orden de construcción
es el de la Parte IV de la guía y no se salta.

## Entorno local

Requisitos: Docker con Compose v2. Un clon limpio **no trae corpus** (está fuera de git), y no le
hace falta para arrancar:

```bash
docker compose up -d --wait
curl http://127.0.0.1:8000/salud
```

`/salud` devuelve 200 solo si las cuatro dependencias responden: base de datos, extensiones `vector`
y `pg_trgm`, redis y worker. Si alguna falla, devuelve 503 y dice cuál. Para parar,
`docker compose down`; con `-v` **se borra la base**. Re-embeber el corpus entero son 58 segundos medidos en la 5080, así que lo caro no es la GPU: es rehacer la carga y los índices.

## Cómo se trabaja aquí

Por encargos numerados (0.1, 0.2, 1.1...), en orden, cada uno con su verificación y su criterio de
cierre. Una fase, una rama. Las reglas completas están en [CLAUDE.md](CLAUDE.md).

## Corpus y licencias

El corpus **no se versiona en git** (`corpus/` está en `.gitignore`; solo entran el manifiesto y el
mapa de cobertura). Cada documento lleva en `corpus/manifiesto.jsonl` su ruta, fuente, licencia,
versión de corpus, hash SHA-256, densidad y marca de plantado: **sin entrada en el manifiesto no
entra en el corpus.** La normativa del BOE es dominio público; los apuntes públicos conservan su
licencia y su atribución; los repos de apuntes sin licencia declarada están registrados como
"sin licencia declarada, uso local, no redistribuible" y no salen de la máquina local.

## La fuente oficial también se contradice

Merece estar en el README porque es la tesis del proyecto vista en pequeño. Al extraer el árbol
oficial del BOE ([extraer_arbol.py](scripts/extraer_arbol.py)) apareció esto en el RD 1629/2009, la
norma que crea el título de ASIR:

| Dónde lo dice la norma | Cómo llama al módulo 0372 |
|---|---|
| Anexo I, encabezado del módulo | Gestión de **Base** de Datos |
| Articulado, lista de módulos | Gestión de **bases** de datos |

El mismo real decreto, el mismo módulo, dos nombres. **No se corrige: se declara.** El árbol
conserva lo que dice el Anexo I, que es de donde sale el nodo, y la contradicción se imprime en
cada extracción con su motivo escrito ([ADR 0006](docs/adr/0006-el-auditor-no-comparte-patron-con-el-parser.md)).

Un sistema que "limpiara" esa incoherencia estaría inventando una norma que no existe, y lo haría
en silencio. Preferir el ruido al silencio, y la procedencia por campo a la procedencia por
documento, es exactamente para lo que este sistema existe: **el material real no es coherente, y
fingir que lo es es la forma barata de mentir.**

## Verificación del corpus

```bash
python scripts/verificar_manifiesto.py   # cruza disco contra manifiesto en las dos direcciones
python scripts/verificar_oro.py          # los 100 pares oro contra el índice, por posición Y por texto
```

Las dos son puertas **locales**: el corpus está fuera de git y el runner de CI no lo tiene
([ADR 0001](docs/adr/0001-puerta-del-manifiesto-local-no-en-ci.md),
[ADR 0010](docs/adr/0010-el-par-oro-se-ancla-al-texto-no-a-la-posicion.md)). Cuándo hay que correr
cada una está en [CLAUDE.md](CLAUDE.md), y no es un detalle: la del oro se corre **antes de cualquier
medida de la fase 3** y **después de cualquier cambio de troceado, normalización o puerta de
admisión**, porque un par oro desplazado no da error, da ruido con aspecto de dato.
