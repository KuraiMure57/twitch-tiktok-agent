import json
import sys


MOMENT_SCORES = {
    "fail": 25,
    "funny": 25,
    "reaction": 25,
    "surprise": 25,
    "clutch": 30,
    "achievement": 20,
    "rage": 20,
    "interesting": 15,
    "normal": 0,
}


EMOTION_SCORES = {
    "surprise": 20,
    "disbelief": 20,
    "joy": 20,
    "anger": 15,
    "fear": 15,
    "excitement": 20,
    "frustration": 15,
    "sadness": 5,
    "neutral": 0,
}


def calculate_score(data):
    analysis = data.get("analysis", {})

    moment_type = str(
        analysis.get("moment_type", "normal")
    ).lower()

    emotion = str(
        analysis.get("emotion", "neutral")
    ).lower()

    is_interesting = analysis.get("is_interesting", False)

    score = 0
    reasons = []

    moment_score = MOMENT_SCORES.get(moment_type, 10)
    emotion_score = EMOTION_SCORES.get(emotion, 5)

    score += moment_score
    score += emotion_score

    if moment_type in MOMENT_SCORES and moment_score > 0:
        reasons.append(
            f"El tipo de momento '{moment_type}' tiene potencial para clip."
        )

    if emotion in EMOTION_SCORES and emotion_score > 0:
        reasons.append(
            f"La emoción '{emotion}' aumenta el potencial de entretenimiento."
        )

    if is_interesting is True:
        score += 30
        reasons.append(
            "Gemini considera que el momento es interesante."
        )

    score = min(score, 100)

    if score >= 80:
        category = "excellent"
        recommendation = "create_clip"
    elif score >= 60:
        category = "good"
        recommendation = "consider_clip"
    elif score >= 40:
        category = "possible"
        recommendation = "review"
    else:
        category = "weak"
        recommendation = "discard"

    return {
        "score": score,
        "category": category,
        "recommendation": recommendation,
        "reasons": reasons
    }


def main():
    if len(sys.argv) != 3:
        print(
            "Uso: python src/scoring.py "
            "ai_response.json scored_response.json"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = calculate_score(data)

    data["scoring"] = result

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("Puntuación calculada correctamente.")
    print(f"Puntuación: {result['score']}/100")
    print(f"Categoría: {result['category']}")
    print(f"Recomendación: {result['recommendation']}")

    print("Motivos:")
    for reason in result["reasons"]:
        print(f"- {reason}")


if __name__ == "__main__":
    main()
