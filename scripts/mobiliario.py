#!/usr/bin/env python3
"""Mobiliario de pagina: lo que el PDF trae y el documento no dice.

Se limpia AQUI, en la normalizacion (1.3), y no al trocear, por una razon que importa en la fase 4:
el fragmento que se cita a un alumno tiene que poder compararse LETRA A LETRA con el fichero
derivado del que sale (principio 6: la cita literal se verifica con comparacion de cadenas, sin
modelo). Si el troceado limpiara por su cuenta, el texto citado y el texto de origen dejarian de
coincidir y la comprobacion literal se caeria justo donde tiene que sostenerse.

El filtro por frecuencia que ya habia en normalizar.py quita cabeceras y pies REPETIDOS IGUAL en
muchas paginas ("PROGRAMACION / CFGS DAW"). No quita estos, y por eso se le escapaban 3.329
ocurrencias en 2.448 fragmentos: cada numero de pagina es una linea DISTINTA ("- 7 -", "- 8 -"),
asi que ninguna se repite lo bastante para cruzar el umbral. Contra eso no vale contar: hay que
reconocer la forma.

Tres formas, medidas sobre el corpus real:

  "- 8 -" en su propia linea            2.324 fragmentos
  "... usuarios. - 4 - 2.- Edicion"     pegado dentro de la linea, como corte de pagina
  "9 concat(), devuelve..."             el 9 no es un nueve: es la viñeta Wingdings del PDF, que
                                        el extractor convierte en el digito que le toque
"""
import re

# Numero de pagina solo, con o sin guiones: "8", "- 8 -", "8 / 24", "Pag. 8".
RE_PAGINA_SOLA = re.compile(
    r"^\s*[-–—]?\s*(?:p[aá]g(?:ina)?\.?\s*)?\d{1,3}\s*(?:/\s*\d{1,3})?\s*[-–—]?\s*$", re.I)

# Pie con titulo corto delante: "Tema 3 - 13 -". Se exige el guion de cierre a proposito: sin el,
# "Windows 10 - 2" o "Ejercicio 4 - 3" caerian tambien, y esos si dicen algo.
RE_PIE_NUMERADO = re.compile(
    r"^\s*[\wÁÉÍÓÚÑáéíóúñ][\wÁÉÍÓÚÑáéíóúñ .:ºª]{0,28}?\s*[-–—]\s*\d{1,3}\s*[-–—]\s*$")

# El mismo corte de pagina cuando el extractor lo deja pegado a la frase anterior.
RE_PAGINA_PEGADA = re.compile(r"(?<=\s)[-–—]\s?\d{1,3}\s?[-–—](?=\s|$)")

RE_ESPACIO_DOBLE = re.compile(r"[ \t]{2,}")
RE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def saltos_reales(texto: str) -> str:
    r"""El \r suelto y los caracteres de control que el PDF mete dentro del texto.

    Esto salio de un falso verde y merece quedar escrito. Un "\r" solo no es un salto de linea para
    el fichero, pero SI lo es para cualquiera que lo lea en modo texto, porque Python traduce \r a
    \n al leer. Resultado: el limpiador partia las lineas de una forma y el troceador de otra, y el
    numero de pagina que el limpiador no veia como linea suelta, el troceador si. Dos componentes
    del mismo tubo con dos ideas distintas de que es una linea es exactamente el fallo que este
    repo lleva persiguiendo todo el dia, esta vez en el separador.
    """
    return RE_CONTROL.sub("", texto.replace("\r\n", "\n").replace("\r", "\n"))


def es_mobiliario(linea: str) -> bool:
    """La linea entera es numero de pagina o pie: no aporta nada al fragmento."""
    desnuda = linea.strip()
    if not desnuda:
        return False
    return bool(RE_PAGINA_SOLA.match(desnuda) or RE_PIE_NUMERADO.match(desnuda))


def quitar_pagina_pegada(texto: str) -> str:
    return RE_ESPACIO_DOBLE.sub(" ", RE_PAGINA_PEGADA.sub(" ", texto))


def glifo_de_vineta(texto: str, minimo: int = 3) -> str:
    """Un digito suelto haciendo de viñeta, sustituido por '- '.

    La condicion es lo que evita destrozar una lista numerada de verdad: solo se sustituye si el
    MISMO digito abre al menos `minimo` lineas y sin puntuacion detras. Una lista numerada escribe
    "9." o "9)", y ademas gasta cada numero una sola vez; una viñeta mal convertida repite el mismo
    caracter en todos sus puntos, que es justo la señal.
    """
    for digito in "0123456789":
        patron = re.compile(rf"^[ \t]*{digito}[ \t]+(?=[A-Za-zÁÉÍÓÚÑáéíóúñ(¿¡])", re.M)
        if len(patron.findall(texto)) >= minimo:
            texto = patron.sub("- ", texto)
    return texto


def limpiar(texto: str) -> str:
    """Las tres formas de una pasada. Idempotente: aplicarla dos veces da lo mismo."""
    texto = glifo_de_vineta(saltos_reales(texto))
    lineas = [x for x in texto.split("\n") if not es_mobiliario(x)]
    return quitar_pagina_pegada("\n".join(lineas))
