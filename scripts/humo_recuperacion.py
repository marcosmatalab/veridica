#!/usr/bin/env python3
"""Encargo 1.5: busqueda de humo sobre los vectores, EN LAS DOS DIRECCIONES.

La primera direccion es la que pide la guia: una consulta cuya respuesta esta en el temario tiene
que devolver fragmentos de la unidad correcta.

La segunda es el corolario del principio 6, y es la que de verdad ensena algo: se lanza una
consulta cuya respuesta NO esta en el corpus y se mira que devuelve. Va a devolver algo, y con
buena puntuacion, porque la similitud coseno siempre encuentra su vecino mas cercano: no sabe decir
"esto no esta". Ese numero es la LINEA BASE que justifica la capa de verificacion entera, y es la
abstencion de la fase 4 vista desde el otro lado. Sale gratis medirla hoy.

Uso:
    python scripts/humo_recuperacion.py
"""
import json
import sys

import numpy as np

VECTORES = "corpus/embeddings/vectores.npy"
IDS = "corpus/embeddings/ids.jsonl"
FRAGMENTOS = "corpus/fragmentos.jsonl"

DENTRO = [
    ("que es una clave primaria", "bases de datos / programacion"),
    ("como se declara un bucle for en Java", "programacion"),
    ("que es un cortafuegos", "seguridad, ASIR"),
]
FUERA = [
    ("cuando se poda un olivo joven", "agricultura: no esta en un ciclo de informatica"),
    ("cual es la dosis de paracetamol para un nino de 20 kilos", "medicina"),
    ("quien gano el mundial de futbol de 1978", "deporte"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    import torch
    from sentence_transformers import SentenceTransformer

    sys.path.insert(0, "scripts")
    from embeber import MODELO, REVISION

    vectores = np.load(VECTORES)
    with open(IDS, encoding="utf-8") as f:
        ids = [json.loads(linea) for linea in f if linea.strip()]
    fragmentos = {}
    with open(FRAGMENTOS, encoding="utf-8") as f:
        for linea in f:
            fr = json.loads(linea)
            fragmentos[(fr["documento"], fr["orden"])] = fr

    modelo = SentenceTransformer(MODELO, revision=REVISION,
                                 device="cuda" if torch.cuda.is_available() else "cpu")
    modelo.max_seq_length = 512

    def buscar(consulta: str, k: int = 3):
        v = modelo.encode([consulta], normalize_embeddings=True, convert_to_numpy=True)[0]
        puntos = vectores @ v
        mejores = np.argsort(-puntos)[:k]
        return [(float(puntos[i]), ids[i]) for i in mejores]

    print("=" * 78)
    print("DIRECCION 1: la respuesta ESTA en el temario")
    print("=" * 78)
    for consulta, esperado in DENTRO:
        print(f"\n  «{consulta}»   (se espera: {esperado})")
        for punto, clave in buscar(consulta):
            fr = fragmentos.get((clave["documento"], clave["orden"]), {})
            print(f"    {punto:.3f}  {clave['asignatura']:22} {fr.get('unidad') or '-'}")
            print(f"            {(fr.get('texto') or '')[:95].strip()}")

    print("\n" + "=" * 78)
    print("DIRECCION 2: la respuesta NO esta en el corpus (la linea base)")
    print("=" * 78)
    peores = []
    for consulta, que_es in FUERA:
        resultados = buscar(consulta)
        peores.append(resultados[0][0])
        print(f"\n  «{consulta}»   ({que_es})")
        for punto, clave in resultados:
            fr = fragmentos.get((clave["documento"], clave["orden"]), {})
            print(f"    {punto:.3f}  {clave['asignatura']:22} {fr.get('unidad') or '-'}")
            print(f"            {(fr.get('texto') or '')[:95].strip()}")

    print("\n" + "-" * 78)
    print(f"La similitud NUNCA dice 'esto no esta': la mejor puntuacion de una pregunta fuera de")
    print(f"temario ha sido {max(peores):.3f} y la media {sum(peores)/len(peores):.3f}.")
    print("Esa es la linea base: sin capa de verificacion, el sistema contestaria a las tres con")
    print("material del temario, y con aplomo. La abstencion de la fase 4 es lo que arregla esto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
