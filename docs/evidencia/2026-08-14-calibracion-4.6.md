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
| 1 | `entailment` del NLI | 0,80 | sección 8, declarado sin calibrar | **CALIBRADO: 0,60** (plano de la corrida 32, desempate pre-escrito; ADR 0020; §3) |
| 2 | `COBERTURA_MINIMA` (suelo de selección de frase) | 0,20 | 4.3 | **CALIBRADO: 0,30** (mismo plano, barrido CON el umbral; ADR 0020; §3) |
| 3 | `SOLAPE_MINIMO` (portero de frases) | 0,50 | 4.5 | **SIGUE SIN CALIBRAR** (§4: la prosa no se persiste — sin denominador no hay barrido; lo desbloquea el 2.5) |
| 4 | márgenes de `confianza_recuperacion` (alta/media/baja) | 0,08 / 0,05 / coseno 0,66 | 3.3, declarado sin calibrar | **CALIBRADO sobre DWES: 0,085 / 0,025 / 0,664** (corrida 33, criterio pre-escrito, §7); la normalización por partición sale **DECLARADA** — el instrumento no lo permite (§6) |
| 5 | vigilante de ritmo | 35 tok/s, ventana 2 s | 3.4bis, declarado sin calibrar | **SIGUE SIN CALIBRAR** (§4: n=2 averías observadas; el ritmo por consulta no se persiste; lo desbloquea el 2.5) |
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
