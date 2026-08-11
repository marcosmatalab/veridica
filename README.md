# Veridica

Un profesor por asignatura sobre temario real que solo afirma lo que puede sostener: cita literal
comprobada carácter a carácter, paráfrasis verificada contra el fragmento fuente, cálculo recalculado
y silencio honesto cuando la respuesta no está en el material. La tesis del proyecto: **la honestidad
del sistema no depende de la brillantez del modelo, depende de la capa de verificación.**

> **README provisional.** El README definitivo, con los números medidos, la configuración elegida y
> la sección "Escala", lo produce el **encargo 8.3**. Hasta entonces este fichero solo declara el
> estado real del repo. Nada de lo que aquí no aparezca como construido lo está.

## Estado (11 de agosto de 2026)

**Fase 0 en curso, encargo 0.1.** No hay servicio, ni tubería de ingesta, ni verificación, ni
métricas. Lo único que existe hoy:

| Qué | Dónde | Estado |
|---|---|---|
| Playbook y fuente de verdad | [guia-definitiva.md](guia-definitiva.md) | escrito |
| Reglas de trabajo | [CLAUDE.md](CLAUDE.md) | escritas |
| Corpus de las tres titulaciones (DAW, DAM, ASIR) | `corpus/` (fuera de git) | descargado y en manifiesto |
| Manifiesto del corpus | [corpus/manifiesto.jsonl](corpus/manifiesto.jsonl) | 2.097 entradas, verificador en verde |
| Mapa de cobertura por módulo | [corpus/COBERTURA.md](corpus/COBERTURA.md) | escrito, con sus huecos declarados |
| Estructura de carpetas del proyecto | árbol del repo | vacía, esperando su fase |

Todo lo demás —API, recuperación, generación tipada, verificadores, arnés de evaluación, tabla de
configuraciones y despliegue— está **diseñado en la guía y no construido**. El orden de construcción
es el de la Parte IV de la guía y no se salta.

## Cómo se trabaja aquí

Por encargos numerados (0.1, 0.2, 1.1...), en orden, cada uno con su verificación y su criterio de
cierre. Una fase, una rama. Las reglas completas están en [CLAUDE.md](CLAUDE.md).

## Corpus y licencias

El corpus **no se versiona en git** (`corpus/` está en `.gitignore`; solo entran el manifiesto y el
mapa de cobertura). Cada documento lleva en `corpus/manifiesto.jsonl` su ruta, fuente, licencia,
versión de corpus, hash SHA-256, densidad y marca de plantado: **sin entrada en el manifiesto no
entra en el corpus.** La normativa del BOE es dominio público; los apuntes públicos conservan su
licencia y su atribución; los repos de apuntes sin licencia declarada están registrados como
"sin licencia declarada, uso local, no redistribuible" y no salen de la máquina local.

## Verificación del corpus

```bash
python scripts/verificar_manifiesto.py   # cruza disco contra manifiesto en las dos direcciones
```
