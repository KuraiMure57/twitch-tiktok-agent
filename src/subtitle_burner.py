import re
import subprocess
import sys
from pathlib import Path

from speaker_styles import (
    DEFAULT_SPEAKER,
    get_speaker_style,
)


PROFANITY_WORDS = {
    "puta",
    "putas",
    "puto",
    "putos",
    "mierda",
    "mierdas",
    "joder",
    "jodido",
    "jodida",
    "jodidos",
    "jodidas",
    "coño",
    "cojones",
    "hostia",
    "hostias",
    "gilipollas",
    "cabron",
    "cabrona",
    "cabrones",
    "cabronas",
    "maricon",
    "maricón",
    "maricona",
    "maricas",
    "idiota",
    "idiotas",
}


# ---------------------------------------------------------
# CONFIGURACIÓN VISUAL DE SUBTÍTULOS
# ---------------------------------------------------------
#
# El vídeo es vertical 1080x1920.
#
# 18 era demasiado pequeño para TikTok.
# 48 proporciona una lectura mucho más cómoda
# manteniendo suficiente espacio para varias palabras.
#
# Si posteriormente queremos hacerlo todavía más grande,
# podemos probar 52 o 56.
# ---------------------------------------------------------

SUBTITLE_FONT_NAME = "Arial"
SUBTITLE_FONT_SIZE = 48

SUBTITLE_OUTLINE = 4
SUBTITLE_SHADOW = 1

SUBTITLE_MARGIN_LEFT = 60
SUBTITLE_MARGIN_RIGHT = 60
SUBTITLE_MARGIN_BOTTOM = 100


def censor_profanity(
    text: str,
) -> str:

    if not text:
        return text

    censored_text = text

    for word in PROFANITY_WORDS:

        pattern = re.compile(
            rf"(?<!\w){re.escape(word)}(?!\w)",
            re.IGNORECASE,
        )

        censored_text = pattern.sub(
            "***",
            censored_text,
        )

    return censored_text


def format_ass_timestamp(
    seconds: float,
) -> str:

    total_centiseconds = int(
        round(seconds * 100)
    )

    hours = (
        total_centiseconds
        // 360000
    )

    total_centiseconds %= 360000

    minutes = (
        total_centiseconds
        // 6000
    )

    total_centiseconds %= 6000

    seconds_value = (
        total_centiseconds
        // 100
    )

    centiseconds = (
        total_centiseconds
        % 100
    )

    return (
        f"{hours}:"
        f"{minutes:02d}:"
        f"{seconds_value:02d}."
        f"{centiseconds:02d}"
    )


def ass_color(
    rgb,
) -> str:

    red, green, blue = rgb

    return (
        f"&H00"
        f"{blue:02X}"
        f"{green:02X}"
        f"{red:02X}"
    )


def safe_style_name(
    speaker: str,
) -> str:

    name = re.sub(
        r"[^a-zA-Z0-9_]",
        "_",
        speaker,
    )

    if not name:
        return DEFAULT_SPEAKER

    return name


