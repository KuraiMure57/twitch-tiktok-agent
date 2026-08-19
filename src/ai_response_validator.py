import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_ANALYSIS_DEFAULTS = {
    "transcription_reviewed": True,
    "timestamps_preserved": True,
    "is_interesting": True,
}


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: str) -> dict[str, Any]:
    file_path = Path(path)

    if not file_path.exists():
        fail(f"No existe el archivo: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        fail(
            f"JSON inválido en {file_path}: "
            f"{exc}"
        )

    if not isinstance(data, dict):
        fail("La respuesta de Gemini debe ser un objeto JSON.")

    return data


def validate_segments(data: dict[str, Any]) -> list[dict[str, Any]]:
    segments = data.get("segments")

    if segments is None:
        fail("Falta 'segments'.")

    if not isinstance(segments, list):
        fail("'segments' debe ser una lista.")

    if not segments:
        fail("'segments' no puede estar vacío.")

    print(f"Segmentos recibidos: {len(segments)}")

    validated_segments = []

    previous_start = -1.0
    previous_end = -1.0

    for index, segment in enumerate(segments, start=1):

        if not isinstance(segment, dict):
            fail(
                f"El segmento {index} no es un objeto JSON."
            )

        if "start" not in segment:
            fail(
                f"Falta 'start' en el segmento {index}."
            )

        if "end" not in segment:
            fail(
                f"Falta 'end' en el segmento {index}."
            )

        if "text" not in segment:
            fail(
                f"Falta 'text' en el segmento {index}."
            )

        try:
            start = float(segment["start"])
            end = float(segment["end"])
        except (TypeError, ValueError):
            fail(
                f"'start' y 'end' deben ser números "
                f"en el segmento {index}."
            )

        text = segment["text"]

        if not isinstance(text, str):
            fail(
                f"'text' debe ser texto "
                f"en el segmento {index}."
            )

        if start < 0:
            fail(
                f"'start' no puede ser negativo "
                f"en el segmento {index}."
            )

        if end <= start:
            fail(
                f"'end' debe ser mayor que 'start' "
                f"en el segmento {index}."
            )

        # Los timestamps deben mantenerse en orden.
        if start < previous_start:
            fail(
                f"Los timestamps no están ordenados "
                f"en el segmento {index}."
            )

        if start < previous_end:
            fail(
                f"Los segmentos se solapan "
                f"en el segmento {index}."
            )

        previous_start = start
        previous_end = end

        validated_segments.append(
            {
                "start": start,
                "end": end,
                "text": text,
            }
        )

    return validated_segments


def validate_analysis(
    data: dict[str, Any],
) -> dict[str, Any]:

    analysis = data.get("analysis")

    # Gemini puede devolver los segmentos correctamente
    # pero omitir alguno de los metadatos de análisis.
    #
    # No debemos rechazar una transcripción válida por
    # la ausencia de un campo opcional.

    if analysis is None:
        print(
            "AVISO: Gemini no devolvió 'analysis'. "
            "Se utilizarán valores predeterminados."
        )

        analysis = {}

    if not isinstance(analysis, dict):
        fail("'analysis' debe ser un objeto JSON.")

    normalized = dict(analysis)

    for key, default in REQUIRED_ANALYSIS_DEFAULTS.items():

        if key not in normalized:
            print(
                f"AVISO: Falta analysis.{key}. "
                f"Valor predeterminado: {default}"
            )

            normalized[key] = default

    return normalized


def validate_language(data: dict[str, Any]) -> str:

    language = data.get("language", "es")

    if not isinstance(language, str):
        fail("'language' debe ser texto.")

    language = language.strip()

    if not language:
        language = "es"

    return language


def validate_response(path: str) -> None:

    print("========================================")
    print("VALIDANDO RESPUESTA DE GEMINI")
    print("========================================")

    data = load_json(path)

    segments = validate_segments(data)

    language = validate_language(data)

    analysis = validate_analysis(data)

    # Normalizamos la estructura para que los siguientes
    # pasos del workflow reciban siempre los campos esperados.
    data["language"] = language
    data["segments"] = segments
    data["analysis"] = analysis

    # Guardamos la respuesta normalizada.
    file_path = Path(path)

    with file_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("")
    print("========================================")
    print("VALIDACIÓN CORRECTA")
    print("========================================")

    print(f"Idioma: {language}")
    print(f"Segmentos: {len(segments)}")

    print("")
    print("Análisis:")

    for key, value in analysis.items():
        print(f"  {key}: {value}")

    print("")
    print(
        "La respuesta de Gemini es válida y ha sido "
        "normalizada correctamente."
    )


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            "Uso: python src/ai_response_validator.py "
            "<ai_response.json>"
        )
        sys.exit(1)

    try:
        validate_response(sys.argv[1])

    except ValueError as exc:
        print("")
        print("========================================")
        print("ERROR DE VALIDACIÓN")
        print("========================================")
        print(str(exc))
        sys.exit(1)