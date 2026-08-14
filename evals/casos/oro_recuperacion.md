# Pares oro de recuperación (encargo 3.0) — 94 pares

**Esto no es un examen y aquí no se contesta nada.** Un par oro es una pareja: una pregunta
escrita por el profesor del módulo, y **el fragmento del corpus que ya contiene la respuesta**.
Existen para medir `recall@6` y `nDCG@5`: si el buscador del sistema, ante esa pregunta, trae ese
fragmento entre los seis del contexto final.

Lo único que se revisa al validarlos: **¿está la respuesta dentro del texto que va debajo?** Es
comprensión lectora, no conocimiento del framework.

> ## ✅ ESTADO A 14 DE AGOSTO DE 2026: RECONSTRUCCIÓN APLICADA — 94 PARES
>
> El propietario terminó la relectura de los cien pares uno a uno y entregó la corrección como
> **diff** (id → orden nuevo, mismo documento), para que quedara auditable en vez de reescribir el
> fichero. Aplicada el 14 de agosto con los `hash_texto` recalculados contra el índice y
> `verificar_oro` en verde: **54 pares movidos, 40 sin tocar, 6 retirados**.
>
> **Y el diff llegó con una línea de menos, cazada sumando en vez de creyendo.** El mensaje de
> entrega decía *"54 movidos y 40 correctos"* y la lista traía **53** movimientos: se aplicó la
> lista y la discrepancia se señaló en vez de resolverse en silencio. El propietario confirmó que
> era suya —al transcribir la tabla final se dejó la línea `oro-063→18`— y el movimiento se aplicó
> en segunda tanda, con re-medida (solo movió el nDCG en la tercera decimal; los recalls, ni una
> décima). **La lección, de la familia del instrumento:** un recuento correcto y una transcripción
> incompleta se ven **igual** desde fuera — lo que los separó no fue leer con más cuidado, fue que
> el receptor **sumara** (53 + 41 + 6 ≠ 100 con los números declarados) en vez de fiarse del
> resumen. Todo total que llega con su desglose se comprueba sumando, cueste lo que cueste: aquí
> costó una resta.
>
> El detalle entero, en la sección *"La corrección aplicada"* de abajo. El bloque siguiente se
> conserva como historia de cómo se llegó, porque la corrección se declara, no se borra.
>
> ## ⚠️ ESTADO A 13 DE AGOSTO DE 2026 (HISTÓRICO): EL CONJUNTO ESTÁ EN RECONSTRUCCIÓN
>
> **Ningún recall medido contra esta versión del fichero es definitivo, y ninguno sale a la
> evidencia como tal.** El motivo, con los dos muestreos que lo establecen:
>
> 1. **El muestreo sesgado (14 pares).** Al leer los catorce pares que ninguna vía de recuperación
>    encontraba, once tenían el fragmento mal etiquetado
>    (`docs/evidencia/2026-08-13-fusion.md`). Ese número **no se puede extrapolar**: esos catorce
>    se eligieron *precisamente porque* la recuperación fallaba, que es una de las cosas que un mal
>    etiquetado produce. Estaba sobrerrepresentado por construcción.
> 2. **El muestreo al azar (8 pares), que es el que sí estima.** El propietario tomó al azar ocho
>    pares **que nadie había marcado** —los que nunca cayeron bajo sospecha porque la recuperación
>    sí los acertaba— y salieron **tres claramente mal y uno dudoso**. Ese sí es un estimador del
>    conjunto entero, y da el orden de **cuarenta pares mal de cien, no catorce**.
> 3. **Y el recuento directo, que ya no estima: 51 de 100 revisados uno a uno a 13 de agosto de
>    2026, con cerca de la mitad mal etiquetados.** Confirma lo que la muestra al azar predecía, y lo
>    confirma **por encima**. Vale la pena dejar los tres pasos escritos y no solo el último: la
>    diferencia entre 11 de 14, 4 de 8 y ~25 de 51 no está en cuánto se miró, sino en **cómo se
>    eligió lo que se miraba**.
>
> **Por eso es una reconstrucción y no un parche**, y la está haciendo el propietario leyendo los
> cien uno a uno. Cuando termine se repiten las corridas del 3.1, 3.2 y 3.3 con la misma
> configuración y **se reportan los dos números, antes y después, con el tamaño del conjunto al
> lado** —que cambiará: hay pares que se retiran, no solo pares que se corrigen—.
>
> **Y la consecuencia que corrige lo que se había escrito:** con errores también entre los pares que
> la recuperación SÍ acertaba, ya no se puede afirmar que el recall corregido vaya a subir. Un par
> mal etiquetado que la recuperación encontraba estaba **regalando** un acierto. La corrección puede
> mover el número en cualquiera de los dos sentidos, y se sabrá midiendo.

## Método, declarado entero (esto es lo que hace que el número signifique algo)

1. **La pregunta viene SIEMPRE de fuera del corpus indexado**: de los bancos de test y de los
   cuestionarios escritos por el profesor (`practicas/01-test*.md`, `practicas/02-cuestionario*.md`,
   `practicas/04-test-*.md`), quitando las cuatro opciones y dejando el enunciado, reformulado como
   lo escribiría un alumno. **Jamás se genera una pregunta a partir de un fragmento**: si naciera del
   fragmento, la recuperación acertaría por construcción y el recall sería un espejo.
2. **Los fragmentos de `practicas/` están excluidos como oro.** Son la pregunta, no la respuesta.
3. **El fragmento oro NUNCA se localiza con la recuperación del sistema.** Sería medir el sistema
   con el sistema. Se localiza de dos maneras distintas, y **cada par declara cuál**:
   - `busqueda`: buscando literalmente términos de la pregunta en el texto del corpus.
   - `lectura`: leyendo el mapa de secciones del documento y yendo a la sección que trata el tema,
     sin buscar los términos de la pregunta.
4. **Por qué esa distinción no es cosmética, y es el punto importante de este fichero.** El método
   `busqueda` comparte mecanismo con la recuperación léxica (BM25) del encargo 3.1: un fragmento
   elegido por coincidencia de términos es un fragmento que BM25 encuentra fácil, así que el recall
   sobre esos pares **sale inflado por construcción**. El método `lectura` no comparte ese
   mecanismo. **El encargo 3.5 debe reportar recall@6 por separado en los dos subconjuntos: la
   diferencia entre ambos ES el sesgo del conjunto de evaluación, medido en vez de declarado.**
   Reparto tras la corrección del 14 de agosto: **19 `busqueda` y 75 `lectura`** (los 6 retirados
   eran todos `lectura`; hasta entonces eran 19 y 81).
5. **Quién lo construyó, dicho claro:** los pares los construyó el asistente de la conversación de
   diseño, no el agente que escribe el sistema. Es deliberado: si el mismo autor escribiera la
   recuperación y la vara con la que se mide, el número no valdría nada (principio 6). No hay
   validación humana experta disponible —el propietario no imparte el módulo— y **eso también se
   declara en vez de fingirse**; el respaldo es el punto 4, que convierte la duda en una medida.
6. **Regla de fragmentos múltiples:** un solo fragmento oro por pregunta, el que la responde más
   completo. Otros fragmentos relevantes no cuentan ni como acierto ni como fallo.
7. **Preguntas descartadas por diseño:** las que piden contrastar dos mecanismos, porque su
   respuesta vive en dos fragmentos y `recall@6` es binario contra uno. No se tiran: van a los
   casos de generación de la fase 4, donde el modelo recibe seis fragmentos y sintetiza.
8. **Un par dudoso se resuelve leyendo el fragmento COMPLETO, nunca un extracto** (regla añadida el
   13 de agosto de 2026, y es el mismo error que construyó el conjunto: se etiquetó contra
   extractos). El extracto que acompaña a cada par en este fichero está para poder comprobarlo de
   un vistazo; **el que decide es el fragmento entero**, que son 400-500 tokens y se leen en medio
   minuto.
9. **Un par se juzga solo, contra su pregunta — nunca en tanda y nunca contra una hipótesis**
   (misma fecha, y esta salió de un fallo propio que conviene no maquillar). De siete pares
   propuestos como mal etiquetados, el propietario confirmó cinco y **rechazó dos**: `oro-001`
   —el *Tip del Examinador* del orden 4 dice *"la sesión se almacena en el servidor, la cookie solo
   contiene el ID"*, que responde las dos mitades de la pregunta— y `oro-002` —el orden 3 define
   `@SessionAttribute` en singular como *"anotación en un parámetro de método para leer un atributo
   de sesión existente"*, que es la pregunta con sus mismas palabras—. **Y lo incómodo, que es lo
   que hace útil la regla: en los dos casos el extracto citado aquí YA contenía la respuesta.** No
   faltaba texto. Los dos se juzgaron en una tanda de catorce y bajo una hipótesis previa —"estos
   son los que nadie encuentra, a ver cuántos están mal"—, y la hipótesis se llevó por delante lo
   que estaba escrito delante. Por eso leer el fragmento entero es el **mínimo**, no el arreglo.
   **Que dos revisores difieran en dos de siete es un dato del método y por eso está escrito**, y la
   salida no es votar: es que la unidad de decisión sea el fragmento y la unidad de trabajo sea el
   par.
10. **El solape de 64 tokens hace que dos fragmentos contiguos parezcan intercambiables, y no lo
    son.** Aviso operativo para la reconstrucción, porque el patrón detectado —*el fragmento
    correcto es casi siempre `orden + 1`*— es exactamente la clase de hipótesis contra la que avisa
    la regla 9. Ejemplo real y comprobable: `oro-002` apunta al orden 3 y **está bien**; el orden 4
    contiene `@SessionAttributes` **en plural** —la anotación de clase, para formularios de varios
    pasos— porque el solape arrastró ese trozo, pero **no contiene la singular**, que es la que la
    pregunta pide. Mover ese par a `orden + 1` daría un fragmento que menciona algo con casi el
    mismo nombre y no responde. **La corrección se comprueba una a una con el mismo criterio que el
    etiquetado original**, o cambia un sesgo por otro.

> **Añadido al colocar el fichero en el repo (12 de agosto de 2026), no por su autor.** El `.jsonl`
> lleva desde entonces un campo más por par: `fragmento_oro.hash_texto`, el SHA-256 del texto del
> fragmento etiquetado. El par apuntaba solo por `(documento, orden)`, y `orden` es posicional: si el
> corpus se vuelve a trocear, el par sigue apuntando a un fragmento que existe pero es otro texto, y
> no protesta —`recall@6` pasa a medir otra cosa sin que nada falle—. `scripts/verificar_oro.py`
> compara el hash además de la posición. Antes de anclarlo se comprobó que los 100 extractos citados
> en este documento son subcadena literal del fragmento al que apunta cada par, así que el hash ancla
> el texto que se leyó al etiquetar y no el que hubiera hoy. El porqué entero, en
> [ADR 0010](../../docs/adr/0010-el-par-oro-se-ancla-al-texto-no-a-la-posicion.md).

## Composición real

La guía pedía 50 de DWES y 50 de Programación. **No es posible y aquí está el motivo:** Programación
(lionel-ict) **no tiene banco de preguntas del profesor**; lo que tiene son enunciados de ejercicio
("escribe un programa que…"), que son tareas cuya respuesta es código, no preguntas cuya respuesta
viva en un fragmento de teoría. Inventarlas habría roto la regla 1. Así que los 100 salen de DWES,
que sí tiene 650 preguntas de test y 117 abiertas, repartidos por repositorio:

| Repositorio | Pares | Materia |
|---|---:|---|
| joseluisgs-02 | 27 | Java, Spring y Spring Boot, Spring Security, REST |
| joseluisgs-03 | 11 | Spring MVC, Pebble, formularios, estado y seguridad |
| joseluisgs-04 | 32 | ASP.NET Core, EF Core, caché, transacciones, testing, C# |
| joseluisgs-05 | 24 | ASP.NET Core MVC y Razor Pages, estado, Tag Helpers |

(La tabla refleja el conjunto corregido de 94: los 6 retirados del 14 de agosto salieron 3 del
`-04` y 3 del `-05`; antes eran 35 y 27.)

**Dos fragmentos aparecen como oro en dos preguntas cada uno**, declarados; no se corrigen, porque
corregirlos sería elegir un fragmento peor:

- `joseluisgs-02/springboot/04-SpringWebRest.md` orden 11: explica `@RestController` y
  `@Repository` en el mismo trozo, y las dos preguntas del banco son distintas (desde el origen).
- `joseluisgs-03/03-controladores-formularios.md` orden 8: **apareció con la corrección del 14 de
  agosto** — `oro-004` (qué problema resuelve PRG) se movió del 7 al 8 y cayó en el fragmento de
  `oro-005` (cómo pasar un mensaje tras redirigir), que explica las dos cosas seguidas.

## La corrección aplicada (14 de agosto de 2026)

**Motivo común de los movimientos:** el par se ancló al **encabezado** de la sección, y el
encabezado caía al final de un fragmento, así que el contenido estaba en el siguiente — por eso casi
todos los destinos son `orden + 1`, y los que no lo son se releyeron igual (regla 10: la corrección
se comprueba una a una, nunca con la hipótesis del `+1`). **Nueve pares apuntaban directamente al
ÍNDICE del documento** (024*, 045*, 047*, 054*, 055*, 066*, 083*, 091*, 093* — los marcados en el
diff del propietario)... y los `hash_texto` se recalcularon contra el índice al aplicar, que es lo
que el propietario pidió: él entrega posiciones leídas, la máquina ancla el texto.

**El diff entero, aplicado tal cual se entregó** (id: orden viejo → nuevo, mismo documento):

```
004:7→8    008:10→11  015:9→10   018:4→5    020:15→16  021:5→7    022:19→20  024:5→6
025:26→27  026:27→28  027:30→31  029:19→20  031:16→17  032:10→11  033:18→19  038:7→8
041:13→14  043:21→22  044:24→25  045:3→4    047:1→2    048:4→5    049:5→6    052:7→8
054:1→2    055:1→2    056:3→4    057:5→6    058:6→7    059:8→9    061:11→12  063:17→18
064:28→29  066:4→5    067:8→9    068:19→20  069:23→24  070:6→7    071:10→11  072:23→24
074:15→16  075:26→28  079:5→6    080:6→7    082:22→23  083:5→6    084:8→10   085:11→12
086:14→15  089:12→13  091:2→3    093:2→3    099:7→8    100:20→21
```

