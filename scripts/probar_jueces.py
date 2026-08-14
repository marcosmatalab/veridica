#!/usr/bin/env python3
"""LA PRUEBA DE IDENTIDAD sobre jueces NLI alternativos: ¿aprueba A contra A?

    DATABASE_URL=... python scripts/probar_jueces.py [--dispositivo cuda]

## POR QUÉ ESTA VARA, Y POR QUÉ VA ANTES QUE CUALQUIER OTRA COSA

Un juez que dice `neutral` a un texto que se sigue de **sí mismo** no puede juzgar una paráfrasis.
Sobre 60 identidades reales, el juez actual (mDeBERTa-v3-base) contesta `neutral` al **20 %** y su
probabilidad de `entailment` tiene mediana **0,66** — o sea que el umbral de servicio (0,60) no mide
cuánta evidencia hace falta: **mide hasta dónde llega este modelo**. Con ese techo, mejorar premisa,
selección o datos no puede subir nada.

**Y va antes del índice y de la ventana por procedimiento, no por prisa:** se calibra sobre el
instrumento arreglado, nunca sobre el roto. Elegir juez después obligaría a re-calibrar dos veces y
la primera no habría valido. Orden: **juez → ventana → índice**.

## LA VARA

- **No necesita etiquetado, ni humanos, ni desempate.** Los 60 pares salen solos: son las
  afirmaciones `literal` cuya hipótesis está **literalmente dentro** de la premisa que la tubería de
  servicio construye. Si un juez falla ahí, falla en el caso trivialmente cierto de su tarea.
- **La premisa se construye con `premisa_para`, la MISMA que el servicio**, para que la comparación
  entre jueces no mezcle dos tuberías.
- **Criterio de elección, escrito antes de correr**: gana el que etiqueta `entailment` MÁS
  identidades (sin mirar umbral); empate → el de **mediana de probabilidad más alta**; empate →
  el más pequeño, porque corre en CPU dentro de la ventana de la prosa.
- **Y lo que esta vara NO dice, dicho antes**: aprobar identidades es **necesario y no suficiente**.
  Un modelo que dijera `entailment` a todo sacaría pleno aquí; por eso se corre TAMBIÉN sobre los
  **negativos** del mismo conjunto —la afirmación contra un fragmento ajeno—, que es el control que
  ya existe. Un juez solo pasa si aprueba identidades **y** rechaza ajenos.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                        # noqa: E402

from app.core.verificador_literal import n1_espacios                  # noqa: E402
from app.core.verificador_nli import MODELO as MODELO_ACTUAL          # noqa: E402
from app.core.verificador_nli import parece_codigo, premisa_para      # noqa: E402
from app.modelos.contrato import TIPOS                                # noqa: E402

#: Los candidatos. Multilingües y con cabeza de NLI, que es lo que esta tarea necesita; el actual va
#: el primero para que su columna salga en la misma tabla y con el mismo código.
CANDIDATOS = [
    MODELO_ACTUAL,
    "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
    # NO COMPITIÓ: su tokenizador no convierte en esta instalación (falta el `.model` de
    # SentencePiece). **Un candidato que no carga no es un candidato que pierde**, y se deja escrito
    # aquí en vez de borrarlo de la lista: si mañana alguien se pregunta por qué no se probó un
    # modelo grande, la respuesta está en el sitio donde miraría.
    "joeddav/xlm-roberta-large-xnli",
]

PARES = """
SELECT a.id, a.texto, a.detalle->>'cita' AS cita, f.texto AS fragmento,
       f.asignatura_id, d.ruta AS documento, f.orden
  FROM afirmaciones a
  JOIN fragmentos f ON f.id = a.fragmento_id
  JOIN documentos d ON d.id = f.documento_id
 WHERE a.tipo = 'literal' AND a.veredicto = 'verificada'
   AND a.detalle->>'cita' IS NOT NULL
   AND a.detalle->'verificacion'->>'nivel' IS NOT NULL
   AND a.texto <> ALL(%(tipos)s)
 ORDER BY a.id
"""

AJENOS = """
SELECT f.id, f.texto, d.ruta AS documento, f.orden
  FROM fragmentos f JOIN documentos d ON d.id = f.documento_id
 WHERE f.asignatura_id = %s
 ORDER BY f.id
