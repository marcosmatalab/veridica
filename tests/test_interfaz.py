"""La interfaz mínima del encargo 2.4: lo que se puede comprobar hoy, y solo eso.

QUE ESTOS TESTS NO PRUEBAN, dicho aquí para que nadie lea de más: **no prueban que los cuatro tipos
se distingan sobre salida REAL**, porque sin recuperación no existe ninguna afirmación `literal` ni
ninguna `parafrasis` de verdad. Ese criterio, tal como estaba escrito en el encargo, se cumpliría
validando la interfaz contra material fabricado, que es la misma familia que "los tipos son
estables" cuando el modelo no tenía alternativa. Aquí se comprueba que **los estilos** se distinguen
—sobre `/estilos`, con datos declarados como inventados— y que la distinción **no es solo de
color**. La comprobación sobre salida real viaja a la fase 3, junto con el clic de la referencia.

Y tampoco prueban que los tipos se VEAN distintos, que no es lo mismo que declararlos distintos.
Estas sondas leen el CSS: saben si `literal` y `parafrasis` traen señales de forma diferentes, no
si esas señales sobreviven a un metro de distancia y a la compresión de vídeo. El fallo de la
paráfrasis del 12 de agosto de 2026 lo encontró un ojo mirando `/estilos` al 50 %, no esta puerta.
**Por eso el cierre del encargo pide otra mirada humana al 50 %**, escrito en el enunciado: dar el
encargo por bueno con ruff y pytest en verde sería sustituir el instrumento que funcionó por el que
falló.

Y sobre qué corren estos tests, que importa para saber qué NO dicen: leen los ficheros de `web/` en
el disco del repo y hablan con la aplicación **en proceso**. No hablan con el contenedor. Si la
imagen se construyó antes del último cambio de `web/`, estos tests estarán en verde sobre el fichero
nuevo mientras el contenedor sirve el viejo —pasó la noche del 12 de agosto de 2026—, porque `web/`
va copiado dentro de la imagen. Por eso el ritual del 8.4 empieza por `docker compose up -d --build
api` y solo después por la ventana limpia. Es una limitación declarada, no un olvido: una puerta que
lo cubriera tendría que levantar el contenedor, y eso no cabe en la puerta del CI.
"""

import os
import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.main import EstaticosQueRevalidan, app
from app.core.catalogo import CatalogoEnMemoria, fila_a_asignatura
from app.core.traza import TrazaEnMemoria
from tests.test_consulta_sse import BUENO, ClienteFalso, en_trozos, eventos

WEB = Path(__file__).resolve().parents[1] / "web"
TIPOS = ("literal", "parafrasis", "conocimiento", "calculo", "andamiaje")

ASIGNATURAS = {
    "daw": [{"id": 29, "codigo": "0484", "nombre": "Bases de datos", "curso": 1, "horas": 165,
             "norma": "RD 405/2023", "titulacion_duena": "daw", "fragmentos": 3892,
             "transversal": False}],
    "asir": [{"id": 12, "codigo": "0373",
              "nombre": "Lenguajes de Marcas y Sistemas de Gestión de Información", "curso": None,
              "horas": None, "norma": "RD 1629/2009", "titulacion_duena": "daw",
              "fragmentos": 210, "transversal": True}],
}


@pytest.fixture
def cliente_http():
    app.state.traza = TrazaEnMemoria()
    # El embebedor se apaga a proposito: estos tests son del CONTRATO y del streaming, no de la
    # recuperacion. Con el puesto, /consulta iria a buscar fragmentos a una base que aqui no hay.
    app.state.embebedor = None
    app.state.catalogo = CatalogoEnMemoria(
        asignaturas=ASIGNATURAS,
        fragmentos={(7, 4321): {"id": 4321, "texto": "una clave primaria identifica cada fila",
                                "unidad": "Unidad 3", "codigo": "0484",
                                "asignatura": "Bases de datos", "documento": "BD05.pdf.md",
                                "ruta": "corpus/x.md", "contexto": "ctx"},
                    # El fragmento que la CASCADA trae de otra asignatura de la titulacion: la
                    # misma respuesta 7 lo cito, asi que tiene que abrir por procedencia.
                    (7, 5555): {"id": 5555, "texto": "el kernel gestiona los procesos",
                                "unidad": "Unidad 1", "codigo": "0369",
                                "asignatura": "Implantación de Sistemas Operativos",
                                "documento": "ISO01.pdf.md", "ruta": "corpus/y.md",
                                "contexto": "ctx"}})
    with TestClient(app) as c:
        yield c


# --- el selector, que es el primer sitio donde se ve el trabajo del 2.1 -------------------------

def test_el_selector_marca_los_transversales_y_no_se_inventa_el_curso(cliente_http):
    """DAM y ASIR van sin curso a propósito (solo tenemos la orden de currículo de DAW), y el 0373
    llega a ASIR por la puente aunque su fila viva bajo DAW."""
    datos = cliente_http.get("/asignaturas?titulacion=asir").json()
    a = datos["asignaturas"][0]
    assert a["transversal"] is True and a["titulacion_duena"] == "daw"
    assert a["curso"] is None


