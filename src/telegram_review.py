import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


POLL_TIMEOUT_SECONDS = 20
DEFAULT_SPEAKER = "kuraimure"


# ============================================================
# ATAJOS DE SPEAKER
# ============================================================
#
# @1 = Kurai / kuraimure
# @2 = speaker_2
# @3 = speaker_3
# @4 = speaker_4
# @5 = speaker_5
# @6 = speaker_6
#
# También se aceptan los nombres completos.
# ============================================================

SPEAKER_ALIASES = {
    "1": "kuraimure",
    "2": "speaker_2",
    "3": "speaker_3",
    "4": "speaker_4",
    "5": "speaker_5",
    "6": "speaker_6",
}


class TelegramError(RuntimeError):
    pass


# ============================================================
# SPEAKERS
# ============================================================

def normalize_speaker(speaker):
    """
    Convierte:

        @1 -> kuraimure
        @2 -> speaker_2
        @3 -> speaker_3
        ...

    También acepta directamente:

        kuraimure
        speaker_2
        speaker_3
        ...

    El @ se elimina si viene incluido.
    """

    if not speaker:
        return DEFAULT_SPEAKER

    speaker = str(speaker).strip()

    if speaker.startswith("@"):
        speaker = speaker[1:]

    if speaker in SPEAKER_ALIASES:
        return SPEAKER_ALIASES[speaker]

    return speaker


def speaker_to_alias(speaker):
    """
    Convierte un speaker interno a su alias.

        kuraimure -> @1
        speaker_2 -> @2
        ...
    """

    speaker = normalize_speaker(speaker)

    for alias, real_speaker in SPEAKER_ALIASES.items():
        if real_speaker == speaker:
            return f"@{alias}"

    return f"@{speaker}"


def speaker_display_name(speaker):
    """
    Devuelve un nombre amigable.
    """

    speaker = normalize_speaker(speaker)

    if speaker == "kuraimure":
        return "Kurai (kuraimure) → negro"

    if speaker.startswith("speaker_"):
        number = speaker.replace("speaker_", "")
        return f"Speaker {number}"

    return speaker


# ============================================================
# TELEGRAM API
# ============================================================

def api_call(token, method, data=None, files=None):
    url = (
        f"https://api.telegram.org/bot"
        f"{token}/{method}"
    )

    if files:
        response = requests.post(
            url,
            data=data,
            files=files,
            timeout=120,
        )
    else:
        response = requests.post(
            url,
            json=data or {},
            timeout=60,
        )

    if not response.ok:
        print("RESPUESTA DE TELEGRAM:")
        print(response.text)

        raise TelegramError(
            f"Telegram API HTTP error in {method}: "
            f"{response.status_code} - {response.text}"
        )

    payload = response.json()

    if not payload.get("ok"):
        raise TelegramError(
            f"Telegram API error in {method}: "
            f"{payload}"
        )

    return payload["result"]


def clear_pending_updates(token):
    updates = api_call(
        token,
        "getUpdates",
        {
            "offset": -100,
            "limit": 100,
            "timeout": 0,
        },
    )

    if not updates:
        return None

    return max(
        update["update_id"]
        for update in updates
    ) + 1


# ============================================================
# MENSAJES
# ============================================================

def build_caption(metadata):
    title = metadata.get(
        "title",
        "Clip para revisión",
    )

    hook = metadata.get(
        "hook",
        "",
    )

    description = metadata.get(
        "description",
        "",
    )

    hashtags = metadata.get(
        "hashtags",
        [],
    )

    score = metadata.get(
        "score"
    )

    lines = [
        "🎬 CLIP PARA REVISAR",
        "",
        f"📌 Título: {title}",
    ]

    if hook:
        lines.append(
            f"🎯 Hook: {hook}"
        )

    if description:
        lines.extend([
            "",
            f"📝 Descripción: {description}",
        ])

    if score is not None:
        lines.extend([
            "",
            f"⭐ Puntuación: {score}/100",
        ])

    if hashtags:
        lines.extend([
            "",
            " ".join(hashtags),
        ])

    return "\n".join(lines)[:1024]


def review_keyboard():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Autorizar",
                    "callback_data": "approve",
                },
                {
                    "text": "✏️ Corregir texto",
                    "callback_data": "revise",
                },
            ],
            [
                {
                    "text": "❌ Descartar",
                    "callback_data": "reject",
                }
            ],
        ]
    }


