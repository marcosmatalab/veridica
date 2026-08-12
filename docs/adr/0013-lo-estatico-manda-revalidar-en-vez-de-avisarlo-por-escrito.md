# ADR 0013: `/estatico` manda revalidar, en vez de avisarlo por escrito

- **Fecha:** 13 de agosto de 2026
- **Encargo:** 2.4 (interfaz mínima), con la política de producción declarada para el 8.1
- **Estado:** aceptada

## Contexto

El cierre del 2.4 no lo da la suite: lo da una persona mirando `/estilos` al 50 % de zoom, porque si
`literal` y `parafrasis` se distinguen a un metro y tras la compresión de vídeo no lo sabe ningún
test (ADR 0011).

El 12 de agosto de 2026 esa mirada estuvo a punto de dictar un veredicto sobre una página que ya no
existía: la primera captura tras un arreglo de la hoja era **la versión cacheada**. La puerta que
este proyecto pone por encima de los tests resultó tener su propio verde mentiroso, y es la caché del
navegador.

El diagnóstico era exacto y la primera respuesta fue el rodeo: escribir el aviso en cinco sitios
—enunciado del 2.4, 8.4, la propia página `/estilos`, el comentario del CSS y el ADR 0011— para que
quien mire se acuerde de recargar. Pero **la causa no era que a nadie se le olvidara recargar: era
que faltaba una cabecera.** `/estatico` se servía con `ETag` y `Last-Modified` y **sin
`Cache-Control`**, y sin instrucción de frescura el navegador la inventa por heurística y puede
servir su copia sin preguntar al servidor. Cinco avisos escritos siguen siendo prosa que alguien
tiene que recordar.

## Decisión

**1. Todo lo que cuelga de `/estatico` se sirve con `Cache-Control: no-cache`.** No significa "no
caches": significa "no uses tu copia sin preguntar antes". El navegador se queda el fichero y
revalida con el ETag que ya servíamos, así que lo normal es un **304 sin cuerpo**, no una descarga.
Una línea de servidor, ningún cambio en la vista del alumno, ninguna marca de versión que decidir.

**2. Cubre `/estatico` entero, no la hoja.** Es el punto que más caro sale y el que menos se ve
venir: un estilo cacheado se ve raro, pero **un `render.js` viejo dibuja las etapas de otra forma o
no las dibuja**, y esa es justo la capa sin puerta automática, porque en el CI no hay motor de
JavaScript. La cabecera va en la clase que sirve el directorio, así que un fichero nuevo la hereda
sin que nadie se acuerde de nada.

**3. Se verifica con el cliente de test, no mirando un navegador**, y en las dos direcciones. Lo que
nos mordió fue precisamente la heurística de un navegador: no es determinista y no se puede poner en
una puerta. Los tres hechos comprobados en `tests/test_interfaz.py`: la cabecera está en `estilo.css`,
`render.js` y `app.js`; una petición con `If-None-Match` devuelve **304 sin cuerpo** —y con la
cabecera repetida, que es donde el navegador refresca lo que guarda junto a la copia—; y **tras tocar
el fichero, la misma petición condicional devuelve 200 con el contenido nuevo**, porque un 304 eterno
sería el mismo fallo con otra cara. El cambio del fichero se confirma en disco (tamaño y `mtime`)
antes de leer ninguna respuesta. Y la puerta se vio en rojo quitando la cabecera antes de creerse su
verde.

**4. La respuesta de producción es otra y queda declarada en el 8.1, no construida hoy:** URL con
marca de versión y `max-age` largo con `immutable`, de forma que el navegador no pregunte nunca y una
versión nueva sea una URL nueva. Ahí sí hace falta decidir de dónde sale la marca —`mtime` al
arrancar es lo barato, hash del contenido lo correcto—, y esa decisión no se toma para ahorrar un 304
contra localhost.

