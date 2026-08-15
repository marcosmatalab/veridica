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
import re
import shutil
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
#: Las capacidades que el montaje del lunes tiene que tener ARRIBA, y son tres desde el 15/08/2026.
#:
#: `embebedor` y `nli` son las que la sesión **enseña**: sin ellas no es que el sistema vaya peor,
#: es que la mitad de lo que se dice en voz alta no está ocurriendo en pantalla.
#:
#: **`proveedor` se añadió después de que su ausencia atravesara esta puerta entera.** El montaje
#: arrancó con el intérprete correcto, torch, CUDA, embebedor ok, nli ok, token puesto y túnel
#: abierto — y devolvía 503 a la primera pregunta, porque uvicorn se lanzó sin las variables del
#: proveedor. La guarda miraba lo que la sesión ENSEÑA y se saltaba lo que la sesión NECESITA.
CAPACIDADES = ("proveedor", "embebedor", "nli")


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
    print(f"\n  LISTO: {' y '.join(CAPACIDADES)} arriba.")

    # LA PUERTA DEL TOKEN, Y VIVE AQUI POR UN MOTIVO PRECISO: este es el UNICO sitio del proyecto
    # donde se sabe con certeza que lo siguiente que va a pasar es PUBLICAR ESTO EN INTERNET. Un
    # aviso en un documento sobre "acuerdate de poner el token antes de abrir el tunel" es prosa que
    # alguien tiene que acordarse de leer, y de esas van dos de dos en este repo. Asi que no se
    # avisa: no se da el comando.
    #
    # Y NO SE PARA EL SERVICIO. Servir en local sin token es legitimo -es la demo de siempre-; lo
    # que no es legitimo es publicarlo. Se separa lo que esta mal de lo que no.
    if not (s.get("autenticacion") or "").startswith("con token"):
        print("\n  NO TE DOY EL COMANDO DEL TUNEL: esta instancia esta ABIERTA.", file=sys.stderr)
        print("  El tunel la publica en internet y /consulta gasta saldo del proveedor, asi que\n"
              "  cualquiera que de con la URL -y los bots dan- gasta tu clave, lee las trazas de\n"
              "  otros y se pasea por el corpus. Para local no hace falta; para el tunel, si.\n",
              file=sys.stderr)
        print("  Ponle un token y vuelve a arrancar:\n", file=sys.stderr)
        print('      export VERIDICA_TOKEN="$(python -c "import secrets;'
              'print(secrets.token_urlsafe(24))")"', file=sys.stderr)
        print(f"      python scripts/servir_anfitrion.py --puerto {puerto}\n", file=sys.stderr)
        return 1

    print(f"  El tunel puede apuntar al {puerto}, y la puerta del token esta puesta.")
    return 0


def cloudflared() -> str | None:
    """Donde esta cloudflared, mirando tambien fuera del PATH.

    En esta maquina esta instalado en Program Files y NO en el PATH de la shell, o sea que
    `which cloudflared` dice que no y el ejecutable esta ahi: exactamente la clase de "no existe"
    que hay que comprobar antes de creersela.
    """
    if ruta := shutil.which("cloudflared"):
        return ruta
    for candidata in (r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
                      r"C:\Program Files\cloudflared\cloudflared.exe"):
        if os.path.isfile(candidata):
            return candidata
    return None


