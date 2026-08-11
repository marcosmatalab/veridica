-- Encargo 0.3: extensiones que pide la seccion 9 de la guia.
--
-- OJO con lo que este fichero NO garantiza: docker-entrypoint-initdb.d solo se ejecuta en la
-- PRIMERA inicializacion del volumen. Un volumen creado antes de que este script existiera no lo
-- vera nunca, y el IF NOT EXISTS no arregla eso porque ni siquiera llega a correr.
-- Por eso GET /salud comprueba en cada arranque que las dos extensiones estan de verdad,
-- en vez de suponerlo: la idempotencia util es la del arranque, no la de esta linea.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
