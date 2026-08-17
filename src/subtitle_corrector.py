import json
import sys
from pathlib import Path


def clean_text(text: str) -> str:
    return " ".join(
        text.replace("\n", " ").split()
    ).strip()


def correct_subtitles(
    input_path: str,
    output_path: str,
) -> None:
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {input_file}"
        )

    with input_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "El archivo de subtítulos debe ser un objeto JSON."
        )

    segments = data.get("segments", [])

    if not isinstance(segments, list):
        raise ValueError(
            "'segments' debe ser una lista."
        )

    corrected_segments = []

    for index, subtitle in enumerate(segments):
        if not isinstance(subtitle, dict):
            raise ValueError(
                f"El segmento {index} no es un objeto."
            )

        if "start" not in subtitle:
            raise ValueError(
                f"Falta start en el segmento {index}."
            )

        if "end" not in subtitle:
            raise ValueError(
                f"Falta end en el segmento {index}."
            )

        start = float(subtitle["start"])
        end = float(subtitle["end"])

        if end <= start:
            raise ValueError(
                f"Timestamps inválidos en segmento {index}."
            )

        text = clean_text(
            str(subtitle.get("text", ""))
        )

        if not text:
            continue

        corrected_segments.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "text": text,
            }
        )

    result = {
        "language": data.get("language", "es"),
        "segments": corrected_segments,
    }

    with output_file.open(
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
        f"Subtítulos corregidos: "
        f"{len(corrected_segments)}"
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
