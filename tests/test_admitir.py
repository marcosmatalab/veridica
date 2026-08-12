"""Tests de la puerta de admision (arreglo del 1.4 tras el muestreo a mano de Marcos).

De 20 fragmentos leidos por una persona salieron 6 que no eran material docente. El detector de
firmas que habia cazaba 2 de esos 6. Estos tests anclan las dos direcciones:

  CAZA lo que no es temario  ..... los 6, con el texto real que los delata;
  NO CAZA lo que si lo es    ..... y estos controles negativos NO son inventados: son documentos
                                   que la primera version de la puerta se llevo por delante, que
                                   es como se descubrio que buscaba las palabras equivocadas.

El control negativo importa mas que el positivo. Una puerta ajustada a los seis casos conocidos
siempre da verde sobre los seis casos conocidos; lo que hay que saber es a quien mas se lleva.
"""
import json
import re
from pathlib import Path

import admitir
import pytest

RAIZ = Path(__file__).resolve().parents[1]
FRAGMENTOS = RAIZ / "corpus" / "fragmentos.jsonl"
sin_corpus = pytest.mark.skipif(not FRAGMENTOS.exists(),
                                reason="necesita el corpus local (ADR 0001)")


def fr(texto, tipo="explicacion", orden=1):
    return {"texto": texto, "tipo_contenido": tipo, "orden": orden}


# --- direccion 1: lo que tiene que cazar ------------------------------------------------------

SALIDA_APT = """19 not upgraded. Need to get 10.0 MB of archives.
After this operation, 66.7 MB of additional disk space will be used.
Get:1 http://deb.debian.org/debian buster/main amd64 perl-modules-5.28 all 5.28.1-6 [2,873 kB]
Get:2 http://deb.debian.org/debian buster/main amd64 libgdbm6 amd64 1.18.1-4 [64.7 kB]
Get:3 http://deb.debian.org/debian buster/main amd64 libperl5.28 amd64 5.28.1-6 [3,894 kB]
Setting up perl-modules-5.28 (5.28.1-6) ...
Unpacking libgdbm6:amd64 (1.18.1-4) ..."""

CUERPO_DKIM = """bh=Q+8oe7O3kSgMBbJdBaqa+zeQT8hLFSMFPgazn3jdb5U=;
b=g7nzY3uwxc5h6SS2FDPvUsleL6fPqJ+vZ9STRRa6bIzNgCiSTQNgsxtzBICEn7Qnuv
xVJeUnscR/R6CLfOAZoPwkz85RhNQCqIKfda8jWciM2VC9CEeKEtdA/QcSItuMDDK7V5
Zb1+WWPcd1bNGs8R68P68cT/ln4qYtloPDMpdnjiAKke6Jyp/SjiOx1iJTAbsq6IE5cm"""

DICCIONARIO = ("huesudo huetar hueteño hueva huevada huevar huevazos huevear huevera huevería "
               "huevero huévil huevo huevonada huevonear huevón hugonote huichó huiclacoche huida "
               "huidero huidizo huido huidor huifa huilense huillín huilo huilota huilte huimos "
               "huincha huingán huinche huipil huiro huiscoyol huisquil huisquilar huitrín")

INDICE_DE_ENLACES = """# De Kotlin a C#: Un Tutorial Detallado

- [De Kotlin a C#](#de-kotlin-a-c-un-tutorial-detallado)
    - [Kotlin](#kotlin)
    - [C#](#c)
    - [Notas](#notas)
- [Manejo de Tipos Nulos](#manejo-de-tipos-nulos)
- [Clases y Objetos](#clases-y-objetos)
- [Colecciones](#colecciones)"""


def test_caza_la_salida_de_un_gestor_de_paquetes():
    assert admitir.juzgar_fragmento(fr(SALIDA_APT)) == "salida de gestor de paquetes"


def test_caza_el_cuerpo_de_una_firma_dkim():
    """Se le escapaba: la palabra "DKIM-Signature" vivia en OTRO fragmento, y este solo tiene el
    base64. Buscar la palabra en vez de lo que delata al bloque era el error."""
    assert admitir.juzgar_fragmento(fr(CUERPO_DKIM)) is not None


