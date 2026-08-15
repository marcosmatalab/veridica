#!/usr/bin/env python3
"""Levanta el servicio EN EL ANFITRIÓN, con torch y GPU, y NO lo da por bueno hasta comprobarlo.

    python scripts/servir_anfitrion.py            # arranca, comprueba y se queda sirviendo
    python scripts/servir_anfitrion.py --solo-comprobar --puerto 8010

## POR QUÉ EXISTE, y la decisión que implementa

**El lunes no se sirve desde el contenedor.** La imagen no lleva torch, así que por el túnel se
serviría la configuración **degradada**: recuperación solo léxica —**58 %** de recall@6 frente al
**80,9 %** de la fusión, medido en el 3.1— y, peor, **paráfrasis SIN VERIFICAR**, o sea **media
tesis del proyecto**. Y los números que se van a citar en la sesión salen de la configuración
**completa**: enseñar la degradada mientras se cita la entera es exactamente la falta de
correspondencia que este repo persigue en los documentos, **cometida en vivo**.

Así que se levanta uvicorn **aquí**, donde ya viven torch y la GPU —que es con lo que corren los
tests y de donde salen todos los números medidos—, apuntando a la base que el contenedor ya expone
en el 5434. **Meter torch en la imagen es lo correcto, pero DESPUÉS del lunes**: cambiar el
empaquetado a dos días de la sesión es tocar el despliegue, que sigue congelado.

## Y POR QUÉ ES UN COMANDO Y NO UNA NOTA EN UN DOCUMENTO

Porque la comprobación previa no se puede dejar a que alguien se acuerde. **"Arriba" no significa
"arriba el mío" — y aquí ni siquiera basta con eso: hace falta "arriba CON SUS CAPACIDADES".** Un
proceso puede contestar `/salud` con 200 y estar sirviendo sin embebedor y sin NLI, que es
literalmente lo que pasa hoy en el contenedor. Es la misma familia del uvicorn viejo ocupando el
puerto, un piso más arriba: allí el proceso no era el mío, aquí el proceso es el mío **y no sabe
hacer lo que la sesión va a enseñar**.

Por eso este script:

1. **Enseña qué intérprete es** antes de nada (miniconda o se planta).
2. Comprueba que `torch` importa **y que ve la GPU**.
3. Arranca uvicorn en un **puerto propio**, para que un residuo no pueda taparlo.
4. Espera leyendo **el log de su propio proceso**, no preguntando al puerto.
5. **Exige que `/salud` diga `embebedor` y `nli` ARRIBA.** Si están caídos, **se para y lo dice**:
   servir así sería enseñar media tesis con los números de la entera.
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: EL PUERTO DE LA SESIÓN ES FIJO, y esto corrige la primera versión de este script.
#:
#: Arrancaba en un puerto nuevo cada vez (8012 un día, 8013 al siguiente) para garantizar que se
#: habla con MI proceso y no con un zombi — la lección que costó media tarde. **Para desarrollo está
#: bien; para la sesión es un peligro con forma de virtud**: el ensayo se hace en un puerto, la
#: sesión arranca en otro, y el comando del túnel que alguien tenga apuntado queda mal **justo
#: cuando no hay tiempo de averiguarlo**.
#:
#: **La garantía de "es el mío" sale de donde ya la teníamos: `arrancado_en`.** Comparar una MARCA
#: DE TIEMPO con el momento en que lanzaste el proceso es mejor prueba que estrenar número de
#: puerto, porque no depende de que nadie más use ese número: depende de un hecho del proceso.
PUERTO_DEMO = 8010
#: La base la sirve el contenedor y no se toca: el `-v` que la borraría sigue siendo el `-v`.
BASE_POR_DEFECTO = "postgresql://veridica:veridica_local@127.0.0.1:5434/veridica"
#: Las dos capacidades que la sesión del lunes ENSEÑA. Sin ellas no es que el sistema vaya peor:
#: es que la mitad de lo que se dice en voz alta no está ocurriendo en pantalla.
CAPACIDADES = ("embebedor", "nli")


def comprobar_interprete() -> int:
    print(f"interprete: {sys.executable}")
    if "miniconda" not in sys.executable.lower():
        print("  ESTE NO ES EL INTERPRETE DECLARADO. torch y CUDA viven en el de miniconda, y los "
              "numeros medidos salen de ahi.", file=sys.stderr)
        return 2
    try:
        import torch
    except Exception as e:                                    # noqa: BLE001
        print(f"  torch NO importa ({type(e).__name__}: {e}): esto serviria la degradada",
              file=sys.stderr)
        return 2
    print(f"  torch {torch.__version__} | cuda disponible: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("  AVISO: sin CUDA el embebedor va a CPU. Arranca igual -la capacidad esta- pero la "
              "latencia no sera la medida (201,2 frag/s en la 5080 frente a 3,1 en CPU).")
    return 0


def salud(puerto: int, intentos: int = 6) -> dict | None:
    """`/salud` NO es una comprobación barata: sondea base, extensiones, redis, worker, embebedor,
    reordenador y NLI, y el worker solo ya midió **2.030 ms**. Con un plazo de 5 s y un intento, un
    arranque sano se leía como *"no contesta"* — la guarda inventándose la avería que perseguía.
    Plazo amplio y varios intentos: lo que se quiere saber es si la capacidad está, no si contesta
    rápido."""
    import json
    for i in range(intentos):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/salud", timeout=20) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError, ValueError, ConnectionError):
            if i < intentos - 1:
                time.sleep(2)
    return None


def es_el_mio(s: dict, lanzado_en: float | None) -> bool:
    """¿El proceso que contesta es EL QUE ACABO DE LANZAR, o un residuo que ya ocupaba el puerto?

    Con puerto fijo esta pregunta vuelve a tener sentido, y la contesta `arrancado_en`: si el
    proceso dice que arrancó ANTES de que yo lanzara el mío, no es el mío. Es la misma comprobación
    que antes daba el puerto nuevo, hecha sobre un hecho del proceso en vez de sobre la suerte de
    que nadie más use ese número.
    """
    if lanzado_en is None:
        return True                                  # `--solo-comprobar`: no hay nada que comparar
    marca = s.get("arrancado_en")
    if not marca:
        return False
    try:
        t = time.mktime(time.strptime(marca, "%Y-%m-%d %H:%M:%S"))
    except ValueError:
        return False
    return t >= lanzado_en - 5                       # margen por el redondeo al segundo


def comprobar_capacidades(puerto: int, lanzado_en: float | None = None) -> int:
    """LA PUERTA QUE DECIDE. No pregunta si hay servidor: pregunta si el servidor ES EL MIO y si
    SABE HACER lo que la sesion va a enseñar."""
    s = salud(puerto)
    if s is None:
        print(f"  /salud no contesta en el {puerto}", file=sys.stderr)
        return 1
    print(f"  arrancado_en {s.get('arrancado_en')}")
    if not es_el_mio(s, lanzado_en):
        print(f"  ESTE NO ES EL PROCESO QUE ACABO DE LANZAR: contesta algo que arrancó antes. "
              f"Hay un residuo ocupando el {puerto} y serviría codigo viejo.", file=sys.stderr)
        return 1
    caidas = set(s.get("caidas") or []) | set(s.get("degradadas") or [])
    faltan = [c for c in CAPACIDADES if c in caidas]
    for c in CAPACIDADES:
        estado = (s.get("dependencias", {}).get(c) or {}).get("estado", "?")
        print(f"  {c:<11} {estado}" + ("   <-- ABAJO" if c in caidas else ""))
    if faltan:
        print(f"\n  NO SE ABRE EL TUNEL: {', '.join(faltan)} abajo. Esto serviria recuperacion "
              f"solo lexica (58 % frente al 80,9 %) y las parafrasis saldrian SIN VERIFICAR, "
              f"mientras la sesion cita los numeros de la configuracion completa.", file=sys.stderr)
        return 1
    print(f"\n  LISTO: {' y '.join(CAPACIDADES)} arriba. El tunel puede apuntar al {puerto}.")
    # EL ULTIMO HUECO DE MEMORIA HUMANA, CERRADO: el comando del tunel se IMPRIME aqui, con este
    # puerto dentro. Es la idea de `fusionar.py` otra vez -si un paso puede olvidarse, se convierte
    # en salida del comando anterior- y quita de en medio la posibilidad de apuntar al 8000 por
    # accidente, que es el contenedor y sirve la configuracion degradada.
    print(f"\n  ABRE EL TUNEL CON ESTO, copiando y pegando:\n\n"
          f"      cloudflared tunnel --url http://127.0.0.1:{puerto}\n")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--puerto", type=int, default=PUERTO_DEMO)
    p.add_argument("--solo-comprobar", action="store_true",
                   help="no arranca nada: comprueba un proceso que ya este sirviendo")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if a.solo_comprobar:
        return comprobar_capacidades(a.puerto)

    if comprobar_interprete() != 0:
        return 2

    lanzado_en = time.time()
    entorno = {**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL", BASE_POR_DEFECTO)}
    registro = os.path.join(RAIZ, f"uvicorn-{a.puerto}.log")
    print(f"arrancando uvicorn en el {a.puerto}; su log en {registro}")
    with open(registro, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.api.main:app",
             "--host", "127.0.0.1", "--port", str(a.puerto)],
            cwd=RAIZ, env=entorno, stdout=log, stderr=subprocess.STDOUT)

    # SE ESPERA LEYENDO EL LOG DEL PROCESO PROPIO, no preguntando al puerto: un residuo ajeno
    # contestaria igual y todas las medidas las serviria codigo que no es este.
    arrancado, t0 = False, time.time()
    while time.time() - t0 < 300:
        if proc.poll() is not None:
            print(f"el proceso murio (codigo {proc.returncode}). Sus ultimas lineas:",
                  file=sys.stderr)
            with open(registro, encoding="utf-8") as f:
                print("".join(f.readlines()[-15:]), file=sys.stderr)
            return 2
        with open(registro, encoding="utf-8") as f:
            texto = f.read()
        if "ERROR" in texto and "bind" in texto:
            print(f"  el puerto {a.puerto} ya esta ocupado: ELIGE OTRO. Un residuo contestaria "
                  f"/salud y serviria codigo viejo.", file=sys.stderr)
            proc.terminate()
            return 2
        # SE ESPERA A "Uvicorn running on", NO a "Application startup complete", y la diferencia
        # costo una vuelta: `startup complete` se imprime cuando el `lifespan` termina, y uvicorn
        # todavia NO esta aceptando conexiones. Comprobar ahi daba "/salud no contesta" sobre un
        # arranque perfectamente sano — la guarda inventandose la averia que perseguia, por esperar
        # un marcador que no significa lo que yo suponia. Es la familia del "arriba" que no era el
        # mio, con el error al otro lado: aqui el proceso ES el mio y todavia no escucha.
        if "Uvicorn running on" in texto:
            arrancado = True
            break
        time.sleep(1)
    if not arrancado:
        print("  no arranco en 300 s (los modelos se cargan la primera vez)", file=sys.stderr)
        proc.terminate()
        return 2
    print("  arranque confirmado por SU PROPIO log")
    codigo = comprobar_capacidades(a.puerto, lanzado_en)
    if codigo != 0:
        proc.terminate()
        return codigo
    print("\nCtrl+C para parar. La base sigue siendo la del contenedor: `docker compose down` NO "
          "la borra; `down -v` si.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
