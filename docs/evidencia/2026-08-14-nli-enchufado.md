# El NLI, enchufado — 14 de agosto de 2026

El 4.3 dejó `app/core/verificador_nli.py` completo y probado. **No lo llamaba nadie.** Toda afirmación
`parafrasis` salía `sin_verificar`, y con ella una de las cuatro frases del README: *"paráfrasis
verificada contra el fragmento fuente"*.

```bash
python scripts/medir_veredictos.py "30 minutes"     # reparto de veredictos por tipo
python scripts/comparar_configuracion.py --vivo     # codigo vs compose vs contenedor
```

---

## 1. El efecto sobre los veredictos, que es la pregunta

Mismo lote de 20 consultas, cinco asignaturas, tres modos, secuenciales.

| tipo | antes (sin enchufar) | después |
|---|---|---|
| `literal` | verificada 7, **degradada 8** | verificada 21, reintento 3, no_verificable 3 |
| `parafrasis` | **sin_verificar 14 de 14** | **verificada 5, reintento 4, no_verificable 1** |
| `calculo` | verificada 5, no_verificable 1 | verificada 1 |
| **factuales sin verificar** | **17 de 38 (44,7 %)** | **0 de 38 (0,0 %)** |

**De 44,7 % de afirmaciones factuales sin verificar a 0 %.** Y no solo por las paráfrasis: las
`literal` **degradadas** —cuya cita no aparece letra a letra— llevaban desde el 4.2 saliendo con una
nota que decía *"ya lo verificará el NLI"*, y ahora lo verifica. Ese circuito estaba abierto.

`andamiaje` sigue `sin_verificar` y así debe ser: no es una afirmación factual.

## 2. Lo que cuesta, con una sola variable

Cuatro lotes de **20 consultas cada uno, a la misma hora**, cambiando **una** pieza cada vez:

| configuración | cortes a 5 s | p50 |
|---|---|---|
| local: embebedor + reordenador + **NLI** | 6/20 (30 %) | 3.962 ms |
| local: embebedor + reordenador, **sin NLI** | 6/20 (30 %) | 3.544 ms |
| local: embebedor + **NLI**, sin reordenador | 4/20 (20 %) | 3.534 ms |
| contenedor: **solo léxica** (sin torch) | 0/20 (0 %) | 2.274 ms |

**El NLI cuesta ~130 ms de media y CERO cortes.** El interruptor `NLI_ACTIVO=0` —que además es lo que
la ablación del 7.3 va a necesitar— permite medirlo sin cambiar de proceso, o sea sin mover más de
una variable a la vez.

### Y de paso corrige un número mío de ayer

Ayer reporté **11,5 % de cortes** como "el número de hoy". **Ese número era del contenedor**, o sea de
la configuración **solo léxica**, que recupera al 58 % de recall en vez del 80,9 %. La configuración
que va a correr el lunes —con vectorial y reordenador— corta el **30 %**.

Es la misma trampa de la muestra elegida por *cuándo*, una vuelta más: esta vez **elegida por la
configuración en la que era cómodo medir**. En una sesión de ocho preguntas, 30 % son dos o tres
cortes, no una.

**Dónde está el tiempo, con n=20 por celda (o sea con ruido):** el salto grande es
solo-léxica → vectorial completo (**+1,3 s de p50**); el reordenador aporta ~0,4 s y **2 cortes de 20**,
que a este tamaño de muestra no es una diferencia sólida. El NLI, nada.

## 3. Dos cosas que el enchufe obliga a declarar

**Una `literal` degradada recibe DOS veredictos**, y el bueno es el segundo: primero
`degradada_a_parafrasis` del 4.2, después el del NLI. No es ruido: es la cadena de verificación
enseñándose a sí misma, que es justo lo que el alumno tiene que poder ver. Con test.

**Y un veredicto `reintento_con_señal` NO puede reintentar.** La sección 8 manda que `neutral` dispare
el reintento único; **verificar en curso se lo come**, porque cuando el NLI contesta la prosa ya está
en pantalla y repetirla sería reescribirle al alumno lo que acaba de leer. El evento lo dice
(`reintento_disponible: false` con su motivo) para que la tasa de `neutral` del 4.6 no se lea como
*"se reintentó y siguió mal"*. Es el precio del solape, y en este lote son **7 afirmaciones de 38**.

## 4. El barrido de configuración, que sale del mismo hallazgo

`scripts/comparar_configuracion.py --vivo` compara **código, compose y contenedor** y marca las
diferencias. Primera pasada, un hallazgo real: **`VERSION_PROMPT` fijado en compose a
`2.2-eco-sin-recuperacion`**. Desde el 4.1 la versión sale del módulo que escribe el prompt, así que
ese valor solo actuaba como respaldo si alguien llamaba a la traza sin pasarla — y entonces estampaba
una etiqueta de dos encargos atrás en filas generadas con el prompt del 4.4. **No es un valor muerto:
es una etiqueta equivocada esperando un olvido.** Fuera de compose.

**Y el instrumento falló en su primera corrida:** imprimió `INFERENCIA_API_KEY` entera por pantalla.
Una herramienta de auditoría que enseña la clave es peor que no tenerla, porque se corre a menudo y su
salida se pega en informes. Arreglado: compara con el valor real y **imprime `(oculto)`** para todo
nombre que contenga `KEY`, `PASSWORD`, `SECRET`, `TOKEN` o `CLAVE`.