def test_caza_una_lista_de_palabras():
    """Tampoco lo cazaba: las palabras van separadas por espacios, no una por linea."""
    assert admitir.juzgar_fragmento(fr(DICCIONARIO)) == \
        "ni puntuacion ni una frase entera: lista, tabla o volcado, no prosa"


def test_caza_un_indice_que_solo_son_enlaces():
    assert admitir.juzgar_fragmento(fr(INDICE_DE_ENLACES)) == \
        "indice de enlaces sin contenido propio"


def test_caza_por_documento_lo_que_ninguna_firma_puede_ver():
    """Los dos que solo se pueden juzgar como documento: la guia de formato para subir tareas al
    Moodle y el trabajo de alumno sobre Polonia. Este ultimo esta escrito como prosa normal y no
    tiene ninguna señal tecnica: por eso va a la lista manual y no a una regla automatica, que
    seria cara y se llevaria por delante los enunciados de ejercicio, que si valen."""
    guia = "corpus/asir/apuntes/aberlanas-iso/GuiaDeEstilo_ISO.md"
    polonia = ("corpus/derivado/asir/apuntes/lora-1asir/Redes/Ejercicios/polonia/Polonia.docx.md")
    assert admitir.juzgar_documento(guia, [fr("Todas las tareas deben tener este formato.")])
    assert "trabajo de alumno" in admitir.juzgar_documento(polonia, [fr("Polonia es un pais.")])


def test_un_arbol_entero_se_excluye_con_una_sola_entrada():
    assert admitir.excluido_a_mano(
        "corpus/dam/apuntes/temario-dam-comesana/SENDACYL/sendacyl-api/app/cache/index.html")
    assert admitir.excluido_a_mano("corpus/dam/apuntes/temario-dam-comesana/DI/interfaces.md") is None


# --- direccion 2: a quien NO puede llevarse ---------------------------------------------------

TEORIA_DPKG = """## dpkg

*dpkg* es el programa base para manejar paquetes Debian en el sistema.
Si tiene paquetes .deb, dpkg es lo que permite instalar o analizar sus contenidos.
Pero este programa solo tiene una vision parcial del universo Debian: sabe lo que esta
instalado en el sistema y lo que se le provee en la linea de ordenes, pero no sabe nada mas.
Fallara si no se satisface una dependencia. Por el contrario, herramientas como apt crearan
una lista de dependencias para instalar todo tan automaticamente como sea posible."""

GUIA_CON_CAPTURAS = """### Nombre y tipo ###

![Creacion de la MV 1](https://raw.githubusercontent.com/aberlanas/ImplantacionSistemasOperativos/master/Unidad_01/InstalacionUbuntuServer/UbuntuServer_1.PNG)

Establecemos el nombre y la *arquitectura* de la maquina virtual: ubuntuServer, LinuX,
Ubuntu de 64 bits. La memoria RAM se deja en 768 MB porque los ordenadores del aula no
permiten mucho mas.

![Creacion de la MV 2](https://raw.githubusercontent.com/aberlanas/ImplantacionSistemasOperativos/master/Unidad_01/InstalacionUbuntuServer/UbuntuServer_2.PNG)"""

PRACTICA_CON_SALIDA = """En primer lugar vamos a instalar el servidor de correos postfix en
nuestra maquina de OVH. El paquete se encarga de la entrega y del reenvio de los mensajes.

```
debian@pandora:~$ sudo apt-get install postfix
```

Durante la instalacion nos preguntara el tipo de configuracion: elegimos "Sitio de Internet",
que es la que corresponde a un servidor con dominio propio."""


def test_no_se_lleva_un_documento_de_teoria_que_habla_de_apt():
    """El fallo real de la primera version: buscaba "apt-get" y "dpkg " y con eso tiro un
    documento de teoria titulado Teoria_03_LinuX_dpkg.md. En ASIR los comandos SON la materia."""
    assert admitir.juzgar_fragmento(fr(TEORIA_DPKG)) is None


