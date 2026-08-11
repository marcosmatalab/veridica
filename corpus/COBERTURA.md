# El corpus: qué es y cobertura por titulación y módulo (v3, 11 ago 2026)

Este fichero es el **mapa único del corpus**. Absorbe al antiguo `LEEME.md`, que describía el paquete
v1 y había quedado desfasado en rutas, números y pendientes: dos documentos sobre el mismo corpus se
separan solos, y la guía nombra este mapa (encargos 1.12 y cierre de fase 1) y no aquel.

## Qué es y de dónde sale

Paquete de arranque de la fase 1 de [la guía](../guia-definitiva.md). El árbol es
`corpus/<titulacion>/<curso>/<asignatura>/` desde ya, o sea el paso 1 del encargo 1.12 está hecho:

- **`daw/`** — normativa BOE (RD 686/2010, Orden EDU/2887/2010 y RD 405/2023), Programación (0485)
  completa con los apuntes de lionel-ict, DWES (0613) del curso 2025-2026 de José Luis González en
  markdown, el DWES antiguo de Comesaña marcado `plantado: true`, y el resto de módulos con material
  de Comesaña podado a didáctico.
- **`dam/`** y **`asir/`** — titulaciones hermanas a densidad parcial: normativa BOE (RD 450/2010 y
  RD 1629/2009), temario DAM de Comesaña podado, y para ASIR los repos lora-1asir, lora-2asir y
  aberlanas-iso con su LICENSE.
- **`familia/`** — índice de material formativo de la familia profesional.

El corpus **no se versiona en git**: en el repo solo viven sus metadatos, que son este mapa,
`manifiesto.jsonl` y `arbol_oficial.jsonl`. Cada fichero tiene su entrada de manifiesto con ruta,
fuente, licencia, versión de corpus, hash SHA-256, densidad y marca de plantado. **Sin entrada en el
manifiesto no entra en el corpus.**

## Números medidos (11 de agosto de 2026)

- **2.098 ficheros**, ~390 MB en disco; **2.098 entradas** en el manifiesto.
- `python scripts/verificar_manifiesto.py` en verde: **cero hallazgos** en sus cuatro clases
  (rutas huérfanas, ficheros que faltan, hashes cambiados y rutas duplicadas), en 0,9 s.
- Reparto: DAW 1.551, ASIR 429, DAM 115, familia 1 (más este mapa y el árbol oficial).
- **16 ficheros plantados**, todos del DWES antiguo de Comesaña: el par contradictorio real del
  encargo 1.7. Los otros dos tipos de basura de ese encargo (tres casi duplicados y un documento
  colado en la carpeta equivocada) **todavía no están plantados**.

## Licencias

| Licencia | Ficheros | Dónde |
|---|---|---|
| CC BY-NC-SA 4.0 (José Luis González Sánchez) | 989 | daw/curso2/desarrollo-web-entorno-servidor |
| CC BY-NC-SA 3.0 ES | 428 | daw/curso1/programacion (lionel-ict) |
| CC no comercial (Comesaña) | 244 | temario DAM y los módulos parciales de DAW |
| sin licencia declarada: uso local, no redistribuible | 216 | asir/apuntes/lora-1asir y lora-2asir, familia |
| CC BY-SA 3.0 ES (base Ministerio de Educación) | 212 | asir/apuntes/aberlanas-iso (LICENSE dentro) |
| dominio público (art. 13 LPI) | 5 | normativa BOE de las tres titulaciones |

Regla del encargo 1.12 ya aplicada: los repos de apuntes personales sin licencia declarada se
registran como uso local no redistribuible y **jamás salen del corpus local**.

## El árbol oficial y la asimetría de sus fuentes (encargo 1.1)

`corpus/arbol_oficial.jsonl` lleva el árbol extraído del BOE: **536 nodos** (una línea cada uno),
con la referencia legal —norma, documento y página del PDF— en cada nivel.

| Titulación | Asignaturas | Con curso | Unidades | Resultados de aprendizaje |
|---|---|---|---|---|
| DAW | 13 | **13** | 80 | 86 |
| DAM | 14 | 0 | 76 | 88 |
| ASIR | 14 | 0 | 74 | 88 |

**Las tres titulaciones no tienen la misma fuente, y eso se ve en el árbol:**

| Nivel | DAW | DAM | ASIR |
|---|---|---|---|
| Asignaturas y resultados de aprendizaje | RD 686/2010 **actualizado por el RD 405/2023** (9 de 13 módulos vienen del de 2023) | RD 450/2010 **actualizado por el RD 405/2023** (11 de 14) | RD 1629/2009 (el 405/2023 no toca ASIR) |
| Unidades (bloques de contenido) | **Orden EDU/2887/2010** (currículo), que amplía contenidos módulo a módulo | Anexo I del RD, contenidos básicos | Anexo I del RD, contenidos básicos |
| Curso (1º / 2º) | Anexo II de la Orden EDU/2887/2010, tabla de secuenciación | **null** | **null** |
| Horas | Anexo II de la Orden (170, 230…) | **null** | **null** |

