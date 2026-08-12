# Muestreo de fragmentos (encargo 1.4)

Veinte fragmentos a intervalo regular (574) sobre los 11483 del índice, empezando en el 575. **Los lee una persona**, con su línea de
contexto delante, y anota si el fragmento se entiende solo y si su `tipo_contenido` es el que le pega.

La `unidad` es el primer directorio con significado bajo la asignatura, y va vacía cuando no hay ninguno (ADR 0005: sale de la carpeta del material, no del BOE).

## 1. `explicacion` · 488 tokens

- **Contexto:** ASIR · administracion-de-sistemas-operativos · Actualización de Quijote a CentOS 8
- **Origen:** `corpus/asir/apuntes/lora-2asir/ASO/CentOS7a8.md` (trozo 45)
- **Asignatura:** administracion-de-sistemas-operativos — *sigla del material, tabla declarada*
- **Unidad:** (ninguna carpeta con significado)

> kB/s | 101 kB 00:00 (66/67): sssd-common-2.2.3-20.el8.x86_64.rpm 5.1 MB/s | 1.5 MB 00:00 (67/67):  yum-4.2.17-7.el8_2.noarch.rpm                                   1.4 MB/s | 191 kB     00:00     --------------------------------------------------------------------------------------------------------- Total                                                                    5.3 MB/s |  26 MB     00:04      Running transaction check Transaction check succeeded.  Running transaction test Transaction test succeeded.  Running transaction   Preparing        :  1/1    Installing       :  libtalloc-2.2.…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 2. `codigo` · 505 tokens

- **Contexto:** ASIR · seguridad-y-alta-disponibilidad · Cortafuegos
- **Origen:** `corpus/asir/apuntes/lora-2asir/SAD/Cortafuegosopenstack.md` (trozo 14)
- **Asignatura:** seguridad-y-alta-disponibilidad — *sigla del material, tabla declarada*
- **Unidad:** (ninguna carpeta con significado)

> ;; WHEN: Thu Jan 28 12:05:19 UTC 2021 ;; MSG SIZE rcvd: 151 [centos@quijote ~]$ dig www.josedomingo.org  ; <<>> DiG 9.11.20-RedHat-9.11.20-5.el8 <<>> www.josedomingo.org ;; global options: +cmd ;; Got answer: ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 23347 ;; flags: qr rd ra; QUERY: 1, ANSWER: 2, AUTHORITY: 5, ADDITIONAL: 2  ;; OPT PSEUDOSECTION: ; EDNS: version: 0, flags:; udp: 4096 ; COOKIE: 99615458501c5fe16f818d826012a939bde78b64f2d9fe9f (good) ;; QUESTION SECTION: ;www.josedomingo.org.		IN	A  ;; ANSWER SECTION: www.josedomingo.org.	900	IN	CNAME	endor.josedomingo.org. endor.josed…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 3. `explicacion` · 376 tokens

- **Contexto:** DAW · curso 1 · programacion · Unidad 6 Arrays · Repaso de la unidad (versión resumida para el examen)
- **Origen:** `corpus/daw/curso1/programacion/lionel-ict/Unidad 6 Arrays/ud6_Arrays_repaso.md` (trozo 5)
- **Asignatura:** programacion — *carpeta del ciclo*
- **Unidad:** Unidad 6 Arrays

