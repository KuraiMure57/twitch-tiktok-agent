import json
import sys


def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_subtitles(
    ai_data,
    timing_data,
    output_file,
):
    ai_segments = ai_data.get(
        "segments",
        [],
    )

    timing_segments = timing_data.get(
        "segments",
        [],
    )

    if len(ai_segments) != len(
        timing_segments
    ):
        raise ValueError(
            "El número de segmentos de Gemini "
            "no coincide con los timestamps originales."
        )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:

        for timing, ai in zip(
            timing_segments,
            ai_segments,
        ):
            start = float(
                timing["start"]
            )

            end = float(
                timing["end"]
            )

            text = " ".join(
                str(
                    ai.get(
                        "text",
                        timing.get(
                            "text",
                            "",
                        ),
                    )
                ).split()
            ).strip()

            if not text:
                continue

            file.write(
                f"{start:.3f}|"
                f"{end:.3f}|"
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

    timing_data = load_json(
        sys.argv[2]
    )

    save_subtitles(
        ai_data,
        timing_data,
        sys.argv[3],
    )

    print(
        "Subtítulos finales creados "
        "utilizando los timestamps originales."
    )
