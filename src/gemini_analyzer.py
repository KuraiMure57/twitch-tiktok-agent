import base64
import json
import os
import sys
from pathlib import Path

import requests


GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.6-flash:generateContent"
)


def load_json(path: str) -> dict:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {file_path}"
        )

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_video_as_base64(video_path: str) -> str:
    file_path = Path(video_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"No existe el vídeo: {file_path}"
        )

    with file_path.open("rb") as file:
        return base64.b64encode(
            file.read()
        ).decode("utf-8")


def clean_json_response(text: str) -> dict:
    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    return json.loads(text)


def validate_segments(segments):
    if not isinstance(segments, list):
        raise RuntimeError(
            "'segments' debe ser una lista."
        )

    validated = []

    for index, segment in enumerate(
        segments,
        start=1,
    ):
        if not isinstance(segment, dict):
            raise RuntimeError(
                f"Segmento {index} inválido."
            )

        if "start" not in segment:
            raise RuntimeError(
                f"Segmento {index} no contiene 'start'."
            )

        if "end" not in segment:
            raise RuntimeError(
                f"Segmento {index} no contiene 'end'."
            )

        if "text" not in segment:
            raise RuntimeError(
                f"Segmento {index} no contiene 'text'."
            )

        start = float(segment["start"])
        end = float(segment["end"])
        text = str(segment["text"]).strip()

        if start < 0:
            raise RuntimeError(
                f"Segmento {index}: start negativo."
            )

        if end <= start:
            raise RuntimeError(
                f"Segmento {index}: end <= start."
            )

        if not text:
            raise RuntimeError(
                f"Segmento {index}: texto vacío."
            )

        validated.append(
            {
                "start": start,
                "end": end,
                "text": text,
            }
        )

    validated.sort(
        key=lambda segment: (
            segment["start"],
            segment["end"],
        )
    )

    return validated


def validate_analysis(analysis: dict, video_duration: float) -> dict:
    if not isinstance(analysis, dict):
        raise RuntimeError(
            "'analysis' debe ser un objeto."
        )

    required_fields = [
        "transcription_reviewed",
        "missing_segments_added",
        "timestamps_preserved",
        "moment_type",
        "emotion",
        "description",
        "is_interesting",
        "clip_start",
        "clip_end",
        "hook",
        "title",
    ]

    missing = [
        field
        for field in required_fields
        if field not in analysis
    ]

    if missing:
        raise RuntimeError(
            "Faltan campos en 'analysis': "
            + ", ".join(missing)
        )

    clip_start = float(
        analysis["clip_start"]
    )

    clip_end = float(
        analysis["clip_end"]
    )

    if clip_start < 0:
        clip_start = 0.0

    if clip_end <= clip_start:
        clip_end = video_duration

    if clip_end > video_duration:
        clip_end = video_duration

    if clip_end <= clip_start:
        raise RuntimeError(
            "Los timestamps de análisis no son válidos."
        )

    return {
        "transcription_reviewed": bool(
            analysis["transcription_reviewed"]
        ),
        "missing_segments_added": bool(
            analysis["missing_segments_added"]
        ),
        "timestamps_preserved": bool(
            analysis["timestamps_preserved"]
        ),
        "moment_type": str(
            analysis["moment_type"]
        ).lower().strip(),
        "emotion": str(
            analysis["emotion"]
        ).lower().strip(),
        "description": str(
            analysis["description"]
        ).strip(),
        "is_interesting": bool(
            analysis["is_interesting"]
        ),
        "clip_start": clip_start,
        "clip_end": clip_end,
        "hook": str(
            analysis["hook"]
        ).strip(),
        "title": str(
            analysis["title"]
        ).strip(),
    }


