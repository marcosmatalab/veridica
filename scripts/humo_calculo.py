#!/usr/bin/env python3
"""Humo del verificador de cálculo (encargo 4.4). Llamada REAL: este script gasta dinero.

    python scripts/humo_calculo.py

**POR QUÉ HACE FALTA MIRAR ESTO A OJO Y NO BASTA CON LOS TESTS.** En las 345 afirmaciones reales que
hay en la base, **no hay ni una de tipo `calculo`**: 337 `literal` y 8 `parafrasis`. O sea que el 4.4
se ha construido entero contra casos que escribí yo, y los casos que uno escribe se parecen
sospechosamente a lo que uno ya sabe manejar. Aquí se le pregunta al modelo de verdad, con el prompt
de verdad y con el contrato de verdad, y se mira **qué escribe él** en `expresion` y en
`resultado_afirmado`.

Contesta a tres preguntas que ningún test puede contestar:

1. **¿La gramática nueva viaja?** `resultado_afirmado` es un campo con `pattern`, así que la
   decodificación restringida no puede emitir nada que no sea un número. Se comprueba que el campo
   llega y con qué forma.
2. **¿Qué mete el modelo en `expresion`?** El tope de 200 caracteres se puso a ojo por falta de
   datos; esto es el primer dato. Si el modelo escribe código donde esperábamos aritmética, sale
   `no_verificable` y hay que saberlo.
3. **¿Y usa el `null`?** Cuando su resultado no es un número, ¿lo dice o deforma el campo? Es el 7bis
   comprobado en vivo en vez de razonado.

No hay fragmentos del temario aquí (eso pide Postgres con el corpus, ADR 0001), así que se le dice
que las afirmaciones factuales van como `conocimiento`. Lo que se está mirando es el CÁLCULO, que no
depende del contexto.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.entorno import cargar_dotenv                                       # noqa: E402
from app.core.inferencia import Ajustes, ClienteInferencia, Llamada              # noqa: E402
from app.core.prompts import sistema                                             # noqa: E402
from app.core.verificador_calculo import verificar                               # noqa: E402
from app.modelos.contrato import ContratoRoto, response_format, validar_forma    # noqa: E402

SIN_CORPUS = ("No tienes fragmentos del temario, asi que toda afirmacion factual que no sea un "
              "calculo va con tipo 'conocimiento' y fragmento_id nulo.")

#: Ejercicios con resultado, que es el momento 4 de la demo. El último NO tiene resultado numérico:
#: está para ver si el modelo usa el `null` o se inventa un número para rellenar el campo.
EJERCICIOS = [
    ("corregir", "Un alumno dice que en una subred /26 caben 62 equipos utiles. Comprueba si el "
                 "numero le sale bien."),
    ("responder", "Cuantas combinaciones distintas de 2 asignaturas se pueden elegir entre 7? "
                  "Dame el numero."),
    ("corregir", "Un alumno calcula el IVA de 250 euros al 21 % y le da 302,50 euros. Revisalo."),
    ("responder", "Cuantas direcciones IPv4 distintas existen en total? Dame el numero."),
    ("responder", "Que ventajas tiene normalizar una base de datos a tercera forma normal?"),
]


def una_llamada(cliente, modo: str, pregunta: str) -> dict:
    mensajes = [{"role": "system", "content": sistema(modo, contexto=False) + "\n" + SIN_CORPUS},
                {"role": "user", "content": pregunta}]
    llamada = Llamada()
    t0 = time.perf_counter()
    crudo, fin, uso = "", None, None
    for trozo in cliente.stream(mensajes, response_format(), traza=llamada):
        if trozo.uso:
            uso = trozo.uso
        if trozo.fin:
            fin = trozo.fin
        if trozo.texto:
            crudo += trozo.texto
    return {"crudo": crudo, "ms": (time.perf_counter() - t0) * 1000, "fin": fin, "uso": uso}


def main() -> int:
    cargar_dotenv()
    try:
        cliente = ClienteInferencia(Ajustes.desde_entorno())
    except Exception as e:                                  # noqa: BLE001
        print(f"mal configurado: {type(e).__name__}: {e}")
        return 2

    calculos, longitudes, nulos, sin_calculo = [], [], 0, []
    for modo, pregunta in EJERCICIOS:
        r = una_llamada(cliente, modo, pregunta)
        print("=" * 100)
        print(f"[{modo}] {pregunta}   ({r['ms']:.0f} ms)")
        try:
            respuesta = validar_forma(json.loads(r["crudo"]))
        except (json.JSONDecodeError, ContratoRoto) as e:
            # EL CRUDO A LA VISTA. Un "contrato roto" puede ser el modelo escribiendo mal o el
            # PROVEEDOR CORTANDO por tope de tokens, y son averias distintas con arreglos distintos.
            print(f"  CONTRATO ROTO: {e}   (fin={r['fin']}, uso={r['uso']})")
            print(f"  ultimos 200 caracteres del crudo: ...{r['crudo'][-200:]!r}")
            continue
        print(f"  prosa: {respuesta.respuesta_redactada[:150]}")
        del_caso = [a for a in respuesta.afirmaciones if a.tipo == "calculo"]
        if not del_caso:
            sin_calculo.append(pregunta)
            print(f"  sin afirmaciones de calculo (tipos: "
                  f"{[a.tipo for a in respuesta.afirmaciones]})")
        for a in del_caso:
            v = verificar({"expresion": a.expresion, "resultado_afirmado": a.resultado_afirmado})
            calculos.append((a, v))
            longitudes.append(len(a.expresion))
            nulos += a.resultado_afirmado is None
            print(f"  expresion={a.expresion!r} ({len(a.expresion)} car.)  "
                  f"afirmado={a.resultado_afirmado!r}")
            print(f"     -> {v['veredicto']:15} {v.get('comparacion') or v.get('motivo') or ''}"
                  f"   recalculado={v.get('recalculado', '-')}")
            print(f"     texto: {a.texto[:110]}")

    print("\n" + "=" * 100)
    print(f"afirmaciones de calculo: {len(calculos)} en {len(EJERCICIOS)} consultas")
    if longitudes:
        print(f"longitud de `expresion`: min {min(longitudes)}, max {max(longitudes)} "
              f"(el tope esta en 200)")
    print(f"con resultado_afirmado nulo: {nulos}")
    print(f"consultas sin ninguna afirmacion de calculo: {len(sin_calculo)}")
    reparto = {}
    for _, v in calculos:
        reparto[v["veredicto"]] = reparto.get(v["veredicto"], 0) + 1
    print(f"reparto de veredictos: {reparto}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
