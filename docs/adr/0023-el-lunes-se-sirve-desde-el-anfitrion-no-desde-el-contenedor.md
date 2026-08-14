# ADR 0023 — El lunes se sirve desde el ANFITRIÓN, no desde el contenedor

- **Fecha:** 14 de agosto de 2026
- **Encargo:** 8.4 (la sesión), decidido por el propietario al destaparse que la imagen sirve la
  configuración degradada
- **Estado:** aceptada, y **con caducidad escrita**: se revierte metiendo torch en la imagen
  **después** de la sesión.

## Contexto

La imagen de `api` no lleva torch. Comprobado en los dos sitios el mismo minuto, en vez de razonado:

```
puerto 8000 (CONTENEDOR): embebedor fallo | nli fallo
puerto 8012 (ANFITRION):  embebedor ok    | nli ok
```

Con el túnel apuntando al contenedor, la sesión enseñaría la configuración **degradada**:

- **Recuperación solo léxica y glosario**: el 3.1 la midió en **58 %** de recall@6 frente al
  **80,9 %** de la fusión.
- **Paráfrasis SIN VERIFICAR**: sin NLI, toda afirmación reformulada sale `sin_verificar`. O sea
  **la mitad difícil de la tesis del proyecto no ocurre en pantalla**.

## Decisión

**El lunes se sirve desde uvicorn en el anfitrión**, donde ya viven torch y la GPU, apuntando a la
base que el contenedor sigue exponiendo en el 5434. El túnel apunta ahí.

**El argumento no es de comodidad, y por eso la decisión no admite el atajo:** los números que se
van a citar en la sesión salen de la configuración **completa**. **Enseñar la degradada mientras se
citan los números de la entera es exactamente la falta de correspondencia que este repo persigue en
los documentos, cometida en vivo** — y peor que en un documento, porque nadie puede releerla.

**Meter torch en la imagen es lo correcto y va DESPUÉS**: cambiar el empaquetado a dos días de la
sesión es tocar el despliegue, que sigue congelado. La deuda queda escrita aquí con su fecha.

## Trade-off, dicho entero

| | contenedor | anfitrión |
|---|---|---|
| embebedor y NLI | **caídos** | **arriba** |
| reproducibilidad del entorno | la de la imagen | la de esta máquina |
| `redis` y `worker` | arriba | **caídos** (`redis:6379` no resuelve fuera de compose) |

**Lo que se pierde es real y se declara**: se sirve desde un entorno que no está empaquetado, o sea
que *"funciona aquí"* deja de ser una garantía transportable. Se acepta **para una sesión y con
fecha de caducidad**, no como forma de desplegar. Y `redis`/`worker` caídos no afectan: `/consulta`
no los usa, y `/salud` lo dice con esas palabras.

## La comprobación previa, que es un PASO DEL PROCEDIMIENTO y no una nota

```bash
python scripts/servir_anfitrion.py --puerto 8012      # arranca y comprueba
python scripts/servir_anfitrion.py --solo-comprobar --puerto 8012
```

**Antes de abrir el túnel, `/salud` tiene que decir `embebedor` y `nli` ARRIBA.** Si dice caídos, se
está sirviendo otra cosa y el script se para en vez de arrancar.

Es **"arriba no significa arriba el mío" aplicado a la CAPACIDAD y no al proceso**, que es un piso
más arriba: allí el proceso no era el mío; aquí el proceso es el mío **y no sabe hacer lo que la
sesión va a enseñar**. Un `/salud` con 200 y `puede_responder: true` es compatible con las dos
capacidades caídas — de hecho es literalmente lo que contesta el contenedor hoy.

### Y dos defectos del propio script, cazados al escribirlo

1. **Esperaba `Application startup complete` y esa línea no significa "ya escucha"**: uvicorn la
   imprime al terminar el `lifespan` y todavía no acepta conexiones. La comprobación daba
   *"/salud no contesta"* sobre un arranque perfectamente sano — **la guarda inventándose la avería
   que perseguía**. Se espera a `Uvicorn running on`.
2. **`/salud` con 5 s de plazo y un intento era demasiado poco**: sondea base, extensiones, redis,
   worker, embebedor, reordenador y NLI, y el worker solo ya midió **2.030 ms**. Plazo de 20 s y
   seis intentos: lo que se quiere saber es si la capacidad **está**, no si contesta rápido.

## Consecuencia para el ensayo

**El ensayo del propietario tiene que hacerse contra este montaje**, no contra el contenedor. Un
ensayo en el 8000 estaría probando un sistema **distinto** del que se ve el lunes — el mismo error
que este ADR evita, cometido en la preparación.
