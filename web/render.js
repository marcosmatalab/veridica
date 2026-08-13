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
  caja.appendChild(texto("div", datos.ya_habia_prosa_en_pantalla
    ? "Respuesta retirada" : "Sin respuesta", "etiqueta"));
  caja.appendChild(texto("p", datos.ya_habia_prosa_en_pantalla
    ? "La respuesta se rompió a media frase, así que lo que había en pantalla queda tachado y no "
      + "cuenta. No se borra sin decirlo: borrar a la callada te dejaría pensando que lo leíste mal."
    : "El sistema no ha podido dar una respuesta con la forma que se exige, así que no da ninguna."));
  caja.appendChild(texto("p", datos.motivo || "", "motivo"));
  return caja;
}
