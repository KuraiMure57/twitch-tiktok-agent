import json
import sys
from pathlib import Path


def clean_text(text: str) -> str:
    return " ".join(
        text.replace("\n", " ").split()
    ).strip()


def correct_subtitles(input_path: str, output_path: str) -> None:
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {input_file}"
        )

    with input_file.open("r", encoding="utf-8") as file:
        subtitles = json.load(file)

    if not isinstance(subtitles, list):
        raise ValueError(
            "El archivo de subtítulos debe contener una lista."
        )

    corrected = []

    for subtitle in subtitles:
        if not isinstance(subtitle, dict):
            continue

        text = clean_text(
            str(subtitle.get("text", ""))
        )

        if not text:
            continue

        start = float(subtitle["start"])
        end = float(subtitle["end"])

        if end <= start:
            continue

        corrected.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "text": text,
            }
        )

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            corrected,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Subtítulos corregidos: {len(corrected)}"
    )
    print(
        f"Archivo guardado en: {output_file}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Uso: python src/subtitle_corrector.py "
            "<input.json> <output.json>"
        )
        sys.exit(1)

    correct_subtitles(
        sys.argv[1],
        sys.argv[2],
    )
