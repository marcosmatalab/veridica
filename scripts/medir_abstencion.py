#!/usr/bin/env python3
"""Tasa de abstención y forma de las respuestas de `corregir`, desde las trazas (encargo 4.4).

    python scripts/medir_abstencion.py

**DOS NÚMEROS Y NO UNO, y el motivo es que quedarse con el fino también es una selección.** El
desglose por motivo solo puede salir de las consultas **nuevas** —el motivo de fallo empezó a
persistirse en el 4.5, así que antes de eso no existe—, pero reportar solo esas sería elegir la
muestra por **cuándo**, que es la forma más común del principio 11 en software: datos de después del
cambio, esta vez. Así que van los dos:

1. La **tasa total** de abstención sobre TODAS las respuestas, que sí se puede contar aunque no se
   pueda desglosar. El número grande no depende del cambio de instrumento.
2. El **desglose por motivo** sobre las nuevas, **con su n al lado**, para que se vea sobre qué corre.

Y el denominador de cada uno va escrito, porque una tasa sin denominador es una opinión con decimales.

**LA MUESTRA DE `corregir` SE COMPRUEBA, NO SE SUPONE.** `version_prompt` lleva el modo dentro desde
el 4.1 (`4.4-2026-08-13/corregir`), así que la consulta filtra por ahí en vez de fiarse de la columna
`modo`: son dos campos distintos y podrían discrepar — el modo es lo que pidió el cliente y la versión
es el prompt que de verdad se usó. Es la primera vez que ese campo sirve para algo, y sirve justo para
lo que se puso.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg                                                          # noqa: E402

from app.core.entorno import cargar_dotenv                              # noqa: E402

URL = os.environ.get("DATABASE_URL") or "postgresql://veridica:veridica_local@127.0.0.1:5434/veridica"


def fila(cur, sql, params=None):
    # Sin `params` se ejecuta SIN diccionario: psycopg solo interpreta `%` como marcador cuando se
    # le pasan parametros, y estas consultas llevan `%` dentro de un LIKE.
    cur.execute(sql, params) if params else cur.execute(sql)
    return cur.fetchall()


def main() -> int:
    cargar_dotenv()
    with psycopg.connect(URL, connect_timeout=5) as con, con.cursor() as cur:
        cur.execute("SET statement_timeout = '15s'")

        total, abst = fila(cur, """
            SELECT count(*), count(*) FILTER (WHERE abstencion) FROM respuestas
        """)[0]
        print("=" * 96)
        print("1) TASA TOTAL DE ABSTENCION  (denominador: TODAS las respuestas persistidas)")
        print("=" * 96)
        pct = (abst / total * 100) if total else 0.0
        print(f"   {abst} de {total} respuestas -> {pct:.1f} %")

        print("\n" + "=" * 96)
        print("2) DESGLOSE POR MOTIVO  (denominador: solo las que llevan motivo en la traza)")
        print("=" * 96)
        # El campo vive en `etapas->generacion->motivo_fallo` y lo escribe el 4.5. Se agrupa por la
        # CLASE del motivo -lo que va antes de los dos puntos- porque el texto lleva los
        # milisegundos dentro: agrupar por la cadena entera da una fila por cada milisegundo, que es
        # un histograma del reloj disfrazado de reparto de causas.
        conmotivo = fila(cur, """
            SELECT count(*) FROM respuestas
             WHERE etapas->'generacion' ? 'motivo_fallo'
               AND COALESCE(etapas->'generacion'->>'motivo_fallo', '') <> ''
        """)[0][0]
        print(f"   n = {conmotivo} respuestas con motivo de fallo persistido, de {total} totales"
              f"  ({(conmotivo / total * 100) if total else 0:.1f} %)")
        for motivo, n in fila(cur, """
            SELECT split_part(etapas->'generacion'->>'motivo_fallo', ':', 1) AS clase, count(*)
              FROM respuestas
             WHERE etapas->'generacion' ? 'motivo_fallo'
               AND COALESCE(etapas->'generacion'->>'motivo_fallo', '') <> ''
             GROUP BY 1 ORDER BY 2 DESC
        """):
            print(f"     {motivo:34} {n}")
        print("     (las clases que la seccion 8 define y que NO aparecen -contrato roto tras "
              "reintento, todo podado, nada que recuperar- no es que sean cero: es que hoy nadie "
              "las escribe, y eso NO es lo mismo)")

        print("\n" + "=" * 96)
        print("3) RESPUESTAS QUE SE SOSTIENEN SOLO CON `conocimiento` MARCADO")
        print("=" * 96)
        solo, con_afirm = fila(cur, """
            SELECT count(*) FILTER (WHERE tipos = ARRAY['conocimiento']), count(*)
              FROM (SELECT respuesta_id, array_agg(DISTINCT tipo ORDER BY tipo) AS tipos
                      FROM afirmaciones WHERE tipo <> 'andamiaje' GROUP BY respuesta_id) x
        """)[0]
        print(f"   {solo} de {con_afirm} respuestas con afirmaciones factuales "
              f"({(solo / con_afirm * 100) if con_afirm else 0:.1f} %) no citan el temario ni una vez")

        print("\n" + "=" * 96)
        print("4) FORMA DE `corregir`, FILTRADA POR version_prompt (no por la columna `modo`)")
        print("=" * 96)
        for etiqueta, patron in (("corregir", "%/corregir"), ("responder", "%/responder"),
                                 ("acompanar", "%/acompanar")):
            filas = fila(cur, """
                SELECT count(*) AS respuestas,
                       round(avg(n)::numeric, 1) AS afirm_media, max(n) AS afirm_max,
                       round(avg(r.tokens_salida)::numeric, 0) AS tokens_media,
                       max(r.tokens_salida) AS tokens_max,
                       round(avg(r.tokens_salida::numeric / NULLIF(n, 0)), 0) AS tokens_por_afirm
                  FROM respuestas r
                  JOIN consultas c ON c.id = r.consulta_id
                  LEFT JOIN (SELECT respuesta_id, count(*) n FROM afirmaciones GROUP BY 1) a
                         ON a.respuesta_id = r.id
                 WHERE c.version_prompt LIKE %(p)s
            """, {"p": patron})
            n, media, mx, tk, tkmax, por = filas[0]
            print(f"   {etiqueta:10} respuestas={n or 0:3}  afirmaciones media={media} max={mx}  "
                  f"tokens_salida media={tk} max={tkmax}  tokens/afirmacion={por}")
        print("\n   (respuestas con version_prompt SIN modo dentro, o sea anteriores al 4.1):",
              fila(cur, "SELECT count(*) FROM consultas WHERE version_prompt NOT LIKE '%/%'")[0][0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