Consecuencia, dicha en voz alta: **las unidades de DAW salen de una fuente más rica que las de sus
hermanas.** No es un fallo del extractor, es la fuente: DAW tiene orden de currículo estatal y ellas
no. Cuando se comparen unidades entre titulaciones, hay que saber esto.

**Por qué `curso` va nulo en DAM y ASIR.** El real decreto del título fija módulos, resultados de
aprendizaje y contenidos, pero **no reparte los módulos entre primero y segundo**: eso lo hace la
orden de currículo, y de esas solo tenemos la de DAW. Rellenarlo "por lo que suele ser" en un
fichero que presume de referencia legal por nodo sería exactamente lo contrario de lo que se
construye aquí, así que va nulo con su motivo escrito en cada nodo (`curso_nota`). Si algún día hace
falta, se baja del BOE la orden de currículo de cada título y se completa con su cita.

**Por qué `horas` va nulo en DAM y ASIR.** Sus reales decretos sí traen duraciones, pero son las
mínimas estatales, de otra magnitud que las del currículo completo: en DAW conviven las dos y se ve
el salto (el RD da 100 o 135 horas donde la Orden da 170 o 230). Mezclarlas en la misma columna
daría una tabla que se lee mal y compara peor, así que solo se rellena desde la Orden.

**Módulos sin unidades, y por qué.** Cuatro módulos salen con cero unidades: Proyecto y FCT de DAM
(0492, 0495) y de ASIR (0379, 0382). No es una pérdida del extractor: sus normas no traen sección de
contenidos para ellos, y eso lo comprueba una puerta automática que denuncia cualquier módulo que
SÍ declare contenidos y no dé ninguna unidad. DAW tiene los suyos porque la Orden de currículo sí
les da contenido (0616 con dos unidades).

**Comprobación del árbol.** El extractor cruza los códigos que saca del Anexo I contra la lista de
módulos que cada norma declara en su articulado, que es otra parte del documento: 13/13 en DAW,
14/14 en DAM y 14/14 en ASIR. Además hay diez nodos elegidos para revisión **a mano** contra el BOE
en [`docs/muestreo-arbol-oficial.md`](../docs/muestreo-arbol-oficial.md); ese número de acuerdo lo
pone una persona, no el extractor, y se anota como lo que es: un muestreo de diez.

## Normalización a texto: un documento, una fuente (encargo 1.3)

El corpus trae **el mismo documento en varios formatos por todas partes**: en Programación, 53 de
sus 63 PDF tienen gemelo `.odt` o `.docx`. Normalizar los dos metería el mismo contenido dos veces,
lo que infla el índice, reparte el peso de recuperación entre dos copias y **llena de falsos
positivos el detector de conflictos del encargo 1.8**, que es justo la pieza que tiene que estar
limpia para la demo. Así que cuando hay gemelos se normaliza **uno solo**.

**Criterio, por este orden:**

1. **Markdown o HTML, si existen.** Ya son texto limpio: convertir un PDF para obtener lo que ya
   está en markdown solo puede empeorarlo. (2 casos: `DAFO.md` y `Lista_de_Funciones.html`.)
2. **PDF**, en los demás casos.
3. **`.odt` o `.docx`**, solo cuando no hay PDF (39 documentos huérfanos).

**Por qué el PDF y no el original ofimático**, medido antes de decidir sobre pares reales del
corpus:

| Comprobación | Resultado |
|---|---|
| ¿Alguno de los dos pierde contenido? | No. Las palabras "solo en el PDF" resultaron ser puntos de índice (`Introducción......5`); las "solo en el ODT", números pegados (`Introducción4`) |
| Palabras rotas por kerning | Comparable: 0,7–1,7% en ambos formatos |
| Mobiliario de página repetido | **Peor en PDF** (hasta 303 líneas repetidas en un documento), pero es ruido sistemático y se quita por regla; el del ODT es irregular |
| Cobertura | **Solo el PDF cubre el 100%**, incluidos los `.odg`, cuyo único texto usable es su PDF exportado |
| Consistencia | 63 de los 65 documentos de Programación entran por un solo camino |

Y el camino del PDF hay que escribirlo de todas formas: **216 PDF del corpus no tienen gemelo**.

**Dibujos, fuera y declarados.** Los `.odg` (35 en total, con `.dia` y `.svg`) son dibujos de
LibreOffice, no documentos: no se convierten. Cuando tienen PDF, ese PDF es la fuente.

