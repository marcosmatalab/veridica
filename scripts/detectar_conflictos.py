#!/usr/bin/env python3
"""Encargo 1.8: detector de conflictos del corpus. En INGESTA, jamas en respuesta.

Tres tipos de hallazgo, y cada uno con su porque:

  casi_duplicado  coseno >= 0,95 dentro de la MISMA asignatura. Excluye por diseño los pares
                  consecutivos del mismo documento: el troceado solapa 64 tokens, asi que ese
                  parecido es artefacto nuestro y el detector tiene que saberlo (principio 6).
  contradiccion   NLI sobre pares muy parecidos que NO son duplicados. El NLI es un modelo
                  DISTINTO del que genero o troceo nada: quien comprueba no comparte supuesto.
  colado          documento cuyos fragmentos tienen CASI DUPLICADOS en otra asignatura. Ojo con
                  la señal: "vecindario semantico ajeno" NO sirve, porque un documento legitimo
                  puede hablar de otra materia (Consultas-SQL en Programacion tiene 11 de 15
                  vecinos en Bases de datos y es legitimo). Lo que delata un colado es que sea
                  una COPIA de material que vive en otra asignatura, que es como ocurre de
                  verdad: alguien deja el fichero en la carpeta equivocada.

Lo que se persiste NO es una marca de "aqui hay conflicto", es lo que la fase 4 necesita para
RESPONDER: los dos fragmentos, la similitud, el veredicto del NLI con su probabilidad y la FECHA
de cada fuente. El 4.5 enseña las dos versiones y ordena por vigencia sin arrogarse la verdad.

Uso:
    python scripts/detectar_conflictos.py --sin-nli      # rapido, solo duplicados y colados
    python scripts/detectar_conflictos.py
"""
import argparse
import collections
import json
import re
import sys

import numpy as np

from app.core.frases import frases_de, palabras_de

VECTORES = "corpus/embeddings/vectores.npy"
IDS = "corpus/embeddings/ids.jsonl"
FRAGMENTOS = "corpus/fragmentos.jsonl"
MANIFIESTO = "corpus/manifiesto.jsonl"
SALIDA = "corpus/conflictos.jsonl"

MODELO_NLI = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
REVISION_NLI = "b5113eb38ab63efdd7f280f8c144ea8b13f978ce"   # anclada, como BGE-M3

UMBRAL_DUPLICADO = 0.95
BANDA_NLI = (0.80, 0.95)
UMBRAL_COLADO = 0.10          # medido: el colado plantado da 0,20 y los controles legitimos 0,00
PROB_CONTRADICCION = 0.90   # medido: por debajo, el ruido se come el hallazgo


def cargar():
    vectores = np.load(VECTORES)
    ids = [json.loads(x) for x in open(IDS, encoding="utf-8") if x.strip()]
    fragmentos = {}
    for linea in open(FRAGMENTOS, encoding="utf-8"):
        fr = json.loads(linea)
        fragmentos[(fr["documento"], fr["orden"])] = fr
    fechas = {}
    for linea in open(MANIFIESTO, encoding="utf-8"):
        e = json.loads(linea)
        fechas[e["ruta"]] = (e.get("fecha_fuente"), e.get("fecha_origen"))
    return vectores, ids, fragmentos, fechas


def asignatura_real(nombre: str) -> str:
    """La version antigua de un modulo ES el mismo modulo.

    El corpus separa el DWES de 2013 en una carpeta '-antiguo' para no mezclarlo, y eso hacia que
    el detector no comparara nunca las dos versiones: el par contradictorio REAL del corpus -las
    dos definiciones incompatibles de la Vista de MVC- era invisible para el, que es como tener un
    detector de incendios apuntando a la pared. En produccion los dos serian material del modulo
    0613 y viviran en la misma particion, asi que aqui se comparan igual."""
    return nombre[:-len("-antiguo")] if nombre.endswith("-antiguo") else nombre


