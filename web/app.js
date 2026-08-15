// La vista del alumno (encargo 2.4). Sin framework: fetch, un lector de SSE de veinte líneas y DOM.
//
// LO QUE ESTE FICHERO NO HACE, Y ES SU REGLA: no dibuja nada que no haya llegado del servidor. No
// hay temporizadores, no hay barra que avance sola, no hay "pensando..." puesto a mano. Cada línea
// de la lista de etapas viene de un evento `etapa` con su milisegundo medido, y esos mismos
// milisegundos se guardan en `respuestas.etapas`. Si una etapa no ocurre, no se dibuja.

// `dibujarAfirmacion` y `dibujarVeredicto` YA NO SE IMPORTAN AQUÍ: la vista del alumno no pinta
// tipos ni veredictos. Siguen exportadas en `render.js` porque `/estilos` las usa, que es donde se
// comprueba que los cinco tipos se distinguen a un metro.
import { dibujarEtapa, dibujarAbstencion, dibujarReintento } from "/estatico/render.js";

const $ = (id) => document.getElementById(id);

//: Las asignaturas de la titulacion elegida, tal como las devolvio la puente. Se
//: guardan porque la etiqueta del desplegable ya no las lleva dentro: el <option>
//: solo tiene el nombre y el resto -codigo, curso, horas, norma, fragmentos- se
//: pinta debajo al elegir. Sin esta lista habria que volver a pedirlas por cada
//: cambio de seleccion, que es una peticion por clic para dato que ya esta aqui.
let asignaturasCargadas = [];

// EL TOKEN COMPARTIDO (0.3). La instancia de la sesion se publica por un tunel, o sea en internet,
// y /consulta gasta saldo del proveedor. El token llega en la URL -?t=...-, se guarda en la pestana
// y se quita de la barra de direcciones para que no viaje en capturas ni en el historial.
//
// Se guarda en sessionStorage y NO en localStorage a proposito: dura lo que dura la pestana. Un
// token de demo que sobrevive en el portatil de quien pasaba por ahi es la mitad del problema que
// esto viene a resolver.
const TOKEN = (() => {
  const url = new URL(location.href);
  const enLaUrl = url.searchParams.get("t");
  if (enLaUrl) {
    sessionStorage.setItem("veridica_token", enLaUrl);
    url.searchParams.delete("t");
    history.replaceState(null, "", url.pathname + url.search + url.hash);
    return enLaUrl;
  }
  return sessionStorage.getItem("veridica_token") || "";
})();

// Todas las peticiones pasan por aqui. Si manana alguien anade una llamada suelta con `fetch`, se
// queda sin cabecera y da 401 en la primera prueba: falla ruidoso, que es lo que se quiere.
function conToken(cabeceras = {}) {
  return TOKEN ? { ...cabeceras, "X-Veridica-Token": TOKEN } : cabeceras;
}

async function json(url) {
  const r = await fetch(url, { headers: conToken() });
  if (r.status === 401) throw new Error(
    "401: esta instancia pide token. Abre el enlace completo que te han dado, el que lleva ?t=...");
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.json();
}

async function cargarSelector() {
  const { titulaciones } = await json("/titulaciones");
  $("titulacion").innerHTML = titulaciones
    .map((t) => `<option value="${t}">${t.toUpperCase()}</option>`).join("");
  await recargarAsignaturas();
}

//: EL CONTADOR DE PETICIONES, QUE ARREGLA UNA CARRERA REAL. Dos cambios de titulación seguidos
//: lanzan dos peticiones, y si la primera tarda más que la segunda **contesta la última y gana la
//: PRIMERA**: el desplegable acaba con las asignaturas de una titulación que ya no está elegida.
//: No falla nada, no hay error que leer, y a partir de ahí se consulta con la puente cruzada.
let peticionDeAsignaturas = 0;

//: DE QUÉ TITULACIÓN SON LAS ASIGNATURAS QUE HAY AHORA EN EL DESPLEGABLE. No es lo mismo que
//: `$("titulacion").value`, y esa diferencia es justo el agujero: el `<select>` de titulación
//: cambia de valor **en el mismo instante** en que el alumno lo toca, y las asignaturas tardan lo
//: que tarde la red. En esa ventana la pantalla enseña "ASIR" arriba con las asignaturas de DAW
//: debajo, y pulsar Preguntar manda un par que no existe.
let titulacionDeLaLista = null;
//: La carga en vuelo, para poder ESPERARLA en vez de rechazar la consulta por una carrera.
let cargaEnVuelo = null;

// TODA carga pasa por aqui, para que `cargaEnVuelo` no dependa de que quien llame se acuerde
// de registrarla. Tres sitios llaman a esto y bastaba con que uno se olvidara.
function recargarAsignaturas() {
  cargaEnVuelo = cargarAsignaturas().finally(() => { cargaEnVuelo = null; });
  return cargaEnVuelo;
}

