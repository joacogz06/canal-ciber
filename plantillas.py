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


# ---------- Marco de celular (compartido por las plantillas de apps) ----------
GRIS_TEXTO = (120, 130, 145)
MARCO = (20, 20, 24)
ANCHO_CEL, ALTO_CEL = 700, 1180
BORDE_CEL = 22
RADIO_PANTALLA = 60


def celular(dibujar_pantalla):
    """Dibuja el marco de celular y llama a dibujar_pantalla(pantalla, ancho, alto) para el contenido.
    El contenido queda recortado con las esquinas redondeadas de la pantalla."""
    ancho_pant, alto_pant = ANCHO_CEL - BORDE_CEL * 2, ALTO_CEL - BORDE_CEL * 2

    pantalla = Image.new("RGBA", (ancho_pant, alto_pant), BLANCO)
    dibujar_pantalla(pantalla, ancho_pant, alto_pant)

    mascara = Image.new("L", (ancho_pant, alto_pant), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, ancho_pant - 1, alto_pant - 1],
                                              radius=RADIO_PANTALLA, fill=255)

    img = Image.new("RGBA", (ANCHO_CEL, ALTO_CEL), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, ANCHO_CEL - 1, ALTO_CEL - 1], radius=80, fill=MARCO)
    img.paste(pantalla, (BORDE_CEL, BORDE_CEL), mascara)
    return img


def dibujar_texto_resaltado(d, x, y, lineas, fnt, alto_linea, color):
    """Dibuja líneas de (palabra, resaltada) empezando en x, y (arriba a la izquierda)."""
    espacio = fnt.getlength(" ")
    for n, linea in enumerate(lineas):
        cx = x
        cy = y + n * alto_linea + alto_linea / 2
        for palabra, resaltada in linea:
            w = fnt.getlength(palabra)
            if resaltada:
                cx += 8
                d.rounded_rectangle([cx - 8, cy - alto_linea / 2 + 2, cx + w + 8, cy + alto_linea / 2 - 2],
                                    radius=8, fill=AZUL_OSCURO)
                d.text((cx, cy), palabra, font=fnt, fill=AMARILLO, anchor="lm")
                cx += w + espacio + 8
            else:
                d.text((cx, cy), palabra, font=fnt, fill=color, anchor="lm")
                cx += w + espacio


def ancho_de_lineas(lineas, fnt):
    espacio = fnt.getlength(" ")
    return max(
        sum(fnt.getlength(p) + (16 if r else 0) for p, r in linea) + espacio * (len(linea) - 1)
        for linea in lineas
    )


# ---------- Plantilla: chat ----------
FONDO_CHAT = (228, 236, 246)
BURBUJA_OTRO = (255, 255, 255)
BURBUJA_YO = (199, 228, 255)


def burbuja(msg, fnt, fnt_hora, ancho_pant, hora):
    """Devuelve la imagen de una burbuja de mensaje."""
    ascenso, descenso = fnt.getmetrics()
    alto_linea = ascenso + descenso + 6
    padding = 24
    ancho_max = int(ancho_pant * 0.78)

    lineas = partir_lineas(separar_resaltado(msg["texto"]), fnt, ancho_max - padding * 2)
    ancho_texto = ancho_de_lineas(lineas, fnt)
    ancho_b = int(max(ancho_texto, fnt_hora.getlength(hora)) + padding * 2)
    alto_b = int(alto_linea * len(lineas) + padding * 2 + 26)

    color = BURBUJA_YO if msg["de"] == "yo" else BURBUJA_OTRO
    img = Image.new("RGBA", (ancho_b, alto_b), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, ancho_b - 1, alto_b - 1], radius=28, fill=color)
    dibujar_texto_resaltado(d, padding, padding, lineas, fnt, alto_linea, AZUL_OSCURO)
    d.text((ancho_b - padding, alto_b - 14), hora, font=fnt_hora, fill=GRIS_TEXTO, anchor="rb")
    return img


def chat(datos, visibles=None):
    """Celular con una conversación. 'visibles' = cuántos mensajes mostrar (None = todos).
    Como en un chat real, los mensajes nuevos quedan abajo y los viejos suben y se cortan."""
    contacto = datos.get("contacto", "Desconocido")
    mensajes = datos.get("mensajes", [])
    if visibles is not None:
        mensajes = mensajes[:visibles]

    def pantalla_chat(pant, ancho, alto):
        d = ImageDraw.Draw(pant)
        alto_barra = 150
        alto_input = 120

        # Zona de mensajes
        d.rectangle([0, 0, ancho, alto], fill=FONDO_CHAT)
        fnt = fuente(36, bold=False)
        fnt_hora = fuente(22, bold=False)
        burbujas = [burbuja(m, fnt, fnt_hora, ancho, f"12:{30 + i:02d}") for i, m in enumerate(mensajes)]

        # Apilamos desde abajo hacia arriba
        y = alto - alto_input - 20
        for msg, b in reversed(list(zip(mensajes, burbujas))):
            y -= b.height
            x = ancho - 30 - b.width if msg["de"] == "yo" else 30
            pant.paste(b, (x, y), b)
            y -= 18
            if y < alto_barra:
                break

        # Barra de escribir (encima de los mensajes)
        d.rectangle([0, alto - alto_input, ancho, alto], fill=FONDO_CHAT)
        d.rounded_rectangle([24, alto - alto_input + 10, ancho - 24, alto - 30], radius=40, fill=BLANCO)
        d.text((64, alto - alto_input / 2 - 10), "Mensaje", font=fuente(32, bold=False),
               fill=GRIS_TEXTO, anchor="lm")

        # Barra superior (tapa los mensajes que subieron de más)
        d.rectangle([0, 0, ancho, alto_barra], fill=AZUL_MARCA)
        centro = alto_barra / 2 + 12
        d.text((36, centro), "<", font=fuente(48), fill=BLANCO, anchor="lm")
        ax = 116
        d.ellipse([ax - 36, centro - 36, ax + 36, centro + 36], fill=BLANCO)
        primera = contacto.strip()[0]
        if primera.isalpha():
            d.text((ax, centro), primera.upper(), font=fuente(40), fill=AZUL_MARCA, anchor="mm")
        else:
            # Número desconocido: silueta de persona
            d.ellipse([ax - 12, centro - 22, ax + 12, centro + 2], fill=AZUL_MARCA)
            d.pieslice([ax - 24, centro + 4, ax + 24, centro + 52], 180, 360, fill=AZUL_MARCA)
        d.text((ax + 60, centro - 18), contacto, font=fuente(36), fill=BLANCO, anchor="lm")
        d.text((ax + 60, centro + 24), "en línea", font=fuente(26, bold=False),
               fill=(210, 230, 255), anchor="lm")

    return np.array(celular(pantalla_chat))


PLANTILLAS = {
    "texto": texto,
    "chat": chat,
}