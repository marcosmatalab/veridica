#!/usr/bin/env python3
"""Encargo 2.6: extrae el glosario y lo valida SIN MODELO. Llamadas REALES: este script gasta.

    python scripts/glosario.py --asignatura 0613 --repeticiones 3   # la pasada que decide el momento 3
    python scripts/glosario.py                                      # el corpus entero, una pasada
    python scripts/glosario.py --conflictos                         # solo la consulta, sin gastar

QUIEN EXTRAE NO VALIDA. El modelo pequeño lee la FRASE DEFINITORIA del fragmento -no el fragmento
entero: marcar el fragmento acertaba 3 de 20 y la frase acierta 13 de 20, medido en el 1.4- y
devuelve `{termino, definicion}` con salida tipada. Despues, una comparacion de cadenas normalizada
comprueba que esa definicion esta LETRA A LETRA en el fragmento. Sin modelo, sin umbral: o esta o no
esta. La que no pasa, no entra, y se cuenta.

EL CONFLICTO NO SE BUSCA CON EMBEDDINGS. El detector del 1.8 compara fragmentos por similitud y da
0,564 en el par de MVC, porque cada definicion va enterrada en 512 tokens de otra cosa. Aqui la
clave de comparacion es el TERMINO, y desde el ADR 0012 -que permite varias definiciones por
termino- eso es un GROUP BY: determinista, sin modelo y sin umbral.
"""
import argparse
import collections
import concurrent.futures as futuros
import json
import os
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                                    # noqa: E402

from app.core.entorno import cargar_dotenv                                        # noqa: E402
from app.core.inferencia import (Ajustes, ClienteInferencia, ErrorDefinitivo,     # noqa: E402
                                 ErrorTransitorio)
from app.modelos.glosario import (ContratoDeGlosarioRoto, esquema_de_extraccion,  # noqa: E402
                                  leer_entrada, validar_literal)

FRAGMENTOS = "corpus/fragmentos.jsonl"
MAPA = "corpus/mapa_asignaturas.jsonl"

SISTEMA = (
    "Extraes entradas de glosario de material docente de Formacion Profesional.\n"
    "Del texto que te den, dices QUE TERMINO se define y cual es su definicion.\n"
    "REGLA QUE MANDA SOBRE TODAS: la definicion se COPIA LETRA A LETRA del texto, sin reescribirla, "
    "sin resumirla y sin corregirle nada, ni una coma. Si tienes que cambiar algo para que quede "
    "bonito, no lo cambies: copia.\n"
    "Si el texto no define ningun termino -es un ejemplo, una instruccion o prosa suelta-, "
    "'hay_definicion' es 'no' y los otros dos campos van con un guion."
)


def leer_jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def candidatos(codigo: str | None) -> list:
    """Los fragmentos con frase definitoria, ya filtrados por el mapa del 2.1."""
    mapa = {e["clave"]: e for e in leer_jsonl(MAPA)}
    salida = []
    for fr in leer_jsonl(FRAGMENTOS):
        if not (fr.get("frase_definitoria") or "").strip():
            continue
        entrada = mapa.get(f"{fr['titulacion']}/{fr['asignatura']}")
        if entrada is None or entrada.get("excluido"):
            continue
        if codigo and entrada["codigo"] != codigo:
            continue
        salida.append((fr, entrada))
    return salida


def ids_en_base(url: str) -> dict:
    """(ruta, orden) -> (fragmento_id, asignatura_id, texto). El glosario apunta a filas REALES."""
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute("SELECT d.ruta, f.orden, f.id, f.asignatura_id, f.texto"
                    "  FROM fragmentos f JOIN documentos d ON d.id = f.documento_id")
        return {(ruta, orden): (fid, aid, texto) for ruta, orden, fid, aid, texto in cur.fetchall()}


def extraer_uno(cliente: ClienteInferencia, frase: str) -> tuple:
    """Devuelve (entrada|None, uso, motivo). No lanza: un fallo es un descarte contado."""
    mensajes = [{"role": "system", "content": SISTEMA},
                {"role": "user", "content": frase}]
    try:
        texto, uso, _ = cliente.completar(mensajes, esquema_de_extraccion())
    except (ErrorTransitorio, ErrorDefinitivo) as e:
        return None, None, f"llamada fallida: {type(e).__name__}"
    try:
        entrada = leer_entrada(json.loads(texto))
    except (json.JSONDecodeError, ContratoDeGlosarioRoto) as e:
        return None, uso, f"contrato roto: {e}"
    if entrada.hay_definicion != "si":
        return None, uso, "el modelo dice que ahi no se define nada"
    return entrada, uso, ""