async function cargarAsignaturas() {
  const t = $("titulacion").value;
  const mia = ++peticionDeAsignaturas;
  titulacionDeLaLista = null;         // desde ya: lo que hay en el desplegable no es de nadie
  let asignaturas;
  try {
    ({ asignaturas } = await json(`/asignaturas?titulacion=${encodeURIComponent(t)}`));
  } catch (e) {
    // SIN ESTE `catch`, LA LISTA VIEJA SE QUEDA EN PANTALLA Y NADIE SE ENTERA. `cargarSelector`
    // tenía su `.catch` para la carga inicial, pero el `change` colgaba la promesa desnuda del
    // listener: un fallo aquí era un rechazo no capturado, o sea **cero señal** — y el alumno
    // seguía viendo asignaturas de la titulación anterior con otra elegida arriba. Es un `false`
    // persistido con otra cara: la pantalla afirmando un estado que ya no es cierto.
    $("asignatura").innerHTML = "";
    asignaturasCargadas = [];
    $("detalle-asignatura").textContent =
      `No se han podido cargar las asignaturas de ${t.toUpperCase()}: ${e.message}. `
      + "La lista se vacía a propósito: dejar la anterior sería consultar la titulación equivocada.";
    return;
  }
  if (mia !== peticionDeAsignaturas) return;   // llegó tarde: manda la última elección, no esta
  asignaturasCargadas = asignaturas;
  // Todo lo normativo -nombre, curso, horas- sale de la fila de la PUENTE, o sea de la norma de la
  // titulación que pregunta, y no de la titulación dueña de la fila. El curso y las horas son nulos
  // en DAM y ASIR porque no hay orden de currículo suya, y eso se dice en vez de inventarse un 1.
  // LA ETIQUETA SE ACORTA AL NOMBRE, Y LA EVIDENCIA SE REUBICA -NO SE BORRA-. El desplegable
  // llevaba codigo, nombre, curso, horas, norma, transversalidad y numero de fragmentos en una
  // sola linea: eso es la prueba de que el corpus es real y esta trazado al BOE, y por eso NO
  // desaparece; pero dentro de un <option> es ilegible y es lo primero que ve alguien que llega.
  // Va a la linea secundaria de debajo, que se rellena al elegir. Reubicar, no eliminar.
  $("asignatura").innerHTML = asignaturas
    .map((a) => `<option value="${a.id}">${a.nombre}</option>`).join("");
  titulacionDeLaLista = t;
  detalleAsignatura();
}

// LA MISMA COMPROBACIÓN QUE HACE EL SERVIDOR, HECHA ANTES DE MANDAR — y no es duplicarla: es no
// mandar a sabiendas algo que se sabe malo.
//
// **Sí, la interfaz PUEDE producir el par imposible**, aunque el desplegable solo ofrezca las
// asignaturas de la titulación elegida: entre que se cambia la titulación y llegan sus asignaturas
// hay una ventana —milisegundos en local, lo que sea por un túnel— en la que arriba pone una cosa y
// abajo siguen las opciones de la otra. Pulsar Preguntar ahí manda `(titulacion nueva, asignatura
// vieja)`.
//
// No se arregla con un plazo ni con un `disabled` que alguien pueda saltarse: se arregla
// comprobando que la lista que hay en pantalla ES de la titulación elegida, que es un hecho y no
// una carrera. Y si la carga está en vuelo, se ESPERA en vez de rechazar: la consulta del alumno no
// tiene la culpa de que la red vaya lenta.
async function parCoherente() {
  if (cargaEnVuelo) { try { await cargaEnVuelo; } catch { /* su propio catch ya avisó */ } }
  const t = $("titulacion").value;
  if (titulacionDeLaLista !== t) {
    return `las asignaturas de ${t.toUpperCase()} todavía no han cargado. Vuelve a intentarlo: `
      + "no se manda una consulta con una asignatura que quizá no sea de tu titulación.";
  }
  const id = $("asignatura").value;
  if (id && !(asignaturasCargadas || []).some((a) => String(a.id) === id)) {
    return `la asignatura elegida no es de ${t.toUpperCase()}.`;
  }
  return null;
}

//: La procedencia normativa de la asignatura elegida, en la linea de debajo del selector.
function detalleAsignatura() {
  const destino = $("detalle-asignatura");
  if (!destino) return;
  const t = $("titulacion").value;
  const a = (asignaturasCargadas || []).find((x) => String(x.id) === $("asignatura").value);
  if (!a) { destino.textContent = ""; return; }
  const partes = [a.codigo];
  partes.push(a.curso ? `${a.curso}.º curso` : "curso sin declarar");
  if (a.horas) partes.push(`${a.horas} h`);
  if (a.norma) partes.push(a.norma);
  if (a.transversal) partes.push(`transversal · la fila vive en ${a.titulacion_duena.toUpperCase()}`);
  partes.push(`${a.fragmentos} fragmentos indexados`);
  destino.textContent = partes.join(" · ");
  destino.title = `Datos normativos de ${a.nombre} en ${t.toUpperCase()}`;
}

// --- lector de SSE ------------------------------------------------------------------------------

async function* eventos(respuesta) {
  const lector = respuesta.body.getReader();
  const decodificador = new TextDecoder();
  let resto = "";
  while (true) {
    const { value, done } = await lector.read();
    if (done) break;
    resto += decodificador.decode(value, { stream: true });
    const bloques = resto.split("\n\n");
    resto = bloques.pop();
    for (const bloque of bloques) {
      const nombre = (bloque.match(/^event: (.+)$/m) || [])[1];
      const datos = (bloque.match(/^data: (.+)$/m) || [])[1];
      if (nombre && datos) yield [nombre, JSON.parse(datos)];
    }
  }
}

