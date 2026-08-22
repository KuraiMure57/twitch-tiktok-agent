import base64
import json
import os
import subprocess
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


def get_video_duration(video_path: str) -> float:
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

Duración exacta del vídeo:
{video_duration:.3f} segundos.

La siguiente transcripción procede de Whisper:

==============================
TRANSCRIPCIÓN WHISPER
==============================

{transcript}

==============================
OBJETIVO
==============================

Debes escuchar directamente TODO el audio del vídeo y revisar
la transcripción de Whisper.

Whisper puede haber cometido errores o haber omitido palabras
o frases.

IMPORTANTE:

1. Escucha TODO el audio.

2. No te limites a corregir ortografía.

3. Detecta frases que Whisper haya omitido completamente.

4. Si escuchas una frase que no aparece en Whisper, añádela.

5. Corrige palabras que Whisper haya entendido incorrectamente.

6. Conserva los timestamps originales de Whisper cuando el
segmento sea correcto.

7. NO cambies innecesariamente los timestamps.

8. Si una frase nueva no existe en Whisper, estima sus
timestamps según el momento en que realmente se escucha.

9. Mantén el español.

10. Conserva expresiones coloquiales y tacos.

11. Añade signos de puntuación naturales.

12. Si una frase se dice claramente con sorpresa, miedo,
grito o exclamación, utiliza los signos correspondientes.

13. Identifica también quién está hablando en cada segmento.

Debes distinguir las diferentes voces que aparecen en el vídeo.

El streamer principal es:

"kuraimure"

Si puedes identificar claramente que habla el streamer,
utiliza exactamente:

"kuraimure"

Para otras personas utiliza identificadores consistentes:

"speaker_2"
"speaker_3"
"speaker_4"
"speaker_5"
"speaker_6"

IMPORTANTE:

- La misma voz debe utilizar siempre el mismo identificador.
- No cambies de identificador para una misma persona.
- Si una persona habla varias veces durante el vídeo,
  conserva su identificador.
- No inventes personas que no aparezcan.
- Si solamente existe una voz, todos los segmentos deben
  utilizar "kuraimure".
- Si hay varias voces pero no puedes identificar con certeza
  quién es quién, utiliza speaker_2, speaker_3, etc.
- El campo "speaker" es obligatorio en TODOS los segmentos.

Ejemplo:

{
  "start": 1.56,
  "end": 2.08,
  "text": "¡Mira eso!",
  "speaker": "kuraimure"
}

Otro ejemplo:

{
  "start": 2.10,
  "end": 3.50,
  "text": "¿Pero qué ha pasado?",
  "speaker": "speaker_2"
}

Ejemplo:

La Llorona

si se dice con sorpresa o susto:

¡La Llorona!

13. No inventes contenido que no se escuche.

14. Los segmentos deben estar ordenados cronológicamente.

15. El contenido debe cubrir TODO lo hablado que sea audible.

==============================
FORMATO OBLIGATORIO
==============================

Devuelve EXCLUSIVAMENTE JSON válido.

La estructura OBLIGATORIA es:

{{
  "analysis": {{
    "transcription_reviewed": true,
    "corrections_made": true,
    "missing_segments_added": true,
    "notes": "Descripción breve de las correcciones."
  }},
  "language": "es",
  "segments": [
    {{
      "start": 1.56,
      "end": 2.08,
      "text": "texto"
      "speaker": "kuraimure"
    }}
  ]
}}

IMPORTANTE:

El campo:

analysis.transcription_reviewed

ES OBLIGATORIO.

No omitas ningún campo de analysis.

No incluyas markdown.

No incluyas ```json.

No incluyas explicaciones fuera del JSON.

Los timestamps están expresados en segundos.
""".strip()


def extract_json(text: str) -> dict:

    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].strip().startswith("```"):
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


