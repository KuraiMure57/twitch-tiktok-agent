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
        },
        "analysis": {
            "type": "object",
            "properties": {
                "moment_type": {"type": "string"},
                "emotion": {"type": "string"},
                "description": {"type": "string"},
                "is_interesting": {"type": "boolean"}
            },
            "required": [
                "moment_type",
                "emotion",
                "description",
                "is_interesting"
            ]
        }
    },
    "required": ["language", "segments", "analysis"]
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
Analiza este clip de vídeo de Twitch junto con su transcripción.

La transcripción procede de Whisper y puede contener errores.

Debes realizar DOS tareas:

1. CORREGIR LA TRANSCRIPCIÓN

Corrige errores evidentes de transcripción, puntuación,
mayúsculas/minúsculas y expresión emocional.

Una frase puede estar formulada como una pregunta pero ser
realmente una reacción de sorpresa, incredulidad, enfado, etc.

Por ejemplo:

"En serio?"

si se pronuncia como una reacción de sorpresa puede convertirse en:

"¡¿EN SERIO?!"

Utiliza el audio, el vídeo y el contexto para decidirlo.

No inventes palabras y mantén exactamente los timestamps originales.

2. ANALIZAR EL MOMENTO DEL VÍDEO

Determina qué está ocurriendo en el clip.

Clasifica el momento utilizando una descripción breve en
"moment_type", por ejemplo:

- reaction
- gameplay
- funny
- surprising
- fail
- achievement
- intense
- emotional
- conversation
- other

Indica la emoción principal del momento en "emotion".

Explica brevemente qué ocurre en "description".

Indica si consideras que el momento es interesante para
un posible clip corto en "is_interesting".

IMPORTANTE:

No determines si algo es interesante únicamente por la transcripción.
Utiliza también lo que ocurre visualmente en el vídeo.

Reglas:

- Mantén el idioma original.
- Mantén exactamente los timestamps.
- No elimines segmentos.
- No inventes palabras.
- Devuelve únicamente JSON válido.

Información proporcionada:

{json.dumps(ai_input, ensure_ascii=False, indent=2)}

Analiza primero el vídeo y después genera la respuesta.
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
