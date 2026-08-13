import sys
from pathlib import Path

import whisper


def transcribe_video(video_path: str, output_path: str) -> None:
    video = Path(video_path)
    output = Path(output_path)

    if not video.exists():
        raise FileNotFoundError(f"No existe el vídeo: {video}")

    model = whisper.load_model("small")

    result = model.transcribe(
        str(video),
        language="es",
        fp16=False,
        word_timestamps=True,
        condition_on_previous_text=False
    )

    with output.open("w", encoding="utf-8") as file:
        for segment in result["segments"]:
            for word in segment.get("words", []):
                start = word["start"]
                end = word["end"]
                text = word["word"].strip()

                if text:
                    file.write(
                        f"{start:.3f}|{end:.3f}|{text}\n"
                    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Uso: python src/transcribe.py "
            "<video.mp4> <subtitles.txt>"
        )
        sys.exit(1)

    transcribe_video(sys.argv[1], sys.argv[2])