def test_por_la_puente_solo_viaja_lo_que_respalda_la_norma_de_quien_pregunta():
    """EL BARRIDO ENTERO, no solo el caso que se encontró mirando la pantalla.

    El curso fue el primero: el 0373 salía en ASIR con "1.º", que es el de la orden de currículo DE
    DAW. Barriendo aparecieron dos más —el nombre, que el RD de ASIR escribe con otras mayúsculas, y
    las horas, que salen de una orden que ASIR no tiene—. Los tres viajan ahora desde la fila de la
    puente, que es la que representa "este módulo visto desde este título".
    """
    daw = (12, "0373", "daw", "Lenguajes de marcas y sistemas de gestión de información", 1, 120,
           "RD 405/2023", 210)
    asir = (12, "0373", "daw", "Lenguajes de Marcas y Sistemas de Gestión de Información", None,
            None, "RD 1629/2009", 210)
    a, b = fila_a_asignatura(daw, "daw"), fila_a_asignatura(asir, "asir")
    assert a["curso"] == 1 and a["horas"] == 120 and a["transversal"] is False
    assert b["curso"] is None, "el curso de DAW no puede aparecer como si fuera el de ASIR"
    assert b["horas"] is None, "las horas salen de una orden de curriculo que ASIR no tiene"
    assert b["nombre"] != a["nombre"], "cada titulo escribe el nombre como lo escribe su norma"
    assert b["norma"] == "RD 1629/2009", "el nombre se acompaña de la norma que lo respalda"
    assert b["transversal"] is True and b["titulacion_duena"] == "daw"


def test_el_codigo_y_el_conteo_de_fragmentos_si_viajan():
    """La otra mitad del criterio: no todo campo está afectado. El código es el mismo en los tres
    títulos —eso es lo que hace transversal a un módulo— y el número de fragmentos es un hecho de
    nuestro corpus, no de ninguna norma."""
    fila = (12, "0373", "daw", "Lenguajes de Marcas", None, None, "RD 1629/2009", 210)
    visto = fila_a_asignatura(fila, "asir")
    assert visto["codigo"] == "0373" and visto["fragmentos"] == 210


def test_una_titulacion_que_no_esta_no_devuelve_una_lista_vacia_con_aire_de_correcta(cliente_http):
    assert cliente_http.get("/asignaturas?titulacion=inventada").status_code == 404


# --- el fragmento se abre por procedencia -------------------------------------------------------

def test_el_fragmento_se_abre_si_esa_respuesta_lo_cito(cliente_http):
    f = cliente_http.get("/respuestas/7/fragmentos/4321")
    assert f.status_code == 200 and f.json()["codigo"] == "0484"


def test_el_fragmento_DE_OTRA_ASIGNATURA_se_abre_si_esa_respuesta_lo_cito(cliente_http):
    """LA MITAD QUE FALTABA DE LA CASCADA: si el sistema responde con material de otra asignatura de
    tu titulación, el enlace tiene que ABRIR ese fragmento. Responder sin poder comprobar de dónde
    sale sería media reforma.

    **Y esto ya funcionaba por construcción, lo cual no es excusa para no probarlo**: la
    autorización de `fragmento_citado` es por PROCEDENCIA —*"el sistema lo usó para responderte"*— y
    no por asignatura, así que un fragmento de al lado abre por el mismo camino. Una capacidad que
    nadie ejercita es una capacidad que se rompe en el primer refactor sin que nada se ponga rojo:
    la regla de la casa es que por cada respaldo declarado haya función **y** test.

    **Qué prueba este test y qué NO**, dicho aquí para que nadie lea de más: prueba que la capa HTTP
    no mete un filtro de asignatura por su cuenta. **No prueba el SQL de `CatalogoPostgres`**, que en
    CI no corre (ADR 0001). Esa mitad se comprobó contra la base real el 14/08/2026 y salió con
    número: **3 pares reales** de respuesta que cita fragmento de otra asignatura, **3 de 3 abren**
    (respuestas 9, 17 y 36, fragmentos de Implantación de Sistemas Operativos servidos a consultas
    de Bases de datos).
    """
    f = cliente_http.get("/respuestas/7/fragmentos/5555")
    assert f.status_code == 200, "un fragmento de otra asignatura citado por la respuesta no abre"
    assert f.json()["asignatura"] == "Implantación de Sistemas Operativos"


def test_el_mismo_fragmento_desde_otra_respuesta_no_se_abre(cliente_http):
    """LA DIRECCIÓN QUE IMPORTA. Cambiar el id en la URL no puede abrir material que el sistema no
    usó para responderte: eso es la lectura cruzada entre asignaturas que el 3.5 mide."""
    r = cliente_http.get("/respuestas/8/fragmentos/4321")
    assert r.status_code == 404
    assert "procedencia" in r.json()["detail"]


# --- las etapas: dibujadas solo si ocurren, y ancladas a la traza --------------------------------

def test_toda_etapa_dibujada_tiene_su_entrada_en_la_traza(cliente_http):
    """LA CONDICIÓN DEL ENCARGO CONVERTIDA EN TEST. Si la interfaz pudiera enseñar una etapa que no
    está en la traza, sería una animación de relleno con aspecto de medida."""
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    evs = eventos(cliente_http.post("/consulta", json={"texto": "x"}))
    dibujadas = [(d["nombre"], d["ms"]) for n, d in evs if n == "etapa"]
    guardadas = [(m["nombre"], m["ms"])
                 for m in app.state.traza.respuestas[0]["etapas"]["marcas"]]
    assert dibujadas and dibujadas == guardadas


def test_las_etapas_son_las_reales_y_van_en_orden_creciente(cliente_http):
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    evs = eventos(cliente_http.post("/consulta", json={"texto": "x"}))
    etapas = [d for n, d in evs if n == "etapa"]
    assert [e["nombre"] for e in etapas] == ["peticion_enviada", "primer_token_proveedor",
                                             "primera_prosa", "contrato_validado"]
    assert [e["ms"] for e in etapas] == sorted(e["ms"] for e in etapas)


def test_si_no_hay_prosa_no_se_dibuja_la_etapa_de_prosa(cliente_http):
    """Lo que no ocurre, no se dibuja: con el contrato roto antes de la redacción, `primera_prosa`
    no puede aparecer en la lista."""
    app.state.cliente_inferencia = ClienteFalso(["{no es JSON"])
    evs = eventos(cliente_http.post("/consulta", json={"texto": "x"}))
    nombres = [d["nombre"] for n, d in evs if n == "etapa"]
    assert "primera_prosa" not in nombres
    assert nombres[-1] == "abstencion"


