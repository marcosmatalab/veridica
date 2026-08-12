"""Saca la prosa del alumno de un JSON que todavía se está escribiendo (encargo 2.2).

EL PROBLEMA, QUE ES EL QUE DECIDE SI LA DEMO PARECE RÁPIDA. Con salida tipada el modelo no emite
prosa: emite un objeto JSON. Eso deja dos tiempos distintos donde antes parecía haber uno:

- el **TTFT del proveedor**, cuando llega el primer token del JSON (que es `{`), y
- el **TTFT del alumno**, cuando aparece en pantalla el primer carácter de prosa de verdad.

Si el servidor espera al objeto entero para validarlo antes de emitir nada, el segundo número es
igual al total y el streaming no compra absolutamente nada. Si emite el JSON crudo, el alumno ve
llaves y comillas. Este módulo es la tercera salida: leer el objeto según llega y emitir SOLO el
contenido de `respuesta_redactada`, decodificado, carácter a carácter (ADR 0009).

CÓMO, Y POR QUÉ NO CON UNA EXPRESIÓN REGULAR. Buscar `"respuesta_redactada"` en el texto acumulado
casa también cuando esa cadena aparece DENTRO de otro valor —una `cita` del temario que hable del
contrato, por ejemplo—, y entonces se emitiría como prosa lo que no lo es. Así que se recorre el
flujo carácter a carácter con un autómata que sabe si está dentro de una cadena, a qué profundidad
está y si la cadena que acaba de cerrar era una CLAVE (le sigue `:`) o un valor. La clave solo cuenta
a profundidad 1, o sea en el objeto raíz.

Los escapes se decodifican aquí (`\\n`, `\\"`, `\\uXXXX`), incluso partidos entre dos trozos del
flujo: un `\\u00e9` cortado por la mitad no puede salir a pantalla como `\\u00`.
"""
from app.modelos.contrato import CAMPO_PROSA

_SIMPLES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f",
            "n": "\n", "r": "\r", "t": "\t"}


class ProsaEnCurso:
    """Autómata incremental: se le dan trozos del JSON y devuelve la prosa nueva de cada trozo."""

    def __init__(self, campo: str = CAMPO_PROSA):
        self.campo = campo
        self.terminada = False
        self.empezada = False
        self._profundidad = 0
        self._en_cadena = False
        self._escapando = False
        self._esperando_hex = False   # estamos leyendo los 4 hexadecimales de un \uXXXX
        self._unicode = ""            # los que han llegado ya
        self._alto = None             # mitad alta de un par suplente, a la espera de su pareja
        self._cadena = []             # la cadena que se está leyendo, para reconocer la clave
        self._clave_cerrada = None    # cadena recién cerrada, a la espera de saber si es clave
        self._toca_valor = False      # la clave era la nuestra: la próxima cadena es la prosa
        self._en_prosa = False

    def alimentar(self, trozo: str) -> str:
        """Devuelve los caracteres de prosa NUEVOS que aporta este trozo (a veces, ninguno)."""
        salida = []
        for c in trozo:
            if self._en_prosa:
                self._paso_en_prosa(c, salida)
            else:
                self._paso_fuera(c)
        return "".join(salida)

    # --- dentro del valor que nos interesa ------------------------------------------------------

    def _paso_en_prosa(self, c: str, salida: list) -> None:
        if self._esperando_hex:
            self._unicode += c
            if len(self._unicode) == 4:
                self._esperando_hex = False
                self._emitir_punto(int(self._unicode, 16), salida)
                self._unicode = ""
            return
        if self._escapando:
            self._escapando = False
            if c == "u":
                self._esperando_hex = True
                self._unicode = ""
                return
            salida.append(_SIMPLES.get(c, c))
            return
        if c == "\\":
            self._escapando = True
            return
        if c == '"':
            self._en_prosa = False
            self.terminada = True
            return
        salida.append(c)

    def _emitir_punto(self, punto: int, salida: list) -> None:
        """Junta los pares suplentes. Un `\\ud83d` suelto no es un carácter y no puede salir a
        pantalla: rompe la codificación del evento SSE en cuanto haya un emoji en la redacción."""
        if 0xD800 <= punto <= 0xDBFF:
            self._alto = punto
            return
        if self._alto is not None and 0xDC00 <= punto <= 0xDFFF:
            salida.append(chr(0x10000 + ((self._alto - 0xD800) << 10) + (punto - 0xDC00)))
            self._alto = None
            return
        self._alto = None
        salida.append(chr(punto))

    # --- fuera: contar llaves, cadenas y claves --------------------------------------------------

    def _paso_fuera(self, c: str) -> None:
        if self._en_cadena:
            if self._escapando:
                self._escapando = False
                self._cadena.append(c)
            elif c == "\\":
                self._escapando = True
            elif c == '"':
                self._en_cadena = False
                self._clave_cerrada = "".join(self._cadena)
                self._cadena = []
            else:
                self._cadena.append(c)
            return

        if c == '"':
            if self._toca_valor:
                self._toca_valor = False
                self._en_prosa = True
                self.empezada = True
                self._escapando = False
                self._esperando_hex = False
                self._unicode = ""
            else:
                self._en_cadena = True
                self._cadena = []
            return

        if c == ":":
            if self._clave_cerrada == self.campo and self._profundidad == 1 and not self.terminada:
                self._toca_valor = True
            self._clave_cerrada = None
            return

        if c in "{[":
            self._profundidad += 1
            self._clave_cerrada = None
        elif c in "}]":
            self._profundidad -= 1
            self._clave_cerrada = None
        elif not c.isspace():
            self._clave_cerrada = None
