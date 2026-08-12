# ADR 0011: la paráfrasis lleva glifo propio, y la sonda de estilos compara pares

- **Fecha:** 12 de agosto de 2026
- **Encargo:** 2.4 (interfaz mínima)
- **Estado:** aceptada

## Contexto

El 2.4 cerró con la puerta en verde: `tests/test_interfaz.py` comprobaba que ningún tipo de
afirmación se distingue **solo por color**, que es la condición que el enunciado escribe para que la
distinción aguante una videollamada. Mirando `/estilos` al 50 % de zoom —la comprobación que el
propio enunciado manda hacer— cuatro de los cinco tipos se reconocían sin leer la etiqueta:
`conocimiento` por el recuadro discontinuo, `analogia` por el punteado, `calculo` por la caja
monoespaciada y `andamiaje` por no tener recuadro.

`literal` y `parafrasis` no. Las dos eran "barra vertical a la izquierda más texto", y lo único que
las separaba era el color de la barra y el grosor del borde: el color muere en vídeo comprimido y un
borde de 1 o 2 px no se ve ni en el monitor. La `literal` se salvaba por poco gracias a las comillas
grandes y el sangrado. La `parafrasis` **no tenía marca estructural propia: era el estilo por
defecto.** Y es la pareja que hace el trabajo en la sesión, porque separa lo que el temario dice
palabra por palabra de lo que el sistema reformula.

La sonda daba verde porque preguntaba a cada tipo por separado —"¿traes alguna propiedad de forma?"—
y `border-left` se la daba a los dos. **Una señal que dos tipos comparten no distingue nada.**

## Decisión

**1. La `parafrasis` recibe una señal estructural suya: el glifo `≈`, con la misma construcción que
las comillas de la `literal` —dos marcas, una antes y otra después del cuerpo—.** Ni color ni
grosor, que son las dos cosas que la compresión de vídeo se lleva. El glifo además dice lo que el
tipo es —"esto viene a decir"— frente a las comillas de la cita textual.

**2. Y una segunda señal que no es el glifo: el cuerpo de la `parafrasis` va a ras y el de la
`literal` sangrado**, así que las dos siluetas empiezan en sitios distintos y la distinción no
depende entera de saber cuál de las dos marcas se está mirando.

**3. El peso visual va escrito en el CSS como condición, no como gusto.** Una marca pequeña se
pierde al 50 % exactamente igual que se pierde el color: sería cambiar una distinción invisible por
otra. Ninguna sonda puede comprobar esto, porque lee lo declarado y no lo visible, así que la
condición se escribe donde la va a leer quien toque el tamaño.

**4. La sonda nueva compara PARES.** `senales_de_forma()` reúne todas las reglas que alcanzan a un
tipo —incluidas las de `.cuerpo::before`, que es donde viven las comillas y donde la sonda vieja no
miraba— y exige que `literal` y `parafrasis` conserven cada una una señal que la otra **no** tiene.
Al hacerlo descarta lo que no distingue: el color, el grosor (incluido `double`, que igualado a un
grosor fino se dibuja como una línea sólida), los números —`margin-left: 14px` y `28px` son la misma
señal, porque un sangrado que solo cambia de cantidad no se ve si los dos tipos no están pegados— y
la fontanería que coloca la marca, porque el hueco donde va el glifo no es el glifo.

**5. La sonda se valida en las dos direcciones y con la mutación que dice el enunciado.** La hoja se
muta a un solo color y un solo grosor de borde; la mutación **devuelve su diff y el test lo afirma
antes de leer nada**, porque una mutación que no muta pone el test en verde por el motivo
equivocado. Y las reglas del 12 de agosto quedan ancladas como fixture: la sonda tiene que declarar
aquella pareja indistinguible. Eso convierte "visto en rojo con los ojos" en regresión permanente.

**6. Que `conocimiento` y `analogia` se parezcan es correcto y queda declarado** en el CSS, en
`/estilos` y en el enunciado. Los dos dicen "esto no sale de tu temario": la semejanza es semántica,
comparten familia —recuadro discontinuo por los cuatro lados— y se separan por el trazo y por la
etiqueta. Parecidos, no confundibles. No es el mismo caso que la pareja anterior, porque `literal` y
`parafrasis` **no** dicen lo mismo.