# --- el enganche de la ablacion ------------------------------------------------------------------

def test_el_interruptor_de_verificacion_se_registra_aunque_no_haga_nada(cliente_http):
    """Reservado en el 2.4 para no injertarlo la noche antes de la demo. Hoy no cambia el
    resultado, y por eso lo que se comprueba es que QUEDA CONSTANCIA de lo que se pidió.

    **ACTUALIZADO EN EL 2.5:** este test anclaba `construido: False`, que era cierto cuando se
    escribió y dejó de serlo con el 4.5 — y como el valor se PERSISTE, las 391 respuestas de la
    base dicen que no hubo verificación en consultas donde sí la hubo. Lo que se ancla ahora son las
    dos mitades separadas: la capa **está** construida, y el interruptor **sigue** sin efecto. Antes
    iban confundidas en un solo `False`, que es lo que permitía que una siguiera pareciendo la otra.
    """
    app.state.cliente_inferencia = ClienteFalso(en_trozos(BUENO))
    evs = eventos(cliente_http.post("/consulta", json={"texto": "x", "verificacion": False}))
    fin = [d for n, d in evs if n == "fin"][0]
    assert fin["verificacion"]["solicitada"] is False
    assert fin["verificacion"]["construido"] is True
    assert fin["verificacion"]["solicitada_tiene_efecto"] is False, \
        "un interruptor que no hace nada se declara, no se disfraza de capa ausente"
    guardado = app.state.traza.respuestas[0]["etapas"]["verificacion"]
    assert guardado["solicitada"] is False and guardado["construido"] is True
    assert guardado["encargos"] == ["4.2", "4.3", "4.4", "4.5"]


# --- la muestra de estilos vive aparte ------------------------------------------------------------

def test_la_vista_del_alumno_no_enlaza_la_muestra_de_estilos(cliente_http):
    """Una etiqueta no basta: en directo se abre por accidente. La muestra está en su ruta y la
    vista del alumno no tiene por dónde llegar."""
    inicio = cliente_http.get("/").text
    assert "estilos" not in inicio.replace("estilo.css", "")


#: Formas de "esto todavía no está" que un fichero ESTÁTICO no puede saber y por tanto no puede
#: afirmar. La lista es de PATRONES y no de las frases exactas que hubo: anclar las frases exactas
#: haría una puerta que solo caza el error de anteayer, que es el filtro escrito sobre el ejemplo.
PROMESAS_QUE_UN_CARTEL_NO_PUEDE_HACER = (
    r"sin recuperaci[óo]n",
    r"sin verificaci[óo]n",
    r"hasta la fase \d",
    r"sin GPU",
    r"salen <b>sin verificar</b>",
    r"no hay citas del temario",
)


def sin_comentarios(html: str) -> str:
    """Lo que el alumno VE. Los comentarios viajan en el cuerpo pero no se muestran, y este barrido
    pregunta por lo que se afirma, no por lo que se explica — de hecho los comentarios de
    `index.html` CITAN las frases viejas para contar por qué se quitaron, así que un grep a pelo
    sobre la página cuenta dos y se lee como si el arreglo no hubiera entrado. El instrumento tiene
    que mirar lo mismo que mira el ojo."""
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


@pytest.mark.parametrize("patron", PROMESAS_QUE_UN_CARTEL_NO_PUEDE_HACER)
def test_la_vista_del_alumno_no_declara_capacidades_del_proceso(cliente_http, patron):
    """LA CABECERA SE QUEDÓ DICIENDO LO DE ANTEAYER Y SE SIRVIÓ POR HTTP DÍAS, CON TESTIGO.

    Decía *"Encargo 2.4 · sin recuperación (fase 3) ni verificación (fase 4)"* y *"sin efecto hasta
    la fase 4"* con las dos construidas y enchufadas. **No era la imagen vieja**: las cadenas
    estaban vivas en `web/index.html`, así que reconstruir no lo habría arreglado — y por eso esta
    puerta lee el FICHERO y no el contenedor.

    Y la regla general, que es lo que se ancla aquí y no las tres frases: **un fichero estático no
    puede saber qué sabe hacer el proceso.** Sin torch no hay búsqueda por significado ni NLI, y el
    cartel no se entera. Quien contesta a eso es `/salud`, que lo mide. Un cartel que declare
    capacidades acierta el día que se escribe y miente todos los demás.
    """
    visible = sin_comentarios(cliente_http.get("/").text)
    encontrado = re.search(patron, visible, re.I)
    assert not encontrado, (
        f"la vista del alumno afirma algo sobre el estado del proceso: {encontrado.group(0)!r}. "
        "Eso lo dice /salud, que lo comprueba; un cartel estático solo puede enlazarlo.")


def test_la_sonda_del_cartel_se_pone_roja_con_una_pagina_que_si_lo_declara():
    """La otra dirección, que es la que dice si la sonda sirve: sobre una página que SÍ lleva la
    promesa, tiene que cazarla — y sobre la misma promesa metida en un comentario, NO, porque el
    alumno no la ve. Sin esta segunda mitad, `sin_comentarios` podría estar borrando la página
    entera y los seis casos de arriba pasarían igual."""
    mala = '<span class="aviso">Encargo 2.4 · sin verificación (fase 4)</span>'
    buena = '<!-- decía "sin verificación (fase 4)" y se quitó --><span>Todo enchufado</span>'
    assert any(re.search(p, sin_comentarios(mala), re.I)
               for p in PROMESAS_QUE_UN_CARTEL_NO_PUEDE_HACER), "la sonda no caza la promesa visible"
    assert not any(re.search(p, sin_comentarios(buena), re.I)
                   for p in PROMESAS_QUE_UN_CARTEL_NO_PUEDE_HACER), \
        "la sonda caza un comentario, o sea que no está mirando lo que ve el alumno"