"""


class Juez:
    """Un NLI cualquiera con la interfaz mínima. Lee sus etiquetas de `id2label`, que es lo que
    permite comparar modelos con vocabularios distintos sin suponer el orden."""

    def __init__(self, nombre: str, dispositivo: str):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.nombre = nombre
        self.dispositivo = dispositivo
        self.tokenizador = AutoTokenizer.from_pretrained(nombre)
        self.modelo = AutoModelForSequenceClassification.from_pretrained(nombre,
                                                                        dtype=torch.float32)
        self.modelo.to(dispositivo).eval()
        self.etiquetas = [self.modelo.config.id2label[k].lower()
                          for k in sorted(self.modelo.config.id2label)]
        self.parametros = sum(p.numel() for p in self.modelo.parameters())

    def clasificar(self, premisa: str, hipotesis: str) -> tuple:
        import torch
        with torch.no_grad():
            e = self.tokenizador(premisa, hipotesis, truncation=True, max_length=512,
                                 return_tensors="pt").to(self.dispositivo)
            p = torch.softmax(self.modelo(**e).logits, dim=-1)[0]
        i = int(p.argmax())
        return self.etiquetas[i], float(p[i]), float(p[self.etiquetas.index("entailment")])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dispositivo", default="cuda")
    a = p.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")

    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute(PARES, {"tipos": list(TIPOS)})
        columnas = [d.name for d in cur.description]
        filas = [dict(zip(columnas, f)) for f in cur.fetchall()]
        ajenos_por_asig = {}
        for f in filas:
            if f["asignatura_id"] not in ajenos_por_asig:
                cur.execute(AJENOS, (f["asignatura_id"],))
                cols = [d.name for d in cur.description]
                ajenos_por_asig[f["asignatura_id"]] = [dict(zip(cols, x)) for x in cur.fetchall()]

    identidades, negativos = [], []
    for i, f in enumerate(filas):
        premisa, _, _ = premisa_para(f["fragmento"], f["texto"], f["cita"])
        if not premisa or parece_codigo(premisa):
            continue
        # IDENTIDAD = la hipótesis está literalmente dentro de la premisa. Se comprueba con la
        # normalización del 4.2 (espacios), que es la del servicio.
        if n1_espacios(f["texto"]).lower() not in n1_espacios(premisa).lower():
            continue
        identidades.append({"id": f["id"], "premisa": premisa, "hipotesis": f["texto"]})
        # EL CONTROL DE LA OTRA DIRECCIÓN: la misma afirmación contra un fragmento AJENO. Sin él,
        # un modelo que dijera `entailment` a todo sacaría pleno en la prueba de identidad.
        # SE SIGUE BUSCANDO HASTA ENCONTRAR UNO UTIL. La primera version se rendia con el primer
        # candidato -si no daba premisa o era codigo, ese positivo se quedaba sin negativo- y por
        # eso salian 26 negativos contra 70 identidades: el control acababa existiendo solo donde
        # el azar del emparejado lo permitia, o sea una muestra elegida por una condicion ajena a
        # lo que se mide.
        candidatos = ajenos_por_asig.get(f["asignatura_id"]) or []
        for salto in range(len(candidatos)):
            c = candidatos[(i * 7 + salto) % len(candidatos)]
            if c["documento"] == f["documento"]:
                continue
            ajena, _, _ = premisa_para(c["texto"], f["texto"], None)
            if ajena and not parece_codigo(ajena):
                negativos.append({"id": f["id"], "premisa": ajena, "hipotesis": f["texto"]})
                break

    print(f"identidades: {len(identidades)} | negativos (fragmento ajeno): {len(negativos)}")

    resumen = []
    for nombre in CANDIDATOS:
        print(f"\n=== {nombre}")
        t0 = time.perf_counter()
        try:
            juez = Juez(nombre, a.dispositivo)
        except Exception as e:                       # noqa: BLE001 - un modelo que no baja se dice
            print(f"  NO SE PUDO CARGAR: {type(e).__name__}: {e}")
            resumen.append({"modelo": nombre, "error": f"{type(e).__name__}: {e}"})
            continue
        carga_s = time.perf_counter() - t0

        # SE GUARDA PAR A PAR Y NO SOLO LA MEDIANA: con medianas no se puede contestar la pregunta
        # que decide -¿un umbral separa identidades de negativos?- ni mirar a ojo los que fallan.
        # Es el mismo agujero que obligo a repetir la recogida de solapes: el agregado promedia.
        t0 = time.perf_counter()
        etiquetas, probs_ent, detalle_id = {}, [], []
        for par in identidades:
            etiqueta, _, p_ent = juez.clasificar(par["premisa"], par["hipotesis"])
            etiquetas[etiqueta] = etiquetas.get(etiqueta, 0) + 1
            probs_ent.append(p_ent)
            detalle_id.append({"id": par["id"], "etiqueta": etiqueta, "p_ent": round(p_ent, 4)})
        ms_par = (time.perf_counter() - t0) * 1000 / max(1, len(identidades))

        neg_ent = 0
        neg_probs, detalle_neg = [], []
        for par in negativos:
            etiqueta, _, p_ent = juez.clasificar(par["premisa"], par["hipotesis"])
            neg_probs.append(p_ent)
            detalle_neg.append({"id": par["id"], "etiqueta": etiqueta, "p_ent": round(p_ent, 4)})
            if etiqueta == "entailment":
                neg_ent += 1

        aprobadas = etiquetas.get("entailment", 0)
        fila = {"modelo": nombre, "parametros_M": round(juez.parametros / 1e6),
                "etiquetas_identidad": etiquetas,
                "identidades_entailment": aprobadas,
                "identidades": len(identidades),
                "prob_ent_mediana": round(statistics.median(probs_ent), 4) if probs_ent else None,
                "prob_ent_min": round(min(probs_ent), 4) if probs_ent else None,
                "prob_ent_p10": round(sorted(probs_ent)[len(probs_ent)//10], 4) if probs_ent else None,
                "negativos_entailment": neg_ent, "negativos": len(negativos),
                "neg_prob_mediana": round(statistics.median(neg_probs), 4) if neg_probs else None,
                "carga_s": round(carga_s, 1), "ms_por_par": round(ms_par, 1),
                "dispositivo": a.dispositivo,
                "por_par": {"identidades": detalle_id, "negativos": detalle_neg}}
        resumen.append(fila)
        # LA PREGUNTA QUE DECIDE, y solo se contesta con los pares: ¿hay algun corte que deje TODAS
        # las identidades dentro y TODOS los negativos fuera? La etiqueta `entailment` sola no basta
        # -un negativo etiquetado entailment con p=0,4 lo tira cualquier umbral-.
        peor_identidad = min(probs_ent) if probs_ent else None
        mejor_negativo = max(neg_probs) if neg_probs else None
        if peor_identidad is not None and mejor_negativo is not None:
            print(f"  SEPARACION: peor identidad {peor_identidad:.4f} | mejor negativo "
                  f"{mejor_negativo:.4f} | "
                  + ("HAY corte limpio" if peor_identidad > mejor_negativo
                     else "NO hay corte limpio: se solapan"))
        print(f"  parametros: {fila['parametros_M']} M | carga {fila['carga_s']} s | "
              f"{fila['ms_por_par']} ms/par en {a.dispositivo}")
        print(f"  IDENTIDADES: {aprobadas}/{len(identidades)} entailment {etiquetas} | "
              f"prob mediana {fila['prob_ent_mediana']} p10 {fila['prob_ent_p10']} "
              f"min {fila['prob_ent_min']}")
        print(f"  NEGATIVOS (fragmento ajeno): {neg_ent}/{len(negativos)} entailment | "
              f"prob mediana {fila['neg_prob_mediana']}")

    validos = [r for r in resumen if "error" not in r]
    if validos:
        # EL CRITERIO PRE-ESCRITO: mas identidades aprobadas; empate -> mediana mas alta; empate ->
        # menos parametros. El rechazo de negativos NO se mete en el desempate: se declara aparte,
        # porque un juez que apruebe negativos queda descartado por la puerta, no por el orden.
        elegido = max(validos, key=lambda r: (r["identidades_entailment"],
                                              r["prob_ent_mediana"] or 0, -r["parametros_M"]))
        print(f"\nELEGIDO POR EL CRITERIO PRE-ESCRITO: {elegido['modelo']}")
        print(f"  {elegido['identidades_entailment']}/{elegido['identidades']} identidades, "
              f"mediana {elegido['prob_ent_mediana']}, "
              f"{elegido['negativos_entailment']}/{elegido['negativos']} negativos aprobados")

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("INSERT INTO corridas_eval (commit_sha, config, metricas) VALUES (%s,%s,%s)"
                    " RETURNING id",
                    (commit,
                     json.dumps({"que": "prueba de identidad sobre jueces NLI alternativos",
                                 "vara": "la hipotesis esta LITERAL en la premisa; un juez que no "
                                         "aprueba eso no puede juzgar una parafrasis",
                                 "criterio": "mas identidades entailment; empate -> mediana mas "
                                             "alta; empate -> menos parametros",
                                 "control": "los mismos pares contra un fragmento AJENO",
                                 "candidatos": CANDIDATOS, "dispositivo": a.dispositivo}),
                     json.dumps({"resumen": resumen}, ensure_ascii=False)))
        print(f"\npersistido en corridas_eval: id {cur.fetchone()[0]}")
        con.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