(El `063:17→18` —el filtro JWT: el 17 es el servicio de signup/signin y el 18 el filtro invocado
una vez por petición— es la línea que faltaba en la transcripción, aplicado en segunda tanda el
mismo día; la historia, en el estado de arriba.)

**Retirados, con los dos motivos POR SEPARADO porque no son la misma cosa:**

- **`oro-028`, `oro-037`, `oro-081` — preguntas de CONTRASTE**: su respuesta vive en dos fragmentos
  y `recall@6` es binario contra uno; la regla 7 de este mismo método las excluía. **No se tiran**:
  están en `evals/casos/generacion_contraste.jsonl` para los casos de generación de la fase 4.
- **`oro-040`, `oro-090`, `oro-097` — HUECO DE CORPUS**: ninguna ventana del documento etiquetado
  contiene la respuesta (sesión con balanceador, niveles de aislamiento, patrón AAA). No es que se
  eligiera mal el fragmento: el material no está. Declarado en `corpus/COBERTURA.md`.

**Sobre las fichas de abajo:** describen el etiquetado original del 12 de agosto. Para los 53 pares
movidos, **el ancla operativa es la del `.jsonl`** (orden nuevo + hash del texto nuevo, verificados
por `scripts/verificar_oro.py`); el extracto de la ficha corresponde al fragmento antiguo y se
conserva como historia. Las fichas de los 6 retirados también se conservan; sus pares ya no están en
el `.jsonl`.

---

## 1. ¿Dónde se almacenan los datos de la sesión de un usuario en Spring Boot, y qué es lo único que viaja en la cookie?

- **Fragmento oro:** `joseluisgs-03/04-estado-seguridad.md` orden **4** (explicacion, 445 tok)
- **Origen de la pregunta:** 01-test.md p.42 + 02-cuestionario.md p.10
- **Localización:** `busqueda`

> …n HTTP es como una mochila que el servidor le da a cada usuario. Mientras el usuario siga visitando la web, la mochila se mantiene. Cuando cierra el navegador o transcurre el timeout, se pierde. 💡 **Tip del Examinador**: La sesión se almacena en el servidor, la cookie solo contiene el ID. Esto es más seguro que almacenar datos sensibles en cookies. ⚠️ **Advertencia**: Las sesiones consumen memoria del servidor. En aplicaciones con muchos usuarios, considera usar sesiones distribuidas (Redis) o reducir el timeout.…

## 2. ¿Qué anotación se usa en un parámetro de método del controlador para leer un atributo de sesión que ya existe?

- **Fragmento oro:** `joseluisgs-03/04-estado-seguridad.md` orden **3** (explicacion, 467 tok)
- **Origen de la pregunta:** 01-test.md p.43
- **Localización:** `busqueda`

> …); } return carrito; } } ``` **Mecanismos Alternativos de Sesión en Spring:** - **`@SessionAttribute`:** Anotación en un parámetro de método para leer un atributo de sesión *existente*. Es solo para leer, no para escribir. ```java @GetMapping("/ver") public String verCarrito( @SessionAttribute(name = "carrito", required = false) Map<Long, ItemCarrito> carrito, Model model ) { if (carrito == null) { carrito = new HashMap<>(); } model.addAttribute("carrito", carrito); return "carrito/ver"; } ``` - **`@SessionAttributes` (en la Clase):** Anotación a nivel de `@Controller` que le dice a Spring…

## 3. ¿Para qué tipo de datos son apropiadas las cookies y por qué no se deben guardar en ellas datos sensibles?

- **Fragmento oro:** `joseluisgs-03/04-estado-seguridad.md` orden **6** (explicacion, 415 tok)
- **Origen de la pregunta:** 01-test.md p.48 + 02-cuestionario.md p.10
- **Localización:** `busqueda`

> …angeInterceptor()); } } ``` Ahora, cuando un usuario cambia de idioma, esa preferencia se guarda en una cookie en su navegador durante 30 días. 📝 **Nota del Profesor**: Las cookies son como pósits en el frigorífico. El cliente las tiene (no el servidor), puede verlas y cambiarlas. ¡No pongas secretos en pósits! ## 4.2 Autenticación de Usuarios ### 4.2.1 El Mecanismo: Spring Security Usamos **Spring Security**, el estándar de la industria en Java. Es un "muro" de "filtros" (Filter Chain) que intercepta *todas* las peticiones antes de que lleguen a nuestro Controller. Su trabajo es gestionar la autenticación (quién eres) y la autorización (qué puedes hacer). **Configuración:** ```java @Configuration @EnableWebSecurity @EnableMethodSe…

## 4. ¿Qué problema resuelve el patrón Post-Redirect-Get después de procesar un formulario POST?

- **Fragmento oro:** `joseluisgs-03/03-controladores-formularios.md` orden **7** (explicacion, 434 tok)
- **Origen de la pregunta:** 01-test.md p.8 + 02-cuestionario.md p.4
- **Localización:** `busqueda`

> …tos"; } } ``` 📝 **Nota del Profesor**: El `@ModelAttribute` es como un traductor. Convierte los datos del formulario HTML (que son Strings) a un objeto Java. ¡Es automagia! ### 3.2.3 Patrón Post-Redirect-Get En el ejemplo anterior, devolvimos `return "redirect:/productos";` en lugar de `return "productos/lista";`. ¿Por qué? Esto se llama el **Patrón PRG** y es una **buena práctica obligatoria**. **❌ Qué NO hacer:** Devolver el nombre de la vista (`return "productos/lista";`) después de un POST. - **Problema:** Si el usuario refresca la página, el navegador **reenviará el formulario POST**, duplicando la acción (ej. creando el producto dos veces).…

## 5. Si el Model se pierde al redirigir, ¿cómo se le pasa un mensaje de éxito a la página de destino?

- **Fragmento oro:** `joseluisgs-03/03-controladores-formularios.md` orden **8** (procedimiento, 472 tok)
- **Origen de la pregunta:** 02-cuestionario.md p.4
- **Localización:** `busqueda`

