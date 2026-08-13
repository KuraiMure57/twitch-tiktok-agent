import json
import sys
from pathlib import Path


def format_text(text: str) -> str:
    """
    Preparación básica del texto para subtítulos.

    De momento no intenta interpretar el contexto.
    La corrección inteligente se añadirá posteriormente.
    """

    text = " ".join(text.split()).strip()

    if not text:
        return ""

    return text


def format_transcription(input_path: str, output_path: str) -> None:
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {input_file}"
        )

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    formatted_segments = []

    for word in data.get("words", []):
        text = format_text(word.get("text", ""))

        if not text:
            continue

        formatted_segments.append({
            "start": word["start"],
            "end": word["end"],
            "text": text
        })

    result = {
        "language": data.get("language", "es"),
        "segments": formatted_segments
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Uso: python src/subtitle_formatter.py "
            "<input.json> <output.json>"
        )
        sys.exit(1)

    format_transcription(
        sys.argv[1],
        sys.argv[2]
    )
