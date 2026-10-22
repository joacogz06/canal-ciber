import os
import wave
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

MODELO_TTS = "gemini-3.8-flash-tts"
VOZ = "Achird"
ETIQUETA = "porteno_ultra_guion5" # cambiala en cada prueba para no pisar las anteriores

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

estilo = Path("estilo_voz.txt").read_text(encoding="utf-8").strip()
texto_prueba = Path("guiones/05_por-qué-no-usar-la-misma-contraseña-en-todos-lados.txt").read_text(encoding="utf-8").strip()

respuesta = client.models.generate_content(
    model=MODELO_TTS,
    contents=f"{estilo}\n{texto_prueba}",
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOZ)
            )
        ),
    ),
)

audio = respuesta.candidates[0].content.parts[0].inline_data.data
nombre = f"prueba_{VOZ}_{ETIQUETA}.wav"

with wave.open(nombre, "wb") as archivo:
    archivo.setnchannels(1)
    archivo.setsampwidth(2)
    archivo.setframerate(24000)
    archivo.writeframes(audio)

print(f"Listo: {nombre}")