> …al, lo cual es inofensivo. **Problema de las Redirecciones:** ¿Cómo mostramos un mensaje de "Producto guardado" si redirigimos? El Model se pierde en la redirección. **Solución: RedirectAttributes (Flash Attributes).** Los "Flash Attributes" son atributos especiales que sobreviven una sola redirección. ```java @PostMapping("/guardar") public String guardarProducto( @ModelAttribute Producto producto, RedirectAttributes redirectAttributes // 1. Inyectamos RedirectAttributes ) { productoServicio.guardar(producto); // 2. Añadimos un atributo flash redirectAttributes.addFlashAttribute("mensajeExito", "¡Producto guardado correctamente!"); return "redirect:/productos"; } ``` ```twig // Y en la vista 'productos/lista.peb',…

## 6. ¿Qué dos parámetros hay que poner justo detrás del @ModelAttribute en un POST para que se valide el formulario y se capturen los errores?

- **Fragmento oro:** `joseluisgs-03/03-controladores-formularios.md` orden **11** (explicacion, 447 tok)
- **Origen de la pregunta:** 01-test.md p.45 + 02-cuestionario.md p.8
- **Localización:** `busqueda`

> …so 2: Activar la Validación en el Controlador Modificamos nuestro método POST para que active la validación: 1. Añadimos `@Valid` al `@ModelAttribute` que queremos validar. 2. Añadimos un parámetro `BindingResult` **inmediatamente después**. ```java @PostMapping("/guardar") public String guardarProducto( @Valid @ModelAttribute("producto") Producto producto, // 1. Activa la validación BindingResult result, // 2. Spring deja los errores de validación aquí Model model, RedirectAttributes redirectAttributes ) { // 3. Comprobamos si hay errores if (result.hasErrors()) { // Si hay errores, NO guardamos. // Volvemos a mostrar la vista del formulario para que el usuario corrija. // Sprin…

## 7. ¿Por qué se recomienda Model en vez de ModelAndView para pasar datos a la vista?

- **Fragmento oro:** `joseluisgs-03/03-controladores-formularios.md` orden **3** (explicacion, 509 tok)
- **Origen de la pregunta:** 02-cuestionario.md p.2
- **Localización:** `busqueda`

> …él mismo! ### 3.1.1 Model vs ModelAndView Hay dos formas de pasar datos del Controlador a la Vista: **1. Model (Enfoque Moderno y Recomendado):** - **Cómo:** Recibes un `Model` como parámetro del método. Añades atributos (`model.addAttribute(...)`) y devuelves un String con el nombre de la vista. - **Ventaja:** Más limpio, más flexible (puedes tener if/else y devolver distintos String de vistas) y mucho más fácil de testear. ```java @GetMapping("/detalle/{id}") public String detalle(@PathVariable Long id, Model model) { Producto producto = productoServicio.findById(id); if (producto == null) { model.addAttribute("error", "Producto no encontrad…

## 8. ¿Qué mecanismo de Pebble se usa para definir el esqueleto o layout base con agujeros que rellenan las plantillas hijas?

- **Fragmento oro:** `joseluisgs-03/02-pebble.md` orden **10** (explicacion, 481 tok)
- **Origen de la pregunta:** 01-test.md p.36 + 02-cuestionario.md p.7
- **Localización:** `busqueda`

> …en cada uno de nuestros 30 archivos HTML. Pebble ofrece tres mecanismos para esto. ### 2.4.1 Herencia de Plantillas (extends y block) Es el mecanismo más potente y recomendado. 1. **Definimos un "esqueleto" o "layout" base** con "agujeros". 2. **Las plantillas "hijas"** "extienden" ese esqueleto y se limitan a "rellenar los agujeros". **templates/layouts/base.peb (El Esqueleto o Layout):** ```html <!DOCTYPE html> <html lang="es"> <head> <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0"> {# Directiva 'block' define un "agujero" con contenido por defecto #} <title>{% block title %}Mi Aplicación E-Commerce{% endblock %}</title> <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3…

## 9. ¿Qué directiva de Pebble se usa para insertar un componente reutilizable como el navbar dentro de otra plantilla?

- **Fragmento oro:** `joseluisgs-03/02-pebble.md` orden **13** (explicacion, 424 tok)
- **Origen de la pregunta:** 01-test.md p.36
- **Localización:** `busqueda`

> …dentro de otra. Es perfecto para componentes reutilizables (navbar, footer, un formulario de login, una tarjeta de producto). **templates/fragments/navbar.peb:** ```twig <nav class="navbar navbar-expand-lg navbar-dark bg-dark"> <div class="container-fluid"> <a class="navbar-brand" href="/">Mi E-Commerce</a> <ul class="navbar-nav ms-auto"> {# ... toda la lógica de 'isAuthenticated' y 'isAdmin' ... #} {# ... y el badge del 'cartItemCount' ... #} </ul> </div> </nav> ``` Esta plantilla se inserta en base.peb usando `{…

## 10. ¿Por qué Page es lento en repositorios grandes y qué se puede usar en su lugar?

- **Fragmento oro:** `joseluisgs-03/05-tecnologias-hibridas.md` orden **14** (explicacion, 422 tok)
- **Origen de la pregunta:** 01-test.md p.47 + 02-cuestionario.md p.6
- **Localización:** `busqueda`

> …</li> {% endif %} </ul> </nav> ``` ### 5.4.4 Optimización de Paginación: Page vs Slice **Nota Avanzada del Profesor:** Cuando usas `Page<T>` en tu repositorio, Spring Data JPA ejecuta **dos** consultas SQL: 1. Una consulta para obtener los datos de la página (ej. `SELECT * FROM producto LIMIT 10 OFFSET 0`). 2. Una consulta de conteo para saber el total de elementos (ej. `SELECT COUNT(*) FROM producto`). Esta consulta `COUNT(*)` puede ser muy lenta en tablas con millones de filas. Si solo necesitas saber si hay una página *siguiente*, pero no necesitas el número total de páginas, puedes usar `Slice<T>` en lugar de `Page<T>…

## 11. ¿Qué lógica debe ir en el servicio y cuál en el controlador?

- **Fragmento oro:** `joseluisgs-03/01-fundamentos.md` orden **14** (explicacion, 495 tok)
- **Origen de la pregunta:** 02-cuestionario.md p.9
- **Localización:** `busqueda`

> …de la Lógica de Negocio (Patrón Service-Repository):** **Ejemplo de Separación Correcta:** **❌ Mal (Lógica en el Controller):** ```java @Controller public class ProductoController { @Autowired private ProductoRepository repositorio; // Mal, el Controller no debe conocer al Repository @GetMapping("/productos") public String lista(Model model) { // Mal, la lógica de negocio (buscar en BBDD) está en el Controller List<Producto> productos = repositorio.findAll(); model.addAttribute("productos", productos); return "productos/lista"; } } ``` **✅ Bien:** ```java // --- CAPA REPOSITORY --- public interfa…

## 12. ¿Qué anotación combina @Configuration, @EnableAutoConfiguration y @ComponentScan y marca la clase principal de la aplicación?

- **Fragmento oro:** `joseluisgs-02/springboot/04-SpringWebRest.md` orden **7** (procedimiento, 508 tok)
- **Origen de la pregunta:** 04-test-springboot.md p.16
- **Localización:** `busqueda`

> …fill:#c8e6c9 style Contenedor fill:#fff9c4 style Beans fill:#c8e6c9 ``` A continuación, te explico cada componente de la clase: 1. `@SpringBootApplication`: Esta anotación es una combinación de varias anotaciones de Spring Boot, incluyendo `@Configuration`, `@EnableAutoConfiguration` y `@ComponentScan`. Esta anotación marca la clase como una clase de configuración de Spring Boot y habilita la configuración automática de la aplicación. Además, escanea los componentes dentro del paquete actual y sus subpaquetes para su detección automática. 2. `public static void main(String[] args)`: Este es el método principal de la aplicación. Es el punto de entrada de la aplicación Spring Boot. Aquí, se llama al método `run` de la clase `Sprin…

## 13. ¿Qué anotación se usa en una clase que recibe peticiones y devuelve datos serializados en JSON en lugar de una vista?

- **Fragmento oro:** `joseluisgs-02/springboot/04-SpringWebRest.md` orden **11** (explicacion, 489 tok)
- **Origen de la pregunta:** 04-test-springboot.md p.20
- **Localización:** `busqueda`

> …roller fill:#c8e6c9 style Service fill:#fff9c4 style Repository fill:#e8f5e9 style Entity fill:#ffcdd2 ``` - Controladores: Se etiquetan como *@Controller* o en nuestro caso al ser una API REST como @RestController. Estos son los controladores que se encargan de recibir las peticiones de los usuarios y devolver respuestas, es decir, son anotaciones utilizadas para manejar las solicitudes HTTP en una aplicación web. Como se indica hay dos opciones: - @Controller: Esta anotación se utiliza para marcar una clase como un controlador en Spring MVC. Un controlador en Spring MVC se encarga de manejar las solicitudes HTTP y generar una respuesta, que puede ser una página HTML, una vista, un archivo JSON, etc. Los métodos dentro de una clase anotada con @C…

## 14. ¿Con qué anotación se marca el componente que implementa el acceso a la base de datos o a una API externa?

- **Fragmento oro:** `joseluisgs-02/springboot/04-SpringWebRest.md` orden **11** (explicacion, 489 tok)
- **Origen de la pregunta:** 04-test-springboot.md p.23
- **Localización:** `busqueda`

> …e etiquetan como *@Service*. Se encargan de implementar la parte de negocio o infraestructura. En nuestro caso puede ser el sistema de almacenamiento o parte de la seguridad y perfiles de usuario. - Repositorios: Se etiquetan como *@Repository* e implementan la interfaz y operaciones de persistencia de la información. En nuestro caso, puede ser una base de datos o una API externa. Podemos extender de repositorios pre establecidos o diseñar el nuestro propio. - Configuración: Se etiquetan como *@Configuration*. Se encargan de configurar los componentes de la aplicación. Se se suelen iniciar al comienzo de nuestra aplicación.…

## 15. ¿Qué son la inversión de control y la inyección de dependencias en Spring?

- **Fragmento oro:** `joseluisgs-02/springboot/03-Spring.md` orden **9** (explicacion, 402 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque Spring Core)
- **Localización:** `busqueda`

> …2fd style Singleton fill:#c8e6c9 style Prototype fill:#fff9c4 style Request fill:#e8f5e9 style Session fill:#e8f5e9 ``` ### 3.1.3. Inversión de Control e Inyección de Dependencias **Inversión de Control (IoC)** y **Inyección de Dependencias (DI)** son dos conceptos fundamentales en Spring y Spring Boot que facilitan la creación de aplicaciones modulares y flexibles. ```mermaid graph LR subgraph "Tradicional" A1["Clase A"] -- "new B()" --> B1["Clase B"] end subgraph "Con IoC/DI" A2["Clase A"] -- "@Autowired" --> B2["Clase B"] Spring["Spring<br/>🗄️"] -->|Crea| B2 Spring -->|Inyecta| A2 end ```…

## 16. ¿Qué módulo de Spring proporciona funcionalidades de producción como la monitorización y la gestión de la aplicación?

- **Fragmento oro:** `joseluisgs-02/springboot/03-Spring.md` orden **4** (explicacion, 509 tok)
- **Origen de la pregunta:** 04-test-springboot.md p.13
- **Localización:** `busqueda`

> …as --> Security Dependencias --> Test style Dependencias fill:#e3f2fd style Web fill:#c8e6c9 style Data fill:#c8e6c9 style Security fill:#c8e6c9 style Test fill:#c8e6c9 ``` 5. **Actuator**: Proporciona funcionalidades de producción listas para usar, como la monitorización y la gestión de la aplicación. 6. **Pruebas**: Spring Boot proporciona soporte para pruebas con Spring Boot Test Starter, lo que facilita la escritura de pruebas para las aplicaciones Spring Boot. ### 3.1.1. Módulos principales de Spring **Spring Framework** está diseñado de manera modular, lo que significa que puedes elegir usar solo los módulos que necesitas para tu aplicación. Aquí te describo algunos de los [módulos](https://spring.io/projects/) más comu…

## 17. ¿Qué interfaz hay que implementar para ejecutar código justo al iniciarse la aplicación Spring Boot?

- **Fragmento oro:** `joseluisgs-02/springboot/04-SpringWebRest.md` orden **8** (explicacion, 428 tok)
- **Origen de la pregunta:** 04-test-springboot.md p.24
- **Localización:** `busqueda`

> …ion`, se inicia la aplicación Spring Boot y se configura el entorno de ejecución. Si nosotros queremos hacer algo por consola o antes de todo, dentro del contexto de Spring Boot debemos implementar `CommandLineRunner` y sobreescribir el método run. De esta manera, cuando se inicie la aplicación, se ejecutará el método run y podremos hacer lo que queramos. No es obligatorio ```java @SpringBootApplication public class TiendaApiSpringApplication implements CommandLineRunner { public static void main(String[] args) { SpringApplication.run(TiendaApiSpringApplication.class, args); } @Override public void run(String... args) throws Exception { System.out.println("Hola Mundo"); } } ``` ### 4.1.3. Parametrizando la aplicación…

## 18. ¿Qué anotación indica que un bean solo debe crearse en un perfil concreto?

- **Fragmento oro:** `joseluisgs-02/springboot/14-Perfiles.md` orden **4** (explicacion, 501 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque perfiles)
- **Localización:** `busqueda`

> …app.jar --spring.profiles.active=prod ``` - **Por variable de entorno:** ```bash export SPRING_PROFILES_ACTIVE=prod ``` ### 14.1.4. Uso de anotaciones con perfiles Puedes usar la anotación `@Profile` para indicar que un bean solo debe crearse en un perfil concreto:…

## 19. ¿Cuál es la diferencia entre CommandLineRunner y @PostConstruct al inicializar?

- **Fragmento oro:** `joseluisgs-02/springboot/08-AlmacenamientoFicheros.md` orden **9** (explicacion, 504 tok)
- **Origen de la pregunta:** 04-test-springboot.md p.24 (derivada)
- **Localización:** `busqueda`

> …- CommandLineRunner: Se ejecuta después del contexto de Spring > - @PostConstruct: Se ejecuta después de la inyección de dependencias, pero antes del contexto completo Una forma alternativa de lograr el mismo resultado sin usar CommandLineRunner es utilizar la anotación `@PostConstruct` en un método dentro de un bean. La anotación @PostConstruct es una anotación estándar de Java que indica que un método debe ejecutarse después de que el bean haya sido construido y se hayan inyectado todas las dependencias. En este ejemplo, el método init() está anotado c…

## 20. ¿Cuál es la principal función del componente Controlador en el patrón MVC de ASP.NET Core?

- **Fragmento oro:** `joseluisgs-05/01-fundamentos.md` orden **15** (explicacion, 453 tok)
- **Origen de la pregunta:** 01-test.md p.2
- **Localización:** `lectura`

> …ner una **caja de herramientas organizada**: sabes exactamente dónde está cada cosa y de qué tamaño es. --- ## 1.4. El Patrón MVC (Model-View-Controller) ### 1.4.1. Responsabilidades y Separación de Conceptos 🎓 **Analogía del Profesor**: > - **Modelo (Cocina)**: Recetas y alimentos (Datos y Lógica). > - **Controlador (Camarero)**: Atiende al cliente y coordina. > - **Vista (Emplatado)**: La presentación final al cliente (HTML). ### 1.4.2. Tipos de Modelos: Entities, ViewModels e InputModels 1. **Entities (.cs)**: Reflejo fiel de la Base de Datos. Contienen datos sensibles. 2. **ViewModels (.cs)**: Solo contienen lo que la vista va a mostrar. Es un "escudo" protector. 3. **InputModels (.cs)**: Optimizados para recibir y validar datos de formulari…

## 21. ¿Qué componente actúa como el núcleo del pipeline que procesa las peticiones HTTP?

- **Fragmento oro:** `joseluisgs-05/01-fundamentos.md` orden **5** (explicacion, 481 tok)
- **Origen de la pregunta:** 01-test.md p.3
- **Localización:** `lectura`

> …iente classDef default fill:#fff,stroke:#333,color:#000 classDef highlight fill:#dfd,stroke:#333,color:#000 class Kestrel highlight ``` ### 1.1.2. El Pipeline de Middleware: El Corazón del Sistema El **Pipeline** es una tubería por la que viaja la petición. Está formada por **Middlewares**: componentes que procesan la petición (Request) y la respuesta (Response). #### La Secuencia Bidireccional: Ida y Vuelta Es vital entender que un middleware no solo actúa cuando la petición entra, sino también cuando la respuesta sale hacia el navegador. ```mermaid flowchart TD REQ["HTTP REQUEST (Navegador)"] --> M1["Middleware 1: Registro/Logs"] M1 --> M2["Middleware 2: Seguridad/Auth"] M2 --> M3["Middleware 3: Archivos Estáticos"] M3…

## 22. ¿Qué tipo de ciclo de vida de un servicio crea una instancia nueva en cada petición HTTP?

- **Fragmento oro:** `joseluisgs-05/01-fundamentos.md` orden **19** (explicacion, 487 tok)
- **Origen de la pregunta:** 01-test.md p.23
- **Localización:** `lectura`

> …SQL)] classDef default fill:#fff,stroke:#333,color:#000 classDef highlight fill:#dae8fc,stroke:#6c8ebf,color:#000 class CTX highlight ``` ### 1.8.2. Ciclos de Vida en Inyección de Dependencias (DI) | Ciclo de Vida | Registro en C# | Comportamiento | Duración | | :------------ | :------------- | :--------------------------------------------------- | :---------------- | | **Transient** | `AddTransient` | **Efímero**: Instancia nueva cada vez que se pide. | Un solo uso. | | **Scoped** | `AddScoped` | **Por Petición**: Instancia única por petición HTTP. | Vida del Request. | | **Singleton** | `AddSingleton` | **Global**: Una sola instancia para toda la app. | Vida de la App. |…

## 23. ¿Para qué sirve el middleware UseStaticFiles en ASP.NET Core?

- **Fragmento oro:** `joseluisgs-05/01-fundamentos.md` orden **9** (explicacion, 494 tok)
- **Origen de la pregunta:** 01-test.md p.24
- **Localización:** `lectura`

> …código en el nombre) para que el navegador sepa si el archivo ha cambiado sin tener que preguntar al servidor. ¡Es puro rendimiento! ### 1.1.6. El Directorio wwwroot y la Gestión de Activos (.NET 10) En ASP.NET Core, existe una frontera física infranqueable: la carpeta **`wwwroot`**. Por seguridad, el servidor web solo puede servir archivos que estén dentro de esta carpeta (el "Web Root"). Ningún usuario podrá acceder a tus archivos `.cs` o secretos, ya que están fuera de este directorio. Sin embargo, .NET 10 permite gestionar lo que hay dentro de `wwwroot` de dos formas distintas: **A. UseStaticFiles (Acceso Literal)** Considera a `wwwroot` como un simple disco duro. Se usa para: - Archivos subidos por usuarios (uploads). - PDF o documentos par…

## 24. ¿Qué es y cómo funciona el Model Binding en ASP.NET Core?

- **Fragmento oro:** `joseluisgs-05/03-formularios.md` orden **5** (definicion, 510 tok)
- **Origen de la pregunta:** 01-test.md p.7
- **Localización:** `lectura`

