import json
from pathlib import Path

import numpy as np
from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont

CARPETA_LIMPIOS = Path("audios_limpios")
CARPETA_SUBTITULOS = Path("subtitulos")
CARPETA_VIDEOS = Path("videos")

ANCHO, ALTO = 1080, 1920
COLOR_FONDO = (20, 24, 40)          # azul muy oscuro, provisorio
COLOR_TEXTO = (255, 255, 255)       # blanco
COLOR_RESALTADO = (255, 214, 0)     # amarillo
FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TAMANO_FUENTE = 96
ANCHO_MAXIMO_TEXTO = 900            # deja margen a los costados
GROSOR_BORDE = 8
ESPACIO_ENTRE_LINEAS = 20
FPS = 30


def partir_en_lineas(palabras, fuente):
    """Reparte las palabras en líneas que entren a lo ancho. Devuelve una lista de listas de índices."""
    lineas, actual, ancho_actual = [], [], 0
    espacio = fuente.getlength(" ")
    for i, palabra in enumerate(palabras):
        ancho_palabra = fuente.getlength(palabra)
        ancho_con_esta = ancho_actual + (espacio if actual else 0) + ancho_palabra
        if actual and ancho_con_esta > ANCHO_MAXIMO_TEXTO:
            lineas.append(actual)
            actual, ancho_actual = [i], ancho_palabra
        else:
            actual.append(i)
            ancho_actual = ancho_con_esta
    if actual:
        lineas.append(actual)
    return lineas


def dibujar_subtitulo(palabras, resaltada, fuente):
    """Dibuja el bloque palabra por palabra, con la palabra 'resaltada' en amarillo.
    La imagen mide solo lo que ocupa el texto, no toda la pantalla."""
    palabras = [p.upper() for p in palabras]
    lineas = partir_en_lineas(palabras, fuente)
    espacio = fuente.getlength(" ")
    ascenso, descenso = fuente.getmetrics()
    alto_linea = ascenso + descenso + ESPACIO_ENTRE_LINEAS

    margen = GROSOR_BORDE * 2
    ancho_imagen = ANCHO_MAXIMO_TEXTO + margen * 2
    alto_imagen = alto_linea * len(lineas) + margen * 2

    imagen = Image.new("RGBA", (ancho_imagen, alto_imagen), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)

    for n, indices in enumerate(lineas):
        ancho_linea = sum(fuente.getlength(palabras[i]) for i in indices) + espacio * (len(indices) - 1)
        x = (ancho_imagen - ancho_linea) / 2           # centramos cada línea
        y = margen + n * alto_linea + alto_linea / 2   # centro vertical de la línea
        for i in indices:
            color = COLOR_RESALTADO if i == resaltada else COLOR_TEXTO
            dibujo.text(
                (x, y),
                palabras[i],
                font=fuente,
                fill=color,
                anchor="lm",                    # x = borde izquierdo, y = centro vertical
                stroke_width=GROSOR_BORDE,
                stroke_fill="black",
            )
            x += fuente.getlength(palabras[i]) + espacio

    return np.array(imagen)


def armar_video(nombre, fuente):
    audio = AudioFileClip(str(CARPETA_LIMPIOS / f"{nombre}.wav"))
    bloques = json.loads((CARPETA_SUBTITULOS / f"{nombre}.json").read_text(encoding="utf-8"))

    fondo = ColorClip(size=(ANCHO, ALTO), color=COLOR_FONDO).with_duration(audio.duration)

    capas = [fondo]
    for bloque in bloques:
        textos = [p["texto"] for p in bloque["palabras"]]
        for i, palabra in enumerate(bloque["palabras"]):
            duracion = palabra["fin"] - palabra["inicio"]
            if duracion <= 0:
                continue
            capas.append(
                ImageClip(dibujar_subtitulo(textos, i, fuente))
                .with_start(palabra["inicio"])
                .with_duration(duracion)
                .with_position("center")
            )

    video = CompositeVideoClip(capas, size=(ANCHO, ALTO)).with_audio(audio)
    video.write_videofile(
        str(CARPETA_VIDEOS / f"{nombre}.mp4"),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="veryfast",
        ffmpeg_params=["-pix_fmt", "yuv420p"],
        logger=None,
    )


def main():
    CARPETA_VIDEOS.mkdir(exist_ok=True)
    fuente = ImageFont.truetype(FUENTE, TAMANO_FUENTE)
    subtitulos = sorted(CARPETA_SUBTITULOS.glob("*.json"))

    for numero, ruta in enumerate(subtitulos, start=1):
        nombre = ruta.stem
        destino = CARPETA_VIDEOS / f"{nombre}.mp4"
        print(f"[{numero}/{len(subtitulos)}] {nombre}")
        if destino.exists():
            print("  Ya existe, lo salteo.")
            continue
        armar_video(nombre, fuente)
        print(f"  Guardado en {destino}")


if __name__ == "__main__":
    main()