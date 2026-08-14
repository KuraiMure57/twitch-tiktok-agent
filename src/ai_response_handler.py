import json
import sys


def load_ai_response(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "segments" not in data:
        raise ValueError("La respuesta de IA no contiene 'segments'")

    return data


def save_subtitles(data, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for segment in data["segments"]:
            start = segment["start"]
            end = segment["end"]
            text = segment["text"]

            f.write(f"{start:.3f}|{end:.3f}|{text}\n")


if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    data = load_ai_response(input_file)
    save_subtitles(data, output_file)

    print(f"Subtítulos finales guardados en {output_file}")
