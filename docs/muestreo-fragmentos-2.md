# Muestreo de fragmentos (encargo 1.4)

Veinte fragmentos a intervalo regular (578) sobre los 11574 del índice, empezando en el 289. **Los lee una persona**, con su línea de
contexto delante, y anota si el fragmento se entiende solo y si su `tipo_contenido` es el que le pega.

La `unidad` es el primer directorio con significado bajo la asignatura, y va vacía cuando no hay ninguno (ADR 0005: sale de la carpeta del material, no del BOE).

## 1. `explicacion` · 266 tokens

- **Contexto:** ASIR · implantacion-de-sistemas-operativos · UD06_SistemasDeFicheros · Tarea: 11 de Febrero - Parte I
- **Origen:** `corpus/asir/apuntes/aberlanas-iso/UD06_SistemasDeFicheros/Tarea_40_11DeFebrero_Ada.md` (trozo 4)
- **Asignatura:** implantacion-de-sistemas-operativos — *repositorio de una sola asignatura, tabla declarada*
- **Unidad:** UD06_SistemasDeFicheros

> estar y además son como deben ser. La misión consiste en crear un script que se llamará “workspace_emmy.sh” que lo que hará será lo siguiente:  * Comprobar que `/maquina/fisica` es una carpeta * Comprobar que existen los ficheros y SI NO existen, crearlos (los ficheros de Emmy) * En el caso del enlace, comprobar que no esta roto, pero no crearlo  si no existe el destino del mismo. * El fichero `fichero_emmynoether.datos` ha de ser leído y escrito solo por ella y el grupo solo ha de poder leer. * El fichero `fichero_emmynoether.secreto` solo ha de ser leído por ella. * El fichero `fichero_emmyn…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 2. `codigo` · 508 tokens

- **Contexto:** ASIR · Servidores Web, Base de Datos y DNS.
- **Origen:** `corpus/asir/apuntes/lora-2asir/BBDDNServopenstack.md` (trozo 22)
- **Asignatura:** (no declarada) — *no declarada: ficheros sueltos en la raiz del repositorio*
- **Unidad:** (ninguna carpeta con significado)

> con la pila LAMP, a crear la contraseña de root, borrar usuarios por defecto, etc....: ``` ubuntu@sancho:~$ sudo mysql_secure_installation  NOTE: RUNNING ALL PARTS OF THIS SCRIPT IS RECOMMENDED FOR ALL MariaDB       SERVERS IN PRODUCTION USE!  PLEASE READ EACH STEP CAREFULLY!  In order to log into MariaDB to secure it, we'll need the current password for the root user.  If you've just installed MariaDB, and you haven't set the root password yet, the password will be blank, so you should just press enter here.  Enter current password for root (enter for none):  OK, successfully used password, m…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 3. `explicacion` · 335 tokens

- **Contexto:** DAM · sistemas-de-gestion-empresarial · Unidad 5 SGE · -*- coding: utf-8 -*
- **Origen:** `corpus/dam/apuntes/temario-dam-comesana/SGE/Unidad 5 SGE/Actividades/expresiones_regulares.txt` (trozo 2)
- **Asignatura:** sistemas-de-gestion-empresarial — *sigla del material, tabla declarada*
- **Unidad:** Unidad 5 SGE

