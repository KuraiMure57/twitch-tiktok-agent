import json
import sys
from pathlib import Path


REQUIRED_SEGMENT_FIELDS = {
    "start",
    "end",
    "text"
}


def validate_response(input_path: str) -> None:
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {input_file}"
        )

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("La respuesta de la IA debe ser un objeto JSON.")

    if "segments" not in data:
        raise ValueError("Falta el campo 'segments'.")

    if not isinstance(data["segments"], list):
        raise ValueError("'segments' debe ser una lista.")

    for index, segment in enumerate(data["segments"]):
        if not isinstance(segment, dict):
            raise ValueError(
                f"El segmento {index} no es un objeto."
            )

        missing = REQUIRED_SEGMENT_FIELDS - segment.keys()

        if missing:
            raise ValueError(
                f"El segmento {index} no contiene: "
                f"{', '.join(sorted(missing))}"
            )

        if not isinstance(segment["start"], (int, float)):
            raise ValueError(
                f"El start del segmento {index} no es numérico."
            )

        if not isinstance(segment["end"], (int, float)):
            raise ValueError(
                f"El end del segmento {index} no es numérico."
            )

        if not isinstance(segment["text"], str):
            raise ValueError(
                f"El text del segmento {index} no es texto."
            )

        if segment["end"] < segment["start"]:
            raise ValueError(
                f"El segmento {index} tiene tiempos incorrectos."
            )

    print("Respuesta de IA válida.")
    print(f"Segmentos validados: {len(data['segments'])}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Uso: python src/ai_response_validator.py "
            "<archivo.json>"
        )
        sys.exit(1)

    validate_response(sys.argv[1])
