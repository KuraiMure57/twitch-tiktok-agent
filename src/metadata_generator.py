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
    text = re.sub(r"\s+", " ", text).strip()
    return text


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
    combined_text = " ".join([
        str(analysis.get("title", "")),
        str(analysis.get("hook", "")),
        str(analysis.get("description", "")),
    ])

    game = detect_game(combined_text)

    hashtags = []

    if game:
        hashtags.extend(GAME_HASHTAGS[game])

    hashtags.extend([
        "#Twitch",
        "#TwitchClips",
        "#TikTokGaming",
        "#Gaming",
    ])

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

    if emotion in {"surprise", "disbelief"}:
        hashtags.append("#WTF")

    # Eliminar duplicados manteniendo el orden.
    return list(dict.fromkeys(hashtags))


def generate_metadata(input_path: str, output_path: str) -> None:
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(
            f"No existe el archivo de entrada: {input_file}"
        )

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    analysis = data.get("analysis", {})

    title = clean_text(
        analysis.get("title", "")
    )

    hook = clean_text(
        analysis.get("hook", "")
    )

    description = generate_description(analysis)
    hashtags = generate_hashtags(analysis)

    metadata = {
        "language": data.get("language", "es"),
        "title": title,
        "hook": hook,
        "description": description,
        "hashtags": hashtags,
        "moment_type": analysis.get("moment_type"),
        "emotion": analysis.get("emotion"),
        "score": data.get("scoring", {}).get("score"),
        "recommendation": data.get("scoring", {}).get(
            "recommendation"
        ),
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("Metadata generada correctamente.")
    print(f"Título: {title}")
    print(f"Hook: {hook}")
    print(f"Descripción: {description}")
    print(
        "Hashtags: "
        + " ".join(hashtags)
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
        sys.argv[2]
    )
