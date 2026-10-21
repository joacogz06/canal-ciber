import json
import wave
from difflib import SequenceMatcher
from pathlib import Path

from procesar_audios import normalizar

CARPETA_GUIONES = Path("guiones")
CARPETA_LIMPIOS = Path("audios_limpios")
CARPETA_TIEMPOS = Path("tiempos")
CARPETA_SUBTITULOS = Path("subtitulos")
PALABRAS_POR_BLOQUE = 3


def duracion_wav(ruta):
    with wave.open(str(ruta), "rb") as archivo:
        return archivo.getnframes() / archivo.getframerate()


def alinear(palabras_guion, palabras_whisper, duracion):
    """Le asigna a cada palabra del guion un (inicio, fin) usando los tiempos de Whisper."""
    a = [normalizar(p) for p in palabras_guion]
    b = [normalizar(p["palabra"]) for p in palabras_whisper]
    tiempos = [None] * len(a)

    comparador = SequenceMatcher(None, a, b, autojunk=False)
    for tipo, i1, i2, j1, j2 in comparador.get_opcodes():
        if tipo == "equal":
            for k in range(i2 - i1):
                w = palabras_whisper[j1 + k]
                tiempos[i1 + k] = (w["inicio"], w["fin"])
        elif tipo == "replace":
            # Repartimos el tramo de Whisper en partes iguales entre las palabras del guion
            inicio = palabras_whisper[j1]["inicio"]
            fin = palabras_whisper[j2 - 1]["fin"]
            paso = (fin - inicio) / (i2 - i1)
            for k in range(i2 - i1):
                tiempos[i1 + k] = (inicio + k * paso, inicio + (k + 1) * paso)
        # "delete" = palabras del guion que Whisper no escuchó: quedan en None
        # "insert" = palabras que Whisper escuchó de más: las ignoramos

    # Rellenamos los huecos (None) repartiendo el espacio libre entre sus vecinos
    i = 0
    while i < len(tiempos):
        if tiempos[i] is not None:
            i += 1
            continue
        j = i
        while j < len(tiempos) and tiempos[j] is None:
            j += 1
        desde = tiempos[i - 1][1] if i > 0 else 0.0
        hasta = tiempos[j][0] if j < len(tiempos) else duracion
        paso = (hasta - desde) / (j - i)
        for k in range(i, j):
            tiempos[k] = (desde + (k - i) * paso, desde + (k - i + 1) * paso)
        i = j

    return tiempos


def armar_bloques(guion, tiempos, duracion):
    """Agrupa las palabras en bloques de hasta N, sin cruzar el final de una línea del guion.
    Cada bloque guarda además sus palabras con su propio tiempo, para el resaltado."""
    bloques = []
    indice = 0
    for linea in guion.splitlines():
        palabras = linea.split()
        for inicio_bloque in range(0, len(palabras), PALABRAS_POR_BLOQUE):
            grupo = palabras[inicio_bloque:inicio_bloque + PALABRAS_POR_BLOQUE]
            bloques.append({
                "texto": " ".join(grupo),
                "inicio": round(tiempos[indice][0], 2),
                "palabras": [
                    {"texto": palabra, "inicio": round(tiempos[indice + k][0], 2)}
                    for k, palabra in enumerate(grupo)
                ],
            })
            indice += len(grupo)

    # Cada bloque dura hasta que empieza el siguiente; el último, hasta el final del audio
    for actual, siguiente in zip(bloques, bloques[1:]):
        actual["fin"] = siguiente["inicio"]
    if bloques:
        bloques[-1]["fin"] = round(duracion, 2)

    # Lo mismo con las palabras dentro de cada bloque
    for bloque in bloques:
        palabras = bloque["palabras"]
        for actual, siguiente in zip(palabras, palabras[1:]):
            actual["fin"] = siguiente["inicio"]
        palabras[-1]["fin"] = bloque["fin"]

    return bloques

def main():
    CARPETA_SUBTITULOS.mkdir(exist_ok=True)
    for ruta_tiempos in sorted(CARPETA_TIEMPOS.glob("*.json")):
        nombre = ruta_tiempos.stem
        print(nombre)

        guion = (CARPETA_GUIONES / f"{nombre}.txt").read_text(encoding="utf-8").strip()
        palabras_whisper = json.loads(ruta_tiempos.read_text(encoding="utf-8"))
        duracion = duracion_wav(CARPETA_LIMPIOS / f"{nombre}.wav")

        tiempos = alinear(guion.split(), palabras_whisper, duracion)
        bloques = armar_bloques(guion, tiempos, duracion)

        salida = CARPETA_SUBTITULOS / f"{nombre}.json"
        salida.write_text(json.dumps(bloques, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {len(bloques)} bloques guardados en {salida}")


if __name__ == "__main__":
    main()