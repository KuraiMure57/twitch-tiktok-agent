# ============================================================
# CONFIGURACIÓN DE COLORES POR PERSONA
# ============================================================
#
# "outline" es el color del borde de las letras.
#
# Formato:
#   (R, G, B)
#
# ============================================================


SPEAKER_STYLES = {

    # --------------------------------------------------------
    # TU VOZ
    # --------------------------------------------------------
    #
    # Tu voz debe aparecer con borde AZUL.
    #
    "kuraimure": {
        "outline": (0, 102, 255),
    },

    # --------------------------------------------------------
    # SEGUNDA PERSONA
    # --------------------------------------------------------
    #
    # Speaker 2 debe aparecer con borde NEGRO.
    #
    "speaker_2": {
        "outline": (0, 0, 0),
    },

    # --------------------------------------------------------
    # TERCERA PERSONA
    # --------------------------------------------------------

    "speaker_3": {
        "outline": (255, 0, 0),
    },

    # --------------------------------------------------------
    # CUARTA PERSONA
    # --------------------------------------------------------

    "speaker_4": {
        "outline": (0, 180, 0),
    },

    # --------------------------------------------------------
    # QUINTA PERSONA
    # --------------------------------------------------------

    "speaker_5": {
        "outline": (180, 0, 180),
    },

    # --------------------------------------------------------
    # SEXTA PERSONA
    # --------------------------------------------------------

    "speaker_6": {
        "outline": (255, 140, 0),
    },
}


DEFAULT_SPEAKER = "kuraimure"


def get_speaker_style(
    speaker: str,
) -> dict:

    """
    Devuelve el estilo correspondiente al hablante.

    Si Gemini devuelve un hablante que todavía no
    tenemos configurado, se utiliza el estilo por defecto.
    """

    if not speaker:

        speaker = DEFAULT_SPEAKER

    return SPEAKER_STYLES.get(
        speaker,
        SPEAKER_STYLES[
            DEFAULT_SPEAKER
        ],
    )
