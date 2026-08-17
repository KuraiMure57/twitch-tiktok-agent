import json
import sys


def load_json(input_file):
    with open(
        input_file,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def save_subtitles(
    ai_data,
    original_data,
    output_file
):
    ai_segments = ai_data.get(
        "segments",
        []
    )

    original_segments = original_data.get(
        "segments",
        []
    )

    if not original_segments:
        raise ValueError(
            "La transcripción original no contiene segmentos."
        )

    if not ai_segments:
        raise ValueError(
            "La respuesta de IA no contiene segmentos."
        )

    if len(ai_segments) != len(original_segments):
        raise ValueError(
            "Gemini modificó el número de segmentos. "
            f"Originales: {len(original_segments)} | "
            f"Gemini: {len(ai_segments)}"
        )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        for index, (
            original,
            ai_segment
        ) in enumerate(
            zip(
                original_segments,
                ai_segments
            ),
            start=1
        ):

            original_start = float(
                original["start"]
            )

            original_end = float(
                original["end"]
            )

            ai_start = float(
                ai_segment["start"]
            )

            ai_end = float(
                ai_segment["end"]
            )

            # Gemini NO puede modificar los timestamps.
            if ai_start != original_start:
                raise ValueError(
                    "Gemini modificó el timestamp de inicio "
                    f"del segmento {index}. "
                    f"Original: {original_start} | "
                    f"Gemini: {ai_start}"
                )

            if ai_end != original_end:
                raise ValueError(
                    "Gemini modificó el timestamp de final "
                    f"del segmento {index}. "
                    f"Original: {original_end} | "
                    f"Gemini: {ai_end}"
                )

            text = ai_segment.get(
                "text",
                ""
            ).strip()

            if not text:
                text = original.get(
                    "text",
                    ""
                ).strip()

            f.write(
                f"{original_start:.3f}|"
                f"{original_end:.3f}|"
                f"{text}\n"
            )


if __name__ == "__main__":

    if len(sys.argv) != 4:
        raise SystemExit(
            "Uso: python src/ai_response_handler.py "
            "ai_response.json "
            "corrected_subtitles.json "
            "final_subtitles.txt"
        )

    ai_data = load_json(
        sys.argv[1]
    )

    original_data = load_json(
        sys.argv[2]
    )

    save_subtitles(
        ai_data,
        original_data,
        sys.argv[3]
    )

    print(
        f"Subtítulos finales guardados en "
        f"{sys.argv[3]}"
    )