# ============================================================
# ENVÍO DEL VÍDEO
# ============================================================

def send_video(token, chat_id, video_path, metadata):
    """
    Envía el vídeo final a Telegram.

    Hasta 50 MB:
        sendVideo

    Más de 50 MB:
        sendDocument

    Se utiliza requests directamente mediante api_call()
    para que Telegram reciba correctamente el archivo.
    """

    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(
            f"No se encontró el vídeo en: {video_path}"
        )

    file_size = video_path.stat().st_size

    # Convertimos metadata a texto antes de construir
    # los datos del envío para evitar pasar el diccionario
    # directamente como caption.
    caption = build_caption(metadata)

    if file_size > 50 * 1024 * 1024:
        method = "sendDocument"
        file_field_name = "document"
    else:
        method = "sendVideo"
        file_field_name = "video"

    data = {
        "chat_id": str(chat_id),
        "caption": caption,
        "reply_markup": json.dumps(
            review_keyboard(),
            ensure_ascii=False,
        ),
    }

    if method == "sendVideo":
        data["supports_streaming"] = "true"

    print(
        f"Enviando vídeo a Telegram: "
        f"{video_path.name} "
        f"({file_size / (1024 * 1024):.2f} MB)"
    )

    with video_path.open("rb") as video_file:
        result = api_call(
            token,
            method,
            data=data,
            files={
                file_field_name: (
                    video_path.name,
                    video_file,
                    "video/mp4",
                )
            },
        )

    return result["message_id"]


def answer_callback(
    token,
    callback_id,
    text,
):
    api_call(
        token,
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id,
            "text": text,
        },
    )


def edit_review_message(
    token,
    chat_id,
    message_id,
    caption,
):
    api_call(
        token,
        "editMessageCaption",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "caption": caption,
            "reply_markup": json.dumps(
                {
                    "inline_keyboard": []
                }
            ),
        },
    )


def send_message(
    token,
    chat_id,
    text,
):
    api_call(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
        },
    )


# ============================================================
# SUBTÍTULOS
# ============================================================

