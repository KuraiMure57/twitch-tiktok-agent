import json
import sys
from pathlib import Path


REQUIRED_TOP_LEVEL_FIELDS = {
    "language",
    "segments",
    "analysis",
}

REQUIRED_SEGMENT_FIELDS = {
    "start",
    "end",
    "text",
}

REQUIRED_ANALYSIS_FIELDS = {
    "moment_type",
    "emotion",
    "description",
    "is_interesting",
    "clip_start",
    "clip_end",
    "hook",
    "title",
}


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: str) -> dict:
    file_path = Path(path)

    if not file_path.exists():
        fail(f"No existe el archivo: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        fail(
            f"El archivo no contiene JSON válido: "
            f"{file_path} ({exc})"
        )

    if not isinstance(data, dict):
        fail("La respuesta JSON debe ser un objeto.")

    return data


def validate_segment(
    segment: dict,
    index: int,
) -> None:

    if not isinstance(segment, dict):
        fail(
            f"El segmento {index} no es un objeto JSON."
        )

    missing = REQUIRED_SEGMENT_FIELDS - segment.keys()

    if missing:
        fail(
            f"Faltan campos en segments[{index}]: "
            f"{', '.join(sorted(missing))}"
        )

    start = segment["start"]
    end = segment["end"]
    text = segment["text"]

    if not isinstance(start, (int, float)):
        fail(
            f"segments[{index}].start debe ser numérico."
        )

    if not isinstance(end, (int, float)):
        fail(
            f"segments[{index}].end debe ser numérico."
        )

    if start < 0:
        fail(
            f"segments[{index}].start no puede ser negativo."
        )

    if end <= start:
        fail(
            f"segments[{index}] tiene timestamps inválidos: "
            f"{start} -> {end}"
        )

    if not isinstance(text, str):
        fail(
            f"segments[{index}].text debe ser texto."
        )

    if not text.strip():
        fail(
            f"segments[{index}].text no puede estar vacío."
        )


def validate_segments(
    segments: list,
) -> None:

    if not isinstance(segments, list):
        fail("'segments' debe ser una lista.")

    if not segments:
        fail("'segments' no puede estar vacío.")

    previous_start = None

    for index, segment in enumerate(
        segments
    ):
        validate_segment(
            segment,
            index,
        )

        start = segment["start"]

        if previous_start is not None:
            if start < previous_start:
                fail(
                    "Los segmentos no están ordenados "
                    "cronológicamente."
                )

        previous_start = start


def validate_analysis(
    analysis: dict,
) -> None:

    if not isinstance(analysis, dict):
        fail("'analysis' debe ser un objeto.")

    missing = (
        REQUIRED_ANALYSIS_FIELDS
        - analysis.keys()
    )

    if missing:
        fail(
            "Faltan campos obligatorios en analysis: "
            + ", ".join(sorted(missing))
        )

    if not isinstance(
        analysis["moment_type"],
        str,
    ):
        fail(
            "analysis.moment_type debe ser texto."
        )

    if not isinstance(
        analysis["emotion"],
        str,
    ):
        fail(
            "analysis.emotion debe ser texto."
        )

    if not isinstance(
        analysis["description"],
        str,
    ):
        fail(
            "analysis.description debe ser texto."
        )

    if not isinstance(
        analysis["hook"],
        str,
    ):
        fail(
            "analysis.hook debe ser texto."
        )

    if not isinstance(
        analysis["title"],
        str,
    ):
        fail(
            "analysis.title debe ser texto."
        )

    if not isinstance(
        analysis["is_interesting"],
        bool,
    ):
        fail(
            "analysis.is_interesting debe ser booleano."
        )

    clip_start = analysis["clip_start"]
    clip_end = analysis["clip_end"]

    if not isinstance(
        clip_start,
        (int, float),
    ):
        fail(
            "analysis.clip_start debe ser numérico."
        )

    if not isinstance(
        clip_end,
        (int, float),
    ):
        fail(
            "analysis.clip_end debe ser numérico."
        )

    if clip_start < 0:
        fail(
            "analysis.clip_start no puede ser negativo."
        )

    if clip_end <= clip_start:
        fail(
            "analysis.clip_end debe ser mayor "
            "que analysis.clip_start."
        )


