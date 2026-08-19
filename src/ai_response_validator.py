import json
import sys
from pathlib import Path


def load_json(path: str) -> dict:
    file_path = Path(path)

    if not file_path.exists():
        raise ValueError(
            f"No existe el archivo: {file_path}"
        )

    try:
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON inválido en {file_path}: {exc}"
        )

    if not isinstance(data, dict):
        raise ValueError(
            f"{file_path} debe contener un objeto JSON."
        )

    return data


def validate_number(
    value,
    field_name: str,
) -> float:

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} debe ser numérico."
        )

    if not isinstance(
        value,
        (int, float),
    ):
        raise ValueError(
            f"{field_name} debe ser numérico."
        )

    return float(value)


def validate_segment(
    segment: dict,
    index: int,
) -> None:

    if not isinstance(segment, dict):
        raise ValueError(
            f"segments[{index}] no es un objeto."
        )

    for field in (
        "start",
        "end",
        "text",
    ):
        if field not in segment:
            raise ValueError(
                f"Falta segments[{index}].{field}"
            )

    start = validate_number(
        segment["start"],
        f"segments[{index}].start",
    )

    end = validate_number(
        segment["end"],
        f"segments[{index}].end",
    )

    text = segment["text"]

    if not isinstance(text, str):
        raise ValueError(
            f"segments[{index}].text debe ser texto."
        )

    if not text.strip():
        raise ValueError(
            f"segments[{index}].text está vacío."
        )

    if start < 0:
        raise ValueError(
            f"segments[{index}].start no puede ser negativo."
        )

    if end <= start:
        raise ValueError(
            f"Timestamp inválido en segments[{index}]: "
            f"{start} -> {end}"
        )


def validate_segments(
    segments,
) -> None:

    if not isinstance(
        segments,
        list,
    ):
        raise ValueError(
            "'segments' debe ser una lista."
        )

    if not segments:
        raise ValueError(
            "'segments' no puede estar vacío."
        )

    previous_start = None

    for index, segment in enumerate(
        segments
    ):

        validate_segment(
            segment,
            index,
        )

        start = float(
            segment["start"]
        )

        if (
            previous_start is not None
            and start < previous_start
        ):
            raise ValueError(
                "Los segmentos no están "
                "ordenados cronológicamente."
            )

        previous_start = start


def validate_analysis(
    analysis: dict,
) -> None:

    if not isinstance(
        analysis,
        dict,
    ):
        raise ValueError(
            "'analysis' debe ser un objeto."
        )

    # --------------------------------------------------------
    # Estos son los únicos campos que realmente necesitamos
    # para continuar el pipeline.
    # --------------------------------------------------------

    required_fields = [
        "is_interesting",
        "clip_start",
        "clip_end",
    ]

    for field in required_fields:

        if field not in analysis:
            raise ValueError(
                f"Falta analysis.{field}"
            )

    if not isinstance(
        analysis["is_interesting"],
        bool,
    ):
        raise ValueError(
            "analysis.is_interesting debe ser booleano."
        )

    clip_start = validate_number(
        analysis["clip_start"],
        "analysis.clip_start",
    )

    clip_end = validate_number(
        analysis["clip_end"],
        "analysis.clip_end",
    )

    if clip_start < 0:
        raise ValueError(
            "analysis.clip_start no puede ser negativo."
        )

    if clip_end <= clip_start:
        raise ValueError(
            "analysis.clip_end debe ser mayor "
            "que analysis.clip_start."
        )


def validate_timestamps(
    response_segments: list,
    original_segments: list,
) -> None:

    if not isinstance(
        original_segments,
        list,
    ):
        raise ValueError(
            "Los segmentos originales no son una lista."
        )

    if len(response_segments) != len(
        original_segments
    ):
        raise ValueError(
            "Gemini ha cambiado el número de segmentos. "
            f"Original: {len(original_segments)} | "
            f"Gemini: {len(response_segments)}"
        )

    tolerance = 0.001

    for index, (
        original,
        response,
    ) in enumerate(
        zip(
            original_segments,
            response_segments,
        )
    ):

        original_start = validate_number(
            original["start"],
            f"original segments[{index}].start",
        )

        original_end = validate_number(
            original["end"],
            f"original segments[{index}].end",
        )

        response_start = validate_number(
            response["start"],
            f"Gemini segments[{index}].start",
        )

        response_end = validate_number(
            response["end"],
            f"Gemini segments[{index}].end",
        )

        if abs(
            original_start - response_start
        ) > tolerance:

            raise ValueError(
                "Gemini ha cambiado el timestamp "
                f"de inicio del segmento {index}. "
                f"Original: {original_start} | "
                f"Gemini: {response_start}"
            )

        if abs(
            original_end - response_end
        ) > tolerance:

            raise ValueError(
                "Gemini ha cambiado el timestamp "
                f"de final del segmento {index}. "
                f"Original: {original_end} | "
                f"Gemini: {response_end}"
            )


