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

    while not video.state or video.state.name != "ACTIVE":
        print("Gemini está procesando el vídeo...")
        time.sleep(2)
        video = client.files.get(name=video.name)

        if video.state and video.state.name == "FAILED":
            raise RuntimeError("Gemini no pudo procesar el vídeo")

    print("Vídeo procesado correctamente.")

    prompt = f"""
Analiza este clip de vídeo de Twitch junto con la transcripción.

La transcripción procede de Whisper y puede contener errores.

Tu tarea es corregir la transcripción teniendo en cuenta:
- el audio;
- lo que ocurre visualmente en el vídeo;
- la intención del hablante;
- el tono y la emoción;
- el contexto proporcionado.

IMPORTANTE:

Una frase puede estar gramaticalmente formulada como una pregunta,
pero ser realmente una reacción de sorpresa o incredulidad.

Debes representar correctamente la intención emocional mediante la
puntuación, sin cambiar las palabras que realmente se pronuncian.

Por ejemplo:

"En serio?"

si se pronuncia como una reacción de sorpresa puede convertirse en:

"¡¿EN SERIO?!"

No debes convertir automáticamente todas las preguntas en exclamaciones.
Utiliza el vídeo y el contexto para decidirlo.

Reglas:

1. Comprende qué ocurre visualmente en el vídeo.
2. Utiliza el audio y la transcripción.
3. Corrige errores evidentes de transcripción.
4. Corrige puntuación.
5. Corrige mayúsculas y minúsculas cuando sea necesario.
6. Interpreta correctamente sorpresa, emoción, incredulidad,
   enfado, alegría u otras reacciones cuando sean evidentes.
7. Mantén exactamente los timestamps originales.
8. No inventes palabras.
9. No elimines segmentos.
10. Mantén el idioma original.
11. Devuelve únicamente JSON válido.

Información proporcionada:

{json.dumps(ai_input, ensure_ascii=False, indent=2)}

Analiza primero el vídeo y después decide la corrección.
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
                "type": "video",
                "uri": video.uri,
                "mime_type": video.mime_type
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