async function abrirFragmento(respuestaId, fragmentoId, caja) {
  if (caja.querySelector(".fragmento")) return;
  const contenedor = document.createElement("div");
  contenedor.className = "fragmento";
  try {
    const f = await json(`/respuestas/${respuestaId}/fragmentos/${fragmentoId}`);
    contenedor.textContent = `${f.codigo} ${f.asignatura} · ${f.unidad || "sin unidad"}\n`
      + `${f.documento}\n\n${f.texto}`;
  } catch (e) {
    contenedor.textContent = `No se puede abrir: ${e.message}`;
  }
  caja.appendChild(contenedor);
}

// --- la consulta --------------------------------------------------------------------------------

// EL RESPALDO, que existe porque las etapas son carga estructural y no adorno: con 601 ms de
// adelanto en una consulta y 11 ms en otra, lo que cubre la espera son ellas y no el goteo de
// letras. Si el evento `etapa` no llegara, la pantalla se quedaría muerta entre 1,6 y 2,2 segundos
// delante del cliente. Así que el navegador dibuja SU PROPIA etapa, que es un hecho que él sí
// conoce -acaba de enviar la petición- y va marcada como medida en el cliente, no en el servidor.
// No es relleno: es un evento real con su reloj real, y por eso no rompe la regla de arriba.
function etapaDelCliente(texto, ms) {
  const li = document.createElement("li");
  li.className = "viva del-cliente";
  li.dataset.origen = "cliente";
  const izquierda = document.createElement("span");
  izquierda.textContent = texto;
  const derecha = document.createElement("span");
  derecha.className = "ms";
  derecha.textContent = `${Math.round(ms)} ms · medido aquí`;
  li.append(izquierda, derecha);
  return li;
}

// --- los turnos (acabado d1) ---------------------------------------------------------------------
//
// EL DIBUJO DEL SSE NO SE TOCA, Y ESTA ES LA PIEZA QUE LO PERMITE. En vez de reescribir dónde
// escriben `dibujarEtapa`, `dibujarAfirmacion` y compañía, se les deja el mismo sitio: el turno VIVO
// es el único que lleva los cuatro ids (`etapas`, `prosa`, `respuesta`, `pie`). Al preguntar de
// nuevo, el turno anterior los SUELTA -pasa a llevarlos en `data-era`- y se queda como historia, y
// el turno nuevo los toma. Cero cambios en el lector de eventos, que es lo que (d2) sí va a tocar y
// por eso va en su propio commit.
const IDS_DEL_TURNO_VIVO = ["tira", "tira-viva", "etapas", "recuperados", "prosa", "respuesta",
                            "pie"];

// (d2) LA LÍNEA VIVA DE LA TIRA. Traduce el nombre técnico de la etapa a lo que está pasando, en
// una línea que se reescribe según llegan. La tira plegada NO puede quedarse muda justo cuando más
// impresiona: la evidencia está presente y callada, en vez de ausente.
//
// Y ES UN DICCIONARIO Y NO UN `replace` DE GUIONES BAJOS a propósito: `contrato_validado` no le dice
// nada a un alumno, y "verificando" sí. Una etapa sin entrada aquí cae a su nombre técnico, que es
// feo pero honesto — mejor que inventarle una frase bonita a algo que no sabemos qué es.
const ETIQUETA_VIVA = {
  peticion_enviada: "enviando tu pregunta",
  consulta_embebida: "entendiendo la pregunta",
  sin_embebedor: "buscando solo por palabras",
  recuperacion_lexica: "buscando por palabras",
  recuperacion_vectorial: "buscando por significado",
  glosario: "consultando el glosario",
  fusion: "ordenando lo encontrado",
  fragmentos_recuperados: "temario recuperado",
  segunda_recuperacion: "buscando en el resto de tu titulación",
  sin_recuperacion: "sin temario: se responde y se dice",
  primer_token_proveedor: "redactando",
  primera_prosa: "escribiendo la respuesta",
  contrato_validado: "verificando lo que ha escrito",
};

function actualizarTira(etapa, cuantas) {
  const viva = $("tira-viva");
  if (!viva) return;
  const que = ETIQUETA_VIVA[etapa.nombre] || etapa.nombre;
  viva.textContent = `${que} · ${Math.round(etapa.ms)} ms`;
  viva.dataset.cuantas = cuantas;
}

// LOS FRAGMENTOS SE SACAN DE SU ETAPA Y SE SUBEN AL TURNO. `dibujarEtapa` no se toca -sigue
// construyendo el <li> igual, y la etapa sigue dentro de la tira con su milisegundo-: lo que se
// mueve es el NODO de la lista de fragmentos, que es contenido de producto y no puede vivir dentro
// de la evidencia plegada.
function subirFragmentos(li, etapa) {
  const lista = li.querySelector(".fragmentos-recuperados");
  const destino = $("recuperados");
  if (!lista || !destino) return;
  destino.innerHTML = "";
  const cabecera = document.createElement("summary");
  const n = (etapa.fragmentos || []).length;
  const deOtra = (etapa.fragmentos || []).filter((f) => f.asignatura);
  cabecera.textContent = `${n} fragmentos de tu temario`
    + (deOtra.length ? ` · ${deOtra.length} de ${deOtra[0].asignatura}` : "");
  destino.append(cabecera, lista);
}