def test_la_muestra_avisa_de_que_todo_es_inventado_y_lo_dice_arriba(cliente_http):
    pagina = cliente_http.get("/estilos").text
    assert "INVENTADO" in pagina
    assert pagina.index("INVENTADO") < pagina.index("clave primaria"), \
        "el aviso tiene que venir antes que el primer dato falso"


def test_el_estado_en_json_sigue_existiendo_pero_en_api(cliente_http):
    """Este test comprobaba `startswith("2.4")`, y eso ataba una puerta al número de encargo: caduca
    cada vez que se avanza, y lo único que enseña al ponerse roja es que el calendario corre. Peor:
    invita a actualizar el número sin mirar si lo que dice el aviso sigue siendo verdad.

    Lo que sí es invariante —y es para lo que existe `/api`— es que **declare su estado sin afirmar
    en presente lo no construido** (principio 2). Eso es lo que se prueba ahora, en las dos
    direcciones: que lo no construido aparece listado, y que lo construido no se anuncia como
    pendiente.

    **ACTUALIZADO EN EL 2.5, y este test es el ejemplo de su propia lección.** Anclaba dos cosas que
    dejaron de ser verdad: que `/trazas/{id}` estaba SIN construir, y que el aviso dijera *"comprueba
    la FORMA y no la verdad ... toda afirmación viaja con veredicto sin_verificar"* — con el 4.2, el
    4.3, el 4.4 y el 4.5 corriendo en cada consulta. O sea que el test defendía la versión vieja del
    mundo contra su corrección: arreglar `/api` lo ponía rojo y ese rojo se lee como regresión.
    Ahora ancla el invariante en su forma útil: lo construido no aparece como pendiente, y lo que
    sigue SIN calibrar se dice."""
    cuerpo = cliente_http.get("/api").json()
    assert cuerpo["encargo"], "sin encargo declarado, /api no dice en qué punto está"
    assert "/eval/correr" in cuerpo["no_construido"]
    assert "/trazas/{id}" in cuerpo["construido"], "el 2.5 la construyo: anunciarla como pendiente "\
                                                   "es afirmar en presente un estado que ya no existe"
    assert "/trazas/{id}" not in cuerpo["no_construido"]
    aviso = cuerpo["aviso"].lower()
    assert "verifica" in aviso, "el aviso dejó de decir que lo que se afirma se comprueba"
    assert "sin calibrar" in aviso, \
        "lo que sigue sin calibrar (portero y ritmo) tiene que seguir dicho: es lo que hoy NO está"


# --- lo estatico se revalida, que es la causa y no el sintoma -------------------------------------
#
# Se prueba con el cliente de test y no mirando un navegador A PROPOSITO: lo que nos mordio fue
# justamente la heuristica de un navegador, que no es determinista ni se puede poner en una puerta.

ESTATICOS = ("estilo.css", "render.js", "app.js")


@pytest.mark.parametrize("fichero", ESTATICOS)
def test_todo_lo_de_estatico_manda_revalidar(cliente_http, fichero):
    """TODO /estatico, no solo la hoja. El caso caro es `render.js`: un estilo cacheado se ve raro,
    pero un render.js viejo dibuja las etapas de otra forma o no las dibuja, y esa es la capa que no
    tiene puerta automatica porque en el CI no hay motor de JavaScript."""
    r = cliente_http.get(f"/estatico/{fichero}")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-cache", \
        "sin instruccion de frescura el navegador la inventa, y ahi esta el verde mentiroso"


def test_revalidar_sale_barato_un_304_sin_cuerpo(cliente_http):
    """`no-cache` no es "no caches", es "pregunta antes de usar tu copia". Con el ETag que ya se
    servia, preguntar cuesta un 304 vacio, asi que la cabecera no se paga en cada carga."""
    primera = cliente_http.get("/estatico/estilo.css")
    segunda = cliente_http.get("/estatico/estilo.css",
                               headers={"If-None-Match": primera.headers["etag"]})
    assert segunda.status_code == 304 and not segunda.content
    assert segunda.headers["cache-control"] == "no-cache", \
        "el 304 es donde el navegador refresca las instrucciones que guarda con la copia"


def test_tras_tocar_el_fichero_la_misma_peticion_condicional_trae_lo_nuevo(tmp_path):
    """LA DIRECCION QUE IMPORTA, y sobre un directorio de usar y tirar para no tocar el repo: que
    revalidar sirva de algo. Un 304 eterno seria el mismo fallo con otra cara."""
    hoja = tmp_path / "hoja.css"
    hoja.write_text(".a { color: red; }", encoding="utf-8")
    mini = FastAPI()
    mini.mount("/estatico", EstaticosQueRevalidan(directory=tmp_path), name="estatico")
    with TestClient(mini) as cliente:
        primera = cliente.get("/estatico/hoja.css")
        etag = primera.headers["etag"]
        assert primera.headers["cache-control"] == "no-cache"
        assert cliente.get("/estatico/hoja.css",
                           headers={"If-None-Match": etag}).status_code == 304

        # El cambio se confirma EN DISCO antes de leer ninguna respuesta: si el fichero no cambiara
        # de verdad -mismo tamaño y mismo instante-, el 200 de abajo no probaria nada.
        antes = hoja.stat()
        hoja.write_text(".a { color: red; }\n.b { color: blue; }", encoding="utf-8")
        os.utime(hoja, (antes.st_mtime + 2, antes.st_mtime + 2))
        despues = hoja.stat()
        assert (despues.st_size, despues.st_mtime) != (antes.st_size, antes.st_mtime), \
            "el fichero no ha cambiado: lo de abajo no seria una prueba"

        tercera = cliente.get("/estatico/hoja.css", headers={"If-None-Match": etag})
        assert tercera.status_code == 200 and ".b" in tercera.text
        assert tercera.headers["etag"] != etag