> …ementación-en-mvc-vistas-normales) - [C. Implementación en Razor Pages](#c-implementación-en-razor-pages) - [3.8. Resumen](#38-resumen) --- ## 3.1. Model Binding: El Puente entre HTTP y C# ### 3.1.1. ¿Qué es el Model Binding y cómo procesa la información? El Model Binding es el proceso automático por el cual ASP.NET Core mapea los datos de la petición HTTP (formularios, rutas, query strings) directamente a objetos y parámetros de C#. 🎓 **Analogía del Profesor**: > Imagina el **Model Binding** como el sistema de clasificación de equipaje de un aeropuerto. Tú (el cliente) entregas tus maletas (los datos HTTP) en el mostrador. El sistema lee las etiquetas, comprueba el peso y las dimensiones (Validación), y las envía automáticamente por l…

## 25. ¿Qué objetivo tiene el patrón Post-Redirect-Get tras procesar un formulario POST?

- **Fragmento oro:** `joseluisgs-05/03-formularios.md` orden **26** (procedimiento, 425 tok)
- **Origen de la pregunta:** 01-test.md p.8
- **Localización:** `lectura`

> …leer el contenido. En Razor Pages esto es automático, pero en MVC debes ser tú quien ponga el sello en cada acción POST. --- ## 3.3. Navegación Profesional: PRG y TempData ## 3.3. Navegación Profesional: PRG y TempData La navegación en aplicaciones web profesionales no se deja al azar. Dos de los problemas más comunes son el **re-envío de formularios al pulsar F5** y la **pérdida de mensajes de confirmación** tras una redirección. El binomio PRG + TempData es la solución estándar de la industria. ### 3.3.1. Patrón Post-Redirect-Get (PRG) El patrón PRG es una técnica de diseño web que evita que un usuario envíe accidentalmente un formulario varias veces. ❌ **El Problema (Ciclo sin PRG)**: 1. El usuario hace `POST` con sus datos. 2. El servid…

## 26. ¿Qué mecanismo se usa para enviar mensajes que sobreviven a una única redirección?

- **Fragmento oro:** `joseluisgs-05/03-formularios.md` orden **27** (procedimiento, 504 tok)
- **Origen de la pregunta:** 01-test.md p.9
- **Localización:** `lectura`

> …te over U, S: 4. El usuario pulsa F5 U->>S: GET /funkos/detalles/42 S-->>U: HTTP 200 OK (HTML) Note right of U: ✅ NO hay duplicados ``` ### 3.3.2. Mensajes Flash con TempData Al usar el patrón PRG, surge un nuevo reto: ¿Cómo le digo al usuario "¡Funko guardado con éxito!" si el `Redirect` limpia la memoria de la petición actual? La respuesta es **TempData**. Es un almacén temporal basado en sesión que **vive exactamente hasta que es leído una vez** (normalmente tras la primera redirección). #### Comparativa de Implementación: MVC vs Razor Pages…

## 27. ¿Cómo protege ASP.NET Core los formularios contra CSRF?

- **Fragmento oro:** `joseluisgs-05/03-formularios.md` orden **30** (explicacion, 440 tok)
- **Origen de la pregunta:** 01-test.md (bloque seguridad)
- **Localización:** `lectura`

> …limpia la memoria del servidor automáticamente, evitando que mensajes antiguos aparezcan cuando el usuario navega a otras secciones más tarde. --- ### 3.3.4. Protección CSRF (Antiforgery) El **Cross-Site Request Forgery (CSRF)** es un ataque silencioso donde un sitio malicioso engaña al navegador del usuario para que realice una acción no deseada en una aplicación en la que está autenticado.…

## 28. ¿Qué hace falta en el formulario para poder subir un fichero y qué tipo lo recibe en el servidor?

- **Fragmento oro:** `joseluisgs-05/03-formularios.md` orden **18** (explicacion, 485 tok)
- **Origen de la pregunta:** 01-test.md (bloque formularios)
- **Localización:** `lectura`

> …</span> </div> <button type="submit" class="btn btn-success">Guardar vía PageModel</button> </form> </div> ``` ### 3.2.2. El tipo IFormFile y el Enctype Para que el navegador pueda empaquetar y enviar un archivo binario... 🎓 **Analogía del Profesor**: > Imagina que el formulario estándar es un sobre de carta normal. Puedes meter texto, pero no una piedra (un archivo). Si quieres enviar una piedra, necesitas una **caja reforzada** (`multipart/form-data`). El `IFormFile` es el **albarán de entrega** que te dice cuánto pesa la piedra, cómo se llama y qué tipo de material es, permitiéndote decidir si la metes en tu almacén o la tiras a la basura. **A. Implementación en MVC (Vistas Normales)** * **1. El InputModel (`Mod…

## 29. ¿Por qué no basta con comprobar la extensión de un fichero subido?

- **Fragmento oro:** `joseluisgs-05/03-formularios.md` orden **19** (explicacion, 507 tok)
- **Origen de la pregunta:** 01-test.md (bloque formularios)
- **Localización:** `lectura`

> …eturn Page(); // Acceso directo vía this.Form.Imagen return RedirectToPage("./Index"); } } ``` ### 3.2.2. Validación de Seguridad: Magic Numbers vs Extensiones Validar solo la extensión (`.jpg`) es un error de principiante. Un hacker puede renombrar `virus.exe` a `foto.jpg`. La **validación profesional** comprueba los **Magic Numbers**: los primeros bytes que identifican la firma real del archivo.…

## 30. ¿Qué es FluentValidation y para qué se usa?

- **Fragmento oro:** `joseluisgs-05/03-formularios.md` orden **33** (explicacion, 508 tok)
- **Origen de la pregunta:** 01-test.md (bloque validacion)
- **Localización:** `lectura`

> …### 3.4.1. FluentValidation: Reglas de Negocio **El Validador (`Validators/FunkoCreateValidator.cs`)**: ```csharp using FluentValidation; public class FunkoCreateValidator : AbstractValidator<FunkoCreateInput> { public FunkoCreateValidator() { RuleFor(x => x.Nombre) .NotEmpty().WithMessage("Nombre obligatorio") .Length(3, 50).WithMessage("Entre 3 y 50 caracteres"); RuleFor(x => x.Imagen) .Must(img => img.Length < 2*1024*1024) .WithMessage("Máximo 2MB") .When(x => x.Imagen != null); } } ``` ### 3.4.2. Railway Oriented Programmi…

## 31. ¿Qué son los layouts y cómo permiten que las vistas hijas extiendan una plantilla base?

- **Fragmento oro:** `joseluisgs-05/02-razor-pages.md` orden **16** (explicacion, 341 tok)
- **Origen de la pregunta:** 01-test.md p.30
- **Localización:** `lectura`

> …_FunkoCard" model="funko" /> </div> } </div> } } ``` --- ## 2.3. Composición y Reutilización (Layouts) ### 2.3.1. El sistema de Layouts: _ViewStart.cshtml, _Layout.cshtml y _ViewImports.cshtml…

## 32. ¿Qué símbolo y qué delimitadores usa Razor para alternar entre código C# y HTML?

- **Fragmento oro:** `joseluisgs-05/02-razor-pages.md` orden **10** (codigo, 478 tok)
- **Origen de la pregunta:** 01-test.md p.26 y p.29
- **Localización:** `lectura`

> …Parámetros del método o `ViewModel` | | **Salida** | `return Page()` (la suya propia) | `return View()` (puede ser cualquiera) | --- ### 2.1.2. Delimitadores Razor: Diferencias entre @ (expresión) y @{ } (bloque de código) Razor utiliza el símbolo `@` como **delimitador** para diferenciar entre HTML estático y código C#. #### Tipos de delimitadores ```cshtml @* 1. EXPRESIONES INLINE: @ seguido de código C# *@ <h1>@Model.Nombre</h1> @* Genera: <h1>Funko Pop Darth Vader</h1> *@ <p>Precio: @Model.Precio.ToString("C")</p> <p>Precio con IVA: @(Model.Precio * 1.21m)</p>…

## 33. ¿Qué es un ViewComponent y en qué se diferencia de una vista parcial?

- **Fragmento oro:** `joseluisgs-05/02-razor-pages.md` orden **18** (explicacion, 369 tok)
- **Origen de la pregunta:** 01-test.md (bloque vistas)
- **Localización:** `lectura`

> …@* En la Vista Detalle.cshtml *@ @section Scripts { <script src="~/js/detalle-funkos.js"></script> } ``` ### 2.3.3. Componentes de UI: Vistas Parciales y ViewComponents | Herramienta | Analogía | Lógica (C#) | Cuándo usar | | :---------------- | :---------------- | :---------- | :------------------------------------------------------------------------------------------------------------------- | | **Vista Parcial** | Una Pegatina | ❌ No | Fragmentos repetitivos que solo muestran datos ya tienes (ej: una tarjeta de producto). | | **ViewComponent** | Un Robot Autónomo | ✅ Sí | Wid…

## 34. ¿Qué hace la directiva @page y dónde debe colocarse?

- **Fragmento oro:** `joseluisgs-05/02-razor-pages.md` orden **30** (explicacion, 381 tok)
- **Origen de la pregunta:** 01-test.md (bloque razor pages)
- **Localización:** `lectura`

> …directiva `@page` es obligatoria y debe ser la primerísima línea del archivo. Sin ella, el archivo es invisible para el sistema de navegación de .NET. 💡 **Metáfora de la Dirección Postal**: > Imagina que el servidor es una gran ciudad y tus archivos .cshtml son casas. Sin la directiva `@page`, tu casa no tiene número ni calle; nadie puede enviarte una carta. Al poner `@page`, estás inscribiendo tu casa en el callejero oficial de la ciudad. **¿Cómo crea la Vista las rutas?** Razor Pages usa una convención de "Carpetas = URLs", pero la directiva `@page` permite tomar el control total: | Ubicación física…

## 35. ¿Qué son los named handlers en Razor Pages?

- **Fragmento oro:** `joseluisgs-05/02-razor-pages.md` orden **26** (explicacion, 480 tok)
- **Origen de la pregunta:** 01-test.md (bloque razor pages)
- **Localización:** `lectura`

> …**: Carga el formulario vacío o la lista de datos. | | **`OnPost()`** | POST | **Creación**: Recibe los datos del formulario y los guarda. | #### 🎓 Los "Named Handlers" (Múltiples acciones en una página) - **C#**: `public IActionResult OnPostComprar() { ... }` - **HTML**: `<button asp-page-handler="Comprar">Comprar</button>` ### 2.4.4. Gestión de Estado y Model Binding: El Secreto de [BindProperty] 📝 **Nota del Profesor**: > En MVC los datos son "pasajeros" (argumentos de un método). En Razor Pages, los datos son **"miembros de la familia"** (propiedades de la clase). #### ¿Cómo funciona técnicamente? Cuando decoras una propiedad con `[BindProperty]`, le estás diciendo a .NET: "Cualquier dato en el formulario HTML que tenga el mismo nombre…

## 36. ¿Qué es ViewData y cómo se comparte entre el controlador y la vista?

- **Fragmento oro:** `joseluisgs-05/02-razor-pages.md` orden **35** (ejemplo_resuelto, 508 tok)
- **Origen de la pregunta:** 01-test.md p.20
- **Localización:** `lectura`

> …nde de su `PageModel` | | **Ideal para...** | APIs mixtas, sistemas complejos | Aplicaciones web, formularios, CRUDs | --- ### 2.4.8. ViewData: La Mochila Compartida Una de las dudas más frecuentes es: *¿Por qué el título de la pestaña del navegador cambia si todas las páginas usan el mismo `_Layout.cshtml`?* La respuesta es **ViewData**. #### A. Concepto y Funcionamiento `ViewData` es un diccionario compartido durante la petición. Imagina que es una **mochila** que lleva el cartero (la petición HTTP). 1. La **Vista** mete el título en la mochila. 2. El **Layout** abre la mochila y saca el título para ponerlo en la etiqueta `<title>`. ```mermaid sequenceDiagram participant V as Vista participant M as Mochila…

## 37. ¿Qué diferencia hay entre ViewData, TempData y las propiedades del PageModel para guardar estado?

- **Fragmento oro:** `joseluisgs-05/04-estado-seguridad.md` orden **6** (explicacion, 474 tok)
- **Origen de la pregunta:** 01-test.md p.9 y p.20
- **Localización:** `lectura`

> …r en GET (.cs) var msg = TempData["Exito"]; // Se elimina tras la primera lectura TempData.Keep("Exito"); // Opcional: mantener para otra petición ``` #### D. Comparativa técnica | Herramienta | Tipo | ¿Sobrevive Redirección? | Uso Ideal | | :------------- | :--------- | :---------------------- | :------------------------ | | **ViewData** | Dictionary | ❌ No | Casos legacy. | | **ViewBag** | Dynamic | ❌ No | Proyectos rápidos. | | **TempData** | Dictionary | ✅ Sí (1 vez) | Mensajes de confirmación. | | **ViewModels** | Class | ❌ No | **Estándar Profesional**. | --- ### 4.1.2. Cookies: Persistencia en el lado del Cliente…

## 38. ¿Qué atributos de seguridad tiene una cookie y para qué sirve cada uno?

- **Fragmento oro:** `joseluisgs-05/04-estado-seguridad.md` orden **7** (explicacion, 476 tok)
- **Origen de la pregunta:** 01-test.md (bloque estado)
- **Localización:** `lectura`

> …e: theme=dark Note left of S: .NET lee Request.Cookies["theme"]<br/>y renderiza oscuro. S-->>C: 200 OK (HTML Oscuro) ``` #### 4.1.2.1. Tipos de cookies y Atributos de Seguridad | Atributo | Propósito | Recomendación Docente | | :----------- | :------------------------------------ | :----------------------------- | | **HttpOnly** | Bloquea el acceso desde JavaScript. | ✅ Siempre para IDs de sesión. | | **Secure** | Solo se envía por HTTPS. | ✅ Siempre en Producción. | | **SameSite** | Protege contra ataques CSRF. | `Strict` o `Lax`. | | **Expires** | Define si es persistente o de sesión. | `DateTimeOffset.UtcNow.Add...` | #### 4.1.2.2. Operaciones CRUD: Esc…

## 39. ¿Cómo se configura la sesión en Program.cs y cómo se leen y escriben datos en ella?

- **Fragmento oro:** `joseluisgs-05/04-estado-seguridad.md` orden **10** (explicacion, 500 tok)
- **Origen de la pregunta:** 01-test.md (bloque sesiones)
- **Localización:** `lectura`

> …true; options.Cookie.Name = ".FunkoWorld.Session"; }); var app = builder.Build(); app.UseSession(); // ⚠️ DEBE IR DESPUÉS DE UseRouting ``` #### 4.1.3.2. Escritura y Lectura de Datos **A. Datos Básicos (Cadenas y Números)** La sesión funciona como un diccionario clave-valor. .NET proporciona métodos nativos para tipos simples. Es vital gestionar los valores nulos al recuperar datos. ```csharp // 1. ESCRITURA (En cualquier Controller o PageModel) HttpContext.Session.SetString("NombreUsuario", "Mario"); HttpContext.Session.SetInt32("Puntuacion", 1500); // 2. LECTURA // Recuperamos Strings (puede ser null) string nombre = HttpContext.Session.GetString("NombreUsuario") ?? "Invitado"; // Recuperamos Enteros (Devuelve int? nullable) int puntuac…

## 40. ¿Qué se hace con la sesión cuando hay varios servidores detrás de un balanceador?

- **Fragmento oro:** `joseluisgs-05/04-estado-seguridad.md` orden **11** (explicacion, 484 tok)
- **Origen de la pregunta:** 01-test.md (bloque sesiones)
- **Localización:** `lectura`

> …Json("MiCarrito", carrito); // Recuperar objeto complejo var miCarrito = HttpContext.Session.GetJson<List<CartItem>>("MiCarrito") ?? new(); ``` #### 4.1.3.3. Sesiones Distribuidas (Redis) Cuando tenemos varios servidores web (granja), la memoria RAM local no sirve porque cada servidor tiene la suya. Usamos **Redis** como almacén centralizado. ```csharp // Program.cs builder.Services.AddStackExchangeRedisCache(options => { options.Configuration = "localhost:6379"; }); ``` #### 4.1.3.4. Simetría en el Acceso al Contexto: MVC vs Razor Pages Dependiendo del paradigma que uses, el acceso al objeto de sesión varía ligeramente en su sintaxis, aunque el funcionamiento es idéntico.…

## 41. ¿Qué son los claims y el ClaimsPrincipal en la autenticación?

- **Fragmento oro:** `joseluisgs-05/04-estado-seguridad.md` orden **13** (explicacion, 466 tok)
- **Origen de la pregunta:** 01-test.md (bloque autenticacion)
- **Localización:** `lectura`

> …ng.Empty; public string PasswordHash { get; set; } = string.Empty; public Rol Rol { get; set; } = default!; // 🛡️ Relación 1:1 con Rol } ``` ### 4.2.2. Claims y ClaimsPrincipal: El Pasaporte Digital En .NET, la identidad es una cebolla de tres capas: 1. **Claim**: El dato atómico (ej: "Email: ana@dev.com"). 2. **ClaimsIdentity**: El conjunto de claims (la página del pasaporte). 3. **ClaimsPrincipal**: El sujeto que porta una o varias identidades. ```mermaid graph TD CP["ClaimsPrincipal (Sujeto)"] --> CI["ClaimsIdentity (Pasaporte)"] CI --> C1["Claim: Email"] CI --> C2["Claim: Rol (Extraído de Usuario.Rol)"] CI --> C3["Claim: UserId"] style CP fill:#f9f,stroke:#333,color:#000 style CI fill:#cfc,stroke:#333,color:#…

## 42. ¿Cómo se deben guardar las contraseñas de los usuarios?

- **Fragmento oro:** `joseluisgs-05/04-estado-seguridad.md` orden **17** (explicacion, 509 tok)
- **Origen de la pregunta:** 01-test.md (bloque autenticacion)
- **Localización:** `lectura`

> …context.Succeed(requirement); return Task.CompletedTask; } } ``` --- ### 4.2.5. Hashing Seguro de Contraseñas con BCrypt **NUNCA** guardes en texto plano. BCrypt es el estándar por su Salt automático y su "Work Factor" (lentitud intencional). Aunque en **Identity** esto es automático, en el modo manual debemos usar la interfaz del framework. | Algoritmo | Seguridad | Velocidad | Recomendación | | :--------- | :-------- | :---------------- | :------------------------ | | **MD5** | ❌ Nula | Instantáneo | Prohibido. | | **SHA256** | ⚠️ Baja | Rápido | No apto para contraseñas. | | **BCrypt** | ✅ Alta | Lento…

## 43. ¿Qué anotación indica que una acción requiere autenticación y cómo se protegen rutas por política?

- **Fragmento oro:** `joseluisgs-05/04-estado-seguridad.md` orden **21** (explicacion, 459 tok)
- **Origen de la pregunta:** 01-test.md p.25
- **Localización:** `lectura`

> …View("Lockout"); // Cuenta bloqueada temporalmente ModelState.AddModelError(string.Empty, "Credenciales inválidas"); return View(model); } ``` ### 4.3.4. Protección de Rutas y Políticas: MVC vs Razor Pages Una vez autenticado el usuario, debemos decidir **qué puede ver**. En .NET moderno, esto se hace mediante **Políticas (Policies)** que agrupan roles o claims. **1. Definición de Políticas (Program.cs)** Antes de proteger nada, definimos las reglas del juego en el contenedor de servicios. ```csharp builder.Services.AddAuthorization(options => { // Política Simple: Solo requiere un Rol options.AddPolicy("EsAdmin", policy => policy.RequireRole("Admin"));…