function nuevoTurno(pregunta) {
  const vivo = $("turno-vivo");
  if (vivo) {
    // El turno que deja de ser el vivo suelta los ids: dos elementos con el mismo id harían que
    // `getElementById` devolviera el primero -el viejo- y la respuesta nueva se escribiría en el
    // turno anterior sin que nada fallara. Es un id duplicado comportándose como un selector que no
    // casa con lo que crees.
    for (const id of IDS_DEL_TURNO_VIVO) {
      const e = document.getElementById(id);
      if (e) { e.dataset.era = id; e.removeAttribute("id"); }
    }
    vivo.removeAttribute("id");
    if (!vivo.textContent.trim()) vivo.remove();   // el turno de arranque, que nunca se usó
  }
  const conversacion = $("conversacion");
  const delAlumno = document.createElement("article");
  delAlumno.className = "turno turno-alumno";
  delAlumno.textContent = pregunta;
  const delSistema = document.createElement("article");
  delSistema.className = "turno turno-sistema";
  delSistema.id = "turno-vivo";
  delSistema.innerHTML = '<details class="tira" id="tira">'
    + '<summary id="tira-viva">esperando…</summary>'
    + '<ul class="etapas" id="etapas"></ul>'
    + '<div class="pie" id="pie"></div></details>'
    + '<details class="recuperados" id="recuperados" open></details>'
    + '<div class="prosa" id="prosa"></div><div id="respuesta"></div>';
  conversacion.append(delAlumno, delSistema);
  delAlumno.scrollIntoView({ behavior: "smooth", block: "start" });
}

// --- (1.1) el estado vacío, (1.2) los ajustes de desarrollo y (1.3) la barra ---------------------

// LAS CUATRO SUGERIDAS SE LEEN DE UN FICHERO Y NO SE ESCRIBEN AQUÍ. Son curación declarada: cada
// una sale de un conjunto congelado o del oro, y `scripts/curar_sugeridas.py` comprueba contra la
// configuración VIVA que la recuperación hace con ellas lo que se espera. Escritas a mano en el
// HTML, ese script no tendría qué comprobar y la comprobación se volvería un documento.
async function pintarSugeridas() {
  const caja = $("sugeridas");
  if (!caja) return;
  let sugeridas;
  try {
    sugeridas = await json("/estatico/sugeridas.json");
  } catch {
    // Sin sugeridas se sigue pudiendo preguntar: el estado vacío pierde su mejor parte, no la
    // pantalla. Se dice en vez de dejar un hueco mudo.
    caja.textContent = "No se han podido cargar las preguntas de ejemplo. Escribe la tuya abajo.";
    return;
  }
  for (const s of sugeridas) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = `sugerida forma-${s.forma}`;
    // EL CONTEXTO VA EN LA TARJETA Y NO EN LA PREGUNTA, y esa separación es el punto: el texto de
    // la pregunta es el LITERAL del conjunto congelado —es lo que se midió y retocarlo cambia el
    // embedding lo bastante como para cruzar un umbral—, así que lo que hace falta saber para
    // entenderla se dice al lado, no dentro.
    b.innerHTML = `<span class="que-ensena">${s.etiqueta}</span>`
      + `<span class="pregunta"></span><span class="contexto"></span>`
      + `<span class="para-que"></span>`;
    b.querySelector(".pregunta").textContent = s.texto;
    b.querySelector(".contexto").textContent = s.contexto || "";
    b.querySelector(".para-que").textContent = s.ensena;
    // UN CLIC PONE LOS SELECTORES Y **ENVÍA**, y esto corrige la primera versión, que solo dejaba
    // la pantalla lista. El razonamiento de entonces —"enviar sería decidir por quien mira"— era
    // razonable y **el propietario lo probó y no funcionaba**: el único efecto visible de pinchar
    // era rellenar un `<input>` que vive FIJO ABAJO, fuera de donde estabas mirando. Desde una
    // tarjeta en mitad de la página, eso es *"pincho y no pasa absolutamente nada"*, que es lo peor
    // que puede hacer el primer clic de una demo. Un botón que parece un botón, envía.
    b.addEventListener("click", () => elegirSugerida(s));
    caja.appendChild(b);
  }
}

// PONER UN `<select>` A UN VALOR QUE NO EXISTE **NO FALLA: NO HACE NADA**, y el resultado es la
// consulta saliendo con otra asignatura sin que nada se ponga rojo. Es la familia del patrón que
// no casa y devuelve éxito, dentro del DOM. Así que se asigna y se COMPRUEBA que la asignación
// tomó, con el nombre de lo que se buscaba en el mensaje.
function ponerSelector(id, valor) {
  const select = $(id);
  select.value = String(valor);
  if (select.value !== String(valor)) {
    throw new Error(
      `no existe la opción ${valor} en ${id}: la consulta habría salido con «${select.value}»`);
  }
}