def test_no_se_lleva_una_guia_ilustrada_con_capturas():
    """Otro fallo real: las URL de las capturas contaban como volcado de cadenas largas y se
    llevaron los 11 fragmentos de la guia de instalacion de Ubuntu Server."""
    assert admitir.juzgar_fragmento(fr(GUIA_CON_CAPTURAS)) is None


def test_no_se_lleva_una_explicacion_con_dos_lineas_de_consola():
    assert admitir.juzgar_fragmento(fr(PRACTICA_CON_SALIDA)) is None


def test_el_codigo_no_se_juzga_con_reglas_de_prosa():
    """Un .java no tiene puntos ni comas y caeria por todas las reglas. Y el codigo de
    Programacion es material de primera, ademas de la fuente del verificador de ejecucion."""
    java = "public class Punto {\n    private int x;\n    public int getX() { return x; }\n}"
    assert admitir.juzgar_fragmento(fr(java, tipo="codigo")) is None


def test_una_definicion_normal_entra():
    texto = ("La clave ajena es una columna que referencia a la clave primaria de otra tabla. "
             "Sirve para mantener la integridad referencial entre las dos tablas del modelo.")
    assert admitir.juzgar_fragmento(fr(texto, tipo="definicion")) is None


def test_las_marcas_horarias_no_son_prosa_por_llevar_dos_puntos():
    """Los dos puntos contaban como fin de frase, asi que un fichero de tarifas ("08:48:45
    10:30:54 ...") salia con dos puntuaciones por palabra: la prosa mas puntuada del corpus."""
    horas = " ".join("0%d:4%d:1%d" % (i % 10, i % 10, i % 10) for i in range(60))
    assert admitir.juzgar_fragmento(fr(horas)) == \
        "ni puntuacion ni una frase entera: lista, tabla o volcado, no prosa"


# --- anclado al corpus real -------------------------------------------------------------------

@sin_corpus
def test_lo_excluido_a_mano_no_esta_en_el_indice():
    documentos = {json.loads(x)["documento"]
                  for x in FRAGMENTOS.read_text(encoding="utf-8").split("\n") if x.strip()}
    for ruta in admitir.EXCLUIDOS_A_MANO:
        if ruta.endswith("/"):
            assert not [d for d in documentos if d.startswith(ruta)], ruta
        else:
            assert ruta not in documentos, ruta


@sin_corpus
def test_la_puerta_ya_esta_aplicada_en_el_indice():
    """Si la puerta se aplica al trocear, volver a pasarla sobre el indice no puede encontrar
    nada. Es la comprobacion de que el fichero que se embebe es el filtrado y no el de antes."""
    fragmentos = [json.loads(x)
                  for x in FRAGMENTOS.read_text(encoding="utf-8").split("\n") if x.strip()]
    rechazados = [f["documento"] for f in fragmentos if admitir.juzgar_fragmento(f)]
    assert not rechazados[:5], f"{len(rechazados)} fragmentos rechazables siguen en el indice"


INDICE_DE_PDF = """ÍndiCe
Símbolos
__call__ 105
__cmp__ 51
__del__ 51
__doc__ 75, 125
__init__ 43
herencia 45
herencia múltiple 46
hilos 102
lambda 60
lenguaje compilado 7
listas, métodos 55"""


def test_caza_el_indice_de_un_pdf_que_no_tiene_enlaces():
    """La regla del indice de markdown miraba la forma del ENLACE, y en un PDF derivado no hay
    enlaces: hay "termino + numero de pagina". Misma basura, otra superficie."""
    assert admitir.juzgar_fragmento(fr(INDICE_DE_PDF)) == \
        "indice alfabetico o de contenidos, no prosa"


