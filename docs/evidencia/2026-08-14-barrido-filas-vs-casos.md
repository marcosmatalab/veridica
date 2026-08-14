# Barrido: todos los números del 14/08 recontados en las dos unidades, ORDENADOS POR DÓNDE SE LEEN

- **Fecha:** 14 de agosto de 2026, noche
- **Encargo:** resto de la pasada adversarial abierta al descubrir que los titulares del día
  contaban **filas** de `afirmaciones` creyendo contar **casos** ([conteo.py](../../app/core/conteo.py))
- **Método:** ningún modelo se vuelve a correr. Cada corrida persiste su detalle **por par** en
  `corridas_eval`, así que el recuento sale de lo ya medido. La clave es la misma que usan los
  instrumentos arreglados: **fragmento + texto de la afirmación**.
- **Puerta previa, aplicada a cada fila de este documento:** *al recomputar un número publicado, lo
  primero es reproducirlo*. Donde la cifra vieja **no** se reproduce, no se publica corrección: se
  dice que no se reproduce. Van **dos** casos así (§5 y §9) y están marcados.

## 0. La magnitud que infla todo, medida

El arnés repite las mismas preguntas a propósito —así se mide la dispersión— y **cada repetición
vuelve a escribir las mismas afirmaciones**:

```
consultas     523 filas / 108 textos de pregunta distintos   (x4,84)
afirmaciones  1.314 filas / 690 casos distintos              (x1,90)
la más repetida: una sola pregunta, 25 veces
```

**Ningún número calculado sobre esas tablas escapa a esto.** Lo que sigue es qué le hace a cada uno.

**Las dos causas se dan siempre separadas y nunca se suman:**

- **UNIDAD** — mismo conjunto, dos formas de contarlo (filas → casos distintos).
- **POBLACIÓN** — misma unidad, dos conjuntos (la base creció, o son dos corridas).

---

## 1. `README.md`

| lo que dice | unidad | recontado | ¿sobrevive? |
|---|---|---|---|
| «los fallos de selección pasan de **91 de 150** a **0 de 138**» | filas | **33 de 68** → **0 de 58** | **sí**, y el cero es cero en las dos unidades |
| «**152 filas, el 15,6 %** de la tabla» | filas, **y lo dice** | **41 casos**, 9,1 % | **sí**: declara su unidad, que era el problema |
| «cero cortes sobre **30 consultas sanas**, cuyo peor momento va de **110 a 158** tok/s» | filas ≡ casos | ver §6: **con las dos corridas el peor momento es 84,5** | **la conclusión sí, el número no** |
| «al 0,50 ya se marcan **10-12 de 23** frases legítimas» | casos (frases distintas) | 23 marcadas son 23 frases distintas | **sí** |
| «**2 de 22** identidades → **0 de 22**», «**49 % a 76 %**» | casos | ya recontado el 14/08 | **sí** |
| recall/nDCG de la fase 3 | 94 pares oro, **una fila por par** | inmune por construcción | **sí** |

## 2. `corpus/COBERTURA.md` — el defecto del generador

Reproducido dígito a dígito antes de recontar (152/974 y 152/906).

| | filas | **casos distintos** |
|---|---:|---:|
| tabla entera | 974 | **452** (×2,15) |
| factuales (sin `andamiaje`) | 906 | **395** (×2,29) |
| **rotas del generador** | **152 = 15,6 %** | **41 = 9,1 %** |
| … sobre las factuales | 152 = 16,8 % | **41 = 10,4 %** |

- **UNIDAD:** 15,6 % → **9,1 %**. Las rotas se repiten **más** que la media (×3,71 contra ×2,15),
  o sea que el defecto está **concentrado**: 41 afirmaciones distintas escritas 152 veces.
- **POBLACIÓN:** la base es hoy 1.314 filas / 690 casos, así que las mismas 152 filas son ya el
  **11,6 %** en filas y el **5,9 %** en casos.
- **El titular no cambia y el arreglo tampoco** —la gramática cierra la clase entera—, pero
  *«el 15,6 % de la tabla»* describe **cuánto pesa en la tabla**, no **cuántas afirmaciones
  distintas rompió el generador**, y son dos preguntas.

## 3. `calibracion-4.6.md` §3, §8, §9 y `ADR 0020` — los tres planos

Los tres reproducen su cifra publicada exactamente.

