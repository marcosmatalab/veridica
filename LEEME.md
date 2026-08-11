# Corpus multi-titulacion, v3 (11 ago 2026): los tres grados enteros

Paquete de arranque de la fase 1 de la guía. SUSTITUYE a v1 y v2. Novedad v3: DAW completa sus 12 módulos lectivos (los restantes con el material de Comesaña, podado a didáctico), y `corpus/COBERTURA.md` trae el mapa módulo a módulo de las tres titulaciones con fuentes, transversales y los dos huecos declarados (0616 Proyecto DAW y 0489 PMDM de DAM). Programación NO lleva versión antigua a propósito: las contradicciones solo viven plantadas y etiquetadas (el par de DWES). Además: el árbol ya está recolocado por titulación (paso 1 del encargo 1.12 hecho) y entran DAM, ASIR y el índice de la familia como titulaciones hermanas a densidad parcial.

Árbol: `corpus/<titulacion>/...` con `daw/` (todo lo del v1: normativa BOE, Programación completa, DWES moderno completo y DWES antiguo plantado), `dam/apuntes/temario-dam-comesana/` (temario DAM de Comesaña, CC no comercial, PODADO: solo material didáctico, fuera los proyectos de IDE y binarios de actividades), `asir/apuntes/` (lora-1asir y lora-2asir, sin licencia declarada: uso local no redistribuible; y aberlanas-iso, CC BY-SA con base Ministerio, con su LICENSE dentro) y `familia/indice-material-formativo/` (índice de la familia profesional). En `dam/normativa/` y `asir/normativa/` hay un POR-DESCARGAR.txt: ahí van los PDF del RD 450/2010 y del RD 1629/2009 que baja Marcos del BOE, registrados con `scripts/anadir_al_manifiesto.py`.

## Qué contiene

- `corpus/normativa/`: RD 686/2010 (título DAW) y Orden EDU/2887/2010 (currículo), en PDF del BOE. Dominio público. Son el esqueleto del árbol: módulos, horas, unidades y resultados de aprendizaje (el Anexo II de la Orden trae la tabla de módulos por curso con sus horas, y el Anexo I los contenidos por módulo).
- `corpus/curso1/programacion/lionel-ict/`: el módulo de Programación (0485) completo, apuntes de lionel-ict, CC BY-NC-SA. Asignatura 1 a densidad completa.
- `corpus/curso2/desarrollo-web-entorno-servidor/joseluisgs-00..05/`: el módulo DWES (0613) del curso 2025-2026 de José Luis González, seis repos, CC BY-NC-SA. Asignatura 2 a densidad completa y la más moderna.
- `corpus/curso2/desarrollo-web-entorno-servidor-antiguo/comesana-dwes/`: el MISMO módulo en su versión antigua (materiales de Comesaña, CC no comercial). Marcado `plantado: true` en el manifiesto: es el par contradictorio REAL para el detector de conflictos (encargos 1.7 y 1.8) y para el momento 3 de la demo. No se mezcla con el moderno: vive en su propia carpeta y sus fragmentos se etiquetan como versión antigua en la ingesta.
- `corpus/manifiesto.jsonl`: una entrada por fichero con ruta, fuente, licencia, versión de corpus, hash SHA-256, densidad y marca de plantado. Regla de la guía: sin entrada en el manifiesto no entra en el corpus.
- `scripts/descargar_rd405.sh`: el único hueco de normativa que queda (ver abajo).
- `scripts/descargar_fondo.sh`: TemarioDAW entero para la densidad parcial del resto de asignaturas. SOLO si sobra tiempo al final de la fase 1; no es prioridad.

## Qué falta (dos cosas, y por qué)

1. **RD 405/2023** (la actualización de 2023 del título): mi entorno no llega a boe.es, así que va como script para tu máquina. Un comando y entra al manifiesto.
2. **Encargo 1.3, normalización**: Programación viene en PDF y ODT, el DWES antiguo en PDF, y el DWES moderno ya está en markdown limpio. Los PDF y ODT hay que pasarlos a texto o markdown antes del troceado, con la revisión por muestreo que marca la guía.

## Números

1.435 ficheros, ~173 MB. Dos asignaturas a densidad completa (Programación y DWES), normativa completa salvo el RD 405/2023, y 16 ficheros plantados del par contradictorio.
