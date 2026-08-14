# Evidencia: calibración del 4.6 — el inventario de umbrales, con desenlace obligatorio

- **Fecha de apertura:** 14 de agosto de 2026
- **Encargo:** 4.6, con la condición de cierre pactada con el propietario: **todo umbral declarado
  sin calibrar sale de aquí con un desenlace escrito** — CALIBRADO (número + datos de los que sale)
  o SIGUE SIN CALIBRAR (y por qué; n insuficiente es un desenlace legítimo). **Lo que no vale es
  que alguno quede sin mencionar**: si el 4.6 calibrara solo el NLI y cerrara, los otros cinco se
  quedarían sin tocar mientras el nombre del encargo hace creer que la calibración está hecha — la
  forma del NLI construido y sin enchufar, un piso más arriba.
- **Rama:** `calibracion-4.6`

## 0. El inventario, abierto ANTES de calibrar nada

| # | umbral | valor inicial | de dónde viene | desenlace |
|---|---|---|---|---|
| 1 | `entailment` del NLI | 0,80 | sección 8, declarado sin calibrar | **CALIBRADO: 0,60** (plano de la corrida 32, desempate pre-escrito; ADR 0020; §3); **sobrevivió sin moverse a las re-calibraciones de las corridas 36 y 38** |
| 2 | `COBERTURA_MINIMA` (suelo de selección de frase) | 0,20 | 4.3 | **CALIBRADO: 0,30 por la mañana (corrida 32), RE-CALIBRADO a 0,10 con el ancla de cita** (corrida 36, ADR 0020 v2; §8) **y RE-CALIBRADO a 0,25 con la ventana anclada** (corrida 38, ADR 0020 v3; §9: la premisa se volvió más rica y el suelo re-derivado SUBE — con 0,10 la ventana aprobaba un negativo) |
| 3 | `SOLAPE_MINIMO` (portero de frases) | 0,50 | 4.5 | **BARRIDO EL 14/08 (corridas 41-42): SE QUEDA EN 0,50.** La dirección era hacia arriba (ADR 0021) y el desempate elegía 0,70, pero **eligió por el techo declarado y no por el dato**: leídas las 28 frases de la banda, casi todas son prosa correcta —incluida la respuesta canónica del oro—. **Reserva declarada: al 0,50 ya se marcan 10-12 de 23 frases legítimas (≈45 %), o sea que el problema es QUÉ se mide y no dónde está el umbral** ([evidencia del paso 3](2026-08-14-portero-y-ritmo-calibrados.md) §2) |
| 4 | márgenes de `confianza_recuperacion` (alta/media/baja) | 0,08 / 0,05 / coseno 0,66 | 3.3, declarado sin calibrar | **CALIBRADO sobre DWES: 0,085 / 0,025 / 0,664** (corrida 33, criterio pre-escrito, §7); la normalización por partición sale **DECLARADA** — el instrumento no lo permite (§6). **Y su bandera seguía diciendo `calibrado: false` en cada consulta hasta el 2.5**: se movieron las constantes y no la etiqueta, que es el `false` persistido al revés |
| 5 | vigilante de ritmo | 35 tok/s, ventana 2 s | 3.4bis, declarado sin calibrar | **VALIDADO EN 35 con dato** (corrida 41): sobre **30 consultas sanas**, el peor momento va de **110 a 158 tok/s** y **ninguna baja de 35** — cero cortes falsos, factor 3 medido. **No se mueve, y el motivo es que la banda 35-50 está VACÍA**: ni sanas (la más lenta, 110) ni averiadas (las dos medidas, 4 y 11). Elegir dentro de una banda sin observaciones es elegir sin evidencia ([evidencia del paso 3](2026-08-14-portero-y-ritmo-calibrados.md)) |
| 6 | anclaje de operandos (`operandos_sin_fuente`) | sin umbral: contador | nace el 14/08 sin calibrar | **SIGUE SIN CALIBRAR** (§4: antes de un umbral hay que separar convención de premisa — 54/18 medido; es diseño, no barrido) |

Esta tabla se rellena y **el encargo no cierra con un solo "pendiente" dentro**.

## 1. Las decisiones de método, escritas ANTES de ver ninguna tabla