def una_pasada(cliente, trabajos: list, hilos: int) -> dict:
    """Extrae y VALIDA. Devuelve el recuento y las entradas que pasaron."""
    aceptadas, descartes = [], collections.Counter()
    tokens_entrada = tokens_salida = 0
    t0 = time.perf_counter()

    def trabajar(t):
        fr, fid, aid, texto_en_base = t
        entrada, uso, motivo = extraer_uno(cliente, fr["frase_definitoria"])
        return fr, fid, aid, texto_en_base, entrada, uso, motivo

    with futuros.ThreadPoolExecutor(max_workers=hilos) as pool:
        for fr, fid, aid, texto, entrada, uso, motivo in pool.map(trabajar, trabajos):
            if uso:
                tokens_entrada += uso.tokens_entrada
                tokens_salida += uso.tokens_salida
            if entrada is None:
                descartes[motivo.split(":")[0]] += 1
                continue
            # LA VALIDACION, sin modelo: la definicion tiene que estar letra a letra en el fragmento
            # de la BASE, que es el texto que se le citaria al alumno.
            pasa, evidencia = validar_literal(entrada.definicion, texto)
            if not pasa:
                descartes["no es literal del fragmento"] += 1
                continue
            aceptadas.append({"asignatura_id": aid, "termino": entrada.termino.lower(),
                              "definicion": entrada.definicion, "fragmento_id": fid,
                              "via_validacion": "literal_sin_modelo", "evidencia": evidencia,
                              "documento": fr["documento"]})
    return {"aceptadas": aceptadas, "descartes": descartes, "intentos": len(trabajos),
            "tokens_entrada": tokens_entrada, "tokens_salida": tokens_salida,
            "segundos": time.perf_counter() - t0}


def guardar(url: str, aceptadas: list, solo_asignatura: int | None) -> int:
    """Guarda SOLO la ultima pasada, y antes borra lo que hubiera de ese alcance.

    No es limpieza cosmetica: si se acumularan pasadas, un termino extraido del fragmento A en la
    pasada 1 y del fragmento B en la 2 apareceria como "dos definiciones" y el GROUP BY del momento
    3 lo cantaria como conflicto. Seria un conflicto FABRICADO POR LA MEDICION, que es justo lo que
    este proyecto no se puede permitir en el momento que mas mira todo el mundo.
    """
    with psycopg.connect(url) as con, con.cursor() as cur:
        if solo_asignatura:
            cur.execute("DELETE FROM glosario WHERE asignatura_id = %s", (solo_asignatura,))
        else:
            cur.execute("DELETE FROM glosario")
        puestas = 0
        for e in aceptadas:
            cur.execute(
                "INSERT INTO glosario (asignatura_id, termino, definicion, fragmento_id,"
                " via_validacion, evidencia) VALUES (%s,%s,%s,%s,%s,%s)"
                " ON CONFLICT (asignatura_id, termino, fragmento_id) DO NOTHING",
                (e["asignatura_id"], e["termino"], e["definicion"], e["fragmento_id"],
                 e["via_validacion"], e["evidencia"]))
            puestas += cur.rowcount
        con.commit()
    return puestas


def conflictos(url: str, asignatura_id: int | None = None, crudo: bool = False) -> list:
    """Terminos definidos mas de una vez, EN SQL: determinista, sin modelo y sin umbral.

    DOS EXCLUSIONES QUE NO SON UN FILTRO DE CALIDAD SINO CORRECCION DE UN ARTEFACTO PROPIO, y las dos
    salieron de mirar la primera corrida:

    1. **Definiciones identicas no son un conflicto**, son la misma definicion contada dos veces.
    2. **Del MISMO documento tampoco.** El troceado del 1.4 solapa 64 tokens, asi que dos fragmentos
       consecutivos comparten texto POR CONSTRUCCION y una definicion que caiga en la zona de solape
       se extrae dos veces. Es exactamente la exclusion que el 1.8 dejo escrita para el detector de
       casi-duplicados, y al estrenar este mecanismo la herede sin heredar su exclusion: de los 6
       "conflictos" de la primera pasada sobre el 0613, TRES eran este artefacto.

    Con `crudo=True` se devuelve lo de antes, sin excluir nada. Sirve para ver el numero mentiroso al
    lado del bueno, que es como se cuenta en este repo.
    """
    filtro = "WHERE g.asignatura_id = %s" if asignatura_id else ""
    if not crudo:
        # `having` extra: al menos dos definiciones distintas y al menos dos documentos distintos.
        extra = ("HAVING count(*) > 1 AND count(DISTINCT lower(g.definicion)) > 1"
                 " AND count(DISTINCT d.ruta) > 1")
    else:
        extra = "HAVING count(*) > 1"
    with psycopg.connect(url) as con, con.cursor() as cur:
        cur.execute(f"""
            SELECT g.asignatura_id, a.codigo, g.termino, count(*) AS veces,
                   array_agg(g.definicion), array_agg(d.ruta)
              FROM glosario g
              JOIN asignaturas a ON a.id = g.asignatura_id
              JOIN fragmentos f ON f.id = g.fragmento_id AND f.asignatura_id = g.asignatura_id
              JOIN documentos d ON d.id = f.documento_id
              {filtro}
             GROUP BY g.asignatura_id, a.codigo, g.termino
            {extra}
             ORDER BY count(*) DESC, g.termino
        """, (asignatura_id,) if asignatura_id else ())
        return [{"asignatura_id": aid, "codigo": cod, "termino": t, "veces": v,
                 "definiciones": defs, "documentos": docs}
                for aid, cod, t, v, defs, docs in cur.fetchall()]