# --- la distincion entre tipos es estructural, no cromatica --------------------------------------

def test_cada_tipo_lleva_etiqueta_con_texto():
    """Si la compresión de vídeo se come el color y los bordes finos, el alumno todavía lee
    'CITA LITERAL'. La etiqueta es la parte de la distinción que no se pierde nunca."""
    render = (WEB / "render.js").read_text(encoding="utf-8")
    etiquetas = re.search(r"const ETIQUETAS = \{(.+?)\};", render, re.S).group(1)
    for tipo in TIPOS:
        assert f"{tipo}:" in etiquetas, f"{tipo} no tiene etiqueta de texto"
    assert "Analogía" in render, "la analogía necesita su propia etiqueta, no la genérica"
    # Y DISTINTAS ENTRE SÍ, que es la otra mitad y no se seguía de lo de arriba: cinco etiquetas
    # correctas y repetidas pasarían este test sin distinguir nada. Salió al barrer el repo
    # buscando la lección de la pareja literal/parafrasis, y estaba en la línea de al lado.
    textos = re.findall(r':\s*"([^"]+)"', etiquetas)
    assert len(set(textos)) == len(TIPOS), f"dos tipos comparten el texto de la etiqueta: {textos}"


FORMA = ("border", "margin-left", "content", "font-family", "font-style", "padding")


def tipos_solo_por_color(css: str) -> list:
    """Devuelve los tipos que se distinguen ÚNICAMENTE por color. Es la sonda, y por eso está
    separada del test: hay que verla decir que sí sobre una hoja mala antes de creerse su vacío."""
    malos = []
    for tipo in TIPOS:
        bloque = re.search(r"\.afirmacion\.%s\s*\{(.+?)\}" % tipo, css, re.S)
        if not bloque or not any(p in bloque.group(1) for p in FORMA):
            malos.append(tipo)
    return malos


def test_ningun_tipo_se_distingue_solo_por_color():
    """LA COMPROBACIÓN QUE IMPORTA PARA UNA VIDEOLLAMADA. Cada tipo tiene que traer al menos una
    propiedad de FORMA -borde, sangrado, comillas, tipografía-, no solo `color`."""
    malos = tipos_solo_por_color((WEB / "estilo.css").read_text(encoding="utf-8"))
    assert not malos, f"solo se distinguen por color, y en vídeo comprimido eso desaparece: {malos}"


def test_la_sonda_del_color_se_pone_roja_con_una_hoja_que_solo_usa_color():
    """La otra dirección, sobre una hoja mutada a mano: sin esto, el test de arriba estaría en verde
    también el día que alguien borre la mitad de la hoja de estilos."""
    hoja_mala = "\n".join(".afirmacion.%s { color: #123456; background: #fff; }" % t for t in TIPOS)
    assert tipos_solo_por_color(hoja_mala) == list(TIPOS)


# --- la pareja que hace el trabajo: `literal` y `parafrasis` -------------------------------------
#
# La sonda de arriba comprueba una propiedad de cada tipo POR SEPARADO -"tiene alguna señal que no
# es color"- y con eso se le escapó el fallo entero, porque la propiedad que importa es RELACIONAL:
# se distinguen ENTRE SÍ. `border-left` daba verde a `literal` y a `parafrasis` a la vez, y una
# señal que dos tipos COMPARTEN no distingue nada. Lo de abajo compara las dos, no las suma.

TINTA_UNICA = "#000"
GROSOR_UNICO = "3px"
TRAZOS = ("dashed", "dotted", "double", "solid", "hidden", "none")
# La fontanería que COLOCA una marca no es la marca. `display: flex` y su `gap` existen para colgar
# el glifo de la parafrasis; si alguien borrara el glifo y se dejara el flex, la sonda no puede
# seguir diciendo que tiene señal propia, porque en pantalla no quedaría nada que ver.
FONTANERIA = ("display", "flex", "gap", "align", "justify", "grid", "line-height", "box-sizing")

# Las reglas de la pareja tal como estaban el 12 de agosto de 2026, ancladas aquí para que "visto
# en rojo con los ojos" quede convertido en regresión permanente: la `parafrasis` era el estilo por
# defecto con otro color y un borde doble, y no tenía ni una marca estructural propia.
HOJA_DEL_12_DE_AGOSTO = """
.afirmacion.literal { border-left: 10px solid var(--literal); margin-left: 28px; }
.afirmacion.literal .etiqueta { color: var(--literal); }
.afirmacion.literal .cuerpo { font-size: 17px; }
.afirmacion.literal .cuerpo::before,
.afirmacion.literal .cuerpo::after { content: '"'; font-size: 26px; font-weight: 700; }
.afirmacion.parafrasis { border-left: 10px double var(--parafrasis); margin-left: 14px; }
.afirmacion.parafrasis .etiqueta { color: var(--parafrasis); }
"""


def igualar_bordes_y_apagar_color(css: str) -> tuple[str, list[str]]:
    """Muta la hoja a UN color y UN grosor de borde, y devuelve la hoja mutada y su diff.

    El diff sale por la puerta para que el test lo afirme ANTES de leer el resultado. Una mutación
    que no muta pone el test en verde por el motivo equivocado, que es la misma trampa del verde
    mentiroso metida dentro de la herramienta de comprobar.
    """
    mutada = re.sub(r"#[0-9a-fA-F]{3,8}", TINTA_UNICA, css)
    mutada = re.sub(r"var\(--[a-z-]+\)", TINTA_UNICA, mutada)
    mutada = re.sub(r"border[a-z-]*\s*:[^;}]*",
                    lambda m: re.sub(r"\d+(?:\.\d+)?px", GROSOR_UNICO, m.group(0)), mutada)
    diff = [f"{n}: {antes.strip()}   ->   {despues.strip()}"
            for n, (antes, despues) in enumerate(zip(css.splitlines(), mutada.splitlines()), 1)
            if antes != despues]
    return mutada, diff