**Números de la normalización:** 312 derivados, **11 MB de texto** desde ~390 MB de binario, en
2m25s. Origen: 277 PDF, 22 `.docx`, 16 `.odt`. Cada derivado vive en `corpus/derivado/<misma ruta>`
y lleva en el manifiesto `derivado_de`, `herramienta` y `herramienta_version`, heredando licencia,
densidad y marca `plantado` del original (ADR 0004): 9 derivados heredan `plantado: true`.

**Los cuatro documentos que no dieron texto útil**, declarados y no convertidos:

| Documento | Motivo |
|---|---|
| `asir/apuntes/lora-1asir/HW/particionado.docx` | **el fichero está vacío (0 bytes)** en el corpus original |
| `daw/curso1/entornos-de-desarrollo/comesana/ED_MapasConceptuales.pdf` | 37 caracteres únicos por página: es un mapa conceptual, o sea un dibujo |
| `daw/curso2/despliegue-de-aplicaciones-web/comesana/DAW_MapasConceptuales.pdf` | ídem |
| `daw/curso2/diseno-de-interfaces-web/comesana/DIW_MapasConceptuales.pdf` | ídem |

**Descartados por gemelo: 63.** Por carpeta: Programación 54, ASIR (lora-1asir) 5, DAM (temario
Comesaña) 3, y 1 en ASIR (lora-2asir). El listado completo, documento a documento, lo imprime
`python scripts/normalizar.py --simulacro`, que no escribe nada y dice exactamente qué convertiría
y qué descarta con su motivo.

## Regla de lectura de la densidad

**Densidad "completa" significa curado para evaluación** (pares oro, conjuntos de casos), no cantidad
de material. Solo las dos asignaturas de DAW son "completa". El resto de módulos tienen material de
ciclo entero pero sin curar: densidad "parcial". Los módulos marcados TRANSVERSAL se cargan UNA sola
vez y se mapean a varias titulaciones mediante la tabla puente `titulacion_asignaturas` (el propio
Anexo II del RD los marca como transversales: no es un atajo, es fiel al título oficial).

## DAW (Técnico Superior en Desarrollo de Aplicaciones Web, RD 686/2010)

| Módulo (código BOE) | Curso | Fuente en el corpus | Estado |
|---|---|---|---|
| 0483 Sistemas informáticos | 1 | daw/curso1/sistemas-informaticos/comesana | parcial (Comesaña 2012) |
| 0484 Bases de datos | 1 | daw/curso1/bases-de-datos/comesana | parcial (Comesaña 2012) |
| 0485 Programación | 1 | daw/curso1/programacion/lionel-ict | **COMPLETA (curada, moderna)** |
| 0373 Lenguajes de marcas | 1 | daw/curso1/lenguajes-de-marcas/comesana | parcial. TRANSVERSAL (DAW, DAM, ASIR) |
| 0487 Entornos de desarrollo | 1 | daw/curso1/entornos-de-desarrollo/comesana | parcial (Comesaña 2012) |
| 0617 FOL | 1 | daw/curso1/fol/comesana | parcial. Material sirve a DAM y ASIR por transversalidad de contenido |
| 0612 Desarrollo web en entorno cliente | 2 | daw/curso2/desarrollo-web-entorno-cliente/comesana | parcial (Comesaña 2012) |
| 0613 Desarrollo web en entorno servidor | 2 | daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-00..05 | **COMPLETA (curada, 2025-2026)** |
| (0613, versión antigua) | 2 | daw/curso2/desarrollo-web-entorno-servidor-antiguo/comesana-dwes | **PLANTADA** (par contradictorio real, `plantado: true`) |
| 0614 Despliegue de aplicaciones web | 2 | daw/curso2/despliegue-de-aplicaciones-web/comesana | parcial (Comesaña 2012) |
| 0615 Diseño de interfaces web | 2 | daw/curso2/diseno-de-interfaces-web/comesana | parcial (Comesaña 2012) |
| 0618 Empresa e iniciativa emprendedora | 2 | daw/curso2/empresa-e-iniciativa-emprendedora/comesana | parcial |
| 0616 Proyecto | 2 | sin material (módulo de proyecto, sin temario editorial) | hueco declarado |
| 0619 FCT | 2 | no aplica (formación en centros de trabajo) | no aplica |

Nota deliberada: el módulo 0485 Programación NO lleva la versión antigua de Comesaña. Motivo: las
contradicciones del corpus deben estar plantadas y etiquetadas (encargos 1.7 y 1.8), no repartidas
sin control. El único par de épocas conviviendo es el de DWES, que está etiquetado.

## DAM (Técnico Superior en Desarrollo de Aplicaciones Multiplataforma, RD 450/2010)