**7. El cierre del encargo pide otra mirada humana al 50 %, y con recarga forzada.** La sonda
comprueba que el CSS declara señales distintas; que se **vean** a un metro y tras la compresión no lo
sabe ningún test, y este fallo lo encontró un ojo y no la puerta. Cerrar con `ruff` y `pytest` en
verde sería sustituir el instrumento que funcionó por el que falló. Lo de la recarga tampoco es
retórica: la primera captura tras el arreglo de la decisión 1 fue **de la hoja cacheada**, y habría
dictado un veredicto sobre una página que ya no existía. **La puerta que ponemos por encima de los
tests tiene su propio verde mentiroso, y es la caché.** La causa —faltaba `Cache-Control` en
`/estatico`— está arreglada en el ADR 0013; la recarga se mantiene porque una pestaña ya abierta
enseña lo que cargó cuando cargó, y eso no lo arregla ninguna cabecera.

## Una hipótesis que no se sostuvo, escrita con su resultado

La primera versión de la decisión 1 era **un solo `≈` de 32 px en negrita, colgado a la izquierda del
cuerpo**, y venía con una hipótesis explícita: que el trazo del `≈` es más fino que el de una comilla
en negrita, pero que **eso se compensa con el tamaño** —de ahí los 32 px contra los 26 px de las
comillas, proporcionalmente más grande respecto a su cuerpo—.

**No se sostuvo.** Mirado al 50 % a un metro, el `≈` se quedaba corto al lado de las comillas de la
`literal`. La explicación, ya con el resultado delante: subir el tamaño estira el mismo trazo fino,
así que la mancha crece mucho más despacio que el número de píxeles, y llega tarde. Y la salida
tampoco era seguir subiendo, porque eso solo mueve el mismo argumento un poco más lejos, con una
tipografía cada vez más rara.

Lo que sí funciona es dejar de estimar la mancha y **copiar la construcción**: dos marcas, una antes
y otra después, que es exactamente lo que hacen las comillas. Ahí la paridad no depende de que
alguien acierte con un número. El tamaño subió también —a 34 px—, pero ya no es lo que sostiene la
decisión.

Queda escrito porque es la clase de suposición que se borra al arreglarla y luego se vuelve a
proponer: **más tamaño no arregla un trazo fino.** La condición del CSS —"el glifo pesa lo que pesan
las comillas"— siguió siendo la correcta; lo que estaba mal era el medio elegido para cumplirla.

## Trade-off

Lo que se pierde: la sonda es más larga y tiene criterio propio —qué cuenta como señal y qué no—, y
ese criterio es discutible en los bordes. Normalizar los números, por ejemplo, hace que un rediseño
legítimo basado solo en sangrados distintos salga rojo aunque se viera bien. Se prefiere ese falso
rojo, que obliga a mirar, al falso verde de hoy, que no obligó a nada. Y el fixture del 12 de agosto
envejece: si la hoja se reescribe entera, habrá que decidir si sigue representando algo.

Lo que se gana: la propiedad que se comprueba es por fin la que importa. Y queda una regla
reutilizable, que es lo que de verdad se llevaba puesto este fallo: **cuando el criterio dice "se
distinguen", "no se solapan", "son distintos" o "son únicos", el detector compara pares, no
elementos.** Barrido del repo con esa pregunta: un hallazgo, en la línea de al lado —el test de que
cada tipo lleva etiqueta con texto no comprobaba que las cinco fueran distintas—, corregido aquí. El
resto de detectores de propiedades relacionales ya comparaban pares (conflictos del 1.8, pares oro
del 3.0, dispersión del 7.3).

## Cuándo se revisa

Cuando la fase 3 traiga afirmaciones `literal` y `parafrasis` de verdad y la distinción se pueda
comprobar sobre salida real, que es donde el enunciado del 2.4 mandó esa mitad de la verificación.
Ahí la pareja se mira otra vez, ya con texto que no está fabricado.
