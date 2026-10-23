from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------- Marca ----------
ANCHO, ALTO = 1080, 1920
AZUL_MARCA = (11, 113, 221)
AZUL_OSCURO = (10, 40, 90)
BLANCO = (255, 255, 255)
AMARILLO = (255, 214, 0)

FUENTE_BOLD = str(Path("fuentes/Poppins-Bold.ttf"))
FUENTE_SEMI = str(Path("fuentes/Poppins-SemiBold.ttf"))

# Zonas de la pantalla
CENTRO_ESCENA_Y = 760       # donde va el centro de cada plantilla
CENTRO_SUBTITULOS_Y = 1450  # los subtítulos van más abajo


def fuente(tamano, bold=True):
    return ImageFont.truetype(FUENTE_BOLD if bold else FUENTE_SEMI, tamano)


def separar_resaltado(texto):
    """'Nunca pases el *código*' -> [('Nunca', False), ('pases', False), ('el', False), ('código', True)]"""
    palabras = []
    resaltando = False
    for palabra in texto.split():
        empieza = palabra.startswith("*")
        termina = palabra.endswith("*")
        limpia = palabra.strip("*")
        if empieza:
            resaltando = True
        palabras.append((limpia, resaltando))
        if termina:
            resaltando = False
    return palabras


def partir_lineas(palabras, fnt, ancho_max):
    """Agrupa (palabra, resaltada) en líneas que entren en ancho_max."""
    espacio = fnt.getlength(" ")
    lineas, actual, ancho = [], [], 0
    for palabra, resaltada in palabras:
        w = fnt.getlength(palabra)
        nuevo = ancho + (espacio if actual else 0) + w
        if actual and nuevo > ancho_max:
            lineas.append(actual)
            actual, ancho = [(palabra, resaltada)], w
        else:
            actual.append((palabra, resaltada))
            ancho = nuevo
    if actual:
        lineas.append(actual)
    return lineas


# ---------- Plantilla: texto ----------
def texto(datos):
    """Tarjeta blanca con una frase corta. Las palabras entre *asteriscos* se resaltan."""
    fnt = fuente(84)
    ancho_tarjeta = 900
    padding = 60
    palabras = separar_resaltado(datos["texto"])
    lineas = partir_lineas(palabras, fnt, ancho_tarjeta - padding * 2)

    ascenso, descenso = fnt.getmetrics()
    alto_linea = ascenso + descenso + 18
    alto_tarjeta = alto_linea * len(lineas) + padding * 2

    sombra = 14
    img = Image.new("RGBA", (ancho_tarjeta + sombra, alto_tarjeta + sombra), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # sombra y tarjeta
    d.rounded_rectangle([sombra, sombra, ancho_tarjeta + sombra - 1, alto_tarjeta + sombra - 1],
                        radius=40, fill=(0, 0, 0, 70))
    d.rounded_rectangle([0, 0, ancho_tarjeta - 1, alto_tarjeta - 1], radius=40, fill=BLANCO)

    espacio = fnt.getlength(" ")
    extra = 24  # aire extra a cada lado de una palabra resaltada
    for n, linea in enumerate(lineas):
        ancho_linea = (
            sum(fnt.getlength(p) + (extra * 2 if r else 0) for p, r in linea)
            + espacio * (len(linea) - 1)
        )
        x = (ancho_tarjeta - ancho_linea) / 2
        y = padding + n * alto_linea + alto_linea / 2
        for palabra, resaltada in linea:
            w = fnt.getlength(palabra)
            if resaltada:
                x += extra
                d.rounded_rectangle([x - 16, y - alto_linea / 2 + 6, x + w + 16, y + alto_linea / 2 - 6],
                                    radius=14, fill=AZUL_OSCURO)
                d.text((x, y), palabra, font=fnt, fill=AMARILLO, anchor="lm")
                x += w + extra + espacio
            else:
                d.text((x, y), palabra, font=fnt, fill=AZUL_OSCURO, anchor="lm")
                x += w + espacio

    return np.array(img)


PLANTILLAS = {
    "texto": texto,
}