#!/usr/bin/env python3
"""Humo del proveedor de inferencia (encargo 2.2). Llamada REAL: este script gasta dinero.

    python scripts/humo_proveedor.py                      # una llamada en flujo, con sus dos TTFT
    python scripts/humo_proveedor.py --repeticiones 3     # + la comprobacion de determinismo
    python scripts/humo_proveedor.py --evidencia docs/evidencia/<fecha>-humo-proveedor.md

Hace tres cosas, y las tres se apuntan:

1. **Que el contrato viaja.** Una peticion con `response_format` de esquema, la respuesta validada
   en FORMA con el modelo tipado del servidor. Que el proveedor prometa el esquema no exime de
   comprobarlo: quien produce el texto es el, no nosotros.

2. **Los dos TTFT.** Con salida tipada, el primer token del proveedor es `{` y no es lo que ve el
   alumno. Se miden los dos por separado, y el que cuenta el dia de la demo es el de la prosa.

3. **Si temperatura 0 + seed es determinismo de verdad.** N llamadas identicas comparadas BYTE A
   BYTE. No es una formalidad: temperatura 0 con seed es una PETICION de determinismo, y en un
   servidor con lotes variables la aritmetica en coma flotante cambia con el tamano del lote, asi
   que la misma llamada puede diferir. Si difiere, aplica la regla del 7.1 -N=3 y se reporta la
   dispersion- y hay que saberlo HOY, no en la fase 7 midiendo ruido y creyendo que se mide el
   sistema.

Codigos de salida: 0 todo bien, 1 hallazgos, 2 mal configurado (que no es lo mismo).
La clave JAMAS se imprime: el cliente la tapa en cualquier texto que salga de aqui.
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.entorno import cargar_dotenv                                       # noqa: E402
from app.core.inferencia import (Ajustes, ClienteInferencia, ErrorDefinitivo,    # noqa: E402
                                 ErrorTransitorio, Llamada)
from app.core.prosa_parcial import ProsaEnCurso                                  # noqa: E402
from app.modelos.contrato import ContratoRoto, response_format, validar_forma    # noqa: E402

PREGUNTA = ("Explica en pocas frases que es una clave primaria en una base de datos relacional "
            "y por que no puede repetirse.")
SISTEMA = ("Eres un profesor de Formacion Profesional de informatica. Respondes SIEMPRE con el "
           "objeto JSON del contrato. No tienes fragmentos del temario, asi que toda afirmacion "
           "factual va con tipo 'conocimiento' y fragmento_id nulo, y 'confianza_recuperacion' es "
           "'baja'. No uses 'literal' ni 'parafrasis'. Se breve.")


def una_llamada(cliente: ClienteInferencia) -> dict:
    """Una llamada en flujo, midiendo los dos TTFT y quedandose con el JSON crudo entero."""
    mensajes = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": PREGUNTA}]
    llamada, prosa = Llamada(), ProsaEnCurso()
    t0 = time.perf_counter()
    crudo, ttft_prosa, uso, fin = "", None, None, None
    for trozo in cliente.stream(mensajes, response_format(), traza=llamada):
        if trozo.uso:
            uso = trozo.uso
        if trozo.fin:
            fin = trozo.fin
        if not trozo.texto:
            continue
        crudo += trozo.texto
        if prosa.alimentar(trozo.texto) and ttft_prosa is None:
            ttft_prosa = (time.perf_counter() - t0) * 1000
    return {"crudo": crudo, "total_ms": (time.perf_counter() - t0) * 1000,
            "ttft_proveedor_ms": llamada.ttft_proveedor_ms, "ttft_prosa_ms": ttft_prosa,
            "uso": uso, "fin": fin, "intentos": llamada.intentos}


def main() -> int:
    p = argparse.ArgumentParser(description="Humo real contra el proveedor (encargo 2.2).")
    p.add_argument("--repeticiones", type=int, default=1,
                   help="numero de llamadas identicas para comprobar determinismo (3 recomendado)")
    p.add_argument("--evidencia", help="ruta del markdown de evidencia a escribir")
    p.add_argument("--fecha", default="2026-08-12")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cargar_dotenv()

    try:
        ajustes = Ajustes.desde_entorno()
    except ErrorDefinitivo as e:
        print(f"MAL CONFIGURADO: {e}", file=sys.stderr)
        return 2

    print(f"proveedor: {ajustes.base_url.rstrip('/').rsplit('/', 1)[0]}/... | modelo: "
          f"{ajustes.modelo} | temperatura {ajustes.temperatura} | seed {ajustes.semilla} | "
          f"max_tokens {ajustes.max_tokens}")
    cliente = ClienteInferencia(ajustes)
    hallazgos, corridas = [], []
    try:
        for i in range(1, a.repeticiones + 1):
            try:
                r = una_llamada(cliente)
            except (ErrorTransitorio, ErrorDefinitivo) as e:
                print(f"LLAMADA {i} FALLIDA: {e}", file=sys.stderr)
                return 1
            corridas.append(r)
            u = r["uso"]
            coste = u.coste_eur() if u else None
            print(f"\nllamada {i}: ttft_proveedor {r['ttft_proveedor_ms']:.0f} ms | "
                  f"ttft_prosa {r['ttft_prosa_ms']:.0f} ms | total {r['total_ms']:.0f} ms | "
                  f"fin={r['fin']} | tokens {u.tokens_entrada}+{u.tokens_salida} | "
                  f"coste {'%.6f EUR' % coste if coste is not None else 'sin precios en el entorno'}")
            try:
                validada = validar_forma(json.loads(r["crudo"]))
                print(f"  forma del contrato: OK ({len(validada.afirmaciones)} afirmaciones, "
                      f"modo={validada.modo}, confianza={validada.confianza_recuperacion})")
            except (json.JSONDecodeError, ContratoRoto) as e:
                hallazgos.append(f"llamada {i}: el contrato no valida en forma: {e}")
                print(f"  forma del contrato: ROTA -> {e}")
            if r["fin"] == "length":
                hallazgos.append(f"llamada {i}: corto por max_tokens ({ajustes.max_tokens})")
    finally:
        cliente.cerrar()

    identicas = None
    if len(corridas) > 1:
        crudos = [c["crudo"] for c in corridas]
        identicas = all(c == crudos[0] for c in crudos[1:])
        print(f"\ndeterminismo ({len(crudos)} llamadas identicas, comparadas byte a byte): "
              f"{'IDENTICAS' if identicas else 'DISTINTAS'}")
        if not identicas:
            largos = sorted({len(c) for c in crudos})
            print(f"  largos distintos: {largos}")
            for c in crudos[1:]:
                d = next((j for j, (x, y) in enumerate(zip(crudos[0], c)) if x != y), None)
                if d is not None:
                    print(f"  primer byte distinto en la posicion {d}: "
                          f"{crudos[0][max(0, d-30):d+30]!r} vs {c[max(0, d-30):d+30]!r}")
                    break
            print("  => temperatura 0 + seed NO da determinismo aqui. Aplica la regla del 7.1: "
                  "N=3 repeticiones y se reporta la dispersion.")

    if a.evidencia:
        escribir_evidencia(a.evidencia, a.fecha, ajustes, corridas, identicas, hallazgos)
        print(f"\nevidencia -> {a.evidencia}")

    print(f"\nhallazgos: {len(hallazgos)}")
    for h in hallazgos:
        print("  -", h)
    return 1 if hallazgos else 0


def escribir_evidencia(ruta: str, fecha: str, ajustes: Ajustes, corridas: list,
                       identicas, hallazgos: list) -> None:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    filas = []
    for i, c in enumerate(corridas, 1):
        u = c["uso"]
        coste = u.coste_eur() if u else None
        filas.append(f"| {i} | {c['ttft_proveedor_ms']:.0f} | {c['ttft_prosa_ms']:.0f} | "
                     f"{c['total_ms']:.0f} | {u.tokens_entrada} | {u.tokens_salida} | "
                     f"{('%.6f' % coste) if coste is not None else '—'} | {c['fin']} |")
    total_eur = sum((c["uso"].coste_eur() or 0) for c in corridas if c["uso"])
    veredicto = ("no se comprobó (una sola llamada)" if identicas is None else
                 "**idénticas byte a byte**" if identicas else "**distintas**")
    consecuencia = ("" if identicas is None else (
        "El arnés del 7.1 puede fiarse de una sola corrida para comparar configuraciones.\n"
        if identicas else
        "**Aplica la regla del 7.1**: temperatura 0 no basta aquí, así que toda medida de calidad "
        "va con N=3 repeticiones y se reporta la dispersión. Saberlo hoy evita medir ruido en la "
        "fase 7 creyendo que se mide el sistema.\n"))
    texto = f"""# Evidencia: humo real del proveedor de inferencia

