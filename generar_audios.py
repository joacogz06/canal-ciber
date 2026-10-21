import os
import time
import wave
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

MODELO_TTS = "gemini-3.8-flash-tts"
VOZ = "Achird"
CARPETA_GUIONES = Path("guiones")
CARPETA_AUDIOS = Path("audios")
MAX_INTENTOS = 3

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def generar_audio(texto):
    """Pide el audio a Gemini. Reintenta si el servidor está saturado o si hay límite de pedidos."""
    for intento in range(1, MAX_INTENTOS + 1):
        try:
            respuesta = client.models.generate_content(
                model=MODELO_TTS,
                contents=texto,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOZ)
                        )
                    ),
                ),
            )
            return respuesta.candidates[0].content.parts[0].inline_data.data
        except errors.ServerError as e:
            print(f"  Servidor ocupado (intento {intento}/{MAX_INTENTOS}): {e.code}")
        except errors.ClientError as e:
            if e.code != 429:
                raise  # cualquier otro error del cliente es un problema real: cortamos
            if "free_tier_requests" in str(e.message):
                print("  Se terminó la cuota diaria gratuita. Volvé a correrlo mañana.")
                raise SystemExit
            print(f"  Límite de pedidos alcanzado (intento {intento}/{MAX_INTENTOS}): {e.message}")
        time.sleep(20 * intento)  # espera 20s, después 40s, después 60s
    return None


def guardar_wav(datos, ruta):
    """Gemini devuelve audio crudo: le agregamos el encabezado WAV."""
    with wave.open(str(ruta), "wb") as archivo:
        archivo.setnchannels(1)      # mono
        archivo.setsampwidth(2)      # 16 bits
        archivo.setframerate(24000)  # 24 kHz
        archivo.writeframes(datos)


def main():
    estilo = Path("estilo_voz.txt").read_text(encoding="utf-8").strip()
    guiones = sorted(CARPETA_GUIONES.glob("*.txt"))
    CARPETA_AUDIOS.mkdir(exist_ok=True)

    for numero, ruta_guion in enumerate(guiones, start=1):
        ruta_audio = CARPETA_AUDIOS / f"{ruta_guion.stem}.wav"
        print(f"[{numero}/{len(guiones)}] {ruta_guion.name}")

        if ruta_audio.exists():
            print("  Ya existe, lo salteo.")
            continue

        guion = ruta_guion.read_text(encoding="utf-8").strip()
        datos = generar_audio(f"{estilo}\n\n{guion}")

        if datos is None:
            print("  No se pudo generar, lo salteo.")
            continue

        guardar_wav(datos, ruta_audio)
        print(f"  Guardado en {ruta_audio}")


if __name__ == "__main__":
    main()