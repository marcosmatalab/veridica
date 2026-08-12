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

- **2.106 ficheros originales**, ~465 MB en disco, más **307 derivados** de la normalización:
  **2.413 entradas** en el manifiesto, una por fichero.
- **Dos ficheros retirados del árbol** por datos personales (el CSV de notas y un CV real), con sus
  entradas dadas de baja: ver *Tres hallazgos* más abajo.
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
pone una persona, no el extractor.

**Y el número, tal como salió: no es «10 de 10».** De los diez nodos, **3 verificados
directamente** contra el PDF y correctos con sus páginas exactas (nodos 2, 3 y 4), **3 verificados
indirectamente** por transversalidad (el 0373 de ASIR y los bloques de 0483 y 0487), **4 no
verificables** porque esos PDF no están en manos de quien comprueba, y **1 defecto encontrado**: el
nombre truncado del 0373 de DAW, que al tirar del hilo destapó **otros doce**. Cuatro nodos sin
comprobar siguen sin comprobar, y se anotan así: un «10 de 10» aquí sería justo el verde mentiroso
que este repo persigue. El valor del muestreo está en la última fila —una persona mirando diez nodos
encontró lo que las puertas automáticas daban por bueno en el árbol entero.

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

## Troceado: 11.574 fragmentos (encargo 1.4, rehecho tras el muestreo a mano)

`corpus/fragmentos.jsonl` (fuera de git como el resto del corpus, con su entrada de manifiesto).
Contados con el **tokenizador real de BGE-M3**, no estimando:

| | |
|---|---|
| Fragmentos | **11.483** (de 12.494 troceados: 1.011 no pasan la puerta de admisión) |
| Tokens por fragmento | p50 482, p90 507, p99 522, media 446 |
| Reparto | DAW · ASIR · DAM, en la proporción del corpus |
| Tipos | explicación 8.548 · **código 1.389** · definición 597 · procedimiento 387 · ejemplo resuelto 286 · **enunciado de ejercicio 223** · normativa 53 |
| Código por lenguaje | Java 802 · C# 211 · SQL 13 |
| Con unidad declarada | 2.321 |
| Con frase candidata a definición | 878 |

Los números de la versión anterior (13.030 fragmentos, 3.685 "ejemplo resuelto", 12.591 con unidad)
**eran peores de lo que parecían**, y lo que sigue explica por qué: el índice llevaba dentro basura
que no es material docente, la unidad decía el nombre de quien escribió los apuntes y la asignatura
de ASIR y DAM entera decía "apuntes". Se descubrió leyendo veinte fragmentos a ojo, no con tests.

**Los 512 tokens incluyen la línea de contexto**, que cuesta 26–32 tokens (media 29): al cuerpo le
quedan unos 480. Se cuenta dentro porque lo que se embebe es el fragmento entero; si el presupuesto
fuera solo del cuerpo, el vector real llevaría 540 tokens y el "512" no sería cierto.

**La `unidad` sale de la carpeta del material, no del árbol del BOE** ([ADR 0005](../docs/adr/0005-la-unidad-sale-de-la-carpeta-no-del-boe.md)):
son taxonomías distintas ("Unidad 4 Introducción a Java" frente a "Utilización de objetos") y no hay
mapeo fiable. La partición y el filtro van por asignatura, que sí casa en ambas.

### Los cuatro campos que se arreglaron, y por qué importaba cada uno

**1. Puerta de admisión: 1.009 fragmentos fuera (8,0 %).** La lista entera, documento a documento y
con su motivo escrito, se regenera en cada pasada en
[`docs/descartes-admision.md`](../docs/descartes-admision.md). Dos niveles:

| | fragmentos | |
|---|---:|---|
| Documento excluido entero | **850** | 88 documentos: 50 `index.html` de "403 Forbidden" de una app entregada como proyecto, 25 índices de repositorio sin contenido propio, un diccionario de palabras de 654 fragmentos, y la lista manual |
| Fragmento suelto | **159** | volcados de consola, cabeceras de correo, índices de enlaces, tablas sin una sola frase |

La lista manual (`EXCLUIDOS_A_MANO` en `scripts/admitir.py`) es **manual a propósito**: distinguir un
trabajo de alumno de temario por la forma del texto es caro y arriesga falsos positivos sobre
material bueno, porque **los enunciados de ejercicio sí valen** —son la fuente de las preguntas de
los pares oro del 3.6—. Se decide documento a documento, como las cuatro excepciones de DNI. Ahí
están el trabajo sobre operadoras de Polonia firmado por dos alumnos, la reflexión autobiográfica de
FOL, la memoria del proyecto de 2.º ASIR, las dos plantillas de corrección del profesor, la guía del
alumno del módulo, y **un CV real con nombre, teléfono, correo y redes de una persona** —ese no se
quedó en la lista: está borrado del disco, y de ahí salió la regla de concentración de la puerta de
sensibles (más abajo)—.

