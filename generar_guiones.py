import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors

MODELO = "gemini-3.8-flash"
CARPETA_SALIDA = Path("guiones")
MAX_INTENTOS = 3

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def nombre_archivo(numero, tema):
    """Convierte el tema en un nombre de archivo seguro: 01_estafa-del-banco.txt"""
    slug = re.sub(r"[^a-z0-9áéíóúñ]+", "-", tema.lower()).strip("-")
    return f"{numero:02d}_{slug[:50]}.txt"


def generar_guion(prompt):
    """Le pide el guion a Gemini, reintentando si el servidor está saturado."""
    for intento in range(1, MAX_INTENTOS + 1):
        try:
            respuesta = client.models.generate_content(model=MODELO, contents=prompt)
            return respuesta.text.strip()
        except errors.ServerError as e:
            print(f"  Servidor ocupado (intento {intento}/{MAX_INTENTOS}): {e.code}")
            time.sleep(10 * intento)  # espera 10s, después 20s, después 30s
    return None


def main():
    plantilla = Path("prompt.txt").read_text(encoding="utf-8")
    temas = [t.strip() for t in Path("temas.txt").read_text(encoding="utf-8").splitlines() if t.strip()]

    CARPETA_SALIDA.mkdir(exist_ok=True)

    for numero, tema in enumerate(temas, start=1):
        print(f"[{numero}/{len(temas)}] {tema}")
        prompt = plantilla.replace("{tema}", tema)
        guion = generar_guion(prompt)

        if guion is None:
            print("  No se pudo generar, lo salteo.")
            continue

        archivo = CARPETA_SALIDA / nombre_archivo(numero, tema)
        archivo.write_text(guion, encoding="utf-8")
        print(f"  Guardado en {archivo}")


if __name__ == "__main__":
    main()