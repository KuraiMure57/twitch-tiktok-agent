import json
import os
import sys
import time

from google import genai


MODEL = "gemini-3.6-flash"


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {"type": "string"},
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "text": {"type": "string"}
                },
                "required": ["start", "end", "text"]
            }
        }
    },
    "required": ["language", "segments"]
}


def analyze(video_file, input_file, output_file):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("No se encontró GEMINI_API_KEY")

    with open(input_file, "r", encoding="utf-8") as f:
        ai_input = json.load(f)

    client = genai.Client(api_key=api_key)

    print("Subiendo vídeo a Gemini...")

    video = client.files.upload(file=video_file)

    while video.state == "PROCESSING":
        print("Gemini está procesando el vídeo...")
        time.sleep(2)
        video = client.files.get(name=video.name)

    if video.state == "FAILED":
        raise RuntimeError("Gemini no pudo procesar el vídeo")

    print("Vídeo procesado correctamente.")

    prompt = f"""
Analiza este clip de vídeo de Twitch junto con la transcripción.

La transcripción procede de Whisper y puede contener errores.

Tu tarea es:

1. Comprender qué ocurre visualmente en el vídeo.
2. Utilizar el contenido visual para interpretar correctamente la transcripción.
3. Corregir errores evidentes de transcripción.
4. Corregir puntuación.
5. Corregir mayúsculas y minúsculas cuando sea necesario.
6. Interpretar correctamente expresiones de sorpresa, emoción,
   preguntas o exclamaciones cuando el vídeo lo permita.
7. Mantener exactamente los timestamps originales.
8. No inventar palabras.
9. No eliminar segmentos.
10. Mantener el idioma original.
11. Devolver únicamente el JSON solicitado.

Esta es la información obtenida de Whisper:

{json.dumps(ai_input, ensure_ascii=False, indent=2)}

Analiza también el vídeo antes de decidir la corrección.
"""

    print("Enviando vídeo + transcripción a Gemini...")

    interaction = client.interactions.create(
        model=MODEL,
        input=[
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "file",
                "file_id": video.name
            }
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": RESPONSE_SCHEMA
        }
    )

    result = json.loads(interaction.output_text)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Respuesta de Gemini guardada en {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(
            "Uso: python src/gemini_analyzer.py "
            "video.mp4 ai_input.json ai_response.json"
        )

    analyze(sys.argv[1], sys.argv[2], sys.argv[3])