**2. `tipo_contenido`: la unidad estaba mal, no el patrón.** La medida a mano dio **3 aciertos de 20**
en los fragmentos marcados `definicion`, y el motivo no era el patrón: un fragmento son 512 tokens
de prosa y casi cualquier trozo de 512 tokens contiene *en algún sitio* una frase con "es un". Así
que ahora el troceador guarda **la frase concreta** (`frase_definitoria`), que es lo que el 1.6
necesita. Medido sobre una muestra distinta de la que se usó para afinar —si no, el número lo
fabrica quien afina—: **13 de 20 son definiciones de verdad (65 %)**, frente a 3 de 20 antes.
Además encaja con el principio 6: si la definición es literal, comprobar que está en su fragmento es
una comparación de cadenas, sin modelo, independiente del que la extrajo.

**3. `unidad`: el primer directorio con significado, y vacío si no hay ninguno.** Antes era el más
profundo, y de ahí salían unidades como `comesana` (3.370 fragmentos), `Manuales`, `java` o `D4`.
Ahora hay **2.321 fragmentos con unidad de verdad** (`UD05_UsuariosGruposYPermisos`, `Unidad 5 SGE`)
y 9.253 sin ninguna. El número baja y aun así es mejor: la unidad viaja en la línea de contexto y la
línea de contexto **entra en el vector**, así que el ruido no era neutro. Lo que esos 9.253 pierden
lo compensa su título, que sí está en el contexto.

**4. Mobiliario de página: 3.329 ocurrencias fuera.** "- 8 -", "Tema 3 - 13 -" y la viñeta Wingdings
que el extractor convertía en un "9" delante de cada función. Se limpia en la **normalización**
(`scripts/mobiliario.py`), no al trocear, para que el fragmento que se cita siga siendo comparable
letra a letra con su fichero derivado: la cita literal se verifica por comparación de cadenas.

### Los últimos cuatro, del segundo muestreo a mano (15 válidos, 4 flojos, 1 basura)

La segunda lectura a ojo, sobre veinte fragmentos distintos de los primeros, dio **15 / 4 / 1**
frente al **11 / 3 / 6** de la primera. De ahí salieron los cuatro últimos arreglos del corpus:

**1. El índice de un PDF, que la puerta no veía.** La regla del índice miraba la *forma del enlace*
markdown, y en un PDF derivado no hay enlaces: hay `__call__ 105`, `herencia múltiple 46`,
`lambda 60`. La señal que sí los separa es la que comparten todas esas líneas y ninguna prosa —un
término corto, ningún verbo y un número de página al final—. Caza los 2 índices que quedaban en el
índice y ningún fragmento más.

**2. El título de la línea de contexto salía de una línea cualquiera:** `esto es una cadena`,
`fdisk /dev/sdb`, `-*- coding: utf-8 -*-`. Filtrar por "parece un comando" no bastaba, porque el
problema era otro: **en un `.pdf.md` o un `.txt` una almohadilla no significa encabezado**. Ahora
solo se cree el encabezado donde el formato lo garantiza (markdown nativo, o derivado de `.odt` y
`.docx`, donde el conversor lo saca de los estilos) y en el resto manda el nombre del fichero.
`SI09` dice menos que `fdisk /dev/sdb`, pero no miente, y esa línea entra en el vector.

**3. La cabecera corrida, que se ve dentro de la cita:** "TEMA 6-1 Página 139 I.S.O.", "© Copyright
- Copyleft Jorge Sánchez 2004", "CFGS. DESARROLLO DE APLICACIONES WEB 4.4". Salía en **4 de los 20**
fragmentos. El filtro por frecuencia no podía verlas porque cada una es una línea distinta: ahora se
cuentan **por firma**, con los números borrados, se exige que vivan en el **borde** de la página, y
se borran también **como subcadena** cuando el extractor las deja pegadas a un párrafo. Del 20 % se
baja a **1 de 20**, y ese resto está explicado más abajo.

