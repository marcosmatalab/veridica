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

## Puertas de calidad (encargo 0.2)

Las reglas de arriba son el Apéndice A de la guía, tal cual. Esto es la operativa concreta del repo.

**En CI** (`.github/workflows/ci.yml`, en push de cualquier rama y en PR), con las herramientas
ancladas en `requirements-dev.txt` y las reglas fijadas en `pyproject.toml`:

```bash
ruff check .    # reglas escritas en pyproject.toml: F401 y F821 dentro
pytest          # tests sobre corpus de juguete: no necesitan el corpus real
```

**En local, además, antes de commitear cualquier cambio del corpus** (esta NO corre en CI, porque el
corpus está fuera de git y el runner no lo tiene; el porqué y el trade-off, en
[ADR 0001](docs/adr/0001-puerta-del-manifiesto-local-no-en-ci.md)):

```bash
python scripts/verificar_manifiesto.py
```

Python 3.13 en las dos partes: local es CPython 3.13.2 (base de miniconda) y el CI corre 3.13.