## 44. ¿En qué consiste un ataque XSS y cómo lo previene Razor al renderizar variables?

- **Fragmento oro:** `joseluisgs-05/04-estado-seguridad.md` orden **24** (explicacion, 505 tok)
- **Origen de la pregunta:** 01-test.md p.28
- **Localización:** `lectura`

> …da el token en cada método OnPost() por defecto. // No necesitas añadir [ValidateAntiForgeryToken] a menos que lo hayas desactivado globalmente. ``` ### 4.4.2. XSS (Cross-Site Scripting) **El Ataque:** Un usuario inyecta `<script>alert('hack')</script>` en un comentario. Si la web lo renderiza tal cual, el script se ejecuta en el navegador de otros usuarios. **La Defensa (.NET):** Codificación automática.…

## 45. ¿Qué son los Tag Helpers y qué ventaja tienen frente a los HtmlHelper?

- **Fragmento oro:** `joseluisgs-05/05-tags-helper.md` orden **3** (ejemplo_resuelto, 480 tok)
- **Origen de la pregunta:** 01-test.md (bloque tag helpers)
- **Localización:** `lectura`

> …Ejemplo 4: Tag Helper Condicional (Modificador)](#535-ejemplo-4-tag-helper-condicional-modificador) - [5.4. Resumen](#54-resumen) --- ## 5.1. Tag Helpers: Simplificación de la Sintaxis HTML Los **Tag Helpers** son una característica de Razor que permite escribir código del lado del servidor usando sintaxis HTML natural, haciendo el código más limpio y fácil de leer. 🎓 **Analogía del Profesor**: > Los Tag Helpers son como autocorrector inteligente para HTML. En lugar de escribir código C# mezclado con HTML (`@Html.TextBoxFor()`), escribes HTML normal (`<input asp-for="Nombre" />`) y el Tag Helper añade automáticamente todos los atributos necesarios (name, id, validación, etc.). En .NET 10, los Tag Helpers han evolucionado para ser…

## 46. ¿Cuál es el framework de seguridad integrado en ASP.NET Core para autenticación y autorización?

- **Fragmento oro:** `joseluisgs-05/04-estado-seguridad.md` orden **18** (explicacion, 495 tok)
- **Origen de la pregunta:** 01-test.md p.13
- **Localización:** `lectura`

> …tokens de email, 2FA (Doble factor), bloqueos por intentos fallidos y más. ### 4.3.1. Arquitectura de Modelos y DbContext (C# 14) Identity abstrae la gestión mediante herencia de clases del framework, creando automáticamente un esquema de tablas optimizado. **Esquema de Base de Datos (Simplificado):** ```mermaid erDiagram AspNetUsers ||--o{ AspNetUserRoles : "tiene" AspNetRoles ||--o{ AspNetUserRoles : "se asigna a" AspNetUsers { string Id PK string Email string PasswordHash string SecurityStamp } AspNetRoles { string Id PK string Name } AspNetUserRoles { string UserId FK string RoleId FK…

## 47. ¿Qué diferencia hay entre una excepción checked y una unchecked en Java?

- **Fragmento oro:** `joseluisgs-02/java/06-ExcepcionesJava.md` orden **1** (explicacion, 480 tok)
- **Origen de la pregunta:** 01-test-java.md (bloque excepciones)
- **Localización:** `lectura`

> …- [6. Manejo de errores y excepciones](#6-manejo-de-errores-y-excepciones) - [6.1. Tipos de excepciones: `checked` vs. `unchecked`](#61-tipos-de-excepciones-checked-vs-unchecked) - [6.2. Manejo de excepciones: `try-catch-finally`](#62-manejo-de-excepciones-try-catch-finally) - [6.3. El uso de `try-with-resources`](#63-el-uso-de-try-with-resources) - [6.4. Creación de excepciones personalizadas](#64-creación-de-excepciones-personalizadas) # 6. Manejo de errores y excepciones ## 6.1. Tipos de excepciones: `checked` vs. `unchecked` Las excepciones en Java se dividen en dos categorías principales. ### Árbol de Jerarquía de Excepciones en Java ```mermaid classDiagram direction TB class…

## 48. ¿Para qué sirve try-with-resources y qué problema evita?

- **Fragmento oro:** `joseluisgs-02/java/06-ExcepcionesJava.md` orden **4** (explicacion, 498 tok)
- **Origen de la pregunta:** 01-test-java.md (bloque excepciones)
- **Localización:** `lectura`

> …// Un catch genérico para cualquier otra excepción System.err.println("Ocurrió un error inesperado."); } } } ``` ## 6.3. El uso de `try-with-resources` Añadido en Java 7, esta estructura es una mejora del `try-catch` tradicional. Su objetivo es asegurar que los recursos que implementan la interfaz `AutoCloseable` (como archivos o conexiones a bases de datos) se cierran automáticamente, incluso si ocurre una excepción.…

## 49. ¿Cómo se crea una excepción personalizada en Java?

- **Fragmento oro:** `joseluisgs-02/java/06-ExcepcionesJava.md` orden **5** (explicacion, 478 tok)
- **Origen de la pregunta:** 01-test-java.md (bloque excepciones)
- **Localización:** `lectura`

> …System.err.println("Error de E/S: " + e.getMessage()); } // El reader se cierra automáticamente, sin necesidad de un bloque finally ``` ## 6.4. Creación de excepciones personalizadas…

## 50. ¿Qué es el encapsulamiento en programación orientada a objetos?

- **Fragmento oro:** `joseluisgs-02/java/04-POO.md` orden **5** (explicacion, 503 tok)
- **Origen de la pregunta:** 01-test-java.md (bloque POO)
- **Localización:** `lectura`

> …## 4.3. Principios de la POO Estos cuatro pilares son fundamentales para diseñar software de forma eficiente, escalable y mantenible. ### 4.3.1. Encapsulamiento Es el principio de agrupar los datos (atributos) y los métodos que operan sobre esos datos en una sola unidad (la clase), ocultando la implementación interna. Esto se logra principalmente con los modificadores de acceso (`private`, `public`, `protected`) y los métodos **"getters" y "setters"**. Ocultar los datos a través de la encapsulación se conoce como **ocultación de información**. **Ejemplo:** ```java public class CuentaBancaria { private double saldo; // El saldo es privado, no accesible directamente public CuentaBancaria(double saldoInicial) { this.saldo…

## 51. ¿Qué es el polimorfismo y qué permite hacer?

- **Fragmento oro:** `joseluisgs-02/java/04-POO.md` orden **6** (explicacion, 490 tok)
- **Origen de la pregunta:** 01-test-java.md (bloque POO)
- **Localización:** `lectura`

> …Pi-pi!"); } } // La clase Coche hereda de Vehiculo public class Coche extends Vehiculo { public Coche() { this.ruedas = 4; } } ``` ### 4.3.3. Polimorfismo Significa "muchas formas". Permite que objetos de diferentes clases, que están relacionadas por herencia, sean tratados como objetos de una superclase común. Esto se logra mediante la **sobrescritura de métodos (`@Override`)** o la **sobrecarga de métodos**. **Ejemplo de Polimorfismo por sobrescritura:** ```java public class Animal { public void sonido() { System.out.println("El animal hace un sonido."); } } public class Gato extends Animal { @Override public void sonido() { System.out.println("El gato maúlla."); } } public class Perro extend…

## 52. ¿Cuál es la diferencia entre una interfaz y una clase abstracta?

- **Fragmento oro:** `joseluisgs-02/java/04-POO.md` orden **7** (explicacion, 487 tok)
- **Origen de la pregunta:** 01-test-java.md (bloque POO)
- **Localización:** `lectura`

> …abstractas** e **interfaces**. ## 4.4. Interfaces y clases abstractas Ambos son mecanismos clave para lograr la **abstracción**. ### 4.4.1. Clases abstractas Son clases que no se pueden instanciar directamente y pueden contener métodos `abstract` (sin implementación) y métodos concretos (con implementación). Una subclase que hereda de una clase abstracta debe proporcionar una implementación para todos los métodos abstractos, a menos que también sea abstracta. **Ejemplo:** ```java public abstract class FiguraGeometrica { public abstract double calcularArea(); // Método abstracto sin cuerpo public void mostrarMensaje() { // Método conc…

## 53. ¿Qué es un record en Java y para qué se usa?

- **Fragmento oro:** `joseluisgs-02/java/04-POO.md` orden **9** (explicacion, 398 tok)
- **Origen de la pregunta:** 01-test-java.md (bloque POO)
- **Localización:** `lectura`

> …atributos mutables, constructores, "getters", "setters" y cualquier lógica de negocio. Requieren que el programador escriba mucho código repetitivo. ### 4.6.2. Records (Añadidos en Java 16) Son un tipo de clase especial, inmutable y concisa, diseñada para ser un simple contenedor de datos. El compilador de Java genera automáticamente el constructor, los "getters" (conocidos como métodos de acceso), los métodos `equals()`, `hashCode()` y `toString()`. Son ideales para modelos de datos sencillos. **Ejemplo de clase Record vs. una clase normal:** ```java // Clase tradicional (código extenso) public class PersonaClasica { private final String nombre; private final int edad; public PersonaClasica(String nombre, int edad) { this.nombre…

## 54. ¿Cuáles son los cinco principios SOLID?

- **Fragmento oro:** `joseluisgs-02/java/07-PatronesArquitecturas.md` orden **1** (explicacion, 461 tok)
- **Origen de la pregunta:** 01-test-java.md (bloque patrones)
- **Localización:** `lectura`

> …- [7. Patrones y tipos de arquitecturas en Servidor](#7-patrones-y-tipos-de-arquitecturas-en-servidor) - [7.1. Principios SOLID](#71-principios-solid) - [7.2. Patrones de Diseño](#72-patrones-de-diseño) - [7.3. Arquitecturas Software](#73-arquitecturas-software) - [7.3.1. Diagrama Comparativo de Arquitecturas](#731-diagrama-comparativo-de-arquitecturas) - [7.4. Ejemplo de arquitectura de Netflix](#74-ejemplo-de-arquitectura-de-netflix) - [7.5. API Web](#75-api-web) # 7. Patrones y tipos de arquitecturas en Servidor. ## 7.1. Principios SOLID Los cinco principios SOLID son un conjunto de reglas y mejores prácticas para el diseño de software orientado a objetos. [Video SOLID](https://www.youtube.com/w…

## 55. ¿Qué es un test unitario y cómo se escribe con JUnit?

- **Fragmento oro:** `joseluisgs-02/java/10-Testing.md` orden **1** (explicacion, 436 tok)
- **Origen de la pregunta:** 01-test-java.md (bloque testing)
- **Localización:** `lectura`

> …- [10. Testeo y pruebas de aplicaciones en el lado del servidor.](#10-testeo-y-pruebas-de-aplicaciones-en-el-lado-del-servidor) - [10.1. Test unitarios con JUnit](#101-test-unitarios-con-junit) - [10.2. Test con dobles](#102-test-con-dobles) # 10. Testeo y pruebas de aplicaciones en el lado del servidor. > 📝 **Nota del Profesor**: "No hay código sin test" debería ser tu mantra. El testing no es opcional, es parte integral del desarrollo profesional. ## 10.1. Test unitarios con JUnit Un test unitario es una forma de comprobar el correcto funcionamiento de una unidad individual de código fuente. Esta "unidad" puede ser una función, un método, una clase, un módulo, etc. Los tests unitarios son una parte fundamental de la meto…

## 56. ¿Qué son los dobles de prueba y cuándo se usan?

- **Fragmento oro:** `joseluisgs-02/java/10-Testing.md` orden **3** (explicacion, 504 tok)
- **Origen de la pregunta:** 01-test-java.md (bloque testing)
- **Localización:** `lectura`

> …es falsa. - `assertNull(object)`: Verifica que un objeto es nulo. - `assertNotNull(object)`: Verifica que un objeto no es nulo. ## 10.2. Test con dobles Los "dobles de prueba" (test doubles) son sustitutos de los componentes del sistema que tu código está diseñado para interactuar. Los "dobles de prueba" pueden ser útiles cuando los componentes reales son difíciles o imposibles de incorporar en un test unitario o simplemente quieres hacer un test unitario sin realizar la integración de dicho componente, o simular su comportamiento.…

## 57. ¿De qué tres partes se compone un JWT?

- **Fragmento oro:** `joseluisgs-02/java/14-HTTP_REST.md` orden **5** (ejemplo_resuelto, 465 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque seguridad)
- **Localización:** `lectura`

> …lita la expansión del sistema sin preocuparse de la gestión de sesiones. ![token01](../images/jwt01.jpg) ## Partes Un JWT (JSON Web Token) está compuesto por tres partes principales, y cada una está separada por un punto (`.`): 1. **Header** (Encabezado) 2. **Payload** (Carga Útil) 3. **Signature** (Firma) ![token02](../images/jwt02.png) ### Estructura de un JWT Un JWT completo podría verse algo así: ``` eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c ``` ### 1. Header (Encabezado) #### Propósito El encabezado típicamente consiste en dos partes: el tipo de token (que es JWT) y el algoritmo de firma utilizado (por ejemplo, HMAC SHA256 o…

## 58. ¿Qué métodos HTTP existen y qué acción representa cada uno en una API REST?

- **Fragmento oro:** `joseluisgs-02/springboot/02-REST.md` orden **6** (explicacion, 468 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque REST)
- **Localización:** `lectura`

> …> Siempre usa plural en endpoints: `/users` NO `/user`. Esto es un error muy común en el examen. - Evita utilizar verbos en las URL. En su lugar, utiliza los métodos HTTP para representar acciones. Por ejemplo, `GET /users` para obtener la lista de usuarios, `POST /users` para crear un nuevo usuario, `PUT /users/{id}` para actualizar un usuario específico, y `DELETE /users/{id}` para eliminar un usuario específico. ⚠️ **Advertencia** > ERROR: `/users/create` con POST > CORRECTO: `/users` con POST Ten en cuenta que una URL debe identificar un recurso específico, y no una acción. Por ejemplo, `/users/123` es una URL válida, pero `/users/create` no lo es. ## 2.6. Métodos HTTP Los métodos HTTP representan las acciones que se pueden realizar sobre u…

## 59. ¿Qué significan los códigos de estado HTTP en la respuesta de una API?

- **Fragmento oro:** `joseluisgs-02/springboot/02-REST.md` orden **8** (definicion, 427 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque REST)
- **Localización:** `lectura`

> …servicios web que pueden ser utilizados por múltiples clientes, incluyendo navegadores web, aplicaciones móviles, y otros servidores. ## 2.7. Respuestas Los códigos de estado HTTP son una parte integral de cómo funcionan los servicios web y la arquitectura REST. Estos códigos son la manera en que un servidor informa al cliente sobre el resultado de su solicitud, y pueden tener un contenido asociado. Por ejemplo, si realizas una solicitud GET a un servidor y el recurso solicitado se encuentra, el servidor devolverá un código 200 OK junto con el recurso solicitado en el cuerpo de la respuesta. ```mermaid flowchart TD subgraph "Códigos de Estado HTTP" 2xx["2xx Éxito<br/>✅"] 4xx["4xx Error Cliente<br/>❌"] 5xx["5xx Error Se…

## 60. ¿Qué es una API REST y qué características tiene?

- **Fragmento oro:** `joseluisgs-02/springboot/02-REST.md` orden **4** (explicacion, 462 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque REST)
- **Localización:** `lectura`

> …do a la falta de un estándar de seguridad integrado. - No son la mejor opción para operaciones que requieren el mantenimiento de un estado de conexión. ## 2.4. API REST (RestFul) Una API REST (Representational State Transfer) es un estilo de arquitectura de software que se utiliza en el desarrollo de aplicaciones web. REST se basa en principios y estándares que permiten construir interfaces de programación de aplicaciones (API) de una manera coherente y predecible. 📝 **Nota del Profesor** > API REST y API RESTful son lo mismo. El término "RESTful" simplemente indica que la API sigue todos los principios REST. La API REST utiliza métodos HTTP estándar, como GET, POST, DELETE y PUT, para realizar operaciones en los recursos. Los recursos, que son c…

## 61. ¿Por qué conviene versionar una API y cómo se hace?

- **Fragmento oro:** `joseluisgs-02/springboot/02-REST.md` orden **11** (ejemplo_resuelto, 437 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque REST)
- **Localización:** `lectura`

> …Útil"] Formato["Formato<br/>Estándar"] end Error["Error"] --> Codigo Error --> Mensaje Error --> Detalle Error --> Formato ``` ## 2.9. Versionado Es aconsejable versionar tu API para que puedas hacer cambios y mejoras sin romper las aplicaciones existentes que utilizan tu API. Una forma común de hacer esto es incluir el número de versión en la URL, como en `/v1/users`. ```mermaid graph LR subgraph "Estrategias de Versionado" URL["/v1/users"] Header["Accept: v1"] Param["?version=1"] end Cliente --> URL ``` 💡 **Tip del Examinador** > La forma más común y sencilla es versionar por URL: `/v1/users`. Es lo que se espera en el examen. ## 2.10. Ejemplo de diseño de acceso de un recurso…

## 62. ¿Qué es un PasswordEncoder en Spring Security?

- **Fragmento oro:** `joseluisgs-02/springboot/12-Seguridad.md` orden **24** (definicion, 503 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque seguridad)
- **Localización:** `lectura`

> …nticationManager authenticationManager(AuthenticationConfiguration config) throws Exception { return config.getAuthenticationManager(); } } ``` #### 12.2.7.1. PasswordEncoder PasswordEncoder es una interfaz en Spring Security que se utiliza para codificar y descifrar contraseñas. La codificación de contraseñas es una práctica importante en seguridad de aplicaciones web, ya que las contraseñas se almacenan generalmente en bases de datos y, por lo tanto, es importante protegerlas de posibles amenazas externas, como ataques de hackers. En concreto, PasswordEncoder se utiliza para codificar la contraseña proporcionada por el usuario antes de almacenarla en la base de datos. La codificación de contraseñas se realiza utilizando algoritmos de cifrado hash…

## 63. ¿Qué hace el filtro de autenticación JWT en Spring Security?

- **Fragmento oro:** `joseluisgs-02/springboot/12-Seguridad.md` orden **17** (explicacion, 437 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque seguridad)
- **Localización:** `lectura`

> …jwtService.generateToken(user); return JwtAuthenticationResponse.builder().token(jwt).build(); } } ``` ### 12.2.6. Filtro de autenticación JWT Un authentication filter en Spring Boot es un tipo de filtro de seguridad que se utiliza para autenticar las solicitudes de los usuarios en una aplicación web. Los filtros de autenticación en Spring Boot se ejecutan antes de que se procese la solicitud del usuario y se utilizan para validar la identidad del usuario y determinar si se le permite acceder a los recursos protegidos por la aplicación. En definitiva es un middleware que actúa por cada request para decir si debe o no ser atendida la petición. El filtro personalizado extiende [OncePerRequestFilter](https://docs.spring.io/spring-framewor…

## 64. ¿Qué anotaciones permiten restringir el acceso a un método de controlador por rol?

- **Fragmento oro:** `joseluisgs-02/springboot/12-Seguridad.md` orden **28** (explicacion, 451 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque seguridad)
- **Localización:** `lectura`

> …rmente: .authorizeHttpRequests(request -> request.requestMatchers(GET, "/storage/**").hasAnyAuthority(ADMIN_READ.name(), MANAGER_READ.name())) #### 12.2.7.5. Anotaciones en controladores o métodos de controladores…

## 65. ¿Qué diferencia hay entre autenticación y autorización?

- **Fragmento oro:** `joseluisgs-02/springboot/12-Seguridad.md` orden **3** (explicacion, 482 tok)
- **Origen de la pregunta:** 04-test-springboot.md (bloque seguridad)
- **Localización:** `lectura`

> …cnologías de Spring, como Spring MVC, Spring Boot y Spring Data. Esto facilita la implementación de la seguridad en aplicaciones existentes o nuevas. ## 12.1. Autenticación y Autorización Imaginemos que queremos conseguir que: - El usuario hace una solicitud al servicio, buscando crear una cuenta. - Un usuario envía una solicitud al servicio para autenticar su cuenta. - Un usuario autenticado envía una solicitud para acceder a recursos, y solo lo hará dependiendo de su rol. ![auth](../images/auth01.webp) ### 12.1.1. Configurando Spring Security Lo primero que debemos hacer es añadir las dependencias de Spring Security a nuestro proyecto. Usando Gradle ```kotlin implementation("org.springframework.boot:spring-boot-starter-security") // Dependenc…

## 66. ¿Qué es la inyección de dependencias y qué problema resuelve?

- **Fragmento oro:** `joseluisgs-04/netcore/04-inyeccion-dependencias.md` orden **4** (explicacion, 481 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque DI)
- **Localización:** `lectura`

> …4.10. Resumen](#410-resumen) - [4.11. Ejercicio Propuesto](#411-ejercicio-propuesto) --- ## 4.1. Fundamentos de la Inyección de Dependencias ### 4.1.1. ¿Qué es la Inyección de Dependencias? La **inyección de dependencias (DI)** es un patrón de diseño donde un objeto no crea sus propias dependencias, sino que las recibe desde el exterior. En ASP.NET Core, DI es el patrón arquitectónico más importante. Es el mecanismo que permite que tus controladores y servicios reciban sus dependencias (repositorios, loggers, servicios externos) en lugar de crearlas internamente. 🧠 **Analogía**: En un restaurante, el mesero (controlador) toma tu pedido, el chef (servicio) prepara la comida siguiendo la receta (lógica de negocio), y el almacenista (repositori…

## 67. ¿Cuáles son los tres tiempos de vida de un servicio en ASP.NET Core?

- **Fragmento oro:** `joseluisgs-04/netcore/04-inyeccion-dependencias.md` orden **8** (explicacion, 483 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque DI)
- **Localización:** `lectura`

> …| **Reutilización** | Compartir implementaciones entre servicios | ## 4.2. Tiempos de Vida de los Servicios ### 4.2.1. Los Tres Tiempos de Vida En ASP.NET Core, cada servicio registrado en el contenedor DI tiene un **tiempo de vida** que determina cuándo se crea y cuándo se destruye la instancia. Elegir el tiempo de vida correcto es crucial para el funcionamiento correcto de tu aplicación y para evitar bugs sutiles relacionados con el estado compartido. **Transient** crea una nueva instancia cada vez que el servicio es solicitado. Es ideal para servicios ligeros, sin estado, que deben ser independientes entre peticiones. Si solicitas el servicio dos veces en la misma petición, получишь dos instancias diferentes.…

## 68. ¿Cómo se registran los servicios en Program.cs?

- **Fragmento oro:** `joseluisgs-04/netcore/04-inyeccion-dependencias.md` orden **19** (explicacion, 491 tok)
- **Origen de la pregunta:** 04-test-aspcore.md p.19
- **Localización:** `lectura`

> …["Facil de entender dependencias"] end A1 --> A2 --> A3 B1 --> B2 --> B3 C1 --> C2 --> C3 ``` ## 4.6. Registro de Servicios en Program.cs ### 4.6.1. Registro Básico de Servicios ```csharp var builder = WebApplication.CreateBuilder(args); // Registrar servicios uno por uno builder.Services.AddScoped<IProductoRepository, ProductoRepository>(); builder.Services.AddScoped<ICategoriaRepository, CategoriaRepository>(); builder.Services.AddScoped<IPedidoRepository, PedidoRepository>(); builder.Services.AddScoped<IProductoService, ProductoService>(); builder.Services.AddScoped<ICategoriaService, CategoriaService>(); builder.Services.AddScoped<IPedidosService, PedidosService>(); ``` ### 4.6.2. Métodos de Extensión para Organizar el Registro En…

## 69. ¿Qué es Problem Details y qué estándar sigue?

- **Fragmento oro:** `joseluisgs-04/netcore/04-inyeccion-dependencias.md` orden **23** (explicacion, 499 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque errores)
- **Localización:** `lectura`

> …equest.Path, Type = $"https://httpstatuses.com/{statusCode}" }; return context.Response.WriteAsJsonAsync(problem); } } ``` ### 4.7.3. Problem Details (RFC 7807) El estándar RFC 7807 define un formato JSON consistente para errores:…

## 70. ¿Qué es la negociación de contenido en una API?

- **Fragmento oro:** `joseluisgs-04/netcore/05-patron-result.md` orden **6** (explicacion, 426 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque REST)
- **Localización:** `lectura`

> …fill:#0D47A1 style C fill:#E65100 style D fill:#4A148C style E fill:#B71C1C style F fill:#3E2723 ``` 🧠 **Analogía**: Piensa en una API como un restaurante. La negociación de contenido es como pedir el plato en diferente presentación (plato hondo, bowl, tupper). La paginación es como servir la comida por platos, no todo junto. Los filtros son como pedir sin gluten o vegano. Los links HATEOAS son como el camarero que te indica dónde está el baño y la salida. El patrón Result es como el chef que te dice claramente si el plato está listo o qué problema hay, en lugar de lanzar alertas cuando algo falta. --- ## 5.2. Negociación de Contenido ### 5.2.1. ¿Qué es la Negociación de Contenido? La **negociación de contenido** es un mecanismo que permite al c…