> print "Si" if (re.match(reExpresion, "1bc")) else "No" print "Si" if (re.match(reExpresion, "7bc")) else "No"  reExpresion = "[0-9a-zB]bc"     print "Corchetes m�s rango concatenado [0-9a-zB]bc" print "Si" if (re.match(reExpresion, "Abc")) else "No" print "Si" if (re.match(reExpresion, "Bbc")) else "No" print "Si" if (re.match(reExpresion, "xbc")) else "No" print "Si" if (re.match(reExpresion, "7bc")) else "No"  print "    uso de re    " reExpresion = "http://(.+)(.{2})" # no es necesario escapar dentro de () el.  print "Si" if (re.match(reExpresion, "HTTP://www.boe.es", re.IGNORECASE | re.VER…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 4. `codigo` · 552 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · JdbiManagerTest.java
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-02/ejemplos/01-TenistasSync/src/test/java/dev/joseluisgs/database/JdbiManagerTest.java` (trozo 4)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> class CasosNegativos {         @Test         @DisplayName("Ejecutar script inexistente no lanza excepción (se registra el error)")         void ejecutarScriptInexistenteNoLanzaExcepcion() throws Exception {             // Usamos reflexión para invocar el método privado con un recurso que no existe             JdbiManager manager = JdbiManager.getInstance();             Method method = JdbiManager.class.getDeclaredMethod("executeSqlScriptFromResources", String.class);             method.setAccessible(true);              assertDoesNotThrow(() -> {                 try {                     method…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 5. `explicacion` · 490 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · 12. Programación reactiva
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-02/java/12-ProgReactiva.md` (trozo 30)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> import kotlinx.coroutines.flow.* import kotlinx.coroutines.runBlocking import kotlinx.coroutines.launch import kotlinx.coroutines.channels.BufferOverflow  fun main() = runBlocking {     // Crear un SharedFlow con configuración de buffer y sobrecarga     val shared = MutableSharedFlow<String>(         replay = 1,         onBufferOverflow = BufferOverflow.DROP_OLDEST     )     shared.tryEmit("Valor inicial") // Emitir valor inicial     val stateFlow = shared.distinctUntilChanged() // Obtener comportamiento tipo StateFlow  // Suscribirse y observar valores del StateFlow     launch {         state…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 6. `explicacion` · 486 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · 2. Gestión de Proyectos y Construcción en .NET
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-04/csharp/02-GestionProyectos.md` (trozo 12)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> Api.IntegrationTests/ ├── Api.IntegrationTests.csproj └── ApiTests.cs ``` ### 2.1.6. Namespaces y Organización del Código  Los **namespaces** organizan el código en grupos lógicos, evitando conflictos de nombres y facilitando la navegación.  ```mermaid flowchart TD     A["Namespace"] --> B["Agrupación lógica"]     A --> C["Evitar conflictos de nombres"]     A --> D["Facilitar navegación"]     A --> E["Importar con using"]  B --> B1["Por capa"]     B --> B2["Por funcionalidad"]     B --> B3["Por tipo"]  style A fill:#4CAF50 ```  **Convenciones de nombres:**  ```csharp // Por capa (Clean Archite…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 7. `codigo` · 331 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · TenistasResult.Console · TenistaService.cs
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-04/ejemplos/04-TenistasResult/TenistasResult.Console/Services/TenistaService.cs` (trozo 3)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** TenistasResult.Console

> public Result<Tenista> UpdateRanking(long id, int nuevoRanking)     {         return FindById(id)             .Ensure(t => nuevoRanking > 0, "El ranking debe ser mayor que 0")             .Tap(t => t.Ranking = nuevoRanking);     }      /// <summary>     /// Obtiene el top N con validación     /// </summary>     public Result<List<Tenista>> GetTopN(int n)     {         if (n <= 0)             return Result.Failure<List<Tenista>>("N debe ser mayor que 0");                  if (n > _tenistas.Count)             return Result.Failure<List<Tenista>>($"Solo hay {_tenistas.Count} tenistas");          …

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 8. `codigo` · 489 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · 11. NoSQL con MongoDB
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-04/netcore/11-mongodb.md` (trozo 39)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> // Assert marvelFunkos.Should().HaveCount(1); marvelFunkos[0].Categoria.Should().Be("Marvel"); }  [Test]     public async Task FindById_ExistingFunko_ReturnsFunko()     {         // Arrange         var funko = new FunkoDocument         {             Nombre = "Spider-Man",             Precio = 39.99m,             Stock = 15,             Categoria = "Marvel"         };         var created = await _repository.CreateAsync(funko);         created.IsSuccess.Should().BeTrue();  // Act         var result = await _repository.FindByIdAsync(created.Value.Id);  // Assert         result.IsSuccess.Should().…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 9. `explicacion` · 491 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor · Test de ASP.NET Core - API REST
- **Origen:** `corpus/daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-04/practicas/04-test-aspcore.md` (trozo 19)
- **Asignatura:** desarrollo-web-entorno-servidor — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> cliente se conecta? a) `OnConnected()`. b) `OnConnectedAsync()`. c) `ConnectAsync()`. d) b (en versiones modernas). ---  ### Resultados Avanzados, Paginación y Criterios (Preguntas 96-105)  96. ¿Qué mecanismo permite a un cliente especificar el formato de los datos (JSON/XML)?     a) Routing.     b) Content Negotiation.     c) Middleware.     d) Filters.  97. Para soportar XML en ASP.NET Core Web API, ¿qué método se debe agregar en Program.cs?     a) `builder.Services.AddXmlSerializers()`.     b) `builder.Services.AddControllers().AddXmlSerializerFormatters()`.     c) `builder.Services.AddXml(…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 10. `explicacion` · 398 tokens

