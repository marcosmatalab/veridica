# ADR 0002: el verificador de manifiesto comprueba hashes, y siempre

- **Fecha:** 11 de agosto de 2026
- **Encargo:** 1.0
- **Estado:** aceptada

## Contexto

`scripts/verificar_manifiesto.py` cruzaba conjuntos de rutas: disco contra manifiesto, en las dos
direcciones. Nada más. Un fichero alterado, truncado o copiado a medias pasaba su verde, porque su
ruta seguía estando en los dos sitios.

El precedente que lo convirtió en urgente está en el repo: los 249 ficheros con el nombre destrozado
por el descompresor se repararon con `scripts/reparar_nombres.py`, que empareja por SHA-256 del
CONTENIDO. Lo que garantizó la integridad de aquella reparación fue el hash del reparador; el verde
del verificador habría dado por buena una copia truncada. Se dio una puerta por cumplida apoyándose
en la garantía de otra herramienta.

Además, el manifiesto se leía a un diccionario por ruta, así que una entrada duplicada pisaba a la
anterior en silencio y los conteos seguían cuadrando.

## Decisión

El verificador comprueba el `hash_sha256` de cada entrada además de las rutas, leyendo por bloques,
y reporta cuatro clases contadas por separado: `SIN MANIFIESTO`, `SIN FICHERO`, `HASH DISTINTO` y
`RUTA DUPLICADA`. Sale con 1 ante cualquier ocurrencia, y con 2 si el manifiesto es ilegible o está
mal formado, que no es lo mismo que un corpus roto y no debe confundirse con él.

**Se comprueba siempre: no hay modo `--solo-rutas`.** La guía dejaba esa bandera condicionada a que
hashear "molestara en bucle". Medido sobre el corpus real: **0,9 s** para 2.097 ficheros y 391 MB.
La condición no se cumple, así que la bandera no se escribe. Un modo débil que nadie necesita solo
sirve para que alguien lo use un día con prisa y crea que ha verificado algo.

El manifiesto **no se supone inmutable**: va a crecer en el encargo 1.3 con los ficheros
normalizados. Las entradas se leen con tolerancia (solo se exigen `ruta` y `hash_sha256`; cualquier
campo nuevo se ignora sin protestar), y hay un test que lo fija con campos `derivado_de` y `origen`.

## Trade-off

Se paga ~1 s por corrida y la obligación de re-registrar el hash cuando un fichero del corpus cambia
a propósito (editar `COBERTURA.md` ahora exige actualizar su entrada). Es fricción real y deseada:
un cambio no declarado en el corpus debe doler un poco.

Lo que se gana: la puerta detecta el fallo para el que existe. Y detecta el caso que la versión
anterior no podía ver ni en principio: mismo nombre, mismo tamaño, contenido distinto.

## Evidencia (validación del principio 3)

- Test anclado sobre corpus de juguete: se cambia **un byte sin variar el tamaño** y el verificador
  sale con 1 nombrando el fichero. Más borrado, sobrante, duplicado, campos nuevos y manifiesto mal
  formado. Doce tests en total, en CI, sin necesidad del corpus real.
- Prueba de mutación con el diff a la vista: quitando la comparación de hash cae el test del byte;
  quitando la detección de duplicados cae el suyo.
- Sobre el **corpus real**: verde en 0,9 s (2.097 ficheros); y con un byte cambiado en
  `corpus/COBERTURA.md`, `HASH DISTINTO` con los dos hashes y salida 1.
- Un fallo real que cazaron los propios tests al escribirlos: `sys.exit("mensaje")` sale con 1, no
  con 2, así que un manifiesto ilegible se habría confundido con un hallazgo de integridad.

## Cuándo se revisa

Si el corpus crece hasta que 1 s se vuelva molesto (órdenes de magnitud más, o ingesta en bucle),
se revisa con el número delante: primero paralelizar el hasheo, y solo después considerar un modo
parcial, que entonces sí tendría motivo medido.