def read_subtitles(path):
    """
    Lee los subtítulos.

    Formato:

        start|end|speaker|text

    También acepta:

        start|end|text
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo de subtítulos: {path}"
        )

    segments = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:
            line = line.rstrip("\n")

            if not line.strip():
                continue

            parts = line.split("|", 3)

            if len(parts) == 4:
                start, end, speaker, text = parts

                speaker = normalize_speaker(
                    speaker
                )

            elif len(parts) == 3:
                start, end, text = parts

                speaker = DEFAULT_SPEAKER

            else:
                raise ValueError(
                    f"Línea de subtítulo no válida: {line}"
                )

            segments.append({
                "start": start.strip(),
                "end": end.strip(),
                "speaker": speaker,
                "text": text.strip(),
            })

    return segments


def write_subtitles(
    path,
    segments,
):
    """
    Guarda:

        start|end|speaker|text
    """

    path = Path(path)

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        for segment in segments:

            speaker = normalize_speaker(
                segment.get(
                    "speaker",
                    DEFAULT_SPEAKER,
                )
            )

            file.write(
                f"{segment['start']}|"
                f"{segment['end']}|"
                f"{speaker}|"
                f"{segment['text']}\n"
            )


def get_segment_label(
    segment,
    index,
):
    return segment.get(
        "_label",
        str(index),
    )


# ============================================================
# TEXTO DE AYUDA PARA TELEGRAM
# ============================================================

def format_subtitles_for_telegram(
    segments,
):
    lines = [
        "📝 SUBTÍTULOS ACTUALES",
        "",
    ]

    for index, segment in enumerate(
        segments,
        start=1,
    ):
        text = segment.get(
            "text",
            "",
        ).strip()

        if not text:
            text = "[sin texto]"

        speaker = normalize_speaker(
            segment.get(
                "speaker",
                DEFAULT_SPEAKER,
            )
        )

        label = get_segment_label(
            segment,
            index,
        )

        lines.append(
            f"{label}. [{speaker}] {text}"
        )

    lines.extend([
        "",
        "✏️ PARA CORREGIR EL TEXTO:",
        "",
        "3. Texto corregido",
        "➡️ Cambia solo el texto.",
        "",
        "🎨 PARA CAMBIAR SOLO EL COLOR/HABLANTE:",
        "",
        "3. @1",
        "➡️ Cambia solo el color/hablante.",
        "",
        "✏️🎨 PARA CAMBIAR TEXTO + COLOR:",
        "",
        "3. @1 Texto corregido",
        "",
        "🔄 PARA INTERCAMBIAR DOS SPEAKERS:",
        "",
        "@1 > @2",
        "➡️ Intercambia todos los @1 y @2.",
        "",
        "@2 > @3",
        "➡️ Intercambia todos los @2 y @3.",
        "",
        "Los demás speakers se mantienen igual.",
        "",
        "➕ PARA AÑADIR UNA FRASE ENTRE DOS:",
        "",
        "2.1 Texto nuevo",
        "2.2 Otra frase",
        "3.1 Una frase después del 3.",
        "",
        "El sistema calculará automáticamente "
        "el tiempo si existe espacio disponible.",
        "",
        "⏱️ SI QUIERES CONTROLAR EL TIEMPO:",
        "",
        "2.1 [0.4-0.5] Texto nuevo",
        "",
        "FORMATO:",
        "minutos.segundos",
        "",
        "0.7 = 7 segundos",
        "0.12 = 12 segundos",
        "1.2 = 1 minuto y 2 segundos",
        "1.15 = 1 minuto y 15 segundos",
        "",
        "También puedes añadir varias:",
        "2.1 Primera frase",
        "2.2 Segunda frase",
        "2.3 Tercera frase",
        "",
        "🎨 SPEAKERS:",
        "",
        "@1 → Kurai (kuraimure) → negro",
        "@2 → Speaker 2",
        "@3 → Speaker 3",
        "@4 → Speaker 4",
        "@5 → Speaker 5",
        "@6 → Speaker 6",
        "",
        "También puedes usar los nombres completos:",
        "@kuraimure",
        "@speaker_2",
        "@speaker_3",
        "@speaker_4",
        "@speaker_5",
        "@speaker_6",
    ])

    return "\n".join(lines)


# ============================================================
# TIEMPOS
# ============================================================

def parse_custom_time(value):
    """
    Convierte:

        0.7  -> 7 segundos
        0.12 -> 12 segundos
        1.2  -> 1 minuto + 2 segundos
        1.15 -> 1 minuto + 15 segundos

    También admite un número sin punto como minutos.
    """

    value = str(value).strip()

    if not value:
        raise ValueError(
            "Tiempo vacío."
        )

    if "." in value:

        parts = value.split(
            ".",
            1,
        )

        minutes_text = parts[0]
        seconds_text = parts[1]

        if not minutes_text.isdigit():
            raise ValueError(
                f"Minutos no válidos: {value}"
            )

        if not seconds_text.isdigit():
            raise ValueError(
                f"Segundos no válidos: {value}"
            )

        minutes = int(
            minutes_text
        )

        seconds = int(
            seconds_text
        )

        if seconds >= 60:
            raise ValueError(
                f"Los segundos deben estar "
                f"entre 0 y 59: {value}"
            )

        return (
            minutes * 60
            + seconds
        )

    if value.isdigit():
        return int(value) * 60

    raise ValueError(
        f"Tiempo no válido: {value}"
    )


def format_seconds(seconds):
    return f"{float(seconds):.3f}"


def get_numeric_time(
    segment,
    key,
):
    return float(
        segment.get(
            key,
            0,
        )
    )


def calculate_auto_time(
    previous_segment,
    next_segment,
    position,
    total,
):
    previous_end = get_numeric_time(
        previous_segment,
        "end",
    )

    if next_segment is not None:
        next_start = get_numeric_time(
            next_segment,
            "start",
        )
    else:
        next_start = previous_end + 3.0

    available = (
        next_start
        - previous_end
    )

    if available <= 0.05:
        raise ValueError(
            "No hay espacio suficiente entre "
            "los subtítulos para insertar "
            "la nueva frase automáticamente."
        )

    margin = min(
        0.03,
        available / 10,
    )

    usable = (
        available
        - (margin * 2)
    )

    if usable <= 0.05:
        raise ValueError(
            "El espacio disponible es demasiado "
            "pequeño para insertar el subtítulo."
        )

    duration = usable / total

    start = (
        previous_end
        + margin
        + (position * duration)
    )

    end = (
        previous_end
        + margin
        + ((position + 1) * duration)
    )

    return (
        start,
        end,
    )


# ============================================================
# PARSER DE CORRECCIONES
# ============================================================

def parse_correction_line(line):
    """
    Admite:

        3. Texto corregido
        3. @1
        3. @1 Texto corregido

        2.1 Texto nuevo
        2.2 Otra frase

        2.1 [0.4-0.5] Texto nuevo

        @1 > @2
        @2 > @3
    """

    line = line.strip()

    if not line:
        return None

    # ========================================================
    # INTERCAMBIO GLOBAL
    # ========================================================

    swap_match = re.match(
        r"^@([A-Za-z0-9_-]+)"
        r"\s*>\s*"
        r"@([A-Za-z0-9_-]+)"
        r"$",
        line,
        re.IGNORECASE,
    )

    if swap_match:

        speaker_a = normalize_speaker(
            swap_match.group(1)
        )

        speaker_b = normalize_speaker(
            swap_match.group(2)
        )

        return {
            "type": "swap",
            "speaker_a": speaker_a,
            "speaker_b": speaker_b,
        }

    # ========================================================
    # CORRECCIÓN NORMAL
    # ========================================================

    match = re.match(
        r"^(\d+)(?:\.(\d+))?"
        r"\s*[\.\|]?\s*(.*)$",
        line,
    )

    if not match:
        return None

    base_index = int(
        match.group(1)
    )

    insertion_index = (
        int(match.group(2))
        if match.group(2) is not None
        else None
    )

    content = match.group(3).strip()

    start = None
    end = None

    # ========================================================
    # TIEMPOS
    # ========================================================

    time_match = re.match(
        r"^\["
        r"\s*([0-9]+(?:\.[0-9]+)?)"
        r"\s*-\s*"
        r"([0-9]+(?:\.[0-9]+)?)"
        r"\s*\]"
        r"\s*(.*)$",
        content,
    )

    if time_match:

        start = time_match.group(1)
        end = time_match.group(2)

        content = (
            time_match.group(3)
            .strip()
        )

    # ========================================================
    # SPEAKER
    # ========================================================

    speaker = None

    speaker_match = re.match(
        r"^(@[A-Za-z0-9_-]+)"
        r"(?:\s+(.*))?$",
        content,
    )

    if speaker_match:

        speaker = normalize_speaker(
            speaker_match.group(1)
        )

        content = (
            speaker_match.group(2)
            or ""
        ).strip()

    return {
        "type": "normal",
        "base_index": base_index,
        "insertion_index": insertion_index,
        "start": start,
        "end": end,
        "speaker": speaker,
        "text": content,
    }


# ============================================================
# APLICAR CORRECCIONES
# ============================================================

def apply_corrections(
    segments,
    correction_text,
):
    lines = [
        line.strip()
        for line in correction_text.splitlines()
        if line.strip()
    ]

    if not lines:
        return segments, False

    updated = [
        dict(segment)
        for segment in segments
    ]

    # ========================================================
    # NORMALIZAR SPEAKERS
    # ========================================================

    for segment in updated:
        segment["speaker"] = normalize_speaker(
            segment.get(
                "speaker",
                DEFAULT_SPEAKER,
            )
        )

    # ========================================================
    # ASEGURAR ETIQUETAS
    # ========================================================

    for index, segment in enumerate(
        updated,
        start=1,
    ):
        segment.setdefault(
            "_label",
            str(index),
        )

    changed = False

    # ========================================================
    # PRIMERO: INTERCAMBIOS GLOBALES
    # ========================================================

    normal_lines = []

    for line in lines:

        parsed = parse_correction_line(
            line
        )

        if parsed is None:
            continue

        if parsed.get("type") == "swap":

            speaker_a = parsed[
                "speaker_a"
            ]

            speaker_b = parsed[
                "speaker_b"
            ]

            if speaker_a == speaker_b:
                print(
                    f"No se puede intercambiar "
                    f"el mismo speaker: "
                    f"{speaker_a}"
                )
                continue

            print(
                f"INTERCAMBIO GLOBAL: "
                f"{speaker_a} <-> {speaker_b}"
            )

            for segment in updated:

                current_speaker = normalize_speaker(
                    segment.get(
                        "speaker",
                        DEFAULT_SPEAKER,
                    )
                )

                if current_speaker == speaker_a:

                    segment["speaker"] = speaker_b
                    changed = True

                elif current_speaker == speaker_b:

                    segment["speaker"] = speaker_a
                    changed = True

            continue

        normal_lines.append(line)

    # ========================================================
    # CORRECCIONES NORMALES
    # ========================================================

    insertions = []

    for line in normal_lines:

        parsed = parse_correction_line(
            line
        )

        if parsed is None:
            continue

        base_index = parsed[
            "base_index"
        ]

        insertion_index = parsed[
            "insertion_index"
        ]

        new_start = parsed[
            "start"
        ]

        new_end = parsed[
            "end"
        ]

        new_speaker = parsed[
            "speaker"
        ]

        new_text = parsed[
            "text"
        ]

        # ====================================================
        # INSERCIÓN
        # ====================================================

        if insertion_index is not None:

            if not new_text:
                print(
                    f"No se puede insertar "
                    f"{base_index}.{insertion_index} "
                    f"sin texto."
                )
                continue

            insertions.append({
                "base_index": base_index,
                "insertion_index": insertion_index,
                "start": new_start,
                "end": new_end,
                "speaker": new_speaker,
                "text": new_text,
            })

            continue

        # ====================================================
        # MODIFICAR SUBTÍTULO EXISTENTE
        # ====================================================

        if 1 <= base_index <= len(updated):

            segment = updated[
                base_index - 1
            ]

            # ------------------------------------------------
            # CAMBIO DE TIEMPO
            # ------------------------------------------------

            if (
                new_start is not None
                and new_end is not None
            ):

                try:
                    start_value = parse_custom_time(
                        new_start
                    )

                    end_value = parse_custom_time(
                        new_end
                    )

                except ValueError as error:

                    print(
                        f"Tiempo no válido en "
                        f"'{line}': {error}"
                    )

                    continue

                if end_value <= start_value:

                    print(
                        f"El final debe ser mayor "
                        f"que el inicio: {line}"
                    )

                    continue

                segment["start"] = format_seconds(
                    start_value
                )

                segment["end"] = format_seconds(
                    end_value
                )

                changed = True

            # ------------------------------------------------
            # CAMBIO DE SPEAKER
            # ------------------------------------------------

            if new_speaker is not None:

                segment["speaker"] = normalize_speaker(
                    new_speaker
                )

                changed = True

                print(
                    f"Speaker del subtítulo "
                    f"{base_index} cambiado a: "
                    f"{segment['speaker']}"
                )

            # ------------------------------------------------
            # CAMBIO DE TEXTO
            # ------------------------------------------------

            if new_text:

                segment["text"] = new_text

                changed = True

                print(
                    f"Texto del subtítulo "
                    f"{base_index} cambiado: "
                    f"{new_text}"
                )

            continue

        # ====================================================
        # COMPATIBILIDAD CON SISTEMA ANTERIOR
        # ====================================================

        if base_index == len(updated) + 1:

            if (
                new_start is None
                or new_end is None
            ):

                print(
                    f"No se puede añadir el "
                    f"subtítulo {base_index} "
                    f"sin tiempos."
                )

                continue

            if not new_text:

                print(
                    f"No se puede añadir el "
                    f"subtítulo {base_index} "
                    f"sin texto."
                )

                continue

            try:

                start_value = parse_custom_time(
                    new_start
                )

                end_value = parse_custom_time(
                    new_end
                )

            except ValueError as error:

                print(
                    f"Tiempo no válido en "
                    f"'{line}': {error}"
                )

                continue

            if end_value <= start_value:

                print(
                    f"El final debe ser mayor "
                    f"que el inicio: {line}"
                )

                continue

            if new_speaker:

                speaker = normalize_speaker(
                    new_speaker
                )

            elif updated:

                speaker = normalize_speaker(
                    updated[-1].get(
                        "speaker",
                        DEFAULT_SPEAKER,
                    )
                )

            else:

                speaker = DEFAULT_SPEAKER

            updated.append({
                "start": format_seconds(
                    start_value
                ),
                "end": format_seconds(
                    end_value
                ),
                "speaker": speaker,
                "text": new_text,
                "_label": str(base_index),
            })

            changed = True

            print(
                f"Nuevo subtítulo añadido: "
                f"{base_index}. "
                f"[{speaker}] "
                f"{new_start}-{new_end} "
                f"{new_text}"
            )

            continue

        print(
            f"No se puede procesar la línea: "
            f"{line}"
        )

    # ========================================================
    # INSERTAR 2.1 / 2.2 / 3.1...
    #
    # Se procesan de mayor índice a menor para que insertar
    # un bloque no cambie la posición de los bloques anteriores.
    # ========================================================

    grouped = {}

    for insertion in insertions:

        base_index = insertion[
            "base_index"
        ]

        grouped.setdefault(
            base_index,
            [],
        ).append(insertion)

    for base_index in sorted(
        grouped.keys(),
        reverse=True,
    ):

        group = grouped[
            base_index
        ]

        if base_index < 1:

            print(
                f"Índice base no válido: "
                f"{base_index}"
            )

            continue

        if base_index > len(updated):

            print(
                f"No existe el subtítulo "
                f"{base_index} para insertar "
                f"una frase después de él."
            )

            continue

        group.sort(
            key=lambda item: item[
                "insertion_index"
            ]
        )

        previous_segment = updated[
            base_index - 1
        ]

        if base_index < len(updated):

            next_segment = updated[
                base_index
            ]

        else:

            next_segment = None

        insertion_speaker = normalize_speaker(
            previous_segment.get(
                "speaker",
                DEFAULT_SPEAKER,
            )
        )

        # ----------------------------------------------------
        # ELIMINAR ÍNDICES DUPLICADOS
        # ----------------------------------------------------

        seen_indexes = set()
        valid_group = []

        for item in group:

            insertion_index = item[
                "insertion_index"
            ]

            if insertion_index in seen_indexes:

                print(
                    f"Índice duplicado: "
                    f"{base_index}."
                    f"{insertion_index}"
                )

                continue

            seen_indexes.add(
                insertion_index
            )

            valid_group.append(item)

        total = len(valid_group)

        if total == 0:
            continue

        new_segments = []

        # ----------------------------------------------------
        # CREAR NUEVOS SEGMENTOS
        # ----------------------------------------------------

        for position, item in enumerate(
            valid_group
        ):

            manual_start = item[
                "start"
            ]

            manual_end = item[
                "end"
            ]

            item_speaker = item.get(
                "speaker"
            )

            if item_speaker:

                final_speaker = normalize_speaker(
                    item_speaker
                )

            else:

                final_speaker = insertion_speaker

            try:

                if (
                    manual_start is not None
                    and manual_end is not None
                ):

                    start_value = parse_custom_time(
                        manual_start
                    )

                    end_value = parse_custom_time(
                        manual_end
                    )

                else:

                    start_value, end_value = (
                        calculate_auto_time(
                            previous_segment,
                            next_segment,
                            position,
                            total,
                        )
                    )

            except ValueError as error:

                print(
                    f"No se puede insertar "
                    f"{base_index}."
                    f"{item['insertion_index']}: "
                    f"{error}"
                )

                continue

            if end_value <= start_value:

                print(
                    f"Tiempo inválido para "
                    f"{base_index}."
                    f"{item['insertion_index']}"
                )

                continue

            label = (
                f"{base_index}."
                f"{item['insertion_index']}"
            )

            new_segments.append({
                "start": format_seconds(
                    start_value
                ),
                "end": format_seconds(
                    end_value
                ),
                "speaker": final_speaker,
                "text": item["text"],
                "_label": label,
            })

            print(
                f"Nuevo subtítulo {label}: "
                f"[{final_speaker}] "
                f"{format_seconds(start_value)}-"
                f"{format_seconds(end_value)} "
                f"{item['text']}"
            )

        if not new_segments:
            continue

        # Insertar inmediatamente después del
        # subtítulo base.
        insertion_position = base_index

        updated[
            insertion_position:
            insertion_position
        ] = new_segments

        changed = True

    # ========================================================
    # ORDENAR CRONOLÓGICAMENTE
    # ========================================================

    updated.sort(
        key=lambda segment: float(
            segment["start"]
        )
    )

    return updated, changed


# ============================================================
# ESTADO DE REVISIÓN
# ============================================================

def update_review_state(
    path,
    status,
    correction=None,
):
    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        state = json.load(file)

    now = datetime.now(
        timezone.utc
    ).isoformat()

    state["status"] = status
    state["updated_at"] = now

    if status == "revision_requested":

        state["revision_count"] = state.get(
            "revision_count",
            0,
        ) + 1

        if correction:

            state.setdefault(
                "corrections",
                [],
            ).append({
                "timestamp": now,
                "text": correction,
            })

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# REGENERAR VÍDEO
# ============================================================

def rerender_video(
    tiktok_video,
    subtitles,
    output_video,
):
    command = [
        sys.executable,
        "src/subtitle_burner.py",
        str(tiktok_video),
        str(subtitles),
        str(output_video),
    ]

    print(
        "Regenerando vídeo con los subtítulos..."
    )

    subprocess.run(
        command,
        check=True,
    )


# ============================================================
# TELEGRAM UPDATES
# ============================================================

def get_updates(
    token,
    offset,
):
    data = {
        "limit": 100,
        "timeout": POLL_TIMEOUT_SECONDS,
    }

    if offset is not None:
        data["offset"] = offset

    return api_call(
        token,
        "getUpdates",
        data,
    )


# ============================================================
# FLUJO PRINCIPAL DE REVISIÓN
# ============================================================

def run_review(
    token,
    chat_id,
    video_path,
    metadata_path,
    review_state_path,
    subtitles_path,
    vertical_video_path,
    timeout_seconds,
):
    """
    Flujo:

    1. Lee metadata y subtítulos.
    2. Pone el estado en pending.
    3. Limpia mensajes anteriores de Telegram.
    4. Envía el vídeo.
    5. Espera autorización, descarte o corrección.
    6. Si hay corrección:
       - modifica subtítulos
       - regenera vídeo
       - vuelve a enviarlo
    7. Continúa hasta aprobar, descartar o agotar timeout.
    """

    video_path = Path(video_path)
    metadata_path = Path(metadata_path)
    review_state_path = Path(review_state_path)
    subtitles_path = Path(subtitles_path)
    vertical_video_path = Path(
        vertical_video_path
    )

    # ========================================================
    # LEER METADATA
    # ========================================================

    with metadata_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        metadata = json.load(file)

    # ========================================================
    # LEER SUBTÍTULOS
    # ========================================================

    segments = read_subtitles(
        subtitles_path
    )

    # ========================================================
    # ESTADO INICIAL
    # ========================================================

    update_review_state(
        review_state_path,
        "pending",
    )

    # ========================================================
    # LIMPIAR UPDATES ANTERIORES
    # ========================================================

    offset = clear_pending_updates(
        token
    )

    # ========================================================
    # ENVIAR VÍDEO
    # ========================================================

    message_id = send_video(
        token,
        chat_id,
        video_path,
        metadata,
    )

    print(
        "Vídeo enviado a Telegram para revisión."
    )

    # ========================================================
    # TIMEOUT
    # ========================================================

    deadline = (
        time.time()
        + timeout_seconds
    )

    waiting_for_correction = False

    # ========================================================
    # BUCLE DE REVISIÓN
    # ========================================================

    while time.time() < deadline:

        updates = get_updates(
            token,
            offset,
        )

        for update in updates:

            offset = (
                update["update_id"]
                + 1
            )

            # =================================================
            # CALLBACKS DE BOTONES
            # =================================================

            callback = update.get(
                "callback_query"
            )

            if callback:

                message = (
                    callback.get("message")
                    or {}
                )

                callback_chat = str(
                    message.get(
                        "chat",
                        {},
                    ).get(
                        "id",
                        "",
                    )
                )

                if callback_chat != str(
                    chat_id
                ):
                    continue

                data = callback.get(
                    "data"
                )

                # =============================================
                # AUTORIZAR
                # =============================================

                if data == "approve":

                    answer_callback(
                        token,
                        callback["id"],
                        "Clip autorizado.",
                    )

                    edit_review_message(
                        token,
                        chat_id,
                        message_id,
                        "✅ CLIP AUTORIZADO",
                    )

                    update_review_state(
                        review_state_path,
                        "approved",
                    )

                    return "approved"

                # =============================================
                # DESCARTAR
                # =============================================

                if data == "reject":

                    answer_callback(
                        token,
                        callback["id"],
                        "Clip descartado.",
                    )

                    edit_review_message(
                        token,
                        chat_id,
                        message_id,
                        "❌ CLIP DESCARTADO",
                    )

                    update_review_state(
                        review_state_path,
                        "rejected",
                    )

                    return "rejected"

                # =============================================
                # CORREGIR
                # =============================================

                if data == "revise":

                    answer_callback(
                        token,
                        callback["id"],
                        "Envíame ahora la corrección.",
                    )

                    update_review_state(
                        review_state_path,
                        "revision_requested",
                    )

                    send_message(
                        token,
                        chat_id,
                        format_subtitles_for_telegram(
                            segments
                        ),
                    )

                    waiting_for_correction = True

                    continue

            # =================================================
            # SI NO ESTAMOS ESPERANDO CORRECCIÓN
            # =================================================

            if not waiting_for_correction:
                continue

            # =================================================
            # MENSAJE DE TEXTO
            # =================================================

            message = (
                update.get("message")
                or {}
            )

            message_chat = str(
                message.get(
                    "chat",
                    {},
                ).get(
                    "id",
                    "",
                )
            )

            if message_chat != str(
                chat_id
            ):
                continue

            correction_text = (
                message.get(
                    "text",
                    "",
                )
                .strip()
            )

            if not correction_text:
                continue

            # =================================================
            # APLICAR CORRECCIÓN
            # =================================================

            updated_segments, changed = (
                apply_corrections(
                    segments,
                    correction_text,
                )
            )

            if not changed:

                send_message(
                    token,
                    chat_id,
                    "❌ No he podido interpretar "
                    "la corrección.\n\n"

                    "Para cambiar solo el texto:\n"
                    "3. Texto corregido\n\n"

                    "Para cambiar solo el color/hablante:\n"
                    "3. @1\n\n"

                    "Para cambiar texto + color:\n"
                    "3. @1 Texto corregido\n\n"

                    "Para intercambiar speakers:\n"
                    "@1 > @2\n"
                    "➡️ Intercambia todos los @1 y @2.\n\n"

                    "Los demás speakers se mantienen igual.\n\n"

                    "Para añadir entre dos:\n"
                    "2.1 Texto nuevo\n"
                    "2.2 Otra frase\n\n"

                    "Para controlar el tiempo:\n"
                    "2.1 [0.4-0.5] Texto nuevo\n\n"

                    "🎨 SPEAKERS:\n"
                    "@1 → Kurai (kuraimure) → negro\n"
                    "@2 → Speaker 2\n"
                    "@3 → Speaker 3\n"
                    "@4 → Speaker 4\n"
                    "@5 → Speaker 5\n"
                    "@6 → Speaker 6",
                )

                continue

            # =================================================
            # ACTUALIZAR SEGMENTOS
            # =================================================

            segments = updated_segments

            # =================================================
            # GUARDAR SUBTÍTULOS
            # =================================================

            write_subtitles(
                subtitles_path,
                segments,
            )

            # =================================================
            # REGENERAR VÍDEO
            # =================================================

            rerender_video(
                vertical_video_path,
                subtitles_path,
                video_path,
            )

            # =================================================
            # GUARDAR HISTORIAL DE CORRECCIÓN
            # =================================================

            update_review_state(
                review_state_path,
                "revision_requested",
                correction_text,
            )

            # Volvemos a pending mientras
            # esperamos la nueva revisión.
            update_review_state(
                review_state_path,
                "pending",
            )

            # =================================================
            # ENVIAR NUEVO VÍDEO
            # =================================================

            message_id = send_video(
                token,
                chat_id,
                video_path,
                metadata,
            )

            send_message(
                token,
                chat_id,
                "🔄 Vídeo regenerado con tu "
                "corrección.\n\n"
                "Revísalo de nuevo y "
                "autorízalo cuando esté listo.",
            )

            waiting_for_correction = False

            print(
                "Vídeo regenerado tras corrección."
            )

    # ========================================================
    # TIMEOUT
    # ========================================================

    raise TimeoutError(
        "Se agotó el tiempo de espera "
        "de revisión de Telegram."
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 7:

        print(
            "Uso: python src/telegram_review.py "
            "<video.mp4> "
            "<metadata.json> "
            "<review_state.json> "
            "<final_subtitles.txt> "
            "<tiktok_clip.mp4> "
            "<timeout_seconds>"
        )

        sys.exit(1)

    token = os.environ.get(
        "TELEGRAM_BOT_TOKEN"
    )

    chat_id = os.environ.get(
        "TELEGRAM_CHAT_ID"
    )

    if not token:

        raise RuntimeError(
            "Falta TELEGRAM_BOT_TOKEN."
        )

    if not chat_id:

        raise RuntimeError(
            "Falta TELEGRAM_CHAT_ID."
        )

    result = run_review(
        token=token,
        chat_id=chat_id,
        video_path=Path(
            sys.argv[1]
        ),
        metadata_path=Path(
            sys.argv[2]
        ),
        review_state_path=Path(
            sys.argv[3]
        ),
        subtitles_path=Path(
            sys.argv[4]
        ),
        vertical_video_path=Path(
            sys.argv[5]
        ),
        timeout_seconds=int(
            sys.argv[6]
        ),
    )

    with open(
        "review_result.txt",
        "w",
        encoding="utf-8",
    ) as file:

        file.write(result)

    print(
        f"Resultado de revisión: {result}"
    )