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
| 3 | `SOLAPE_MINIMO` (portero de frases) | 0,50 | 4.5 | **pendiente** |
| 4 | márgenes de `confianza_recuperacion` (alta/media/baja) | 0,08 / 0,05 / coseno 0,66 | 3.3, declarado sin calibrar | **pendiente** |
| 5 | vigilante de ritmo | 35 tok/s, ventana 2 s | 3.4bis, declarado sin calibrar | **pendiente** |
| 6 | anclaje de operandos (`operandos_sin_fuente`) | sin umbral: contador | nace el 14/08 sin calibrar | **pendiente** |

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
