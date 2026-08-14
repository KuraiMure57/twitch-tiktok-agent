import json
import sys


def validate_response(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("La respuesta no es un objeto JSON")

    if "language" not in data:
        raise ValueError("Falta 'language'")

    if "segments" not in data:
        raise ValueError("Falta 'segments'")

    if "analysis" not in data:
        raise ValueError("Falta 'analysis'")

    if not isinstance(data["segments"], list):
        raise ValueError("'segments' debe ser una lista")

    analysis = data["analysis"]

    required_analysis = [
        "moment_type",
        "emotion",
        "description",
        "is_interesting"
    ]

    for field in required_analysis:
        if field not in analysis:
            raise ValueError(f"Falta analysis.{field}")

    if not isinstance(analysis["is_interesting"], bool):
        raise ValueError("analysis.is_interesting debe ser booleano")

    for segment in data["segments"]:
        if "start" not in segment:
            raise ValueError("Segmento sin 'start'")

        if "end" not in segment:
            raise ValueError("Segmento sin 'end'")

        if "text" not in segment:
            raise ValueError("Segmento sin 'text'")

        if segment["start"] > segment["end"]:
            raise ValueError("El inicio no puede ser posterior al final")

    print("Respuesta de IA válida.")
    print(f"Segmentos validados: {len(data['segments'])}")
    print(f"Tipo de momento: {analysis['moment_type']}")
    print(f"Emoción: {analysis['emotion']}")
    print(f"Interesante: {analysis['is_interesting']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "Uso: python src/ai_response_validator.py ai_response.json"
        )

    validate_response(sys.argv[1])
