import subprocess
import sys
from pathlib import Path


def format_timestamp(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))

    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000

    minutes = milliseconds // 60_000
    milliseconds %= 60_000

    seconds_value = milliseconds // 1_000
    milliseconds %= 1_000

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds_value:02d},"
        f"{milliseconds:03d}"
    )


def create_srt(
    subtitles_path: str,
    output_path: str,
) -> None:
    subtitles_file = Path(subtitles_path)
    output_file = Path(output_path)

    if not subtitles_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {subtitles_file}"
        )

    entries = []

    with subtitles_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            parts = line.split("|", 2)

            if len(parts) != 3:
                raise ValueError(
                    "Formato de subtítulo inválido: "
                    f"{line}"
                )

            start = float(parts[0])
            end = float(parts[1])
            text = parts[2].strip()

            if end <= start:
                continue

            if not text:
                continue

            entries.append(
                (
                    start,
                    end,
                    text,
                )
            )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        for index, (
            start,
            end,
            text,
        ) in enumerate(entries, start=1):

            file.write(
                f"{index}\n"
            )

            file.write(
                f"{format_timestamp(start)} --> "
                f"{format_timestamp(end)}\n"
            )

            file.write(
                f"{text}\n\n"
            )

    print(
        f"SRT generado: {output_file}"
    )

    print(
        f"Subtítulos: {len(entries)}"
    )


def burn_subtitles(
    video_path: str,
    subtitle_path: str,
    output_path: str,
) -> None:
    video_file = Path(video_path)
    subtitle_file = Path(subtitle_path)
    output_file = Path(output_path)

    if not video_file.exists():
        raise FileNotFoundError(
            f"No existe el vídeo: {video_file}"
        )

    if not subtitle_file.exists():
        raise FileNotFoundError(
            f"No existe el SRT: {subtitle_file}"
        )

    subtitle_filter = (
        "subtitles="
        f"{subtitle_file}:"
        "force_style="
        "FontName=Arial\\,"
        "FontSize=18\\,"
        "Bold=1\\,"
        "Alignment=2\\,"
        "MarginV=60"
    )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_file),
        "-vf",
        subtitle_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "copy",
        str(output_file),
    ]

    print(
        "Quemando subtítulos en el vídeo..."
    )

    print(
        "Ejecutando FFmpeg..."
    )

    subprocess.run(
        command,
        check=True,
    )

    print(
        f"Vídeo final creado: {output_file}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Uso: python src/subtitle_burner.py "
            "<video.mp4> "
            "<subtitles.txt> "
            "<output.mp4>"
        )
        sys.exit(1)

    video_path = sys.argv[1]
    subtitles_path = sys.argv[2]
    output_path = sys.argv[3]

    srt_path = Path(output_path).with_suffix(
        ".srt"
    )

    create_srt(
        subtitles_path,
        str(srt_path),
    )

    burn_subtitles(
        video_path,
        str(srt_path),
        output_path,
    )
