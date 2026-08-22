import json
import sys
from pathlib import Path


TIMESTAMP_TOLERANCE = 0.05

# Número máximo de palabras que aparecerán a la vez.
# Se aplica DESPUÉS de la respuesta de Gemini.
MAX_WORDS_PER_SUBTITLE = 3


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
    return " ".join(
        text.strip().lower().split()
    )


def looks_like_emotional_change(
    original: str,
    corrected: str,
) -> bool:

    original_normalized = normalize_text(
        original
    )

    corrected_normalized = normalize_text(
        corrected
    )

    if (
        not original_normalized
        or not corrected_normalized
    ):
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

    if (
        original_has_exclamation
        and corrected_has_question
        and not corrected_has_exclamation
    ):
        return True

    if (
        original_has_exclamation
        and not corrected_has_exclamation
        and not corrected_has_question
    ):

        original_words = set(
            original_normalized
            .replace("¡", "")
            .replace("!", "")
            .split()
        )

        corrected_words = set(
            corrected_normalized
            .replace("¿", "")
            .replace("?", "")
            .split()
        )

        if (
            original_words
            and corrected_words
        ):

            common_words = (
                original_words
                .intersection(
                    corrected_words
                )
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

    if (
        original_has_exclamation
        and corrected_has_question
    ):

        cleaned = (
            corrected
            .replace("¿", "")
            .replace("?", "")
            .strip()
        )

        if cleaned:
            return (
                "¡"
                + cleaned.rstrip("¡!")
                + "!"
            )

    if (
        original_has_exclamation
        and "!" not in corrected
        and "¡" not in corrected
    ):

        cleaned = corrected.strip()

        if cleaned:
            return (
                "¡"
                + cleaned.rstrip("¡!")
                + "!"
            )

    return corrected


def get_segments(data: dict) -> list:

    segments = data.get(
        "segments",
        [],
    )

    if not isinstance(
        segments,
        list,
    ):
        raise ValueError(
            "El campo 'segments' "
            "debe ser una lista."
        )

    return segments


def find_matching_original_segment(
    ai_segment: dict,
    original_segments: list,
):
    ai_start = float(
        ai_segment["start"]
    )

    ai_end = float(
        ai_segment["end"]
    )

    best_match = None
    best_difference = None

    for original in original_segments:

        original_start = float(
            original["start"]
        )

        original_end = float(
            original["end"]
        )

        difference = (
            abs(
                ai_start
                - original_start
            )
            +
            abs(
                ai_end
                - original_end
            )
        )

        if (
            abs(
                ai_start
                - original_start
            )
            <= TIMESTAMP_TOLERANCE
            and
            abs(
                ai_end
                - original_end
            )
            <= TIMESTAMP_TOLERANCE
        ):

            if (
                best_difference is None
                or difference
                < best_difference
            ):

                best_match = original
                best_difference = difference

    return best_match


def get_speaker(
    segment: dict,
    fallback: str = "kuraimure",
) -> str:

    speaker = str(
        segment.get(
            "speaker",
            fallback,
        )
    ).strip()

    if not speaker:
        return fallback

    return speaker


def build_final_segments(
    ai_response: dict,
    original_segments: list,
) -> list:

    ai_segments = get_segments(
        ai_response
    )

    result = []

    for ai_index, ai_segment in enumerate(
        ai_segments,
        start=1,
    ):

        if not isinstance(
            ai_segment,
            dict,
        ):
            raise ValueError(
                f"Segmento de Gemini "
                f"{ai_index} inválido."
            )

        if "start" not in ai_segment:
            raise ValueError(
                f"Gemini: falta start "
                f"en segmento {ai_index}."
            )

        if "end" not in ai_segment:
            raise ValueError(
                f"Gemini: falta end "
                f"en segmento {ai_index}."
            )

        if "text" not in ai_segment:
            raise ValueError(
                f"Gemini: falta text "
                f"en segmento {ai_index}."
            )

        ai_start = float(
            ai_segment["start"]
        )

        ai_end = float(
            ai_segment["end"]
        )

        ai_text = str(
            ai_segment["text"]
        ).strip()

        if ai_end <= ai_start:
            raise ValueError(
                f"Timestamp inválido "
                f"en segmento {ai_index}."
            )

        if not ai_text:
            continue

        original = find_matching_original_segment(
            ai_segment,
            original_segments,
        )

        if original is not None:

            original_text = str(
                original.get(
                    "text",
                    "",
                )
            ).strip()

            final_text = (
                restore_emotional_punctuation(
                    original_text,
                    ai_text,
                )
            )

            # Mantenemos los timestamps originales.
            start = float(
                original["start"]
            )

            end = float(
                original["end"]
            )

            # Gemini tiene prioridad para identificar
            # al hablante.
            speaker = get_speaker(
                ai_segment,
                get_speaker(
                    original,
                    "kuraimure",
                ),
            )

        else:

            # Segmento nuevo localizado por Gemini.
            start = ai_start
            end = ai_end
            final_text = ai_text

            speaker = get_speaker(
                ai_segment,
                "kuraimure",
            )

            print(
                "Nuevo segmento recuperado "
                "por Gemini: "
                f"{start:.3f}s - "
                f"{end:.3f}s | "
                f"[{speaker}] | "
                f"{final_text}"
            )

        result.append(
            {
                "start": start,
                "end": end,
                "text": final_text,
                "speaker": speaker,
            }
        )

    result.sort(
        key=lambda segment: (
            segment["start"],
            segment["end"],
        )
    )

    return result


def split_long_subtitles(
    segments: list,
    max_words: int = MAX_WORDS_PER_SUBTITLE,
) -> list:
    """
    Divide los textos largos DESPUÉS de Gemini.

    Esto es importante porque subtitle_formatter.py
    puede crear inicialmente frases cortas, pero Gemini
    puede volver a juntarlas en frases mucho más largas.

    Ejemplo:

        "no sé si ves mi cámara pero la"

    se convierte en:

        "no sé si"
        "ves mi"
        "cámara pero"
        "la"

    El tiempo total del segmento se mantiene y se
    reparte proporcionalmente entre las partes.
    """

    if max_words < 1:
        raise ValueError(
            "max_words debe ser mayor que 0."
        )

    result = []

    for segment in segments:

        text = str(
            segment.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        words = text.split()

        # Si ya cumple el límite, no hacemos nada.
        if len(words) <= max_words:
            result.append(segment)
            continue

        start = float(
            segment["start"]
        )

        end = float(
            segment["end"]
        )

        duration = end - start

        chunks = [
            words[index:index + max_words]
            for index in range(
                0,
                len(words),
                max_words,
            )
        ]

        total_words = len(words)
        elapsed_words = 0

        for chunk_index, chunk in enumerate(
            chunks
        ):

            chunk_start = (
                start
                + duration
                * (
                    elapsed_words
                    / total_words
                )
            )

            elapsed_words += len(chunk)

            if chunk_index == len(chunks) - 1:
                chunk_end = end
            else:
                chunk_end = (
                    start
                    + duration
                    * (
                        elapsed_words
                        / total_words
                    )
                )

            result.append(
                {
                    "start": round(
                        chunk_start,
                        3,
                    ),
                    "end": round(
                        chunk_end,
                        3,
                    ),
                    "text": " ".join(chunk),
                    "speaker": get_speaker(
                        segment,
                        "kuraimure",
                    ),
                }
            )

        print(
            "Segmento dividido por exceso "
            "de palabras: "
            f"{len(words)} -> "
            f"{len(chunks)} subtítulos | "
            f"[{get_speaker(segment)}]"
        )

    return result


def remove_duplicate_segments(
    segments: list,
) -> list:

    result = []

    seen = set()

    for segment in segments:

        key = (
            round(
                float(segment["start"]),
                3,
            ),
            round(
                float(segment["end"]),
                3,
            ),
            normalize_text(
                segment["text"]
            ),
            segment.get(
                "speaker",
                "kuraimure",
            ),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(segment)

    return result


def write_final_subtitles(
    segments: list,
    output_path: str,
) -> None:

    output_file = Path(
        output_path
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        for segment in segments:

            start = float(
                segment["start"]
            )

            end = float(
                segment["end"]
            )

            text = segment["text"]

            speaker = get_speaker(
                segment,
                "kuraimure",
            )

            file.write(
                f"{start:.3f}|"
                f"{end:.3f}|"
                f"{speaker}|"
                f"{text}\n"
            )


def main() -> None:

    if len(sys.argv) != 4:

        print(
            "Uso: python "
            "src/ai_response_handler.py "
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

        final_segments = build_final_segments(
            ai_response,
            original_segments,
        )

        # ==================================================
        # IMPORTANTE:
        # Gemini puede devolver frases mucho más largas
        # que las creadas originalmente.
        #
        # Por eso aplicamos el límite OTRA VEZ AQUÍ,
        # DESPUÉS de Gemini.
        # ==================================================

        segments_before_split = len(
            final_segments
        )

        final_segments = split_long_subtitles(
            final_segments,
            MAX_WORDS_PER_SUBTITLE,
        )

        final_segments = (
            remove_duplicate_segments(
                final_segments
            )
        )

        write_final_subtitles(
            final_segments,
            output_path,
        )

        print("")
        print(
            "Subtítulos finales creados."
        )

        print(
            "Los timestamps existentes "
            "se mantienen."
        )

        print(
            "Los segmentos que Whisper "
            "omitió pueden ser añadidos "
            "por Gemini."
        )

        print(
            "La información del hablante "
            "se conserva."
        )

        print(
            "Segmentos antes de dividir: "
            f"{segments_before_split}"
        )

        print(
            "Máximo de palabras por "
            "subtítulo: "
            f"{MAX_WORDS_PER_SUBTITLE}"
        )

        print(
            "Segmentos finales: "
            f"{len(final_segments)}"
        )

    except Exception as error:

        print(
            f"ERROR: {error}"
        )

        sys.exit(1)


if __name__ == "__main__":
    main()
