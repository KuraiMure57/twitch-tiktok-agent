import json
import sys
from pathlib import Path


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


def normalize_text(text: str) -> str:
    """
    Normaliza ligeramente el texto para poder comparar
    la respuesta de Gemini con la transcripción original.

    No modifica el texto que finalmente se escribe.
    """
    return " ".join(
        text.strip().lower().split()
    )


def punctuation_score(text: str) -> int:
    """
    Da una pequeña puntuación a la presencia de signos
    que aportan información emocional o interrogativa.

    No intenta decidir qué frase es correcta.
    Solo sirve para evitar perder puntuación útil.
    """
    score = 0

    for char in text:
        if char in "¡!¿?":
            score += 1

    return score


def looks_like_emotional_change(
    original: str,
    corrected: str,
) -> bool:
    """
    Detecta casos en los que Gemini ha cambiado una frase
    manteniendo aproximadamente el mismo contenido, pero
    ha eliminado una expresión emocional.

    Ejemplo:

        Original:  ¡La Llorona!
        Gemini:    La Llorona

    En ese caso conservamos la puntuación original.

    También evita considerar como mejora un cambio que
    transforme una reacción en una pregunta sin suficiente
    evidencia.
    """

    original_normalized = normalize_text(original)
    corrected_normalized = normalize_text(corrected)

    if not original_normalized or not corrected_normalized:
        return False

    original_has_exclamation = (
        "!" in original
        or "¡" in original
    )

    corrected_has_exclamation = (
        "!" in corrected
        or "¡" in corrected
    )

    original_has_question = (
        "?" in original
        or "¿" in original
    )

    corrected_has_question = (
        "?" in corrected
        or "¿" in corrected
    )

    # Si el original es claramente exclamativo y Gemini
    # lo transforma en pregunta, es una señal de que
    # puede haber perdido la intención emocional.
    if (
        original_has_exclamation
        and corrected_has_question
        and not corrected_has_exclamation
    ):
        return True

    # Si el original tiene exclamación y Gemini elimina
    # completamente la puntuación emocional, también
    # preferimos conservarla.
    if (
        original_has_exclamation
        and not corrected_has_exclamation
        and not corrected_has_question
    ):
        original_words = set(
            original_normalized.replace(
                "¡", ""
            ).replace(
                "!", ""
            ).split()
        )

        corrected_words = set(
            corrected_normalized.replace(
                "¿", ""
            ).replace(
                "?", ""
            ).split()
        )

        if original_words and corrected_words:
            common_words = original_words.intersection(
                corrected_words
            )

            similarity = (
                len(common_words)
                / max(
                    len(original_words),
                    len(corrected_words),
                )
            )

            if similarity >= 0.5:
                return True

    return False


def restore_emotional_punctuation(
    original: str,
    corrected: str,
) -> str:
    """
    Conserva la puntuación emocional del original cuando
    Gemini la ha eliminado o convertido en una pregunta
    sin cambiar el contenido corregido.

    La corrección textual de Gemini se mantiene siempre
    que no haya una señal clara de pérdida de intención.
    """

    if not original or not corrected:
        return corrected

    if not looks_like_emotional_change(
        original,
        corrected,
    ):
        return corrected

    original_has_exclamation = (
        "!" in original
        or "¡" in original
    )

    corrected_has_question = (
        "?" in corrected
        or "¿" in corrected
    )

    # Si Gemini convirtió una exclamación en pregunta,
    # eliminamos los signos de interrogación y usamos
    # exclamación.
    if (
        original_has_exclamation
        and corrected_has_question
    ):
        cleaned = corrected.replace(
            "¿",
            "",
        ).replace(
            "?",
            "",
        ).strip()

        if cleaned:
            return f"¡{cleaned.rstrip('¡!')}!"

    # Si simplemente eliminó la exclamación, la recuperamos.
    if (
        original_has_exclamation
        and "!" not in corrected
        and "¡" not in corrected
    ):
        cleaned = corrected.strip()

        if cleaned:
            return f"¡{cleaned.rstrip('¡!')}!"

    return corrected


def get_segments(data: dict) -> list:
    segments = data.get("segments", [])

    if not isinstance(segments, list):
        raise ValueError(
            "El campo 'segments' debe ser una lista."
        )

    return segments


def build_correction_map(
    ai_response: dict,
    original_segments: list,
) -> list:
    """
    Combina Gemini con la transcripción original.

    IMPORTANTE:
    Los timestamps siempre proceden de los segmentos
    originales.

    Gemini solo puede aportar el texto.
    """

    ai_segments = get_segments(ai_response)

    if len(ai_segments) != len(original_segments):
        raise ValueError(
            "El número de segmentos de Gemini no coincide "
            "con el número de segmentos originales. "
            "No se modificarán los timestamps."
        )

    result = []

    for index, (
        original_segment,
        ai_segment,
    ) in enumerate(
        zip(
            original_segments,
            ai_segments,
        ),
        start=1,
    ):

        if not isinstance(
            original_segment,
            dict,
        ):
            raise ValueError(
                f"Segmento original inválido en posición {index}."
            )

        if not isinstance(
            ai_segment,
            dict,
        ):
            raise ValueError(
                f"Segmento de Gemini inválido en posición {index}."
            )

        original_text = str(
            original_segment.get(
                "text",
                "",
            )
        ).strip()

        ai_text = str(
            ai_segment.get(
                "text",
                "",
            )
        ).strip()

        if not ai_text:
            ai_text = original_text

        final_text = restore_emotional_punctuation(
            original_text,
            ai_text,
        )

        # Los timestamps SIEMPRE son los originales.
        start = original_segment.get("start")
        end = original_segment.get("end")

        if start is None or end is None:
            raise ValueError(
                f"Faltan timestamps en el segmento "
                f"original {index}."
            )

        result.append(
            {
                "start": float(start),
                "end": float(end),
                "text": final_text,
            }
        )

    return result


def write_final_subtitles(
    segments: list,
    output_path: str,
) -> None:

    output_file = Path(output_path)

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        for segment in segments:
            start = segment["start"]
            end = segment["end"]
            text = segment["text"]

            file.write(
                f"{start:.3f}|"
                f"{end:.3f}|"
                f"{text}\n"
            )


def main() -> None:

    if len(sys.argv) != 4:
        print(
            "Uso: python src/ai_response_handler.py "
            "<ai_response.json> "
            "<corrected_subtitles.json> "
            "<final_subtitles.txt>"
        )
        sys.exit(1)

    ai_response_path = sys.argv[1]
    original_path = sys.argv[2]
    output_path = sys.argv[3]

    try:
        ai_response = load_json(
            ai_response_path
        )

        original_data = load_json(
            original_path
        )

        original_segments = get_segments(
            original_data
        )

        final_segments = build_correction_map(
            ai_response,
            original_segments,
        )

        write_final_subtitles(
            final_segments,
            output_path,
        )

        print(
            "Subtítulos finales creados utilizando "
            "los timestamps originales."
        )

        print(
            f"Segmentos procesados: "
            f"{len(final_segments)}"
        )

    except Exception as error:
        print(
            f"ERROR: {error}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
