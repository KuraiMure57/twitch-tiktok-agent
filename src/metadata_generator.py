import json
import re
import sys
from pathlib import Path


GAME_HASHTAGS = {
    "genshin impact": [
        "#GenshinImpact",
        "#Genshin",
        "#GenshinImpactES",
    ],
    "warframe": [
        "#Warframe",
        "#WarframeCommunity",
        "#WarframeES",
    ],
    "phasmophobia": [
        "#Phasmophobia",
        "#PhasmophobiaGame",
        "#PhasmophobiaES",
    ],
    "assassin's creed": [
        "#AssassinsCreed",
        "#AssassinsCreedShadows",
        "#Ubisoft",
    ],
    "soulframe": [
        "#Soulframe",
        "#SoulframeGame",
        "#DigitalExtremes",
    ],
}


def detect_game(text: str) -> str | None:
    text_lower = text.lower()

    for game in GAME_HASHTAGS:
        if game in text_lower:
            return game

    return None


def clean_text(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\s+", " ", text).strip()

    return text


def limit_title(title: str, max_length: int = 100) -> str:
    title = clean_text(title)

    if len(title) <= max_length:
        return title

    truncated = title[:max_length].rsplit(" ", 1)[0].strip()

    if truncated:
        return truncated

    return title[:max_length].strip()


def generate_title(analysis: dict) -> str:
    """
    Obtiene el título generado por Gemini.

    Si Gemini no proporciona un título válido,
    genera uno automáticamente utilizando el hook,
    la descripción o el tipo de momento.
    """

    title = limit_title(
        analysis.get("title", "")
    )

    if title:
        return title

    hook = limit_title(
        analysis.get("hook", "")
    )

    if hook:
        return hook

    description = limit_title(
        analysis.get("description", "")
    )

    if description:
        return description

    moment_type = clean_text(
        analysis.get("moment_type", "")
    )

    emotion = clean_text(
        analysis.get("emotion", "")
    )

    if moment_type and emotion:
        return limit_title(
            f"Momento {moment_type} de {emotion}"
        )

    if moment_type:
        return limit_title(
            f"Momento {moment_type}"
        )

    if emotion:
        return limit_title(
            f"Momento de {emotion}"
        )

    return "Momento destacado del directo"


def generate_description(analysis: dict) -> str:
    description = clean_text(
        analysis.get("description", "")
    )

    hook = clean_text(
        analysis.get("hook", "")
    )

    if description:
        return description

    if hook:
        return hook

    return "Momento destacado del directo."


def generate_hashtags(analysis: dict) -> list[str]:
    combined_text = " ".join(
        [
            str(analysis.get("title", "")),
            str(analysis.get("hook", "")),
            str(analysis.get("description", "")),
        ]
    )

    game = detect_game(combined_text)

    hashtags = []

    if game:
        hashtags.extend(
            GAME_HASHTAGS[game]
        )

    hashtags.extend(
        [
            "#Twitch",
            "#TwitchClips",
            "#TikTokGaming",
            "#Gaming",
        ]
    )

    moment_type = str(
        analysis.get("moment_type", "")
    ).lower()

    emotion = str(
        analysis.get("emotion", "")
    ).lower()

    if moment_type == "fail":
        hashtags.append("#Fail")

    if moment_type == "funny":
        hashtags.append("#Funny")

    if emotion in {
        "surprise",
        "disbelief",
        "susto",
        "sorpresa",
    }:
        hashtags.append("#WTF")

    # Eliminar duplicados manteniendo el orden.
    return list(
        dict.fromkeys(hashtags)
    )


def generate_metadata(
    input_path: str,
    output_path: str,
) -> None:

    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo de entrada: {input_file}"
        )

    with input_file.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    analysis = data.get(
        "analysis",
        {},
    )

    if not isinstance(analysis, dict):
        analysis = {}

    # ============================================================
    # TÍTULO
    # ============================================================

    title = generate_title(
        analysis
    )

    if not title:
        raise ValueError(
            "No se pudo generar un título válido."
        )

    # ============================================================
    # HOOK
    # ============================================================

    hook = clean_text(
        analysis.get("hook", "")
    )

    # ============================================================
    # DESCRIPCIÓN
    # ============================================================

    description = generate_description(
        analysis
    )

    # ============================================================
    # HASHTAGS
    # ============================================================

    hashtags = generate_hashtags(
        analysis
    )

    # ============================================================
    # METADATA
    # ============================================================

    metadata = {
        "language": data.get(
            "language",
            "es",
        ),

        "title": title,

        "hook": hook,

        "description": description,

        "hashtags": hashtags,

        "moment_type": analysis.get(
            "moment_type"
        ),

        "emotion": analysis.get(
            "emotion"
        ),

        "score": data.get(
            "scoring",
            {},
        ).get(
            "score"
        ),

        "recommendation": data.get(
            "scoring",
            {},
        ).get(
            "recommendation"
        ),
    }

    # ============================================================
    # VALIDACIÓN FINAL
    # ============================================================

    metadata["title"] = clean_text(
        metadata["title"]
    )

    if not metadata["title"]:
        raise ValueError(
            "metadata.json no puede contener un título vacío."
        )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        "========================================"
    )

    print(
        "METADATA GENERADA CORRECTAMENTE"
    )

    print(
        "========================================"
    )

    print(
        f"Título: {metadata['title']}"
    )

    print(
        f"Hook: {metadata['hook']}"
    )

    print(
        f"Descripción: {metadata['description']}"
    )

    print(
        "Hashtags: "
        + " ".join(
            metadata["hashtags"]
        )
    )

    print(
        "========================================"
    )


if __name__ == "__main__":

    if len(sys.argv) != 3:

        print(
            "Uso: python src/metadata_generator.py "
            "<scored_response.json> <metadata.json>"
        )

        sys.exit(1)

    generate_metadata(
        sys.argv[1],
        sys.argv[2],
    )