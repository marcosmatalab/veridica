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
import difflib
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


def medir_dispersion(crudos: list) -> dict:
    """Cuanto varian N respuestas a la misma pregunta, POR DIMENSIONES SEPARADAS.

    "Salieron tres textos distintos" no basta para decidir nada, porque no todas las variaciones
    cuestan lo mismo. Que cambie la REDACCION y que cambie el CONJUNTO DE AFIRMACIONES son dos
    cosas distintas y solo una rompe el 7.3: la ablacion compara la fila con verificacion contra la
    fila sin ella, y si el conjunto de afirmaciones varia entre corridas identicas, esa diferencia
    -que es el argumento central del proyecto- puede quedar por debajo del ruido de medida.

    Se miden seis dimensiones, de la mas dura a la mas blanda, y se informan POR SEPARADO:
      1. bytes identicos
      2. numero de afirmaciones
      3. secuencia de tipos de afirmacion
      4. fragmento_id citados
      5. similitud del TEXTO de las afirmaciones
      6. similitud de la redaccion

    Las dimensiones 2, 3 y 4 son la FORMA del conjunto y son las que decide el 7.3. La 5 y la 6 son
    la redaccion. Decir "el conjunto es estable" mirando solo 2, 3 y 4 seria pasarse de listo: dos
    corridas pueden tener dos afirmaciones de tipo `conocimiento` cada una y estar afirmando cosas
    distintas, asi que la 5 esta para que esa diferencia no se cuele como estabilidad.
    """
    firmas = []
    for crudo in crudos:
        try:
            v = validar_forma(json.loads(crudo))
        except (json.JSONDecodeError, ContratoRoto):
            firmas.append(None)
            continue
        firmas.append({
            "n": len(v.afirmaciones),
            "tipos": tuple(af.tipo for af in v.afirmaciones),
            "fragmentos": tuple(sorted(x for x in (getattr(af, "fragmento_id", None)
                                                   for af in v.afirmaciones) if x is not None)),
            "prosa": v.respuesta_redactada,
            "textos": "\n".join(af.texto for af in v.afirmaciones),
        })
    validas = [f for f in firmas if f]
    prosas = [f["prosa"] for f in validas]
    similitudes = [difflib.SequenceMatcher(None, prosas[0], p).ratio() for p in prosas[1:]]
    textos = [f["textos"] for f in validas]
    sim_textos = [difflib.SequenceMatcher(None, textos[0], t).ratio() for t in textos[1:]]
    return {
        "primer_desvio": _primer_desvio(crudos),
        "similitud_afirmaciones": (sum(sim_textos) / len(sim_textos)) if sim_textos else 1.0,
        "n_corridas": len(crudos),
        "bytes_identicos": all(c == crudos[0] for c in crudos[1:]),
        "contratos_validos": len(validas),
        "n_afirmaciones": sorted({f["n"] for f in validas}),
        "tipos_estables": len({f["tipos"] for f in validas}) == 1,
        "tipos": sorted({f["tipos"] for f in validas}),
        "fragmentos_estables": len({f["fragmentos"] for f in validas}) == 1,
        "fragmentos": sorted({f["fragmentos"] for f in validas}),
        "similitud_prosa": (sum(similitudes) / len(similitudes)) if similitudes else 1.0,
    }


def _primer_desvio(crudos: list) -> dict | None:
    """Donde empieza a diferir la primera corrida de la siguiente que no sea igual. Sin esto, un
    "bytes distintos" no dice si lo que cambio fue una coma o media respuesta."""
    for otro in crudos[1:]:
        if otro == crudos[0]:
            continue
        pos = next((j for j, (x, y) in enumerate(zip(crudos[0], otro)) if x != y),
                   min(len(crudos[0]), len(otro)))
        return {"posicion": pos,
                "a": crudos[0][max(0, pos - 40):pos + 40],
                "b": otro[max(0, pos - 40):pos + 40]}
    return None


def contar_dispersion(d: dict) -> None:
    print(f"\ndeterminismo con temperatura 0 y semilla fija ({d['n_corridas']} llamadas identicas):")
    print(f"  1. bytes                : {'IDENTICOS' if d['bytes_identicos'] else 'DISTINTOS'}")
    print(f"  2. numero de afirmaciones: {d['n_afirmaciones']}"
          f" {'(estable)' if len(d['n_afirmaciones']) == 1 else '(VARIA)'}")
    print(f"  3. tipos de afirmacion  : {'estables' if d['tipos_estables'] else 'VARIAN'} -> "
          f"{[list(t) for t in d['tipos']]}")
    print(f"  4. fragmento_id citados : {'estables' if d['fragmentos_estables'] else 'VARIAN'} -> "
          f"{[list(t) for t in d['fragmentos']]}")
    print(f"  5. texto de las afirmaciones: {d['similitud_afirmaciones']*100:.1f}% en comun")
    print(f"  6. redaccion            : {d['similitud_prosa']*100:.1f}% de caracteres en comun")
    if d["primer_desvio"]:
        print(f"     primer desvio en la posicion {d['primer_desvio']['posicion']}:\n"
              f"       A: ...{d['primer_desvio']['a']}...\n"
              f"       B: ...{d['primer_desvio']['b']}...")
    if not d["fragmentos"] or d["fragmentos"] == [()]:
        print("     (aviso: sin recuperacion, fragmento_id es nulo en todas; la dimension 4 no se"
              " puede medir de verdad hasta la fase 3)")


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

    # Solo el host. La URL base lleva el identificador de proyecto dentro y va como secreto del
    # repositorio: imprimir un TROZO de un secreto es peor que imprimirlo entero, porque el
    # enmascarado de GitHub casa el valor exacto y una subcadena se le escapa. Lo enseño el log de
    # la primera corrida en verde, donde el identificador salio a pantalla.
    host = ajustes.base_url.split("//")[-1].split("/")[0]
    print(f"proveedor: {host} | modelo: {ajustes.modelo} | temperatura {ajustes.temperatura} | "
          f"seed {ajustes.semilla} | max_tokens {ajustes.max_tokens}")
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

    dispersion = None
    if len(corridas) > 1:
        dispersion = medir_dispersion([c["crudo"] for c in corridas])
        contar_dispersion(dispersion)

    if a.evidencia:
        escribir_evidencia(a.evidencia, a.fecha, ajustes, corridas, dispersion, hallazgos)
        print(f"\nevidencia -> {a.evidencia}")

    print(f"\nhallazgos: {len(hallazgos)}")
    for h in hallazgos:
        print("  -", h)
    return 1 if hallazgos else 0


