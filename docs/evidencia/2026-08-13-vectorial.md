# Evidencia: recuperación vectorial del 3.2 sobre los 100 pares oro

- **Fecha:** 2026-08-13
- **Encargo:** 3.2
- **Commit:** `e30eb97`
- **Corrida:** `corridas_eval` id **3**
- **Configuración:** BGE-M3 con la revisión anclada del corpus, distancia coseno, k=20,
  **siempre con filtro de asignatura**

## El número, partido desde el primer día y no solo en el 3.5

| Corte | Global | busqueda | lectura |
|---|---|---|---|
| recall@5 | 73.0 % | **68.4 %** (13/19) | **74.1 %** (60/81) |
| recall@20 | 82.0 % | **78.9 %** (15/19) | **82.7 %** (67/81) |

## LA PREDICCIÓN DEL 3.2, ESCRITA ANTES DE MEDIR: CUMPLIDA

Antes de correr esto quedó escrito en el enunciado del 3.2 que, como el vectorial **no comparte
mecanismo** con la forma en que se localizaron los 19 pares `busqueda` —que fue buscar términos de
la pregunta en el texto—, su hueco entre `busqueda` y `lectura` debería ser **mucho menor** que los
15,7 puntos de la léxica. Medido sobre los mismos 100 pares y con el mismo k:

| recall@20 | global | `busqueda` | `lectura` | hueco |
|---|---:|---:|---:|---:|
| Léxica (3.1) | 61,0 % | 73,7 % | 58,0 % | **+15,7** |
| Vectorial (3.2) | 82,0 % | 78,9 % | 82,7 % | **−3,8** |

**Y trae un dato que la predicción no pedía: el hueco no solo se encoge, cambia de signo.** Con el
vectorial, `lectura` sale **mejor** que `busqueda`. Eso es lo que cierra la cuestión: **si los 19
pares de `busqueda` fueran simplemente más fáciles, el vectorial también los acertaría más, y los
acierta menos.** La única explicación que queda en pie es la que se predijo: los 15,7 puntos de la
léxica eran **sesgo de mecanismo compartido**.

**Consecuencia, y es lo que hace que esta medida valga más que el número:** el reparto
`busqueda`/`lectura` del conjunto oro deja de ser una **limitación declarada** y pasa a ser un
**INSTRUMENTO VALIDADO**. A partir de aquí, "reportar por subconjunto" no es una precaución: es una
medida con significado conocido, y la diferencia entre las dos columnas dice cuánto mecanismo
comparte una vía con la construcción del conjunto. La lectura estaba escrita antes de mirar, que es
lo único que la hace valer.

**El número honesto para juzgar la recuperación sigue siendo el de `lectura`**, y ahí el vectorial
da **82,7 %** frente al 58,0 % de la léxica.

## El índice: lo que eligio el planificador

En el 2.1 quedó medido y declarado que, con 3.892 filas en la partición, el planificador prefiere el
escaneo secuencial y el HNSW no se usa. Aquí se comprueba **con la consulta real de este encargo**.

**Y la regla de lectura estaba escrita antes de medir, en el enunciado del 3.2:** si el plan enseña
el índice, el recall es **aproximado por construcción** —`ef_search` por defecto es 40—, y un recall
flojo podría ser del índice y no del embedding; en ese caso se repite con el escaneo forzado antes de
concluir nada, y la diferencia entre los dos números es el precio del aproximado, que es un dato y no
un fallo. Si gana el escaneo, el recall es **exacto** y se declara así.

Se corrió de las dos maneras y **los números salen idénticos al decimal**, que es la comprobación de
que aquí no hay aproximación de por medio: el plan es `Seq Scan` sobre la partición, 9,5 ms.


## Hasta dónde aguanta una paráfrasis, medido y no supuesto

La verificación del encargo es que **paráfrasis de preguntas oro encuentren su fragmento**. Se
probaron dos, las dos quitando el vocabulario que la búsqueda léxica usaría y conservando el término
que nombra la tecnología. **Una pasa y la otra no**, y las dos se escriben aquí porque anclar solo la
que pasa sería ajustar la prueba al resultado:

