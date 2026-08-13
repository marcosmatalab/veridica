// Cómo se dibuja una afirmación, en un fichero aparte a propósito: lo usan la vista del alumno y
// la ruta /estilos, así que lo que se ve en la muestra es EXACTAMENTE lo que se verá en la
// respuesta real. Dos plantillas distintas serían dos verdades distintas, y la muestra dejaría de
// probar nada.
//
// La regla de la hoja de estilos, aquí en el marcado: cada tipo lleva ETIQUETA CON TEXTO. Si la
// compresión de vídeo se come el color y los bordes, el alumno todavía lee "CITA LITERAL".

const ETIQUETAS = {
  literal: "Cita literal",
  parafrasis: "Paráfrasis del temario",
  calculo: "Cálculo",
  conocimiento: "Conocimiento del modelo · no sale de tu temario",
  andamiaje: "Andamiaje",
};

const ANDAMIAJES = {
  analogia: "Analogía · comparación mía, no está en el temario",
  transicion: "Andamiaje · transición",
  pregunta_al_alumno: "Andamiaje · pregunta para ti",
  resumen: "Andamiaje · resumen",
  animo: "Andamiaje · ánimo",
};

function texto(etiqueta, contenido, clase) {
  const e = document.createElement(etiqueta);
  if (clase) e.className = clase;
  if (contenido !== undefined) e.textContent = contenido;
  return e;
}

export function dibujarAfirmacion(af, alAbrirFragmento) {
  const d = af.detalle || {};
  const caja = texto("div", undefined, "afirmacion " + af.tipo);
  let etiqueta = ETIQUETAS[af.tipo] || af.tipo;
  if (af.tipo === "andamiaje") {
    etiqueta = ANDAMIAJES[d.andamiaje] || ETIQUETAS.andamiaje;
    if (d.andamiaje === "analogia") caja.classList.add("analogia");
  }

  const cabecera = texto("div", undefined, "etiqueta");
  cabecera.textContent = etiqueta;
  caja.appendChild(cabecera);

  // El veredicto viaja SIEMPRE y a la vista. En el 2.2 y el 2.4 vale 'sin_verificar' en todas, que
  // es lo único honesto: aquí se comprueba la forma del contrato, no la verdad de lo que dice.
  if (af.veredicto) {
    const v = texto("span", af.veredicto.replace("_", " "), "veredicto");
    cabecera.appendChild(v);
  }

  caja.appendChild(texto("div", af.tipo === "literal" ? d.cita || af.texto : af.texto, "cuerpo"));

  if (af.tipo === "calculo" && d.expresion) {
    caja.appendChild(texto("code", d.expresion, "expresion"));
  }

  if (af.fragmento_id) {
    const p = texto("p", undefined, "referencia");
    const enlace = texto("a", `ver el fragmento ${af.fragmento_id} en el temario`);
    enlace.href = "#";
    enlace.addEventListener("click", (ev) => {
      ev.preventDefault();
      alAbrirFragmento(af.fragmento_id, caja);
    });
    p.appendChild(enlace);
    caja.appendChild(p);
  } else if (af.tipo === "literal" || af.tipo === "parafrasis") {
    caja.appendChild(texto("p", "sin referencia: no debería pasar", "fuente"));
  }
  return caja;
}

export function dibujarEtapa(etapa) {
  const li = texto("li", undefined, "viva");
  const cuerpo = texto("div", undefined, "cuerpo-etapa");
  const cabecera = texto("div", undefined, "linea-etapa");
  cabecera.appendChild(texto("span", etapa.detalle || etapa.nombre));
  cabecera.appendChild(texto("span", `${Math.round(etapa.ms)} ms`, "ms"));
  cuerpo.appendChild(cabecera);

  // LOS FRAGMENTOS RECUPERADOS SE ENSEÑAN, no se cuentan. El alumno ve las citas antes que el
  // texto, que es lo que el 2.4 escribió como objetivo, y leer seis títulos ocupa justo los dos
  // segundos que el modelo tarda en llegar a la prosa. No es relleno: es lo que se acaba de
  // recuperar, con su documento y su unidad.
  if (etapa.fragmentos && etapa.fragmentos.length) {
    const lista = texto("ol", undefined, "fragmentos-recuperados");
    for (const f of etapa.fragmentos) {
      const item = texto("li");
      item.appendChild(texto("span", f.documento, "doc"));
      item.appendChild(texto("span", ` · ${f.unidad}`, "unidad"));
      lista.appendChild(item);
    }
    cuerpo.appendChild(lista);
  }
  li.appendChild(cuerpo);
  li.dataset.etapa = etapa.nombre;
  return li;
}