// EL CLIC DE UNA SUGERIDA, ENTERO Y CON SUS COMPROBACIONES.
//
// Cada sugerida declara su titulación y su asignatura, y el par (titulación, asignatura) lo
// **valida el servidor con un 400** desde el encargo de la cascada. O sea que si el clic no mueve
// los selectores, la consulta sale con el par cruzado y el servidor la rechaza — haciendo bien su
// trabajo. Aquí se ponen los dos, en orden y esperando a que la lista de asignaturas se recargue,
// y si algo no cuadra **se dice en pantalla** en vez de mandar una consulta que se sabe mala.
async function elegirSugerida(s) {
  const antes = {
    titulacion: $("titulacion").value,
    asignatura: ($("asignatura").selectedOptions[0] || {}).textContent || null,
  };
  try {
    if (s.titulacion && $("titulacion").value !== s.titulacion) {
      ponerSelector("titulacion", s.titulacion);
      await recargarAsignaturas();    // la lista de asignaturas es de la titulación: primero esto
    }
    ponerSelector("asignatura", s.asignatura_id);
    ponerSelector("modo", s.modo);
    detalleAsignatura();
    $("texto").value = s.texto;
  } catch (e) {
    avisar(`No se ha podido preparar esa pregunta: ${e.message}`);
    return;
  }
  // **CAMBIAR EN SILENCIO QUÉ CICLO CURSA EL ALUMNO ES DE LA MISMA FAMILIA QUE TODO LO DEMÁS.**
  // Estando en ASIR, pulsar una sugerida de DAW te movía a DAW sin decir nada: la pantalla
  // afirmando algo que quien mira no ha decidido, y encima sobre el dato que decide con qué
  // temario se responde. Se dice, con su motivo, y donde se está mirando.
  const ahora = ($("asignatura").selectedOptions[0] || {}).textContent || "";
  if (antes.titulacion !== $("titulacion").value || antes.asignatura !== ahora) {
    cambioDeAsignatura = `Para esta pregunta he cambiado a ${$("titulacion").value.toUpperCase()}`
      + ` · ${ahora}, que es de donde sale la sugerencia`
      + (antes.asignatura ? ` (estabas en ${antes.titulacion.toUpperCase()} · ${antes.asignatura})` : "")
      + ".";
  }
  await enviar();
}

//: Lo que hay que contar en el turno que viene, si es que hubo cambio. Se guarda en vez de
//: pintarse aquí porque el turno todavía no existe: lo crea `enviar()`.
let cambioDeAsignatura = null;

//: De qué fragmentos se apoya el turno en curso, y sus veredictos. Ya no se pintan: el alumno ve
//: la consecuencia y el panel enseña el mecanismo.
let citasDelTurno = [];
let veredictosDelTurno = [];

//: **EL LÍMITE DE LA MARCA, DECLARADO, porque es fácil leerla como algo más preciso de lo que es.**
//:
//: La marca dice *"esta frase va respaldada"* —eso lo decide el portero, frase a frase, y es
//: exacto— y al pulsarla se abre **el temario en el que se apoya la respuesta**, no el fragmento
//: concreto de esa frase. La diferencia importa y por eso el texto del enlace lo dice así.
//:
//: El motivo no es pereza: el portero mide el solape contra el vocabulario de **todas** las
//: afirmaciones juntas, así que sabe SI una frase está cubierta pero no CUÁL la cubre. Sacar el
//: argmax por afirmación sería un cálculo nuevo dentro de un mecanismo cuyo umbral está barrido y
//: publicado, y hacerlo de madrugada antes de una sesión es exactamente cómo se rompe algo medido.
//: El anclaje frase→fragmento es trabajo del bloque 2, que va precisamente de anclar afirmaciones a
//: su ventana.
function pintarCitas(respuestaId) {
  if (!citasDelTurno.length || !respuestaId) return;
  const p = document.createElement("p");
  p.className = "citas-del-turno";
  const enlace = document.createElement("a");
  enlace.href = "#";
  enlace.textContent = citasDelTurno.length === 1
    ? "Ver el fragmento del temario en el que se apoya"
    : `Ver los ${citasDelTurno.length} fragmentos del temario en los que se apoya`;
  enlace.addEventListener("click", (ev) => {
    ev.preventDefault();
    for (const id of citasDelTurno) abrirFragmento(respuestaId, id, p);
  });
  p.appendChild(enlace);
  $("respuesta").appendChild(p);
}