def sin_la_marca_de(css: str, tipo: str) -> str:
    """Quita las reglas de PSEUDOELEMENTO de un tipo, que es donde vive su marca.

    Escrito así -por el sitio y no por el contenido- a propósito: la marca de la parafrasis ha sido
    un glifo colgado, luego un glifo repetido y hoy son dos barras de borde, y esta mutación tiene
    que seguir mordiendo sin que nadie se acuerde de actualizarla. Si un día no muerde, el test lo
    dice antes de leer ningún resultado.
    """
    return re.sub(r"([^{}]+)\{([^{}]*)\}",
                  lambda r: "" if f".{tipo}" in r.group(1) and "::" in r.group(1) else r.group(0),
                  css)


def declaraciones_del_tipo(css: str, tipo: str) -> list:
    """(sufijo del selector, propiedad, valor) de TODAS las reglas que nombran a un tipo.

    Incluidas las de `.cuerpo::before`, que es donde viven las comillas de `literal`: una sonda que
    solo mirase el bloque `.afirmacion.<tipo> { }` -como la de arriba- no vería la única señal que
    hoy salva a la literal, y creería que se sostiene sobre el borde. Límite declarado: recoge por
    nombre, así que las señales de `andamiaje` traen también las que la `analogia` sobrescribe.
    """
    fuera = []
    for selectores, cuerpo in re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", css,
                                                                        flags=re.S)):
        for selector in selectores.split(","):
            selector = " ".join(selector.split())
            if ".afirmacion" not in selector or f".{tipo}" not in selector:
                continue
            sufijo = re.sub(r"^\.afirmacion[\w.-]*", "", selector).strip()
            for declaracion in cuerpo.split(";"):
                propiedad, _, valor = declaracion.partition(":")
                if valor:
                    fuera.append((sufijo, propiedad.strip(), " ".join(valor.split())))
    return fuera


def senales_de_forma(css: str, tipo: str) -> set:
    """Lo que le queda a un tipo cuando el color y el grosor no cuentan.

    Fuera el color. Fuera el grosor, **incluido `double`**: igualado a un solo grosor, un borde
    doble se dibuja como una línea sólida, así que no puede contar como señal. Y los números se
    normalizan: `margin-left: 14px` y `margin-left: 28px` son LA MISMA señal, porque un sangrado
    que solo cambia de cantidad no se ve cuando los dos tipos no están pegados en pantalla. Cuenta
    como señal propia tener una CLASE de marca que el otro no tiene -un glifo, una tipografía, una
    caja, una manera de colgar el texto-, y no un ajuste del mismo recurso ni la fontanería que lo
    coloca.
    """
    senales = set()
    for sufijo, propiedad, valor in declaraciones_del_tipo(css, tipo):
        if propiedad == "color" or propiedad.endswith("-color") or propiedad.startswith("back"):
            continue
        if propiedad.startswith(FONTANERIA):
            continue
        if propiedad.startswith("border"):
            trazo = next((t for t in TRAZOS if t in valor), None)
            if trazo is None:            # grosor o color a secas: no es señal de forma
                continue
            valor = "solid" if trazo == "double" else trazo
        elif propiedad == "content":
            # El glifo ES la señal, así que se quita SOLO el par de comillas de CSS que lo envuelve
            # y no todas las comillas: `content: '"'` es la marca de la literal, y un `strip` de
            # caracteres se la comía entera y dejaba la señal vacía.
            valor = re.sub(r"^(['\"])(.*)\1$", r"\2", valor)
            if not valor:
                continue  # `content: ""` no dibuja nada: solo hace existir el pseudoelemento
        else:
            valor = re.sub(r"\d+(?:\.\d+)?[a-z%]*", "#", valor)
        senales.add(f"{sufijo}|{propiedad}:{valor}")
    return senales


def test_la_mutacion_de_bordes_y_color_se_aplica_de_verdad():
    """PRIMERO LA MUTACIÓN, Y ENSEÑANDO EL DIFF; el resultado se lee después. Si un día la hoja
    cambia de forma y estas sustituciones dejan de morder, el test de abajo seguiría verde sobre
    una hoja sin mutar, que es exactamente no haber probado nada."""
    mutada, diff = igualar_bordes_y_apagar_color((WEB / "estilo.css").read_text(encoding="utf-8"))
    visto = "\n".join(diff)
    assert diff, "la mutación no ha cambiado NADA de la hoja"
    assert "var(--" not in mutada, f"quedan colores con nombre propio:\n{visto}"
    assert set(re.findall(r"#[0-9a-fA-F]{3,8}", mutada)) == {TINTA_UNICA}, visto
    bordes = " ".join(re.findall(r"border[a-z-]*\s*:[^;}]*", mutada))
    grosores = set(re.findall(r"\d+(?:\.\d+)?px", bordes))
    assert grosores == {GROSOR_UNICO}, f"quedan bordes de grosor distinto: {grosores}\n{visto}"
    for tipo in ("literal", "parafrasis"):
        assert any(tipo in linea for linea in diff), \
            f"la mutación no llega a la regla de {tipo}, que es la que se está probando:\n{visto}"


