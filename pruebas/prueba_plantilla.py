from PIL import Image

import plantillas as p
from generar_videos import dibujar_subtitulo
from PIL import ImageFont

fondo = Image.new("RGB", (p.ANCHO, p.ALTO), p.AZUL_MARCA)

tarjeta = Image.fromarray(p.texto({"texto": "Nunca le pases el *código* a nadie"}))
x = (p.ANCHO - tarjeta.width) // 2
y = p.CENTRO_ESCENA_Y - tarjeta.height // 2
fondo.paste(tarjeta, (x, y), tarjeta)

fuente_sub = ImageFont.truetype(p.FUENTE_BOLD, 96)
sub = Image.fromarray(dibujar_subtitulo(["Nunca", "le", "pases"], 1, fuente_sub))
x = (p.ANCHO - sub.width) // 2
y = p.CENTRO_SUBTITULOS_Y - sub.height // 2
fondo.paste(sub, (x, y), sub)

fondo.save("prueba_plantilla.png")
print("Listo: prueba_plantilla.png")