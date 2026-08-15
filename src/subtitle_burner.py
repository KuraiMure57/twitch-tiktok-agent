import sys
import subprocess
from pathlib import Path


def ass_escape(text: str) -> str:
    """Escapa caracteres especiales para ASS."""
    return (
        text.replace("\\", r"\\")
            .replace("{", r"\{")
            .replace("}", r"\}")
            .replace("\n", r"\N")
    )


def seconds_to_ass_time(seconds: float) -> str:
    """Convierte segundos a formato ASS: H:MM:SS.cc"""
    total_cs = round(seconds * 100)

    hours = total_cs // 360000
    remaining = total_cs % 360000

    minutes = remaining // 6000
    remaining %= 6000

    seconds_value = remaining // 100
    centiseconds = remaining % 100

    return f"{hours}:{minutes:02d}:{seconds_value:02d}.{centiseconds:02d}"


def create_ass_file(subtitles_path: Path, ass_path: Path) -> None:
    if not subtitles_path.exists():
        raise FileNotFoundError(
            f"No existe el archivo de subtítulos: {subtitles_path}"
        )

    events = []

    with subtitles_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            parts = line.split("|", 2)

            if len(parts) != 3:
                raise ValueError(
                    f"Línea inválida en {subtitles_path} "
                    f"(línea {line_number}): {line}"
                )

            start_str, end_str, text = parts

            try:
                start = float(start_str)
                end = float(end_str)
            except ValueError:
                raise ValueError(
                    f"Timestamps inválidos en la línea {line_number}: {line}"
                )

            if end <= start:
                raise ValueError(
                    f"El final debe ser mayor que el inicio "
                    f"en la línea {line_number}: {line}"
                )

            events.append(
                (
                    seconds_to_ass_time(start),
                    seconds_to_ass_time(end),
                    ass_escape(text)
                )
            )

    ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTok,DejaVu Sans,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,2,2,80,80,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    for start, end, text in events:
        ass_content += (
            f"Dialogue: 0,{start},{end},TikTok,,0,0,0,,{text}\n"
        )

    with ass_path.open("w", encoding="utf-8") as file:
        file.write(ass_content)


def burn_subtitles(
    video_path: str,
    subtitles_path: str,
    output_path: str
) -> None:

    video = Path(video_path)
    subtitles = Path(subtitles_path)
    output = Path(output_path)

    if not video.exists():
        raise FileNotFoundError(f"No existe el vídeo: {video}")

    if not subtitles.exists():
        raise FileNotFoundError(
            f"No existen los subtítulos: {subtitles}"
        )

    ass_path = output.with_suffix(".ass")

    print("Creando archivo ASS de subtítulos...")
    create_ass_file(subtitles, ass_path)

    print("Quemando subtítulos en el vídeo...")

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-vf",
        f"subtitles={ass_path}",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output),
    ]

    subprocess.run(command, check=True)

    if not output.exists():
        raise RuntimeError(
            f"FFmpeg terminó pero no creó el archivo: {output}"
        )

    print(f"Vídeo con subtítulos creado: {output}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Uso: python src/subtitle_burner.py "
            "<clip.mp4> <final_subtitles.txt> <final_clip.mp4>"
        )
        sys.exit(1)

    burn_subtitles(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3]
    )
