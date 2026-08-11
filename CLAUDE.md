# Reglas de trabajo de este repo

- La fuente de verdad es guia-definitiva.md. Se trabaja por encargos numerados, en orden.
- Antes de picar: plan de 10 líneas o menos y OK explícito del owner. Sin OK no hay código.
- Una fase, una rama. Merge a main solo con la suite en verde y el criterio de cierre de la fase cumplido.
- Verificación mínima en cada commit: ruff check (con F821 y F401) y los tests del área tocada.
- Al cierre de cada fase: pasada adversarial buscando dónde miente el verde; hallazgos arreglados o anotados como deuda con motivo.
- Toda sonda o métrica nueva se valida contra un caso donde debe fallar antes de creerse su verde, y deja test de regresión anclado.
- Toda prueba de mutación confirma que la mutación se aplicó de verdad, enseñando el diff, ANTES de leer el resultado. Un test que pasa sobre código sin mutar no ha probado nada: es la misma trampa del verde mentiroso, esta vez en la herramienta de comprobar.
- Los códigos de salida se leen SIN tubería. `cmd | tail; echo $?` devuelve el código del último comando de la tubería, no el del programa que importa: para leer el de un programa se corre solo, o se guarda antes de tubear. Misma familia que la mutación que no se aplica: el instrumento mintiendo, no lo medido.
- Toda decisión de diseño: ADR corto en docs/adr/ (contexto, decisión, trade-off).
- Ningún documento del repo afirma en presente lo no construido.
- Secretos jamás en el repo: variables de entorno, .env.example sin valores.
- Los umbrales de configuración marcados como iniciales se calibran donde la guía lo indica y el barrido se persiste en corridas_eval.
- Commits pequeños con el porqué en el mensaje. Nada de "arreglos varios".
- Ocurrencias y hallazgos se cuentan por separado en cualquier número que alimente una decisión.

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
python scripts/verificar_manifiesto.py   # rutas + SHA-256 de las 2.097 entradas, ~1 s
```

**Cuándo se corre, que es tan importante como que exista:**

1. **Al abrir cualquier sesión que vaya a tocar el corpus**, antes de nada. Un fichero corrupto
   descubierto al principio cuesta un `git checkout`; descubierto tarde, contamina todo lo que se
   haya construido encima.
2. **Obligatoriamente antes de la ingesta del encargo 1.5**, sin excepción. Embeber un corpus
   corrupto son horas de GPU tiradas, y no te enteras entonces: te enteras semanas después, cuando
   las respuestas salen raras y no sabes si la culpa es del troceado, del reordenador o del modelo.
   La puerta cuesta un segundo; el fallo que evita cuesta una tarde y una investigación en falso.
3. Antes de commitear cualquier cambio del corpus o del manifiesto.

Códigos de salida: `0` sin hallazgos, `1` con hallazgos de integridad, `2` manifiesto ilegible o mal
formado (que no es lo mismo: un manifiesto roto no es un corpus roto).

Python 3.13 en las dos partes: local es CPython 3.13.2 (base de miniconda) y el CI corre 3.13.

## Entorno local (encargo 0.3)

```bash
docker compose up -d --wait   # db, redis, api y worker; el verde de --wait ES /salud en verde
docker compose down           # para los servicios y CONSERVA los datos
curl http://127.0.0.1:8000/salud
```

**`docker compose down -v` BORRA el volumen `datos-db`, y con él la base entera.** Hoy es inofensivo
porque no hay datos. Desde la fase 1 ahí viven los embeddings del corpus, que son horas de GPU:
tirarlos cuesta una tarde de re-embeber. **Para reiniciar servicios se usa `down` a secas**; el `-v`
solo cuando se quiera una base vacía a propósito y sabiendo lo que se lleva por delante.

Puertos del host, elegidos midiendo la máquina y no por costumbre: **db en 5434** (el 5432 se lo
queda el servicio `postgresql-x64-17`, instalado en modo automático, al reiniciar Windows; el 5433 y
el 6379 los tiene publicados el proyecto `fulkro-oss`), **api en 8000**, y **redis sin publicar**
porque nada fuera de la red de compose lo necesita. `corpus/` no se monta en ningún contenedor: la
ingesta corre en Windows para usar la GPU.