- **Contexto:** ASIR · implantacion-de-sistemas-operativos · # Script de Windows PowerShell para implementación de AD DS
- **Origen:** `corpus/derivado/asir/apuntes/aberlanas-iso/Guias/GuiaDeWindows2012Server.pdf.md` (trozo 145)
- **Asignatura:** implantacion-de-sistemas-operativos — *repositorio de una sola asignatura, tabla declarada*
- **Unidad:** (ninguna carpeta con significado)

> una UO. Podemos configurar que un usuario no pueda ejecutar el símbolo de comandos, podemos configurar que se desactive el rastreador de sucesos de apagado, etc.  TEMA 6-1 Página 139 I.S.O. Windows Server. Directivas de auditoria . Visor de eventos. En Windows podemos generar directivas de auditoria, que nos permiten realizar un seguimiento de las actividades de los usu arios sobre los recursos, registrando estas actividades en el registro de seguridad del sistema. Estas auditorías del sistema son una herramienta muy útil cuando nos encontramos con actividades extrañas en el directorio. Imagin…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 11. `explicacion` · 472 tokens

- **Contexto:** ASIR · gestion-de-bases-de-datos · oracleSQL
- **Origen:** `corpus/derivado/asir/apuntes/lora-1asir/BBDD/Apuntes/oracleSQL.pdf.md` (trozo 35)
- **Asignatura:** gestion-de-bases-de-datos — *sigla del material, tabla declarada*
- **Unidad:** (ninguna carpeta con significado)

> /* 6 meses */ INTERVAL '6' MONTH(3) TO MONTH La precisión en el caso de indicar tanto años como meses, se indica sólo en el año.  © Copyright - Copyleft ' Jorge Sánchez 2004 En intervalos de días a segundos los intervalos se pueden indicar como: /* 4 días 10 horas 12 minutos y 7 con 352 segundos */ INTERVAL '4 10:12:7,352' DAY TO SECOND(3) /* 4 días 10 horas 12 minutos */ INTERVAL '4 10:12' DAY TO MINUTE /* 4 días 10 horas */ INTERVAL '4 10' DAY TO HOUR /* 4 días*/ INTERVAL '4' DAY /*10 horas*/ INTERVAL '10' HOUR /*25 horas*/ INTERVAL '253' HOUR /*12 minutos*/ INTERVAL '12' MINUTE /*30 segundo…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 12. `codigo` · 510 tokens

- **Contexto:** DAM · desarrollo-de-interfaces · 5.- Swing
- **Origen:** `corpus/derivado/dam/apuntes/temario-dam-comesana/DI/Introduccion/5.- Swing.pdf.md` (trozo 210)
- **Asignatura:** desarrollo-de-interfaces — *sigla del material, tabla declarada*
- **Unidad:** (ninguna carpeta con significado)

> embargo, las clases del kit de editor proporciona útiles clases internas y variables de clases que son muy útiles para crear un GUI alrededor de un componente de texto.  Asociar Acciones con Ítems de Menú muestra como asociar una acción con un ítem de menú y Asociar Acciones con Pulsaciones de Teclas muestra como asociar una acción con una pulsación de teclas determinadas.  Ambas secciones hacen uso de clases manejables o de variables definidas en los kits de editor estándars de Swing.  Asociar Acciones con Ítems de Menú Como se mencionó anteriormente, podemos llamar al método getActions sobre…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 13. `explicacion` · 414 tokens

- **Contexto:** DAM · sistemas-de-gestion-empresarial · Unidad 5 SGE · esto es una cadena
- **Origen:** `corpus/derivado/dam/apuntes/temario-dam-comesana/SGE/Unidad 5 SGE/python para todos.pdf.md` (trozo 145)
- **Asignatura:** sistemas-de-gestion-empresarial — *sigla del material, tabla declarada*
- **Unidad:** Unidad 5 SGE