**4. `tipo_contenido`, con la etiqueta que faltaba.** Se añade **`enunciado_ejercicio`** (223
fragmentos): lo que se le *pide* al alumno no es ni explicación ni procedimiento —un procedimiento
cuenta cómo se hace algo, un enunciado manda hacerlo—, y hace falta poder pedirlo por su etiqueta
porque **es la fuente de las preguntas de los pares oro del 3.6**. Cubre boletines de ejercicios,
tareas con entrega y cuestionarios tipo test. Y se corrige el error inverso: prosa sobre Swing
marcada `codigo` porque su tabla de referencia lleva una firma de método en cada fila. Ahora, para
ser `codigo`, además de líneas con pinta de código hace falta que **no haya frases enteras**.

### Dónde no se ha llegado, dicho con su número

- **1 de 20 fragmentos** conserva cabecera corrida: `DWEC06.pdf`, donde el extractor solo emite el
  pie como línea propia en **7 de sus 38 páginas** —muy por debajo de cualquier umbral razonable— y
  además su poda dispara el freno de mano, que restaura la página para no perder contenido. Bajar el
  umbral hasta cazarlo se llevaba por delante frases de contenido de un manual de Proxmox que repite
  una instrucción en 3 de sus 11 páginas. **Se prefiere el resto de ruido a perder material bueno**,
  y queda escrito en vez de disimulado.
- El `tipo_contenido` sigue siendo una etiqueta aproximada fuera de `definicion`, que es la única
  cuya precisión se ha medido. `explicacion` es el cajón por defecto: 8.548 de 11.483.

### Un quinto problema que no estaba en la lista: la asignatura decía "apuntes"

Leyendo la ruta a ciegas, **3.495 fragmentos —el 27 % del índice— tenían asignatura `apuntes`**, que
es el nombre del cajón donde cuelgan los repositorios de ASIR y DAM, no un módulo. Y la asignatura no
es un adorno: es la partición del filtro de recuperación **y la del detector de colados del 1.8**, de
modo que un colado dentro de ASIR era invisible por construcción, igual que los pares consecutivos
del solape.

La equivalencia sigla → módulo va **declarada una a una** en `scripts/trocear.py`, no deducida, con
su norma al lado (`SO` → *implantación de sistemas operativos*, RD 1629/2009). Donde no hay
equivalencia segura **no se inventa**, igual que el `curso` de DAM y ASIR: `HLC` y `Talleres` se
quedan con su sigla y 119 fragmentos sueltos en la raíz de un repositorio se quedan **sin asignatura
declarada**. Origen del campo, medido: 8.235 de la carpeta del ciclo, 1.975 de sigla con tabla
declarada, 1.162 de repositorio de una sola asignatura, 83 de sigla sin equivalencia, 119 sin
declarar. Efecto colateral bueno: `aberlanas-iso` y `lora-1asir/SO` caen ahora en la **misma**
asignatura, que es lo que hace comparables dos fuentes del mismo módulo en el 1.8.

### Dónde falló el propio arreglo (y se arregló mirando, no confiando)

- **La primera puerta se llevó material bueno.** Buscaba `apt-get` y `dpkg ` como señal de basura y
  tiró `Teoria_03_LinuX_dpkg.md`, un documento de teoría que explica qué es dpkg. **En ASIR los
  comandos son la materia.** Las firmas se reescribieron para reconocer lo que dice la *máquina*
  (`Setting up`, `Get:1`, `Unpacking`) y no lo que escribe la persona, y además exigen que el volcado
  sea el 40 % de las líneas del fragmento.
- **Las URL de las capturas contaban como base64** y se llevaron los 11 fragmentos de la guía de
  instalación de Ubuntu Server. Ahora se quitan las direcciones antes de medir y se exige que el
  token largo lleve algún dígito.
- **El limpiador y el troceador no veían las mismas líneas.** Un `\r` suelto dentro del texto
  extraído no es un salto de línea para el fichero, pero **sí lo es para quien lo lee en modo texto**:
  el número de página que el limpiador no veía como línea suelta, el troceador sí. Misma familia que
  el código de salida leído a través de una tubería: el instrumento mintiendo, no lo medido.
- **329 fragmentos se embebían con un título falso** en la línea de contexto: `/etc/init.d/nscd
  restart`, `apt-get install eclipse`. En un `.md` derivado de PDF no hay encabezados, pero sí líneas
  que empiezan por almohadilla, que son comentarios de shell. Quedan 23.
- **El reanudador de embeddings habría corrompido el índice en silencio.** La reanudación es
  posicional, así que con los checkpoints del troceado anterior el vector de la posición 7.000 se
  habría quedado pegado a otro fragmento, con el `.npy` del tamaño correcto y el proceso en verde.
  Ahora se comprueba que los checkpoints son de este fichero de fragmentos y, si no, **para** (salida
  2). Probado disparando antes de creérselo.