def analyze_video(
    video_path: str,
    ai_input_path: str,
    output_path: str,
) -> None:

    api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "Falta la variable de entorno GEMINI_API_KEY."
        )

    ai_input = load_json(
        ai_input_path
    )

    video_file = Path(video_path)

    video_base64 = load_video_as_base64(
        video_path
    )

    language = ai_input.get(
        "language",
        "es",
    )

    segments = ai_input.get(
        "segments",
        [],
    )

    transcription = []

    for segment in segments:
        transcription.append(
            {
                "start": segment.get("start"),
                "end": segment.get("end"),
                "text": segment.get(
                    "text",
                    "",
                ),
            }
        )

    # ------------------------------------------------------------
    # OBTENER DURACIÓN REAL DEL VÍDEO
    # ------------------------------------------------------------

    import subprocess

    duration_result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    video_duration = float(
        duration_result.stdout.strip()
    )

    prompt = f"""
Analiza cuidadosamente TODO el vídeo completo.

IDIOMA:
{language}

DURACIÓN REAL DEL VÍDEO:
{video_duration:.3f} segundos

IMPORTANTE:

Este vídeo YA ES un clip de Twitch.

NO debes recortarlo.

NO debes decidir que el vídeo final debe durar menos.

El vídeo completo debe conservarse posteriormente.

Tu trabajo principal es revisar la TRANSCRIPCIÓN del audio.

La transcripción inicial procede de Whisper, pero Whisper puede:

- equivocarse en palabras
- interpretar mal frases
- omitir palabras
- omitir frases completas
- confundir sonidos o nombres
- perder pequeñas intervenciones

Por tanto, debes ESCUCHAR Y REVISAR EL AUDIO REAL DEL VÍDEO COMPLETO.

TRANSCRIPCIÓN INICIAL DE WHISPER:

{json.dumps(
    transcription,
    ensure_ascii=False,
    indent=2,
)}

============================================================
REGLAS DE TRANSCRIPCIÓN
============================================================

1. Revisa TODO el audio desde el segundo 0 hasta
   aproximadamente {video_duration:.3f} segundos.

2. No te limites a corregir los segmentos que ya existen.

3. Busca activamente frases que Whisper haya omitido.

4. Si escuchas una frase que Whisper no detectó,
   DEBES añadirla.

5. Ejemplo:

   Audio real:
   "Abajo no hay ruidos. Me salen arriba los ruidos."

   Whisper:
   "Me salen arriba los ruidos."

   Resultado correcto:
   "Abajo no hay ruidos."
   "Me salen arriba los ruidos."

6. Los timestamps de los segmentos existentes deben mantenerse
   cuando correspondan correctamente al audio.

7. Si una frase nueva fue omitida por Whisper,
   crea un segmento nuevo con el timestamp correspondiente
   al momento en que realmente se escucha.

8. NO desplaces todos los timestamps.

9. NO adelantes ni retrases una frase simplemente para
   hacer que quede más bonita.

10. No inventes palabras.

11. No inventes frases.

12. No resumas.

13. No elimines contenido hablado.

14. Mantén el significado exacto de lo que se dice.

15. Corrige errores evidentes de Whisper.

16. Corrige puntuación.

17. Utiliza "¿ ?" cuando realmente sea una pregunta.

18. Utiliza "¡ !" cuando el tono sea de:

   - sorpresa
   - susto
   - miedo
   - emoción
   - grito
   - reacción fuerte

19. Por ejemplo:

   Audio:
   "La Llorona"

   Si se dice con sorpresa o susto:

   "¡La Llorona!"

20. NO pongas exclamaciones automáticamente.
    Deben corresponder al tono.

21. Mantén separados los segmentos cuando eso ayude
    a conservar la sincronización.

22. Puedes crear segmentos adicionales si Whisper
    omitió contenido.

23. Ordena todos los segmentos cronológicamente.

24. Todos los timestamps son relativos al comienzo
    de este vídeo.

25. El último segmento nunca debe superar
    la duración real del vídeo.

============================================================
ANÁLISIS DEL CLIP
============================================================

Además de revisar la transcripción, analiza el contenido
para determinar si el clip es interesante.

Debes devolver:

moment_type:
- fail
- funny
- reaction
- surprise
- clutch
- achievement
- rage
- scare
- interesting
- normal

emotion:
- surprise
- disbelief
- joy
- anger
- fear
- excitement
- frustration
- sadness
- neutral

============================================================
CLIP_START Y CLIP_END
============================================================

IMPORTANTE:

Aunque analices qué parte contiene el momento interesante,
NO significa que debas recortar el vídeo en este proyecto.

El clip_start y clip_end sirven únicamente como METADATOS
del momento destacado.

El vídeo físico NO será recortado.

El vídeo final debe conservar la duración completa de:
{video_duration:.3f} segundos.

Si el momento interesante está aproximadamente entre
los segundos 15 y 22, puedes indicar:

"clip_start": 15.0,
"clip_end": 22.0

pero el vídeo final seguirá teniendo los
{video_duration:.3f} segundos completos.

============================================================
HOOK Y TÍTULO
============================================================

Crea un hook corto y atractivo basado en el momento.

Crea un título corto para TikTok.

============================================================
FORMATO OBLIGATORIO
============================================================

Devuelve ÚNICAMENTE JSON válido.

No Markdown.

No explicaciones fuera del JSON.

La estructura DEBE ser:

{{
  "language": "{language}",
  "segments": [
    {{
      "start": 0.0,
      "end": 1.0,
      "text": "Texto"
    }}
  ],
  "analysis": {{
    "transcription_reviewed": true,
    "missing_segments_added": false,
    "timestamps_preserved": true,
    "moment_type": "reaction",
    "emotion": "surprise",
    "description": "Descripción breve.",
    "is_interesting": true,
    "clip_start": 0.0,
    "clip_end": 10.0,
    "hook": "Hook corto",
    "title": "Título corto"
  }}
}}

REGLAS:

- "segments" debe contener TODOS los segmentos finales.
- "analysis" debe existir siempre.
- "transcription_reviewed" debe ser true.
- "missing_segments_added" debe ser true si añadiste
  segmentos que Whisper no detectó.
- "timestamps_preserved" debe ser true cuando
  hayas conservado los timestamps existentes.
- clip_start y clip_end son METADATOS.
- NO utilices clip_start y clip_end para recortar el vídeo.
- Todos los números deben ser números JSON.
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    },
                    {
                        "inline_data": {
                            "mime_type": "video/mp4",
                            "data": video_base64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    print("")
    print("==============================")
    print("ANALIZANDO AUDIO CON GEMINI")
    print("==============================")
    print(
        "Gemini revisará TODO el vídeo "
        "y comprobará la transcripción de Whisper."
    )
    print(
        f"Duración del vídeo: "
        f"{video_duration:.3f}s"
    )
    print("")

    response = requests.post(
        GEMINI_API_URL,
        params={
            "key": api_key,
        },
        headers={
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=300,
    )

    print(
        f"Gemini HTTP: {response.status_code}"
    )

    if response.status_code != 200:
        print("")
        print("Respuesta de Gemini:")
        print(response.text)
        print("")

        raise RuntimeError(
            "Gemini devolvió un error HTTP."
        )

    try:
        response_data = response.json()

    except ValueError as error:
        print(response.text)

        raise RuntimeError(
            "Gemini no devolvió JSON válido."
        ) from error

    try:
        candidates = response_data["candidates"]

        if not candidates:
            raise RuntimeError(
                "Gemini no devolvió candidatos."
            )

        content = candidates[0]["content"]

        parts = content.get(
            "parts",
            [],
        )

        if not parts:
            raise RuntimeError(
                "Gemini no devolvió contenido."
            )

        text = parts[0].get(
            "text",
            "",
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as error:

        print(
            json.dumps(
                response_data,
                ensure_ascii=False,
                indent=2,
            )
        )

        raise RuntimeError(
            "No se pudo extraer la respuesta de Gemini."
        ) from error

    if not text.strip():
        raise RuntimeError(
            "Gemini devolvió una respuesta vacía."
        )

    try:
        result = clean_json_response(
            text
        )

    except json.JSONDecodeError as error:

        print("")
        print(
            "Respuesta recibida de Gemini:"
        )
        print(text)
        print("")

        raise RuntimeError(
            "Gemini no devolvió un JSON válido."
        ) from error

    if not isinstance(
        result,
        dict,
    ):
        raise RuntimeError(
            "La respuesta de Gemini no es un objeto JSON."
        )

    if "language" not in result:
        raise RuntimeError(
            "Falta 'language'."
        )

    if "segments" not in result:
        raise RuntimeError(
            "Falta 'segments'."
        )

    if "analysis" not in result:
        print("")
        print(
            "ERROR: Gemini no devolvió 'analysis'."
        )
        print("")
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        raise RuntimeError(
            "Gemini no devolvió el bloque 'analysis'."
        )

    validated_segments = validate_segments(
        result["segments"]
    )

    validated_analysis = validate_analysis(
        result["analysis"],
        video_duration,
    )

    result = {
        "language": str(
            result.get(
                "language",
                language,
            )
        ),
        "segments": validated_segments,
        "analysis": validated_analysis,
    }

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

    print("")
    print("==============================")
    print("RESPUESTA DE GEMINI GUARDADA")
    print("==============================")
    print(
        f"Segmentos finales: "
        f"{len(validated_segments)}"
    )
    print(
        "Segmentos omitidos por Whisper "
        "recuperados: "
        f"{validated_analysis['missing_segments_added']}"
    )
    print(
        f"Momento: "
        f"{validated_analysis['clip_start']:.2f}s - "
        f"{validated_analysis['clip_end']:.2f}s"
    )
    print(
        f"Tipo: "
        f"{validated_analysis['moment_type']}"
    )
    print(
        f"Emoción: "
        f"{validated_analysis['emotion']}"
    )
    print(
        f"Interesante: "
        f"{validated_analysis['is_interesting']}"
    )
    print(
        f"Archivo: {output_path}"
    )
    print("")

    for index, segment in enumerate(
        validated_segments,
        start=1,
    ):
        print(
            f"{index:02d}. "
            f"{segment['start']:.2f}s - "
            f"{segment['end']:.2f}s | "
            f"{segment['text']}"
        )

    print("")
    print(
        "Título: "
        f"{validated_analysis['title']}"
    )
    print(
        "Hook: "
        f"{validated_analysis['hook']}"
    )


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Uso: python src/gemini_analyzer.py "
            "<video.mp4> "
            "<ai_input.json> "
            "<ai_response.json>"
        )

        sys.exit(1)

    video_path = sys.argv[1]
    ai_input_path = sys.argv[2]
    output_path = sys.argv[3]

    try:
        analyze_video(
            video_path,
            ai_input_path,
            output_path,
        )

    except Exception as error:
        print("")
        print("==============================")
        print("ERROR EN GEMINI")
        print("==============================")
        print(str(error))
        print("")

        sys.exit(1)


if __name__ == "__main__":
    main()
