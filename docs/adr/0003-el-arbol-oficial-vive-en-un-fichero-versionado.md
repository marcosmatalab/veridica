# ADR 0003: el árbol oficial vive en un fichero versionado, no en la base de datos

- **Fecha:** 11 de agosto de 2026
- **Encargo:** 1.1
- **Estado:** aceptada

## Contexto

El encargo 1.1 mandaba extraer el árbol oficial de las tres titulaciones desde los PDF del BOE y
**cargarlo en `asignaturas` y `titulacion_asignaturas`**. Pero esas tablas no existen hasta el
encargo 2.1 (esquema y migraciones): el encargo, tal como estaba escrito, no se podía ejecutar en su
turno. Había que decidir dónde vive el árbol mientras tanto.

## Decisión

El 1.1 produce **`corpus/arbol_oficial.jsonl`**, una línea por nodo (titulación, asignatura, unidad,
resultado de aprendizaje), y el **2.1 lo carga** en base de datos cuando las tablas existan.

Formato JSONL con un nodo por línea, no JSON anidado: así un cambio en una unidad mueve una línea en
el `diff` y no un bloque entero. Cada nodo lleva su referencia legal —norma, documento y página del
PDF—, que es lo que permite comprobarlo contra el BOE sin volver a extraer nada.

Vive bajo `corpus/` junto al manifiesto y el mapa de cobertura, porque es metadato del corpus de la
misma clase que ellos, y entra en git como tercera excepción del `.gitignore`. Coste asumido: como
está bajo `corpus/`, necesita su entrada en el manifiesto (el verificador del 1.0 exige que todo lo
que hay ahí esté declarado).

## Trade-off

Se pierde: el árbol no está consultable por SQL hasta el 2.1, y hay un paso de carga que mantener.

Se gana: se revisa con `diff` en cada cambio (un árbol cargado a mano en una base viva no deja
rastro de qué cambió ni cuándo), no depende de que Postgres esté levantado, sobrevive a un
`down -v`, y viaja en el clon limpio, así que un tercero ve el árbol sin arrancar nada.

## Lo que se decidió al ejecutarlo, con su porqué

1. **Fuentes distintas por titulación, declaradas.** DAW y DAM salen de sus reales decretos de 2010
   **actualizados por el RD 405/2023** (9 de 13 módulos de DAW y 11 de 14 de DAM vienen del texto de
   2023); ASIR sale del RD 1629/2009, al que el 405/2023 no toca. Además DAW tiene la Orden
   EDU/2887/2010, que amplía contenidos módulo a módulo: sus unidades salen más finas (6,2 por
   módulo frente a 4,7 de sus hermanas) y eso es la fuente, no el extractor. Escrito en
   `corpus/COBERTURA.md` junto al árbol.
2. **`curso` nulo en DAM y ASIR.** El reparto entre primero y segundo no lo fija el real decreto del
   título, lo fija la orden de currículo, y solo tenemos la de DAW (su Anexo II, leído **por
   coordenadas** porque en texto plano las columnas se pisan y no se distingue un 5 de primero de un
   5 de segundo). Rellenarlo por analogía en un fichero que presume de referencia legal por nodo
   sería justo lo contrario de lo que se construye aquí, así que va nulo con su motivo en el propio
   nodo (`curso_nota`).
3. **`horas` solo desde la Orden.** Los reales decretos dan duraciones mínimas estatales, de otra
   magnitud que las del currículo completo: en DAW conviven y se ve el salto (100 o 135 horas en el
   RD donde la Orden dice 170 o 230). Mezclarlas daría una columna que compara peras con manzanas.
4. **Un cruce, no un printout.** El extractor compara los códigos que saca del Anexo I contra la
   lista de módulos que cada norma declara en su articulado, que es otra parte del documento, y
   **sale con 1 si no cuadran**: 13/13 en DAW, 14/14 en DAM, 14/14 en ASIR.

## Evidencia (validación del principio 3)

- Tests sobre un **PDF de juguete** fabricado con fpdf2, pasado por la tubería real (pypdf incluido),
  así que corren en CI sin el corpus. El caso anclado reproduce el fallo real: cuando la cabecera del
  BOE cae entre el nombre del módulo y su código, el módulo debe extraerse igual. Ese fallo hacía que
  el módulo 0483 de DAM se leyera del RD de 2010 en vez de su actualización de 2023, en silencio.
- Prueba de mutación con el diff delante: quitando la limpieza del mobiliario del BOE caen 5 de los
  6 tests.
- Un fallo que **no cazaron los tests sino el muestreo a mano**: se colaban como "unidad" frases del
  apartado de orientaciones pedagógicas que terminan en dos puntos ("La función de programación de
  bases de datos incluye aspectos como:"). Acotando la búsqueda a la sección de contenidos
  desaparecieron 49 unidades falsas (DAM 86→66, ASIR 96→67). Es el argumento del muestreo en una
  frase: los tests comprueban lo que sabes que puede fallar; el muestreo encuentra lo que no.

## Lo que este encargo NO garantiza

El número de acuerdo del muestreo de diez nodos (`docs/muestreo-arbol-oficial.md`) lo pone una
persona contra el BOE, no el extractor: comprobarse a sí mismo contra el PDF del que acaba de
extraer no verificaría nada. Y diez nodos comprobados no dicen que los 519 estén bien: dicen lo que
dice un muestreo de diez.