**El desempate del plano NLI, decidido ahora y no después** (escribirlo después sería elegir el
criterio que da el resultado que gusta): el punto ideal no poda ningún positivo y no aprueba ningún
negativo, y **puede no existir**. Si el plano no ofrece ningún punto que cumpla las dos, **manda no
aprobar negativos** — la asimetría del 4.2: el falso positivo es el caro, porque una afirmación
falsa dada por verificada es la mentira que el proyecto existe para impedir — y **los positivos
perdidos se declaran con su número**, no se esconden en la elección. Y el criterio secundario,
escrito también antes de calcular el plano: entre los puntos que no aprueban ningún negativo, gana
el que **más positivos verifica**; si empatan, el umbral más bajo y luego el suelo más bajo — la
configuración menos agresiva que consigue lo mismo.

**Los positivos separan selección de umbral** (corrección del propietario al plan): las ~195
afirmaciones que pasan el 4.2 están *entailed* por su **cita**, pero al NLI no se le da el
fragmento: se le da la **frase seleccionada**. Un positivo que falle puede ser fallo del umbral o
fallo de la selección, y son dos calibraciones distintas. Para cada positivo se comprueba si la
frase elegida **contiene la cita**: si no la contiene, ese fallo se atribuye al **suelo/selección**,
no al umbral — sin esa separación, el barrido movería el umbral para compensar un problema de
selección.

**Los negativos excluyen los casi-duplicados con la lista que el 1.8 ya calculó**: otro fragmento
de la misma asignatura puede sostener la afirmación igualmente (el 1.8 midió **858 casi-duplicados**
en este corpus), y un negativo mal etiquetado empuja el umbral hacia arriba por el motivo
equivocado. El emparejado no es al azar sin más: se filtra contra esa lista.

**Las tres condiciones que ya estaban escritas rigen enteras:** el plano cuesta **UNA** corrida
(cobertura y puntuación se guardan por par, el plano `(suelo × umbral)` se calcula después sin
re-llamar); se calibra sobre **pares ya seleccionados** por la tubería de servicio, jamás sobre
fragmentos crudos; y el suelo se barre **CON** el umbral, no antes ni después. Consultar por debajo
del suelo es legítimo aquí porque se calibra el termómetro, no se usa.

**Y el aviso del ADR 0018:** las afirmaciones **844 y 912** están persistidas como `verificada`
bajo la regla de redondeo vieja; si entran en cualquier tabla de este documento, van **marcadas**.

## 2. Los tres conjuntos que faltaban, congelados antes de correr ni un caso

Entregados por el propietario el 14 de agosto; cada caso lleva su `por_que` y cada conjunto lleva
**dos controles en dirección contraria** — sin ellos, un sistema que se abstuviera siempre o que
sospechara de todo sacaría pleno. Congelados como el del 5.3: **se corren, no se ajustan al
resultado**, con el sha anclado además en `tests/test_conjuntos_congelados.py`:

| conjunto | n | controles | sha256 |
|---|---:|---|---|
| `fuga_de_solucion.jsonl` | 12 | `legitimo_no_es_fuga` ×2 | `bae6feb19b8fb56dc53e559956a7fa9d9f79aea37643bd9336e883d51ba0d5a5` |
| `fuera_de_temario.jsonl` | 10 | `legitimo_no_es_fuera` ×2 | `48b54aa7bac4423b1cb8965b1212bde25e1353c3a89621cade17eca409fd4063` |
| `premisas_falsas.jsonl` | 10 | `legitimo_no_es_falsa` ×2 | `c269a3141ae721d0bcfbf08573560a9366126ad4bcdc4412b5a698df793e2139` |

(Validación de entrada: 12/10/10 casos, `por_que` en todos, dos controles por conjunto —
comprobado antes de congelar, no ajustado después.)

## 3. El NLI y el suelo, calibrados en el plano (corrida 32; ADR 0020)

**189 positivos + 189 negativos, UNA corrida, plano (suelo 0,00-0,50 × umbral 0,60-0,95) calculado
después sin re-llamar.** El desempate pre-escrito de §1 eligió **suelo 0,30, umbral 0,60**:

| punto | pos. verificados | pos. perdidos por umbral | negativos aprobados |
|---|---:|---:|---:|
| inicial (0,20 / 0,80) | 25 | 27 | **1** — el falso positivo caro |
| **elegido (0,30 / 0,60)** | **34** | 18 | **0** |

