#!/usr/bin/env python3
"""Encargo 1.5: embebe los fragmentos con BGE-M3 y anota lo que cuesta.

Salida (una entrada de manifiesto cada una, y solo estas):
    corpus/embeddings/vectores.npy       matriz N x 1024
    corpus/embeddings/ids.jsonl          que fragmento es cada fila, en el mismo orden
    corpus/medidas-ingesta.json          configuracion completa y coste medido

Los CHECKPOINTS no van al corpus: viven en .trabajo/embeddings/ (fuera de git y fuera del
manifiesto). Si cada checkpoint dejara su entrada, el manifiesto se llenaria de ruido que cambia en
cada corrida; lo que se registra es el fichero final consolidado, como con fragmentos.jsonl.

REVISION ANCLADA. No basta con el nombre del modelo: si mañana se publica una revision nueva de
BGE-M3, los vectores nuevos no serian comparables con los viejos y no habria forma de saberlo
mirando el fichero. Se fija el sha del commit y se guarda en medidas-ingesta.json junto con
precision, normalizacion y longitud maxima: sin eso los embeddings son irreproducibles, que es
justo lo que el manifiesto existe para evitar.

Los vectores van a FICHERO y no a Postgres porque las tablas no existen hasta el encargo 2.1
(mismo desfase de orden que se corrigio en el 1.1). El 2.1 los carga con COPY.

Uso:
    python scripts/embeber.py --limite 200          # prueba corta
    python scripts/embeber.py                       # la tanda entera
    python scripts/embeber.py --dispositivo cpu     # forzar CPU
"""
import argparse
import json
import os
import shutil
import sys
import time

import numpy as np

MODELO = "BAAI/bge-m3"
REVISION = "5617a9f61b028005a4858fdac845db406aefb181"   # anclada a proposito
DIMENSION = 1024
LARGO_MAXIMO = 8192          # el maximo real del modelo: asi no se trunca ningun fragmento
FRAGMENTOS = "corpus/fragmentos.jsonl"
SALIDA = "corpus/embeddings"
TRABAJO = ".trabajo/embeddings"
MEDIDAS = "corpus/medidas-ingesta.json"
CADA = 20                    # checkpoint cada N lotes


