#!/usr/bin/env python3
"""Qué deja pasar la guarda del 4.4, y cuánto cuesta el peor caso que deja pasar.

    python scripts/medir_guarda_calculo.py

**PONER LA GUARDA NO ES MEDIRLA.** Un tope escrito da la sensación de estar protegido, que es
distinto de estarlo: la pregunta que hay que contestar con un número es *¿cuánto vale este tope en el
peor caso que existe para cazar?* Aquí se contesta en las dos direcciones, porque las dos pueden
fallar:

1. **Lo que la guarda ADMITE**: expresiones legales pegadas al límite. Si la peor de ellas tarda más
   que el presupuesto de verificación (2 s por consulta, sección 8), el tope está mal puesto aunque
   nunca haya fallado.
2. **Lo que la guarda RECHAZA**: las bombas. Rechazarlas no basta, hay que rechazarlas **rápido** —
   una guarda que tarda tres segundos en decir que no es la misma denegación de servicio que
   pretendía evitar, con otro nombre.

Y la tercera parte son casos de temario mirados **a ojo**: el agregado *"pasa el 90 %"* promedia y al
promediar disuelve la estructura que señala la causa.
"""
import sys
import time

sys.path.insert(0, ".")

from app.core.verificador_calculo import (MAX_CARACTERES, MAX_DIGITOS,  # noqa: E402
                                          MAX_DIGITOS_ARGUMENTO, admisible, verificar)

#: Aritmética de un temario de FP, con su veredicto esperado. Se miran a ojo, no se cuentan.
CASOS = [
    ("2+2", "4", "verificada"),
    ("(255-192)+1", "64", "verificada"),                    # subredes, ASIR
    ("2**32", "4294967296", "verificada"),                  # direcciones IPv4
    ("2**32-2", "4294967294", "verificada"),
    ("binomial(7,2)", "21", "verificada"),                  # combinatoria
    ("factorial(20)", "2432902008176640000", "verificada"),
    ("10/3", "3,33", "verificada"),                         # redondeo a lo que ESCRIBE
    ("10/3", "3,3", "verificada"),
    ("10/3", "3,5", "podada"),
    ("sqrt(2)", "1,41", "verificada"),
    ("pi*2", "6,28", "verificada"),
    ("100*1.21", "121", "verificada"),                      # IVA
    ("1024*1024", "1048576", "verificada"),
    ("2**100", "1267650600228229401496703205376", "verificada"),   # 31 cifras: sin float
    ("2**100", "1267650600228229401496703205377", "podada"),       # una cifra mal
    ("1/8", "0,13", "verificada"),                          # media hacia arriba, la que se acepta
    ("1/8", "0,12", "podada"),                              # al par: ya no es segunda salida (ADR 0018)
    ("1/8", "0,11", "podada"),
    ("3.10", "3,10", "verificada"),
    ("10/0", "5", "no_verificable"),
    ("x + 1", "5", "no_verificable"),
    ("for i in range(10): print(i)", "10", "no_verificable"),
    ('__import__("os").system("dir")', "0", "no_verificable"),
    ("2+2", None, "no_verificable"),                        # el null del contrato
]

#: Expresiones que la guarda ADMITE, pegadas al límite. Son las que hay que cronometrar.
PEGADAS_AL_LIMITE = [
    "10**999",
    "2**3320",
    "factorial(449)",
    "binomial(3300,1650)",
    "9" * 190,
    ("9" * 40 + "*") * 4 + "9" * 39,
    "sqrt(2)+" * 24 + "sqrt(2)",
    "exp(30)",
    "sin(10**29)",
    "factorial(449)*factorial(449)/factorial(449)",
    # Lo más caro que cabe en 200 caracteres: transcendentales con el argumento pegado a su tope,
    # que es donde el coste no está en el resultado sino en la precisión del camino.
    ("sin(10**29)+" * 16)[:-1],
    ("tan(10**29)*" * 16)[:-1],
    ("factorial(69)+" * 14)[:-1],
    ("binomial(300,150)*" * 11)[:-1],
    "sqrt(" * 30 + "2" + ")" * 30,
]

