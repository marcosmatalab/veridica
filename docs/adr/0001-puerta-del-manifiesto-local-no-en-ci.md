# ADR 0001: la puerta del manifiesto es local, no de CI

- **Fecha:** 11 de agosto de 2026
- **Encargo:** 0.2 (CI)
- **Estado:** aceptada

## Contexto

`scripts/verificar_manifiesto.py` es la puerta de integridad del corpus: cruza disco contra
manifiesto y, a partir del encargo 1.0, comprobará también el `hash_sha256` de cada entrada.

El corpus vive fuera de git por decisión de la fase 0 (son ~390 MB y 2.097 ficheros, parte de ellos
con licencias que no permiten redistribución: los repos de apuntes sin licencia declarada están
registrados como "uso local, no redistribuible"). El runner de GitHub Actions, por tanto, clona un
repo **sin corpus**: el verificador allí no tendría nada que verificar.

Las tres salidas posibles eran: (a) meterlo en CI igual, (b) meterlo en CI con un salto condicional
si la carpeta no existe, o (c) dejarlo como puerta local.

## Decisión

Opción (c): **el verificador de manifiesto no entra en el CI.** Es una puerta local, documentada en
`CLAUDE.md` con su comando, que se corre antes de commitear cualquier cambio del corpus.

Descartadas: (a) sería un rojo permanente, y una puerta que siempre está roja acaba relajada o
ignorada, que es peor que no tenerla, porque además engaña; (b) un paso que se salta solo cuando
falta el corpus es verde en el 100% de las corridas de CI y nunca ha comprobado nada: es un verde que
miente, exactamente lo que el principio 3 de la guía prohíbe.

Los tests que SÍ entran en CI son los que corren sobre un corpus de juguete en directorio temporal
(`tests/test_anadir_al_manifiesto.py`, y el test anclado del encargo 1.0 cuando se escriba). Así la
lógica del verificador está cubierta en CI aunque el corpus real no esté.

## Trade-off

Lo que se pierde: la integridad del corpus deja de tener puerta automática y pasa a depender de que
una persona corra un comando. Un fichero corrompido o un manifiesto desincronizado pueden vivir en la
máquina de Marcos sin que nada avise, y el CI seguirá verde.

Lo que se gana: ninguna puerta del repo miente. Las que corren, corren de verdad y sobre algo real.

Mitigaciones, en orden de coste: el encargo 1.0 hace que la puerta local detecte de verdad
(hash, no solo ruta), que es lo que hoy no hace; y el arnés de ingesta de la fase 1 volverá a
comprobar hashes al leer cada documento, así que la corrupción tiene un segundo sitio donde salir.

## Cuándo se revisa

Si el corpus llega a ser publicable (licencias resueltas) o aparece una muestra pequeña versionable,
esta decisión se reabre: con corpus en el runner, la puerta vuelve al CI y este ADR se supera.
