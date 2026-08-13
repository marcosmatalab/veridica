#!/usr/bin/env python3
"""Humo del verificador NLI (encargo 4.3): 10 pares a mano, y un vistazo a ojo antes del umbral.

    python scripts/humo_nli.py

No gasta: el modelo corre en CPU aquí mismo. Fuera de la puerta porque son 279 M de parámetros que
el CI no tiene, mismo criterio que el corpus (ADR 0001).

**LOS DIEZ PARES SON DE ESTE CORPUS, NO DE LIBRO**, y ese es el punto: mDeBERTa se entrenó en prosa
general y las hipótesis de este proyecto van llenas de identificadores —`@Valid`, `BindingResult`,
`@ModelAttribute`—. Un NLI que nunca vio eso puede dar `neutral` a implicaciones obvias, que es la
misma lección que dio la derivación española del 3.1: **medir qué le hace el modelo a los
identificadores antes de creerse el umbral.** Por eso esto imprime la probabilidad de las TRES
etiquetas y no solo el veredicto: un 0,45 de `entailment` contra un 0,44 de `neutral` es un empate
disfrazado de decisión, y eso solo se ve mirando.
"""
import sys

sys.path.insert(0, ".")

from app.core.verificador_nli import UMBRAL, VerificadorNLI  # noqa: E402

FRAGMENTO_VALIDACION = (
    "Para validar un formulario en un POST hay que anotar el parametro con @Valid y poner "
    "BindingResult justo detras. El bean BindingResult recoge los errores de validacion y si se "
    "coloca en otro sitio Spring lanza una excepcion. Sin @Valid la validacion no se ejecuta."
)
FRAGMENTO_SESION = (
    "La sesion se almacena en el servidor y la cookie solo contiene el identificador. "
    "Las cookies son apropiadas para datos no sensibles como la preferencia de idioma. "
    "Cuando el usuario cierra el navegador o pasa el timeout, la sesion se pierde."
)

#: (hipotesis, fragmento, esperado). Cinco que implican, tres neutrales, dos contradicciones, como
#: pide el enunciado. Las que llevan identificadores están marcadas: son las que hay que mirar.
PARES = [
    ("@Valid activa la validacion del formulario.", FRAGMENTO_VALIDACION, "verificada", True),
    ("BindingResult recoge los errores de validacion.", FRAGMENTO_VALIDACION, "verificada", True),
    ("BindingResult tiene que ir justo detras del parametro anotado.", FRAGMENTO_VALIDACION,
     "verificada", True),
    ("Los datos de la sesion se guardan en el servidor.", FRAGMENTO_SESION, "verificada", False),
    ("La cookie solo lleva el identificador de la sesion.", FRAGMENTO_SESION, "verificada", False),
    ("Las cookies se pueden usar para guardar el idioma preferido.", FRAGMENTO_SESION,
     "verificada", False),
    ("La sesion sobrevive al cierre del navegador.", FRAGMENTO_SESION, "podada", False),
    ("Sin @Valid la validacion se ejecuta igualmente.", FRAGMENTO_VALIDACION, "podada", True),
    # ESPERADO CORREGIDO tras la primera corrida, y el motivo se queda escrito porque es una
    # distincion real: con CERO vocabulario en comun el sistema no puede separar "no viene a cuento"
    # de "el fragmento no lo sostiene", asi que declara `no_verificable` en vez de elegir uno. Aguas
    # abajo alimenta la misma decision que `reintento` -la afirmacion no esta respaldada-, pero
    # decirlo como veredicto seria afirmar mas de lo que se sabe.
    ("El controlador se encarga de renderizar la plantilla Pebble.", FRAGMENTO_VALIDACION,
     "no_verificable", False),
    ("La base de datos se replica en tres nodos.", FRAGMENTO_SESION, "reintento_con_señal", False),
]


def main() -> int:
    v = VerificadorNLI()
    print(f"modelo en {v.dispositivo} | umbral {UMBRAL} (SIN CALIBRAR, barrido en el 4.6)\n")
    aciertos = 0
    con_identificador = []
    for hipotesis, fragmento, esperado, tiene_ident in PARES:
        r = v.verificar(hipotesis, fragmento)
        bien = r["veredicto"] == esperado
        aciertos += bien
        marca = "ident" if tiene_ident else "     "
        print(f"{'OK ' if bien else 'MAL'} [{marca}] {r['veredicto']:<20} "
              f"({r.get('nli', '-'):<13} {r.get('probabilidad', 0):.3f})  "
              f"esperado {esperado}")
        print(f"        hipotesis: {hipotesis}")
        if r.get("frase"):
            print(f"        frase elegida (cobertura {r['cobertura']}): {r['frase'][:90]}")
        if tiene_ident:
            con_identificador.append(bien)

    print(f"\naciertos: {aciertos}/{len(PARES)}")
    if con_identificador:
        print(f"CON IDENTIFICADORES: {sum(con_identificador)}/{len(con_identificador)}  "
              f"<- si esto va peor que el resto, el umbral esta midiendo el vocabulario del modelo "
              f"y no la implicacion")
    return 0 if aciertos >= 8 else 1


if __name__ == "__main__":
    raise SystemExit(main())