def main() -> int:
    p = argparse.ArgumentParser(description="Glosario del 2.6: extrae, valida sin modelo y guarda.")
    p.add_argument("--url", default=os.environ.get("DATABASE_URL"))
    p.add_argument("--asignatura", help="codigo del BOE, p.ej. 0613, para limitar la pasada")
    p.add_argument("--repeticiones", type=int, default=1,
                   help="pasadas identicas: la decision del momento 3 exige 3 y salir las 3")
    p.add_argument("--hilos", type=int, default=8)
    p.add_argument("--limite", type=int, help="corta el numero de fragmentos (pruebas)")
    p.add_argument("--conflictos", action="store_true", help="solo la consulta, sin gastar")
    p.add_argument("--evidencia", help="ruta del markdown de evidencia")
    p.add_argument("--fecha", default="2026-08-12")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cargar_dotenv()
    if not a.url:
        print("falta DATABASE_URL", file=sys.stderr)
        return 2

    if a.conflictos:
        for c in conflictos(a.url):
            print(f"\n{c['codigo']} · '{c['termino']}' aparece {c['veces']} veces")
            for d, doc in zip(c["definiciones"], c["documentos"]):
                print(f"   - {d[:140]}\n     ({doc})")
        return 0

    try:
        ajustes = Ajustes.desde_entorno()
    except ErrorDefinitivo as e:
        print(f"MAL CONFIGURADO: {e}", file=sys.stderr)
        return 2

    en_base = ids_en_base(a.url)
    trabajos, sin_fila = [], 0
    for fr, _ in candidatos(a.asignatura):
        fila = en_base.get((fr["documento"], fr["orden"]))
        if fila is None:
            sin_fila += 1
            continue
        trabajos.append((fr, fila[0], fila[1], fila[2]))
    if a.limite:
        trabajos = trabajos[:a.limite]
    print(f"fragmentos con frase definitoria: {len(trabajos)}"
          + (f" (asignatura {a.asignatura})" if a.asignatura else "")
          + (f" | {sin_fila} sin fila en base" if sin_fila else ""))

    cliente = ClienteInferencia(ajustes)
    pasadas = []
    try:
        for i in range(1, a.repeticiones + 1):
            r = una_pasada(cliente, trabajos, a.hilos)
            pasadas.append(r)
            tasa = 100 * (r["intentos"] - len(r["aceptadas"])) / max(1, r["intentos"])
            print(f"\npasada {i}: {len(r['aceptadas'])} entradas de {r['intentos']} intentos | "
                  f"descarte {tasa:.1f}% | {r['segundos']:.0f} s | "
                  f"tokens {r['tokens_entrada']}+{r['tokens_salida']}")
            for motivo, n in r["descartes"].most_common():
                print(f"    {n:4d}  {motivo}")
    finally:
        cliente.cerrar()

    de_esta = {e["asignatura_id"] for e in pasadas[-1]["aceptadas"]}
    solo = next(iter(de_esta)) if (a.asignatura and len(de_esta) == 1) else None
    puestas = guardar(a.url, pasadas[-1]["aceptadas"], solo_asignatura=solo)
    print(f"\nguardadas en glosario: {puestas} filas (de la ultima pasada)")

    conf = conflictos(a.url, solo)
    print(f"terminos con mas de una definicion: {len(conf)}")
    for c in conf[:10]:
        print(f"   {c['codigo']} · {c['termino']} ({c['veces']})")

    if a.evidencia:
        escribir_evidencia(a.evidencia, a.fecha, ajustes, pasadas, conf, a)
        print(f"\nevidencia -> {a.evidencia}")
    return 0