def cargar_fragmentos(camino: str, limite=None) -> list:
    fragmentos = []
    with open(camino, encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                fragmentos.append(json.loads(linea))
            if limite and len(fragmentos) >= limite:
                break
    return fragmentos


def texto_a_embeber(fr: dict) -> str:
    """Lo que se embebe es el fragmento ENTERO, contexto incluido: es la decision del 1.4 y por eso
    los 512 tokens lo cuentan dentro."""
    return fr["contexto"] + "\n\n" + fr["texto"]


def hechos_hasta_ahora(trabajo: str) -> tuple:
    """Lee los checkpoints ya escritos. La reanudacion se apoya en esto, no en un contador."""
    if not os.path.isdir(trabajo):
        return [], []
    vectores, claves = [], []
    for nombre in sorted(os.listdir(trabajo)):
        if not nombre.endswith(".npy"):
            continue
        base = nombre[:-4]
        ids = os.path.join(trabajo, base + ".ids.jsonl")
        if not os.path.exists(ids):
            continue          # checkpoint a medias: se ignora y se rehace
        vectores.append(np.load(os.path.join(trabajo, nombre)))
        with open(ids, encoding="utf-8") as f:
            claves.extend(json.loads(linea) for linea in f if linea.strip())
    return vectores, claves


def guardar_checkpoint(trabajo: str, indice: int, vectores: np.ndarray, claves: list):
    """El .npy se escribe ANTES que su .ids.jsonl: si el proceso muere entre medias, el checkpoint
    queda sin ids y se ignora al reanudar, en vez de dar por buenos vectores sin dueño."""
    os.makedirs(trabajo, exist_ok=True)
    base = os.path.join(trabajo, f"lote_{indice:05d}")
    np.save(base + ".npy", vectores)
    with open(base + ".ids.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for clave in claves:
            f.write(json.dumps(clave, ensure_ascii=False) + "\n")


def suma_de_bytes(raiz: str, excluir=()) -> int:
    total = 0
    for base, _, ficheros in os.walk(raiz):
        base = base.replace(os.sep, "/")
        if any(base.startswith(x) for x in excluir):
            continue
        for nombre in ficheros:
            total += os.path.getsize(os.path.join(base, nombre))
    return total


def vram_usada_mb() -> float:
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.max_memory_allocated() / 1048576, 1)
    except Exception:  # noqa: BLE001
        pass
    return 0.0


def main() -> int:
    p = argparse.ArgumentParser(description="Embebe los fragmentos con BGE-M3 (encargo 1.5).")
    p.add_argument("--limite", type=int, default=None, help="solo los primeros N fragmentos")
    p.add_argument("--dispositivo", default=None, choices=["cuda", "cpu"])
    p.add_argument("--lote", type=int, default=32)
    p.add_argument("--trabajo", default=TRABAJO)
    p.add_argument("--salida", default=SALIDA)
    p.add_argument("--reiniciar", action="store_true", help="tira los checkpoints y empieza de cero")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    # Las medidas oficiales solo se escriben cuando la tanda es la oficial. Una prueba corta con
    # --salida en otro sitio pisaba corpus/medidas-ingesta.json y dejaba los numeros de la prueba
    # como si fueran los buenos: exactamente el tipo de mentira que este fichero existe para evitar.
    medidas_en = MEDIDAS if a.salida == SALIDA else os.path.join(a.salida, "medidas-ingesta.json")

    import torch
    from sentence_transformers import SentenceTransformer

    if a.reiniciar and os.path.isdir(a.trabajo):
        shutil.rmtree(a.trabajo)

    dispositivo = a.dispositivo or ("cuda" if torch.cuda.is_available() else "cpu")
    precision = "float16" if dispositivo == "cuda" else "float32"
    print(f"dispositivo: {dispositivo} | precision: {precision} | torch {torch.__version__}")
    if dispositivo == "cuda":
        print(f"  {torch.cuda.get_device_name(0)} | capability {torch.cuda.get_device_capability()}")

    fragmentos = cargar_fragmentos(FRAGMENTOS, a.limite)
    vectores_previos, claves_previas = hechos_hasta_ahora(a.trabajo)
    ya = len(claves_previas)
    if ya:
        print(f"reanudando: {ya} fragmentos ya embebidos en {a.trabajo}")
    pendientes = fragmentos[ya:]
    if not pendientes:
        print("nada pendiente")

    t0 = time.perf_counter()
    modelo = SentenceTransformer(
        MODELO, revision=REVISION, device=dispositivo,
        model_kwargs={"torch_dtype": torch.float16 if precision == "float16" else torch.float32},
    )
    modelo.max_seq_length = LARGO_MAXIMO
    carga = time.perf_counter() - t0
    print(f"modelo cargado en {carga:.1f}s (revision {REVISION[:12]})")

    t1 = time.perf_counter()
    nuevos_vectores, nuevas_claves, indice = [], [], len(vectores_previos)
    for inicio in range(0, len(pendientes), a.lote):
        tanda = pendientes[inicio:inicio + a.lote]
        # Los fragmentos largos (codigo que no se parte por ventana ciega) van de uno en uno:
        # un lote de 32 de 6.900 tokens no cabe en 16 GB, y truncarlos seria perder el codigo.
        tam = 1 if max(fr["tokens"] for fr in tanda) > 1024 else len(tanda)
        vectores = modelo.encode([texto_a_embeber(fr) for fr in tanda],
                                 batch_size=tam, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)
        nuevos_vectores.append(vectores.astype(np.float32))
        nuevas_claves.extend({"documento": fr["documento"], "orden": fr["orden"],
                              "asignatura": fr["asignatura"]} for fr in tanda)
        if len(nuevos_vectores) % CADA == 0:
            guardar_checkpoint(a.trabajo, indice, np.vstack(nuevos_vectores), nuevas_claves)
            indice += 1
            vectores_previos.append(np.vstack(nuevos_vectores))
            claves_previas.extend(nuevas_claves)
            nuevos_vectores, nuevas_claves = [], []
            # El contador cuenta lo CONSOLIDADO mas lo que va en curso. La primera version sumaba
            # solo lo que llevaba desde el ultimo checkpoint, asi que decia "640/13030 a 20/s"
            # cuando iban 7.680 a 170/s: el instrumento mintiendo, y ademas en el numero que va al
            # README.
            hechos = len(claves_previas) + len(nuevas_claves)
            ritmo = (hechos - ya) / (time.perf_counter() - t1)
            print(f"  {hechos}/{len(fragmentos)} fragmentos | {ritmo:.1f}/s | "
                  f"VRAM {vram_usada_mb()} MB", flush=True)
    if nuevos_vectores:
        guardar_checkpoint(a.trabajo, indice, np.vstack(nuevos_vectores), nuevas_claves)
        vectores_previos.append(np.vstack(nuevos_vectores))
        claves_previas.extend(nuevas_claves)

    segundos = time.perf_counter() - t1
    matriz = np.vstack(vectores_previos) if vectores_previos else np.zeros((0, DIMENSION))
    os.makedirs(a.salida, exist_ok=True)
    np.save(os.path.join(a.salida, "vectores.npy"), matriz)
    with open(os.path.join(a.salida, "ids.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for clave in claves_previas:
            f.write(json.dumps(clave, ensure_ascii=False) + "\n")

    # Ritmo de LO EMBEBIDO EN ESTA TANDA, no del total: en una tanda reanudada, dividir el total
    # entre el tiempo de esta pasada da un numero inventado (decia 535/s cuando eran 220/s).
    embebidos_ahora = len(fragmentos) - ya
    ritmo = embebidos_ahora / segundos if segundos else 0

    # Extrapolacion a un tera, calculada con lo medido en este corpus y no a ojo. El supuesto que
    # la sostiene se declara con ella: este corpus es sobre todo PDF DIGITAL, que destila a texto
    # en torno a 35 a 1. Un tera de cliente real (escaneos y video) encoge mucho mas, asi que da
    # MENOS fragmentos por tera, no mas: esta cifra es el techo pesimista.
    binario = suma_de_bytes("corpus", excluir=("corpus/derivado", "corpus/embeddings"))
    texto = suma_de_bytes("corpus/derivado")
    ratio = binario / texto if texto else 0
    por_mb = len(matriz) / (texto / 1048576) if texto else 0
    fragmentos_por_tera = por_mb * (1048576 / ratio) if ratio else 0
    extrapolacion = {
        "supuesto": "mismo reparto de formatos que este corpus (sobre todo PDF digital)",
        "binario_mb": round(binario / 1048576, 1), "texto_util_mb": round(texto / 1048576, 1),
        "ratio_binario_a_texto": round(ratio, 1),
        "fragmentos_por_mb_de_texto": round(por_mb, 1),
        "fragmentos_por_tera": round(fragmentos_por_tera),
        "horas_de_embebido_por_tera": round(fragmentos_por_tera / ritmo / 3600, 1) if ritmo else None,
        "gb_de_vectores_por_tera_float32": round(fragmentos_por_tera * DIMENSION * 4 / 1073741824, 1),
        "gb_de_vectores_por_tera_float16": round(fragmentos_por_tera * DIMENSION * 2 / 1073741824, 1),
    }
    medidas = {
        "extrapolacion_a_un_tera": extrapolacion,
        "reanudada": ya > 0, "embebidos_en_esta_tanda": embebidos_ahora,
        "modelo": MODELO, "revision": REVISION, "dimension": DIMENSION,
        "precision": precision, "normalizados": True, "largo_maximo": LARGO_MAXIMO,
        "dispositivo": dispositivo, "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0) if dispositivo == "cuda" else None,
        "fragmentos": len(matriz), "lote": a.lote,
        "segundos_carga_modelo": round(carga, 1), "segundos_embebido": round(segundos, 1),
        "fragmentos_por_segundo": round(ritmo, 1), "vram_maxima_mb": vram_usada_mb(),
    }
    os.makedirs(os.path.dirname(medidas_en) or ".", exist_ok=True)
    with open(medidas_en, "w", encoding="utf-8", newline="\n") as f:
        json.dump(medidas, f, ensure_ascii=False, indent=2)

    print(f"\n{len(matriz)} vectores de {matriz.shape[1] if len(matriz) else 0} dimensiones "
          f"-> {a.salida}/vectores.npy")
    print(f"tiempo: {segundos:.1f}s embebiendo {embebidos_ahora} fragmentos "
          f"({ritmo:.1f}/s) + {carga:.1f}s de carga")
    print(f"VRAM maxima: {vram_usada_mb()} MB | medidas -> {medidas_en}")

    if len(matriz) != len(fragmentos):
        print(f"HALLAZGO: {len(matriz)} vectores para {len(fragmentos)} fragmentos")
        return 1
    normas = np.linalg.norm(matriz[:10], axis=1) if len(matriz) else []
    if len(normas) and not np.allclose(normas, 1.0, atol=1e-3):
        print(f"HALLAZGO: los vectores no estan normalizados: {normas[:5]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