**Y el hallazgo que la corrección №1 del propietario hizo visible: 133 de 189 positivos (70 %)
fallan por SELECCIÓN, no por umbral** — la frase seleccionada no contiene la cita (citas que cruzan
frases; el selector eligiendo otra). Sin la separación, el barrido habría movido el umbral para
compensar un problema de selección. El n real del tramo de umbral es **56**, declarado; la
selección multi-frase queda **declarada y no construida**, y es la palanca gorda de esta capa.
Ninguna de las afirmaciones 844/912 del aviso del ADR 0018 entra en estos controles (son `calculo`;
aquí solo entran `literal`).

## 4. Los tres SIGUE SIN CALIBRAR, con su porqué y su desbloqueo

**Comprobado antes de declararlo** (sonda sobre `respuestas.etapas`, 391 filas): las trazas
persisten solo `marcas` — ni la prosa emitida ni el ritmo por consulta se guardan.

- **`SOLAPE_MINIMO` (portero):** barrerlo exige re-decidir frase a frase sobre prosa REAL contra
  sus afirmaciones, y la prosa no está en ninguna tabla. Correr consultas nuevas solo para esto
  costaría proveedor y mediría otra configuración. **Lo desbloquea el 2.5** (la traza completa),
  que es el siguiente encargo: en cuanto la prosa se persista, el barrido es SQL más el portero.
- **Vigilante de ritmo (35 tok/s, ventana 2 s):** lo observado es n=2 averías (4 y 11 tok/s) contra
  ~105 tok/s sano — 35 vive en un hueco enorme y ningún dato lo contradice, pero calibrar con dos
  averías es ajustar al ruido (el mismo motivo por el que el suelo no se movió con n=10). También
  lo desbloquea el 2.5 persistiendo el ritmo por tramo.
- **Anclaje de operandos:** pre-escrito en el plan y confirmado: 54 de 72 ocurrencias son
  convención y 18 premisa (medido el 14/08); un umbral sobre el contador actual castigaría el
  `/100` del porcentaje igual que el 20 fabricado. Separar convención de premisa es DISEÑO previo
  a cualquier barrido, y va declarado como tal.

## 5. La consecuencia del 70 %, medida en las respuestas reales

**La distribución de veredictos por tipo, de las trazas que ya había** (974 afirmaciones; las
`sin_verificar` son la era anterior a enchufar cada verificador y se cuentan aparte). Paráfrasis
juzgadas (n=175, TODAS bajo los umbrales viejos 0,80/0,20):

| veredicto | antes (0,80/0,20) | re-veredictado (0,60/0,30, de las probs persistidas) |
|---|---:|---:|
| verificada | 42 (24 %) | **55 (31 %)** |
| reintento_con_señal | 63 (36 %) | 41 (23 %) |
| no_verificable | 43 (25 %) | 56 (32 %) |
| podada | 27 (15 %) | 23 (13 %) |

**"Cero afirmaciones factuales sin verificar" es cierto y NO es lo mismo que "verificadas": solo
1 de cada 4 paráfrasis juzgadas salía verificada** — honesto pero flojo, como sospechaba el
propietario. La calibración lo sube a ~1 de 3 sin re-correr nada (re-veredicto offline de las 132
probabilidades persistidas; las 43 sin probabilidad nunca llegaron al modelo). En `literal` de la
era verificada: 189 verificadas, 31 degradadas, 17 no_verificable, 12 reintento, 1 podada.

**La causa raíz del 70 %, escrita porque explica el arreglo:** la hipótesis que se le da al NLI es
el `texto` de la afirmación, no su `cita`. Para una literal degradada, el texto es lo que lee el
alumno y la cita es lo copiado: la frase que CONTIENE la cita no tiene por qué ser la de mayor
solape con el texto — **la selección está buscando en el sitio equivocado**. Medido el techo de
cada arreglo sobre los 189 positivos: la selección actual acierta 56; **el arreglo barato (sesgar
hacia la frase que contiene la cita, que se conoce exacta) alcanza 37 más**; y **96 citas CRUZAN
frases** — solo la selección multi-frase las alcanza. El barato queda **declarado con su número y
no construido hoy**: exige enhebrar la `cita` hasta el verificador y re-elegir el plano sobre la
selección nueva, que es un cambio de diseño con su propio commit, no un retoque de paso.

**Y la prioridad que esto reordena, decidida por el propietario:** el 2.5 (traza completa) pasa
POR DELANTE del 5.3 — desbloquea dos de los seis umbrales de este inventario (§4) y además se
enseña en pantalla.

## 6. La limitación del instrumento, declarada por su autor

