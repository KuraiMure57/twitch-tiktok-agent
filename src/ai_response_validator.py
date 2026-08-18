import json
import sys


REQUIRED_ANALYSIS_FIELDS = [
    "transcription_reviewed",
    "missing_segments_added",
    "timestamps_preserved",
    "moment_type",
    "emotion",
    "description",
    "is_interesting",
    "clip_start",
    "clip_end",
    "hook",
    "title",
]


VALID_MOMENT_TYPES = {
    "fail",
    "funny",
    "reaction",
    "surprise",
    "clutch",
    "achievement",
    "rage",
    "scare",
    "interesting",
    "normal",
}


VALID_EMOTIONS = {
    "surprise",
    "disbelief",
    "joy",
    "anger",
    "fear",
    "excitement",
    "frustration",
    "sadness",
    "neutral",
}


def validate_response(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "La respuesta debe ser un objeto JSON."
        )

    if "language" not in data:
        raise ValueError(
            "Falta 'language'."
        )

    if "segments" not in data:
        raise ValueError(
            "Falta 'segments'."
        )

    if not isinstance(
        data["segments"],
        list,
    ):
        raise ValueError(
            "'segments' debe ser una lista."
        )

    if not data["segments"]:
        raise ValueError(
            "'segments' no puede estar vacío."
        )

    previous_end = -1.0

    for index, segment in enumerate(
        data["segments"]
    ):

        if not isinstance(
            segment,
            dict,
        ):
            raise ValueError(
                f"El segmento {index} no es un objeto."
            )

        for field in [
            "start",
            "end",
            "text",
        ]:

            if field not in segment:
                raise ValueError(
                    f"Falta segments[{index}].{field}"
                )

        if not isinstance(
            segment["start"],
            (int, float),
        ):
            raise ValueError(
                f"segments[{index}].start "
                "debe ser numérico."
            )

        if not isinstance(
            segment["end"],
            (int, float),
        ):
            raise ValueError(
                f"segments[{index}].end "
                "debe ser numérico."
            )

        start = float(
            segment["start"]
        )

        end = float(
            segment["end"]
        )

        if start < 0:
            raise ValueError(
                f"segments[{index}].start "
                "no puede ser negativo."
            )

        if end <= start:
            raise ValueError(
                f"segments[{index}] tiene "
                "timestamps inválidos."
            )

        if start < previous_end - 0.05:
            print(
                f"Advertencia: el segmento {index} "
                "se solapa con el anterior."
            )

        previous_end = max(
            previous_end,
            end,
        )

        if not isinstance(
            segment["text"],
            str,
        ):
            raise ValueError(
                f"segments[{index}].text "
                "debe ser texto."
            )

        if not segment["text"].strip():
            raise ValueError(
                f"segments[{index}].text "
                "no puede estar vacío."
            )

    if "analysis" not in data:
        raise ValueError(
            "Falta 'analysis'."
        )

    analysis = data["analysis"]

    if not isinstance(
        analysis,
        dict,
    ):
        raise ValueError(
            "'analysis' debe ser un objeto."
        )

    for field in REQUIRED_ANALYSIS_FIELDS:

        if field not in analysis:
            raise ValueError(
                f"Falta analysis.{field}"
            )

    if not isinstance(
        analysis["transcription_reviewed"],
        bool,
    ):
        raise ValueError(
            "analysis.transcription_reviewed "
            "debe ser booleano."
        )

    if not isinstance(
        analysis["missing_segments_added"],
        bool,
    ):
        raise ValueError(
            "analysis.missing_segments_added "
            "debe ser booleano."
        )

    if not isinstance(
        analysis["timestamps_preserved"],
        bool,
    ):
        raise ValueError(
            "analysis.timestamps_preserved "
            "debe ser booleano."
        )

    moment_type = str(
        analysis["moment_type"]
    ).lower().strip()

    if moment_type not in VALID_MOMENT_TYPES:
        raise ValueError(
            "Tipo de momento no válido: "
            f"{moment_type}"
        )

    emotion = str(
        analysis["emotion"]
    ).lower().strip()

    if emotion not in VALID_EMOTIONS:
        raise ValueError(
            f"Emoción no válida: {emotion}"
        )

    if not isinstance(
        analysis["description"],
        str,
    ):
        raise ValueError(
            "analysis.description "
            "debe ser texto."
        )

    if not isinstance(
        analysis["is_interesting"],
        bool,
    ):
        raise ValueError(
            "analysis.is_interesting "
            "debe ser booleano."
        )

    if not isinstance(
        analysis["clip_start"],
        (int, float),
    ):
        raise ValueError(
            "analysis.clip_start "
            "debe ser numérico."
        )

    if not isinstance(
        analysis["clip_end"],
        (int, float),
    ):
        raise ValueError(
            "analysis.clip_end "
            "debe ser numérico."
        )

    clip_start = float(
        analysis["clip_start"]
    )

    clip_end = float(
        analysis["clip_end"]
    )

    if clip_start < 0:
        raise ValueError(
            "analysis.clip_start "
            "no puede ser negativo."
        )

    if clip_end <= clip_start:
        raise ValueError(
            "analysis.clip_end debe ser "
            "mayor que clip_start."
        )

    for field in [
        "hook",
        "title",
    ]:

        if not isinstance(
            analysis[field],
            str,
        ):
            raise ValueError(
                f"analysis.{field} "
                "debe ser texto."
            )

        if not analysis[field].strip():
            raise ValueError(
                f"analysis.{field} "
                "no puede estar vacío."
            )

    print(
        "Respuesta de IA válida."
    )

    print(
        f"Segmentos validados: "
        f"{len(data['segments'])}"
    )

    print(
        "Transcripción revisada: "
        f"{analysis['transcription_reviewed']}"
    )

    print(
        "Segmentos nuevos añadidos: "
        f"{analysis['missing_segments_added']}"
    )

    print(
        "Timestamps preservados: "
        f"{analysis['timestamps_preserved']}"
    )

    print(
        f"Tipo de momento: "
        f"{moment_type}"
    )

    print(
        f"Emoción: {emotion}"
    )

    print(
        f"Interesante: "
        f"{analysis['is_interesting']}"
    )

    print(
        f"Momento detectado: "
        f"{clip_start:.2f}s - "
        f"{clip_end:.2f}s"
    )

    print(
        f"Hook: {analysis['hook']}"
    )

    print(
        f"Título: {analysis['title']}"
    )

    return True


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            "Uso: python src/ai_response_validator.py "
            "ai_response.json"
        )

        sys.exit(1)

    validate_response(
        sys.argv[1]
    )
