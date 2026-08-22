import json
import sys
from pathlib import Path


# ============================================================
# CONFIGURACIÓN
# ============================================================

REQUIRED_SEGMENT_FIELDS = (
    "start",
    "end",
    "text",
)


# ============================================================
# JSON
# ============================================================

def load_json(path: str) -> dict:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {file_path}"
        )

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# ============================================================
# VALIDACIÓN GENERAL
# ============================================================

def validate_root(data: dict) -> None:

    if not isinstance(data, dict):
        raise ValueError(
            "La respuesta de Gemini debe ser "
            "un objeto JSON."
        )

    if "segments" not in data:
        raise ValueError(
            "La respuesta de Gemini no contiene "
            "el campo 'segments'."
        )

    if not isinstance(
        data["segments"],
        list,
    ):
        raise ValueError(
            "El campo 'segments' debe ser una lista."
        )


# ============================================================
# VALIDAR SEGMENTOS
# ============================================================

def validate_segments(
    segments: list,
) -> None:

    for index, segment in enumerate(
        segments,
        start=1,
    ):

        if not isinstance(
            segment,
            dict,
        ):
            raise ValueError(
                f"Segmento {index}: debe ser "
                f"un objeto JSON."
            )

        # ----------------------------------------------------
        # CAMPOS OBLIGATORIOS
        # ----------------------------------------------------

        for field in REQUIRED_SEGMENT_FIELDS:

            if field not in segment:
                raise ValueError(
                    f"Segmento {index}: falta "
                    f"el campo '{field}'."
                )

        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        try:

            start = float(
                segment["start"]
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                f"Segmento {index}: "
                f"'start' no es numérico."
            )

        # ----------------------------------------------------
        # END
        # ----------------------------------------------------

        try:

            end = float(
                segment["end"]
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                f"Segmento {index}: "
                f"'end' no es numérico."
            )

        # ----------------------------------------------------
        # TIMESTAMPS
        # ----------------------------------------------------

        if start < 0:
            raise ValueError(
                f"Segmento {index}: "
                f"'start' no puede ser negativo."
            )

        if end <= start:
            raise ValueError(
                f"Segmento {index}: "
                f"'end' debe ser mayor que "
                f"'start'. "
                f"({start} -> {end})"
            )

        # ----------------------------------------------------
        # TEXTO
        # ----------------------------------------------------

        text = segment["text"]

        if not isinstance(
            text,
            str,
        ):
            raise ValueError(
                f"Segmento {index}: "
                f"'text' debe ser texto."
            )

        if not text.strip():
            raise ValueError(
                f"Segmento {index}: "
                f"'text' está vacío."
            )

        # ----------------------------------------------------
        # SPEAKER
        #
        # No es obligatorio porque el handler dispone
        # de un fallback a kuraimure.
        # ----------------------------------------------------

        if "speaker" in segment:

            speaker = segment["speaker"]

            if not isinstance(
                speaker,
                str,
            ):
                raise ValueError(
                    f"Segmento {index}: "
                    f"'speaker' debe ser texto."
                )

            if not speaker.strip():
                raise ValueError(
                    f"Segmento {index}: "
                    f"'speaker' no puede estar vacío."
                )


# ============================================================
# VALIDAR RESPUESTA COMPLETA
# ============================================================

def validate_ai_response(
    data: dict,
) -> None:

    validate_root(
        data
    )

    validate_segments(
        data["segments"]
    )


# ============================================================
# NORMALIZAR RESPUESTA
# ============================================================

def normalize_ai_response(
    data: dict,
) -> dict:

    normalized = dict(data)

    normalized_segments = []

    for segment in data["segments"]:

        normalized_segment = dict(
            segment
        )

        normalized_segment["start"] = round(
            float(
                normalized_segment["start"]
            ),
            3,
        )

        normalized_segment["end"] = round(
            float(
                normalized_segment["end"]
            ),
            3,
        )

        normalized_segment["text"] = (
            str(
                normalized_segment["text"]
            )
            .strip()
        )

        if "speaker" in normalized_segment:

            normalized_segment["speaker"] = (
                str(
                    normalized_segment["speaker"]
                )
                .strip()
            )

        normalized_segments.append(
            normalized_segment
        )

    # --------------------------------------------------------
    # ORDENAR POR INICIO
    #
    # IMPORTANTE:
    # NO eliminamos solapamientos.
    #
    # En conversaciones dos speakers pueden hablar
    # simultáneamente.
    # --------------------------------------------------------

    normalized_segments.sort(
        key=lambda segment: (
            segment["start"],
            segment["end"],
        )
    )

    normalized["segments"] = (
        normalized_segments
    )

    return normalized


# ============================================================
# GUARDAR JSON
# ============================================================

def save_json(
    data: dict,
    path: str,
) -> None:

    output_file = Path(path)

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")


