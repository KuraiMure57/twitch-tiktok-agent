import sys
from pathlib import Path


def build_subtitles(input_path: str, output_path: str) -> None:
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(f"No existe el archivo: {input_file}")

    words = []

    with input_file.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            parts = line.split("|", 2)

            if len(parts) != 3:
                continue

            start, end, text = parts

            words.append({
                "start": float(start),
                "end": float(end),
                "text": text.strip()
            })

    if not words:
        raise ValueError("No se encontraron palabras para agrupar.")

    subtitles = []

    current_start = words[0]["start"]
    current_end = words[0]["end"]
    current_text = [words[0]["text"]]

    for word in words[1:]:
        gap = word["start"] - current_end

        # Unimos palabras que están muy próximas.
        if gap <= 0.8:
            current_text.append(word["text"])
            current_end = word["end"]

        else:
            subtitles.append({
                "start": current_start,
                "end": current_end,
                "text": " ".join(current_text)
            })

            current_start = word["start"]
            current_end = word["end"]
            current_text = [word["text"]]

    subtitles.append({
        "start": current_start,
        "end": current_end,
        "text": " ".join(current_text)
    })

    with output_file.open("w", encoding="utf-8") as file:
        for subtitle in subtitles:
            file.write(
                f"{subtitle['start']:.3f}|"
                f"{subtitle['end']:.3f}|"
                f"{subtitle['text']}\n"
            )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Uso: python src/subtitle_builder.py "
            "<words.txt> <subtitles.txt>"
        )
        sys.exit(1)

    build_subtitles(sys.argv[1], sys.argv[2])