def validate_clip_range(
    analysis: dict,
    original_segments: list,
) -> None:

    if not original_segments:
        return

    clip_start = float(
        analysis["clip_start"]
    )

    clip_end = float(
        analysis["clip_end"]
    )

    video_start = min(
        float(segment["start"])
        for segment in original_segments
    )

    video_end = max(
        float(segment["end"])
        for segment in original_segments
    )

    tolerance = 0.1

    if clip_start < video_start - tolerance:
        raise ValueError(
            "analysis.clip_start está fuera "
            "del rango de los subtítulos."
        )

    if clip_end > video_end + tolerance:
        raise ValueError(
            "analysis.clip_end está fuera "
            "del rango de los subtítulos."
        )


def validate_response(
    response_path: str,
    original_path: str = "corrected_subtitles.json",
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

    response = load_json(
        response_path
    )

    # --------------------------------------------------------
    # NIVEL PRINCIPAL
    # --------------------------------------------------------

    if "language" not in response:
        raise ValueError(
            "Falta 'language'."
        )

    if "segments" not in response:
        raise ValueError(
            "Falta 'segments'."
        )

    if "analysis" not in response:
        raise ValueError(
            "Falta 'analysis'."
        )

    language = response["language"]

    if not isinstance(
        language,
        str,
    ):
        raise ValueError(
            "'language' debe ser texto."
        )

    # --------------------------------------------------------
    # SEGMENTOS
    # --------------------------------------------------------

    segments = response["segments"]

    validate_segments(
        segments
    )

    print(
        f"Segmentos recibidos: {len(segments)}"
    )

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    analysis = response["analysis"]

    validate_analysis(
        analysis
    )

    # --------------------------------------------------------
    # TIMESTAMPS CONTRA LA TRANSCRIPCIÓN ORIGINAL
    # --------------------------------------------------------

    original_file = Path(
        original_path
    )

    if original_file.exists():

        original = load_json(
            original_path
        )

        original_segments = original.get(
            "segments",
            [],
        )

        print(
            "Comprobando timestamps originales..."
        )

        validate_timestamps(
            segments,
            original_segments,
        )

        print(
            "OK: los timestamps no han sido modificados."
        )

        validate_clip_range(
            analysis,
            original_segments,
        )

        print(
            "OK: el rango del clip es válido."
        )

    else:

        print(
            "AVISO: no existe "
            f"{original_path}."
        )

        print(
            "Se omite la comparación de timestamps."
        )

    # --------------------------------------------------------
    # INFORMACIÓN OPCIONAL
    # --------------------------------------------------------

    optional_fields = [
        "moment_type",
        "emotion",
        "description",
        "hook",
        "title",
        "transcription_reviewed",
        "missing_segments_added",
        "timestamps_preserved",
    ]

    present_optional = [
        field
        for field in optional_fields
        if field in analysis
    ]

    if present_optional:

        print(
            "Campos opcionales recibidos: "
            + ", ".join(present_optional)
        )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    print("")
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
        f"Interesante: "
        f"{analysis['is_interesting']}"
    )

    print(
        f"Clip sugerido: "
        f"{analysis['clip_start']:.3f}s -> "
        f"{analysis['clip_end']:.3f}s"
    )

    if "title" in analysis:
        print(
            f"Título: {analysis['title']}"
        )

    print(
        "Gemini ha pasado todas las comprobaciones."
    )


if __name__ == "__main__":

    if len(sys.argv) not in (2, 3):

        print(
            "Uso:"
        )

        print(
            "python src/ai_response_validator.py "
            "ai_response.json"
        )

        print(
            "o:"
        )

        print(
            "python src/ai_response_validator.py "
            "ai_response.json "
            "corrected_subtitles.json"
        )

        sys.exit(1)

    response_path = sys.argv[1]

    if len(sys.argv) == 3:
        original_path = sys.argv[2]
    else:
        original_path = (
            "corrected_subtitles.json"
        )

    try:

        validate_response(
            response_path,
            original_path,
        )

    except Exception as exc:

        print("")
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
