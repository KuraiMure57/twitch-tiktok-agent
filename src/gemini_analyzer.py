import json
import os
import sys
import time
from pathlib import Path

import requests


GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-3.6-flash:generateContent"
)

MAX_RETRIES = 5

RETRY_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


def load_json(path: str):
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


def get_video_duration(video_path: str) -> float:
    import subprocess

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return float(result.stdout.strip())


def build_prompt(
    whisper_data: dict,
    video_duration: float,
) -> str:

    segments = whisper_data.get(
        "segments",
        [],
    )

    transcript_lines = []

    for segment in segments:
        start = segment.get("start")
        end = segment.get("end")
        text = segment.get("text", "").strip()

        if start is None or end is None or not text:
            continue

        transcript_lines.append(
            f"[{start:.2f}s - {end:.2f}s] {text}"
        )

    transcript = "\n".join(
        transcript_lines
    )

    return f"""
Analiza TODO el vídeo que se te ha proporcionado.

Duración del vídeo:
{video_duration:.3f} segundos.

La transcripción siguiente procede de Whisper:

==============================
TRANSCRIPCIÓN DE WHISPER
==============================

{transcript}

==============================
OBJETIVO
==============================

Debes comprobar la transcripción escuchando directamente
el AUDIO del vídeo.

Whisper puede haber cometido errores.

MUY IMPORTANTE:

1. Escucha TODO el audio del vídeo.

2. No te limites a comparar visualmente el texto de Whisper.

3. Si Whisper ha omitido una frase, palabra o expresión que
realmente se escucha en el audio, debes añadirla.

4. Si Whisper ha escrito una palabra incorrectamente,
corrígela.

5. Conserva los timestamps originales siempre que correspondan
a una frase existente.

6. Para texto nuevo que Whisper haya omitido, crea timestamps
aproximados basándote en el momento exacto en el que se escucha.

7. NO cambies los timestamps de segmentos que ya sean correctos.

8. No elimines contenido hablado.

9. Mantén el idioma español.

10. Conserva expresiones coloquiales, tacos, exclamaciones
y la forma natural de hablar.

11. Añade signos de puntuación adecuados.

12. Las exclamaciones y expresiones de sorpresa deben reflejar
el tono hablado cuando sea evidente.

Por ejemplo:

"La Llorona"

si se dice con sorpresa o susto debe escribirse:

"¡La Llorona!"

No debes inventar signos si no corresponden al audio.

13. Si una frase está dividida en varios segmentos de Whisper,
puedes mantener los segmentos separados.

14. Si detectas una frase que Whisper NO detectó en absoluto,
debes añadirla.

==============================
FORMATO OBLIGATORIO
==============================

Devuelve EXCLUSIVAMENTE JSON válido.

La estructura debe ser:

{{
  "analysis": {{
    "corrections_made": true,
    "missing_segments_added": true,
    "notes": "Descripción breve de las correcciones realizadas."
  }},
  "language": "es",
  "segments": [
    {{
      "start": 1.56,
      "end": 2.08,
      "text": "texto"
    }}
  ]
}}

No incluyas markdown.

No incluyas ```json.

No incluyas explicaciones fuera del JSON.

Los timestamps deben estar expresados en segundos.

Los segmentos deben estar ordenados cronológicamente.

El primer segmento debe empezar en el momento correspondiente
del audio y el último debe terminar en el momento correspondiente
del audio.
""".strip()


def extract_json(text: str) -> dict:

    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            raise ValueError(
                "Gemini no devolvió un JSON válido."
            )

        return json.loads(
            text[start:end + 1]
        )


