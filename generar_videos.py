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
    vfx,
)
from PIL import Image, ImageDraw, ImageFont

import plantillas as p

CARPETA_LIMPIOS = Path("audios_limpios")
CARPETA_SUBTITULOS = Path("subtitulos")
CARPETA_FRASES = Path("frases")
CARPETA_ESCENAS = Path("escenas")
CARPETA_VIDEOS = Path("videos")
CARPETA_MUSICA = Path("musica")

ANCHO, ALTO = p.ANCHO, p.ALTO
COLOR_FONDO = p.AZUL_MARCA
COLOR_TEXTO = (255, 255, 255)
COLOR_RESALTADO = p.AMARILLO
FUENTE = p.FUENTE_BOLD
TAMANO_FUENTE = 96
ANCHO_MAXIMO_TEXTO = 900
GROSOR_BORDE = 8
ESPACIO_ENTRE_LINEAS = 20
FPS = 30

VOLUMEN_MUSICA = 0.10
FADE_ENTRADA = 1.0
FADE_SALIDA = 2.0
UMBRAL_INTRO = 0.5

DURACION_ANIMACION = 0.3   # segundos que tarda una escena en entrar
DESPLAZAMIENTO = 60        # píxeles que sube al entrar


# ---------- Subtítulos ----------
def partir_en_lineas(palabras, fuente):
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
    palabras = [x.upper() for x in palabras]
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
            dibujo.text((x, y), palabras[i], font=fuente, fill=color, anchor="lm",
                        stroke_width=GROSOR_BORDE, stroke_fill="black")
            x += fuente.getlength(palabras[i]) + espacio

    return np.array(imagen)


def capas_subtitulos(bloques, fuente, centro_y):
    capas = []
    for bloque in bloques:
        textos = [x["texto"] for x in bloque["palabras"]]
        for i, palabra in enumerate(bloque["palabras"]):
            duracion = palabra["fin"] - palabra["inicio"]
            if duracion <= 0:
                continue
            imagen = dibujar_subtitulo(textos, i, fuente)
            capas.append(
                ImageClip(imagen)
                .with_start(palabra["inicio"])
                .with_duration(duracion)
                .with_position(("center", centro_y - imagen.shape[0] / 2))
            )
    return capas


# ---------- Escenas ----------
def posicion_animada(x, y):
    """Devuelve una función: la escena arranca DESPLAZAMIENTO px más abajo y sube hasta su lugar."""
    def posicion(t):
        progreso = min(1.0, t / DURACION_ANIMACION)
        return (x, y + DESPLAZAMIENTO * (1 - progreso))
    return posicion


def capas_escenas(nombre, duracion_total):
    """Lee escenas/<nombre>.json y arma una capa por escena. Si no existe, no hay escenas."""
    ruta_escenas = CARPETA_ESCENAS / f"{nombre}.json"
    if not ruta_escenas.exists():
        return []

    escenas = json.loads(ruta_escenas.read_text(encoding="utf-8"))
    frases = json.loads((CARPETA_FRASES / f"{nombre}.json").read_text(encoding="utf-8"))
    inicio_de = {f["numero"]: f["inicio"] for f in frases}

    capas = []
    for k, escena in enumerate(escenas):
        inicio = inicio_de[escena["frase"]]
        if k + 1 < len(escenas):
            fin = inicio_de[escenas[k + 1]["frase"]]
        else:
            fin = duracion_total
        if fin <= inicio:
            continue

        imagen = p.PLANTILLAS[escena["escena"]](escena)
        alto, ancho = imagen.shape[:2]
        x = (ANCHO - ancho) / 2
        y = p.CENTRO_ESCENA_Y - alto / 2
        capas.append(
            ImageClip(imagen)
            .with_start(inicio)
            .with_duration(fin - inicio)
            .with_position(posicion_animada(x, y))
            .with_effects([vfx.CrossFadeIn(DURACION_ANIMACION)])
        )
    return capas


# ---------- Música ----------
def elegir_musica(nombre):
    pistas = sorted(CARPETA_MUSICA.glob("*.mp3"))
    if not pistas:
        return None
    numero = int(hashlib.md5(nombre.encode()).hexdigest(), 16)
    return pistas[numero % len(pistas)]


def fin_de_intro(musica):
    frecuencia = 4000
    muestras = musica.to_soundarray(fps=frecuencia)
    if muestras.ndim > 1:
        muestras = muestras.mean(axis=1)
    segundos = len(muestras) // frecuencia
    if segundos < 2:
        return 0.0
    volumen = np.array([
        np.sqrt(np.mean(muestras[s * frecuencia:(s + 1) * frecuencia] ** 2))
        for s in range(segundos)
    ])
    referencia = np.percentile(volumen, 90)
    fuertes = np.where(volumen >= referencia * UMBRAL_INTRO)[0]
    return float(fuertes[0]) if len(fuertes) else 0.0


def armar_audio(voz, nombre):
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


# ---------- Video ----------
def armar_video(nombre, fuente):
    voz = AudioFileClip(str(CARPETA_LIMPIOS / f"{nombre}.wav"))
    bloques = json.loads((CARPETA_SUBTITULOS / f"{nombre}.json").read_text(encoding="utf-8"))

    escenas = capas_escenas(nombre, voz.duration)
    print(f"  Escenas: {len(escenas)}")
    centro_subs = p.CENTRO_SUBTITULOS_Y if escenas else ALTO / 2

    fondo = ColorClip(size=(ANCHO, ALTO), color=COLOR_FONDO).with_duration(voz.duration)
    capas = [fondo, *escenas, *capas_subtitulos(bloques, fuente, centro_subs)]

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