def pares_por_asignatura(vectores, ids):
    """Devuelve (i, j, similitud, es_consecutivo) por asignatura. Nunca compara entre asignaturas:
    el indice es por particion, igual que lo sera en produccion."""
    por_asig = collections.defaultdict(list)
    for i, x in enumerate(ids):
        por_asig[asignatura_real(x["asignatura"])].append(i)
    for asignatura, idx in por_asig.items():
        if len(idx) < 2:
            continue
        M = vectores[idx]
        S = M @ M.T
        a, b = np.triu_indices(len(idx), 1)
        s = S[a, b]
        interesa = s >= BANDA_NLI[0]
        for x, y, sim in zip(a[interesa], b[interesa], s[interesa]):
            i, j = idx[x], idx[y]
            consecutivo = (ids[i]["documento"] == ids[j]["documento"]
                           and abs(ids[i]["orden"] - ids[j]["orden"]) <= 1)
            yield asignatura, i, j, float(sim), consecutivo


def colados(vectores, ids):
    """Documentos cuyos fragmentos tienen casi duplicados en OTRA asignatura."""
    doc = np.array([x["documento"] for x in ids])
    asig = np.array([x["asignatura"] for x in ids])
    hallazgos = []
    for d in sorted(set(doc)):
        m = doc == d
        S = vectores[m] @ vectores.T
        S[:, m] = -1
        mejor = S.max(axis=1)
        quien = S.argmax(axis=1)
        propia = asig[m][0]
        ajeno = np.array([asig[j] != propia for j in quien])
        proporcion = float(np.mean((mejor >= UMBRAL_DUPLICADO) & ajeno))
        if proporcion >= UMBRAL_COLADO:
            destino = collections.Counter(asig[j] for j, ok in zip(quien, ajeno) if ok)
            hallazgos.append({"documento": d, "asignatura": propia,
                              "proporcion_casi_duplicada_fuera": round(proporcion, 3),
                              "asignatura_real_probable": destino.most_common(1)[0][0]})
    return hallazgos


RE_CODIGO = re.compile(r"[{}]|;\s*$|\w+\s*=\s*\w|&lt;|\b(private|public|protected|import|class|"
                       r"void|return)\b")
SOLAPE_MINIMO = 0.20


def mejor_par_de_frases(a: str, b: str):
    """La pareja de frases con mas vocabulario en comun.

    El NLI se entreno con FRASES. Darle dos trozos de 500 tokens lo saca de su terreno y se nota:
    a nivel de trozo marcaba 4.255 contradicciones, entre ellas dos salidas de ping con distinta
    IP. A nivel de frase acierta de lleno en la plantada (0,99) y señala las dos frases que chocan,
    que ademas es lo que hay que enseñarle al alumno."""
    mejor, punto = None, 0.0
    for x in frases_de(a)[:12]:
        px = palabras_de(x)
        for y in frases_de(b)[:12]:
            py = palabras_de(y)
            if not px or not py:
                continue
            j = len(px & py) / len(px | py)
            if j > punto:
                mejor, punto = (x, y), j
    return mejor, punto


def veredictos_nli(candidatos, fragmentos, ids, tope):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODELO_NLI, revision=REVISION_NLI)
    modelo = AutoModelForSequenceClassification.from_pretrained(MODELO_NLI, revision=REVISION_NLI)
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    modelo.to(dispositivo).eval()
    etiquetas = [modelo.config.id2label[k].lower() for k in sorted(modelo.config.id2label)]

    # Se preselecciona por frases ANTES de gastar NLI: pares sin vocabulario en comun no pueden
    # contradecirse (hablan de cosas distintas) y pares de codigo dan falsos positivos a puñados.
    preparados = []
    for i, j, sim in candidatos[:tope]:
        a = fragmentos[(ids[i]["documento"], ids[i]["orden"])]["texto"]
        b = fragmentos[(ids[j]["documento"], ids[j]["orden"])]["texto"]
        par, solape = mejor_par_de_frases(a, b)
        if not par or solape < SOLAPE_MINIMO:
            continue
        if RE_CODIGO.search(par[0]) or RE_CODIGO.search(par[1]):
            continue
        preparados.append((i, j, sim, par, solape))

    salida, lote = [], 32
    for inicio in range(0, len(preparados), lote):
        tanda = preparados[inicio:inicio + lote]
        entradas = tok([p[3][0] for p in tanda], [p[3][1] for p in tanda], truncation=True,
                       padding=True, max_length=256, return_tensors="pt").to(dispositivo)
        with torch.no_grad():
            probs = torch.softmax(modelo(**entradas).logits, dim=-1).cpu().numpy()
        for (i, j, sim, par, solape), p in zip(tanda, probs):
            k = int(np.argmax(p))
            salida.append((i, j, sim, etiquetas[k], float(p[k]), par, solape))
    print(f"  preseleccionados por frase: {len(preparados)} de {min(len(candidatos), tope)}")
    return salida


