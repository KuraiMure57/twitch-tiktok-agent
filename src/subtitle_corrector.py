import json
import sys
from pathlib import Path

def clean_text(text: str) -> str:
return " ".join(
text.split()
).strip()

def correct_subtitles(
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

corrected_segments = []

for segment in data.get(
    "segments",
    [],
):

    start = float(
        segment["start"]
    )

    end = float(
        segment["end"]
    )

    text = clean_text(
        segment.get("text", "")
    )

    corrected_segments.append({
        "start": start,
        "end": end,
        "original_text": text,
        "text": text,
    })

result = {
    "language": data.get(
        "language",
        "es",
    ),
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
```

if **name** == "**main**":
if len(sys.argv) != 3:
print(
"Uso: python src/subtitle_corrector.py "
"<input.json> <output.json>"
)
sys.exit(1)

```
correct_subtitles(
    sys.argv[1],
    sys.argv[2],
)
