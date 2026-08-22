import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_ANALYSIS_DEFAULTS = {
    "transcription_reviewed": True,
    "timestamps_preserved": True,
    "is_interesting": True,
}

# Solapamiento máximo que se corregirá automáticamente.
# Si Gemini genera un solapamiento mayor, se considera
# probablemente un problema real de timestamps.
MAX_AUTO_OVERLAP_SECONDS = 0.25


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: str) -> dict[str, Any]:
    file_path = Path(path)

    if not file_path.exists():
        fail(f"No existe el archivo: {file_path}")

    try:
        with file_path.open(
            "r",
            encoding="utf-8-sig",
        ) as file:
            data = json.load(file)

    except json.JSONDecodeError as exc:
        fail(
            f"JSON inválido en {file_path}: "
            f"{exc}"
        )

    if not isinstance(data, dict):
        fail(
            "La respuesta de Gemini debe ser "
            "un objeto JSON."
        )

    return data


def validate_segments(
    data: dict[str, Any],
) -> list[dict[str, Any]]:

    segments = data.get(
        "segments"
    )

    if segments is None:
        fail(
            "Falta 'segments'."
        )

    if not isinstance(
        segments,
        list,
    ):
        fail(
            "'segments' debe ser una lista."
        )

    if not segments:
        fail(
            "'segments' no puede estar vacío."
        )

    print(
        f"Segmentos recibidos: "
        f"{len(segments)}"
    )

    validated_segments = []

    previous_start = -1.0
    previous_end = -1.0

    for index, segment in enumerate(
        segments,
        start=1,
    ):

        if not isinstance(
            segment,
            dict,
        ):
            fail(
                f"El segmento {index} "
                f"no es un objeto JSON."
            )

        if "start" not in segment:
            fail(
                f"Falta 'start' en el "
                f"segmento {index}."
            )

        if "end" not in segment:
            fail(
                f"Falta 'end' en el "
                f"segmento {index}."
            )

        if "text" not in segment:
            fail(
                f"Falta 'text' en el "
                f"segmento {index}."
            )

        try:

            start = float(
                segment["start"]
            )

            end = float(
                segment["end"]
            )

        except (
            TypeError,
            ValueError,
        ):
            fail(
                f"'start' y 'end' deben ser "
                f"números en el segmento "
                f"{index}."
            )

        text = segment["text"]

        if not isinstance(
            text,
            str,
        ):
            fail(
                f"'text' debe ser texto "
                f"en el segmento {index}."
            )

        if start < 0:
            fail(
                f"'start' no puede ser "
                f"negativo en el segmento "
                f"{index}."
            )

        if end <= start:
            fail(
                f"'end' debe ser mayor que "
                f"'start' en el segmento "
                f"{index}."
            )

        # ---------------------------------------------------------
        # ORDEN CRONOLÓGICO
        # ---------------------------------------------------------

        if start < previous_start:
            fail(
                f"Los timestamps no están "
                f"ordenados en el segmento "
                f"{index}."
            )

        # ---------------------------------------------------------
        # SOLAPAMIENTOS
        # ---------------------------------------------------------
        #
        # Gemini puede estimar dos segmentos consecutivos
        # con un pequeño solapamiento.
        #
        # Ejemplo:
        #
        # Segmento 8: 24.50 -> 26.10
        # Segmento 9: 25.95 -> 27.20
        #
        # En este caso existe un solapamiento de 0.15 segundos.
        #
        # Si el solapamiento es pequeño, ajustamos el inicio
        # del segmento actual al final del anterior.
        #
        # Si es demasiado grande, detenemos la validación porque
        # probablemente Gemini ha generado timestamps incorrectos.
        # ---------------------------------------------------------

        if start < previous_end:

            overlap = (
                previous_end
                - start
            )

            if (
                overlap
                <= MAX_AUTO_OVERLAP_SECONDS
            ):

                print(
                    f"AVISO: Solapamiento de "
                    f"{overlap:.3f}s en el "
                    f"segmento {index}."
                )

                print(
                    f"Ajustando inicio de "
                    f"{start:.3f}s a "
                    f"{previous_end:.3f}s."
                )

                start = previous_end

                if end <= start:
                    fail(
                        f"El segmento {index} "
                        f"queda sin duración "
                        f"después de corregir "
                        f"el solapamiento."
                    )

            else:

                fail(
                    f"Los segmentos se solapan "
                    f"en el segmento {index} "
                    f"por {overlap:.3f}s. "
                    f"El solapamiento supera "
                    f"el límite de "
                    f"{MAX_AUTO_OVERLAP_SECONDS:.2f}s."
                )

        previous_start = start
        previous_end = end

        validated_segment = {
            "start": start,
            "end": end,
            "text": text,
        }

        # ---------------------------------------------------------
        # SPEAKER
        # ---------------------------------------------------------
        #
        # Conservamos el speaker generado por Gemini.
        # Esto es necesario para que subtitle_burner.py pueda
        # aplicar el color correspondiente a cada persona.
        # ---------------------------------------------------------

        speaker = segment.get(
            "speaker"
        )

        if speaker is not None:

            if not isinstance(
                speaker,
                str,
            ):
                fail(
                    f"'speaker' debe ser texto "
                    f"en el segmento {index}."
                )

            speaker = speaker.strip()

            if speaker:
                validated_segment[
                    "speaker"
                ] = speaker

        validated_segments.append(
            validated_segment
        )

    return validated_segments


