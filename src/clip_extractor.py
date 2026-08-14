import json
import os
import subprocess
import sys


def extract_clip(video_path, analysis_path, output_path):
    with open(analysis_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    analysis = data.get("analysis", {})

    if "clip_start" not in analysis:
        raise ValueError("Falta analysis.clip_start")

    if "clip_end" not in analysis:
        raise ValueError("Falta analysis.clip_end")

    start = float(analysis["clip_start"])
    end = float(analysis["clip_end"])

    if start < 0:
        raise ValueError("clip_start no puede ser negativo.")

    if end <= start:
        raise ValueError(
            "clip_end debe ser mayor que clip_start."
        )

    duration = end - start

    print(f"Extrayendo clip:")
    print(f"Inicio: {start:.3f}s")
    print(f"Fin: {end:.3f}s")
    print(f"Duración: {duration:.3f}s")

    output_dir = os.path.dirname(output_path)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-i",
        video_path,
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        output_path,
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(
            "FFmpeg no pudo extraer el clip."
        )

    if not os.path.exists(output_path):
        raise RuntimeError(
            "FFmpeg terminó correctamente pero el archivo no existe."
        )

    file_size = os.path.getsize(output_path)

    if file_size == 0:
        raise RuntimeError(
            "El archivo de clip está vacío."
        )

    print(
        f"Clip creado correctamente: {output_path}"
    )
    print(
        f"Tamaño: {file_size / 1024 / 1024:.2f} MB"
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Uso: python src/clip_extractor.py "
            "video.mp4 ai_response.json clip.mp4"
        )
        sys.exit(1)

    extract_clip(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
    )