export function dibujarAbstencion(datos) {
  const caja = texto("div", undefined, "abstencion");
  const porPlazo = Boolean(datos.por_plazo);
  caja.appendChild(texto("div", porPlazo
    ? "Respuesta cortada por tiempo"
    : (datos.ya_habia_prosa_en_pantalla ? "Respuesta retirada" : "Sin respuesta"), "etiqueta"));
  // EL CORTE POR PLAZO ES SU PROPIO CASO Y NO "no supo responder". Confundirlos le haría creer al
  // alumno que su pregunta no tiene respuesta cuando lo que pasó es que llegó tarde: son dos cosas
  // distintas y una de ellas invita a reformular la pregunta para nada.
  caja.appendChild(texto("p", porPlazo
    ? "El modelo estaba respondiendo demasiado despacio y se ha cortado para no dejarte la pantalla "
      + "parada. No es que no haya respuesta: es que no llegó a tiempo. Vuelve a preguntar."
    : (datos.ya_habia_prosa_en_pantalla
      ? "La respuesta se rompió a media frase, así que lo que había en pantalla queda tachado y no "
        + "cuenta. No se borra sin decirlo: borrar a la callada te dejaría pensando que lo leíste mal."
      : "El sistema no ha podido dar una respuesta con la forma que se exige, así que no da ninguna.")));
  caja.appendChild(texto("p", datos.motivo || "", "motivo"));
  return caja;
}

//: Los tres veredictos del verificador literal, con etiqueta y explicación en castellano llano. La
//: distinción es ESTRUCTURAL y no de color (regla del 2.4): tiene que aguantar una videollamada
//: comprimida y una pantalla compartida.
const VEREDICTOS = {
  verificada: ["✓ CITA COMPROBADA",
    "Estas palabras están en el temario, letra por letra. Lo ha comprobado una comparación de "
    + "texto, sin ningún modelo de por medio."],
  degradada_a_parafrasis: ["~ NO ES CITA LITERAL",
    "El contenido puede ser correcto, pero estas NO son las palabras del temario: el sistema las "
    + "reescribió. No las copies como si fueran del libro."],
  podada: ["✗ PROCEDENCIA INVENTADA",
    "El sistema dijo que esto venía de un fragmento que nunca leyó. La afirmación se retira."],
};

export function dibujarVeredicto(datos) {
  const [etiqueta, explicacion] = VEREDICTOS[datos.veredicto] || ["?", ""];
  const caja = texto("div", undefined, `veredicto v-${datos.veredicto}`);
  caja.appendChild(texto("div", `${etiqueta}  ·  afirmación ${datos.id_en_contrato}`, "etiqueta"));
  caja.appendChild(texto("p", explicacion));
  return caja;
}

export function dibujarReintento(datos) {
  // Se anuncia el reintento por RITMO, que es la avería más probable de una sesión: medido, dos de
  // cada veinte consultas se hunden a 4-11 palabras/s tras arrancar bien. Cortarlas y volver a
  // pedir cuesta un par de segundos; no cortarlas cuesta un minuto de pantalla congelada.
  const caja = texto("div", undefined, "reintento");
  caja.appendChild(texto("div", "Reintentando", "etiqueta"));
  caja.appendChild(texto("p", "La respuesta llegaba demasiado despacio"
    + (datos.tokens_por_segundo ? ` (${Math.round(datos.tokens_por_segundo)} palabras por segundo)` : "")
    + ", así que se ha cortado y se ha pedido de nuevo."
    + (datos.ya_habia_prosa_en_pantalla
      ? " Lo que había escrito no cuenta y se ha retirado." : "")));
  return caja;
}