def validate_basic_structure(data: dict) -> None:

    if not isinstance(data, dict):
        raise ValueError(
            "La respuesta de Gemini no es un objeto JSON."
        )

    if "segments" not in data:
        raise ValueError(
            "La respuesta de Gemini no contiene 'segments'."
        )

    if not isinstance(
        data["segments"],
        list,
    ):
        raise ValueError(
            "'segments' debe ser una lista."
        )

    if "analysis" not in data:
        data["analysis"] = {
            "corrections_made": True,
            "missing_segments_added": True,
            "notes": (
                "Gemini no devolvió el bloque analysis; "
                "se añadió automáticamente."
            ),
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
            "Falta la variable GEMINI_API_KEY."
        )

    if not Path(video_path).exists():
        raise FileNotFoundError(
            f"No existe el vídeo: {video_path}"
        )

    whisper_data = load_json(
        ai_input_path
    )

    video_duration = get_video_duration(
        video_path
    )

    print(
        "=============================="
    )

    print(
        "ANALIZANDO AUDIO CON GEMINI"
    )

    print(
        "=============================="
    )

    print(
        "Gemini revisará TODO el vídeo y "
        "comprobará la transcripción de Whisper."
    )

    print(
        f"Duración del vídeo: "
        f"{video_duration:.3f}s"
    )

    prompt = build_prompt(
        whisper_data,
        video_duration,
    )

    with open(
        video_path,
        "rb",
    ) as video_file:

        video_bytes = video_file.read()

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
                            "data": (
                                __import__(
                                    "base64"
                                ).b64encode(
                                    video_bytes
                                ).decode(
                                    "utf-8"
                                )
                            ),
                        },
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    headers = {
        "Content-Type": "application/json"
    }

    params = {
        "key": api_key
    }

    response = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        print(
            ""
        )

        print(
            f"Intento Gemini "
            f"{attempt}/{MAX_RETRIES}"
        )

        try:

            response = requests.post(
                GEMINI_API_URL,
                params=params,
                headers=headers,
                json=payload,
                timeout=300,
            )

        except requests.RequestException as error:

            print(
                "Error de conexión con Gemini:"
            )

            print(error)

            if attempt >= MAX_RETRIES:
                raise

            wait_time = 15 * attempt

            print(
                f"Reintentando en "
                f"{wait_time} segundos..."
            )

            time.sleep(
                wait_time
            )

            continue

        print(
            f"Gemini HTTP: "
            f"{response.status_code}"
        )

        if response.status_code in RETRY_STATUS_CODES:

            print(
                "Gemini ha devuelto un error "
                "temporal."
            )

            try:
                print(
                    json.dumps(
                        response.json(),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            except ValueError:
                print(
                    response.text
                )

            if attempt >= MAX_RETRIES:

                print(
                    "Se agotaron todos los "
                    "intentos de Gemini."
                )

                response.raise_for_status()

            wait_time = 20 * attempt

            print(
                f"Esperando {wait_time} segundos "
                "antes del siguiente intento..."
            )

            time.sleep(
                wait_time
            )

            continue

        if response.status_code != 200:

            print(
                "Respuesta de Gemini:"
            )

            try:
                print(
                    json.dumps(
                        response.json(),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            except ValueError:
                print(
                    response.text
                )

            response.raise_for_status()

        break

    if response is None:
        raise RuntimeError(
            "Gemini no devolvió ninguna respuesta."
        )

    try:

        response_data = response.json()

    except ValueError:

        print(
            "Gemini no devolvió JSON HTTP válido."
        )

        print(
            response.text
        )

        raise

    try:

        candidates = response_data[
            "candidates"
        ]

        if not candidates:
            raise ValueError(
                "Gemini no devolvió candidates."
            )

        parts = candidates[0][
            "content"
        ][
            "parts"
        ]

        if not parts:
            raise ValueError(
                "Gemini no devolvió contenido."
            )

        generated_text = parts[0].get(
            "text",
            ""
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as error:

        print(
            "Respuesta inesperada de Gemini:"
        )

        print(
            json.dumps(
                response_data,
                ensure_ascii=False,
                indent=2,
            )
        )

        raise ValueError(
            "No se pudo extraer el texto "
            "generado por Gemini."
        ) from error

    if not generated_text.strip():

        raise ValueError(
            "Gemini devolvió una respuesta vacía."
        )

    result = extract_json(
        generated_text
    )

    validate_basic_structure(
        result
    )

    segments = result.get(
        "segments",
        [],
    )

    cleaned_segments = []

    for segment in segments:

        if not isinstance(
            segment,
            dict,
        ):
            continue

        if (
            "start" not in segment
            or "end" not in segment
            or "text" not in segment
        ):
            continue

        start = float(
            segment["start"]
        )

        end = float(
            segment["end"]
        )

        text = str(
            segment["text"]
        ).strip()

        if not text:
            continue

        if start < 0:
            start = 0.0

        if end > video_duration:
            end = video_duration

        if end <= start:
            continue

        cleaned_segments.append(
            {
                "start": round(
                    start,
                    3,
                ),
                "end": round(
                    end,
                    3,
                ),
                "text": text,
            }
        )

    cleaned_segments.sort(
        key=lambda segment:
        segment["start"]
    )

    result["segments"] = (
        cleaned_segments
    )

    if "language" not in result:
        result["language"] = (
            whisper_data.get(
                "language",
                "es",
            )
        )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as output_file:

        json.dump(
            result,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        ""
    )

    print(
        "=============================="
    )

    print(
        "GEMINI COMPLETADO"
    )

    print(
        "=============================="
    )

    print(
        f"Segmentos finales: "
        f"{len(cleaned_segments)}"
    )

    print(
        f"Resultado guardado en: "
        f"{output_path}"
    )


if __name__ == "__main__":

    if len(sys.argv) != 4:

        print(
            "Uso:"
        )

        print(
            "python src/gemini_analyzer.py "
            "<video.mp4> "
            "<ai_input.json> "
            "<ai_response.json>"
        )

        sys.exit(1)

    analyze_video(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
    )
