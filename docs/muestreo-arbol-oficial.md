# Muestreo del arbol oficial (encargo 1.1)

Diez nodos elegidos a intervalo regular sobre el arbol extraido. **Los comprueba una
persona contra el PDF del BOE**, no el propio extractor. Escribe al lado si el nodo dice
lo que dice la norma en esa pagina, y el numero de acuerdo se anota tal cual: es un
muestreo de 10, no una prueba de que los cientos restantes esten bien.

| # | Titulación | Nodo | Dice | Norma | Documento (pág. del PDF) | ¿De acuerdo? |
|---|---|---|---|---|---|---|
| 1 | DAW | asignatura 0373 | Lenguajes de marcas y sistemas de gestión de · curso 1 | RD 405/2023 | `RD-405-2023-actualizacion-DAW-DAM.pdf` p. 70 | |
| 2 | DAW | unidad 4 de 0485 | Desarrollo de clases | Orden EDU/2887/2010 | `Orden-EDU-2887-2010-curriculo-DAW.pdf` p. 12 | |
| 3 | DAW | unidad 6 de 0613 | Utilización de técnicas de acceso a datos | Orden EDU/2887/2010 | `Orden-EDU-2887-2010-curriculo-DAW.pdf` p. 19 | |
| 4 | DAW | asignatura 0618 | Empresa e iniciativa emprendedora · curso 2 | RD 686/2010 | `RD-686-2010-titulo-DAW.pdf` p. 56 | |
| 5 | DAM | unidad 7 de 0483 | Explotación de aplicaciones informáticas de propósito general | RD 405/2023 | `RD-405-2023-actualizacion-DAW-DAM.pdf` p. 11 | |
| 6 | DAM | unidad 1 de 0487 | Desarrollo de software | RD 405/2023 | `RD-405-2023-actualizacion-DAW-DAM.pdf` p. 28 | |
| 7 | DAM | asignatura 0491 | Sistemas de gestión empresarial | RD 405/2023 | `RD-405-2023-actualizacion-DAW-DAM.pdf` p. 45 | |
| 8 | ASIR | unidad 6 de 0369 | Supervisión del rendimiento del sistema | RD 1629/2009 | `RD-1629-2009-titulo-ASIR.pdf` p. 15 | |
| 9 | ASIR | unidad 4 de 0373 | Definición de esquemas y vocabularios en XML | RD 1629/2009 | `RD-1629-2009-titulo-ASIR.pdf` p. 31 | |
| 10 | ASIR | unidad 7 de 0376 | Adaptación de gestores de contenidos | RD 1629/2009 | `RD-1629-2009-titulo-ASIR.pdf` p. 44 | |

Número de acuerdo: __ de 10 (lo rellena quien comprueba).

Este fichero **no se sobrescribe** al re-ejecutar el extractor, para no perder lo anotado a mano.
Para rehacer la tabla: `python scripts/extraer_arbol.py --forzar-muestreo`.

## Ya comprobado por Marcos contra el BOE (11 de agosto de 2026)

| Qué se comprobó | Resultado |
|---|---|
| Los 13 módulos de DAW | ✓ |
| El reparto 6 en primero y 7 en segundo, contra el Anexo II | ✓ |
| La separación de horas (mínimos del RD frente a currículo de la Orden) | ✓ |

De esa misma revisión salieron dos preguntas que encontraron sendos fallos, y por eso están aquí
escritas: **por qué los 86 RA de DAW cuadraban con la suma del RD de 2010** (respuesta: el RD
405/2023 conserva el número de RA por módulo y reescribe su redacción; comprobado que el texto
extraído es idéntico al de 2023 y distinto al de 2010, módulo a módulo), y **si el acote a la
sección de contenidos había dejado módulos vacíos** (respuesta: sí, tres, y ya están arreglados y
con puerta automática).
