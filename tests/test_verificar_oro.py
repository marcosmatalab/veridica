"""Tests de la puerta de los pares oro (encargo 3.0).

Dos capas, por el mismo motivo que en el 1.0 y con el mismo trade-off (ADR 0001, ADR 0010):

  JUGUETE   corpus y casos inventados en un directorio temporal. Corren en CI, donde no hay
            corpus, y son los que demuestran que el verificador SE PONE ROJO cuando toca.
  ANCLADOS  los 100 pares reales contra el indice real. Solo corren en la maquina que tiene el
            corpus, y ahi el rojo tambien esta escrito: se muta una copia del fichero de casos.

El caso que da sentido al encargo es DESPLAZADO. Un par oro apunta por (documento, orden), que es
posicional: si el corpus se vuelve a trocear, el par sigue apuntando a algo y no protesta. No falla
nada, no se cae nada; simplemente el recall@6 pasa a medir otro texto. Por eso el par lleva el hash
del fragmento que se etiqueto, y por eso el test de abajo mueve el orden a un fragmento QUE SI
EXISTE: si el verificador solo comprobara posiciones, ese caso saldria en verde.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import admitir
import pytest
import verificar_oro

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "verificar_oro.py"
FRAGMENTOS = RAIZ / "corpus" / "fragmentos.jsonl"
CASOS = RAIZ / "evals" / "casos" / "oro_recuperacion.jsonl"
sin_corpus = pytest.mark.skipif(not FRAGMENTOS.exists(),
                                reason="necesita el corpus local (ADR 0001)")

BASE = "corpus/daw/curso2/juguete"
APUNTES = f"{BASE}/apuntes/01-sesiones.md"
PRACTICAS = f"{BASE}/practicas/01-test.md"
# Con espacios y no con guiones, porque el patron del 1.4 es "guia\\s*de\\s*estilo" y \\s no casa
# con el guion. Lo descubrio este test al salir verde cuando debia salir rojo; queda anotado como
# deuda del 1.4 (hoy no afecta: cero documentos del indice caen en ese hueco).
ESTILO = f"{BASE}/apuntes/guia de estilo.md"

# Prosa docente de verdad, con frases y puntuacion: tiene que PASAR la puerta del 1.4. Si estos
# textos no pasaran, el test de "no admitido" saldria verde por el motivo equivocado.
TEXTOS = {
    (APUNTES, 1): "La sesion se guarda en el servidor y en la cookie solo viaja el identificador. "
                  "Por eso guardar datos sensibles en la cookie es un error de principiante. "
                  "El servidor consulta la sesion en cada peticion usando ese identificador.",
    (APUNTES, 2): "El patron Post-Redirect-Get evita que al refrescar se reenvie el formulario. "
                  "Tras procesar el POST se responde con una redireccion a una pagina de lectura. "
                  "Asi el navegador nunca repite la peticion que modificaba datos.",
    (APUNTES, 3): "Los atributos flash sobreviven exactamente a una redireccion y luego se borran. "
                  "Sirven para ensenar el mensaje de exito en la pagina de destino. "
                  "No sustituyen a la sesion, porque su vida es de una sola peticion.",
    (PRACTICAS, 1): "Pregunta 42 del test de la unidad. Donde se almacenan los datos de la sesion "
                    "de un usuario y que viaja dentro de la cookie que recibe el navegador. "
                    "Justifica la respuesta con lo estudiado en la unidad correspondiente.",
    (ESTILO, 1): "Las entregas se suben al aula virtual antes del domingo a las veintitres horas. "
                 "El nombre del fichero lleva el apellido y el numero de la practica entregada. "
                 "No se corrigen entregas fuera de plazo salvo justificacion documental.",
}


def fragmento(documento: str, orden: int) -> dict:
    return {"documento": documento, "orden": orden, "asignatura": "juguete",
            "tipo_contenido": "explicacion", "texto": TEXTOS[(documento, orden)]}


def hash_de(documento: str, orden: int) -> str:
    return hashlib.sha256(TEXTOS[(documento, orden)].encode("utf-8")).hexdigest()


def par(id_par: str, documento: str, orden: int, **cambios) -> dict:
    p = {"id": id_par, "conjunto": "oro_recuperacion", "asignatura": "juguete",
         "pregunta": "¿Donde se guarda la sesion?", "localizacion": "lectura",
         "fragmento_oro": {"documento": documento, "orden": orden,
                           "hash_texto": hash_de(documento, orden)}}
    p["fragmento_oro"].update(cambios.pop("fragmento_oro", {}))
    p.update(cambios)
    return p


def escribir(camino: Path, filas: list) -> Path:
    camino.parent.mkdir(parents=True, exist_ok=True)
    with open(camino, "w", encoding="utf-8", newline="\n") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    return camino


def juguete(raiz: Path, pares: list) -> tuple[Path, Path]:
    """Indice de juguete completo (incluida la practica y la guia de estilo) y los pares dados."""
    indice = escribir(raiz / "corpus" / "fragmentos.jsonl",
                      [fragmento(d, o) for d, o in TEXTOS])
    casos = escribir(raiz / "evals" / "casos" / "oro.jsonl", pares)
    return casos, indice


def verificar(casos: Path, indice: Path):
    return subprocess.run([sys.executable, str(SCRIPT), "--casos", str(casos),
                           "--fragmentos", str(indice)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


# --- capa juguete: aqui es donde se ve el rojo ------------------------------------------------

def test_el_juguete_limpio_sale_en_verde(tmp_path):
    """El control positivo. Sin el, los rojos de abajo no dicen nada: un verificador que siempre
    grita tambien acierta cuando hay que gritar."""
    casos, indice = juguete(tmp_path, [par("oro-001", APUNTES, 1), par("oro-002", APUNTES, 2)])
    r = verificar(casos, indice)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ocurrencias=0" in r.stdout


def test_un_par_que_apunta_a_un_orden_inexistente_sale_en_rojo(tmp_path):
    casos, indice = juguete(tmp_path, [par("oro-001", APUNTES, 1)])
    trucado = json.loads(casos.read_text(encoding="utf-8").splitlines()[0])
    trucado["fragmento_oro"]["orden"] = 9999
    escribir(casos, [trucado])

    r = verificar(casos, indice)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "NO EXISTE: oro-001" in r.stdout
    assert "no_existe=1" in r.stdout


def test_un_par_desplazado_a_otro_fragmento_QUE_EXISTE_sale_en_rojo(tmp_path):
    """EL caso del encargo. El orden 2 existe y esta admitido: por posicion, este par es perfecto.
    Lo unico que lo delata es que el texto de ahi ya no es el que se etiqueto."""
    casos, indice = juguete(tmp_path, [par("oro-001", APUNTES, 1)])
    desplazado = json.loads(casos.read_text(encoding="utf-8").splitlines()[0])
    desplazado["fragmento_oro"]["orden"] = 2          # existe, admitido, y es otro texto
    escribir(casos, [desplazado])

    r = verificar(casos, indice)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "DESPLAZADO: oro-001" in r.stdout
    assert "desplazado=1" in r.stdout
    assert "no_existe=0" in r.stdout, "un desplazado no es un inexistente: son dos averias distintas"


def test_un_oro_que_sale_de_practicas_sale_en_rojo(tmp_path):
    """La circularidad. El par apunta a un fragmento que existe, esta admitido y cuyo hash cuadra:
    todo verde salvo que ese texto ES la pregunta. El recall saldria perfecto sin merito."""
    casos, indice = juguete(tmp_path, [par("oro-001", PRACTICAS, 1)])
    r = verificar(casos, indice)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "CIRCULAR: oro-001" in r.stdout
    assert "circular=1" in r.stdout
    assert "desplazado=0" in r.stdout, "el circular no puede depender de que ademas falle el hash"


def test_un_oro_de_un_documento_que_la_puerta_del_1_4_tira_sale_en_rojo(tmp_path):
    """La guia de estilo la excluye admitir.py por el nombre. Si manana esa regla cambiara alla,
    este test cambia aqui: es la senal de que las dos piezas siguen atadas."""
    assert admitir.juzgar_documento(ESTILO, [fragmento(ESTILO, 1)]), \
        "el documento plantado tiene que caerse por la puerta, o el test no prueba nada"
    casos, indice = juguete(tmp_path, [par("oro-001", ESTILO, 1)])
    r = verificar(casos, indice)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "NO ADMITIDO: oro-001" in r.stdout
    assert "documento:" in r.stdout
    assert "no_admitido=1" in r.stdout


def test_un_oro_cuyo_fragmento_no_es_prosa_docente_sale_en_rojo(tmp_path):
    """Nivel fragmento, no documento: el documento entra y el trozo concreto no. El criterio de
    cierre pide los 100 'admitidos', y admitido se comprueba en los dos niveles."""
    volcado = ("Get:1 http://deb.debian.org/debian buster/main amd64 perl all 5.28.1-6 [2873 kB]\n"
               "Setting up perl-modules-5.28 (5.28.1-6) ...\n"
               "Unpacking libgdbm6:amd64 (1.18.1-4) ...\n"
               "Reading package lists...\n")
    assert admitir.juzgar_fragmento({"tipo_contenido": "explicacion", "texto": volcado}), \
        "el texto plantado tiene que caerse por la puerta, o el test no prueba nada"

    indice = escribir(tmp_path / "corpus" / "fragmentos.jsonl",
                      [fragmento(APUNTES, 1), fragmento(APUNTES, 2), fragmento(APUNTES, 3),
                       {"documento": APUNTES, "orden": 4, "asignatura": "juguete",
                        "tipo_contenido": "explicacion", "texto": volcado}])
    casos = escribir(tmp_path / "evals" / "casos" / "oro.jsonl",
                     [{"id": "oro-001", "conjunto": "oro_recuperacion", "asignatura": "juguete",
                       "pregunta": "¿Y esto?", "localizacion": "lectura",
                       "fragmento_oro": {"documento": APUNTES, "orden": 4,
                                         "hash_texto": hashlib.sha256(
                                             volcado.encode("utf-8")).hexdigest()}}])
    r = verificar(casos, indice)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "NO ADMITIDO: oro-001" in r.stdout
    assert "fragmento:" in r.stdout


def test_una_asignatura_declarada_que_no_es_la_del_fragmento_sale_en_rojo(tmp_path):
    casos, indice = juguete(tmp_path, [par("oro-001", APUNTES, 1, asignatura="otra-cosa")])
    r = verificar(casos, indice)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "DISCREPANTE: oro-001" in r.stdout
    assert "discrepante=1" in r.stdout


def test_un_par_sin_hash_texto_sale_con_2_y_no_finge_verde(tmp_path):
    """Un fichero de casos sin ancla no es un fichero de casos correcto: es uno de antes del ancla.
    Si esto pasara en verde, la puerta se apagaria sola el dia que alguien regenere el jsonl."""
    p = par("oro-001", APUNTES, 1)
    del p["fragmento_oro"]["hash_texto"]
    casos, indice = juguete(tmp_path, [p])
    r = verificar(casos, indice)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "MAL FORMADO" in r.stderr
    assert "hash_texto" in r.stderr


def test_sin_indice_sale_con_2_y_no_con_1(tmp_path):
    """En CI no hay corpus (ADR 0001). 'No he podido leer el indice' NO es 'el oro esta mal':
    confundirlos convertiria la ausencia del corpus en un hallazgo de integridad."""
    casos, _ = juguete(tmp_path, [par("oro-001", APUNTES, 1)])
    r = verificar(casos, tmp_path / "corpus" / "no_existe.jsonl")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "INDICE ILEGIBLE" in r.stderr


def test_la_puerta_del_1_4_se_importa_no_se_reimplanta():
    """Principio 6 al reves: el que comprueba no puede divergir en silencio del que produce. Una
    copia de las reglas de admision aqui daria verde el dia que cambien en admitir.py."""
    assert verificar_oro.admitir is admitir


# --- capa anclada al corpus real ---------------------------------------------------------------

@sin_corpus
def test_los_100_pares_reales_estan_en_verde():
    """El criterio de cierre del 3.0, cláusula a cláusula: existen, estan admitidos, ninguno sale
    de practicas/ y ninguno se ha desplazado desde que se etiquetaron."""
    r = verificar(CASOS, FRAGMENTOS)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "pares=100" in r.stdout
    assert ("ocurrencias=0 en 0 de 5 clases no_existe=0 desplazado=0 no_admitido=0 "
            "circular=0 discrepante=0") in r.stdout


@sin_corpus
def test_el_corpus_real_tiene_practicas_asi_que_la_clase_circular_no_es_vacua():
    """Sin esto, 'circular=0' podria significar 'no hay de donde colarse'. Habia 18 documentos bajo
    practicas/ cuando se etiquetaron los pares: la comprobacion tiene de que agarrarse."""
    documentos = {json.loads(x)["documento"]
                  for x in FRAGMENTOS.read_text(encoding="utf-8").split("\n") if x.strip()}
    assert len([d for d in documentos if "/practicas/" in d]) >= 18


@sin_corpus
def test_un_par_real_desplazado_a_su_fragmento_vecino_pone_la_puerta_en_rojo(tmp_path):
    """El rojo tambien anclado sobre el corpus de verdad, no solo sobre el juguete: se copia el
    fichero de casos, se mueve UN par al fragmento siguiente del mismo documento -que existe y
    esta admitido- y la puerta tiene que cazarlo por el texto."""
    pares = [json.loads(x) for x in CASOS.read_text(encoding="utf-8").split("\n") if x.strip()]
    pares[0]["fragmento_oro"]["orden"] += 1
    copia = escribir(tmp_path / "oro_desplazado.jsonl", pares)

    r = verificar(copia, FRAGMENTOS)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "DESPLAZADO: oro-001" in r.stdout
    assert "desplazado=1" in r.stdout
    assert "no_existe=0" in r.stdout


@sin_corpus
def test_el_unico_oro_repetido_es_el_declarado():
    """La regla de fragmento unico del 3.0 admite un oro repetido en dos preguntas y lo declara:
    04-SpringWebRest.md orden 11 explica @RestController y @Repository en el mismo trozo. Se
    ancla para que un repetido NUEVO, que ya no estaria declarado en ningun sitio, se vea."""
    pares = [json.loads(x) for x in CASOS.read_text(encoding="utf-8").split("\n") if x.strip()]
    cuenta = {}
    for p in pares:
        clave = (p["fragmento_oro"]["documento"], p["fragmento_oro"]["orden"])
        cuenta[clave] = cuenta.get(clave, 0) + 1
    repetidos = {k: n for k, n in cuenta.items() if n > 1}
    assert repetidos == {
        ("corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-02/springboot/"
         "04-SpringWebRest.md", 11): 2}


@sin_corpus
def test_el_reparto_por_localizacion_es_el_que_declara_el_metodo():
    """19 y 81. El 3.5 reporta recall@6 y nDCG@5 por separado en los dos subconjuntos, asi que si
    el reparto cambiara sin tocar el .md, la medida del sesgo se estaria comparando contra una
    composicion que ya no es la que el metodo declara."""
    pares = [json.loads(x) for x in CASOS.read_text(encoding="utf-8").split("\n") if x.strip()]
    reparto = {}
    for p in pares:
        reparto[p["localizacion"]] = reparto.get(p["localizacion"], 0) + 1
    assert reparto == {"busqueda": 19, "lectura": 81}
