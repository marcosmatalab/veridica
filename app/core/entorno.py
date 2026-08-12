"""Lee el `.env` para los procesos que corren FUERA de compose (encargo 2.2).

La API y el worker reciben su entorno de `compose.yml`. Pero la ingesta, la carga del 2.1 y el humo
del proveedor corren en Windows, y allí no hay nadie que lea el `.env`. Doce líneas propias en vez de
una dependencia más, y con la regla que importa: **lo que ya esté en el entorno manda**, para que
`INFERENCIA_API_KEY=... python script.py` siga funcionando y para que el CI —donde la clave viene del
secret y no hay `.env`— no dependa de un fichero que no existe.
"""
import os


def cargar_dotenv(ruta: str = ".env") -> int:
    """Mete en `os.environ` lo que falte. Devuelve cuántas variables ha puesto."""
    if not os.path.exists(ruta):
        return 0
    puestas = 0
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            nombre, valor = linea.split("=", 1)
            nombre, valor = nombre.strip(), valor.strip().strip('"').strip("'")
            if nombre and valor and nombre not in os.environ:
                os.environ[nombre] = valor
                puestas += 1
    return puestas