def validate_analysis(
    data: dict[str, Any],
) -> dict[str, Any]:

    analysis = data.get(
        "analysis"
    )

    # Gemini puede devolver los segmentos correctamente
    # pero omitir alguno de los metadatos de análisis.
    #
    # No debemos rechazar una transcripción válida por
    # la ausencia de un campo opcional.

    if analysis is None:

        print(
            "AVISO: Gemini no devolvió "
            "'analysis'. "
            "Se utilizarán valores "
            "predeterminados."
        )

        analysis = {}

    if not isinstance(
        analysis,
        dict,
    ):
        fail(
            "'analysis' debe ser un "
            "objeto JSON."
        )

    normalized = dict(
        analysis
    )

    for key, default in (
        REQUIRED_ANALYSIS_DEFAULTS.items()
    ):

        if key not in normalized:

            print(
                f"AVISO: Falta "
                f"analysis.{key}. "
                f"Valor predeterminado: "
                f"{default}"
            )

            normalized[key] = default

    return normalized


def validate_language(
    data: dict[str, Any],
) -> str:

    language = data.get(
        "language",
        "es",
    )

    if not isinstance(
        language,
        str,
    ):
        fail(
            "'language' debe ser texto."
        )

    language = language.strip()

    if not language:
        language = "es"

    return language


def validate_response(
    path: str,
) -> None:

    print(
        "========================================"
    )

    print(
        "VALIDANDO RESPUESTA DE GEMINI"
    )

    print(
        "========================================"
    )

    data = load_json(
        path
    )

    segments = validate_segments(
        data
    )

    language = validate_language(
        data
    )

    analysis = validate_analysis(
        data
    )

    # Normalizamos la estructura para que los siguientes
    # pasos del workflow reciban siempre los campos esperados.

    data["language"] = language

    data["segments"] = segments

    data["analysis"] = analysis

    # Guardamos la respuesta normalizada.

    file_path = Path(
        path
    )

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

    print(
        ""
    )

    print(
        "========================================"
    )

    print(
        "VALIDACIÓN CORRECTA"
    )

    print(
        "========================================"
    )

    print(
        f"Idioma: {language}"
    )

    print(
        f"Segmentos: {len(segments)}"
    )

    print(
        ""
    )

    print(
        "Análisis:"
    )

    for key, value in analysis.items():

        print(
            f"  {key}: {value}"
        )

    print(
        ""
    )

    print(
        "La respuesta de Gemini es válida "
        "y ha sido normalizada correctamente."
    )


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Uso: python "
            "src/ai_response_validator.py "
            "<ai_response.json>"
        )

        sys.exit(1)

    try:

        validate_response(
            sys.argv[1]
        )

    except ValueError as exc:

        print(
            ""
        )

        print(
            "========================================"
        )

        print(
            "ERROR DE VALIDACIÓN"
        )

        print(
            "========================================"
        )

        print(
            str(exc)
        )

        sys.exit(1)
