import json
import re
import sys
from pathlib import Path

MAX_WORDS = 3
MAX_CHARS = 28
MAX_DURATION = 1.6
MAX_GAP = 0.28

def clean_text(text: str) -> str:
return " ".join(text.split()).strip()

def is_sentence_end(text: str) -> bool:
return bool(
re.search(
r"[.!?¡!]+$",
text.strip(),
)
)

def build_segment(words):
if not words:
return None

```
text = " ".join(
    clean_text(word["text"])
    for word in words
    if clean_text(word["text"])
).strip()

if not text:
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
    "text": text,
}
```

def must_split(current, next_word):
if not current:
return False

```
current_text = " ".join(
    word["text"] for word in current
)

proposed_text = (
    current_text
    + " "
    + next_word["text"]
).strip()

start = float(current[0]["start"])
end = float(current[-1]["end"])

duration = end - start

gap = (
    float(next_word["start"])
    - end
)

if len(current) >= MAX_WORDS:
    return True

if len(proposed_text) > MAX_CHARS:
    return True

if duration >= MAX_DURATION:
    return True

if gap >= MAX_GAP:
    return True

if is_sentence_end(
    current[-1]["text"]
):
    return True

return False
```

def format_transcription(
input_path: str,
output_path: str,
) -> None:

```
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
current = []

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

    if not current:
        current.append(word)
        continue

    if must_split(
        current,
        word,
    ):
        segment = build_segment(
            current
        )

        if segment:
            segments.append(segment)

        current = [word]
    else:
        current.append(word)

final_segment = build_segment(
    current
)

if final_segment:
    segments.append(final_segment)

if not segments:
    raise RuntimeError(
        "No se pudieron crear subtítulos."
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
    f"Segmentos de subtítulos: "
    f"{len(segments)}"
)
```

if **name** == "**main**":
if len(sys.argv) != 3:
print(
"Uso: python src/subtitle_formatter.py "
"<input.json> <output.json>"
)
sys.exit(1)

```
format_transcription(
    sys.argv[1],
    sys.argv[2],
)
