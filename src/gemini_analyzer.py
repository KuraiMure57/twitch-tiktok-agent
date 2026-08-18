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


def analyze_video(
    video_path: str,
    ai_input_path: str,
    output_path: str,
) -> None:

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Falta la variable de entorno GEMINI_API_KEY."
        )

    ai_input = load_json(ai_input_path)

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
                "text": segment.get("text", ""),
            }
        )

    prompt = f"""
Analiza cuidadosamente TODO el vídeo completo que se te proporciona.

El idioma hablado es: {language}.

Esta es una transcripción inicial generada por Whisper:

{json.dumps(
    transcription,
    ensure_ascii=False,
    indent=2,
)}

IMPORTANTE:

La transcripción de Whisper NO es necesariamente correcta ni completa.

Debes revisar el AUDIO REAL del vídeo completo y comparar lo que
realmente se escucha con la transcripción proporcionada.

Tu objetivo es crear una transcripción final fiel al audio.

REGLAS OBLIGATORIAS:

1. Escucha/revisa TODO el audio del vídeo.

2. Si Whisper ha omitido una palabra, frase o intervención que realmente
   se escucha, DEBES añadirla.

3. No asumas que la transcripción de Whisper es completa.

4. No inventes frases que no se escuchen.

5. Mantén los timestamps originales de Whisper cuando sean correctos.

6. No cambies un timestamp existente únicamente porque cambies el texto.

7. Si detectas una frase que Whisper omitió, crea un nuevo segmento con
   el momento aproximado en el que realmente se escucha.

8. Todos los timestamps son relativos al comienzo del vídeo.

9. No recortes el vídeo.

10. No desplaces toda la transcripción.

11. El vídeo completo debe analizarse desde el segundo 0 hasta su
    duración real.

12. Corrige errores evidentes de reconocimiento de voz.

13. Mantén el significado real de lo que dice la persona.

14. Corrige la puntuación.

15. Utiliza preguntas cuando el tono sea realmente interrogativo.

16. Utiliza signos de exclamación cuando el tono de voz indique
    sorpresa, miedo, susto, grito o emoción.

17. Por ejemplo, si la persona dice "La Llorona" con sorpresa o miedo,
    debe escribirse:

    "¡La Llorona!"

18. No añadas signos de exclamación automáticamente.

19. No conviertas frases en otras distintas simplemente para hacerlas
    sonar más naturales.

20. No resumas.

21. No elimines contenido hablado.

22. No agrupes frases diferentes si eso perjudica la sincronización.

23. No dividas una frase innecesariamente.

24. El resultado debe representar lo que realmente se escucha.

CASO ESPECIAL:

Si el audio contiene algo parecido a:

"Abajo no hay ruidos. Me salen arriba los ruidos."

pero Whisper solamente proporciona:

"Me salen arriba los ruidos."

DEBES detectar la primera frase en el audio y añadirla.

No debes limitarte a corregir los segmentos existentes.

FORMATO DE RESPUESTA:

Devuelve ÚNICAMENTE JSON válido.

No escribas explicaciones.

No escribas Markdown.

No utilices bloques ```json.

Formato:

{{
  "language": "{language}",
  "segments": [
    {{
      "start": 0.0,
      "end": 1.0,
      "text": "Texto"
    }}
  ]
}}

Cada segmento debe contener exactamente:

- start
- end
- text

Los timestamps deben ser números.

Ordena todos los segmentos cronológicamente.

No incluyas campos adicionales.
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
        "Gemini revisará el vídeo completo "
        "y comprobará la transcripción de Whisper."
    )
    print("")

    response = requests.post(
        GEMINI_API_URL,
        params={
            "key": api_key,
        },
        headers={
            "Content-Type": "application/json",
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

    if "segments" not in result:
        raise RuntimeError(
            "La respuesta de Gemini no contiene 'segments'."
        )

    if not isinstance(
        result["segments"],
        list,
    ):
        raise RuntimeError(
            "'segments' debe ser una lista."
        )

    validated_segments = []

    for index, segment in enumerate(
        result["segments"],
        start=1,
    ):

        if not isinstance(
            segment,
            dict,
        ):
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

        start = float(
            segment["start"]
        )

        end = float(
            segment["end"]
        )

        text = str(
            segment["text"]
        ).strip()

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

        validated_segments.append(
            {
                "start": start,
                "end": end,
                "text": text,
            }
        )

    validated_segments.sort(
        key=lambda segment: (
            segment["start"],
            segment["end"],
        )
    )

    result = {
        "language": result.get(
            "language",
            language,
        ),
        "segments": validated_segments,
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