//: **EL PANEL, QUE ES SOBRE TODO CABLEADO.** `/trazas/{id}` existe desde el 2.5 y contesta a las
//: cuatro preguntas de su enunciado —qué se recuperó, qué se afirmó, qué veredicto tuvo cada
//: afirmación **y con qué instrumento**, cuánto costó cada etapa— leyendo lo persistido. Lo único
//: que faltaba era un enlace por turno.
function pintarComoLoHeComprobado(respuestaId) {
  if (!respuestaId) return;
  const p = document.createElement("p");
  p.className = "como-lo-he-comprobado";
  const enlace = document.createElement("a");
  enlace.href = `/trazas/${respuestaId}`;
  enlace.target = "_blank";
  enlace.rel = "noopener";
  const marcadas = veredictosDelTurno.filter((v) => v.veredicto && v.veredicto !== "verificada");
  enlace.textContent = "Cómo lo he comprobado"
    + (veredictosDelTurno.length
      ? ` · ${veredictosDelTurno.length} comprobaciones`
        + (marcadas.length ? `, ${marcadas.length} con reparos` : "")
      : "");
  p.appendChild(enlace);
  $("respuesta").appendChild(p);
}

// UN SITIO DONDE DECIR LO QUE VA MAL, Y QUE SE VEA. "No pasa nada" nunca es un estado: o hay un
// fallo y se dice, o no lo hay.
function avisar(texto) {
  const caja = document.createElement("div");
  caja.className = "aviso-de-fallo";
  caja.textContent = texto;
  $("conversacion").appendChild(caja);
  caja.scrollIntoView({ behavior: "smooth", block: "center" });
}

// (1.3) La barra: qué está elegido, en una línea, y a un clic de cambiarlo.
function resumenDeAjustes() {
  const asignatura = $("asignatura").selectedOptions[0];
  return [$("titulacion").value.toUpperCase(),
          asignatura ? asignatura.textContent : "sin asignatura",
          $("modo").value].join(" · ");
}

function pintarBarra() {
  const barra = $("barra-ajustes");
  if (barra && !barra.hidden) $("barra-texto").textContent = resumenDeAjustes();
}

// LA ENTRADA SE MUEVE, NO SE DUPLICA. Dos cajas de texto serían dos estados que hay que mantener
// iguales, y la que no se usara se quedaría con lo escrito antes. Es **el mismo `<form>`**: al
// entrar vive dentro de la bienvenida, junto al contenido; al empezar la conversación baja a su
// sitio fijo, que es donde la busca quien ya está conversando.
function colocarEntradaArriba() {
  const hueco = $("entrada-arriba");
  if (hueco) hueco.appendChild($("preguntar"));
}

// La conversación ha empezado: el estado vacío se va y los ajustes se compactan.
function conversacionEmpezada() {
  const bienvenida = $("bienvenida");
  if (bienvenida) {
    document.body.appendChild($("preguntar"));   // primero la entrada, o se iría con la bienvenida
    bienvenida.remove();
  }
  const barra = $("barra-ajustes");
  if (barra && barra.hidden) {
    barra.hidden = false;
    document.body.classList.add("con-conversacion");
    barra.addEventListener("click", () => {
      const abierto = document.body.classList.toggle("ajustes-abiertos");
      barra.setAttribute("aria-expanded", String(abierto));
    });
  }
  pintarBarra();
}

//: **LO QUE NO SE PUEDE CALLAR AL APILAR TURNOS, y es la condición de que esto sea honesto.**
//:
//: Los turnos apilados hacen que la pantalla se lea como una conversación, que es lo que faltaba.
//: Pero **este sistema NO tiene multiturno**: cada pregunta se responde sola, sin nada del contexto
//: de la anterior. Es un límite estructural, está declarado, y no va a estar para el lunes.
//:
//: Apilar los turnos para que PAREZCA un hilo y callarse eso sería que la pantalla afirme algo que
//: el sistema no hace — que es exactamente lo único que este proyecto no se permite, y encima en el
//: sitio donde más se cree: la forma. La forma comunica tanto como el texto, y una fila de burbujas
//: comunica "me acuerdo de lo anterior".
//:
//: Aparece **al llegar el segundo turno** y no antes, porque antes no hay hilo que malinterpretar.
//: Y una sola vez: repetirlo en cada turno sería ruido, y el aviso dejaría de leerse.
let turnosHechos = 0;

function avisarDeQueNoHayHilo() {
  if (turnosHechos !== 2 || $("sin-hilo")) return;
  const nota = document.createElement("p");
  nota.className = "sin-hilo";
  nota.id = "sin-hilo";
  nota.textContent = "Cada pregunta se responde por separado: esta no sabe nada de la anterior. "
    + "El hilo con memoria todavía no existe, y cuando exista se dirá.";
  $("conversacion").appendChild(nota);
}

async function preguntar(ev) {
  ev.preventDefault();
  await enviar();
}