**5. El aviso escrito se queda, porque el arreglo vale de aquí en adelante y NO es retroactivo.**
Una copia guardada **antes** de que la cabecera existiera se guardó sin instrucción de frescura, así
que el navegador la sigue sirviendo por heurística —y como no pregunta, tampoco se entera nunca de la
regla nueva: la entrada vieja no se libera sola—. Añádase que una pestaña abierta desde hace media
hora enseña lo que cargó entonces. Por eso el 8.4 arranca **en ventana limpia**, incógnito o perfil
nuevo, donde la caché empieza vacía y la diferencia se ve al instante; la recarga forzada cubre la
pestaña que ya se tenía abierta. Esto es una propiedad del estado guardado en el navegador, no del
servidor, así que no hay puerta que lo compruebe: va en el ritual y por escrito, a diferencia de las
tres comprobaciones de la decisión 3.

Y merece la pena verlo junto a la decisión 4: **la URL con marca de versión también resuelve esto**,
y no solo el coste. Una versión nueva es una URL nueva, y una URL nueva no tiene copia guardada
contra la que competir —ni vieja ni con reglas raras—. Es el argumento que más peso tiene para el
8.1, más que el 304 que se ahorra.

## La otra fuente de material viejo, y las dos salidas que NO se toman

La caché del navegador no era la única. La noche del 12 de agosto de 2026 el HTML no cambió hasta un
`docker compose up -d --build api`: **`web/` va copiado dentro de la imagen** (`COPY web ./web`, y el
servicio `api` no lo monta), así que tocar un fichero en el disco no cambia lo que sirve el
contenedor. Ninguna ventana limpia arregla eso, porque ahí el que sirve lo viejo es el servidor: a un
navegador impecable se le está dando material caduco con todas las cabeceras correctas. Queda
ritualizado en el 8.4 —primero `--build`, después ventana limpia, en ese orden— y declarado en el
docstring de `tests/test_interfaz.py`, que dice sobre qué corren esos tests: el disco del repo y la
aplicación en proceso, nunca la imagen.

**Descartado: montar `web/` como volumen en el contenedor.** Quitaría la fuente entera en local
—editar y recargar, sin `--build`— y aun así no se hace, porque invertiría la regla que este repo ya
ha aplicado tres veces (transformers sin anclar, psycopg sin instalar, `sys.path`): **lo local se
parece a lo que corre de verdad, nunca al revés.** Cambiaría un modo de fallo conocido, escrito y
ritualizado por una divergencia sin explorar, en vísperas de la sesión y justo en la capa que se
enseña. El coste de no hacerlo es un `--build` en el ritual; el de hacerlo es una demo corriendo
sobre una configuración que no es la que se despliega.

**No construida, y anotada en el 8.1 para que sea decisión y no olvido: hacer la caducidad VISIBLE en
vez de eliminarla.** Una huella de lo que `web/` lleva dentro de la imagen, expuesta en `/salud` y en
la muestra de estilos, convierte "el contenedor sirve lo viejo" en algo que se lee en pantalla en vez
de algo que hay que sospechar. **Y a diferencia de la caché del navegador, esto sí es determinista y
sí puede llevar puerta**, porque es un hecho del servidor y no estado guardado en la máquina de quien
mira. Va con la marca de versión de la decisión 4 porque son la misma pregunta —qué versión de este
material estático se está sirviendo— y comparten la decisión de dónde sale la marca.

## Trade-off

Lo que se pierde: una ida y vuelta por fichero en cada carga. Contra localhost es un 304 sin cuerpo y
no se nota; con TLS y latencia real sí se notaría, y por eso el 8.1 cambia de política en vez de
heredar esta.

Lo que se gana: la puerta humana deja de depender de que alguien se acuerde. Y la lección, que es más
grande que la cabecera: **cuando el diagnóstico señala una causa, la salida es atacar la causa, no
escribir el rodeo.** Un aviso en cinco sitios es cinco sitios donde alguien puede no mirar; una
cabecera es una vez y para todos los ficheros, incluidos los que aún no existen. Este proyecto ya
había elegido dos veces meter el criterio en el código en vez de en el texto —los campos que viajan
por la puente, resueltos en la migración `0003` en vez de en una nota sobre qué campo es de qué
norma; y el cero anclado del 1.13— y esta es la tercera.

## Cuándo se revisa

En el 8.1, al montar producción: ahí `no-cache` se sustituye por URL versionada con `max-age` largo e
`immutable`, y este ADR se actualiza con la marca que se haya elegido y su porqué.
