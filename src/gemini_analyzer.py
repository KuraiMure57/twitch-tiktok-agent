import json
import os
import sys

from google import genai


MODEL = "gemini-3.6-flash"


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {
            "type": "string"
        },
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "number"
                    },
                    "end": {
                        "type": "number"
                    },
                    "text": {
                        "type": "string"
                    }
                },
                "required": [
                    "start",
                    "end",
                    "text"
                ]
            }
        }
    },
    "required": [
        "language",
        "segments"
    ]
}


def analyze(input_file, output_file):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("No se encontró GEMINI_API_KEY")

    with open(input_file, "r", encoding="utf-8") as f:
        ai_input = json.load(f)

    prompt = f"""
Eres el sistema de corrección de subtítulos de un agente que convierte
clips de Twitch en vídeos cortos para TikTok.

Recibirás una transcripción generada automáticamente por Whisper.

Tu tarea es:

1. Corregir errores evidentes de transcripción.
2. Corregir puntuación.
3. Corregir mayúsculas y minúsculas cuando sea necesario.
4. Interpretar correctamente expresiones de sorpresa, emoción,
   preguntas o exclamaciones cuando el contexto lo permita.
5. Mantener exactamente los timestamps originales.
6. No inventar palabras que no estén justificadas por la transcripción.
7. No eliminar segmentos.
8. No añadir información que no aparezca en la transcripción.
9. Mantener el idioma original.
10. Devolver únicamente el JSON solicitado.

Ejemplo:

Transcripción:
"En serio?"

Si por el contexto lingüístico es claramente una reacción de sorpresa,
puedes convertirla en:

"¡¿EN SERIO?!"

Pero no debes modificar arbitrariamente el significado.

Esta es la entrada:

{json.dumps(ai_input, ensure_ascii=False, indent=2)}
"""

    client = genai.Client(api_key=api_key)

    interaction = client.interactions.create(
        model=MODEL,
        input=prompt,
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
    if len(sys.argv) != 3:
        raise SystemExit(
            "Uso: python src/gemini_analyzer.py "
            "ai_input.json ai_response.json"
        )

    analyze(sys.argv[1], sys.argv[2])