async function enviar() {
  const texto = $("texto").value.trim();
  if (!texto) { $("texto").focus(); return; }
  // ANTES DE NADA: que el par (titulación, asignatura) sea de verdad posible. Si no lo es, no se
  // manda y se dice — que es lo contrario de mandarlo y enseñar un 400 que parece una negativa a
  // responder cuando en realidad es "esa asignatura no existe en esa titulación".
  const mal = await parCoherente();
  if (mal) { avisar(`No se ha enviado: ${mal}`); return; }
  $("enviar").disabled = true;
  conversacionEmpezada();
  turnosHechos += 1;
  nuevoTurno(texto);
  if (cambioDeAsignatura) {
    const nota = document.createElement("p");
    nota.className = "cambio-de-asignatura";
    nota.textContent = cambioDeAsignatura;
    $("turno-vivo").prepend(nota);
    cambioDeAsignatura = null;
  }
  avisarDeQueNoHayHilo();

  const cuerpo = {
    texto,
    asignatura_id: Number($("asignatura").value) || null,
    // La cascada del encargo de producto necesita saber POR QUE TITULACION se
    // pregunta: una transversal vive en varias, asi que deducirla del id daria la
    // equivocada justo en las que mas se comparten.
    titulacion: $("titulacion").value || null,
    modo: $("modo").value,
    verificacion: $("verificacion").checked,
  };

  citasDelTurno = [];
  veredictosDelTurno = [];
  let respuestaId = null;
  let etapasDelServidor = 0;
  const arranque = performance.now();
  $("etapas").appendChild(etapaDelCliente("petición enviada desde tu navegador", 0));
  try {
    const r = await fetch("/consulta", {
      method: "POST",
      headers: conToken({ "Content-Type": "application/json" }),
      body: JSON.stringify(cuerpo),
    });
    if (r.status === 401) throw new Error(
      "401: esta instancia pide token. Abre el enlace completo que te han dado, con ?t=...");
    if (!r.ok) throw new Error(`${r.status}: ${(await r.json()).detail}`);

    for await (const [nombre, datos] of eventos(r)) {
      if (nombre === "etapa") {
        etapasDelServidor += 1;
        for (const li of $("etapas").children) li.classList.remove("viva");
        const li = dibujarEtapa(datos);
        $("etapas").appendChild(li);
        // (d2): la etapa entera va a la tira -evidencia-, su linea resumida a la cabecera viva, y
        // los fragmentos suben fuera de la tira porque son producto.
        actualizarTira(datos, etapasDelServidor);
        subirFragmentos(li, datos);
      } else if (nombre === "token") {
        // LA PROSA LLEGA: el temario recuperado deja de ser lo unico que hay que mirar y se pliega
        // solo. No desaparece -sigue a un clic- y hasta este momento ha estado cubriendo la espera,
        // que es para lo que existe.
        const rec = $("recuperados");
        if (rec && rec.open && rec.children.length) rec.open = false;
        // EL PORTERO MARCA Y NO PODA (14/08): la frase sin respaldo LLEGA, y llega señalada. Se
        // pinta en su propio <span> con un símbolo delante y un `title` que dice qué significa —
        // por FORMA y no solo por color, como los cinco tipos de afirmación: en la pantalla de
        // alguien que no distingue rojos, el color solo sería no haber marcado nada.
        if (datos.respaldada === false) {
          const marca = document.createElement("span");
          marca.className = "sin-respaldo";
          marca.title = "Esta frase no está respaldada por ninguna afirmación declarada"
            + ` (solape ${datos.solape}). Se enseña marcada en vez de ocultarla.`;
          marca.textContent = `⚠ ${datos.t}`;
          $("prosa").appendChild(marca);
        } else {
          // LA FRASE RESPALDADA, MARCADA EN DISCRETO Y NO EN FICHA. El alumno ve la CONSECUENCIA
          // —"esto se apoya en el temario y puedes ir a verlo"— y no el mecanismo.
          const tramo = document.createElement("span");
          tramo.className = "respaldada";
          tramo.textContent = datos.t;
          $("prosa").appendChild(tramo);
        }
      } else if (nombre === "afirmaciones") {
        // LAS AFIRMACIONES DEJAN DE PINTARSE EN LA VISTA DEL ALUMNO (15/08/2026). Lo que se
        // guarda es de qué fragmentos se apoya la respuesta, que es lo que abre la marca.
        citasDelTurno = [...new Set((datos.afirmaciones || [])
          .filter((a) => a.fragmento_id).map((a) => a.fragmento_id))];
      } else if (nombre === "veredicto") {
        // EL VEREDICTO YA NO SE PINTA AQUÍ, y este es el giro de producto del 15/08.
        //
        // Estaba en línea porque "los veredictos son el producto", y llevado a la letra producía un
        // muro de «AFIRMACIÓN 1/2/3/4», «PARÁFRASIS DEL TEMARIO», «REINTENTO CON_SEÑAL» y «NO
        // VERIFICABLE» debajo de cuatro líneas de respuesta: jerga de máquina en la pantalla de un
        // alumno de segundo de FP. **El alumno ve la CONSECUENCIA; el panel enseña el MECANISMO.**
        //
        // NO es esconder los fallos: siguen ocurriendo, siguen contándose y siguen en la traza con
        // la firma de su instrumento. Lo que cambia es que el alumno lee *"esta frase no está
        // respaldada"* en vez del nombre interno de un veredicto.
        veredictosDelTurno.push(datos);
      } else if (nombre === "reintento") {
        // EL REINTENTO POR RITMO CAÍDO SE VE, no se disimula. Si ya había prosa, se marca como
        // retirada un instante y se vacía antes de la segunda pasada: el alumno tiene que entender
        // que ese texto ya no cuenta. Borrarlo a la callada le dejaría pensando que lo leyó mal.
        if (datos.ya_habia_prosa_en_pantalla) $("prosa").classList.add("retirada");
        $("respuesta").appendChild(dibujarReintento(datos));
        $("prosa").textContent = "";
        $("prosa").classList.remove("retirada");
      } else if (nombre === "abstencion") {
        if (datos.ya_habia_prosa_en_pantalla) $("prosa").classList.add("retirada");
        $("respuesta").appendChild(dibujarAbstencion(datos));
      } else if (nombre === "fin") {
        respuestaId = datos.respuesta_id;
        pintarCitas(respuestaId);
        pintarComoLoHeComprobado(respuestaId);
        pintarPie(datos);
      }
    }
  } catch (e) {
    // **UN FALLO SE VE, Y SE VE DONDE SE ESTABA MIRANDO.** Antes esto era un `textContent` suelto
    // dentro del turno: texto plano, sin marca, fácil de leer como parte de la respuesta o de no
    // leerlo. Un 400 de par cruzado o un 401 sin token tienen que ser inconfundibles, porque la
    // alternativa es lo que pasó el 15/08 — "pincho y no pasa absolutamente nada"—, y **"no pasa
    // nada" nunca es un estado del sistema: es un estado de la pantalla que no lo cuenta.**
    const caja = document.createElement("p");
    caja.className = "aviso-de-fallo";
    caja.textContent = `No se ha podido responder — ${e.message}`;
    $("respuesta").appendChild(caja);
    caja.scrollIntoView({ behavior: "smooth", block: "center" });
  } finally {
    $("enviar").disabled = false;
    if (etapasDelServidor === 0) {
      // Que el servidor no haya mandado NINGUNA etapa también es un hecho, y decirlo es mejor que
      // dejar la lista con una sola línea y aire de que todo fue bien.
      $("etapas").appendChild(etapaDelCliente(
        "el servidor no envió ninguna etapa: lo de arriba es lo único medido",
        performance.now() - arranque));
    }
  }
}