def test_una_lista_numerada_de_contenido_no_es_un_indice():
    """El control negativo: una enumeracion con numeros al final de linea que SI dice algo."""
    texto = ("El sistema de ficheros organiza los datos en bloques.\n"
             "Cada bloque tiene un tamaño fijo de 4096\n"
             "El inodo guarda los metadatos del fichero y ocupa 256\n"
             "La tabla de particiones cabe en el primer sector, que son 512\n"
             "Un disco moderno declara sectores logicos de 512\n"
             "y sectores fisicos de 4096\n"
             "El arranque lee el MBR, que son los primeros 446\n"
             "y despues salta al gestor de arranque instalado en la particion 1\n"
             "El resultado es un sistema que arranca en menos de 30\n")
    assert admitir.juzgar_fragmento(fr(texto)) is None


# --- la trampa del separador (deuda declarada en el 3.0) --------------------------------------
#
# Los patrones de DOCUMENTOS_FUERA se aplican a la RUTA y separan sus palabras con \s, que casa
# con el espacio y no con el guion, el guion bajo ni el punto. Un fichero llamado
# "guia-de-estilo.md" -la forma mas normal de nombrarlo en un repo- se cuela entero.
#
# Encontrado al escribir el 3.0, y barrido despues en vez de darlo por unico: son CUATRO
# sub-patrones, no uno. Hoy no afecta a ningun documento del indice, y por eso no se arregla desde
# el 3.0 (tocar la puerta obliga a re-verificar la ingesta). Pero un cero escrito en un informe se
# olvida y un cero anclado es una puerta: esto se pone rojo solo el dia que entre el primero.

def con_separadores_reales(patron: str) -> str:
    """El mismo patron admitiendo los separadores que de verdad llevan los nombres de fichero."""
    return patron.replace(r"\s*", r"[\s\-_.]*").replace(r"\s+", r"[\s\-_.]+")


def test_el_barrido_del_hueco_cuenta_lo_mismo_que_conto_el_3_0():
    """Que el numero de la deuda no se pierda: si alguien anade otro patron con \\s a la lista,
    este test lo cuenta y obliga a mirarlo. No lo prohibe: lo hace visible.

    Y las dos magnitudes van por separado, que es regla de la casa y aqui no es ceremonia: al
    escribir este test se conto 7 donde el barrido habia dicho 4, porque 7 son las ocurrencias de
    \\s y 4 los sub-patrones que las llevan. Un solo numero habria escondido cual de los dos era."""
    subpatrones, ocurrencias = 0, 0
    for patron, _ in admitir.DOCUMENTOS_FUERA:
        for alternativa in patron.pattern.split("|"):
            if "\\s" in alternativa:
                subpatrones += 1
                ocurrencias += alternativa.count("\\s")
    reglas = sum(1 for p, _ in admitir.DOCUMENTOS_FUERA if "\\s" in p.pattern)
    assert (subpatrones, ocurrencias, reglas) == (4, 7, 2), (
        f"el barrido del 3.0 conto 4 sub-patrones con el hueco del separador, 7 ocurrencias de "
        f"\\s en ellos y 2 reglas afectadas de {len(admitir.DOCUMENTOS_FUERA)}; ahora sale "
        f"{(subpatrones, ocurrencias, reglas)}. Si ha crecido, la deuda ya no es la que se aparco.")


@sin_corpus
def test_ningun_documento_del_indice_se_cuela_por_el_hueco_del_separador():
    """LA TRAMPA. Hoy pasa en verde con cero y no cuesta nada. El dia que alguien meta un
    'guia-de-estilo.md' o un 'normas_de_entrega.md', esto se pone rojo sin que nadie se acuerde
    de la deuda, que es la unica forma de que una deuda no se olvide."""
    documentos = {json.loads(x)["documento"]
                  for x in FRAGMENTOS.read_text(encoding="utf-8").split("\n") if x.strip()}
    colados = []
    for patron, motivo in admitir.DOCUMENTOS_FUERA:
        laxo = re.compile(con_separadores_reales(patron.pattern), re.I)
        colados += [(d, motivo) for d in documentos if laxo.search(d) and not patron.search(d)]
    assert colados == [], (
        f"{len(colados)} documentos entran al indice y no deberian: el patron los dejo pasar solo "
        f"porque su nombre usa guion, guion bajo o punto donde el patron espera un espacio. "
        f"Arreglar admitir.py y re-verificar la ingesta. {colados}")