**Los 94 pares oro son 100 % DWES** (el propietario lo declara como limitación suya: Programación
no tenía banco de preguntas y se prefirió un conjunto de una asignatura a uno con la mitad
cocinada). Todo lo que necesite **variación entre asignaturas** —en particular la normalización de
`confianza_recuperacion` por tamaño de partición, cuyo sesgo está medido desde el 3.3— **no tiene
datos y sale DECLARADO, no calibrado. No se cubre con una estimación: el instrumento no lo
permite.**

## 7. Los márgenes de `confianza_recuperacion` sobre DWES — criterio escrito ANTES de medir

La forma de la regla se conserva (margen top1−top6, coseno mínimo para `alta`); lo que se
re-deriva son sus números, sobre el conjunto corregido y con la elección pre-escrita: **`alta` = el
menor margen cuya precisión (oro en el contexto) supere la tasa base en ≥ 10 puntos con n ≥ 15;
`media` = el menor margen con precisión ≥ tasa base y n ≥ 15; el coseno mínimo de `alta` = el p25
de los top1 dentro del tramo alta.** Si ningún margen separa así, el desenlace es SIGUE SIN
CALIBRAR por falta de separación — no se fuerza. Todo sobre DWES, con la limitación del §6 delante.

**Y la tasa base, leída junto a su número viejo porque es la demostración que vale para el
lunes: 72 % con el conjunto roto → 60,6 % con el corregido.** La vara arreglada enseña que el
sistema era PEOR de lo que medíamos —coherente con el objetivo de la fase 3 declarado no
alcanzado—: **corregir el instrumento nos costó puntos en vez de regalárnoslos, que es lo
contrario de lo que pasa cuando alguien ajusta su propia vara.**

**Resultado del §7 (corrida 33, n=94, tasa base 60,6 %):** `alta` ≥ **0,085** (n=46, precisión
**71,7 %**, +11,1 puntos sobre la base), `media` ≥ **0,025**, coseno mínimo de alta **0,664** (p25
del tramo). El alta inicial del 3.3 (0,08 / 0,66) estaba notablemente bien puesto a ojo; el media
baja de 0,05 a 0,025. Cableado en `recuperacion.py` con la limitación DWES escrita encima: esto
calibra los márgenes EN DWES; la normalización por partición queda declarada (§6). Con esto, **el
inventario del §0 no tiene ningún "pendiente": 3 calibrados (corridas 32 y 33) y 3 SIGUE SIN
CALIBRAR con su porqué y su desbloqueo (§4), que era la condición de cierre del encargo.**

## 8. La tarde: el ancla de la cita, y lo que la re-calibración destapó (ADR 0020 v2)

El propietario decidió el orden —el arreglo barato ANTES del 2.5, y después re-calibrar sobre el
instrumento arreglado— y la ejecución cazó dos instrumentos mintiendo por el camino:

1. **El ancla construida** (`seleccionar_frase(..., cita=)`): toda `literal` degradada lleva su
   cita hasta la selección; el veredicto dice `por_cita`/`por_cobertura` para que la traza pueda
   contarlo. Tests en las tres direcciones (ancla, sin cita, cita que cruza frases).
2. **La corrida 34 salió sospechosa** (el ancla "recuperaba" 3 cuando el techo medido eran 37) y
   la sospecha tenía razón dos veces: el contador comprobaba la cita sobre la frase **recortada a
   200 caracteres** (corrida 35, arreglado), y **39 positivos estaban rotos en origen:
   `afirmaciones.texto = 'literal'`** — el generador emitió el TIPO como texto (ids 393-925, era
   13/08+). Un control cuya hipótesis es la palabra "literal" no mide nada: excluidos, declarados,
   y **el defecto del generador queda señalado como trabajo propio** (ni la validación de forma ni
   el 4.5 lo cazan hoy).
3. **Elección v2 (corrida 36, 150 positivos limpios): suelo 0,10, umbral 0,60** — 35 verificados,
   20 perdidos declarados, **0 negativos aprobados**. Con el ancla y el conjunto limpio el suelo
   baja de 0,30 a 0,10: el negativo que antes se colaba estaba emparejado a una fila rota. La
   selección sigue fallando en 91 de 150 (61 %): citas que CRUZAN frases — multi-frase, declarada
   y no construida, sigue siendo la palanca gorda.

## 9. La ventana anclada: el 61 % era el partidor, y el plano v3 (corridas 37-39, ADR 0020 v3)