// `pintarAfirmaciones` VIVIÓ AQUÍ Y SE FUE EL 15/08/2026. Dibujaba una ficha por afirmación con su
// tipo, su veredicto y su referencia: el muro de «AFIRMACIÓN 1/2/3/4 · PARÁFRASIS DEL TEMARIO ·
// REINTENTO CON_SEÑAL» debajo de cuatro líneas de respuesta. **El alumno ve la consecuencia; el
// panel enseña el mecanismo.** Todo eso sigue existiendo, se sigue midiendo y se lee entero en
// `/trazas/{id}`, que lo tiene además con la firma del instrumento de cada veredicto.
//
// `dibujarAfirmacion` NO se borra de `render.js`: la muestra de estilos la usa, y esa muestra existe
// justo para comprobar que los cinco tipos se distinguen. Lo que cambia es quién la llama.

// EL PIE ES MECANISMO, ASÍ QUE SE VA A LA TIRA. Milisegundos, tokens y euros no son cosa del
// alumno: son cosa de quien mira cómo funciona esto. Sigue estando entero —no se borra ni un
// número— pero dentro de la evidencia plegada, junto a las etapas, que es donde vive su familia.
function pintarPie(d) {
  const eur = d.coste_eur === null || d.coste_eur === undefined
    ? "sin precios configurados" : `${d.coste_eur.toFixed(6)} €`;
  $("pie").innerHTML =
    `Primer carácter para ti: <b>${Math.round(d.ttft_prosa_ms || 0)} ms</b> · `
    + `primer token del modelo: <b>${Math.round(d.ttft_proveedor_ms || 0)} ms</b> · `
    + `total <b>${Math.round(d.total_ms)} ms</b> · ${d.tokens_entrada}+${d.tokens_salida} tokens · `
    // LA TRAZA DEJA DE SER UN NUMERO Y PASA A SER UN ENLACE (encargo 2.5): hasta hoy el pie
    // enseñaba el id de una traza que no se podia abrir, que es enseñar la referencia de algo que
    // no existe. `/trazas/{id}` contesta a las cuatro preguntas del enunciado.
    + `${eur} · <a href="/trazas/${d.respuesta_id}" target="_blank" rel="noopener">`
    + `traza ${d.respuesta_id}</a>`
    // EL INTERRUPTOR QUE NO HACE NADA SE SIGUE DICIENDO, y ahora con precision: antes esta linea
    // colgaba de `!construido` -o sea, se enseñaba porque la capa no existia- y al construirse la
    // fase 4 habria desaparecido llevandose el aviso. Lo que hay que declarar no es que falte la
    // capa: es que el interruptor pedido NO la apaga.
    + (d.verificacion && d.verificacion.solicitada === false
       && d.verificacion.solicitada_tiene_efecto === false
      ? " · verificación pedida: no, pero el interruptor todavía no la apaga (ablación: 7.3)"
      : "");
}

$("titulacion").addEventListener("change", async () => { await recargarAsignaturas(); pintarBarra(); });
$("asignatura").addEventListener("change", () => { detalleAsignatura(); pintarBarra(); });
$("modo").addEventListener("change", pintarBarra);
$("preguntar").addEventListener("submit", preguntar);
colocarEntradaArriba();
cargarSelector().catch((e) => avisar(`No se pudo cargar el selector: ${e.message}`));
pintarSugeridas();
$("texto").focus();
