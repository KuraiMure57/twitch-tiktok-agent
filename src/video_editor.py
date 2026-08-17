import subprocess
import sys
from pathlib import Path


def run_ffmpeg(input_video: str, output_video: str) -> None:
    input_path = Path(input_video)
    output_path = Path(output_video)

    if not input_path.exists():
        raise FileNotFoundError(f"No existe el vídeo: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Creando vídeo vertical 9:16 con estilo Twitch...")

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),

        "-filter_complex",
        (
            # Fondo ampliado, desenfocado y ocupando todo el formato 9:16.
            "[0:v]"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "boxblur=25:10"
            "[background];"

            # Recortar el vídeo principal a formato 1:1.
            # Se conserva la zona central del gameplay.
            "[0:v]"
            "crop=ih:ih:(iw-ih)/2:0,"
            "scale=1080:1080"
            "[foreground];"

            # Colocar el gameplay cuadrado en el centro vertical.
            "[background][foreground]"
            "overlay=0:420"
            "[v]"
        ),

        "-map",
        "[v]",
        "-map",
        "0:a?",

        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "20",

        "-c:a",
        "aac",
        "-b:a",
        "192k",

        "-movflags",
        "+faststart",

        str(output_path),
    ]

    subprocess.run(command, check=True)

    if not output_path.exists():
        raise RuntimeError(
            "FFmpeg no creó el vídeo de salida."
        )

    print(
        f"Vídeo vertical creado correctamente: "
        f"{output_path}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Uso: python src/video_editor.py "
            "<video_entrada.mp4> <video_salida.mp4>"
        )
        sys.exit(1)

    run_ffmpeg(
        sys.argv[1],
        sys.argv[2]
    )