> license=”GPL”, scripts=[“ejemplo.py”], console=[“ejemplo.py”], options={“py2exe”: {“bundle_files”: 1}}, zipfile=None )  ÍndiCe Símbolos __call__ 105 __cmp__ 51 __del__ 51 __doc__ 75, 125 __init__ 43 __len__ 51 __main__ 74 __name__ 74 __new__ 51 __str__ 51 A archivos 82 atributos 42 B bases de datos 117 bool 22 break 33 C cadenas, métodos 54 candados 106 clases 42 clases de nuevo estilo 50 class 43 close 82 cola multihilo 111 colecciones diccionarios 27 listas 24  tuplas 26 comentarios 9 compile 91 comprensión de listas 61 condiciones, sincronización 108 continue 33 cookies 100 count 45 cPickle…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 14. `explicacion` · 507 tokens

- **Contexto:** DAW · curso 1 · entornos-de-desarrollo · ED3
- **Origen:** `corpus/derivado/daw/curso1/entornos-de-desarrollo/comesana/ED3.pdf.md` (trozo 30)
- **Asignatura:** entornos-de-desarrollo — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> con los valores esperados. Las principales son: AssertTrue() evalúa una expresión booleana. La prueba pasa si el valor de la expresión es true.  assertFalse()  evalúa una expresión booleana.  La prueba pasa si el valor de la expresión es false.  AssertNull()  verifica que la referencia a un objeto es nula.  assertNotNull() verifica que la referencia a un objeto es no nula.  AssertSame()  compara dos referencias y asegura que los objetos referenciados tienen la misma dirección de memoria.  La prueba pasa si los dos argumentos son el mismo objeto o pertenecen al mismo objeto.  assertNotSame()  C…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 15. `explicacion` · 498 tokens

- **Contexto:** DAW · curso 1 · fol · FO08
- **Origen:** `corpus/derivado/daw/curso1/fol/comesana/FO08.pdf.md` (trozo 24)
- **Asignatura:** fol — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> protección individual Protección de: 1. Cabeza. 2. Manos y brazos. 3. Total del cuerpo. 4. Pies y piernas. 5. Piel. 6. Ojos y cara. 7.  Oido.  8.  Vías respiratorias.  9.  Tronco y abdomen.  .  PROTECTORES DE LA CABEZA:  Cascos de seguridad, cascos de protección contra choques e impactos, gorros o sombreros para proteger la cabeza, cascos protectores del fuego, productos químicos, PROTECTORES DE MANOS Y BRAZOS:  Guantes protectores de perforaciones, cortes y vibraciones;  guantes contra las agresiones químicas, biológicas, térmicas o eléctricas;  manoplas, manguitos y mangas.  PROTECCIÓN TOTAL…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 16. `explicacion` · 460 tokens

- **Contexto:** DAW · curso 1 · programacion · Unidad 4 Introducción a Java · ud4_Guia_NetBeans
- **Origen:** `corpus/derivado/daw/curso1/programacion/lionel-ict/Unidad 4 Introducción a Java/ud4_Guia_NetBeans.pdf.md` (trozo 3)
- **Asignatura:** programacion — *carpeta del ciclo*
- **Unidad:** Unidad 4 Introducción a Java

> fácilmente: http://www.oracle.com/technetwork/es/java/javase/ downloads/jdk-netbeans-jsp-3413139-esa.html CFGS. DESARROLLO DE APLICACIONES WEB 4.4  Una vez en la página deberemos aceptar la licencia y elegir la descarga del sistema operativo que estemos utilizando. 2.2 Instalación de JDK & Netbeans IDE Una vez descargado el paquete, la instalación es muy sencilla, simplemente hemos de seguir los pasos del instalador: CFGS. DESARROLLO DE APLICACIONES WEB 4.5  CFGS. DESARROLLO DE APLICACIONES WEB 4.6  CFGS. DESARROLLO DE APLICACIONES WEB 4.7  3. CREACIÓN DE PROYECTOS 3.1 Conceptos básicos Un pro…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 17. `explicacion` · 423 tokens

