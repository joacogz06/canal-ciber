import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel


def cargar_wav(ruta):
    """Lee nuestro WAV (mono, 16 bits, 24 kHz) y lo pasa a 16 kHz, que es lo que espera Whisper."""
    with wave.open(str(ruta), "rb") as archivo:
        frecuencia = archivo.getframerate()
        datos = archivo.readframes(archivo.getnframes())

    audio = np.frombuffer(datos, dtype=np.int16).astype(np.float32) / 32768.0

    # Remuestreo de 24 kHz a 16 kHz por interpolación
    duracion = len(audio) / frecuencia
    tiempos_viejos = np.linspace(0, duracion, num=len(audio), endpoint=False)
    tiempos_nuevos = np.linspace(0, duracion, num=int(duracion * 16000), endpoint=False)
    return np.interp(tiempos_nuevos, tiempos_viejos, audio).astype(np.float32)


audio_path = sorted(Path("audios").glob("*.wav"))[0]
print(f"Transcribiendo {audio_path.name}...\n")

modelo = WhisperModel("small", device="cpu", compute_type="int8")
segmentos, info = modelo.transcribe(cargar_wav(audio_path), language="es", word_timestamps=True)

for segmento in segmentos:
    for palabra in segmento.words:
        print(f"{palabra.start:6.2f} - {palabra.end:6.2f}  {palabra.word}")