def abrir_tunel(puerto: int, token: str) -> int:
    """ABRE EL TUNEL Y ESCUPE EL ENLACE TERMINADO. No el comando: el ENLACE.

    **Por que esto no es comodidad.** Hasta hoy este script imprimia el comando de cloudflared y una
    plantilla con `<lo-que-diga-cloudflared>` dentro, o sea que quedaban DOS pasos a mano el lunes
    por la manana: correr el comando, y pegar su dominio dentro de una URL con `?t=` detras. El
    segundo es justo el que se olvida — y olvidarlo no da un error, **da un 401 en la cara del
    alumno en la primera pantalla**, que es la peor forma de fallar que tiene una demo.

    Es la misma regla que ya trajo `fusionar.py` y que trajo el comando del tunel: si un paso puede
    olvidarse, se convierte en salida del paso anterior. Aqui el paso que faltaba era el ULTIMO.
    """
    binario = cloudflared()
    if binario is None:
        print("  cloudflared no esta instalado. Instalalo o abre el tunel a mano:\n"
              f"      cloudflared tunnel --url http://127.0.0.1:{puerto}\n"
              f"  Y REPARTE la URL que te de CON ?t={token} detras.", file=sys.stderr)
        return 2
    print(f"\nabriendo el tunel con {binario} ...")
    proc = subprocess.Popen([binario, "tunnel", "--url", f"http://127.0.0.1:{puerto}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    dominio, t0 = None, time.time()
    for linea in proc.stdout:
        if m := re.search(r"https://[\w-]+\.trycloudflare\.com", linea):
            dominio = m.group(0)
            break
        if time.time() - t0 > 60:
            break
    if not dominio:
        print("  cloudflared no dio una URL en 60 s", file=sys.stderr)
        proc.terminate()
        return 2
    enlace = f"{dominio}/?t={token}"
    print("\n" + "=" * 78)
    print("  ESTE ES EL ENLACE QUE SE REPARTE. Copialo entero, con el ?t= del final:")
    print(f"\n      {enlace}\n")
    print("  Abrirlo es TODO lo que hay que hacer: la pagina se queda el token en la pestana y lo")
    print("  borra de la barra de direcciones, asi que no sale en capturas ni en el historial.")
    print("  Sin el ?t=, esa misma URL da 401 -que es de lo que se trata-.")
    print("=" * 78 + "\n")
    print("Ctrl+C para cerrar el tunel.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--puerto", type=int, default=PUERTO_DEMO)
    p.add_argument("--solo-comprobar", action="store_true",
                   help="no arranca nada: comprueba un proceso que ya este sirviendo")
    p.add_argument("--tunel", action="store_true",
                   help="abre el tunel con cloudflared y escupe el ENLACE COMPLETO con su ?t=")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if a.solo_comprobar:
        codigo = comprobar_capacidades(a.puerto)
        if codigo == 0 and a.tunel:
            return abrir_tunel(a.puerto, os.environ.get("VERIDICA_TOKEN", ""))
        return codigo

    if comprobar_interprete() != 0:
        return 2

    # EL `.env`, QUE AQUÍ NO LO LEE NADIE MÁS, Y ESTA LÍNEA ES LA QUE SALVA LA SESIÓN (15/08/2026).
    #
    # La API recibe su entorno de `compose.yml`; el montaje del anfitrión lanza uvicorn a mano desde
    # una shell, así que **nadie pone las variables del proveedor**. `cargar_dotenv` existía desde el
    # 2.2 para exactamente esto y esta ruta no la llamaba: capacidad construida, correcta y no
    # enchufada, que es la familia del NLI del 4.3.
    #
    # Y LA FORMA EN QUE SE DESTAPÓ ES LA LECCIÓN: el montaje pasó su puerta ENTERA —intérprete de
    # miniconda, torch, CUDA, embebedor ok, nli ok, token puesto, túnel abierto— y **no podía
    # contestar ni una pregunta**. La guarda comprobaba las dos capacidades que la sesión ENSEÑA y
    # se saltaba la que las PRODUCE. Se vio haciendo una consulta de verdad por el túnel, no
    # leyendo código. Desde hoy `proveedor` es una sonda esencial de `/salud` y esta puerta la mira.
    sys.path.insert(0, RAIZ)
    from app.core.entorno import cargar_dotenv
    puestas = cargar_dotenv(os.path.join(RAIZ, ".env"))
    print(f"  .env: {puestas} variables cargadas (las que ya estaban en el entorno mandan)")

    lanzado_en = time.time()
    entorno = {**os.environ, "DATABASE_URL": os.environ.get("DATABASE_URL", BASE_POR_DEFECTO)}
    registro = os.path.join(RAIZ, f"uvicorn-{a.puerto}.log")
    print(f"arrancando uvicorn en el {a.puerto}; su log en {registro}")
    with open(registro, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.api.main:app",
             "--host", "127.0.0.1", "--port", str(a.puerto)],
            cwd=RAIZ, env=entorno, stdout=log, stderr=subprocess.STDOUT)

    # NADA DE LO DE ABAJO PUEDE DEJAR EL UVICORN SUELTO, y esto se escribe porque acaba de pasar:
    # el 15/08/2026 la lectura del log murio con UnicodeDecodeError, la excepcion se llevo el script
    # por delante y el uvicorn se quedo VIVO ocupando el 8010. El siguiente arranque murio con
    # "[Errno 10048] bind" -su propia guarda funcionando- y hubo que ir a matar el proceso a mano.
    # O sea: un fallo del supervisor fabricaba exactamente el residuo que este script existe para
    # que no exista. `finally` y no `except` a proposito: da igual por que se salga.
    try:
        return _esperar_y_servir(proc, registro, a.puerto, lanzado_en)
    except BaseException:
        proc.terminate()
        raise


def _esperar_y_servir(proc, registro: str, puerto: int, lanzado_en: float) -> int:
    # SE ESPERA LEYENDO EL LOG DEL PROCESO PROPIO, no preguntando al puerto: un residuo ajeno
    # contestaria igual y todas las medidas las serviria codigo que no es este.
    arrancado, t0 = False, time.time()
    while time.time() - t0 < 300:
        if proc.poll() is not None:
            print(f"el proceso murio (codigo {proc.returncode}). Sus ultimas lineas:",
                  file=sys.stderr)
            with open(registro, encoding="utf-8", errors="replace") as f:
                print("".join(f.readlines()[-15:]), file=sys.stderr)
            return 2
        # `errors="replace"` Y NO ES DEJADEZ: uvicorn escribe su log en la CODIFICACION DE LA
        # CONSOLA (cp1252 en este Windows), no en UTF-8, asi que la primera linea con una tilde
        # -"conexion", "parametro"- reventaba esta lectura con UnicodeDecodeError y se llevaba por
        # delante el arranque entero. Cazado el 15/08/2026 corriendo el script de verdad, que es la
        # unica forma: leyendo el codigo no se ve, porque el fallo depende de lo que el servidor
        # decida imprimir ese dia. Aqui solo se buscan marcadores ASCII -"Uvicorn running on",
        # "ERROR", "bind"-, asi que perder un acento no cuesta nada y morirse cuesta la sesion.
        with open(registro, encoding="utf-8", errors="replace") as f:
            texto = f.read()
        if "ERROR" in texto and "bind" in texto:
            print(f"  el puerto {puerto} ya esta ocupado: ELIGE OTRO. Un residuo contestaria "
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
    codigo = comprobar_capacidades(puerto, lanzado_en)
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