def escribir_evidencia(ruta: str, fecha: str, ajustes: Ajustes, corridas: list,
                       dispersion, hallazgos: list) -> None:
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
    consecuencia = "No se comprobó: hace falta más de una llamada.\n"
    if dispersion:
        d = dispersion
        sin_fragmentos = not d["fragmentos"] or d["fragmentos"] == [()]
        forma_estable = len(d["n_afirmaciones"]) == 1 and d["tipos_estables"]
        if forma_estable and d["similitud_afirmaciones"] > 0.95:
            lectura = (
                "**El conjunto de afirmaciones es estable: mismo número, mismos tipos y "
                "prácticamente el mismo contenido.** Lo que varía es la redacción palabra a "
                "palabra, en el sitio que enseña el desvío de arriba. La ablación del 7.3 sigue "
                "siendo legible con N=3, porque lo que compara son afirmaciones y veredictos, no "
                "la literalidad del texto.")
        elif forma_estable:
            lectura = (
                f"**La forma del conjunto es estable —mismo número y mismos tipos— pero el texto de "
                f"las afirmaciones varía ({d['similitud_afirmaciones']*100:.1f} % en común).** Eso "
                f"no rompe la ablación por sí solo, porque la fila con verificación y la fila sin "
                f"ella se comparan por veredictos; pero sí obliga a que cualquier métrica que mire "
                f"el CONTENIDO de una afirmación (fidelidad literal, NLI) se reporte con su "
                f"dispersión y no como un número único.")
        else:
            lectura = (
                "**El conjunto de afirmaciones VARÍA entre corridas idénticas.** Antes de dar por "
                "buena cualquier fila del 7.3 hay que medir el tamaño de ese ruido y comprobar que "
                "la diferencia entre con y sin verificación lo supera. Si no lo supera, la ablación "
                "necesita más repeticiones o una métrica menos sensible al conjunto.")
        consecuencia = f"""{d['n_corridas']} llamadas con la MISMA entrada, la MISMA semilla y
temperatura 0, comparadas por dimensiones separadas, porque no todas cuestan lo mismo:

| Dimensión | Resultado |
|---|---|
| 1. Bytes de la respuesta | {'idénticos' if d['bytes_identicos'] else '**distintos**'} |
| 2. Número de afirmaciones | {d['n_afirmaciones']} — {'estable' if len(d['n_afirmaciones']) == 1 else '**varía**'} |
| 3. Tipos de las afirmaciones | {'estables' if d['tipos_estables'] else '**varían**'}: {[list(t) for t in d['tipos']]} |
| 4. `fragmento_id` citados | {'estables' if d['fragmentos_estables'] else '**varían**'}: {[list(t) for t in d['fragmentos']]} |
| 5. Texto de las afirmaciones | {d['similitud_afirmaciones']*100:.1f} % en común |
| 6. Redacción | {d['similitud_prosa']*100:.1f} % de caracteres en común |

Las tres primeras dimensiones son la **forma del conjunto**, que es lo que lee la ablación. Las dos
últimas son **redacción**. Se separan porque dos corridas pueden traer dos afirmaciones de tipo
`conocimiento` cada una y estar afirmando cosas distintas: sin la dimensión 5, eso pasaría por
estabilidad.
{f'''
Y como los bytes difieren, dónde empiezan a hacerlo (posición {d["primer_desvio"]["posicion"]}):

```
A: ...{d["primer_desvio"]["a"]}...
B: ...{d["primer_desvio"]["b"]}...
```
''' if d["primer_desvio"] else ''}

**Lo que estos números deciden, que es lo que importa.** Que varíe la redacción y que varíe el
conjunto de afirmaciones no son la misma cosa, y solo lo segundo compromete el **7.3**: la ablación
compara la fila con verificación contra la fila sin ella, y si el conjunto de afirmaciones bailara
entre corridas idénticas, esa diferencia —el argumento central del proyecto— podría quedar por
debajo del ruido de medida.

{lectura}
{'''
**Aviso sobre la dimensión 4:** en el 2.2 no hay recuperación, así que `fragmento_id` es nulo en
todas las afirmaciones y su estabilidad aquí no significa nada. Esta medida hay que repetirla en la
fase 3, con recuperación de verdad, que es cuando citar o no citar el mismo fragmento empieza a ser
una diferencia real.
''' if sin_fragmentos else ''}
**Aplica la regla del 7.1**: temperatura 0 con semilla es una *petición* de determinismo, no
determinismo —en un servidor con lotes variables la aritmética en coma flotante cambia con el
tamaño del lote—, así que toda medida de calidad va con N=3 repeticiones y se reporta la
dispersión. Saberlo hoy evita medir ruido en la fase 7 creyendo que se mide el sistema.
"""
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

## Determinismo con temperatura 0 y seed fijo: cuánto varía, y en qué

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