| plano | positivos | **casos** | lo publicado | **en casos** |
|---|---:|---:|---|---|
| §3 corrida 32 (v1) | 189 | **81** (×2,33) | 133 (70 %) fallan por selección; n del tramo 56 | **49 de 81 (60,5 %)**; n del tramo **33** |
| §8 corrida 36 (v2) | 150 | **68** (×2,21) | 91 de 150 (61 %) no anclan | **33 de 68 (48,5 %)** |
| §9 corrida 38 (v3) | 138 | **58** (×2,38) | **138/138 anclan**; 77 verificados (56 %) | **58/58 anclan**; **34 de 58 (59 %)** |

- **Los tres hallazgos estructurales sobreviven**, y el más importante **mejora**: *«138 de 138
  anclan»* es **58 de 58** en casos distintos — un 100 % no se diluye al deduplicar.
- **La tasa de verificación del plano v3 sube al deduplicar** (56 % → 59 %), al revés que el número
  de cabecera. Aquí la repetición pesaba hacia los positivos **difíciles**.
- **La caída de fallos de selección 61 % → 0 % sigue siendo la misma historia** en casos: 48,5 % → 0 %.

### Y una corrección a MI PROPIO recuento, porque casi regala un verde

La primera versión de este barrido dedujo los **negativos** por `(fragmento propio, texto)` — la
misma clave que los positivos. **Está mal.** Un negativo es la afirmación contra un fragmento
**ajeno**, y el emparejado es determinista por índice, así que dos filas de la misma afirmación
llevan ajenos **distintos**: son dos pares de control distintos. Con la clave equivocada, 158
negativos colapsaban a 74 y **el único negativo aprobado desaparecía del recuento**. Con la clave
correcta —`(fragmento AJENO, texto)`— son **146** y el negativo **sigue ahí**.

Es la regla del filtro escrito sobre el ejemplo, cometida dentro de la herramienta de auditar: el
deduplicador no falla, **devuelve otra cosa**, y lo que devuelve tiene mejor pinta.

## 4. `ADR 0022` y `el-juez-es-el-techo.md` §5-§6 — la tabla que decidió el cambio de juez

Comparación **pareada** correcta: corrida **47** (juez viejo) contra **46** y **48** (juez nuevo),
sobre los **mismos 158 pares**, suelo 0,25.

| configuración | filas | **casos** | negativos aprobados |
|---|---:|---:|---:|
| juez viejo, ventana estrecha (47, a 0,90) | 53/158 | **36/74 (49 %)** | 0 de 146 |
| juez nuevo, ventana estrecha (46) | 112/158 (71 %) | **52/74 (70 %)** | **1** de 146 |
| **juez nuevo, ventana ampliada (48)** | 119/158 (75 %) | **56/74 (76 %)** | **1** de 146 |

**Coincide con lo que el ADR 0022 ya publicó esta tarde, y ahora con los negativos contados por su
clave correcta: el negativo aprobado es 1 en las dos unidades.** La decisión se refuerza: +27 puntos
en casos distintos y 0 fallos de identidad contra 2.

**Lo que este barrido añade:** *«dispara en 32 de 158 (20 %)»* de la ampliación de ventana es
**18 de 74 (24,3 %)** en casos — el único número del día que **sube** al deduplicar, porque los
deícticos huérfanos no son lo que más se repite.

## 5. `el-juez-es-el-techo.md` §1 — NO SE REPRODUCE, y por eso no se re-numera

§1 publica *«60 pares con la hipótesis literal en la premisa, 12 neutral (20 %), mediana 0,66,
mínimo 0,545, 45 de 60 aprobados»*. **Reconstruido hoy con `premisa_para` y el filtro de código del
servicio salen 63 pares, 11 neutral y 49 aprobados** — el mínimo coincide dígito a dígito (0,5451) y
el resto no. No hay filtro que devuelva 60.

**Así que aquí no se publica corrección.** Se marca la sección como **superada por el ADR 0022**,
que es donde el recuento sí se hizo sobre una población reproducible. Lo que sí se puede decir sin
reproducir nada, porque vale para cualquiera de las dos poblaciones: **el factor de repetición de
ese conjunto es ×3,7 y la mediana pasa de 0,67 en filas a 0,90 en casos**, que es exactamente la
corrección ya escrita. Y el *«un tercio de la pérdida es el modelo fallando en A ⊆ A»* (18 de 61)
es, en casos, **4 de 24: un sexto**.

