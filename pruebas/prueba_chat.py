from PIL import Image

import plantillas as p

datos = {
    "contacto": "+54 9 11 5555-0000",
    "mensajes": [
        {"de": "otro", "texto": "Hola má, cambié de número"},
        {"de": "otro", "texto": "Agendá este nuevo porfa"},
        {"de": "yo", "texto": "¿Quién sos?"},
        {"de": "otro", "texto": "Soy yo má, se me rompió el celu"},
        {"de": "otro", "texto": "Necesito que me transfieras *$80.000* urgente, después te explico"},
    ],
}

fondo = Image.new("RGB", (p.ANCHO, p.ALTO), p.AZUL_MARCA)
cel = Image.fromarray(p.chat(datos))
fondo.paste(cel, ((p.ANCHO - cel.width) // 2, p.CENTRO_ESCENA_Y - cel.height // 2), cel)
fondo.save("prueba_chat.png")
print("Listo: prueba_chat.png")