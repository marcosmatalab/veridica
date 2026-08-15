#!/usr/bin/env python3
"""Corre un JSONL de preguntas POR EL CAMINO QUE CORRE y guarda TODO lo que sale.

    python scripts/correr_preguntas.py evals/casos/veinte_ordinarias_dwes.jsonl --titulacion daw
    python scripts/correr_preguntas.py evals/casos/premisas_falsas.jsonl --campo pregunta

## Por qué existe, y es la carencia que lo justifica

**Todo lo medido en este repo está sobre conjuntos CURADOS** —los 94 pares oro, los congelados de
modos, las cuatro sugeridas—. Nadie había mirado qué contesta el sistema a una pregunta CUALQUIERA, y
el lunes alguien va a escribir la suya. Esto no mide contra una etiqueta: **saca las respuestas para
leerlas con los ojos**, que es lo que este repo hace cuando un agregado no basta.

## Lo que captura, y por qué cada cosa

Va por HTTP contra el servicio vivo —no importa `_flujo` ni llama a las funciones por dentro—, porque
lo que hay que saber es qué sale por el camino real: el mismo prompt, la misma recuperación, el mismo
portero y el mismo NLI que va a ver quien pregunte. De cada consulta guarda:

- **la prosa entera**, que es lo único que el alumno lee;
- **el modo elegido y por quién**, para poder separar "la respuesta es mala" de "se eligió otro modo";
- **la asignatura elegida** cuando no venía dada, por lo mismo: una respuesta pobre porque el módulo
  era el equivocado es otro problema, en otro sitio, con otro arreglo;
- **las etapas con sus marcas**, de donde salen las latencias sin volver a medir nada;
- **las frases marcadas por el portero** y las afirmaciones con su veredicto;
- y **el fallo con su motivo** si lo hubo. Se persiste ANTES de poder fallar: si el flujo revienta a
  mitad, la fila queda con lo que llevaba y su excepción, en vez de desaparecer del recuento.

**El JSON se escribe al terminar CADA consulta**, no al final: una tanda de veinte que se corta en la
quince deja quince leídas, no cero.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sse(url: str, cuerpo: dict, token: str | None, plazo: float):
    """Lector de SSE mínimo. Devuelve la lista de (evento, datos) tal cual llegan."""
    datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
    cabeceras = {"Content-Type": "application/json"}
    if token:
        cabeceras["X-Veridica-Token"] = token
    peticion = urllib.request.Request(url, data=datos, headers=cabeceras, method="POST")
    eventos, nombre, trozos = [], None, []
    with urllib.request.urlopen(peticion, timeout=plazo) as r:
        for linea in r:
            linea = linea.decode("utf-8").rstrip("\n")
            if linea.startswith("event: "):
                nombre = linea[7:]
            elif linea.startswith("data: "):
                trozos.append(linea[6:])
            elif not linea and nombre:
                eventos.append((nombre, json.loads("".join(trozos))))
                nombre, trozos = None, []
    return eventos


def resumir(eventos: list) -> dict:
    """De los eventos a las cifras que se van a leer. NADA se calcula dos veces: los ms salen de las
    marcas que la propia API persiste, que es lo mismo que hay en `respuestas.etapas`."""
    por_nombre = {}
    for n, d in eventos:
        por_nombre.setdefault(n, []).append(d)
    fin = (por_nombre.get("fin") or [{}])[0]
    modo = (por_nombre.get("modo") or [{}])[0]
    etapas = por_nombre.get("etapa") or []
    tokens = por_nombre.get("token") or []
    elegida = next((e for e in etapas if e["nombre"] == "asignatura_elegida"), None)
    return {
        "prosa": "".join(t.get("t", "") for t in tokens),
        "frases": [{"t": t.get("t"), "respaldada": t.get("respaldada"), "solape": t.get("solape")}
                   for t in tokens],
        "modo": modo.get("modo"), "modo_elegido_por": modo.get("elegido_por"),
        "modo_clausula": modo.get("clausula"),
        "asignatura_elegida": (elegida or {}).get("asignatura"),
        "asignatura_elegida_id": (elegida or {}).get("asignatura_id"),
        "etapas": [{"nombre": e["nombre"], "ms": e.get("ms")} for e in etapas],
        "afirmaciones": [{"tipo": a["tipo"], "veredicto": a["veredicto"], "texto": a["texto"]}
                         for a in (por_nombre.get("afirmaciones") or [{}])[0].get(
                             "afirmaciones", [])],
        "abstencion": bool(por_nombre.get("abstencion")) or fin.get("abstencion"),
        "motivo_abstencion": (por_nombre.get("abstencion") or [{}])[0].get("motivo"),
        "reintentos": len(por_nombre.get("reintento") or []),
        "total_ms": fin.get("total_ms"), "ttft_prosa_ms": fin.get("ttft_prosa_ms"),
        "paso_del_objetivo": fin.get("paso_del_objetivo"),
        "objetivo_ms": fin.get("objetivo_ms"), "presupuesto_ms": fin.get("presupuesto_ms"),
        "confianza": fin.get("confianza_recuperacion"),
        "respuesta_id": fin.get("respuesta_id"),
        "version_prompt": fin.get("version_prompt"),
        "fragmentos_en_contexto": fin.get("fragmentos_en_contexto"),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("casos")
    p.add_argument("--base", default="http://127.0.0.1:8010")
    p.add_argument("--titulacion", default="daw")
    p.add_argument("--asignatura-id", type=int, default=None,
                   help="por defecto NINGUNA: el camino que corre el lunes")
    p.add_argument("--modo", default=None, help="por defecto lo decide el clasificador del 5.1")
    p.add_argument("--campo", default="texto", help="clave del JSONL que lleva la pregunta")
    p.add_argument("--salida", default=None)
    p.add_argument("--plazo", type=float, default=120.0)
    a = p.parse_args()

    token = os.environ.get("VERIDICA_TOKEN")
    if not token:
        ruta = os.path.join(RAIZ, ".token-sesion")
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                token = f.read().strip()

    casos = []
    with open(os.path.join(RAIZ, a.casos), encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                casos.append(json.loads(linea))

    salida = a.salida or os.path.join(
        RAIZ, "evals", "corridas", f"ordinarias-{os.path.basename(a.casos)}.json")
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    filas = []
    for i, caso in enumerate(casos, 1):
        texto = caso.get(a.campo) or caso.get("texto") or caso.get("pregunta")
        cuerpo = {"texto": texto, "titulacion": a.titulacion,
                  "asignatura_id": a.asignatura_id, "modo": a.modo}
        arranque = time.perf_counter()
        # SE PERSISTE ANTES DE PODER FALLAR: si esto revienta, la fila queda con su motivo en vez de
        # desaparecer del recuento, que es como una tasa acaba calculada solo sobre lo que salio bien.
        fila = {"n": i, "id": caso.get("id"), "unidad": caso.get("unidad"), "pregunta": texto,
                "fallo": None}
        try:
            fila.update(resumir(sse(f"{a.base}/consulta", cuerpo, token, a.plazo)))
        except urllib.error.HTTPError as e:
            fila["fallo"] = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}"
        except Exception as e:                                          # noqa: BLE001
            fila["fallo"] = f"{type(e).__name__}: {e}"[:200]
        fila["cliente_ms"] = round((time.perf_counter() - arranque) * 1000, 1)
        filas.append(fila)
        with open(salida, "w", encoding="utf-8") as f:
            json.dump({"casos": a.casos, "titulacion": a.titulacion,
                       "asignatura_id": a.asignatura_id, "modo_pedido": a.modo,
                       "filas": filas}, f, ensure_ascii=False, indent=1)
        print(f"[{i:>2}/{len(casos)}] {fila.get('modo') or '-':<10} "
              f"{(fila.get('asignatura_elegida') or '-')[:28]:<28} "
              f"{fila.get('total_ms') or fila['fallo']}")
    print(f"\n{len(filas)} filas en {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