## 6. `portero-y-ritmo-calibrados.md` — DOS CORRIDAS MEZCLADAS, y el techo se rompe

**Este es el hallazgo del barrido, y no es de filas contra casos.** Las corridas 41 y 42 son **dos
pasadas independientes de las mismas ~58 preguntas**, con **cero respuestas compartidas** (120
consultas en total). El documento publica **la tabla de la 41** y **lee los casos de la 42**.

| umbral | 41 (la publicada) | 42 (la leída) | **las dos juntas** |
|---:|---:|---:|---:|
| 0,50 | 18/153 = 11,8 % | 23/165 = 13,9 % | **41/318 = 12,9 %** |
| 0,60 | 29/153 = 19,0 % | 32/165 = 19,4 % | **61/318 = 19,2 %** |
| **0,70** | **38/153 = 24,8 %** | **51/165 = 30,9 %** | **89/318 = 28,0 %** |
| 0,75 | 42/153 = 27,5 % | 55/165 = 33,3 % | 97/318 = 30,5 % |

**El desempate pre-escrito decía: entre los umbrales que no marcan más del 25 %, gana el más alto.**
Con la tabla publicada, el 0,70 aterrizaba en **0,2484 contra el techo de 0,25** y el documento
escribió que *«eligió por el techo y no por el dato»*. **Con las dos corridas delante el 0,70 marca
el 28,0 % y queda DESCALIFICADO por el techo, sin discusión.**

- **La decisión no cambia: el portero se queda en 0,50.**
- **El porqué publicado sí cambia, y es la tercera explicación elegante que se cae hoy.** *«Aterrizó
  a un pelo del techo»* era un artefacto de haber publicado **la menor de dos corridas**; y la
  lectura de los 28 casos —que es lo que de verdad sostuvo la decisión— sigue valiendo entera.
- **La unidad, por si acaso: aquí filas ≈ casos** (191 frases → 184 textos distintos, ×1,04), porque
  el modelo no repite prosa palabra por palabra aunque la pregunta se repita. **Lo que está
  desequilibrado no es la unidad, es la muestra:** esas frases salen de preguntas repetidas ×3,24.

### El ritmo: la conclusión aguanta, el número publicado no

| | n | mín | p25 | mediana | máx | bajo 35 | margen sobre 35 |
|---|---:|---:|---:|---:|---:|---:|---:|
| corrida 41 (**publicada**) | 30 | **110,0** | 128,0 | 139,8 | 158,5 | 0 | ×3,14 |
| corrida 42 | 29 | **84,5** | 141,5 | 148,0 | 158,0 | 0 | ×2,41 |
| **las dos** | **59** | **84,5** | 135,5 | 144,5 | 158,5 | **0** | **×2,41** |

- **VALIDADO en 35 sigue en pie**: cero cortes falsos sobre **59** consultas sanas, no 30.
- **«La más lenta va a 110» es falso**: va a **84,5**, y el margen medido es **×2,41**, no «factor 3».
- **La banda 35-50 sigue vacía** —el argumento que impidió mover el umbral— y ahora con el doble de
  observaciones, así que **el desempate anulado se queda anulado con más razón**.

## 7. `portero-marca.md` — lo que compró el cambio

**§2 reproduce exacto** (205 respuestas, 543 frases, 133 podadas, 86 afectadas, 32 en blanco):

| | filas | **casos (pregunta distinta)** |
|---|---:|---:|
| respuestas con portero | 205 | **46** (×4,46) |
| frases juzgadas | 543 | **114** |
| frases podadas | 133 = **24,5 %** | 27 = **23,7 %** |
| respuestas que perdían ≥1 frase | 86 = 42,0 % | **17 = 37,0 %** |
| **pantalla en blanco** | **32** | **8** |

- **La tasa de poda es robusta** (24,5 % → 23,7 %): es una tasa **por frase**, y las frases no se
  repiten. **El titular del ADR 0021 sobrevive intacto.**
- **«32 respuestas en blanco» son 8 preguntas distintas**, y las dos cifras dicen cosas distintas:
  32 es cuántas veces ocurrió, 8 es a cuántas preguntas les pasa. Para dimensionar el daño de
  producción vale la segunda.