- **Fecha:** {fecha}
- **Encargo:** 2.2
- **Commit:** `{commit}`
- **Modelo:** `{ajustes.modelo}` | temperatura `{ajustes.temperatura}` | seed `{ajustes.semilla}` |
  `max_tokens` `{ajustes.max_tokens}` | `response_format` en modo esquema (`json_schema`)

## Las llamadas (reales, pagadas)

| # | TTFT proveedor (ms) | TTFT prosa (ms) | total (ms) | tokens entrada | tokens salida | coste (EUR) | fin |
|---|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(filas)}

**Coste total de esta corrida: {total_eur:.6f} EUR.** Se anota aunque sean céntimos: la contabilidad
del 2.6 se construye sumando líneas como esta, y una que falte no se reconstruye después.

**Los dos TTFT no son el mismo número y por eso están los dos.** El del proveedor es el primer token
del JSON, que es `{{`. El de la prosa es el primer carácter de `respuesta_redactada` que sale por el
evento `token`, o sea lo que ve el alumno. La diferencia entre los dos es lo que tarda el modelo en
escribir `modo` y `afirmaciones`, que en el contrato van antes de la redacción (ADR 0009).

## Determinismo con temperatura 0 y seed fijo

{len(corridas)} llamadas idénticas, comparadas byte a byte: {veredicto}.

{consecuencia}
## Hallazgos

{chr(10).join('- ' + h for h in hallazgos) if hallazgos else 'Ninguno.'}

## Cómo se reproduce

```bash
python scripts/humo_proveedor.py --repeticiones {len(corridas)} --evidencia {ruta}
```

La clave sale de `INFERENCIA_API_KEY` (del `.env` en local, del secret del repositorio en CI) y no
aparece en este documento ni en la salida del script.
"""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


if __name__ == "__main__":
    sys.exit(main())
