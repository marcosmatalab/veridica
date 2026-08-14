# Evidencia: el paso 3 — el umbral del portero y el vigilante de ritmo, con el dato que el 2.5 destapó

- **Fecha:** 14 de agosto de 2026
- **Encargo:** 4.6, umbrales #3 (`SOLAPE_MINIMO`) y #5 (ritmo), que cerraron SIN CALIBRAR
- **Rama:** `portero-marca`
- **Corridas:** **41** (recogida con 60 consultas reales) y su repetición con el texto de cada frase

## 0. De dónde salen los datos, y por qué de ahí

**60 consultas reales** por el camino de servicio, con las preguntas de los **conjuntos congelados**
del 4.0/5.x (`fuga_de_solucion`, `fuera_de_temario`, `premisas_falsas`) y del **conjunto oro** del
3.0. Dos motivos, y el segundo es el que decide: son preguntas del temario, y **están congeladas con
su sha**, así que el conjunto sobre el que se calibra no lo elige quien calibra.

Cero consultas fallidas. El servicio se levantó con el código de esta rama en un puerto nuevo y su
arranque se confirmó **por su propio log**, no por si el puerto contestaba.

## 1. El vigilante de ritmo: VALIDADO en 35, y no se mueve

El 4.6 lo dejó SIN CALIBRAR diciendo *"el ritmo por consulta no se persiste"*. El 2.5 corrigió el
diagnóstico —**sí** se persistía, pero era el de la **última ventana**, y el umbral pregunta por el
**peor momento**— y empezó a guardar `minimo_observado`.

**Con 30 consultas sanas:**

```
peor momento (tokens/s):  min 110,0 | p10 118,5 | p25 127,5 | mediana 140,0 | max 158,5
umbral actual 35:         cortaría 0 de 30 consultas SANAS
```

**Cero cortes falsos, con un factor 3 de margen medido** en vez de estimado. El umbral pasa de
*declarado sin calibrar* a **validado**.

**Y no se mueve, aunque el desempate mecánico decía 50.** El motivo es que **la banda 35-50 está
vacía**: no hay ninguna consulta sana ahí (la más lenta va a 110) ni ninguna averiada (las dos
medidas el 13/08 iban a 4 y 11 tok/s). **Elegir dentro de una banda donde no se ha observado nada
es elegir sin evidencia**, y mover un guarda sin evidencia es exactamente lo que este encargo
existe para no hacer.

### La corrección de método, que es lo que este barrido enseñó de verdad

El criterio pre-escrito del script decía *"manda no cortar sano"* y **contradecía la asimetría
MEDIDA que `app/core/ritmo.py` ya tenía escrita**: un corte falso cuesta **~2 s** —se corta, se
avisa y se vuelve a pedir— y un corte que no ocurre cuesta **~60 s de pantalla congelada**, o sea
**treinta veces más**. Escribí un criterio nuevo sin leer el que ya estaba justificado con números.

Queda escrito en el script en vez de corregido en silencio, porque es la misma familia que heredar
una calibración sin re-derivarla, vista desde el otro lado: **allí se reutiliza un porqué que ya no
vale; aquí se inventa uno nuevo teniendo uno medido al lado.**

### Límite declarado

30 consultas de **una sola sesión** con el proveedor sano, todas entre 110 y 158 tok/s. Eso **no es
el envolvente operativo**: no contiene el caso *"sana pero lenta"*. Si aparece, el número se vuelve
a mirar con ese dato delante.

## 2. El umbral del portero: se queda en 0,50, y el motivo lo dieron los CASOS

La dirección del barrido era **hacia arriba** (ADR 0021: desde que el portero marca, el error caro
es dejar pasar sin marca). El desempate pre-escrito era: entre los umbrales que no marcan más del
**25 %** de las frases —techo declarado antes de mirar, porque *marcar todo es no marcar nada*—,
gana el más alto.

**Lo que salió del barrido mecánico** (153 frases juzgadas, 60 consultas):

| umbral | marcadas | tasa |
|---:|---:|---:|
| 0,50 (actual) | 18 | 11,8 % |
| 0,60 | 29 | 19,0 % |
| **0,70** | **38** | **24,8 %** ← elegido por el desempate |
| 0,75 | 42 | 27,5 % (pasa del techo) |

