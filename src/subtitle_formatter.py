import json
import sys
from pathlib import Path


MAX_GAP = 0.8


def clean_text(text: str) -> str:
    return " ".join(text.split()).strip()


def format_transcription(input_path: str, output_path: str) -> None:
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
        raise ValueError("No se encontraron palabras.")

    segments = []

    current_start = words[0]["start"]
    current_end = words[0]["end"]
    current_text = [clean_text(words[0]["text"])]

    for word in words[1:]:
        text = clean_text(word["text"])

        if not text:
            continue

        gap = word["start"] - current_end

        if gap <= MAX_GAP:
            current_text.append(text)
            current_end = word["end"]
        else:
            segments.append({
                "start": round(current_start, 3),
                "end": round(current_end, 3),
                "text": " ".join(current_text)
            })

            current_start = word["start"]
            current_end = word["end"]
            current_text = [text]

    segments.append({
        "start": round(current_start, 3),
        "end": round(current_end, 3),
        "text": " ".join(current_text)
    })

    result = {
        "language": data.get("language", "es"),
        "segments": segments
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
