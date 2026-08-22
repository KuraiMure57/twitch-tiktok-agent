from pathlib import Path


# ============================================================
# CONFIGURACIÓN DE COLORES POR PERSONA
# ============================================================
#
# "outline" es el color del borde de las letras.
#
# Formato:
#   (R, G, B)
#
# Puedes cambiar los colores sin tocar el resto del código.
#
# ============================================================

SPEAKER_STYLES = {
    # Tú
    "kuraimure": {
        "outline": (0, 0, 0),
    },

    # Segunda persona
    "speaker_2": {
        "outline": (0, 102, 255),
    },

    # Tercera persona
    "speaker_3": {
        "outline": (255, 0, 0),
    },

    # Cuarta persona
    "speaker_4": {
        "outline": (0, 180, 0),
    },

    # Quinta persona
    "speaker_5": {
        "outline": (180, 0, 180),
    },

    # Sexta persona
    "speaker_6": {
        "outline": (255, 140, 0),
    },
}


DEFAULT_SPEAKER = "kuraimure"


def get_speaker_style(speaker: str) -> dict:
    """
    Devuelve el estilo correspondiente al hablante.

    Si Gemini devuelve un hablante que todavía no
    tenemos configurado, se utiliza el estilo por defecto.
    """

    if not speaker:
        speaker = DEFAULT_SPEAKER

    return SPEAKER_STYLES.get(
        speaker,
        SPEAKER_STYLES[DEFAULT_SPEAKER],
    )
