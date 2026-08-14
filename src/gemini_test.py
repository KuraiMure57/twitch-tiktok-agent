import os
from google import genai


def main():
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("No se encontró GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input="Responde únicamente con: Gemini conectado correctamente."
    )

    print(interaction.output_text)


if __name__ == "__main__":
    main()