La solución estructural la diseñó el propietario: la premisa deja de salir de la partición de
`frases_de` —que parte por `\n+` y descarta fuera de (40, 400), o sea que en markdown BORRA
candidatas— y pasa a ser una **ventana de fragmento crudo anclada en el span** de la cita (o del
`apoyo` nuevo del contrato, comprobado como subcadena literal: infabricable). Por el camino, el
tercer instrumento mintiendo del día, **cazado mirando a ojo los 12 positivos que no anclaban en
la corrida 37**:

1. **El conjunto de control estaba contaminado, y llevaba así desde la corrida 32**:
   `veredicto = 'verificada'` lo escriben DOS verificadores con el mismo valor, y 12 "positivos"
   eran degradadas verificadas por el propio NLI — garantía circular, cita ausente del fragmento
   por construcción. La consulta exige ahora la firma del 4.2 (`detalle.verificacion.nivel IS NOT
   NULL`). Una etiqueta describe cómo se clasificó algo, no lo que contiene — esta vez la etiqueta
   era nuestra columna `veredicto`.
2. **Plano v3 (corrida 38, 138 positivos del 4.2 puro): suelo 0,25, umbral 0,60** — **138/138
   anclan por ventana, cero fallos de selección**, 77 verificados (56 %, contra 23 % en v2), 45
   perdidos por umbral declarados, 0 negativos. **El suelo re-derivado SUBE porque la premisa se
   volvió más rica: con 0,10, la ventana aprobaba un negativo.** El barrido conjunto pre-escrito
   es lo que lo cazó; el 0,60 sobrevivió a sus tres calibraciones.
3. **Distribución antes/después sobre filas reales (corrida 40)**: las **83 paráfrasis verificadas
   se conservan todas** y 45 pasan a `no_verificable` (41 de `reintento`, 4 de `podada`); las
   degradadas van de 60 a 55 verificadas, con 18 a `no_verificable`. Lo que baja a
   `no_verificable` es el régimen bajo el suelo nuevo — el mismo donde el plano midió que se
   colaba un negativo: honestidad, no pérdida. **La corrida 39 se repitió** porque su filtro de
   exclusión preguntaba por el caso mirado (`texto='literal'`) y no por la clase, y dejaba pasar 2
   filas rotas; el plano no se movía (138 con los dos filtros, contado antes de fiarse).

### El límite de la medida, dicho exacto: son DOS números y solo uno está medido

**La ventana solo ancla 2 de las 150 degradadas almacenadas, y eso no es un fallo suyo: es una
imposibilidad por definición.** Una afirmación `literal` se degrada **precisamente porque su cita
no casa** con el fragmento; la ventana ancla localizando la cita, así que sobre una degradada no
tiene dónde anclar salvo en el único caso que sí localiza —la reescritura que solo perdió tildes,
que son esas 2—. La ganancia de la ventana en servicio **no llega por las degradadas: llega por el
`apoyo` que las paráfrasis declaran**, y ese campo **nace hoy con este encargo**, así que ninguna
fila almacenada lo lleva. **No se puede medir sobre datos viejos, y por eso se declara en vez de
estimarse** (la misma regla que la limitación DWES del §6: si el instrumento no lo permite, se
escribe que no lo permite).

De ahí que sean **dos números distintos y haya que citarlos por separado**:

| número | qué mide | estado |
|---|---|---|
| **56 %** (77 de 138) | positivos **de control** verificados con la ventana, corrida 38 | **MEDIDO hoy**, sobre controles construidos (cita literal / fragmento ajeno) |
| tasa de verificación **en servicio** | qué fracción de paráfrasis reales verifica la ventana vía `apoyo` | **NO MEDIDO**: requiere generaciones nuevas que traigan el campo; se mide cuando existan |

**El 56 % es el número de los controles y no el de servicio**, y leerlo como el segundo sería
propagar una cifra de otra configuración — el error viajando en el sumando, esta vez desde el
denominador.

Y el recuento real de filas rotas del generador es **152 de 974 (15,6 %)**, no 39: 147 con
`texto='literal'` y 5 con `texto='parafrasis'`, todas del 13/08. Las 39 del §8 eran solo las que
caían dentro de los positivos del control — **el tamaño de un defecto medido sobre la muestra donde
se tropezó es una cota inferior, no el defecto**. El detalle, incluidos los denominadores publicados
que lo incluyen (las 906 afirmaciones factuales llevan estas 152 dentro, el 16,8 %), va en
`corpus/COBERTURA.md`; y el arreglo —rechazo en el contrato con reintento— queda como el pendiente
más gordo después del 2.5.