def test_literal_y_parafrasis_se_distinguen_con_los_bordes_IGUALADOS():
    """LA PAREJA QUE HACE EL TRABAJO EN LA SESIÓN: separa lo que el temario dice palabra por
    palabra de lo que el sistema reformula. Con el color apagado y todos los bordes al mismo
    grosor, cada una tiene que conservar una señal de forma que la otra NO tiene. No basta con que
    cada una traiga alguna señal: `border-left` las traía las dos y no distinguía nada."""
    hoja = (WEB / "estilo.css").read_text(encoding="utf-8")
    mutada, diff = igualar_bordes_y_apagar_color(hoja)
    assert diff, "sin mutación aplicada no se lee el resultado"
    literal, parafrasis = senales_de_forma(mutada, "literal"), senales_de_forma(mutada, "parafrasis")
    assert parafrasis - literal, \
        "la parafrasis no tiene ninguna señal de forma propia: es la literal sin comillas"
    assert literal - parafrasis, "la literal ha perdido lo que la separaba de la parafrasis"

    # Y de qué depende ese verde: quitando la marca tiene que caerse. Sin esto, la fontanería que
    # la coloca bastaría para dar por buena una parafrasis sin nada que ver en pantalla.
    sin_marca = sin_la_marca_de(hoja, "parafrasis")
    assert sin_marca != hoja, "la mutación no ha quitado ninguna marca: el resultado no valdría"
    apagada, _ = igualar_bordes_y_apagar_color(sin_marca)
    assert not senales_de_forma(apagada, "parafrasis") - senales_de_forma(apagada, "literal"), \
        "el verde de arriba no lo sostiene la marca: la sonda lo daría igual sin ella"


def test_la_sonda_de_la_pareja_se_pone_roja_con_la_hoja_del_12_de_agosto():
    """LA OTRA DIRECCIÓN, sobre las reglas que de verdad estaban en el repo y que de verdad se
    veían iguales al 50 %. Sin esto, la sonda de arriba estaría en verde también el día que alguien
    devuelva la parafrasis al estilo por defecto."""
    mutada, diff = igualar_bordes_y_apagar_color(HOJA_DEL_12_DE_AGOSTO)
    assert diff, "sin mutación aplicada no se lee el resultado"
    literal, parafrasis = senales_de_forma(mutada, "literal"), senales_de_forma(mutada, "parafrasis")
    assert not parafrasis - literal, \
        "la sonda tiene que ver que aquella parafrasis no tenía ni una señal propia"
    assert '.cuerpo::before|content:"' in literal - parafrasis, \
        "lo que salvaba a la literal era el glifo, y la sonda tiene que conservarlo tal cual"


# --- y la sonda lee la HOJA, no la PAGINA ---------------------------------------------------------
#
# Todo lo de arriba comprueba que el CSS DECLARA señales distintas. Ninguna de esas sondas sabe si
# los selectores casan con algo: un `.afirmacion.parafrasis .texto::before` -con el gancho mal
# escrito- declara una señal preciosa que no se dibuja jamas, y pasaria en verde. Es la misma familia
# que el resto del fichero: se comprueba una mitad y se da por buena la otra.


def clases_que_escribe_el_dibujante(js: str) -> set:
    """Las clases que `render.js` pone de verdad en el marcado.

    Limite declarado: esto LEE el fuente del dibujante, no lo ejecuta, porque en el CI no hay motor
    de JavaScript. Ve los ganchos que el codigo escribe; no ve si una rama concreta se toma.
    """
    literales = set()
    for expresion in re.findall(r"texto\(\s*\"[^\"]*\"\s*,[^,]*,\s*([^)]+)\)", js):
        literales.update(re.findall(r"\"([^\"]+)\"", expresion))
    literales.update(re.findall(r"classList\.add\(\"([^\"]+)\"\)", js))
    literales.update(re.findall(r"className\s*=\s*\"([^\"]+)\"", js))
    clases = {trozo for literal in literales for trozo in literal.split()}
    assert '"afirmacion " + af.tipo' in js, \
        "el tipo dejo de viajar como clase en la caja: esta sonda ya no sabe que ganchos existen"
    return clases | set(TIPOS)


def selectores_huerfanos(css: str, js: str) -> list:
    """(selector, clase) de cada selector de afirmacion que pide un gancho que nadie dibuja."""
    disponibles = clases_que_escribe_el_dibujante(js)
    huerfanos = []
    for selectores, _ in re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", css,
                                                                   flags=re.S)):
        for selector in selectores.split(","):
            if ".afirmacion" not in selector:
                continue
            for clase in re.findall(r"\.([a-zA-Z][\w-]*)", selector):
                if clase not in disponibles:
                    huerfanos.append((" ".join(selector.split()), clase))
    return huerfanos


def test_cada_selector_de_tipo_casa_con_el_marcado_QUE_SE_DIBUJA():
    """EL HUECO ENTRE LA HOJA Y LA PAGINA. Un selector que no casa con nada no da error: da una
    señal declarada que no existe en pantalla, y todas las sondas de arriba la dan por buena."""
    css = (WEB / "estilo.css").read_text(encoding="utf-8")
    js = (WEB / "render.js").read_text(encoding="utf-8")
    huerfanos = selectores_huerfanos(css, js)
    assert not huerfanos, f"selectores que piden ganchos que el dibujante no escribe: {huerfanos}"


def test_la_sonda_de_los_ganchos_se_pone_roja_con_un_selector_que_no_casa():
    """La otra direccion, con el fallo que esta sonda existe para cazar: el gancho mal escrito."""
    js = (WEB / "render.js").read_text(encoding="utf-8")
    malo = '.afirmacion.parafrasis .texto::before { content: "≈"; }'
    assert selectores_huerfanos(malo, js) == [(".afirmacion.parafrasis .texto::before", "texto")]
    bueno = '.afirmacion.parafrasis .cuerpo::before { content: "≈"; }'
    assert selectores_huerfanos(bueno, js) == [], "y en verde sobre el gancho que si se dibuja"


