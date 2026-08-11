# Cobertura del corpus por titulación y módulo (v3, 11 ago 2026)

Regla de lectura: **densidad "completa" significa curado para evaluación** (pares oro, conjuntos de casos), no cantidad de material. Solo las dos asignaturas de DAW son "completa". El resto de módulos tienen material de ciclo entero pero sin curar: densidad "parcial". Los módulos marcados TRANSVERSAL se cargan UNA sola vez y se mapean a varias titulaciones mediante la tabla puente `titulacion_asignaturas` (el propio Anexo II del RD los marca como transversales: no es un atajo, es fiel al título oficial).

## DAW (Técnico Superior en Desarrollo de Aplicaciones Web, RD 686/2010)

| Módulo (código BOE) | Curso | Fuente en el corpus | Estado |
|---|---|---|---|
| 0483 Sistemas informáticos | 1 | daw/curso1/sistemas-informaticos/comesana | parcial (Comesaña 2012) |
| 0484 Bases de datos | 1 | daw/curso1/bases-de-datos/comesana | parcial (Comesaña 2012) |
| 0485 Programación | 1 | daw/curso1/programacion/lionel-ict | **COMPLETA (curada, moderna)** |
| 0373 Lenguajes de marcas | 1 | daw/curso1/lenguajes-de-marcas/comesana | parcial. TRANSVERSAL (DAW, DAM, ASIR) |
| 0487 Entornos de desarrollo | 1 | daw/curso1/entornos-de-desarrollo/comesana | parcial (Comesaña 2012) |
| 0617 FOL | 1 | daw/curso1/fol/comesana | parcial. Material sirve a DAM y ASIR por transversalidad de contenido |
| 0612 Desarrollo web en entorno cliente | 2 | daw/curso2/desarrollo-web-entorno-cliente/comesana | parcial (Comesaña 2012) |
| 0613 Desarrollo web en entorno servidor | 2 | daw/curso2/desarrollo-web-entorno-servidor/joseluisgs-00..05 | **COMPLETA (curada, 2025-2026)** |
| (0613, versión antigua) | 2 | daw/curso2/desarrollo-web-entorno-servidor-antiguo/comesana-dwes | **PLANTADA** (par contradictorio real, `plantado: true`) |
| 0614 Despliegue de aplicaciones web | 2 | daw/curso2/despliegue-de-aplicaciones-web/comesana | parcial (Comesaña 2012) |
| 0615 Diseño de interfaces web | 2 | daw/curso2/diseno-de-interfaces-web/comesana | parcial (Comesaña 2012) |
| 0618 Empresa e iniciativa emprendedora | 2 | daw/curso2/empresa-e-iniciativa-emprendedora/comesana | parcial |
| 0616 Proyecto | 2 | sin material (módulo de proyecto, sin temario editorial) | hueco declarado |
| 0619 FCT | 2 | no aplica (formación en centros de trabajo) | no aplica |

Nota deliberada: el módulo 0485 Programación NO lleva la versión antigua de Comesaña. Motivo: las contradicciones del corpus deben estar plantadas y etiquetadas (encargos 1.7 y 1.8), no repartidas sin control. El único par de épocas conviviendo es el de DWES, que está etiquetado.

## DAM (Técnico Superior en Desarrollo de Aplicaciones Multiplataforma, RD 450/2010)

Primer curso: comparte con DAW los módulos 0483, 0484, 0485, 0373 y 0487 (mismos códigos en el título oficial). Se cargan UNA vez bajo DAW y se mapean a DAM por la tabla puente. FOL por transversalidad de contenido.

| Módulo 2º curso | Fuente en el corpus | Estado |
|---|---|---|
| 0486 Acceso a datos | dam/apuntes/temario-dam-comesana/AD | parcial (Comesaña) |
| 0488 Desarrollo de interfaces | dam/apuntes/temario-dam-comesana/DI | parcial (Comesaña) |
| 0489 Programación multimedia y dispositivos móviles | sin material en la fuente | **hueco declarado** |
| 0490 Programación de servicios y procesos | dam/apuntes/temario-dam-comesana/PSP | parcial (Comesaña) |
| 0491 Sistemas de gestión empresarial | dam/apuntes/temario-dam-comesana/SGE | parcial (Comesaña) |
| EIE | material transversal (daw/curso2/eie) | por puente de contenido |
| Proyecto / FCT | sin material / no aplica | hueco declarado / no aplica |

(Los códigos de FOL, EIE, Proyecto y FCT propios de DAM se verifican contra el PDF del RD 450/2010 cuando entre en `dam/normativa/`.)

## ASIR (Técnico Superior en Administración de Sistemas Informáticos en Red, RD 1629/2009)

| Módulo | Fuente en el corpus | Estado |
|---|---|---|
| 0369 Implantación de sistemas operativos | asir/apuntes/lora-1asir/SO y asir/apuntes/aberlanas-iso (UD01..UD12, CC BY-SA) | parcial, DOS fuentes |
| 0370 Planificación y administración de redes | asir/apuntes/lora-1asir/Redes | parcial |
| 0371 Fundamentos de hardware | asir/apuntes/lora-1asir/HW | parcial |
| 0372 Gestión de bases de datos | asir/apuntes/lora-1asir/BBDD | parcial |
| 0373 Lenguajes de marcas | TRANSVERSAL: daw/curso1/lenguajes-de-marcas | por puente |
| 0374 Administración de sistemas operativos | asir/apuntes/lora-2asir/ASO | parcial |
| 0375 Servicios de red e internet | asir/apuntes/lora-2asir/SRI | parcial |
| 0376 Implantación de aplicaciones web | asir/apuntes/lora-2asir/IAW | parcial |
| 0377 Administración de sistemas gestores de BBDD | asir/apuntes/lora-2asir/BBDD | parcial |
| 0378 Seguridad y alta disponibilidad | asir/apuntes/lora-2asir/SAD | parcial |
| 0379 Proyecto | asir/apuntes/lora-2asir/Proyecto.md | testimonial |
| 0380 FOL | asir/apuntes/lora-1asir/FOL (+ transversal daw/fol) | parcial |
| 0381 EIE | asir/apuntes/lora-2asir/"Empresa e iniciativa emprendedora" | parcial |

(Códigos a confirmar contra el PDF del RD 1629/2009 cuando entre en `asir/normativa/`. El material suelto de lora-2asir sobre Git, Openstack, OVH y Docusaurus queda como complementario de HLC/proyecto.)

## Resumen honesto

Tres titulaciones con material de ciclo prácticamente entero: DAW con sus 12 módulos lectivos cubiertos (2 curados, 9 parciales, 1 hueco de proyecto), DAM con 1º entero por transversales y 4 de 5 módulos propios de 2º (hueco: PMDM 0489), ASIR con los 13 módulos cubiertos por alguna fuente. Los huecos están declarados aquí, no escondidos: un mapa con dos huecos escritos vale más que un "completo" que no lo es.
