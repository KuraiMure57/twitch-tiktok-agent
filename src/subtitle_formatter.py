import json
import sys
from pathlib import Path


MAX_WORDS = 6
MAX_DURATION = 2.5
MAX_GAP = 0.45


def clean_text(text: str) -> str:
    return " ".join(text.split()).strip()


def should_break(
    current_words,
    current_start,
    current_end,
    next_word
) -> bool:

    next_text = clean_text(next_word["text"])

    if not next_text:
        return False

    word_count = len(current_words)

    if word_count >= MAX_WORDS:
        return True

    current_duration = current_end - current_start

    if current_duration >= MAX_DURATION:
        return True

    gap = next_word["start"] - current_end

    if gap >= MAX_GAP:
        return True

    if current_words:
        last_word = current_words[-1]

        if last_word.endswith((".", "!", "?", "…")):
            return True

    return False


def format_transcription(
    input_path: str,
    output_path: str
) -> None:

    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {input_file}"
        )

    with input_file.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    words = data.get("words", [])

    if not words:
        raise ValueError(
            "No se encontraron palabras."
        )

    segments = []

    current_start = words[0]["start"]
    current_end = words[0]["end"]
    current_words = [
        clean_text(words[0]["text"])
    ]

    for word in words[1:]:

        text = clean_text(word["text"])

        if not text:
            continue

        if should_break(
            current_words,
            current_start,
            current_end,
            word
        ):
            segments.append({
                "start": round(
                    current_start,
                    3
                ),
                "end": round(
                    current_end,
                    3
                ),
                "text": " ".join(
                    current_words
                )
            })

            current_start = word["start"]
            current_end = word["end"]

            current_words = [text]

        else:
            current_words.append(text)
            current_end = word["end"]

    if current_words:
        segments.append({
            "start": round(
                current_start,
                3
            ),
            "end": round(
                current_end,
                3
            ),
            "text": " ".join(
                current_words
            )
        })

    result = {
        "language": data.get(
            "language",
            "es"
        ),
        "segments": segments
    }

    with output_file.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"Segmentos generados: "
        f"{len(segments)}"
    )

    for index, segment in enumerate(
        segments,
        start=1
    ):
        print(
            f"{index}: "
            f"{segment['start']:.3f} → "
            f"{segment['end']:.3f} | "
            f"{segment['text']}"
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
