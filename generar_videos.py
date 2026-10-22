import hashlib
import json
from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    afx,
)
from PIL import Image, ImageDraw, ImageFont

CARPETA_LIMPIOS = Path("audios_limpios")
CARPETA_SUBTITULOS = Path("subtitulos")
CARPETA_VIDEOS = Path("videos")
CARPETA_MUSICA = Path("musica")

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

VOLUMEN_MUSICA = 0.10               # 10% del volumen original
FADE_ENTRADA = 1.0                  # segundos
FADE_SALIDA = 2.0                   # segundos
UMBRAL_INTRO = 0.5                  # arranca cuando la pista llega al 50% de su volumen fuerte


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
    """Dibuja el bloque palabra por palabra, con la palabra 'resaltada' en amarillo."""
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
        x = (ancho_imagen - ancho_linea) / 2
        y = margen + n * alto_linea + alto_linea / 2
        for i in indices:
            color = COLOR_RESALTADO if i == resaltada else COLOR_TEXTO
            dibujo.text(
                (x, y),
                palabras[i],
                font=fuente,
                fill=color,
                anchor="lm",
                stroke_width=GROSOR_BORDE,
                stroke_fill="black",
            )
            x += fuente.getlength(palabras[i]) + espacio

    return np.array(imagen)


def elegir_musica(nombre):
    """Elige una pista según el nombre del video: siempre la misma para el mismo video."""
    pistas = sorted(CARPETA_MUSICA.glob("*.mp3"))
    if not pistas:
        return None
    numero = int(hashlib.md5(nombre.encode()).hexdigest(), 16)
    return pistas[numero % len(pistas)]


def fin_de_intro(musica):
    """Devuelve el segundo donde la pista ya suena fuerte, saltando una intro silenciosa."""
    frecuencia = 4000  # alcanza para medir volumen, y es mucho más rápido que leer en calidad completa
    muestras = musica.to_soundarray(fps=frecuencia)
    if muestras.ndim > 1:
        muestras = muestras.mean(axis=1)  # estéreo a mono

    segundos = len(muestras) // frecuencia
    if segundos < 2:
        return 0.0
    volumen = np.array([
        np.sqrt(np.mean(muestras[s * frecuencia:(s + 1) * frecuencia] ** 2))
        for s in range(segundos)
    ])
    referencia = np.percentile(volumen, 90)  # lo fuerte que suena en sus partes altas
    fuertes = np.where(volumen >= referencia * UMBRAL_INTRO)[0]
    return float(fuertes[0]) if len(fuertes) else 0.0


def armar_audio(voz, nombre):
    """Mezcla la voz con una pista de música de fondo, si hay."""
    ruta_musica = elegir_musica(nombre)
    if ruta_musica is None:
        print("  No hay música en la carpeta, sigo solo con la voz.")
        return voz

    musica = AudioFileClip(str(ruta_musica))
    inicio = fin_de_intro(musica)
    print(f"  Música: {ruta_musica.name} (desde el segundo {inicio:.0f})")
    musica = musica.subclipped(inicio, musica.duration)

    if musica.duration < voz.duration:
        musica = musica.with_effects([afx.AudioLoop(duration=voz.duration)])
    else:
        musica = musica.subclipped(0, voz.duration)

    musica = musica.with_effects([
        afx.MultiplyVolume(VOLUMEN_MUSICA),
        afx.AudioFadeIn(FADE_ENTRADA),
        afx.AudioFadeOut(FADE_SALIDA),
    ])
    return CompositeAudioClip([musica, voz]).with_duration(voz.duration)


def armar_video(nombre, fuente):
    voz = AudioFileClip(str(CARPETA_LIMPIOS / f"{nombre}.wav"))
    bloques = json.loads((CARPETA_SUBTITULOS / f"{nombre}.json").read_text(encoding="utf-8"))

    fondo = ColorClip(size=(ANCHO, ALTO), color=COLOR_FONDO).with_duration(voz.duration)

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

    video = CompositeVideoClip(capas, size=(ANCHO, ALTO)).with_audio(armar_audio(voz, nombre))
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