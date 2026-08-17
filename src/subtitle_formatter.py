import json
import re
import sys
from pathlib import Path


MAX_WORDS = 5
MAX_CHARS = 38
MAX_DURATION = 2.2
MAX_GAP = 0.35


def clean_text(text: str) -> str:
    return " ".join(text.split()).strip()


def is_sentence_end(text: str) -> bool:
    return bool(
        re.search(
            r"[.!?¡!]+$",
            text.strip(),
        )
    )


def should_split(
    current_words,
    next_word,
) -> bool:
    if not current_words:
        return False

    current_text = " ".join(
        word["text"] for word in current_words
    )

    proposed_text = (
        current_text + " " + next_word["text"]
    ).strip()

    start = current_words[0]["start"]
    end = current_words[-1]["end"]

    duration = end - start
    gap = next_word["start"] - end

    if len(current_words) >= MAX_WORDS:
        return True

    if len(proposed_text) > MAX_CHARS:
        return True

    if duration >= MAX_DURATION:
        return True

    if gap > MAX_GAP:
        return True

    if is_sentence_end(current_words[-1]["text"]):
        return True

    return False


def build_segment(words):
    if not words:
        return None

    text_parts = []

    for word in words:
        text = clean_text(word["text"])

        if text:
            text_parts.append(text)

    if not text_parts:
        return None

    return {
        "start": round(
            float(words[0]["start"]),
            3,
        ),
        "end": round(
            float(words[-1]["end"]),
            3,
        ),
        "text": " ".join(text_parts),
    }


def format_transcription(
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

    words = data.get("words", [])

    if not words:
        raise ValueError(
            "No se encontraron palabras."
        )

    segments = []
    current_words = []

    for raw_word in words:
        text = clean_text(
            raw_word.get("text", "")
        )

        if not text:
            continue

        word = {
            "start": float(
                raw_word["start"]
            ),
            "end": float(
                raw_word["end"]
            ),
            "text": text,
        }

        if not current_words:
            current_words.append(word)
            continue

        if should_split(
            current_words,
            word,
        ):
            segment = build_segment(
                current_words
            )

            if segment:
                segments.append(segment)

            current_words = [word]
        else:
            current_words.append(word)

    final_segment = build_segment(
        current_words
    )

    if final_segment:
        segments.append(final_segment)

    if not segments:
        raise ValueError(
            "No se pudieron crear segmentos."
        )

    result = {
        "language": data.get(
            "language",
            "es",
        ),
        "segments": segments,
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
        f"Segmentos creados: {len(segments)}"
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
        sys.argv[2],
    )
