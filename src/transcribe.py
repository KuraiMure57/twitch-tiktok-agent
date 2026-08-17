import json
import sys
from pathlib import Path

import whisper

MODEL = "small"

def transcribe_video(video_path: str, output_path: str) -> None:
video = Path(video_path)
output = Path(output_path)

```
if not video.exists():
    raise FileNotFoundError(
        f"No existe el vídeo: {video}"
    )

print("Cargando modelo Whisper...")
model = whisper.load_model(MODEL)

print("Transcribiendo vídeo...")

result = model.transcribe(
    str(video),
    language="es",
    fp16=False,
    word_timestamps=True,
    condition_on_previous_text=False,
    temperature=0,
    verbose=False,
)

words = []

for segment in result.get("segments", []):
    for word in segment.get("words", []):
        text = word.get("word", "").strip()

        if not text:
            continue

        start = word.get("start")
        end = word.get("end")

        if start is None or end is None:
            continue

        start = float(start)
        end = float(end)

        if end <= start:
            continue

        words.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "text": text,
        })

if not words:
    raise RuntimeError(
        "Whisper no devolvió palabras con timestamps."
    )

transcription = {
    "language": result.get("language", "es"),
    "words": words,
}

json_output = output.with_suffix(".json")

with json_output.open("w", encoding="utf-8") as file:
    json.dump(
        transcription,
        file,
        ensure_ascii=False,
        indent=2,
    )

with output.open("w", encoding="utf-8") as file:
    for word in words:
        file.write(
            f"{word['start']:.3f}|"
            f"{word['end']:.3f}|"
            f"{word['text']}\n"
        )

print(f"Transcripción guardada en {output}")
print(f"JSON guardado en {json_output}")
print(f"Palabras detectadas: {len(words)}")
```

if **name** == "**main**":
if len(sys.argv) != 3:
print(
"Uso: python src/transcribe.py "
"<video.mp4> <output.txt>"
)
sys.exit(1)

```
transcribe_video(
    sys.argv[1],
    sys.argv[2],
)
```