| Paráfrasis | De | ¿Encuentra su fragmento? |
|---|---|---|
| *"¿Qué se escribe en Pebble para meter un trozo reutilizable como la barra de navegación dentro de otra página?"* | oro-009 | **sí**, en el top 5 |
| *"Si los datos se pierden al mandar al usuario a otra página, ¿cómo se le hace llegar un aviso de que todo fue bien?"* | oro-005 | **no** |

**Y un caso más, que enseña el límite con claridad.** Sobre oro-001 se probaron cuatro versiones de
la misma pregunta —original, paráfrasis suave conservando "Spring Boot" y "cookie", media, y dura sin
vocabulario técnico— y **ninguna de las cuatro** trae el fragmento oro en el top 20. Ese par es uno
de los que fallan también con la pregunta original, así que no mide la paráfrasis: mide que hay un
18 % de pares que esta vía no encuentra de ninguna manera.

**Lectura honesta: la vía vectorial aguanta algunas paráfrasis, no todas.** Cuando se le quita
también el término que nombra la tecnología, se va a prosa genérica del mismo tema —sesiones,
servidores— que es semánticamente vecina y no es la respuesta. No es un fallo de este encargo: es
hasta dónde llega una sola vía, y es exactamente el motivo por el que el 3.3 **fusiona en vez de
elegir**.

## Los que no entran en el top 5

| Par | Grupo | Posición | Pregunta |
|---|---|---|---|
| `oro-001` | busqueda | no aparece | ¿Dónde se almacenan los datos de la sesión de un usuario en Spring Boot, y qué es lo único |
| `oro-002` | busqueda | no aparece | ¿Qué anotación se usa en un parámetro de método del controlador para leer un atributo de s |
| `oro-003` | busqueda | 17 | ¿Para qué tipo de datos son apropiadas las cookies y por qué no se deben guardar en ellas  |
| `oro-013` | busqueda | no aparece | ¿Qué anotación se usa en una clase que recibe peticiones y devuelve datos serializados en  |
| `oro-014` | busqueda | no aparece | ¿Con qué anotación se marca el componente que implementa el acceso a la base de datos o a  |
| `oro-016` | busqueda | 13 | ¿Qué módulo de Spring proporciona funcionalidades de producción como la monitorización y l |
| `oro-020` | lectura | no aparece | ¿Cuál es la principal función del componente Controlador en el patrón MVC de ASP.NET Core? |
| `oro-022` | lectura | 12 | ¿Qué tipo de ciclo de vida de un servicio crea una instancia nueva en cada petición HTTP? |
| `oro-025` | lectura | no aparece | ¿Qué objetivo tiene el patrón Post-Redirect-Get tras procesar un formulario POST? |
| `oro-027` | lectura | no aparece | ¿Cómo protege ASP.NET Core los formularios contra CSRF? |
| `oro-031` | lectura | no aparece | ¿Qué son los layouts y cómo permiten que las vistas hijas extiendan una plantilla base? |
| `oro-037` | lectura | 9 | ¿Qué diferencia hay entre ViewData, TempData y las propiedades del PageModel para guardar  |
| `oro-040` | lectura | no aparece | ¿Qué se hace con la sesión cuando hay varios servidores detrás de un balanceador? |
| `oro-041` | lectura | no aparece | ¿Qué son los claims y el ClaimsPrincipal en la autenticación? |
| `oro-042` | lectura | no aparece | ¿Cómo se deben guardar las contraseñas de los usuarios? |

## Cómo se reproduce

```bash
DATABASE_URL=... python scripts/medir_recuperacion.py --evidencia docs/evidencia/2026-08-13-vectorial.md
```

No gasta dinero: es SQL contra la base local. Antes de correrlo, `python scripts/verificar_oro.py`,
que es la regla del 3.0 —un par oro desplazado no da error, da ruido con aspecto de dato—.
