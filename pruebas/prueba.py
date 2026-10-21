import os
from dotenv import load_dotenv
from google import genai

load_dotenv()  # lee el archivo .env
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

respuesta = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="Decime en una frase qué es el phishing.",
)
print(respuesta.text)