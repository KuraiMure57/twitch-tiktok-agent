import sys
import subprocess
from pathlib import Path

FONT_SIZE = 68
MARGIN_L = 140
MARGIN_R = 140
MARGIN_V = 145

def ass_escape(text):
return (
text.replace("\", r"\")
.replace("{", r"{")
.replace("}", r"}")
.replace("\n", r"\N")
)

def seconds_to_ass_time(seconds):
total_cs = round(
float(seconds) * 100
)

```
hours = total_cs // 360000
remaining = total_cs % 360000

minutes = remaining // 6000
remaining %= 6000

seconds_value = remaining // 100
centiseconds = remaining % 100

return (
    f"{hours}:"
    f"{minutes:02d}:"
    f"{seconds_value:02d}."
    f"{centiseconds:02d}"
)
```

def create_ass_file(
subtitles_path,
ass_path,
):

```
events = []

with subtitles_path.open(
    "r",
    encoding="utf-8",
) as file:

    for line_number, line in enumerate(
        file,
        start=1,
    ):

        line = line.strip()

        if not line:
            continue

        parts = line.split(
            "|",
            2,
        )

        if len(parts) != 3:
            raise ValueError(
                f"Línea inválida "
                f"{line_number}: {line}"
            )

        start_str, end_str, text = parts

        start = float(start_str)
        end = float(end_str)

        if end <= start:
            raise ValueError(
                f"Timestamp inválido "
                f"en línea {line_number}"
            )

        text = " ".join(
            text.split()
        ).strip()

        if not text:
            continue

        events.append(
            (
                seconds_to_ass_time(
                    start
                ),
                seconds_to_ass_time(
                    end
                ),
                ass_escape(text),
            )
        )

ass_content = f"""[Script Info]
```

ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TwitchLike,DejaVu Sans,{FONT_SIZE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,2,2,{MARGIN_L},{MARGIN_R},{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

```
for start, end, text in events:
    ass_content += (
        f"Dialogue: 0,"
        f"{start},"
        f"{end},"
        f"TwitchLike,,0,0,0,,"
        f"{text}\n"
    )

with ass_path.open(
    "w",
    encoding="utf-8",
) as file:
    file.write(
        ass_content
    )
```

def burn_subtitles(
video_path,
subtitles_path,
output_path,
):

```
video = Path(video_path)
subtitles = Path(
    subtitles_path
)
output = Path(output_path)

if not video.exists():
    raise FileNotFoundError(
        f"No existe el vídeo: {video}"
    )

if not subtitles.exists():
    raise FileNotFoundError(
        f"No existen los subtítulos: "
        f"{subtitles}"
    )

ass_path = output.with_suffix(
    ".ass"
)

print(
    "Creando archivo ASS..."
)

create_ass_file(
    subtitles,
    ass_path,
)

print(
    "Quemando subtítulos..."
)

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
    "-movflags",
    "+faststart",
    str(output),
]

subprocess.run(
    command,
    check=True,
)

if not output.exists():
    raise RuntimeError(
        "FFmpeg no creó el vídeo."
    )

print(
    f"Vídeo final creado: {output}"
)
```

if **name** == "**main**":

```
if len(sys.argv) != 4:
    print(
        "Uso: python src/subtitle_burner.py "
        "<clip.mp4> "
        "<final_subtitles.txt> "
        "<final_clip.mp4>"
    )
    sys.exit(1)

burn_subtitles(
    sys.argv[1],
    sys.argv[2],
    sys.argv[3],
)
```
