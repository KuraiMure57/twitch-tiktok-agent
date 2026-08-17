import json
import os
import sys
import time

from google import genai


MODEL = "gemini-3.6-flash"


def upload_video(client, video_path):
    print("Subiendo vídeo a Gemini...")

    video_file = client.files.upload(
        file=video_path
    )

    while True:
        print(
            "Gemini está procesando el vídeo..."
        )

        file_info = client.files.get(
            name=video_file.name
        )

        if file_info.state.name == "ACTIVE":
            print(
                "Vídeo procesado correctamente."
            )
            return file_info

        if file_info.state.name == "FAILED":
            raise RuntimeError(
                "Gemini no pudo procesar el vídeo."
            )

        time.sleep(2)


def analyze(
    video_path: str,
    input_path: str,
    output_path: str,
):
    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "No se ha encontrado la variable "
            "GEMINI_API_KEY."
        )

    client = genai.Client(
        api_key=api_key
    )

    with open(
        input_path,
        "r",
        encoding="utf-8",
    ) as f:
        ai_input = json.load(f)

    video_file = upload_video(
        client,
        video_path,
    )

    prompt = f"""
Analiza este clip de Twitch junto con la
transcripción proporcionada.

La transcripción procede de Whisper.

IMPORTANTE:

Los timestamps de la transcripción son los
timestamps originales obtenidos por Whisper.

DEBES CONSERVARLOS EXACTAMENTE.

NO puedes:
- cambiar start;
- cambiar end;
- unir segmentos;
- dividir segmentos;
- crear nuevos timestamps;
- eliminar segmentos;
- desplazar el texto a otro momento.

Tu trabajo principal es corregir el texto.

Puedes:
- corregir errores evidentes de Whisper;
- corregir mayúsculas;
- corregir puntuación;
- corregir palabras mal reconocidas cuando
  el audio lo confirme.

NO puedes inventar palabras.

NO puedes cambiar el significado de lo dicho.

Los subtítulos deben seguir exactamente lo
que se escucha en el audio.

La respuesta debe mantener EXACTAMENTE el
mismo número de segmentos y los mismos
timestamps que aparecen en la entrada.

También analiza el potencial del clip.

Devuelve exactamente esta estructura:

{{
  "language": "es",
  "segments": [
    {{
      "start": 0.000,
      "end": 1.000,
      "text": "Texto corregido."
    }}
  ],
  "analysis": {{
    "moment_type": "funny",
    "emotion": "surprise",
    "description": "Descripción breve.",
    "is_interesting": true,
    "clip_start": 0.0,
    "clip_end": 0.0,
    "hook": "Hook breve.",
    "title": "Título breve."
  }}
}}

TIPOS DE MOMENTO:

- fail
- funny
- reaction
- surprise
- clutch
- achievement
- rage
- interesting
- normal

EMOCIONES:

- surprise
- disbelief
- joy
- anger
- fear
- excitement
- frustration
- sadness
- neutral

REGLAS DE SEGMENTOS:

1. Conserva exactamente todos los segmentos.
2. Conserva exactamente cada start.
3. Conserva exactamente cada end.
4. Modifica únicamente text.
5. No inventes palabras.
6. No elimines palabras salvo que sean
   claramente un error de Whisper.
7. Mantén el idioma original.
8. Prioriza que el texto coincida con
   lo que realmente se escucha.

Devuelve ÚNICAMENTE JSON válido.

Información de Whisper:

{json.dumps(
    ai_input,
    ensure_ascii=False,
    indent=2
)}

Analiza primero el vídeo y el audio y después
corrige exclusivamente el texto.
"""

    print(
        "Enviando vídeo + transcripción "
        "a Gemini..."
    )

    interaction = client.interactions.create(
        model=MODEL,
        input=[
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "video",
                        "uri": video_file.uri,
                        "mime_type": (
                            video_file.mime_type
                        ),
                    },
                ],
            }
        ],
    )

    response_text = interaction.output_text

    if not response_text:
        raise RuntimeError(
            "Gemini no devolvió contenido "
            "de texto."
        )

    try:
        result = json.loads(
            response_text
        )

    except json.JSONDecodeError:
        cleaned = response_text.strip()

        if cleaned.startswith(
            "```json"
        ):
            cleaned = cleaned[7:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        result = json.loads(
            cleaned.strip()
        )

    original_segments = ai_input.get(
        "segments",
        []
    )

    returned_segments = result.get(
        "segments",
        []
    )

    if len(original_segments) != len(
        returned_segments
    ):
        raise RuntimeError(
            "Gemini modificó el número de "
            "segmentos. Se rechaza la respuesta."
        )

    for original, returned in zip(
        original_segments,
        returned_segments,
    ):
        original_start = float(
            original["start"]
        )
        original_end = float(
            original["end"]
        )

        returned_start = float(
            returned["start"]
        )
        returned_end = float(
            returned["end"]
        )

        if (
            abs(
                original_start
                - returned_start
            )
            > 0.001
            or
            abs(
                original_end
                - returned_end
            )
            > 0.001
        ):
            raise RuntimeError(
                "Gemini modificó timestamps. "
                "Se rechaza la respuesta."
            )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Respuesta de Gemini guardada "
        f"en {output_path}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Uso: python src/gemini_analyzer.py "
            "video.mp4 ai_input.json "
            "ai_response.json"
        )
        sys.exit(1)

    analyze(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
    )
