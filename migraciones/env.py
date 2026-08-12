"""Entorno de Alembic (encargo 2.1).

Sin SQLAlchemy ORM: el DDL de la seccion 9 se escribe tal cual en SQL. Alembic esta aqui por lo
que aporta de verdad -una version de esquema en la base, migraciones ordenadas y reversibles- y no
por su capacidad de generar DDL a partir de modelos, que aqui seria una capa de traduccion entre
lo que dice la guia y lo que acaba en Postgres.

La URL sale de DATABASE_URL. Desde Windows, contra el contenedor:
    DATABASE_URL=postgresql://veridica:veridica_local@127.0.0.1:5434/veridica
"""
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

configuracion = context.config
URL = os.environ.get("DATABASE_URL")
if not URL:
    raise SystemExit(
        "DATABASE_URL no esta puesta. Desde Windows contra el compose local:\n"
        "  DATABASE_URL=postgresql://veridica:veridica_local@127.0.0.1:5434/veridica")
# "postgresql://" a secas hace que SQLAlchemy busque psycopg2, que NO esta en requirements: el
# driver anclado es psycopg 3. Se fuerza aqui para que la misma URL valga para la app y para las
# migraciones, en vez de tener dos cadenas de conexion distintas que se separan solas.
if URL.startswith("postgresql://"):
    URL = URL.replace("postgresql://", "postgresql+psycopg://", 1)
configuracion.set_main_option("sqlalchemy.url", URL)


def migrar_sin_conexion():
    context.configure(url=URL, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def migrar_con_conexion():
    motor = engine_from_config(configuracion.get_section(configuracion.config_ini_section, {}),
                               prefix="sqlalchemy.", poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(connection=conexion)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    migrar_sin_conexion()
else:
    migrar_con_conexion()