- **Contexto:** DAW · curso 1 · sistemas-informaticos · fdisk /dev/sdb
- **Origen:** `corpus/derivado/daw/curso1/sistemas-informaticos/comesana/SI09.pdf.md` (trozo 7)
- **Asignatura:** sistemas-informaticos — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> sistemas RAID. Para identificar los discos duros o particiones se utiliza la siguiente sintaxis /dev/sda1 donde:  s indica el tipo de disco duro:  s – discos duros SATA o SCSI;  y h para discos IDE.   a identifica el primer disco duro, b el segundo, etcétera  1 indica el número de partición dentro del disco duro.  Así por ejemplo /dev/sdb3 identifica la tercera partición del segundo disco duro y /dev/sdb identifica el segundo disco duro.  Aunque vamos a hacer un repaso de algunas herramientas para trabajar con el sistema de ficheros, te recomendamos el siguiente enlace para conocer algo más…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 18. `explicacion` · 474 tokens

- **Contexto:** DAW · curso 2 · desarrollo-web-entorno-servidor-antiguo · DWES04
- **Origen:** `corpus/derivado/daw/curso2/desarrollo-web-entorno-servidor-antiguo/comesana-dwes/DWES04.pdf.md` (trozo 4)
- **Asignatura:** desarrollo-web-entorno-servidor-antiguo — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> a los usuarios. El proceso es el siguiente:  El servidor web debe proveer algún método para definir los usuarios que se utilizarán y cómo se pueden autentificar.  Además, se tendrán que definir los recursos a los qu e se restringe el acceso y qué lista de control de acceso (ACL - lista de permisos sobre un objeto (fichero, directorio, etc.), que indica qué usuarios pueden utilizar el objeto y las acciones concretas que pueden realizar con el mismo (lectura, escritura, borrado, etc.)) se aplica a cada uno.   Cuando un usuario no autentificado intenta acceder a un recurso restringido, el servi…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 19. `explicacion` · 490 tokens

- **Contexto:** DAW · curso 2 · despliegue-de-aplicaciones-web · Objetos raiz del dominio
- **Origen:** `corpus/derivado/daw/curso2/despliegue-de-aplicaciones-web/comesana/DAW05.pdf.md` (trozo 42)
- **Asignatura:** despliegue-de-aplicaciones-web — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> ejecución: 1. Verificar archivo de configuración /etc/bind/named.conf: root@debian-servidor-fp:/etc/bind# named-checkconf -p /etc/bind/named.conf 2.  Verificar el dominio de zona ejemplo.com en el archivo de zona /var/lib/bind/master/db.ejemplo.com.hosts root@debian-servidor-fp:/etc/bind# named-checkzone ejemplo.com /var/lib/bind/master/db.ejemplo.com.hosts  Despliegue de Aplicaciones Web José Luis Comesaña DAW 1.11.2.- Arranque y parada del servidor DNS.  En un sistema operativo Debian 6.0 (Squeeze) puedes comprobar el estado del servicio bind mediante el comando service o mediante el comando…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

## 20. `explicacion` · 422 tokens

- **Contexto:** DAW · curso 2 · empresa-e-iniciativa-emprendedora · EIE02
- **Origen:** `corpus/derivado/daw/curso2/empresa-e-iniciativa-emprendedora/comesana/EIE02.pdf.md` (trozo 18)
- **Asignatura:** empresa-e-iniciativa-emprendedora — *carpeta del ciclo*
- **Unidad:** (ninguna carpeta con significado)

> franquicia canadiense de venta de churros que vende al mundo una idea española; Saniphone (consultas médicas por teléfono)... ¡Anímate y participa en el foro!   Las siglas I+D+I responden a Investigación+ Desarrollo+ Innovación En el siguiente enlace se proporciona un artículo que explica de forma sencilla qué es eso de I+D+I, a la vez que proporciona información sobre programas marco de la Unión Europea y de España en I+D+I, y algunos ejemplos de empresas que están aplicando ambiciosos pro- gramas de I+D+I.  http://www.el-exportador.com/022003/digital/portada_articulo_a.asp Si estás interesa…

¿Se entiende solo? ___  ¿El tipo es correcto? ___