def validate_timestamps_against_original(
    response: dict,
    original: dict,
) -> None:

    response_segments = response.get(
        "segments",
        [],
    )

    original_segments = original.get(
        "segments",
        [],
    )

    if not isinstance(
        original_segments,
        list,
    ):
        fail(
            "Los subtítulos originales no contienen "
            "una lista válida de segments."
        )

    if len(response_segments) != len(
        original_segments
    ):
        fail(
            "Gemini ha cambiado el número de segmentos. "
            f"Original: {len(original_segments)} | "
            f"Respuesta: {len(response_segments)}"
        )

    tolerance = 0.001

    for index, (
        original_segment,
        response_segment,
    ) in enumerate(
        zip(
            original_segments,
            response_segments,
        )
    ):

        original_start = float(
            original_segment["start"]
        )
        original_end = float(
            original_segment["end"]
        )

        response_start = float(
            response_segment["start"]
        )
        response_end = float(
            response_segment["end"]
        )

        if abs(
            original_start - response_start
        ) > tolerance:

            fail(
                "Gemini ha cambiado el timestamp "
                f"de inicio del segmento {index}: "
                f"original={original_start}, "
                f"respuesta={response_start}"
            )

        if abs(
            original_end - response_end
        ) > tolerance:

            fail(
                "Gemini ha cambiado el timestamp "
                f"de final del segmento {index}: "
                f"original={original_end}, "
                f"respuesta={response_end}"
            )


def validate_clip_range(
    response: dict,
    original: dict,
) -> None:

    analysis = response["analysis"]

    clip_start = float(
        analysis["clip_start"]
    )

    clip_end = float(
        analysis["clip_end"]
    )

    original_segments = original.get(
        "segments",
        [],
    )

    if not original_segments:
        return

    original_start = min(
        float(segment["start"])
        for segment in original_segments
    )

    original_end = max(
        float(segment["end"])
        for segment in original_segments
    )

    tolerance = 0.1

    if clip_start < original_start - tolerance:
        fail(
            "analysis.clip_start está fuera "
            "del rango del vídeo."
        )

    if clip_end > original_end + tolerance:
        fail(
            "analysis.clip_end está fuera "
            "del rango del vídeo."
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

    missing = (
        REQUIRED_TOP_LEVEL_FIELDS
        - response.keys()
    )

    if missing:
        fail(
            "Faltan campos obligatorios en la "
            "respuesta de Gemini: "
            + ", ".join(sorted(missing))
        )

    language = response["language"]

    if not isinstance(language, str):
        fail(
            "'language' debe ser texto."
        )

    validate_segments(
        response["segments"]
    )

    validate_analysis(
        response["analysis"]
    )

    original_file = Path(
        original_path
    )

    if original_file.exists():

        print(
            "Comprobando timestamps contra "
            "corrected_subtitles.json..."
        )

        original = load_json(
            original_path
        )

        validate_timestamps_against_original(
            response,
            original,
        )

        validate_clip_range(
            response,
            original,
        )

        print(
            "Timestamps originales conservados."
        )

    else:

        print(
            "AVISO: No existe "
            f"{original_path}. "
            "Se omite la comparación de timestamps."
        )

    print("")
    print(
        "========================================"
    )
    print(
        "RESPUESTA DE GEMINI VÁLIDA"
    )
    print(
        "========================================"
    )

    print(
        f"Idioma: {language}"
    )

    print(
        f"Segmentos: "
        f"{len(response['segments'])}"
    )

    analysis = response["analysis"]

    print(
        f"Momento: "
        f"{analysis['moment_type']}"
    )

    print(
        f"Emoción: "
        f"{analysis['emotion']}"
    )

    print(
        f"Interesante: "
        f"{analysis['is_interesting']}"
    )

    print(
        f"Clip: "
        f"{analysis['clip_start']:.3f}s -> "
        f"{analysis['clip_end']:.3f}s"
    )

    print(
        f"Título: "
        f"{analysis['title']}"
    )

    print("")
    print(
        "Validación completada correctamente."
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