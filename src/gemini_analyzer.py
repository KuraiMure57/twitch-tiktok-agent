import json
import os
import sys
import time

from google import genai


MODEL = "gemini-3.6-flash"


def upload_video(client, video_path):
    print("Subiendo vídeo a Gemini...")

    video_file = client.files.upload(file=video_path)

    while True:
        print("Gemini está procesando el vídeo...")

        file_info = client.files.get(name=video_file.name)

        if file_info.state.name == "ACTIVE":
            print("Vídeo procesado correctamente.")
            return file_info

        if file_info.state.name == "FAILED":
            raise RuntimeError("Gemini no pudo procesar el vídeo.")

        time.sleep(2)


def analyze(video_path, input_path, output_path):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "No se ha encontrado la variable GEMINI_API_KEY."
        )

    client = genai.Client(api_key=api_key)

    with open(input_path, "r", encoding="utf-8") as f:
        ai_input = json.load(f)

    video_file = upload_video(client, video_path)

    prompt = f"""
Analiza este clip de vídeo de Twitch junto con la transcripción.

La transcripción procede de Whisper y puede contener errores.

Tu objetivo es determinar si existe un momento interesante para convertir
este fragmento en un TikTok o Short.

Analiza:

- lo que ocurre visualmente;
- el audio;
- la transcripción;
- la intención del hablante;
- el tono;
- la emoción;
- el contexto del momento;
- si el momento tiene potencial para redes sociales.

IMPORTANTE SOBRE LA TRANSCRIPCIÓN:

Una frase puede estar gramaticalmente formulada como una pregunta,
pero ser realmente una reacción de sorpresa o incredulidad.

Debes representar correctamente la intención emocional mediante la
puntuación, sin cambiar las palabras que realmente se pronuncian.

Por ejemplo:

"En serio?"

si se pronuncia como una reacción de sorpresa puede convertirse en:

"¡¿En serio?!"

No debes convertir automáticamente todas las preguntas en exclamaciones.
Utiliza el audio y el vídeo para decidirlo.

REGLAS DE TRANSCRIPCIÓN:

1. Comprende qué ocurre visualmente.
2. Utiliza el audio y la transcripción.
3. Corrige errores evidentes de transcripción.
4. Corrige la puntuación.
5. Corrige mayúsculas y minúsculas cuando sea necesario.
6. Interpreta correctamente sorpresa, emoción, incredulidad, enfado,
   alegría, miedo, frustración u otras reacciones cuando sean evidentes.
7. Mantén exactamente los timestamps originales de los segmentos.
8. No inventes palabras.
9. No elimines segmentos.
10. Mantén el idioma original.

ANÁLISIS DEL CLIP:

Debes determinar:

- el tipo de momento;
- la emoción principal;
- una descripción breve;
- si es interesante;
- dónde empieza el momento relevante;
- dónde termina el momento relevante;
- un posible hook para captar la atención;
- un posible título.

Los timestamps del clip deben estar dentro del rango del vídeo.

El clip_start debe representar el momento en el que empieza el
acontecimiento relevante.

El clip_end debe representar el momento en el que termina el
acontecimiento relevante.

No inventes timestamps arbitrarios. Utiliza el vídeo para decidirlos.

El hook debe ser breve y pensado para captar la atención del espectador.

El title debe ser breve y adecuado para TikTok/YouTube Shorts.

La respuesta DEBE tener exactamente esta estructura:

{{
  "language": "es",
  "segments": [
    {{
      "start": 0.0,
      "end": 0.0,
      "text": "texto"
    }}
  ],
  "analysis": {{
    "moment_type": "fail",
    "emotion": "surprise",
    "description": "Descripción breve del momento.",
    "is_interesting": true,
    "clip_start": 0.0,
    "clip_end": 0.0,
    "hook": "Texto breve para captar la atención.",
    "title": "Título del clip."
  }}
}}

TIPOS DE MOMENTO POSIBLES:

- fail
- funny
- reaction
- surprise
- clutch
- achievement
- rage
- interesting
- normal

EMOCIONES POSIBLES:

- surprise
- disbelief
- joy
- anger
- fear
- excitement
- frustration
- sadness
- neutral

Devuelve ÚNICAMENTE JSON válido.

Información proporcionada:

{json.dumps(ai_input, ensure_ascii=False, indent=2)}

Analiza primero el vídeo y después decide la corrección y el potencial
del clip.
"""

    print("Enviando vídeo + transcripción a Gemini...")

    interaction = client.interactions.create(
        model=MODEL,
        input=[
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "video",
                        "uri": video_file.uri,
                        "mime_type": video_file.mime_type
                    }
                ]
            }
        ]
    )

    response_text = interaction.output_text

    if not response_text:
        raise RuntimeError(
            "Gemini no devolvió contenido de texto."
        )

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        cleaned = response_text.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        result = json.loads(cleaned.strip())

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Respuesta de Gemini guardada en {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Uso: python src/gemini_analyzer.py "
            "video.mp4 ai_input.json ai_response.json"
        )
        sys.exit(1)

    analyze(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3]
    )
