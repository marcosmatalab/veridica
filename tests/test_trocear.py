"""Tests del troceador (encargo 1.4).

Los anclados son los tres que salieron de decisiones, no de gusto:
  - los 512 tokens se cuentan con el tokenizador REAL y INCLUYEN la linea de contexto;
  - el codigo no se parte por ventana ciega: un fichero es un fragmento si cabe, y si no, se corta
    por clase o por metodo;
  - los volcados de secretos no entran (en el corpus real hay una clave privada RSA en unos
    apuntes de ASIR).
"""
import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "trocear.py"


def cargar():
    spec = importlib.util.spec_from_file_location("trocear", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


tr = cargar()


@pytest.fixture(scope="module")
def tok():
    return tr.cargar_tokenizador()


# --- la unidad sale de la carpeta, no del BOE (ADR 0005) --------------------------------------

def test_la_unidad_sale_de_la_carpeta_del_material():
    partes = tr.ruta_a_partes(
        "corpus/derivado/daw/curso1/programacion/lionel-ict/Unidad 4 Introducción a Java/x.pdf.md")
    assert partes["titulacion"] == "daw"
    assert partes["curso"] == 1
    assert partes["asignatura"] == "programacion"
    assert partes["unidad"] == "Unidad 4 Introducción a Java"   # la del profesor, no la del BOE


def test_un_documento_sin_carpeta_de_unidad_no_se_inventa_una():
    partes = tr.ruta_a_partes("corpus/derivado/dam/apuntes/temario/tema.pdf.md")
    assert partes["unidad"] in (None, "temario")
    assert partes["titulacion"] == "dam"


# --- presupuesto de tokens ---------------------------------------------------------------------

def test_ningun_fragmento_de_prosa_pasa_de_512_contando_el_contexto(tok):
    texto = "\n\n".join(f"Parrafo numero {i} con contenido docente suficiente para llenar el "
                        f"presupuesto de tokens del fragmento y obligar a cortar." * 3
                        for i in range(40))
    contexto = "DAW · curso 1 · programacion · Unidad 4 · documento de prueba"
    presupuesto = tr.TOKENS - tr.contar(tok, contexto) - 2
    trozos, _ = tr.trocear_prosa(tok, texto, presupuesto)
    assert trozos
    for t in trozos:
        assert tr.contar(tok, contexto + "\n\n" + t) <= tr.TOKENS


def test_un_parrafo_sin_puntuacion_se_parte_igual(tok):
    """Las tablas de atajos de NetBeans del corpus son 1.011 tokens sin un solo punto."""
    texto = " ".join(f"atajo{i} combinacion{i}" for i in range(600))
    trozos, _ = tr.trocear_prosa(tok, texto, 200)
    assert len(trozos) > 1
    assert all(tr.contar(tok, t) <= 200 for t in trozos)


# --- codigo -------------------------------------------------------------------------------------

CLASE_JAVA = """package ejemplo;

public class Calculadora {
    public int sumar(int a, int b) {
        return a + b;
    }

    public int restar(int a, int b) {
        return a - b;
    }
}
"""


def test_un_fichero_de_codigo_que_cabe_es_UN_fragmento(tok):
    trozos, aviso = tr.trocear_codigo(tok, CLASE_JAVA, 480)
    assert trozos == [CLASE_JAVA] and aviso is None


def test_el_codigo_grande_se_corta_por_metodo_no_por_ventana(tok):
    cuerpo = "\n".join(f"        System.out.println(\"linea {i}\");" for i in range(60))
    fichero = ("public class Grande {\n"
               f"    public void primero() {{\n{cuerpo}\n    }}\n\n"
               f"    public void segundo() {{\n{cuerpo}\n    }}\n}}\n")
    trozos, _ = tr.trocear_codigo(tok, fichero, 480)
    assert len(trozos) > 1
    # cada trozo empieza donde empieza una clase o un metodo, no a media linea
    for t in trozos[1:]:
        assert t.lstrip().startswith(("public", "private", "protected", "class", "@")), t[:60]


def test_si_no_hay_donde_cortar_se_avisa_y_no_se_destroza(tok):
    """Mejor un fragmento grande que uno roto: uno roto no compila ni se entiende."""
    fichero = "\n".join(f"int variable{i} = {i};" for i in range(400))
    trozos, aviso = tr.trocear_codigo(tok, fichero, 200)
    assert trozos == [fichero]
    assert aviso and "clase" in aviso


# --- secretos -------------------------------------------------------------------------------

def test_una_clave_privada_no_entra_al_corpus(tok):
    """Encontrado en el corpus real: apuntes de ASIR con certificados de Kubernetes y una clave
    privada RSA volcados en base64. Un sistema que cita fragmentos al alumno no puede tener eso."""
    clave = "-----BEGIN RSA PRIVATE KEY-----\n" + "MIIEowIBAAKCAQEAwL3NvRaIPz2s" * 20
    texto = f"Contenido docente normal del tema.\n\n{clave}\n\nMas contenido docente."
    trozos, tirados = tr.trocear_prosa(tok, texto, 480)
    assert tirados == 1
    assert all("PRIVATE KEY" not in t for t in trozos)
    assert any("Contenido docente normal" in t for t in trozos)


def test_el_texto_normal_no_se_confunde_con_un_secreto():
    assert not tr.parece_secreto_o_volcado(
        "Una clave primaria identifica de forma unica cada fila de una tabla relacional. " * 5)


# --- asignatura: la particion, que no puede decir "apuntes" ------------------------------------

def test_la_asignatura_de_asir_no_es_la_carpeta_apuntes():
    """Leyendo la ruta a ciegas, 3.495 fragmentos (el 27% del indice) salian con asignatura
    "apuntes", que es el nombre del cajon donde estan los repositorios, no un modulo. Y la
    asignatura es la particion del filtro y la del detector de colados."""
    partes = tr.ruta_a_partes("corpus/derivado/asir/apuntes/lora-1asir/SO/Examen/Procesos.docx.md")
    assert partes["asignatura"] == "implantacion-de-sistemas-operativos"
    assert partes["asignatura_origen"] == "sigla del material, tabla declarada"


def test_dos_repositorios_distintos_del_mismo_modulo_caen_en_la_misma_asignatura():
    """Es lo que hace comparables sus contenidos en el 1.8: dos fuentes del mismo modulo."""
    a = tr.ruta_a_partes("corpus/derivado/asir/apuntes/lora-1asir/SO/x.md")["asignatura"]
    b = tr.ruta_a_partes("corpus/derivado/asir/apuntes/aberlanas-iso/UD02_Virtualizacion/y.md")
    assert a == b["asignatura"] == "implantacion-de-sistemas-operativos"
    assert b["unidad"] == "UD02_Virtualizacion"


def test_una_sigla_sin_equivalencia_declarada_se_queda_como_esta():
    """HLC no es un modulo del RD 1629/2009. No se traduce a ojo: se declara que no consta."""
    partes = tr.ruta_a_partes("corpus/asir/apuntes/lora-2asir/HLC/practicaZFS.md")
    assert partes["asignatura"] == "hlc"
    assert "SIN equivalencia declarada" in partes["asignatura_origen"]


def test_los_ficheros_sueltos_de_un_repositorio_no_reciben_asignatura_inventada():
    partes = tr.ruta_a_partes("corpus/asir/apuntes/lora-2asir/Openstack.md")
    assert partes["asignatura"] == ""
    assert partes["asignatura_origen"].startswith("no declarada")


# --- unidad: el primer directorio con significado -----------------------------------------------

def test_la_unidad_no_es_el_nombre_de_quien_escribio_los_apuntes():
    """"comesana" era la unidad de 3.370 fragmentos. Vacio es mejor que ruido, porque la unidad
    viaja en la linea de contexto y la linea de contexto se embebe."""
    partes = tr.ruta_a_partes(
        "corpus/derivado/daw/curso2/desarrollo-web-entorno-servidor-antiguo/comesana-dwes/x.pdf.md")
    assert partes["unidad"] is None


def test_entre_dos_carpetas_gana_la_de_arriba_si_dice_algo():
    partes = tr.ruta_a_partes(
        "corpus/derivado/dam/apuntes/temario-dam-comesana/SGE/Unidad 3 SGE/Actividades.docx.md")
    assert partes["unidad"] == "Unidad 3 SGE"


def test_una_carpeta_que_solo_dice_el_formato_no_es_unidad():
    for generica in ("java", "Manuales", "Guias", "src", "Ejercicios", "apuntes"):
        assert not tr.carpeta_significativa(generica), generica
    for buena in ("UD05_UsuariosGruposYPermisos", "Unidad 4 Introducción a Java",
                  "Practica_Navideña", "Tema 3"):
        assert tr.carpeta_significativa(buena), buena


# --- tipo de contenido --------------------------------------------------------------------------

def test_el_tipo_de_contenido_sale_por_reglas():
    assert tr.tipo_de_contenido("class Foo {}", True) == "codigo"
    assert tr.tipo_de_contenido("Real Decreto 686/2010, anexo I", False) == "normativa"
    assert tr.tipo_de_contenido("Ejemplo 3: el caso resuelto paso a paso", False) == "ejemplo_resuelto"


DEFINICION = ("La clave ajena es una columna, o un conjunto de columnas, que referencia a la clave "
              "primaria de otra tabla y obliga a que su valor exista alli. Sirve para mantener la "
              "integridad referencial entre las dos tablas relacionadas del modelo.")


def test_una_definicion_de_verdad_se_marca_como_definicion():
    assert tr.tipo_de_contenido(DEFINICION, False) == "definicion"


def test_lo_que_no_es_definicion_no_se_marca_como_definicion():
    """Los cuatro casos salieron del muestreo a mano de Marcos: de 12 fragmentos marcados
    `definicion`, 9 eran esto. Y del `definicion` sale el glosario del 1.6, asi que un
    catch-all aqui envenena el glosario entero."""
    pasos = ("1. Instala el paquete con apt-get install jboss. 2. Edita el fichero de "
             "configuracion standalone.xml. 3. Arranca el servicio con systemctl start jboss. "
             "El servidor es un proceso que queda escuchando en el puerto 8080 de la maquina.")
    pregunta = ("Pregunta 3. ¿Cual de las siguientes afirmaciones es una definicion correcta de "
                "clave ajena? ¿Y de clave primaria? Razona la respuesta en el examen del tema.")
    codigo = ("public class Persona { private String nombre; public String getNombre() { "
              "return nombre; } public void setNombre(String n) { this.nombre = n; } }")
    corto = "El bucle es una estructura repetitiva."
    assert tr.tipo_de_contenido(pasos, False) == "procedimiento"
    assert tr.tipo_de_contenido(pregunta, False) != "definicion"
    assert tr.tipo_de_contenido(codigo, False) == "codigo"
    assert tr.tipo_de_contenido(corto, False) != "definicion"


def test_el_codigo_dentro_de_un_markdown_se_marca_como_codigo():
    """Fragmento 7 del muestreo: Java y Spring dentro de un .md salian como `explicacion`."""
    texto = ("Vamos a ver el controlador de ejemplo.\n\n```java\n"
             "@RestController\npublic class UsuarioController {\n"
             "    @GetMapping(\"/usuarios\")\n    public List<Usuario> todos() {\n"
             "        return servicio.buscarTodos();\n    }\n}\n```\n")
    assert tr.tipo_de_contenido(texto, False) == "codigo"


def test_tres_puntos_numerados_no_convierten_una_lista_en_procedimiento():
    """El control negativo del procedimiento: una lista de ventajas tambien va numerada. Lo que
    distingue al procedimiento es que MANDA hacer algo."""
    ventajas = ("Las ventajas de la herencia son tres. 1. Reutilizacion del codigo comun. "
                "2. Extension del comportamiento. 3. Polimorfismo entre las clases derivadas.")
    assert tr.tipo_de_contenido(ventajas, False) != "procedimiento"


def test_el_titulo_no_puede_ser_un_comando_de_shell():
    """329 fragmentos se embebian con el contexto acabado en "/etc/init.d/nscd restart". En un
    markdown de verdad el encabezado vale, pero si lo que dice es un comando no es un titulo."""
    texto = ("# apt-get install eclipse\n\nInstalamos el entorno de desarrollo.\n\n"
             "# Despliegue de aplicaciones web\n\nContenido del tema.")
    assert tr.titulo_de("corpus/x/despliegue.md", texto) == "Despliegue de aplicaciones web"
    assert tr.titulo_de("corpus/x/DAW05.pdf.md", "# /etc/init.d/nscd restart\n\ntexto") == "DAW05"


def test_la_linea_de_contexto_lleva_el_camino_del_alumno():
    partes = {"titulacion": "daw", "curso": 1, "asignatura": "programacion",
              "unidad": "Unidad 4 Introducción a Java"}
    linea = tr.linea_de_contexto("x", partes, "ud4_Introduccion_a_Java")
    assert linea == ("DAW · curso 1 · programacion · Unidad 4 Introducción a Java · "
                     "ud4_Introduccion_a_Java")


# --- el titulo de la linea de contexto ---------------------------------------------------------

def test_en_un_pdf_derivado_una_almohadilla_no_es_un_encabezado():
    """Del segundo muestreo: titulos como "esto es una cadena", "fdisk /dev/sdb" o
    "-*- coding: utf-8 -*-". En un .pdf.md no hay encabezados; lo que empieza por almohadilla es
    un comentario que venia dentro del texto. El nombre del fichero dice menos, pero no miente."""
    assert not tr.hay_encabezados_de_verdad("corpus/derivado/x/SI09.pdf.md")
    assert not tr.hay_encabezados_de_verdad("corpus/x/expresiones_regulares.txt")
    assert tr.hay_encabezados_de_verdad("corpus/x/01-introduccion-web.md")
    assert tr.hay_encabezados_de_verdad("corpus/derivado/x/Teoria5.docx.md")

    assert tr.titulo_de("corpus/derivado/x/SI09.pdf.md", "# fdisk /dev/sdb\n\ntexto") == "SI09"
    assert tr.titulo_de("corpus/x/expresiones_regulares.txt",
                        "# -*- coding: utf-8 -*-\nprint 1") == "expresiones_regulares"
    assert tr.titulo_de("corpus/x/12-redis.md", "# Redis Caching\n\ntexto") == "Redis Caching"


# --- enunciado de ejercicio, la etiqueta que faltaba --------------------------------------------

def test_un_boletin_de_ejercicios_es_un_enunciado_no_un_procedimiento():
    """Lo que se le PIDE al alumno no es ni explicacion ni procedimiento, y hace falta poder
    pedirlo por su etiqueta: los enunciados son la fuente de los pares oro del 3.6."""
    texto = ("NIVEL PADAWAN\n1. Escribe un programa que de los buenos dias.\n"
             "2. Escribe un programa que calcule el area de un cuadrado de lado 5.\n"
             "3. Escribe un programa que lea dos numeros y muestre su suma.\n")
    assert tr.tipo_de_contenido(texto, False, "ud4_Ejercicios") == "enunciado_ejercicio"


def test_un_cuestionario_tipo_test_tambien_es_un_enunciado():
    texto = ("95. ¿Que metodo se ejecuta cuando un cliente se conecta?\n"
             "a) OnConnected().\nb) OnConnectedAsync().\nc) ConnectAsync().\nd) Ninguno.\n")
    assert tr.tipo_de_contenido(texto, False, "Test de ASP.NET Core") == "enunciado_ejercicio"


def test_una_explicacion_no_se_convierte_en_enunciado_por_el_titulo():
    """El control negativo: el titulo dice "practica" pero el texto explica, no manda."""
    texto = ("La memoria virtual permite que un proceso use mas memoria de la fisica disponible. "
             "El sistema operativo mantiene una tabla de paginas que traduce las direcciones "
             "logicas en fisicas, y lleva a disco las paginas que llevan mas tiempo sin usarse.")
    assert tr.tipo_de_contenido(texto, False, "Practica 3 de sistemas") != "enunciado_ejercicio"


def test_la_prosa_con_nombres_de_metodos_no_es_codigo():
    """El error inverso del segundo muestreo: una tabla de referencia de Swing, que es prosa,
    salia marcada `codigo` porque cada fila lleva una firma de metodo dentro."""
    texto = ("void setSelectionMode(int) Selecciona los intervalos de seleccion permitidos en la "
             "tabla. Los valores validos estan definidos en ListSelectionModel como "
             "SINGLE_SELECTION y MULTIPLE_INTERVAL_SELECTION, que es el valor por defecto.\n"
             "void setSelectionModel(ListSelectionModel) Selecciona el modelo usado para "
             "controlar las selecciones de la tabla, y devuelve el modelo anterior.")
    assert tr.tipo_de_contenido(texto, False, "5.- Swing") != "codigo"


def test_el_python_suelto_en_un_txt_si_es_codigo():
    """Y el directo: Python no lleva llaves ni puntos y coma, asi que un .txt lleno de Python
    pasaba por prosa."""
    texto = ("reExpresion = \"[0-9a-zB]bc\"\n"
             "print \"Corchetes mas rango concatenado\"\n"
             "print \"Si\" if (re.match(reExpresion, \"Abc\")) else \"No\"\n"
             "from re import match\n")
    assert tr.tipo_de_contenido(texto, False, "expresiones_regulares") == "codigo"
