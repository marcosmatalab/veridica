# Veridica

Un profesor por asignatura sobre temario real que solo afirma lo que puede sostener: cita literal
comprobada carácter a carácter, paráfrasis verificada contra el fragmento fuente, cálculo recalculado
y silencio honesto cuando la respuesta no está en el material. La tesis del proyecto: **la honestidad
del sistema no depende de la brillantez del modelo, depende de la capa de verificación.**

> **README provisional.** El README definitivo, con los números medidos, la configuración elegida y
> la sección "Escala", lo produce el **encargo 8.3**. Hasta entonces este fichero solo declara el
> estado real del repo. Nada de lo que aquí no aparezca como construido lo está.

## Estado (11 de agosto de 2026)

**Fase 0 cerrada (encargos 0.1, 0.2 y 0.3).** Hay esqueleto de servicios y puertas de calidad; no hay
todavía recuperación, generación, verificación ni métricas. Lo que existe hoy:

| Qué | Dónde | Estado |
|---|---|---|
| Playbook y fuente de verdad | [guia-definitiva.md](guia-definitiva.md) | escrito |
| Reglas de trabajo | [CLAUDE.md](CLAUDE.md) | escritas |
| Corpus de las tres titulaciones (DAW, DAM, ASIR) | `corpus/` (fuera de git) | descargado y en manifiesto |
| Manifiesto del corpus | [corpus/manifiesto.jsonl](corpus/manifiesto.jsonl) | 2.097 entradas, verificador de rutas en verde |
| Mapa de cobertura por módulo | [corpus/COBERTURA.md](corpus/COBERTURA.md) | escrito, con sus huecos declarados |
| CI (ruff y pytest, todas las ramas) | [.github/workflows/ci.yml](.github/workflows/ci.yml) | en verde, y visto en rojo |
| Entorno local (db, redis, api, worker) | [compose.yml](compose.yml) | levanta y `/salud` en verde |
| API | [app/api/main.py](app/api/main.py) | solo `/` y `/salud` |

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
`docker compose down`; con `-v` **se borra la base**, y desde la fase 1 eso son horas de GPU.

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

## Verificación del corpus

```bash
python scripts/verificar_manifiesto.py   # cruza disco contra manifiesto en las dos direcciones
```