**El código no se parte por ventana ciega.** Un fichero es un fragmento si cabe; si no, se corta por
clase o por método. Consecuencia declarada: **126 fragmentos de código pasan de 512 tokens** (el
mayor, 6.910, un `BurgerMenuApp.java` con un método enorme), porque partirlos por tamaño daría
código que no compila ni se entiende. Ninguno pasa de 8.192, el máximo del modelo, así que todos se
pueden embeber. Los 21 ficheros donde el corte por clase o método no basta quedan listados como
avisos por el propio script.

### Hallazgo de seguridad en el corpus

Los apuntes `asir/apuntes/lora-2asir/HLC/Kubernetes.md` traen **certificados de Kubernetes y una
clave privada RSA** volcados en base64. **No entran al corpus**: el troceador los descarta y los
declara (3 bloques). Un sistema que cita fragmentos del corpus a un alumno no puede tener eso
dentro. El fichero original se conserva como está —es material de un repo de terceros y el corpus no
se reescribe—, pero su contenido sensible no llega a fragmento ni, por tanto, a embedding.

## Embeddings: 11.574 vectores en 59 segundos (encargo 1.5)

`corpus/embeddings/vectores.npy` (11.574 × 1024, float32) y su `ids.jsonl`. La configuración
completa con la que se generaron está en `corpus/medidas-ingesta.json`, **con la revisión del modelo
anclada**: sin eso los embeddings son irreproducibles, que es justo lo que el manifiesto existe para
evitar.

| | |
|---|---|
| Modelo | `BAAI/bge-m3`, revisión `5617a9f61b028005a4858fdac845db406aefb181` |
| Precisión / normalización / largo máximo | float16 · normalizados · 8192 (nada se trunca) |
| GPU | RTX 5080, CUDA 12.8, torch 2.11.0+cu128, capability (12,0) |
| **Ritmo** | **194,9 fragmentos/s** · 59,4 s en total · 2,8 s de carga del modelo |
| VRAM máxima | **1,85 GB** de 16 |
| En CPU (plan B, medido sobre 500) | 3,1 fragmentos/s → **~62 minutos** el índice entero |
| Puesta a punto de CUDA | 1 min 50 s (rueda cu128, 2,75 GB) |

**Extrapolación a un tera**, calculada con lo medido y no a ojo: ratio binario→texto **38,8:1**,
1.073 fragmentos por MB de texto → **29,0 millones de fragmentos por TB**, **41,3 horas** de
embebido en esta GPU y **110,6 GB** de vectores en float32 (55,3 en float16). El supuesto va con el
número: este corpus es sobre todo **PDF digital**. Un tera de cliente real (escaneos y vídeo) destila
mucho más, así que da *menos* fragmentos por tera: esta cifra es el techo pesimista, no el optimista.
La cifra baja respecto a la medición anterior (32,7 millones) porque el índice ya no lleva dentro los
1.009 fragmentos que no eran material docente: son **menos fragmentos por MB, no menos corpus**.

### La línea base que justifica la capa de verificación

Búsqueda de humo en las dos direcciones (`scripts/humo_recuperacion.py`):

- **Con respuesta en el temario:** "qué es una clave primaria" → 0,658, y el fragmento contiene
  literalmente la definición; "cómo se declara un bucle for en Java" → 0,666, unidad *Unidad 5
  Bucles*, que es la correcta.
- **Sin respuesta en el corpus:** "cuándo se poda un olivo joven" → **0,431**, devolviendo código
  Java de excepciones; "dosis de paracetamol para un niño de 20 kilos" → 0,407; "quién ganó el
  mundial de 1978" → 0,421.

**La similitud nunca dice "esto no está":** siempre devuelve su vecino más cercano, con aplomo. La
distancia entre 0,43 (fuera de temario) y 0,66 (dentro) no da un umbral limpio, y ese solape es
exactamente el argumento de por qué hace falta la capa de verificación de la fase 4. Es la
abstención vista desde el otro lado, y medirla hoy salió gratis.

### Puerta de material sensible: el corpus entero revisado

Los dos primeros hallazgos (la clave privada y el CSV de notas) se cazaron **de rebote**, mirando
otra cosa. Ahora hay pasada sistemática: `python scripts/detectar_sensibles.py` revisa los 1.482
ficheros de texto del corpus en 5,6 s y **sale con 1 si encuentra algo bloqueante**.