**Y el 0,70 aterrizó a un pelo del techo (0,2484 contra 0,25), o sea que eligió el TECHO y no el
dato.** Por eso se miraron los casos, que es la regla de esta casa antes de creerse una tasa.

### Las 28 frases de la banda [0,50, 0,70), leídas una a una

Casi todas son **prosa correcta y respaldada**. Cuatro ejemplos de las que el 0,70 marcaría:

- *«Lo único que viaja en la cookie es el identificador de la sesión (JSESSIONID).»* (0,67) — **es
  la respuesta canónica del conjunto oro**.
- *«El patrón Post-Redirect-Get (PRG) tiene como objetivo principal prevenir el reenvío accidental
  del formulario si el usuario refresca la página.»* (0,62).
- *«Para validar el formulario y capturar los errores en un POST, debes añadir @Valid justo antes
  del @ModelAttribute y un parámetro BindingResult…»* (0,60).
- *«No se deben guardar datos sensibles en cookies porque el usuario puede ver y modificar los
  datos…»* (0,58).

**Subir el umbral marca lo bueno.** El agregado decía "24,8 %, cabe bajo el techo"; los casos dicen
"marcarías la mejor respuesta del conjunto". **Un agregado no miente: promedia.**

### La reserva, que es el hallazgo de verdad

**Al 0,50 ya se marca prosa legítima.** De las **23** frases marcadas hoy, contadas a ojo, **entre
10 y 12 son correctas y están respaldadas** (≈45 % de las marcas), entre ellas:

- *«Siempre debes validar también en el servidor para garantizar la seguridad…»* (0,40) — que es
  **la refutación correcta** de una premisa falsa del conjunto.
- *«La anotación que se usa en una clase que recibe peticiones y devuelve datos serializados en
  JSON… es @RestController.»* (0,18) — correcta y específica.
- *«No basta con comprobar la extensión de un fichero subido porque un hacker podría renombrarlo.»*
  (0,33).

Las otras 11-13 sí merecen la marca: contenido **de otra asignatura** (clave primaria, Entity
Framework, GraphQL) en respuestas a preguntas de DWES, relleno valorativo (*"es una buena práctica
obligatoria"*), procedencia inventada (*"la pregunta 24 de tu temario"*) y una invención técnica
(*"el modo estricto de @Valid"*).

**Conclusión, y no es sobre el umbral: el problema es QUÉ se mide.** El solape de vocabulario no
distingue *"respaldado"* de *"dicho con otras palabras"*, y por encima de 0,5 no discrimina nada. La
palanca no es mover el número: es **medir el respaldo de otra forma** —el NLI ya está construido y
sabría juzgar si una frase se sigue de las afirmaciones—. Queda **declarado y no construido**.

### Y un defecto nuevo, destapado por la lectura

Una de las marcadas era *«El núcleo del pipeline que procesa las peticiones HTTP en ASP.»* — la
frase está **cortada en `ASP.NET`**, porque `FIN_DE_FRASE` incluye el punto. El trozo puntúa bajo
por estar mutilado, no por carecer de respaldo. **Es la misma familia que la partición de
`frases_de` que obligó a la ventana anclada del NLI: el partidor decide qué se juzga.** Declarado en
el código; no se toca aquí porque cambiarlo mueve todos los contadores de cobertura publicados.

## 3. Desenlace del inventario del 4.6

| umbral | antes del paso 3 | ahora |
|---|---|---|
| #3 `SOLAPE_MINIMO` | SIGUE SIN CALIBRAR | **BARRIDO: se queda en 0,50**, con los casos leídos y la reserva del 45 % de marcas injustas declarada |
| #5 ritmo | SIGUE SIN CALIBRAR | **VALIDADO en 35**: cero cortes sobre 30 sanas, banda 35-50 vacía |

Quedan **1 de 6** sin calibrar: el anclaje de operandos (#6), que necesita diseño antes que barrido
— separar convención de premisa— y así estaba declarado desde el principio.