#: Bombas. Tienen que salir `no_verificable`, y tienen que salir DEPRISA.
BOMBAS = [
    "2**2**2**30",
    "10**999999999",
    "factorial(100000)",
    "factorial(100000)/factorial(100000)",       # magnitud final 0: la cancelación abre el boquete
    "binomial(10**9,10**8)",
    "sin(10**900)",
    "exp(10**6)",
    # Anidar paréntesis NO es una bomba: `9**999` son 954 cifras y se calcula en medio milisegundo.
    # Estaba en esta lista por parecerlo, y salió `podada` con razón. Lo que la convierte en bomba es
    # el exponente, así que es el exponente lo que va aquí.
    "(" * 50 + "9" + ")" * 50 + "**99999",
    "factorial(449)*" * 13 + "factorial(449)",     # 13 veces el tope: la magnitud SUMA
]


def cronometrar(expresion: str, afirmado: str = "1"):
    """Dos pasadas, y se devuelven las DOS. **La primera medida de `sqrt(2)+...` dio 31 ms y la
    segunda 1,7**: sympy calienta sus cachés internas, así que un solo cronómetro sobre la primera
    llamada publica un número que es en un 95 % arranque de la librería. El proceso de la API es
    largo, o sea que el número que decide es el caliente; el frío se paga una vez y también se dice,
    en vez de elegir el que quede mejor."""
    t = time.perf_counter()
    v = verificar({"expresion": expresion, "resultado_afirmado": afirmado})
    frio = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    v = verificar({"expresion": expresion, "resultado_afirmado": afirmado})
    return frio, (time.perf_counter() - t) * 1000, v


def main() -> int:
    print(f"topes: {MAX_CARACTERES} caracteres, {MAX_DIGITOS} digitos, "
          f"{MAX_DIGITOS_ARGUMENTO} digitos de argumento transcendental\n")

    print("=" * 104)
    print("1) CASOS DE TEMARIO, A OJO")
    print("=" * 104)
    fallos = 0
    for expresion, afirmado, esperado in CASOS:
        frio, ms, v = cronometrar(expresion, afirmado)
        marca = " " if v["veredicto"] == esperado else "X"
        fallos += marca == "X"
        detalle = v.get("comparacion") or v.get("motivo") or ""
        print(f"{marca} {expresion[:32]:34} = {str(afirmado)[:12]:14} -> "
              f"{v['veredicto']:15} {detalle[:28]:30} {ms:7.2f} ms")

    print("\n" + "=" * 100)
    print("2) LO QUE LA GUARDA ADMITE, PEGADO AL LIMITE (el peor caso que existe para cazar)")
    print("=" * 104)
    peor = peor_frio = 0.0
    for expresion in PEGADAS_AL_LIMITE:
        ok, _ = admisible(expresion)
        frio, ms, v = cronometrar(expresion)
        if v["veredicto"] != "no_verificable":
            peor, peor_frio = max(peor, ms), max(peor_frio, frio)
        print(f"  {expresion[:40]:42} admisible={str(ok):5} -> {v['veredicto']:15} "
              f"{(v.get('motivo') or ''):26} {frio:8.2f} / {ms:7.2f} ms")
    print(f"\n  PEOR CASO ADMITIDO: {peor:.2f} ms en caliente ({peor_frio:.2f} ms en frio)")

    print("\n" + "=" * 100)
    print("3) BOMBAS: tienen que salir no_verificable, y RAPIDO")
    print("=" * 104)
    peor_bomba = 0.0
    for expresion in BOMBAS:
        frio, ms, v = cronometrar(expresion)
        peor_bomba = max(peor_bomba, ms)
        marca = " " if v["veredicto"] == "no_verificable" else "X"
        fallos += marca == "X"
        print(f"{marca} {expresion[:40]:42} -> {v['veredicto']:15} "
              f"{(v.get('motivo') or ''):32} {frio:8.2f} / {ms:7.2f} ms")
    print(f"\n  PEOR RECHAZO: {peor_bomba:.2f} ms")

    print(f"\ncasos que no dan lo esperado: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