**§1 reproduce exacto** (826 sanas, min 3 / p1 8 / p5 22 / p25 45 / mediana 75 / p95 217 / max 368):

| suelo | rechaza (filas) | **rechaza (casos)** |
|---:|---:|---:|
| **13** | 16 = 1,9 % | **7 de 414 = 1,7 %** |
| 20 | 40 = 4,8 % | **11 de 414 = 2,7 %** |

**La decisión sobrevive y su argumento no dependía de esto:** el 13 sale del nombre de tipo más
largo (`conocimiento`, 12 caracteres), no del porcentaje. Lo que se estrecha es el margen relativo
entre 13 y 20 (×2,5 en filas, ×1,6 en casos), o sea que **el argumento porcentual era el flojo y el
estructural era el bueno** — que es como se eligió.

## 8. `corregir-desde-resultado.md` §9 y §10

**§9 reproduce exacto** por afirmación (219/9, 296/8, 459/12):

| confianza | filas | **casos** |
|---|---:|---:|
| alta | 9/219 = **4,1 %** | **5/80 = 6,2 %** |
| media | 8/296 = 2,7 % | 6/117 = 5,1 % |
| baja | 12/459 = 2,6 % | **11/268 = 4,1 %** |

**El hallazgo sobrevive**: con confianza **alta** el modelo tira de `conocimiento` **más** que con
baja también en casos distintos (6,2 % contra 4,1 %). La magnitud sigue siendo incierta y ahora se
ve mejor por qué: **el numerador son 5 casos contra 11**. Y la tabla vieja *«por respuesta»*, que el
documento ya había retirado por confundido de longitud, **en casos se aplana del todo** (7,1 / 9,1 /
7,5 %): la retirada estaba bien hecha.

**§10 reproduce exacto** (74 `calculo` con expresión, 40 hallazgos = 54,1 %, 72 ocurrencias):

| | filas | **casos** |
|---|---:|---:|
| denominador | 74 | **21** (×3,52) |
| hallazgos (afirmaciones con algún operando sin fuente) | 40 = 54,1 % | **10 = 47,6 %** |
| ocurrencias de operando sin fuente | 72 | **18** |
| **familia `5 horas > 4.5 horas` (la premisa inventada)** | 14 afirmaciones / 15 operandos | **3 afirmaciones / 4 operandos** |

**Y aquí está la misma forma que el número de cabecera, en pequeño:** este documento **sí** separa
ocurrencias de hallazgos —*«40 afirmaciones, 72 ocurrencias»*— pero **un piso más abajo del que
importaba**: cuenta operandos por afirmación y no filas de afirmación por caso distinto. La regla
aplicada y saltada **en la misma tabla**.

**El desenlace del 4.6 se refuerza:** *«el anclaje de operandos SIGUE SIN CALIBRAR porque separar
convención de premisa es diseño antes que barrido»* — con **4 operandos de premisa en 3
afirmaciones distintas**, calibrar un umbral ahí sería ajustar al ruido con más ganas todavía.

---

## 9. Cierre: qué se cae, qué aguanta

**Se cae** (tres cosas, ninguna es una decisión):

1. *«El 0,70 del portero aterrizó a un pelo del techo»* — **rompe el techo (28,0 %)**; se publicó la
   menor de dos corridas. El 0,50 se queda igualmente.
2. *«La consulta sana más lenta va a 110 tok/s, factor 3 de margen»* — es **84,5** y **×2,41**.
3. *«Un tercio de la pérdida del NLI es el modelo fallando en A ⊆ A»* — es **un sexto**, y su
   sección no es reproducible, así que se marca como superada en vez de re-numerarse.

**Aguanta todo lo que decidió algo:** el suelo de longitud 13, el portero en 0,50, el ritmo en 35,
el cambio de juez, la ventana ampliada, `NIVEL_POR_DEFECTO = espacios`, los tres planos del NLI y el
`SIGUE SIN CALIBRAR` del anclaje de operandos. **Nueve decisiones, cero invertidas.**

**Y el patrón del día, que es lo que hay que llevarse:** el recuento por casos **no ha invertido ni
una decisión**, pero ha tumbado **cuatro explicaciones** (la mediana de las identidades, los dos
denominadores mezclados, el pelo del techo del portero y el factor 3 del ritmo). **Un número se
re-mide; una explicación se hereda** — por eso salen más caras.