def main() -> int:
    p = argparse.ArgumentParser(description="Detecta conflictos en el corpus (encargo 1.8).")
    p.add_argument("--sin-nli", action="store_true")
    p.add_argument("--tope-nli", type=int, default=40000)
    p.add_argument("--salida", default=SALIDA)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    vectores, ids, fragmentos, fechas = cargar()

    duplicados, candidatos, excluidos = [], [], 0
    for asignatura, i, j, sim, consecutivo in pares_por_asignatura(vectores, ids):
        if consecutivo:
            excluidos += 1
            continue
        if sim >= UMBRAL_DUPLICADO:
            duplicados.append((i, j, sim))
        else:
            candidatos.append((i, j, sim))

    print(f"pares por encima de {BANDA_NLI[0]}: {len(duplicados) + len(candidatos) + excluidos}")
    print(f"  excluidos por ser consecutivos del mismo documento: {excluidos} (artefacto del solape)")
    print(f"  casi duplicados (>= {UMBRAL_DUPLICADO}): {len(duplicados)}")
    print(f"  candidatos a contradiccion: {len(candidatos)}")

    contradicciones = []
    if not a.sin_nli and candidatos:
        candidatos.sort(key=lambda x: -x[2])
        if len(candidatos) > a.tope_nli:
            print(f"  AVISO: se pasan por NLI los {a.tope_nli} mas parecidos de {len(candidatos)}")
        for i, j, sim, etiqueta, prob, par, solape in veredictos_nli(
                candidatos, fragmentos, ids, a.tope_nli):
            if etiqueta.startswith("contradic") and prob >= PROB_CONTRADICCION:
                contradicciones.append((i, j, sim, etiqueta, prob, par, solape))

    def fila(tipo, i, j, sim, veredicto=None, prob=None, par=None, solape=None):
        fa = fragmentos[(ids[i]["documento"], ids[i]["orden"])]
        fb = fragmentos[(ids[j]["documento"], ids[j]["orden"])]
        return {"tipo": tipo, "similitud": round(sim, 4),
                "veredicto_nli": veredicto, "probabilidad_nli": round(prob, 4) if prob else None,
                "frase_a": par[0] if par else None, "frase_b": par[1] if par else None,
                "solape_lexico": round(solape, 3) if solape else None,
                "asignatura": fa["asignatura"],
                "a": {"documento": fa["documento"], "orden": fa["orden"], "unidad": fa["unidad"],
                      "fecha_fuente": fechas.get(fa["documento"], (None, None))[0],
                      "texto": fa["texto"][:600]},
                "b": {"documento": fb["documento"], "orden": fb["orden"], "unidad": fb["unidad"],
                      "fecha_fuente": fechas.get(fb["documento"], (None, None))[0],
                      "texto": fb["texto"][:600]}}

    filas = [fila("casi_duplicado", i, j, s) for i, j, s in duplicados]
    filas += [fila("contradiccion", i, j, s, v, p, par, sol)
              for i, j, s, v, p, par, sol in contradicciones]
    for c in colados(vectores, ids):
        filas.append({"tipo": "colado", **c})

    with open(a.salida, "w", encoding="utf-8", newline="\n") as f:
        for x in filas:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

    por_tipo = collections.Counter(x["tipo"] for x in filas)
    print(f"\nhallazgos -> {a.salida}: {dict(por_tipo)}")
    print(f"  contradicciones con probabilidad >= {PROB_CONTRADICCION}: {len(contradicciones)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
