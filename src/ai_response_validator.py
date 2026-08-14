import json
import sys


REQUIRED_ANALYSIS_FIELDS = [
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
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("La respuesta debe ser un objeto JSON.")

    if "language" not in data:
        raise ValueError("Falta 'language'.")

    if "segments" not in data:
        raise ValueError("Falta 'segments'.")

    if not isinstance(data["segments"], list):
        raise ValueError("'segments' debe ser una lista.")

    for index, segment in enumerate(data["segments"]):
        if not isinstance(segment, dict):
            raise ValueError(
                f"El segmento {index} no es un objeto."
            )

        for field in ["start", "end", "text"]:
            if field not in segment:
                raise ValueError(
                    f"Falta segments[{index}].{field}"
                )

        if not isinstance(segment["start"], (int, float)):
            raise ValueError(
                f"segments[{index}].start debe ser numérico."
            )

        if not isinstance(segment["end"], (int, float)):
            raise ValueError(
                f"segments[{index}].end debe ser numérico."
            )

        if segment["end"] < segment["start"]:
            raise ValueError(
                f"segments[{index}] tiene timestamps inválidos."
            )

        if not isinstance(segment["text"], str):
            raise ValueError(
                f"segments[{index}].text debe ser texto."
            )

    if "analysis" not in data:
        raise ValueError("Falta 'analysis'.")

    analysis = data["analysis"]

    for field in REQUIRED_ANALYSIS_FIELDS:
        if field not in analysis:
            raise ValueError(
                f"Falta analysis.{field}"
            )

    moment_type = str(
        analysis["moment_type"]
    ).lower()

    if moment_type not in VALID_MOMENT_TYPES:
        raise ValueError(
            f"Tipo de momento no válido: {moment_type}"
        )

    emotion = str(
        analysis["emotion"]
    ).lower()

    if emotion not in VALID_EMOTIONS:
        raise ValueError(
            f"Emoción no válida: {emotion}"
        )

    if not isinstance(
        analysis["description"],
        str
    ):
        raise ValueError(
            "analysis.description debe ser texto."
        )

    if not isinstance(
        analysis["is_interesting"],
        bool
    ):
        raise ValueError(
            "analysis.is_interesting debe ser booleano."
        )

    if not isinstance(
        analysis["clip_start"],
        (int, float)
    ):
        raise ValueError(
            "analysis.clip_start debe ser numérico."
        )

    if not isinstance(
        analysis["clip_end"],
        (int, float)
    ):
        raise ValueError(
            "analysis.clip_end debe ser numérico."
        )

    if analysis["clip_end"] <= analysis["clip_start"]:
        raise ValueError(
            "analysis.clip_end debe ser mayor que clip_start."
        )

    for field in ["hook", "title"]:
        if not isinstance(analysis[field], str):
            raise ValueError(
                f"analysis.{field} debe ser texto."
            )

        if not analysis[field].strip():
            raise ValueError(
                f"analysis.{field} no puede estar vacío."
            )

    print("Respuesta de IA válida.")
    print(f"Segmentos validados: {len(data['segments'])}")
    print(f"Tipo de momento: {moment_type}")
    print(f"Emoción: {emotion}")
    print(f"Interesante: {analysis['is_interesting']}")
    print(
        f"Clip: {analysis['clip_start']:.2f}s - "
        f"{analysis['clip_end']:.2f}s"
    )
    print(f"Hook: {analysis['hook']}")
    print(f"Título: {analysis['title']}")

    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Uso: python src/ai_response_validator.py "
            "ai_response.json"
        )
        sys.exit(1)

    validate_response(sys.argv[1])
