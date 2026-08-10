import json
from pathlib import Path


CONFIG_PATH = Path("config/scoring.json")


def load_scoring_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def calculate_score(scores):
    config = load_scoring_config()
    criteria = config["clip_scoring"]

    total = 0

    for criterion, data in criteria.items():
        value = scores.get(criterion, 0)

        # Cada criterio se expresa en una escala de 0 a 10.
        # Se convierte después según el peso configurado.
        normalized = value / 10
        total += normalized * data["weight"]

    return round(total / 10, 1)


def is_candidate(score):
    config = load_scoring_config()
    threshold = config["decision"]["candidate_threshold"]

    return score >= threshold


if __name__ == "__main__":
    example_scores = {
        "epic_moment": 8,
        "humor": 6,
        "surprise_reaction": 9,
        "skill_play": 8,
        "comment": 4,
        "context": 9
    }

    score = calculate_score(example_scores)

    print(f"Puntuación: {score}/10")
    print(f"Candidato: {'Sí' if is_candidate(score) else 'No'}")