# ============================================================
# MOSTRAR INFORMACIÓN DE SOLAPAMIENTOS
# ============================================================

def show_overlaps(
    segments: list,
) -> None:

    overlaps = []

    for index in range(
        1,
        len(segments),
    ):

        previous = segments[index - 1]
        current = segments[index]

        previous_end = float(
            previous["end"]
        )

        current_start = float(
            current["start"]
        )

        if current_start < previous_end:

            overlaps.append(
                (
                    index,
                    previous,
                    current,
                )
            )

    if not overlaps:
        return

    print("")
    print(
        "========================================"
    )
    print(
        "SOLAPAMIENTOS DETECTADOS"
    )
    print(
        "========================================"
    )

    print(
        "Se permiten porque pueden corresponder "
        "a dos speakers hablando simultáneamente."
    )

    for (
        index,
        previous,
        current,
    ) in overlaps:

        previous_speaker = previous.get(
            "speaker",
            "kuraimure",
        )

        current_speaker = current.get(
            "speaker",
            "kuraimure",
        )

        print("")
        print(
            f"Segmentos {index} y {index + 1}:"
        )

        print(
            f"  [{previous_speaker}] "
            f"{float(previous['start']):.3f}s -> "
            f"{float(previous['end']):.3f}s"
        )

        print(
            f"  [{current_speaker}] "
            f"{float(current['start']):.3f}s -> "
            f"{float(current['end']):.3f}s"
        )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    # ========================================================
    # ARGUMENTOS
    #
    # Permitimos:
    #
    # python src/ai_response_validator.py
    #
    # y:
    #
    # python src/ai_response_validator.py ai_response.json
    #
    # ========================================================

    if len(sys.argv) == 1:

        input_path = (
            "ai_response.json"
        )

    elif len(sys.argv) == 2:

        input_path = sys.argv[1]

    else:

        print(
            "Uso:"
        )

        print(
            "python src/ai_response_validator.py"
        )

        print(
            "o:"
        )

        print(
            "python src/ai_response_validator.py "
            "<ai_response.json>"
        )

        sys.exit(1)

    try:

        print(
            "========================================"
        )

        print(
            "VALIDANDO RESPUESTA DE GEMINI"
        )

        print(
            "========================================"
        )

        print(
            f"Archivo: {input_path}"
        )

        # ----------------------------------------------------
        # CARGAR
        # ----------------------------------------------------

        data = load_json(
            input_path
        )

        # ----------------------------------------------------
        # VALIDAR
        # ----------------------------------------------------

        validate_ai_response(
            data
        )

        # ----------------------------------------------------
        # NORMALIZAR
        # ----------------------------------------------------

        normalized = normalize_ai_response(
            data
        )

        segments = normalized[
            "segments"
        ]

        # ----------------------------------------------------
        # MOSTRAR SOLAPAMIENTOS
        #
        # Solo informativo.
        # NO provocan fallo.
        # ----------------------------------------------------

        show_overlaps(
            segments
        )

        # ----------------------------------------------------
        # INFORMACIÓN
        # ----------------------------------------------------

        print("")
        print(
            "========================================"
        )
        print(
            "RESPUESTA VÁLIDA"
        )
        print(
            "========================================"
        )

        print(
            f"Segmentos válidos: "
            f"{len(segments)}"
        )

        if segments:

            first = segments[0]
            last = segments[-1]

            print("")
            print(
                "Primer segmento:"
            )

            print(
                f"  {first['start']:.3f}s -> "
                f"{first['end']:.3f}s"
            )

            print(
                f"  [{first.get('speaker', 'kuraimure')}] "
                f"{first['text']}"
            )

            print("")
            print(
                "Último segmento:"
            )

            print(
                f"  {last['start']:.3f}s -> "
                f"{last['end']:.3f}s"
            )

            print(
                f"  [{last.get('speaker', 'kuraimure')}] "
                f"{last['text']}"
            )

        # ----------------------------------------------------
        # GUARDAR
        # ----------------------------------------------------

        save_json(
            normalized,
            input_path,
        )

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
            f"Archivo guardado: "
            f"{input_path}"
        )

        print(
            "Los solapamientos entre speakers "
            "se conservan."
        )

    except json.JSONDecodeError as error:

        print("")
        print(
            "ERROR: El archivo no contiene "
            "JSON válido."
        )

        print(
            f"Detalle: {error}"
        )

        sys.exit(1)

    except FileNotFoundError as error:

        print("")
        print(
            f"ERROR: {error}"
        )

        sys.exit(1)

    except ValueError as error:

        print("")
        print(
            f"ERROR DE VALIDACIÓN: {error}"
        )

        sys.exit(1)

    except Exception as error:

        print("")
        print(
            f"ERROR INESPERADO: {error}"
        )

        sys.exit(1)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