| Nivel | Qué busca | Encontrado en la revisión completa |
|---|---|---|
| **Bloqueante por línea** | claves privadas, certificados, tokens de API, DNI/NIE con letra correcta, IBAN, listados de nombre con notas | **0**, tras retirar el CSV de alumnos |
| **Bloqueante por documento** | concentración de datos personales (regla nueva, más abajo) | **0**, tras retirar el CV y declarar el enunciado de BBDD |
| Aviso | correos y teléfonos | **747 ocurrencias en 176 ficheros** |

Los avisos no bloquean a propósito: en material docente el correo del profesor está en la portada de
sus propios apuntes, y una puerta permanentemente roja acaba relajada (la lección del ADR 0001).

**Cinco excepciones declaradas una a una, con su motivo**, no silenciando la categoría: un ejercicio
de validación de DNI, dos enunciados de bases de datos con personas inventadas y la explicación del
formato IBAN. Si mañana aparece un DNI en material nuevo, la puerta se pone roja igual.

### Tres hallazgos en un corpus que nadie recolectó con mala intención

**Tres**, y esa es la cifra que hay que leer completa, porque es el argumento entero de por qué esta
puerta existe:

| # | Qué | Cómo se encontró | Qué se hizo |
|---|---|---|---|
| 1 | Clave privada RSA y certificados de Kubernetes en unos apuntes de ASIR | **de rebote**, mirando el troceado | fuera del índice (3 bloques), fichero original intacto |
| 2 | CSV con nombres de alumnos, grupo y notas | **de rebote**, mirando otra cosa en el 1.5 | **borrado del disco** y del manifiesto |
| 3 | CV real de una persona: nombre, código postal, móvil, correo y cuatro redes | la **puerta de admisión** del índice, no la de sensibles | **borrado del disco** y del manifiesto |

Dos de los tres se cazaron por casualidad y el tercero lo cazó la puerta equivocada. Ninguno lo puso
nadie a propósito: son tres repositorios públicos de apuntes de profesores y alumnos. **Un corpus
recolectado de repos públicos contiene datos personales aunque nadie los haya puesto ahí queriendo**,
y por eso buscarlos tiene que ser una pasada sistemática y no un golpe de suerte. Los tres ficheros
originales venían de repos de terceros; los dos que eran datos personales de una persona
identificable **ya no están en el árbol**.

### La regla de concentración: un documento que ES datos personales

El CV enseñó un hueco, y cerrarlo **sin deshacer** la decisión de que correo y teléfono sean aviso:
esa decisión sigue siendo correcta —el correo del profesor está en la portada de sus apuntes y una
puerta permanentemente roja se acaba relajando—. Lo que faltaba era mirar el documento entero:

> **Un documento que contiene un correo no es lo mismo que un documento que ES datos personales.**
> Si las señales son densas respecto a su longitud **y de varias clases**, es hallazgo bloqueante.

La variedad de clases no es adorno: es lo que hace que el criterio funcione, y se decidió midiendo
sobre el corpus real. **Por densidad sola el CV no destacaba**: 13,8 señales por mil palabras, por
debajo de una actividad de Postgres con diez correos de ejemplo (23,3) y de unos apuntes de Docker
(15,9). Contando **valores distintos por clase** —el correo del profesor repetido en sesenta pies de
página es un dato, no sesenta— el reparto se separa solo:

| Documento | Clases | Señales / mil palabras | Veredicto |
|---|---:|---:|---|
| CV real (ya borrado) | **4** (correo, teléfono, dirección postal, redes) | **48,3** | hallazgo |
| `Primera_base_de_datos_de_alumnos.pdf.md` | 2 (correo, teléfono) | 11,5 | hallazgo → **excepción declarada** |
| Ejemplos de Docker de DWES | 2 | 2,3 | limpio |
| Apuntes con el correo del profesor en portada | 1 | 9,5 | limpio |
| Actividad de Postgres con diez correos de ejemplo | 1 | 23,3 | limpio |

Umbral: **2 clases, 3 señales y 10 por mil palabras**. Entre el último hallazgo (11,5) y el primer
documento limpio con dos clases (2,3) hay un margen de cuatro veces, no de un pelo.

El segundo hallazgo es un **enunciado del IES Gonzalo Nazareno** que manda teclear una tabla de
«alumnos»: personas inventadas, con DNI sin letra, fechas de 1956 a 1977 y direcciones que no
existen. Revisado a mano línea por línea y **declarado como excepción con su motivo**, igual que las
cuatro de DNI. Que la regla dispare ahí no es un falso positivo: es la regla haciendo su trabajo y
una persona decidiendo, que es exactamente el reparto de papeles que se buscaba.

