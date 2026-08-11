#!/usr/bin/env python3
"""Re-registra en el manifiesto el hash de ficheros que han cambiado A PROPOSITO.

Esto NO es un boton de "poner el verificador en verde". Por eso:
  - exige las rutas UNA A UNA en la linea de ordenes; no hay modo "arreglalo todo",
  - solo toca entradas que ya existen (para dar de alta un fichero nuevo, anadir_al_manifiesto.py),
  - imprime el hash viejo y el nuevo de cada una, para que el cambio se vea.

Un "actualiza todos los hashes que no cuadren" convertiria la puerta del encargo 1.0 en un adorno:
cualquier corrupcion quedaria registrada como si fuera un cambio querido.

Uso:
    python scripts/actualizar_hash_manifiesto.py corpus/COBERTURA.md corpus/arbol_oficial.jsonl
"""
import hashlib
import json
import sys

MANIFIESTO = "corpus/manifiesto.jsonl"
BLOQUE = 1 << 20


def sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(BLOQUE), b""):
            h.update(bloque)
    return h.hexdigest()


def main() -> int:
    rutas = sys.argv[1:]
    if not rutas:
        sys.exit(__doc__)

    with open(MANIFIESTO, encoding="utf-8") as f:
        entradas = [json.loads(linea) for linea in f if linea.strip()]

    por_ruta = {e["ruta"]: e for e in entradas}
    desconocidas = [r for r in rutas if r not in por_ruta]
    if desconocidas:
        sys.exit("no estan en el manifiesto (usa anadir_al_manifiesto.py): "
                 + ", ".join(desconocidas))

    cambiadas = 0
    for ruta in rutas:
        entrada = por_ruta[ruta]
        nuevo = sha256(ruta)
        if nuevo == entrada["hash_sha256"]:
            print(f"sin cambios: {ruta}")
            continue
        print(f"{ruta}\n  antes  {entrada['hash_sha256']}\n  ahora  {nuevo}")
        entrada["hash_sha256"] = nuevo
        cambiadas += 1

    if cambiadas:
        with open(MANIFIESTO, "w", encoding="utf-8", newline="\n") as f:
            for e in entradas:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"entradas actualizadas: {cambiadas} de {len(rutas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
