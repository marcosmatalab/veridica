// La vista del alumno (encargo 2.4). Sin framework: fetch, un lector de SSE de veinte líneas y DOM.
//
// LO QUE ESTE FICHERO NO HACE, Y ES SU REGLA: no dibuja nada que no haya llegado del servidor. No
// hay temporizadores, no hay barra que avance sola, no hay "pensando..." puesto a mano. Cada línea
// de la lista de etapas viene de un evento `etapa` con su milisegundo medido, y esos mismos
// milisegundos se guardan en `respuestas.etapas`. Si una etapa no ocurre, no se dibuja.

import { dibujarAfirmacion, dibujarEtapa, dibujarAbstencion, dibujarReintento,
         dibujarVeredicto } from "/estatico/render.js";

const $ = (id) => document.getElementById(id);

//: Las asignaturas de la titulacion elegida, tal como las devolvio la puente. Se
//: guardan porque la etiqueta del desplegable ya no las lleva dentro: el <option>
//: solo tiene el nombre y el resto -codigo, curso, horas, norma, fragmentos- se
//: pinta debajo al elegir. Sin esta lista habria que volver a pedirlas por cada
//: cambio de seleccion, que es una peticion por clic para dato que ya esta aqui.
let asignaturasCargadas = [];

async function json(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.json();
}

async function cargarSelector() {
  const { titulaciones } = await json("/titulaciones");
  $("titulacion").innerHTML = titulaciones
    .map((t) => `<option value="${t}">${t.toUpperCase()}</option>`).join("");
  await cargarAsignaturas();
}

async function cargarAsignaturas() {
  const t = $("titulacion").value;
  const { asignaturas } = await json(`/asignaturas?titulacion=${encodeURIComponent(t)}`);
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
  detalleAsignatura();
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
const IDS_DEL_TURNO_VIVO = ["etapas", "prosa", "respuesta", "pie"];

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
  delSistema.innerHTML = '<ul class="etapas" id="etapas"></ul>'
    + '<div class="prosa" id="prosa"></div><div id="respuesta"></div>'
    + '<div class="pie" id="pie"></div>';
  conversacion.append(delAlumno, delSistema);
  delAlumno.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function preguntar(ev) {
  ev.preventDefault();
  $("enviar").disabled = true;
  nuevoTurno($("texto").value);

  const cuerpo = {
    texto: $("texto").value,
    asignatura_id: Number($("asignatura").value) || null,
    // La cascada del encargo de producto necesita saber POR QUE TITULACION se
    // pregunta: una transversal vive en varias, asi que deducirla del id daria la
    // equivocada justo en las que mas se comparten.
    titulacion: $("titulacion").value || null,
    modo: $("modo").value,
    verificacion: $("verificacion").checked,
  };

  let respuestaId = null;
  let etapasDelServidor = 0;
  const arranque = performance.now();
  $("etapas").appendChild(etapaDelCliente("petición enviada desde tu navegador", 0));
  try {
    const r = await fetch("/consulta", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    });
    if (!r.ok) throw new Error(`${r.status}: ${(await r.json()).detail}`);

    for await (const [nombre, datos] of eventos(r)) {
      if (nombre === "etapa") {
        etapasDelServidor += 1;
        for (const li of $("etapas").children) li.classList.remove("viva");
        $("etapas").appendChild(dibujarEtapa(datos));
      } else if (nombre === "token") {
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
          $("prosa").appendChild(document.createTextNode(datos.t));
        }
      } else if (nombre === "afirmaciones") {
        pintarAfirmaciones(datos, () => respuestaId);
      } else if (nombre === "veredicto") {
        // LO QUE ESTE PROYECTO EXISTE PARA ENSEÑAR, y ocurre MIENTRAS el modelo sigue escribiendo:
        // las afirmaciones van antes que la prosa en el contrato, así que cuando empieza el texto
        // ya se pueden comprobar. La espera deja de ser un rótulo encendido y se llena con la
        // comprobación de verdad.
        $("respuesta").appendChild(dibujarVeredicto(datos));
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
        pintarPie(datos);
      }
    }
  } catch (e) {
    $("respuesta").textContent = `Error: ${e.message}`;
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

function pintarAfirmaciones(datos, dameRespuestaId) {
  const caja = document.createElement("div");
  const pedido = $("modo").value;
  if (datos.modo !== pedido) {
    // Hueco declarado del 2.2: el modo lo elige hoy el modelo, no la petición. Se enseña el que
    // vino, no el que se pidió, porque enseñar el pedido sería enseñar algo que no ha pasado.
    caja.appendChild(Object.assign(document.createElement("p"), {
      className: "fuente",
      textContent: `Modo pedido: ${pedido} · modo devuelto por el modelo: ${datos.modo}`
        + " (los prompts por modo son el encargo 4.1)",
    }));
  }
  for (const af of datos.afirmaciones) {
    caja.appendChild(dibujarAfirmacion(af, (fragmentoId, donde) =>
      abrirFragmento(dameRespuestaId(), fragmentoId, donde)));
  }
  $("respuesta").appendChild(caja);
}

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

$("titulacion").addEventListener("change", cargarAsignaturas);
$("asignatura").addEventListener("change", detalleAsignatura);
$("preguntar").addEventListener("submit", preguntar);
cargarSelector().catch((e) => { $("pie").textContent = `No se pudo cargar el selector: ${e.message}`; });
