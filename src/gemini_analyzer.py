import json
import os
import sys
import time

from google import genai


MODEL = "gemini-3.6-flash"


VALID_MOMENT_TYPES = {
    "fail",
    "funny",
    "reaction",
    "surprise",
    "scare",
    "clutch",
    "achievement",
    "rage",
    "interesting",
    "normal",
}


VALID_EMOTIONS = {
    "surprise",
    "disbelief",
    "joy",
    "anger",
    "fear",
    "excitement",
    "frustration",
    "sadness",
    "neutral",
}


def upload_video(client, video_path):
    print("Subiendo vídeo a Gemini...")

    video_file = client.files.upload(
        file=video_path
    )

    while True:
        file_info = client.files.get(
            name=video_file.name
        )

        print(
            "Estado del vídeo:",
            file_info.state.name,
        )

        if file_info.state.name == "ACTIVE":
            return file_info

        if file_info.state.name == "FAILED":
            raise RuntimeError(
                "Gemini no pudo procesar el vídeo."
            )

        time.sleep(2)


def analyze(
    video_path,
    input_path,
    output_path,
):
    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "No se ha encontrado "
            "GEMINI_API_KEY."
        )

    client = genai.Client(
        api_key=api_key
    )

    with open(
        input_path,
        "r",
        encoding="utf-8",
    ) as file:
        ai_input = json.load(file)

    video_file = upload_video(
        client,
        video_path,
    )

    prompt = f"""
Analiza este clip de Twitch.

La transcripción ha sido creada por Whisper
utilizando timestamps por palabra y después
dividida en segmentos cortos.

IMPORTANTE SOBRE LOS SUBTÍTULOS:

Los segmentos proporcionados contienen los
timestamps correctos.

Debes conservarlos EXACTAMENTE.

NO cambies:

* start
* end
* número de segmentos
* orden de segmentos

Solo puedes corregir el campo "text".

Puedes corregir:

* errores evidentes de Whisper;
* palabras mal reconocidas;
* mayúsculas;
* puntuación.

No inventes palabras.

No añadas palabras que no se escuchen.

No elimines segmentos.

La sincronización es prioritaria.

Devuelve exactamente el mismo número de
segmentos.

IMPORTANTE SOBRE EL ANÁLISIS:

"moment_type" DEBE ser exactamente uno de:

{", ".join(sorted(VALID_MOMENT_TYPES))}

No inventes nuevos tipos.

"emotion" DEBE ser exactamente una de:

{", ".join(sorted(VALID_EMOTIONS))}

Para sustos, jumpscares o momentos de miedo
en juegos como Phasmophobia, utiliza:

moment_type = "scare"

y normalmente:

emotion = "fear"

Entrada:

{json.dumps(
    ai_input,
    ensure_ascii=False,
    indent=2
)}

Devuelve únicamente JSON válido:

{{
  "language": "es",
  "segments": [
    {{
      "start": 0.000,
      "end": 1.000,
      "text": "texto corregido"
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
"""

    print(
        "Analizando vídeo con Gemini..."
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
                        "mime_type": video_file.mime_type,
                    },
                ],
            }
        ],
    )

    response_text = interaction.output_text

    if not response_text:
        raise RuntimeError(
            "Gemini no devolvió contenido."
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

        if cleaned.endswith(
            "```"
        ):
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
            "segmentos."
        )

    for original, returned in zip(
        original_segments,
        returned_segments,
    ):
        if (
            float(original["start"])
            != float(returned["start"])
            or
            float(original["end"])
            != float(returned["end"])
        ):
            raise RuntimeError(
                "Gemini modificó timestamps. "
                "Se rechaza la respuesta."
            )

    analysis = result.get(
        "analysis",
        {}
    )

    moment_type = str(
        analysis.get(
            "moment_type",
            ""
        )
    ).lower()

    if moment_type not in VALID_MOMENT_TYPES:
        raise RuntimeError(
            "Gemini devolvió un "
            f"moment_type no permitido: "
            f"{moment_type}"
        )

    emotion = str(
        analysis.get(
            "emotion",
            ""
        )
    ).lower()

    if emotion not in VALID_EMOTIONS:
        raise RuntimeError(
            "Gemini devolvió una "
            f"emotion no permitida: "
            f"{emotion}"
        )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Respuesta guardada en {output_path}"
    )

    print(
        f"Tipo de momento Gemini: "
        f"{moment_type}"
    )

    print(
        f"Emoción Gemini: {emotion}"
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