def normalize_analysis(
    data: dict,
) -> dict:

    analysis = data.get(
        "analysis"
    )

    if not isinstance(
        analysis,
        dict,
    ):
        analysis = {}

    transcription_reviewed = analysis.get(
        "transcription_reviewed"
    )

    if not isinstance(
        transcription_reviewed,
        bool,
    ):
        transcription_reviewed = True

    corrections_made = analysis.get(
        "corrections_made"
    )

    if not isinstance(
        corrections_made,
        bool,
    ):
        corrections_made = True

    missing_segments_added = analysis.get(
        "missing_segments_added"
    )

    if not isinstance(
        missing_segments_added,
        bool,
    ):
        missing_segments_added = True

    notes = analysis.get(
        "notes"
    )

    if not isinstance(
        notes,
        str,
    ):
        notes = (
            "La transcripción fue revisada "
            "directamente contra el audio."
        )

    data["analysis"] = {
        "transcription_reviewed": transcription_reviewed,
        "corrections_made": corrections_made,
        "missing_segments_added": missing_segments_added,
        "notes": notes,
    }

    return data


def normalize_segments(
    data: dict,
    video_duration: float,
) -> dict:

    segments = data.get(
        "segments",
        [],
    )

    if not isinstance(
        segments,
        list,
    ):
        raise ValueError(
            "'segments' debe ser una lista."
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

        try:
            start = float(
                segment["start"]
            )

            end = float(
                segment["end"]
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        text = str(
            segment["text"]
        ).strip()

        if not text:
            continue

        start = max(
            0.0,
            start,
        )

        end = min(
            video_duration,
            end,
        )

        if end <= start:
            continue

        speaker = str(
            segment.get(
                "speaker",
                "kuraimure",
            )
        ).strip()
        
        if not speaker:
            speaker = "kuraimure"
        
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
                "speaker": speaker,
            }
        )

    cleaned_segments.sort(
        key=lambda item: (
            item["start"],
            item["end"],
        )
    )

    data["segments"] = cleaned_segments

    return data


def normalize_response(
    data: dict,
    whisper_data: dict,
    video_duration: float,
) -> dict:

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "La respuesta de Gemini no es un objeto JSON."
        )

    data = normalize_analysis(
        data
    )

    data = normalize_segments(
        data,
        video_duration,
    )

    language = data.get(
        "language"
    )

    if not isinstance(
        language,
        str,
    ) or not language.strip():

        language = whisper_data.get(
            "language",
            "es",
        )

    data["language"] = language

    return data


def call_gemini(
    payload: dict,
    api_key: str,
) -> dict:

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
                "Gemini ha devuelto un error temporal."
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
                response.raise_for_status()

            wait_time = 20 * attempt

            print(
                f"Esperando {wait_time} segundos..."
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
            "Gemini no devolvió respuesta."
        )

    try:
        response_data = response.json()
    except ValueError as error:
        raise ValueError(
            "Gemini no devolvió JSON HTTP válido."
        ) from error

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
            "",
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
            "No se pudo extraer la respuesta "
            "de Gemini."
        ) from error

    if not generated_text.strip():
        raise ValueError(
            "Gemini devolvió una respuesta vacía."
        )

    return extract_json(
        generated_text
    )


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
            "Falta GEMINI_API_KEY."
        )

    video_file = Path(
        video_path
    )

    if not video_file.exists():
        raise FileNotFoundError(
            f"No existe el vídeo: {video_file}"
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

    with video_file.open(
        "rb"
    ) as file:

        video_bytes = file.read()

    encoded_video = base64.b64encode(
        video_bytes
    ).decode(
        "utf-8"
    )

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
                            "data": encoded_video,
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

    result = call_gemini(
        payload,
        api_key,
    )

    result = normalize_response(
        result,
        whisper_data,
        video_duration,
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
        f"{len(result['segments'])}"
    )

    print(
        "analysis.transcription_reviewed: "
        f"{result['analysis']['transcription_reviewed']}"
    )

    print(
        "analysis.corrections_made: "
        f"{result['analysis']['corrections_made']}"
    )

    print(
        "analysis.missing_segments_added: "
        f"{result['analysis']['missing_segments_added']}"
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
