import json
import sys
from pathlib import Path

import whisper


def transcribe_video(video_path: str, output_path: str) -> None:
    video = Path(video_path)
    output = Path(output_path)

    if not video.exists():
        raise FileNotFoundError(f"No existe el vídeo: {video}")

    print("Cargando modelo Whisper...")
    model = whisper.load_model("small")

    print("Transcribiendo vídeo...")

    result = model.transcribe(
        str(video),
        language="es",
        fp16=False,
        word_timestamps=True,
        condition_on_previous_text=False
    )

    words = []

    for segment in result["segments"]:
        for word in segment.get("words", []):
            text = word["word"].strip()

            if text:
                words.append({
                    "start": round(word["start"], 3),
                    "end": round(word["end"], 3),
                    "text": text
                })

    transcription = {
        "language": "es",
        "words": words
    }

    json_output = output.with_suffix(".json")

    with json_output.open("w", encoding="utf-8") as file:
        json.dump(
            transcription,
            file,
            ensure_ascii=False,
            indent=2
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


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Uso: python src/transcribe.py "
            "<video.mp4> <output.txt>"
        )
        sys.exit(1)

    transcribe_video(sys.argv[1], sys.argv[2])
