#!/usr/bin/env python3
"""Renderiza TODOS los bloques ```mermaid del repo con el mermaid de verdad.

    python scripts/comprobar_diagramas.py            # todos los .md rastreados
    python scripts/comprobar_diagramas.py README.md

## POR QUÉ EXISTE, con el caso que lo pagó

El 15 de agosto de 2026 el README traía un `gantt` que **daba error en GitHub** —*"Unable to render
rich display · Cannot read properties of undefined"*— mientras aquí se daba por bueno. **Dos puertas
midiendo cosas distintas, y la que vale es la que ve quien abre el repo:** un diagrama que solo
renderiza en mi cabeza es un diagrama roto en el único sitio donde se mira.

**Comprobar la sintaxis con un parser propio no sirve**, porque el fallo no estaba en la sintaxis que
yo sabía mirar: estaba en lo que la versión de mermaid de GitHub hace con ella. Así que esto llama al
**renderizador de verdad** (`@mermaid-js/mermaid-cli`, que es mermaid dentro de un Chromium) y exige
un SVG. Si no sale SVG, el diagrama está roto y da igual lo bien que se lea el texto.

## Lo que este script NO puede prometer

**No es GitHub.** GitHub fija su propia versión de mermaid y puede ir por detrás o por delante de la
que haya instalada aquí, así que esto **reduce** la distancia entre las dos puertas, no la cierra. La
versión con la que se comprobó se imprime siempre, porque un verde sin decir con qué versión se
consiguió es la mitad de la información.

## Requisito, y por qué no está en `requirements-dev.txt`

Necesita `node` y `npx`. **No entra en las puertas del CI** por el mismo motivo que el manifiesto
(ADR 0001): añadir una descarga de Chromium a cada push cuesta más de lo que ahorra. Se corre a mano
antes de tocar un diagrama, que es cuando puede romperse. Sin `npx`, sale con **2** —"no he podido
comprobarlo"—, que no es lo mismo que **1** —"está roto"—.
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
BLOQUE = re.compile(r"^```mermaid\n(.*?)^```", re.M | re.S)


def diagramas(ruta: pathlib.Path):
    texto = ruta.read_text(encoding="utf-8")
    for n, m in enumerate(BLOQUE.finditer(texto), 1):
        linea = texto[:m.start()].count("\n") + 1
        yield n, linea, m.group(1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ficheros", nargs="*", default=None)
    a = ap.parse_args()

    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx is None:
        print("sin `npx`: no se puede comprobar el renderizado (no es lo mismo que estar roto)",
              file=sys.stderr)
        return 2

    ficheros = [pathlib.Path(f) for f in a.ficheros] if a.ficheros else [
        RAIZ / f for f in subprocess.run(
            ("git", "ls-files", "*.md"), cwd=RAIZ, capture_output=True, text=True
        ).stdout.split()]

    rotos, total = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for ruta in ficheros:
            if not ruta.exists():
                continue
            for n, linea, cuerpo in diagramas(ruta):
                total += 1
                # `relative_to` REVIENTA si el fichero esta fuera del repo, y eso convertia el
                # rojo de la puerta en un rojo de la puerta ROTA: mismo codigo de salida, motivo
                # distinto. Se cazo validandola contra el gantt que GitHub rechaza, que es para lo
                # que sirve validar en la direccion contraria.
                try:
                    nombre = ruta.relative_to(RAIZ).as_posix()
                except ValueError:
                    nombre = ruta.as_posix()
                entrada = pathlib.Path(tmp) / f"d{total}.mmd"
                salida = pathlib.Path(tmp) / f"d{total}.svg"
                entrada.write_text(cuerpo, encoding="utf-8")
                hecho = subprocess.run((npx, "--no-install", "mmdc", "-i", str(entrada),
                                        "-o", str(salida)), capture_output=True, text=True)
                # SE COMPRUEBA QUE EL SVG EXISTE, no el codigo de salida: `mmdc` ha llegado a salir
                # con 0 dejando el error en la salida y sin escribir nada, que es exactamente el
                # verde que no ha comprobado nada.
                if salida.exists() and salida.stat().st_size > 0:
                    print(f"  OK  {nombre}:{linea}  ({cuerpo.split(chr(10))[0].strip()})")
                else:
                    rotos.append(f"{nombre}:{linea}")
                    fallo = (hecho.stderr or hecho.stdout or "").strip().splitlines()
                    print(f"  NO  {nombre}:{linea}  ({cuerpo.split(chr(10))[0].strip()})")
                    for renglon in fallo[:3]:
                        print(f"        {renglon[:160]}")

    version = subprocess.run((npx, "--no-install", "mmdc", "--version"),
                             capture_output=True, text=True).stdout.strip()
    print(f"\n{total - len(rotos)}/{total} diagramas renderizan · mermaid-cli {version or '?'}")
    if rotos:
        print("ROTOS: " + ", ".join(rotos))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