> pero su primer elemento se encuentra en notas[0] y el último en notas[3]. Índices → 0 1 2 3 4 Valores → 8 10 2 3 5  3.5 Recorrido de un vector Para recorrer un vector (acceder a todos sus elementos) siempre será necesario un bucle. En el siguiente ejemplo declaramos e instanciamos un vector tipo int con las notas de un alumno y luego utilizamos un bucle for para recorrer el vector y mostrar todos los elementos. // Declaramos e instanciamos vector tipo int int notas[] = new int[] {7, 3, 9, 6, 5}; // Como el vector es de tamaño 5 sus elementos estarán en las posiciones de 0 a 4 // Recorremos el …

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 4. `codigo` · 615 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · TenistasReactiveServiceImpl
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-02/ejemplos/06-TenistasReactive/src/main/java/dev/joseluisgs/service/TenistasReactiveServiceImpl.java` (trozo 6)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> @Override     public Single<Boolean> deleteById(long id) {         return Single.fromCallable(() -> {             logger.info("Borrando tenista con id: {} en el servicio", id);             tenistaCache.invalidate(id);              boolean deleted = repository.deleteById(id);             if (!deleted) {                 logger.error("Tenista con id {} no encontrado para borrar", id);                 throw new TenistaException.NotFoundException("Tenista con ID " + id + " no encontrado para borrar.");             }             // 🚀 Enviamos la notificación de tipo BORRADO             notificacione…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 5. `explicacion` · 504 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · 8. Almacenamiento de Ficheros
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-02/springboot/08-AlmacenamientoFicheros.md` (trozo 9)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> - CommandLineRunner: Se ejecuta después del contexto de Spring > - @PostConstruct: Se ejecuta después de la inyección de dependencias, pero antes del contexto completo  Una forma alternativa de lograr el mismo resultado sin usar CommandLineRunner es utilizar la anotación `@PostConstruct` en un método dentro de un bean. La anotación @PostConstruct es una anotación estándar de Java que indica que un método debe ejecutarse después de que el bean haya sido construido y se hayan inyectado todas las dependencias.  En este ejemplo, el método init() está anotado con @PostConstruct, lo que indica que s…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 6. `explicacion` · 508 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · 10. Concurrencia y Asincronía en .NET
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-04/csharp/10-ConcurrenciaAsincronia.md` (trozo 9)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> el hilo Thread.Sleep(1000); var duracion2 = DateTime.Now - inicio; Console.WriteLine($"Thread.Sleep: {duracion2.TotalMilliseconds}ms"); }  // Parallel.ForEach para procesamiento paralelo         public void DemoParallelForEach()         {             var items = Enumerable.Range(1, 100).ToList();  Parallel.ForEach(items, item =>             {                 Console.WriteLine($"Procesando {item} en hilo {Thread.CurrentThread.ManagedThreadId}");             });  // Con opciones             Parallel.ForEach(items, new ParallelOptions              {                  MaxDegreeOfParallelism = Envir…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 7. `explicacion` · 442 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · 3. Arquitectura Global y Pipeline HTTP en ASP.NET Core
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-04/netcore/03-arquitectura-pipeline.md` (trozo 11)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> result.Should().NotBeNull(); result.Result.Should().BeOfType<NotFoundResult>(); } } ``` **Características que facilitan el testing:**  - **Interfaces para todo**: Servicios, repositorios, etc. - **HttpContext abstractions**: Mocking de contexto HTTP - **TestServer**: Servidor en memoria para integración - **InMemoryDatabase**: Base de datos efímera para tests  ## 3.3. Módulos Principales de ASP.NET Core  ```mermaid flowchart TD     subgraph "ASP.NET Core"         A[MVC] --> B[Aplicaciones Web<br/>con vistas]         C[Minimal APIs] --> D[APIs ligeras]         E[Razor Pages] --> F[Páginas web<b…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 8. `explicacion` · 487 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · 20. File Storage: Almacenamiento de Archivos
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-04/netcore/20-file-storage.md` (trozo 5)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> = 10 * 1024 * 1024; // 10 MB }); ``` ### Clase de Configuracion ```csharp namespace TiendaApi.Apis.Configuration;  public class StorageSettings {     /// <summary>     /// Ruta base donde se guardan los archivos     /// </summary>     public string RootPath { get; set; } = "wwwroot/uploads";  /// <summary>     /// Tamanio maximo en bytes (5 MB por defecto)     /// </summary>     public long MaxFileSize { get; set; } = 5 * 1024 * 1024;  /// <summary>     /// Extensiones permitidas     /// </summary>     public string[] AllowedExtensions { get; set; } =          { ".jpg", ".jpeg", ".png", ".gif"…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 9. `explicacion` · 501 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · 7. Blazor y Blazor Server: Interactividad sin JavaScript
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-05/07-blazor.md` (trozo 81)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> httpClientLocal; private CancellationTokenSource? cts; private IDisposable? suscripcion; private string ultimoDato = ""; private int contadorActualizaciones = 0;  protected override void OnInitialized()     {         // ────────────────────────────────────────────────────         // RECURSO 1: Timer         // ────────────────────────────────────────────────────         timer = new Timer(async _ =>         {             await ActualizarDatos();             contadorActualizaciones++;             await InvokeAsync(StateHasChanged);         }, null, TimeSpan.Zero, TimeSpan.FromSeconds(5));  // ──…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 10. `explicacion` · 431 tokens

- **Contexto:** ASIR · implantacion-de-sistemas-operativos · UD07_SoftwareYActualizaciones · RegistroWindows
- **Origen:** `corpus/derivado/asir/apuntes/aberlanas-iso/UD07_SoftwareYActualizaciones/Manuales/RegistroWindows.pdf.md` (trozo 12)
- **Asignatura:** implantacion-de-sistemas-operativos — *repositorio de una sola asignatura, tabla declarada*
- **Unidad:** UD07_SoftwareYActualizaciones

> Unknown REG_SZ" PS> New-ItemProperty -path hkcu:/Console/MiClave -propertyType Unknown -Name Tipo-UnknownBinary -value  $ArrayDeBytes PS> New-ItemProperty -path hkcu:/Console/MiClave -Name Tipo-OtroString -value "Este es el valor Otro REG_SZ" PS> New-ItemProperty -path hkcu:/Console/MiClave -Name Tipo-OtroBinary -value $ArrayDeBytes Por cierto, que tanto con New-Item como con New-ItemProperty se puede usar -Type (en lugar de -itemType o -propertyType) para especificar el tipo de dato, pues PowerShell es capaz de autocompletar comandos y opciones siempre que lo que se le ponga no pueda ser tamb…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 11. `explicacion` · 510 tokens

- **Contexto:** DAM · acceso-a-datos · CLASIFICACIÓN DE FICHEROS
- **Origen:** `corpus/derivado/dam/apuntes/temario-dam-comesana/AD/apuntes/TEMA 1 - Clasificación de ficheros.docx.md` (trozo 5)
- **Asignatura:** acceso-a-datos — *sigla del material, tabla declarada*
- **Unidad:** (ninguna carpeta con significado)

> Métodos: setIgnoringComments(boolean ignore): Ignora los comentarios de un fichero XML. setIgnoringElementWhitespace(boolean ignore): Ignora los espacios en blanco.  setNamespaceAware(boolean aware): Interpretar el documento usando el espacio de nombres.  setValidating(boolean validate): Validar el documento XML según el esquema.  ##### org.w3c.dom.Document  Métodos:  getFirstChild() / getNextSibling(): Permiten obtener los nodos uno a uno: los nodos descendientes (hijos) y sus adyacentes (hermanos).  getNodeType(): Devuelve una constante para distinguir entre los distintos tipos de nodos (ele…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 12. `explicacion` · 437 tokens

- **Contexto:** DAM · sistemas-de-gestion-empresarial · Unidad 1 SGE · BOCYL-curriculo-TS.apli-multiplataforma (1)
- **Origen:** `corpus/derivado/dam/apuntes/temario-dam-comesana/SGE/Unidad 1 SGE/BOCYL-curriculo-TS.apli-multiplataforma (1).pdf.md` (trozo 25)
- **Asignatura:** sistemas-de-gestion-empresarial — *sigla del material, tabla declarada*
- **Unidad:** Unidad 1 SGE

> − Acceso a métodos de la superclase. − Diseño y creación de jerarquías de clases. − Aplicación del polimorfismo a listas de referencias de objetos.  8. Mantenimiento de la persistencia de los objetos: − Bases de datos orientadas a objetos. − Características de las bases de datos orientadas a objetos. − Instalación del gestor de bases de datos. − Creación de bases de datos. − Tipos de datos básicos y estructurados. − El lenguaje de definición de objetos. − Mecanismos de consulta. − El lenguaje de consultas: sintaxis, expresiones, operadores. − Recuperación, modificación y borrado de información…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 13. `explicacion` · 500 tokens

- **Contexto:** DAW · curso 1 · bases-de-datos · BD05
- **Origen:** `corpus/derivado/daw/curso1/bases-de-datos/comesana/BD05.pdf.md` (trozo 12)
- **Asignatura:** bases-de-datos — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> no se indica, debes tener muy claro que se borrará todo el contenido de la tabla, aunque la tabla seguirá existiendo con la estructura que tenía hasta el momento.  Por ejemplo, si usas la siguiente sentencia, borrarás todos los registros de la tabla USUARIOS:  DELETE FROM USUARIOS;  Para ver un ejemplo de uso de la sentencia DELETE en la que se indique una condición, supongamos que queremos eliminar todos los usuarios cuyo crédito es cero:  DELETE FROM USUARIOS WHERE Credito = 0;  Como resultado de la ejecución de este tipo de sentencia, se obtendrá un mensaje de error si se ha producido algún…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 14. `explicacion` · 504 tokens

- **Contexto:** DAW · curso 1 · fol · FO03
- **Origen:** `corpus/derivado/daw/curso1/fol/comesana/FO03.pdf.md` (trozo 33)
- **Asignatura:** fol — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> según su duración Jornada completa Es aquella cuya duración máxima viene establecida en el Convenio colectivo aplicable, que en todo caso respetará el límite máximo establecido en el art.  34 ET, donde se establece que la jornada ordinaria máxima será de 40 horas semanales de promedio en cómputo anual, en consecuencia los Convenios podrán pactar jornadas de igual duración o inferiores, pero nunca superiores.  En el Convenio Colectivo Estatal de Ingeniería y Oficinas de Estudios Técnicos se establece que a partir del 1 de enero de 2.011, la jornada ordinaria máxima de trabajo efectivo, en cómpu…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 15. `explicacion` · 498 tokens

- **Contexto:** DAW · curso 1 · lenguajes-de-marcas · LMSGI_06
- **Origen:** `corpus/derivado/daw/curso1/lenguajes-de-marcas/comesana/LMSGI_06.pdf.md` (trozo 10)
- **Asignatura:** lenguajes-de-marcas — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> - Recuperar información a partir de conjuntos de datos XML. - Transformar unas estructuras de datos XML en otras estructuras que organizan la información de forma diferente.  - Ofrecer  una  alternativa  a  XSLT  para  realizar  transformaciones  de  datos  en  XML  a  otro  tipo  de representaciones, como HTML o PDF.  ¿Y cuáles son los motores XQuery de código abierto (También llamado "open source", es la denominación que se le da al software que se desarrolla y distribuye libremente, es decir aquellos programas que podemos utilizar, modificar y redistribuir de forma gratuita) más relevantes …

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 16. `explicacion` · 501 tokens

- **Contexto:** DAW · curso 1 · sistemas-informaticos · SI03
- **Origen:** `corpus/derivado/daw/curso1/sistemas-informaticos/comesana/SI03.pdf.md` (trozo 41)
- **Asignatura:** sistemas-informaticos — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> características más importantes. Una tarjeta de red o adaptador de red permite la comunicación con aparatos conectados entre sí y también permite compartir recursos entre dos o más ordenadores.  A las tarjetas de red también se les llama NIC del inglés network interface card o en español tarjeta de interfaz de red.  Su función principal es la de permitir la conexión del ordenado r a la red, en la tarjeta se graban los protocolos necesarios para que esto suceda.  Todas las tarjetas de red tienen grabada la dirección MAC correspondiente.  Como ya hemos visto, la dirección MAC esta compuesta de 4…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 17. `explicacion` · 348 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-cliente · DWEC06
- **Origen:** `corpus/derivado/daw/curso2/desarrollo-web-entorno-cliente/comesana/DWEC06.pdf.md` (trozo 48)
- **Asignatura:** desarrollo-web-entorno-cliente — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> to element x. The true/false flag at the end states whether the event handler should be executed in the capturing or in the bubbling phase.  Modelo de objetos del documento en javascript. José Luis Comesaña Tema 6 Propiedad Eventos Explorer Explorer Explorer 5.2 MAC Mozilla 1.75 Safari 1.2 Opera 8 Netscape attachEvent() Añade un manejador de eventos a un elemento click x.attachEvent('onclick',doSomething); Add an onclick event handler that executes function doSomething() to element x. detachEvent() Quita un manejador de eventos de un elemento click x.detachEvent('onclick',doSomething); Remove …

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 18. `explicacion` · 482 tokens

- **Contexto:** DAW · curso 2 · despliegue-de-aplicaciones-web · DAW01
- **Origen:** `corpus/derivado/daw/curso2/despliegue-de-aplicaciones-web/comesana/DAW01.pdf.md` (trozo 11)
- **Asignatura:** despliegue-de-aplicaciones-web — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> largo del tiempo. La finalidad es tener en cuenta las características de cada uno de ellos y, en función de las mismas, distinguir sus ventajas e inconvenientes.  Se puede establecer que la arquitectura de un sitio web comprende los sistemas de organización y estructuración de los contenidos junto con los sistemas de recuperación de información y navegación  que provea el sitio web, con el objetivo de servir de ayuda a los usuarios a encontrar y manejar la información.  Centraremos el estudio de los modelos de arquitectura web relacionados, en función de cómo im- plementan cada una de las capa…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 19. `explicacion` · 502 tokens

- **Contexto:** DAW · curso 2 · diseno-de-interfaces-web · DIW03
- **Origen:** `corpus/derivado/daw/curso2/diseno-de-interfaces-web/comesana/DIW03.pdf.md` (trozo 17)
- **Asignatura:** diseno-de-interfaces-web — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> que tener especial cuidado a la hora de diseñarlo. En el apartado anterior decíamos que una interfaz es usable si los usuarios pueden contestar a las preguntas:  ¿Dónde estoy?  ¿Cómo llegué aquí?  ¿A dónde puedo ir después?  ¿Qué puedo hacer en este momento?  y ¿Cómo puedo regresar al punto anterior?  La mayoría de estas preguntas serán de fácil respuesta para el usuario si se tienen presentes las ca- racterísticas deseables de un sistema de navegación cuando diseñamos un sitio web.  2.1.- Información accesible.  ¿Cómo organizas la información que almacenas en tu ordenador?  ¿Creas accesos dir…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 20. `explicacion` · 483 tokens

- **Contexto:** DAW · curso 2 · empresa-e-iniciativa-emprendedora · Programacion_EIE
- **Origen:** `corpus/derivado/daw/curso2/empresa-e-iniciativa-emprendedora/comesana/Programacion_EIE.pdf.md` (trozo 16)
- **Asignatura:** empresa-e-iniciativa-emprendedora — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> establecen dos pruebas presenciales, una de carácter voluntario en el mes de febrero (par a eliminar materia) y otra obligatoria en el mes de junio. Tareas:  Para aprobar esta parte, la media aritmética de las tareas ha de ser 5 o superior.  En relación a las tareas destacaremos que:  Existen unas fechas límite de entrega de las tareas de cada unidad didáctica, a partir de las fechas que se exponen a c ontinuación no se corregirán tareas de las unidades señaladas:  Unidades 1, 2, 3 y 4:  las tareas de estas unidades han de estar entregadas antes del día 4 de marzo.  Unidades 5, 6, 7 y 8:  las …

¿Se entiende solo? ___  ¿El tipo es correcto? ___