Validada en las dos direcciones y anclada en tests: el positivo es un CV **sintético con datos
inventados** —meter el CV de alguien en la suite para probar que detectamos CV sería repetir el
problema dentro del repo—, y los negativos son ficheros reales del corpus elegidos **por estar cerca
del umbral**, no lejos.

### Los dos ficheros borrados del disco, uno a uno

**El CSV de notas** (`asir/apuntes/lora-1asir/LM/PYTHON/Entrega 3/notas.txt`): nombres de alumnos,
grupo y notas. No se puede saber si son reales o inventados para el ejercicio, y da igual: no es
temario y el coste de equivocarse es serio. Borrado del disco además de excluirlo (6 fragmentos
menos): es material de terceros y no lo queremos ni en el árbol, aunque no llegara a embedding.

**El CV** (`asir/apuntes/lora-1asir/FOL/Ejercicios/CV-Manuel-Lora-Román.odt` y su derivado): el
currículum real de una persona —nombre y apellidos, código postal y localidad, móvil, correo y sus
perfiles de Twitter, LinkedIn, Facebook y Medium—, hecho como ejercicio de FOL con sus datos de
verdad. Borrado del disco y dadas de baja sus **dos** entradas de manifiesto, la del original y la
del derivado.

Ninguno de los dos originales se reescribió: se retiraron enteros. El troceador, además, avisa de
los candidatos que encuentre para que lo decida una persona, sin excluirlos por su cuenta.

## ¿Se contradicen de verdad los dos DWES? (comprobado antes de plantar nada)

El momento 3 de la demo se apoya en que el DWES antiguo (Comesaña, ~2012) y el moderno
(joseluisgs, 2025-26) **digan cosas distintas del mismo concepto**. Eso era una suposición y podía
ser falsa: el antiguo va de **PHP** (1.018 menciones) y el moderno de **Java/Spring/Kotlin/C#**
(2.146 de Java, 1.129 de Spring), así que lo primero que había que descartar es que simplemente
cubran tecnologías distintas, que no es contradicción sino ausencia de solape.

**Sí hay solape conceptual**, comprobado con los propios embeddings: los dos tratan sesiones,
cookies, autenticación, acceso a datos, arquitectura cliente-servidor y MVC. Y en MVC **hay
contradicción literal sobre el mismo concepto**:

> **ANTIGUO** — `daw/curso2/desarrollo-web-entorno-servidor-antiguo/comesana-dwes/DWES05.pdf`,
> unidad *comesana-dwes*:
> «Este patrón pretende dividir el código en tres partes, dedicando cada una a una función definida
> y diferenciada de las otras. […] **Vista. Es la parte del modelo que se encarga de la interacción
> con el usuario.**»

> **MODERNO** — `daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-05/03-arquitecturas-web.md`,
> unidad *joseluisgs-05*:
> «El **Modelo-Vista-Controlador (MVC)** es un modelo de arquitectura que **separa los datos y la
> lógica de negocio de la interfaz de usuario** y el componente encargado de gestionar los eventos y
> las comunicaciones.»

Son incompatibles: si la Vista fuera *parte del modelo*, no habría la separación entre modelo e
interfaz que define el moderno. Un alumno que lea el primero y luego el segundo se lleva dos ideas
distintas de qué es la Vista, y el sistema debe avisar del conflicto en vez de elegir a cara o cruz.

**Segunda divergencia, sobre cookies**, más suave pero real:

> **ANTIGUO** (`DWES04.pdf`): «Una cookie es **un fichero de texto** que un sitio web guarda en el
> entorno del usuario del navegador» y, de las sesiones, «también se le conoce como **cookies del
> lado del servidor**».

> **MODERNO** (`04-estado-seguridad.md`): «**A diferencia de las sesiones**, los datos de las
> cookies se almacenan **en el navegador del cliente**», con sus atributos `HttpOnly`, `Secure` y
> `SameSite`.

Bajo el marco del moderno, "cookie del lado del servidor" es una contradicción en los términos.

