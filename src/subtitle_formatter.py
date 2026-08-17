import json
import sys
from pathlib import Path


def clean_text(text: str) -> str:
    return " ".join(text.split()).strip()


def format_subtitles(input_path: str, output_path: str) -> None:
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {input_file}"
        )

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    words = data.get("words", [])

    if not words:
        raise RuntimeError(
            "No se encontraron palabras con timestamps."
        )

    subtitles = []

    current_words = []
    current_start = None
    current_end = None

    max_words = 5
    max_duration = 2.5

    for word in words:
        text = clean_text(word.get("text", ""))

        if not text:
            continue

        start = float(word["start"])
        end = float(word["end"])

        if current_start is None:
            current_start = start

        current_words.append(text)
        current_end = end

        duration = current_end - current_start

        if (
            len(current_words) >= max_words
            or duration >= max_duration
            or text.endswith((".", "!", "?", ","))
        ):
            subtitles.append(
                {
                    "start": round(current_start, 3),
                    "end": round(current_end, 3),
                    "text": " ".join(current_words),
                }
            )

            current_words = []
            current_start = None
            current_end = None

    if current_words and current_start is not None:
        subtitles.append(
            {
                "start": round(current_start, 3),
                "end": round(current_end, 3),
                "text": " ".join(current_words),
            }
        )

    result = {
        "language": data.get("language", "es"),
        "segments": subtitles,
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Subtítulos generados: {len(subtitles)}"
    )
    print(
        f"Archivo guardado en: {output_file}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Uso: python src/subtitle_formatter.py "
            "<input.json> <output.json>"
        )
        sys.exit(1)

    format_subtitles(
        sys.argv[1],
        sys.argv[2],
    )
