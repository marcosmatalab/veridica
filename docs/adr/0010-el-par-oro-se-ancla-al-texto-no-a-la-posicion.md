# ADR 0010: el par oro se ancla al texto, no a la posición, y su puerta no repara

- **Fecha:** 12 de agosto de 2026
- **Encargo:** 3.0 (pares oro)
- **Estado:** aceptada

## Contexto

Los 100 pares de `evals/casos/oro_recuperacion.jsonl` llegaron apuntando a su fragmento por
`(documento, orden)`. `orden` es **posicional dentro del documento**: lo asigna el troceado, y el
troceado ya ha cambiado tres veces durante los arreglos del corpus de la fase 1.

El fallo que esto habilita no es una excepción ni un rojo. Si el corpus se vuelve a trocear, cada
par sigue apuntando a *algo* —el fragmento número 4 de ese documento existirá igual— solo que a otro
texto. Nada se rompe: `recall@6` simplemente empieza a medir si la recuperación encuentra un párrafo
que nadie eligió, y sale un número con el mismo aspecto que el bueno. Es exactamente la avería del
verificador de solo rutas que arregló el encargo 1.0, repetida en el conjunto de evaluación, y aquí
duele más, porque en el 1.0 el fichero corrupto se notaba al leerlo y aquí lo único que se degrada
es la confianza en una métrica.

Además, el índice contra el que se comprueba (`corpus/fragmentos.jsonl`) **no está en git**: vive
bajo `corpus/`, que la fase 0 dejó fuera por tamaño y licencias (ADR 0001). El runner de CI no lo
tiene.

## Decisión

**1. Cada par lleva el SHA-256 del texto del fragmento que se etiquetó** (`fragmento_oro.hash_texto`),
y `scripts/verificar_oro.py` lo compara **además** de la posición, con clase de hallazgo propia:
`DESPLAZADO`, "el fragmento existe pero ya no es el que se etiquetó". Sin ella, la puerta comprobaría
que hay algo ahí, no que sea lo que se leyó al etiquetar.

El hash se calculó sobre el texto crudo, sin normalizar, y eso es deliberado: un cambio de
normalización SÍ debe disparar la puerta, porque el fragmento que la persona leyó ya no es el que
leería hoy. Se prefiere una alarma que obliga a releer 100 pares a un silencio que no obliga a nada.

**2. El verificador no repara.** Re-anclar un par desplazado es volver a leer el fragmento y decidir
si todavía responde la pregunta, que es trabajo de persona y no de un script. Un verificador capaz de
reescribir el fichero que verifica puede ponerse verde solo, y entonces no verifica: es la misma
familia que la mutación que no se aplica y que el verde de la tubería, el instrumento mintiendo en
vez de lo medido. Por eso el anclaje inicial se hizo con un script de un solo uso, fuera del repo, y
lo que queda dentro solo sabe decir que no cuadra.

**3. La puerta es local, no de CI**, por el mismo motivo y con el mismo trade-off que el ADR 0001:
sin corpus en el runner no hay nada que cruzar. Y para que la ausencia del corpus no se disfrace de
otra cosa, `verificar_oro.py` distingue los códigos de salida: `1` es "los pares oro están mal",
`2` es "no he podido leer el índice". Confundirlos convertiría la falta de corpus en un hallazgo de
integridad, o —peor— al revés.

**4. Lo que cubre el CI es la capa de juguete.** `tests/test_verificar_oro.py` monta un índice y unos
casos inventados en un directorio temporal y ahí sí demuestra, en el runner, que el verificador se
pone rojo con un par inexistente, con un par desplazado a un fragmento **que existe y está admitido**,
con un oro salido de `practicas/`, con un documento que tira la puerta del 1.4 y con un fragmento que
la tira. Los pares reales se comprueban en la capa anclada, que se salta sin corpus.

**5. La puerta del 1.4 se importa de `admitir.py`, no se reimplanta.** Una copia de las reglas de
admisión dentro del verificador daría verde el día que cambien en su sitio. El principio 6 dice que
el que comprueba no comparte el supuesto del que produce; su reverso también hace daño, y es que el
que comprueba diverja en silencio de lo que produce.

## Trade-off

Lo que se pierde: el `hash_texto` es rígido a propósito, así que cualquier re-troceado o cambio de
normalización pondrá los 100 pares en rojo a la vez, aunque 95 de ellos sigan siendo correctos. Eso
es caro: obliga a una pasada de relectura en vez de a un `sed`. Y como la puerta no repara, no hay
atajo automático para esa pasada.

Lo que se gana: es imposible que la fase 3 mida contra un conjunto oro desalineado sin que alguien lo
sepa. Los números del 3.5 valen lo que vale su verdad de referencia, y un conjunto oro desplazado no
degrada la medida, la sustituye por otra con el mismo aspecto.

Se acepta el coste porque la alternativa —anclar solo por posición, o normalizar el texto antes de
hashear para que "cambios pequeños" no molesten— compra comodidad justo en el sitio donde no se puede
pagar con confianza: la vara de medir.

## Cuándo se revisa

Si el troceado se estabiliza y se versiona (un `version_troceado` en el índice, comparable de un
vistazo), el hash por par pasa a ser redundante con esa versión y esta decisión se puede simplificar.
Y si el corpus llega a ser publicable, la puerta se va al CI con el ADR 0001 y este se actualiza
detrás.