def test_la_muestra_no_escribe_a_mano_el_marcado_DE_LAS_AFIRMACIONES():
    """EL SEGUNDO HUECO: si /estilos dibujara las afirmaciones con HTML propio, la muestra sobre la
    que verificamos podria divergir de lo que ve el alumno, y estariamos comprobando los estilos
    contra un marcado que no sirve nadie. Hoy no pasa -las dibuja render.js, el mismo que la vista
    del alumno- y esto lo deja anclado en vez de fiado."""
    pagina = (WEB / "estilos.html").read_text(encoding="utf-8")
    for gancho in ("afirmacion", "cuerpo", "etiqueta", "veredicto", "expresion"):
        assert f'class="{gancho}' not in pagina, \
            f"la muestra escribe a mano un {gancho}: eso puede separarse de lo que ve el alumno"
    assert "dibujarAfirmacion" in pagina, "la muestra tiene que pasar por el dibujante de verdad"


def test_conocimiento_y_analogia_se_parecen_A_PROPOSITO():
    """ESCRITO PARA QUE NADIE LO "CORRIJA" MÁS ADELANTE creyendo que es el fallo de la parafrasis.
    Los dos dicen "esto no sale de tu temario", así que el parecido es SEMÁNTICO y es correcto que
    el ojo los lea como una familia; la pareja literal/parafrasis era un fallo porque esas dos no
    dicen lo mismo. Lo que se ancla es la forma del parecido: misma familia -recuadro discontinuo
    por los cuatro lados- y trazo distinto. Parecidos, no confundibles."""
    mutada, _ = igualar_bordes_y_apagar_color((WEB / "estilo.css").read_text(encoding="utf-8"))
    assert "|border:dashed" in senales_de_forma(mutada, "conocimiento")
    assert "|border:dotted" in senales_de_forma(mutada, "analogia")
    render = (WEB / "render.js").read_text(encoding="utf-8")
    assert "no sale de tu temario" in render and "no está en el temario" in render, \
        "el parecido visual solo es correcto mientras las dos etiquetas digan lo mismo"


def test_la_analogia_no_comparte_tratamiento_con_el_resto_del_andamiaje():
    """La guía lo pide por un motivo concreto: una comparación con el DNI ayuda a entender una clave
    primaria y NO está en el temario. Marcarla es lo que impide que el alumno la cite en un examen
    creyendo que la dijo el libro."""
    css = (WEB / "estilo.css").read_text(encoding="utf-8")
    assert ".afirmacion.andamiaje.analogia" in css
    render = (WEB / "render.js").read_text(encoding="utf-8")
    assert 'classList.add("analogia")' in render


def test_la_muestra_ensena_los_cinco_tipos_y_las_dos_abstenciones():
    pagina = (WEB / "estilos.html").read_text(encoding="utf-8")
    ejemplos = re.findall(r'tipo: "(\w+)"', pagina)
    assert set(ejemplos) == set(TIPOS)
    assert pagina.count("ya_habia_prosa_en_pantalla") == 2
    assert '"analogia"' in pagina


def test_la_muestra_y_la_vista_del_alumno_usan_EL_MISMO_dibujante():
    """Dos plantillas serían dos verdades: la muestra dejaría de probar lo que se ve de verdad."""
    for pagina in ("estilos.html", "app.js"):
        assert "render.js" in (WEB / pagina).read_text(encoding="utf-8")


def test_la_interfaz_no_trae_dependencias_de_fuera():
    """Sin framework y sin CDN, que dice el encargo. Y de paso: una demo que depende de una CDN es
    una demo que depende de la wifi de la sala."""
    for fichero in ("index.html", "estilos.html", "app.js", "render.js", "estilo.css"):
        texto = (WEB / fichero).read_text(encoding="utf-8")
        assert "http://" not in texto and "https://" not in texto, f"{fichero} sale a internet"


def test_hay_respaldo_si_el_servidor_no_manda_etapas():
    """LAS ETAPAS SON CARGA ESTRUCTURAL, no adorno: con 601 ms de adelanto del streaming en una
    consulta y 11 ms en otra, lo que cubre la espera son ellas. Si el evento `etapa` no llegara, la
    pantalla se quedaría muerta 1,6-2,2 s delante del cliente.

    El respaldo no es una animación: el navegador dibuja SU propia etapa, que es un hecho que él sí
    conoce -acaba de enviar la petición-, medida con su reloj y **marcada como medida en el
    cliente**, para que nunca se confunda con las que salen de la traza.

    Comprobación a nivel de fuente: en la puerta no hay motor de JavaScript, así que esto mira el
    fichero. Es una limitación declarada, no un olvido.
    """
    app_js = (WEB / "app.js").read_text(encoding="utf-8")
    assert "etapaDelCliente" in app_js
    assert 'dataset.origen = "cliente"' in app_js, "la etapa del cliente tiene que ir marcada"
    assert "etapasDelServidor === 0" in app_js, "falta el caso de cero etapas del servidor"
    assert "medido aquí" in app_js
    css = (WEB / "estilo.css").read_text(encoding="utf-8")
    assert ".etapas li.del-cliente" in css, "y tiene que verse distinta de las del servidor"


def test_la_interfaz_no_dibuja_nada_por_temporizador():
    """La condición del encargo, buscada donde se rompería: si apareciera un setTimeout o un
    setInterval pintando etapas, la barra avanzaría sola y dejaría de medir nada."""
    app_js = (WEB / "app.js").read_text(encoding="utf-8")
    for prohibido in ("setTimeout", "setInterval", "requestAnimationFrame"):
        assert prohibido not in app_js, f"{prohibido} en la vista: eso es relleno, no medida"


def test_las_etapas_que_dibuja_el_javascript_vienen_del_evento_y_no_de_una_lista_fija():
    render = (WEB / "render.js").read_text(encoding="utf-8")
    assert "etapa.detalle" in render and "etapa.ms" in render


def test_el_veredicto_sin_verificar_se_ve_en_pantalla():
    """Que viaje en el JSON no basta: el 2.2 lo guarda y el 2.4 tiene que ENSEÑARLO."""
    render = (WEB / "render.js").read_text(encoding="utf-8")
    assert "af.veredicto" in render and '"veredicto"' in render