Primer curso: comparte con DAW los módulos 0483, 0484, 0485, 0373 y 0487 (mismos códigos en el título
oficial). Se cargan UNA vez bajo DAW y se mapean a DAM por la tabla puente. FOL por transversalidad
de contenido.

| Módulo 2º curso | Fuente en el corpus | Estado |
|---|---|---|
| 0486 Acceso a datos | dam/apuntes/temario-dam-comesana/AD | parcial (Comesaña) |
| 0488 Desarrollo de interfaces | dam/apuntes/temario-dam-comesana/DI | parcial (Comesaña) |
| 0489 Programación multimedia y dispositivos móviles | sin material en la fuente | **hueco declarado** |
| 0490 Programación de servicios y procesos | dam/apuntes/temario-dam-comesana/PSP | parcial (Comesaña) |
| 0491 Sistemas de gestión empresarial | dam/apuntes/temario-dam-comesana/SGE | parcial (Comesaña) |
| EIE | material transversal (daw/curso2/eie) | por puente de contenido |
| Proyecto / FCT | sin material / no aplica | hueco declarado / no aplica |

(Los códigos de FOL, EIE, Proyecto y FCT propios de DAM se verifican contra el PDF del RD 450/2010,
ya presente en `dam/normativa/`, cuando el encargo 1.1 cargue el árbol en `asignaturas`.)

## ASIR (Técnico Superior en Administración de Sistemas Informáticos en Red, RD 1629/2009)

| Módulo | Fuente en el corpus | Estado |
|---|---|---|
| 0369 Implantación de sistemas operativos | asir/apuntes/lora-1asir/SO y asir/apuntes/aberlanas-iso (UD01..UD12, CC BY-SA) | parcial, DOS fuentes |
| 0370 Planificación y administración de redes | asir/apuntes/lora-1asir/Redes | parcial |
| 0371 Fundamentos de hardware | asir/apuntes/lora-1asir/HW | parcial |
| 0372 Gestión de bases de datos | asir/apuntes/lora-1asir/BBDD | parcial |
| 0373 Lenguajes de marcas | TRANSVERSAL: daw/curso1/lenguajes-de-marcas | por puente |
| 0374 Administración de sistemas operativos | asir/apuntes/lora-2asir/ASO | parcial |
| 0375 Servicios de red e internet | asir/apuntes/lora-2asir/SRI | parcial |
| 0376 Implantación de aplicaciones web | asir/apuntes/lora-2asir/IAW | parcial |
| 0377 Administración de sistemas gestores de BBDD | asir/apuntes/lora-2asir/BBDD | parcial |
| 0378 Seguridad y alta disponibilidad | asir/apuntes/lora-2asir/SAD | parcial |
| 0379 Proyecto | asir/apuntes/lora-2asir/Proyecto.md | testimonial |
| 0380 FOL | asir/apuntes/lora-1asir/FOL (+ transversal daw/fol) | parcial |
| 0381 EIE | asir/apuntes/lora-2asir/"Empresa e iniciativa emprendedora" | parcial |

(Códigos a confirmar contra el PDF del RD 1629/2009, ya presente en `asir/normativa/`, cuando el
encargo 1.1 cargue el árbol. El material suelto de lora-2asir sobre Git, Openstack, OVH y Docusaurus
queda como complementario de HLC/proyecto.)

## Resumen honesto

Tres titulaciones con material de ciclo prácticamente entero: DAW con sus 12 módulos lectivos
cubiertos (2 curados, 9 parciales, 1 hueco de proyecto), DAM con 1º entero por transversales y 4 de 5
módulos propios de 2º (hueco: PMDM 0489), ASIR con los 13 módulos cubiertos por alguna fuente. Los
huecos están declarados aquí, no escondidos: un mapa con dos huecos escritos vale más que un
"completo" que no lo es.

## Qué falta (encargos de la fase 1 todavía abiertos)

1. **1.1** — extraer de los PDF de normativa el árbol oficial de cada titulación y cargarlo en
   `asignaturas` con su puente `titulacion_asignaturas`. La normativa está toda dentro; lo que falta
   es la carga, que necesita la base de datos de la fase 2.
2. **1.3** — normalización: Programación viene en PDF y ODT y el DWES antiguo en PDF; hay que pasarlos
   a texto o markdown con la revisión por muestreo que marca la guía. El DWES moderno ya es markdown.
3. **1.7** — plantar los tres casi duplicados y el documento colado en la carpeta equivocada; el par
   contradictorio ya está.
4. **Limpieza pendiente:** `dam/normativa/POR-DESCARGAR.txt` y `asir/normativa/POR-DESCARGAR.txt`
   piden unos PDF que ya están dentro. Se borran junto con sus dos entradas de manifiesto cuando se
   abra el primer encargo de la fase 1, para no tocar el corpus fuera de su encargo.
