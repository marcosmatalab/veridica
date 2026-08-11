# ADR 0005: la unidad del fragmento sale de la carpeta del material, no del árbol del BOE

- **Fecha:** 11 de agosto de 2026
- **Encargo:** 1.4 (decidido antes de empezarlo)
- **Estado:** aceptada

## Contexto

El encargo 1.1 dejó el árbol oficial extraído del BOE con 536 nodos, y hasta unidades. El encargo
1.4 tiene que etiquetar cada fragmento con su sitio en el árbol: titulación, curso, asignatura,
unidad. Parecía inmediato usar la unidad del BOE. No lo es.

**Son dos taxonomías distintas que describen la misma materia.** El profesor organiza su material en
`Unidad 4 Introducción a Java`; el BOE llama a esa materia `Utilización de objetos`. No es un
problema de nombres parecidos con otra puntuación: son cortes distintos del temario, hechos por
gente distinta con propósitos distintos (uno para dar clase, otro para normar el título). Un mismo
bloque de contenidos del BOE puede repartirse entre tres unidades del profesor, y una unidad suya
puede tocar dos bloques.

Emparejarlas automáticamente exigiría similitud semántica entre títulos, con umbral, y ese umbral no
se puede validar sin pares oro de esa correspondencia, que no existen. Sería una capa de adivinación
en la etiqueta que después alimenta el filtro de recuperación.

## Decisión

1. **La partición y el filtro van por ASIGNATURA**, que sí casa bien entre las dos taxonomías: el
   código de módulo (0485, 0613...) es el mismo en el BOE y en la organización del material.
2. **La `unidad` de un fragmento sale de la carpeta del material** de la que viene, y se declara
   como lo que es: la unidad del profesor, no la del BOE.
3. **El árbol oficial se queda donde vale**: referencia normativa para el selector del alumno
   (titulación, curso, asignatura) y para el guiado del recorrido y la proactividad del encargo 5.4.
   No etiqueta fragmentos.
4. **Cruzar ambas taxonomías es trabajo aparte**, y hasta que exista se declara como no construido.

## Trade-off

Se pierde: no se puede responder "enséñame lo que el BOE llama *Utilización de objetos*" filtrando
fragmentos, porque ningún fragmento lleva esa etiqueta. La proactividad del 5.4 propondrá el
siguiente paso desde el árbol oficial, pero el material que lo sostiene se recupera por asignatura,
no por unidad normativa.

Se gana: ninguna etiqueta del corpus es una suposición. El filtro que decide qué puede tocar una
consulta —el que sostiene el argumento de partición y de contaminación cruzada— se apoya en el único
nivel donde las dos taxonomías coinciden de verdad.

Y hay una consecuencia que no es menor: **el argumento de escala de la Parte V no se toca**. La clave
de partición siempre fue la asignatura, no la unidad.

## Por qué no se intenta el mapeo ahora

Porque sería un detector sin caso donde validarlo (principio 3): no hay pares oro
unidad-del-profesor ↔ bloque-del-BOE, así que su acierto no se podría medir, solo suponer. Y porque
un error ahí no falla en voz alta: etiqueta mal un fragmento, el filtro lo esconde o lo trae de más,
y eso se manifiesta semanas después como "el recall está flojo" sin que nadie sepa por qué.

Si algún día hace falta, el camino honesto está escrito: construir primero los pares oro de
correspondencia a mano sobre una asignatura, medir el acierto de la propuesta automática contra
ellos, y solo entonces adoptarla, con su ADR y su número.
