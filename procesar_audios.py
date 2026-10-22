import json
import unicodedata
import wave
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

CARPETA_GUIONES = Path("guiones")
CARPETA_AUDIOS = Path("audios")
CARPETA_LIMPIOS = Path("audios_limpios")
CARPETA_TIEMPOS = Path("tiempos")
ARCHIVO_ESTILO = Path("estilo_voz.txt")
PALABRAS_A_BUSCAR = 3   # cuántas palabras buscamos (del inicio del guion o del final de la instrucción)
MARGEN = 0.15           # segundos que dejamos antes de la primera palabra, para no cortarla


def normalizar(palabra):
    """Minúsculas, sin tildes y sin puntuación: 'Cortá,' -> 'corta'."""
    sin_tildes = unicodedata.normalize("NFD", palabra.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return "".join(c for c in sin_tildes if c.isalnum())


def leer_wav(ruta):
    """Devuelve las muestras crudas (int16) y la frecuencia de nuestro WAV."""
    with wave.open(str(ruta), "rb") as archivo:
        frecuencia = archivo.getframerate()
        datos = archivo.readframes(archivo.getnframes())
    return np.frombuffer(datos, dtype=np.int16), frecuencia


def para_whisper(muestras, frecuencia):
    """Pasa las muestras a float entre -1 y 1, remuestreadas a 16 kHz."""
    audio = muestras.astype(np.float32) / 32768.0
    duracion = len(audio) / frecuencia
    t_viejo = np.linspace(0, duracion, num=len(audio), endpoint=False)
    t_nuevo = np.linspace(0, duracion, num=int(duracion * 16000), endpoint=False)
    return np.interp(t_nuevo, t_viejo, audio).astype(np.float32)


def transcribir(modelo, muestras, frecuencia):
    """Devuelve una lista de palabras con su inicio y fin en segundos."""
    segmentos, _ = modelo.transcribe(
        para_whisper(muestras, frecuencia), language="es", word_timestamps=True
    )
    return [
        {"palabra": p.word.strip(), "inicio": p.start, "fin": p.end}
        for s in segmentos
        for p in s.words
    ]


def se_parecen(a, b):
    """True si dos palabras normalizadas son iguales o muy parecidas."""
    return a == b or SequenceMatcher(None, a, b).ratio() >= 0.7


def buscar_secuencia(palabras, objetivo):
    """Busca 'objetivo' (lista de palabras) en la transcripción, tolerando una palabra distinta.
    Devuelve el índice donde empieza, o None."""
    objetivo = [normalizar(p) for p in objetivo]
    objetivo = [p for p in objetivo if p]  # descarta "palabras" que eran solo signos
    transcritas = [normalizar(p["palabra"]) for p in palabras]
    minimo = len(objetivo) - 1

    for i in range(len(transcritas) - len(objetivo) + 1):
        ventana = transcritas[i:i + len(objetivo)]
        coincidencias = sum(se_parecen(a, b) for a, b in zip(ventana, objetivo))
        if coincidencias >= minimo:
            return i
    return None


def buscar_corte(palabras, guion, estilo):
    """Devuelve el segundo donde empieza el guion, o None si no lo encuentra.
    Plan A: buscar las primeras palabras del guion.
    Plan B: buscar las últimas palabras de la instrucción y tomar la palabra siguiente."""
    i = buscar_secuencia(palabras, guion.split()[:PALABRAS_A_BUSCAR])
    if i is not None:
        return palabras[i]["inicio"], "inicio del guion"

    final_instruccion = estilo.split()[-PALABRAS_A_BUSCAR:]
    i = buscar_secuencia(palabras, final_instruccion)
    if i is not None:
        siguiente = i + len(final_instruccion)
        if siguiente < len(palabras):
            return palabras[siguiente]["inicio"], "final de la instrucción"
    return None, None


def guardar_wav(muestras, frecuencia, ruta):
    with wave.open(str(ruta), "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(frecuencia)
        archivo.writeframes(muestras.tobytes())


def main():
    CARPETA_LIMPIOS.mkdir(exist_ok=True)
    CARPETA_TIEMPOS.mkdir(exist_ok=True)
    estilo = ARCHIVO_ESTILO.read_text(encoding="utf-8").strip()
    audios = sorted(CARPETA_AUDIOS.glob("*.wav"))
    modelo = None  # lo cargamos solo si hay algo que procesar

    for numero, ruta_audio in enumerate(audios, start=1):
        nombre = ruta_audio.stem
        ruta_limpio = CARPETA_LIMPIOS / f"{nombre}.wav"
        ruta_tiempos = CARPETA_TIEMPOS / f"{nombre}.json"
        print(f"[{numero}/{len(audios)}] {nombre}")

        if ruta_limpio.exists() and ruta_tiempos.exists():
            print("  Ya procesado, lo salteo.")
            continue

        if modelo is None:
            print("  Cargando Whisper...")
            modelo = WhisperModel("small", device="cpu", compute_type="int8")

        guion = (CARPETA_GUIONES / f"{nombre}.txt").read_text(encoding="utf-8")
        muestras, frecuencia = leer_wav(ruta_audio)
        palabras = transcribir(modelo, muestras, frecuencia)

        inicio, metodo = buscar_corte(palabras, guion, estilo)
        if inicio is None:
            print("  No encontré dónde empieza el guion. No recorto: revisalo a mano.")
            corte = 0.0
        else:
            corte = max(0.0, inicio - MARGEN)
            print(f"  Corte en {inicio:.2f}s (por {metodo}). Recorto desde {corte:.2f}s.")

        guardar_wav(muestras[int(corte * frecuencia):], frecuencia, ruta_limpio)

        # Corremos los tiempos para que coincidan con el audio recortado
        tiempos = [
            {**p, "inicio": round(p["inicio"] - corte, 2), "fin": round(p["fin"] - corte, 2)}
            for p in palabras
            if p["inicio"] >= corte
        ]
        ruta_tiempos.write_text(json.dumps(tiempos, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Guardado en {ruta_limpio} y {ruta_tiempos}")


if __name__ == "__main__":
    main()