def escribir_evidencia(ruta, fecha, ajustes, pasadas, conf, a) -> None:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    precio_e = float(os.environ.get("PRECIO_ENTRADA_PEQ") or 0)
    precio_s = float(os.environ.get("PRECIO_SALIDA_PEQ") or 0)
    filas, tasas, coste_total = [], [], 0.0
    for i, r in enumerate(pasadas, 1):
        tasa = 100 * (r["intentos"] - len(r["aceptadas"])) / max(1, r["intentos"])
        tasas.append(tasa)
        coste = (r["tokens_entrada"] * precio_e + r["tokens_salida"] * precio_s) / 1_000_000
        coste_total += coste
        filas.append(f"| {i} | {r['intentos']} | {len(r['aceptadas'])} | {tasa:.1f} % | "
                     f"{r['tokens_entrada']} | {r['tokens_salida']} | {coste:.6f} | "
                     f"{r['segundos']:.0f} s |")
    dispersion = (f"{min(tasas):.1f} % – {max(tasas):.1f} % (desviación "
                  f"{statistics.pstdev(tasas):.2f})" if len(tasas) > 1 else "una sola pasada")
    lineas_conf = "\n".join(
        f"- **`{c['termino']}`** ({c['codigo']}), {c['veces']} definiciones:\n"
        + "\n".join(f"  - {d[:200]}\n    — `{doc}`" for d, doc in zip(c["definiciones"],
                                                                     c["documentos"]))
        for c in conf[:12]) or "Ninguno."
    texto = f"""# Evidencia: glosario del 2.6 y los términos en conflicto

- **Fecha:** {fecha}
- **Encargo:** 2.6
- **Commit:** `{commit}`
- **Modelo:** `{ajustes.modelo}` · temperatura {ajustes.temperatura} · salida tipada
- **Alcance:** {"asignatura " + a.asignatura if a.asignatura else "corpus entero"}

## Las pasadas

| # | Intentos | Entradas aceptadas | Tasa de descarte | Tokens entrada | Tokens salida | Coste (EUR) | Tiempo |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(filas)}

**Coste real de la pasada: {coste_total:.6f} EUR.** Medido, no estimado: es la primera vez que este
proyecto gasta por volumen y ese número se tiene.

**Sobre qué código corrió esta medida, que es el dato que dentro de un mes nadie podría
reconstruir.** El contrato de extracción llevaba `min_length` en `termino` y `definicion`, así que
la respuesta correcta *"aquí no se define nada"* —un guion en los dos campos— reventaba la
validación y se contaba como **contrato roto** en vez de como *sin definición*. Dos cubos de
descarte intercambiándose casos en silencio, y son los cubos de los que sale la tasa de esta tabla.
Se arregló y **estos números son de una pasada posterior al arreglo**, con los cubos ya separados.

**Dispersión de la tasa de descarte: {dispersion}.** Se reporta así y no como número único porque es
una métrica que mira contenido, y en el 7.1 quedó medido que este proveedor no es determinista ni a
temperatura 0.

**Qué dice la tasa de descarte, que no es lo que parece.** Mide sobre todo al EXTRACTOR y no al
corpus: cada descarte es una definición que el modelo reescribió en vez de copiar, o una frase donde
no había definición ninguna. Una tasa alta con una validación estricta es preferible a una tasa baja
con una validación laxa, porque **lo que entra en el glosario se le va a citar a un alumno**.

## La validación, y por qué es de fiar

Cada entrada aceptada está **letra a letra** en su fragmento: normalización de la sección 8
(minúsculas, espacios colapsados, tildes conservadas) y búsqueda de subcadena. **Sin modelo, sin
umbral y sin porcentaje de parecido.** El extractor es el modelo pequeño y el validador es una
comparación de cadenas, así que el que comprueba no comparte supuesto con el que produce
(principio 6). La vía NLI para definiciones parafraseadas queda para el 4.3, donde ese modelo tiene
que existir de todas formas.

## Términos con más de una definición

Esto es el momento 3 de la demo, y **es una consulta SQL**, no una tubería de similitud:

```sql
SELECT termino, count(*) FROM glosario GROUP BY asignatura_id, termino HAVING count(*) > 1;
```

Determinista, sin modelo y sin umbral (ADR 0012). El detector del 1.8 no vale para esto: compara
fragmentos por embeddings y da 0,564 en el par de MVC, porque cada definición va enterrada en 512
tokens de otra cosa.

{lineas_conf}

## Cómo se reproduce

```bash
python scripts/glosario.py {"--asignatura " + a.asignatura if a.asignatura else ""} --repeticiones {len(pasadas)} --evidencia {ruta}
python scripts/glosario.py --conflictos     # solo la consulta, sin gastar
```
"""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


if __name__ == "__main__":
    sys.exit(main())