def create_ass(
    subtitles_path: str,
    output_path: str,
    clip_start: float = 0.0,
) -> None:

    subtitles_file = Path(
        subtitles_path
    )

    output_file = Path(
        output_path
    )

    if not subtitles_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo de subtítulos: "
            f"{subtitles_file}"
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

            parts = line.split(
                "|",
                3,
            )

            # -----------------------------------------------
            # FORMATO ANTIGUO
            # -----------------------------------------------
            #
            # start|end|text
            #
            # -----------------------------------------------

            if len(parts) == 3:

                original_start = float(
                    parts[0]
                )

                original_end = float(
                    parts[1]
                )

                speaker = DEFAULT_SPEAKER

                text = parts[2].strip()

            # -----------------------------------------------
            # FORMATO NUEVO
            # -----------------------------------------------
            #
            # start|end|speaker|text
            #
            # -----------------------------------------------

            elif len(parts) == 4:

                original_start = float(
                    parts[0]
                )

                original_end = float(
                    parts[1]
                )

                speaker = parts[2].strip()

                if not speaker:
                    speaker = DEFAULT_SPEAKER

                text = parts[3].strip()

            else:

                raise ValueError(
                    "Formato de subtítulo "
                    f"inválido: {line}"
                )

            start = (
                original_start
                - clip_start
            )

            end = (
                original_end
                - clip_start
            )

            if end <= 0:
                continue

            start = max(
                0.0,
                start,
            )

            if end <= start:
                continue

            if not text:
                continue

            censored_text = (
                censor_profanity(text)
            )

            entries.append(
                (
                    start,
                    end,
                    speaker,
                    censored_text,
                )
            )

    # -------------------------------------------------------
    # CREAR ASS
    # -------------------------------------------------------

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            "[Script Info]\n"
        )

        file.write(
            "ScriptType: v4.00+\n"
        )

        file.write(
            "PlayResX: 1080\n"
        )

        file.write(
            "PlayResY: 1920\n"
        )

        file.write(
            "ScaledBorderAndShadow: yes\n"
        )

        file.write("\n")

        file.write(
            "[V4+ Styles]\n"
        )

        file.write(
            "Format: "
            "Name,Fontname,Fontsize,"
            "PrimaryColour,SecondaryColour,"
            "OutlineColour,BackColour,"
            "Bold,Italic,Underline,StrikeOut,"
            "ScaleX,ScaleY,Spacing,Angle,"
            "BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,"
            "Encoding\n"
        )

        speakers = set(
            entry[2]
            for entry in entries
        )

        style_names = {}

        for speaker in speakers:

            style_name = safe_style_name(
                speaker
            )

            style_names[
                speaker
            ] = style_name

            style = get_speaker_style(
                speaker
            )

            outline = ass_color(
                style["outline"]
            )

            file.write(
                f"Style: {style_name},"
                f"{SUBTITLE_FONT_NAME},"
                f"{SUBTITLE_FONT_SIZE},"
                f"&H00FFFFFF,"
                f"&H00FFFFFF,"
                f"{outline},"
                f"&H00000000,"
                f"1,0,0,0,"
                f"100,100,0,0,"
                f"1,"
                f"{SUBTITLE_OUTLINE},"
                f"{SUBTITLE_SHADOW},"
                f"2,"
                f"{SUBTITLE_MARGIN_LEFT},"
                f"{SUBTITLE_MARGIN_RIGHT},"
                f"{SUBTITLE_MARGIN_BOTTOM},"
                f"1\n"
            )

        file.write("\n")

        file.write(
            "[Events]\n"
        )

        file.write(
            "Format: Layer,Start,End,"
            "Style,Name,MarginL,MarginR,"
            "MarginV,Effect,Text\n"
        )

        for (
            start,
            end,
            speaker,
            text,
        ) in entries:

            style_name = style_names.get(
                speaker,
                safe_style_name(
                    DEFAULT_SPEAKER
                ),
            )

            text = (
                text
                .replace(
                    "\n",
                    "\\N",
                )
                .replace(
                    "\r",
                    "",
                )
            )

            file.write(
                f"Dialogue: 0,"
                f"{format_ass_timestamp(start)},"
                f"{format_ass_timestamp(end)},"
                f"{style_name},"
                f",0,0,0,,"
                f"{text}\n"
            )

    print(
        f"ASS generado: {output_file}"
    )

    print(
        f"Subtítulos: {len(entries)}"
    )

    print(
        "Hablantes detectados:"
    )

    for speaker in sorted(
        speakers
    ):
        print(
            f"  - {speaker}"
        )


def burn_subtitles(
    video_path: str,
    subtitle_path: str,
    output_path: str,
) -> None:

    video_file = Path(
        video_path
    )

    subtitle_file = Path(
        subtitle_path
    )

    output_file = Path(
        output_path
    )

    if not video_file.exists():
        raise FileNotFoundError(
            f"No existe el vídeo: "
            f"{video_file}"
        )

    if not subtitle_file.exists():
        raise FileNotFoundError(
            f"No existe el ASS: "
            f"{subtitle_file}"
        )

    subtitle_path_ffmpeg = (
        str(subtitle_file)
        .replace(
            "\\",
            "/",
        )
        .replace(
            ":",
            r"\:",
        )
        .replace(
            "'",
            r"\'",
        )
    )

    video_filter = (
        f"ass='{subtitle_path_ffmpeg}'"
    )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_file),
        "-vf",
        video_filter,
        "-c:a",
        "copy",
        str(output_file),
    ]

    print(
        "Quemando subtítulos "
        "multicolor en el vídeo..."
    )

    print(
        f"Tamaño de fuente: "
        f"{SUBTITLE_FONT_SIZE}"
    )

    print(
        f"Borde: "
        f"{SUBTITLE_OUTLINE}"
    )

    subprocess.run(
        command,
        check=True,
    )

    print(
        f"Vídeo final creado: "
        f"{output_file}"
    )


def main() -> None:

    if len(sys.argv) not in (
        4,
        5,
    ):

        print(
            "Uso: python "
            "src/subtitle_burner.py "
            "<video.mp4> "
            "<subtitles.txt> "
            "<output.mp4> "
            "[clip_start]"
        )

        sys.exit(1)

    video_path = sys.argv[1]

    subtitles_path = sys.argv[2]

    output_path = sys.argv[3]

    clip_start = 0.0

    if len(sys.argv) == 5:

        try:

            clip_start = float(
                sys.argv[4]
            )

        except ValueError:

            print(
                "ERROR: clip_start "
                "debe ser un número."
            )

            sys.exit(1)

    ass_path = Path(
        output_path
    ).with_suffix(
        ".ass"
    )

    create_ass(
        subtitles_path,
        str(ass_path),
        clip_start,
    )

    burn_subtitles(
        video_path,
        str(ass_path),
        output_path,
    )


if __name__ == "__main__":
    main()