**La objeción que van a hacer, y la respuesta.** «Eso no es una contradicción doctrinal, es
redacción descuidada del texto antiguo: seguramente quiso decir "la parte del patrón" y escribió
"la parte del modelo"». Probablemente sea cierto, **y da igual**, porque **esa es exactamente la
forma que toma la basura en un corpus educativo real**. Nadie publica apuntes que digan "2+2=5". Lo
que hay son formulaciones viejas que suenan bien, están escritas con seguridad y llevan al alumno a
un error que no chirría: se lee, se entiende, se memoriza mal y no salta ninguna alarma. Un detector
que solo cazara contradicciones flagrantes sería inútil contra el corpus que existe. Y para el
alumno la consecuencia es idéntica: si lee ese párrafo, se lleva una idea equivocada de qué es la
Vista, con independencia de si el autor la tenía clara y escribió rápido.

**Lo que NO se ha encontrado, dicho igual de claro:** ninguna contradicción numérica ni de hecho
duro (del tipo "el máximo son 20 cookies" contra "son 50"). Y en seguridad **coinciden**: los dos
dicen que las credenciales no van en cookies. Así que el momento 3 de la demo se plantea como lo que
es —**dos versiones del mismo concepto que no dicen lo mismo, una de 2012 y otra de 2025**—, que es
exactamente el ejemplo que la propia guía pone en el encargo 1.7 ("una definición con la sintaxis
antigua de una tecnología y otra con la vigente"), y no como un choque de cifras que no existe.

## Basura plantada (encargo 1.7)

`python scripts/plantar_basura.py --plantar` deja cinco documentos, todos declarados en el
manifiesto con `plantado: true` y un `plantado_motivo` que dice de qué tipo es cada uno. El script
sin argumentos **cuadra disco contra manifiesto y sale con 1** si sobra o falta algo: si se plantara
algo sin declarar, el detector del 1.8 encontraría un "hallazgo" que en realidad es basura nuestra
sin etiquetar, y su número dejaría de significar nada.

| Motivo | Cuántos | Qué es |
|---|---|---|
| `casi_duplicado` | 3 | copias de apuntes reales de Programación (bucles, arrays, POO) con cambios menores: sinónimos, una cifra y un párrafo reordenado |
| `contradiccion` | 1 | hoja de repaso de UD7 que contradice al temario sobre el paso de parámetros |
| `colado` | 1 | `BD05` de Bases de datos (0484) metido en la carpeta de Programación (0485) |

**La contradicción sintética, y por qué es esa.** El temario dice, en `ud7_Funciones`: «Parámetros
de tipo objeto (paso por referencias) […] no se copia el objeto sino que se le pasa a la función una
referencia al objeto original». La hoja plantada dice lo contrario: «**En Java TODOS los parámetros
se pasan por valor, también los objetos. No existe el paso por referencia en Java**». No es un "el
valor es 5" contra "es 7": es una discusión real entre materiales docentes de Java, con su
consecuencia observable (qué pasa al reasignar el parámetro dentro de la función), y está redactada
como la escribiría un profesor que corrige una simplificación de sus apuntes.

**Se plantó ANTES de escribir el detector del 1.8, y a propósito.** Si se escribiera pensando en
cómo la va a encontrar el detector, el detector no demostraría nada: sería el auditor compartiendo
supuesto con el parser (principio 6). Queda declarado el reparto de papeles: **el caso sintético es
condición necesaria** —si el detector no lo encuentra, no sirve— y **el par real del corpus es la
prueba honesta**, porque nadie lo escribió para ser encontrado.

Tras plantar: **13.096 fragmentos** (66 s de re-embebido) y las cuatro puertas en verde.

## Detector de conflictos (encargo 1.8): lo que encuentra y lo que NO

`python scripts/detectar_conflictos.py` → `corpus/conflictos.jsonl` en 39 s. Cada hallazgo guarda
los dos fragmentos, la similitud, el veredicto del NLI con su probabilidad, **las dos frases que
chocan** y **la fecha de cada fuente**, que es lo que el 4.5 necesita para ordenar por vigencia.

| Tipo | Hallazgos | Qué tan fiable es |
|---|---|---|
| `casi_duplicado` (≥0,95) | **858** | preciso; la mayoría, ficheros con el mismo nombre en sitios distintos |
| `colado` | **2** | preciso, y validado contra controles negativos |
| `contradiccion` | **361** | **candidatos para revisión humana, no hallazgos cerrados** |

Los tres números son de la pasada sobre el índice ya limpio. Antes de arreglar el 1.4 salían 1.980
casi duplicados y 769 contradicciones: **la mitad de los casi duplicados eran basura repetida**
—índices de repositorio, `index.html` de 403, listas de palabras—, no material docente duplicado, y
las contradicciones se han quedado en menos de la mitad.

**Y el tercer casi duplicado plantado, que se escapaba, ahora se encuentra: sin tocar el umbral.**
`ud5_Bucles_en_Java_v2` se quedaba en 0,946 contra un umbral de 0,95, y se dejó anotado como fallo
declarado porque bajar el umbral para que pasara mi propio plantado habría sido ajustar el detector
a la trampa. Al quitar el mobiliario de página, la copia y su original dejaron de diferenciarse en
el ruido que llevaban pegado y la similitud subió a **0,963**. El umbral sigue en 0,95: lo que
cambió fue el texto que se compara. Es la mejor prueba de que limpiar el corpus no era cosmética.

**La exclusión de solapes no era teórica: 4.021 pares** (uno de cada cuatro candidatos) son fragmentos
consecutivos del mismo documento, parecidos por el solape de 64 tokens del troceado. Sin excluirlos
el detector estaría midiendo su propia sombra. A ≥0,95 solo son 23, pero en la banda del NLI son
uno de cada seis.

**El colado necesitó dos intentos, y el primero era plausible y falso.** La señal obvia —"su
vecindario semántico cae en otra asignatura"— **no sirve**: el colado plantado marca 0,97 y
`Consultas-SQL.pdf` de Programación marca 0,89 siendo legítimo. La señal que sí discrimina es
**tener casi duplicados en otra asignatura**, porque un colado es una COPIA que aterrizó en la
carpeta equivocada:

| Documento | Casi-dup ajeno | Veredicto |
|---|---|---|
| `BD05_modelo_relacional.md` (plantado) | **0,20** | colado |
| `ud13_AccesoBBDD.pdf` (legítimo) | 0,00 | limpio |
| `Consultas-SQL.pdf` (legítimo, 11 de 15 vecinos en Bases de datos) | 0,00 | limpio |
| `LMSGI_01.pdf` (transversal 0373) | 0,00 | limpio |

**Un plantado se escapa, y se declara:** `ud5_Bucles_en_Java_v2.md` se queda en **0,946**, por debajo
del umbral de 0,95. Se miró si bajarlo, con la banda [0,93-0,95) delante: el 60% de esos pares tienen
el mismo nombre de fichero frente al 84% de la banda alta, así que **la evidencia no justifica
moverlo** y bajarlo solo para que pase mi propio plantado sería ajustar el detector a la trampa. Se
queda en 0,95 con el fallo anotado y anclado en el test.

### Lo que este detector NO encuentra, y es lo más importante

**No encuentra el par contradictorio REAL del corpus.** Los dos fragmentos que contienen las
definiciones incompatibles de la Vista de MVC tienen una similitud de **0,564**, muy por debajo de la
banda de candidatos: cada definición va enterrada en un trozo de 512 tokens lleno de otra cosa (el
antiguo, dentro de un caso práctico sobre PHP; el moderno, dentro de una discusión de arquitecturas).
La similitud entre trozos no ve una contradicción entre dos frases concretas.

Lo que haría falta es comparar **definiciones del mismo término**, y eso es exactamente lo que
produce el glosario del encargo 1.6, que está pendiente porque necesita el proveedor. **Consecuencia
declarada: el momento 3 de la demo depende del 1.6**, no del 1.8.

Y sobre el NLI, medido: a nivel de trozo daba **4.255** contradicciones, entre ellas dos salidas de
`ping` con distinta IP y dos métodos `@Test` distintos. A nivel de **frase** —que es para lo que el
modelo se entrenó— acierta de lleno en la plantada (**0,99**, señalando las dos frases que chocan) y
el ruido baja a 769. Sigue habiendo ruido (direcciones MAC, listados de paquetes), así que se
entregan como candidatos ordenados por probabilidad, no como verdad.

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

1. **1.6** — el glosario, que necesita el proveedor de inferencia. Es el que sostiene el momento 3 de
   la demo, porque el 1.8 **no** encuentra el par contradictorio real (ver más arriba). La entrada
   que le toca ya está preparada: la `frase_definitoria` de cada fragmento, con su precisión medida.
2. **2.1** — cargar el árbol oficial en `asignaturas` con su puente `titulacion_asignaturas`. El
   árbol ya está extraído y en git; lo que falta es la carga, que necesita la base de la fase 2.
4. **Limpieza pendiente:** `dam/normativa/POR-DESCARGAR.txt` y `asir/normativa/POR-DESCARGAR.txt`
   piden unos PDF que ya están dentro. Se borran junto con sus dos entradas de manifiesto cuando se
   abra el primer encargo de la fase 1, para no tocar el corpus fuera de su encargo.
