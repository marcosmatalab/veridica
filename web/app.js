// La vista del alumno (encargo 2.4). Sin framework: fetch, un lector de SSE de veinte líneas y DOM.
//
// LO QUE ESTE FICHERO NO HACE, Y ES SU REGLA: no dibuja nada que no haya llegado del servidor. No
// hay temporizadores, no hay barra que avance sola, no hay "pensando..." puesto a mano. Cada línea
// de la lista de etapas viene de un evento `etapa` con su milisegundo medido, y esos mismos
// milisegundos se guardan en `respuestas.etapas`. Si una etapa no ocurre, no se dibuja.

import { dibujarAfirmacion, dibujarEtapa, dibujarAbstencion } from "/estatico/render.js";

const $ = (id) => document.getElementById(id);

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
  // Todo lo normativo -nombre, curso, horas- sale de la fila de la PUENTE, o sea de la norma de la
  // titulación que pregunta, y no de la titulación dueña de la fila. El curso y las horas son nulos
  // en DAM y ASIR porque no hay orden de currículo suya, y eso se dice en vez de inventarse un 1.
  $("asignatura").innerHTML = asignaturas.map((a) => {
    const curso = a.curso ? `${a.curso}.º` : "curso sin declarar";
    const horas = a.horas ? ` · ${a.horas} h` : "";
    const trans = a.transversal ? ` · transversal, la fila vive en ${a.titulacion_duena.toUpperCase()}` : "";
    const norma = a.norma ? ` · ${a.norma}` : "";
    return `<option value="${a.id}">${a.codigo} ${a.nombre} — ${curso}${horas}${norma}${trans}`
      + ` · ${a.fragmentos} fragmentos</option>`;
  }).join("");
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

async function preguntar(ev) {
  ev.preventDefault();
  $("enviar").disabled = true;
  $("etapas").innerHTML = "";
  $("prosa").textContent = "";
  $("prosa").className = "prosa";
  $("respuesta").innerHTML = "";
  $("pie").textContent = "";

  const cuerpo = {
    texto: $("texto").value,
    asignatura_id: Number($("asignatura").value) || null,
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
        $("prosa").textContent += datos.t;
      } else if (nombre === "afirmaciones") {
        pintarAfirmaciones(datos, () => respuestaId);
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
    + `${eur} · traza <b>${d.respuesta_id}</b>`
    + (d.verificacion && !d.verificacion.construido
      ? ` · verificación pedida: ${d.verificacion.solicitada ? "sí" : "no"} (sin efecto todavía)`
      : "");
}

$("titulacion").addEventListener("change", cargarAsignaturas);
$("preguntar").addEventListener("submit", preguntar);
cargarSelector().catch((e) => { $("pie").textContent = `No se pudo cargar el selector: ${e.message}`; });