## 71. ¿Por qué hace falta paginar los resultados de una API?

- **Fragmento oro:** `joseluisgs-04/netcore/05-patron-result.md` orden **10** (explicacion, 416 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque paginacion)
- **Localización:** `lectura`

> …un comportamiento más permisivo, puedes omitir esta opción y solo configurar los formateadores que soportas. --- ## 5.3. Paginación y Ordenación ### 5.3.1. ¿Por qué Paginación? La **paginación** es el proceso de dividir grandes conjuntos de datos en páginas manejables. Es una de las características más importantes de cualquier API que devuelva colecciones, especialmente cuando el volumen de datos puede ser grande.…

## 72. ¿Qué es HATEOAS y cómo se aplica a los enlaces de paginación?

- **Fragmento oro:** `joseluisgs-04/netcore/05-patron-result.md` orden **23** (explicacion, 486 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque paginacion)
- **Localización:** `lectura`

> …pi/funkos?pageNumber=2&pageSize=20&sortBy=nombre&direction=asc HTTP/1.1 Accept: application/json ``` --- ## 5.4. Enlaces de Paginación en Headers ### 5.4.1. HATEOAS y Links de Paginación **HATEOAS** (Hypertext As The Engine Of Application State) es un principio REST que indica que la respuesta debe incluir enlaces para navegar por los estados de la aplicación. Para paginación, esto significa incluir enlaces a la primera página, página anterior, página siguiente y última página. Los enlaces de paginación en headers son una práctica profesional que sigue el estándar RFC 5988 (Web Linking). Esto permite que los clientes naveguen por las páginas sin tener que construir las URLs manualmente, y separa claramente los datos de los metadatos de navegació…

## 73. ¿Qué es el patrón Repository y qué problema resuelve?

- **Fragmento oro:** `joseluisgs-04/netcore/06-repository-pattern.md` orden **3** (explicacion, 499 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque repositorios)
- **Localización:** `lectura`

> …- [6.10. Resumen](#610-resumen) --- ## 6.1. Introducción al Repository Pattern ### 6.1.1. ¿Qué es el Repository Pattern? El **Repository Pattern** (Patrón Repositorio) es un patrón de diseño que abstrae el acceso a datos, proporcionando una interfaz limpia para las operaciones de CRUD (Create, Read, Update, Delete) y consultas. Este patrón separa la lógica de acceso a datos de la lógica de negocio, permitiendo cambiar la implementación de persistencia (por ejemplo, de PostgreSQL a MongoDB) sin afectar el código de los servicios que lo utilizan. 🧠 **Analogía**: Imagina un biblioteca. En lugar de que cada usuario vaya directamente a la sala de archivos…

## 74. ¿Para qué sirve un repositorio genérico?

- **Fragmento oro:** `joseluisgs-04/netcore/06-repository-pattern.md` orden **15** (explicacion, 458 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque repositorios)
- **Localización:** `lectura`

> …n una transacción await _context.SaveChangesAsync(); return pedido; } } ``` --- ## 6.3. Repository Genérico ### 6.3.1. Interfaz IRepository<T> Para evitar repetición, puedes crear un repositorio genérico con las operaciones CRUD básicas que todas las entidades comparten. ```csharp namespace FunkosApi.Core.Interfaces; public interface IRepository<T> where T : class { // Consultas básicas Task<T?> FindById(long id); Task<List<T>> GetAll(); Task<List<T>> GetByIds(IEnumerable<long> ids); // Verificaciones Task<bool> ExistsById(long id); // Modificación Task<T> Save(T entity); Task<T> Update(T entity); Task<bool> Delete(long id); } ``` ### 6.3.2. Implementación Genérica ```csharp using Microsoft.Entit…

## 75. ¿Qué relación hay entre el DbContext y el patrón Unit of Work?

- **Fragmento oro:** `joseluisgs-04/netcore/06-repository-pattern.md` orden **26** (explicacion, 445 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque repositorios)
- **Localización:** `lectura`

> …sPorStock(int topN) { return await _context.Funkos .OrderByDescending(f => f.Stock) .Take(topN) .ToListAsync(); } ``` --- ## 6.6. Unit of Work con EF Core ### 6.6.1. DbContext como Unit of Work Entity Framework Core ya implementa el patrón Unit of Work internamente. El DbContext rastrea todos los cambios realizados a las entidades y los persiste en una sola transacción cuando llamas a `SaveChangesAsync()`. ```mermaid flowchart TB subgraph "Operaciones en memoria" A[Funko Added] --> B[Change Tracker] B --> C[Categoria Modified] C --> B B --> D[Pedido Deleted] D --> B end subgraph "SaveChangesAsync" E[Validar cambios] E --> F[Generar SQL] F --> G[E…

## 76. ¿Qué es la arquitectura en capas y qué ventajas e inconvenientes tiene?

- **Fragmento oro:** `joseluisgs-04/netcore/09-clean-architecture.md` orden **5** (definicion, 433 tok)
- **Origen de la pregunta:** 04-test-aspcore.md p.22
- **Localización:** `lectura`

> …que se protege de los cambios externos mediante capas sucesivas de proteccion. --- ## 9.2. Arquitectura en Capas ### 9.2.1. Conceptos Fundamentales La **arquitectura en capas** (Layered Architecture) es uno de los patrones arquitectonicos mas antiguos y utilizados en el desarrollo de software. Su principio fundamental es organizar el codigo en capas horizontales, donde cada capa tiene una responsabilidad especifica y solo se comunica con las capas adyacentes en una direccion definida. Este patron promueve la separación de preocupaciones y facilita el mantenimiento del sistema al aislar las diferentes areas de responsabilidad. El concepto clave de esta arquitectura es la **separaci…

## 77. ¿Qué dice la regla de dependencia de Clean Architecture?

- **Fragmento oro:** `joseluisgs-04/netcore/09-clean-architecture.md` orden **15** (explicacion, 489 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque arquitectura)
- **Localización:** `lectura`

> …Esta independencia se logra mediante la aplicación estricta de la **Regla de Dependencia**, que establece que las dependencias de codigo solo pueden apuntar hacia adentro. La filosofia detras de Clean Architecture es crear sistemas que sean **resistentes al cambio tecnologico**. Los frameworks, bases de datos y interfaces de usuario son detalles que pueden y deben cambiar con el tiempo, pero las reglas de negocio deben permanecer estables. Al aislar las reglas de negocio de los detalles de implementación, el sistema puede evoluciónar tecnologicamente sin afectar la logica central del negocio. Los principios fundamentales de Clean Architecture se derivan de d…

## 78. ¿Qué problema tienen las excepciones como mecanismo de control de errores y qué propone ROP?

- **Fragmento oro:** `joseluisgs-04/netcore/09-clean-architecture.md` orden **27** (definicion, 437 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque ROP)
- **Localización:** `lectura`

> …| Facil extension del sistema | Alta | --- ## 9.5. ROP vs Excepciones en Arquitectura ### 9.5.1. El Problema con las Excepciones Las excepciónes fueron diseñadas para manejar situaciones excepciónales, errores inesperados que interrumpen el flujo normal de ejecución. Sin embargo, en arquitecturas bien diseñadas, el manejo de errores de negocio no deberia depender de excepciónes por varias razones fundamentales que afectan la calidad y mantenibilidad del codigo. El primer problema es que las **excepciónes rompen el flujo de ejecución** de manera no local. Cuando se lanza una excepción, el call stack se desenrolla hasta encontrar un bloque catch, lo cual es costoso en terminos de rendimiento…

## 79. ¿Qué es un ORM?

- **Fragmento oro:** `joseluisgs-04/netcore/10-entity-framework-core.md` orden **5** (explicacion, 496 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque EF Core)
- **Localización:** `lectura`

> …D1[Objetos C#] style A1 fill:#0D47A1 style A4 fill:#1B5E20 style C1 fill:#1565C0 style C2 fill:#1565C0 style C3 fill:#1565C0 ``` ### 10.1.1. ¿Qué es un ORM? Un **ORM (Object-Relational Mapper)** es una herramienta que permite convertir datos entre sistemas de tipos incompatibles: las bases de datos relacionales (que trabajan con tablas, filas, columnas y SQL) y los objetos orientados (que trabajan con clases, instancias, propiedades y métodos). En lugar de escribir SQL manualmente para cada operación, trabajas con objetos C# y el ORM genera el SQL correspondiente.…

## 80. ¿Qué es el DbContext en Entity Framework Core?

- **Fragmento oro:** `joseluisgs-04/netcore/10-entity-framework-core.md` orden **6** (explicacion, 423 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque EF Core)
- **Localización:** `lectura`

> …EF Core lo traduce a SQL SELECT f.*, c.* FROM Funkos f LEFT JOIN Categorias c ON f.CategoriaId = c.Id WHERE f.Precio > 20 ORDER BY f.Nombre ``` ### 10.1.2. ¿Qué es el DbContext? El **DbContext** es la clase principal en EF Core que representa una sesión con la base de datos. Es el punto de entrada para todas las operaciones de acceso a datos, permitiendo consultar entidades, guardar cambios y gestionar relaciones entre entidades. El DbContext actúa como un **carrito de compras** en un supermercado.…

## 81. ¿Cuál es la diferencia entre Data Annotations y Fluent API para configurar el modelo?

- **Fragmento oro:** `joseluisgs-04/netcore/10-entity-framework-core.md` orden **12** (explicacion, 476 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque EF Core)
- **Localización:** `lectura`

> …)] public string? Descripcion { get; set; } // Relación inversa public ICollection<Funko> Funkos { get; set; } = new List<Funko>(); } ``` ### 10.3.2. Fluent API La Fluent API se configura en el método `OnModelCreating` del DbContext. Ofrece mayor flexibilidad y control sobre la configuración, especialmente para relaciones complejas. ```csharp protected override void OnModelCreating(ModelBuilder modelBuilder) { base.OnModelCreating(modelBuilder); // Configuración de Funko modelBuilder.Entity<Funko>(entity => { // Clave primaria entity.HasKey(e => e.Id);…

## 82. ¿Cómo se define una relación uno a muchos entre entidades?

- **Fragmento oro:** `joseluisgs-04/netcore/10-entity-framework-core.md` orden **22** (explicacion, 503 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque EF Core)
- **Localización:** `lectura`

> …} FUNKO_DETALLE { int FunkoId PK, FK string Descripcion string Material decimal Altura } ``` ### 10.5.3. Relación Uno a Muchos (One-to-Many) Una `Categoria` tiene muchos `Funkos`, pero cada `Funko` pertenece a una `Categoria`. ```csharp // Entidad principal (uno) public class Categoria { public int Id { get; set; } public string Nombre { get; set; } = string.Empty; // Colección de funkos (muchos) public ICollection<Funko> Funkos { get; set; } = new List<Funko>(); } // Entidad dependiente (muchos) public class Funko { public int Id { get; set; } public string Nombre { get; set; } = string.Empty; public decimal Precio { get; set; } // Foreign Key public int CategoriaId { get…

## 83. ¿Qué es una caché y qué problema resuelve?

- **Fragmento oro:** `joseluisgs-04/netcore/12-redis-caching.md` orden **5** (explicacion, 454 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque cache)
- **Localización:** `lectura`

> …- [12.16. Resumen](#1216-resumen) - [12.17. Ejercicio Propuesto](#1217-ejercicio-propuesto) --- # 12. Redis Caching ## 12.1. Introducción ### 12.1.1. ¿Qué es un Caché? Un **caché** es una capa de almacenamiento temporal de alta velocidad que guarda copias de datos frecuentemente accedidos, permitiendo recuperarlos más rápido en solicitudes futuras. El objetivo principal es reducir la latencia y la carga en sistemas más lentos (como bases de datos) almacenando temporalmente datos que son costosos de obtener pero que se acceden con frecuencia. 🧠 **Analogía**: Imagina un supermercado. En lugar de ir a buscar cada producto al almacén gigante del sótano cada vez que un cliente lo pide, el personal mantiene los productos más populares en los est…

## 84. ¿Qué diferencia hay entre una caché en memoria y una caché distribuida?

- **Fragmento oro:** `joseluisgs-04/netcore/12-redis-caching.md` orden **8** (explicacion, 500 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque cache)
- **Localización:** `lectura`

> …ínimo) | | **Compartición** | No compartido entre instancias | | **Persistencia** | Se pierde al reiniciar | | **Memoria** | Limitada al proceso | ### 12.2.2. Caché Distribuido Un caché distribuido es un servicio independiente que múltiples instancias de aplicación pueden compartir. Redis es el ejemplo más popular. ```csharp using Microsoft.Extensions.Caching.Distributed; using StackExchange.Redis; public class DistributedCacheExample { private readonly IDistributedCache _cache; private readonly IConnectionMultiplexer _redis; public DistributedCacheExample( IDistributedCache cache, IConnectionMultiplexer redis) { _cache = cache; _redis = redis; }…

## 85. ¿Qué es el algoritmo LRU de caché?

- **Fragmento oro:** `joseluisgs-04/netcore/12-redis-caching.md` orden **11** (explicacion, 506 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque cache)
- **Localización:** `lectura`

> …iguración | Redis | Sincronizado entre instancias | | Contadores/rate limiting | Redis | Operaciones atómicas | --- ## 12.3. Algoritmos de Caché ### 12.3.1. LRU - Least Recently Used **LRU** (Least Recently Used) elimina primero los elementos que no han sido usados durante más tiempo. Es el algoritmo más común y funciona bien cuando los patrones de acceso tienen localidad temporal. ```mermaid flowchart TD subgraph "Estado Inicial" A["Cache A B C<br/>Orden uso A B C"] --> B[Solicitud D] end subgraph "Cache MISS Evict LRU" B --> C["Cache B C D<br/>Orden uso B C D"] C --> D["A fue eliminado<br/>Hace mas tiempo"] end…

## 86. ¿Qué es Redis y qué estructuras de datos ofrece?

- **Fragmento oro:** `joseluisgs-04/netcore/12-redis-caching.md` orden **14** (explicacion, 461 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque cache)
- **Localización:** `lectura`

> …streaming | | **TTL** | Datos que caducan naturalmente | Datos permanentes | O(1) | Tokens, sesiones, caches | --- ## 12.4. Redis: Fundamentos ### 12.4.1. ¿Qué es Redis? **Redis** (Remote Dictionary Server) es una base de datos en memoria de código abierto que funciona como almacén de estructuras de datos clave-valor. Es extremadamente rápido porque mantiene todos los datos en memoria RAM. 📝 **Nota del Profesor**: Redis fue creado por Salvatore Sanfilippo en 2009 para resolver problemas de escalabilidad en su startup. Fue diseñado con un enfoque en la simplicidad y el rendimiento. En 2015, Redis Labs (ahora Redis Inc.) adquirió los derechos del proyecto. ### 12.4.2. Estructuras de Datos en Redis A diferencia de un simple key-value store, Redi…

## 87. ¿Qué son las propiedades ACID de una transacción?

- **Fragmento oro:** `joseluisgs-04/netcore/13-transacciones.md` orden **5** (explicacion, 488 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque transacciones)
- **Localización:** `lectura`

> …edes sacar dinero de una cuenta sin asegurarte de que se deposite en la otra. Si algo falla a mitad del proceso, todo debe revertirse. ### 13.2.2. Propiedades ACID ```mermaid flowchart LR subgraph "Propiedades ACID" A["Atomicity<br/>Atomicidad"] --> C["Consistency<br/>Consistencia"] C --> I["Isolation<br/>Aislamiento"] I --> D["Durability<br/>Durabilidad"] end style A fill:#1B5E20 style C fill:#1B5E20 style I fill:#1B5E20 style D fill:#1B5E20 ``` | Propiedad | Descripcion | Ejemplo | |-----------|-------------|---------| | **Atomicidad** | Todo o nada | Si el pedido falla, el stock no se decrementa | | **Consistencia** | Datos siempre validos | Stock nunca negativo, pedidos siempre validos | | **Aislami…

## 88. ¿En qué consiste el control de concurrencia optimista con RowVersion?

- **Fragmento oro:** `joseluisgs-04/netcore/13-transacciones.md` orden **9** (explicacion, 480 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque transacciones)
- **Localización:** `lectura`

> …ersiones | | **Rendimiento** | Mejor cuando conflictos son raros | | **Casos de uso** | Lecturas frecuentes, escrituras pocas | ### 13.4.2. Implementacion con RowVersion ```csharp // Entity con RowVersion para optimistic concurrency public class Producto { public long Id { get; set; } public string Nombre { get; set; } = string.Empty; public decimal Precio { get; set; } public int Stock { get; set; } // Timestamp de version para concurrency [Timestamp] public byte[] RowVersion { get; set; } = null!; } // En Fluent API modelBuilder.Entity<Producto>(entity => { entity.Property(p => p.RowVersion) .IsRowVersion(); }); ``` ### 13.4.3. Manejo de DbUpdateConcurrencyException ```csharp public class PedidoService {…

## 89. ¿Qué es el control de concurrencia pesimista y cuándo se usa?

- **Fragmento oro:** `joseluisgs-04/netcore/13-transacciones.md` orden **12** (explicacion, 466 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque transacciones)
- **Localización:** `lectura`

> …{ return await CreatePedidoInternoAsync(request); }); } } ``` ## 13.5. Enfoque Pesimista ### 13.5.1. Concepto y Caracteristicas El **control de concurrencia pesimista** asume que los conflictos son frecuentes y utiliza bloqueos para prevenir que otros procesos accedan a los datos modificados. ```mermaid flowchart TD A["Transaccion comienza"] --> B["Adquirir bloqueo"] B --> C["Leer datos"] C --> D["Procesar logica"] D --> E["Escribir cambios"] E --> F["Liberar bloqueo"] F --> G["Transaccion exitosa"] H["Otras transacciónes"] --> I{"Bloqueado"} I -->|Si| J["Esperar"] I -->|No| K["Leer datos"] ```…

## 90. ¿Qué son los niveles de aislamiento de una transacción?

- **Fragmento oro:** `joseluisgs-04/netcore/13-transacciones.md` orden **13** (codigo, 475 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque transacciones)
- **Localización:** `lectura`

> …| | **Rendimiento** | Peor con alta contencion | | **Consistencia** | Garantizada siempre | | **Casos de uso** | Inventario critico, financieras | ### 13.5.2. Niveles de Aislamiento | Nivel | Dirty Read | Non-repeatable | Phantom | Bloqueo | |-------|------------|----------------|---------|---------| | **Read Uncommitted** | Permitido | Permitido | Permitido | Ninguno | | **Read Committed** | Protegido | Permitido | Permitido | Filas | | **Repeatable Read** | Protegido | Protegido | Permitido | Filas | | **Serializable** | Protegido | Protegido | Protegido | Tabla | ### 13.5.3. SELECT FOR UPDATE ```csharp public async Task<Result<Pedido, Error>> CreatePedidoConPesimistaAsync( CreatePedidoRequest request) { await using var transaction = aw…

## 91. ¿Para qué sirve un mapeador entre entidades y DTOs?

- **Fragmento oro:** `joseluisgs-04/netcore/08-mapeadores.md` orden **2** (explicacion, 489 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque mapeadores)
- **Localización:** `lectura`

> …- [8.8. Errores Comunes](#88-errores-comunes) - [8.9. Resumen](#89-resumen) --- ## 8.1. ¿Por Qué Usar Mapeadores? En arquitecturas limpias como Clean Architecture, las **entidades** (modelos de dominio) y los **DTOs** (Data Transfer Objects) suelen tener estructuras diferentes. Las entidades contienen toda la información del dominio, incluyendo relaciones, marcas temporales y estados internos. Los DTOs, en cambio, están optimizados para la API y exponen solo los datos necesarios, con formatos específicos para la presentación. 🧠 **Analogía**: Los mapeadores son como traductores en una reunión internacional. La entidad habla "idioma de dominio" (con toda su complejidad interna) y…

## 92. ¿Qué es AutoMapper y cómo se configura un Profile?

- **Fragmento oro:** `joseluisgs-04/netcore/08-mapeadores.md` orden **5** (codigo, 408 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque mapeadores)
- **Localización:** `lectura`

> …### 8.2.2. MappingProfile El Profile es la clase donde defines los mapeos entre tipos. Puedes tener un Profile global o varios Profiles específicos por dominio. ```csharp using AutoMapper; using FunkosApi.Core.Dtos.Categorias; using FunkosApi.Core.Dtos.Funkos; using FunkosApi.Core.Dtos.Usuarios; using FunkosApi.Core.Models; namespace FunkosApi.Core.Mappers; public class MappingProfile : Profile { public MappingProfile() { // Mapeos de categoria CreateMap<Categoria, CategoriaDto>(); CreateMap<CategoriaRequestDto, Categoria>(); // Mapeos de funko CreateMap<Funko,…

## 93. ¿Qué significa que la autenticación sea stateless y por qué se usa en APIs?

- **Fragmento oro:** `joseluisgs-04/netcore/14-autenticacion.md` orden **2** (explicacion, 441 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque autenticacion)
- **Localización:** `lectura`

> …icas-de-seguridad) - [14.17. Resumen](#1417-resumen) - [14.18. Recursos Adicionales](#1418-recursos-adicionales) --- ## 14.1. Concepto de Autenticación Stateless ### ¿Qué significa Stateless (Sin Estado)? En una arquitectura **stateful** (con estado), el servidor mantiene información de sesión del usuario. Esto requiere: - Almacenamiento de sesión en servidor (memoria, base de datos) - Affinity/session stickiness en load balancers - El servidor "recuerda" al usuario entre requests En una arquitectura **stateless** (sin estado): - Cada request contiene toda la información necesaria - No hay sesión en el servidor - El servidor no almacena información del usuario - Escalabilidad horizontal simple (cualquier servidor puede atender cualquier re…

## 94. ¿Qué información lleva el payload de un JWT?

- **Fragmento oro:** `joseluisgs-04/netcore/14-autenticacion.md` orden **5** (explicacion, 503 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque autenticacion)
- **Localización:** `lectura`

> …de firma (HS256, RS256, ES256) | | `typ` | Tipo de token (siempre "JWT") | ### Payload (Claims) ```json { "sub": "1234567890", "name": "John Doe", "email": "john@example.com", "roles": ["Admin", "User"], "iat": 1516239022, "exp": 1516242622, "iss": "TiendaApi", "aud": "TiendaApiClients", "jti": "unique-token-id" } ``` | Claim | Significado | |-------|-------------| | `sub` | Subject (identificador principal) | | `iss` | Issuer (quién emite) | | `aud` | Audience (para quién) | | `exp` | Expiration Time | | `nbf` | Not Before | | `iat` | Issued At | | `jti` | JWT ID (identificador único) | ### Signature ```csharp var key = new SymmetricSecurityKey(Enc…

## 95. ¿Qué es BCrypt y por qué es lento a propósito?

- **Fragmento oro:** `joseluisgs-04/netcore/14-autenticacion.md` orden **9** (explicacion, 500 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque autenticacion)
- **Localización:** `lectura`

> …BCrypt? **BCrypt** es un algoritmo de hashing de contraseñas diseñado para ser lento y costoso computacionalmente. Esto lo hace resistente a ataques de fuerza bruta. ```mermaid flowchart LR subgraph "Registro (Signup)" R1["Password: Test1234"] --> R2["BCrypt.HashPassword()"] R2 --> R3["$2y$12$xyz...abc"] R3 --> R4["Guardar en BD"] end subgraph "Login (Signin)" L1["Password: Test1234"] --> L2["Leer hash de BD"] L2 --> L3["BCrypt.Verify(Test1234, hash)"] L3 --> L4{"Coincide?"} L4 -->|Si| L5["Login OK"] L4 -->|No| L6["Login…

## 96. ¿Qué diferencia hay entre un test unitario y uno de integración?

- **Fragmento oro:** `joseluisgs-04/netcore/21-testing.md` orden **5** (procedimiento, 484 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque testing)
- **Localización:** `lectura`

> …os | | **Integration** | Multiples componentes juntos | Medio (~s) | Medio | Medio | | **E2E** | Flujo completo de usuario | Lento (~min) | Bajo | Pocos | ### Test Unitario Un test unitario verifica que una **unica unidad** de codigo funciona correctamente. Esta unidad suele ser un metodo. Un buen test unitario: 1. **Es rapido**: Se ejecuta en milisegundos 2. **Es aislado**: No depende de bases de datos, redes o archivos 3. **Es determinista**: Siempre da el mismo resultado 4. **Es independiente**: No depende de otros tests ### Test de Integracion Los tests de integracion prueban multiples componentes trabajando juntos sin mocks o con mocks limitados. ### Test E2E Los tests End-to-End simulan un usuario real, probando la aplicación completa de…

## 97. ¿Qué es el patrón AAA en un test?

- **Fragmento oro:** `joseluisgs-04/netcore/21-testing.md` orden **14** (explicacion, 474 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque testing)
- **Localización:** `lectura`

> …or"); } } ``` --- ## 21.8. Moq - Creando Mocks **Moq** es una libreria que permite crear objetos falsos (mocks) para aislar el codigo bajo test. ### El Patron AAA con Moq Todo test con Moq debe seguir el patron **Arrange-Act-Assert**: ```mermaid flowchart TD subgraph "ARRANGE - Preparar" A1["Crear mocks"] A2["Configurar comportamiento"] A3["Inicializar sistema bajo test"] end subgraph "ACT - Ejecutar" B1["Llamar al metodo"] end subgraph "ASSERT - Verificar" C1["Verificar resultado"] C2["Verify interacciones con mocks"] C3["Verify excepciones"] end A1 --> A2 --> A3 A3 --> B1 B1 --> C1 --> C2 --> C3 ``` ### 21.8.1. Configurar Comportamiento con Setup ```cshar…

## 98. ¿Para qué sirve Verify en Moq?

- **Fragmento oro:** `joseluisgs-04/netcore/21-testing.md` orden **17** (explicacion, 471 tok)
- **Origen de la pregunta:** 04-test-aspcore.md (bloque testing)
- **Localización:** `lectura`

> …} ``` ### 21.8.3. Verify - Verificar Interacciones El **Verify** es crucial para asegurar que el codigo llama las dependencias correctamente. ```csharp [Test] public void VerifyExamples() { // Arrange var productoId = 1L; var producto = new Producto { Id = productoId, Nombre = "Test" }; _repositoryMock .Setup(r => r.GetByIdAsync(productoId)) .ReturnsAsync(producto); // Act var resultado = await _service.GetByIdAsync(productoId); // ===================================== // ASSERT - Verificar con Moq Verify // ===================================== // Verify basic: veri…

## 99. ¿Qué diferencia hay entre los tipos por valor y los tipos por referencia en C#?

- **Fragmento oro:** `joseluisgs-04/csharp/04-Fundamentoscsharp.md` orden **7** (explicacion, 506 tok)
- **Origen de la pregunta:** 01-test-csharp.md (bloque fundamentos)
- **Localización:** `lectura`

> …{ DemoWriteLine(); DemoReadLine(); DemoColores(); DemoTabla(); } } } ``` ## 4.2. Analogía: Value Types vs Reference Types Los tipos por valor almacenan el dato directamente, mientras que los tipos por referencia almacenan una dirección de memoria. - **Tipos por valor** son como fotocopiar un documento. La copia es independiente del original. - **Tipos por referencia** son como darle a alguien la dirección de archivo. Si alguien modifica el archivo, todos ven los cambios. - **Tipos por valor** son como photocopiar el documento. Si cambias la copia, el original no se ve afectado. - **Tipos por referencia** son como darle a alguien la ubicación del archivo original en el archivador.…

## 100. ¿Para qué sirve la declaración using al trabajar con recursos?

- **Fragmento oro:** `joseluisgs-04/csharp/04-Fundamentoscsharp.md` orden **20** (explicacion, 467 tok)
- **Origen de la pregunta:** 01-test-csharp.md (bloque excepciones)
- **Localización:** `lectura`

> …M -->|No| N[Terminar programa] M -->|Sí| A style D fill:#F44336 style F fill:#4CAF50 style N fill:#FF9800 ``` ### 4.7.6. try-catch con Recursos: using La declaración `using` garantiza que los recursos se liberen correctamente, incluso si ocurre una excepción. ```csharp namespace Fundamentos.Excepciones { public class UsingExamples { // Formato antiguo (C# 8-) public void FormatoAntiguo() { using (var stream = new StreamReader("archivo.txt")) { string contenido = stream.ReadToEnd(); Console.WriteLine(contenido); } // stream.Dispose() se llama automáticamente }…

