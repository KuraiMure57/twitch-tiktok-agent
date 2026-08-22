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


class TelegramError(RuntimeError):
    pass


def api_call(token, method, data=None, files=None):
    url = f"https://api.telegram.org/bot{token}/{method}"

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
            f"Telegram API error in {method}: {payload}"
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


def build_caption(metadata):
    title = metadata.get(
        "title",
        "Clip para revisión",
    )

    hook = metadata.get("hook", "")

    description = metadata.get(
        "description",
        "",
    )

    hashtags = metadata.get(
        "hashtags",
        [],
    )

    score = metadata.get("score")

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


def send_video(
    token,
    chat_id,
    video_path,
    metadata,
):
    if not video_path.exists():
        raise FileNotFoundError(
            f"No existe el vídeo: {video_path}"
        )

    size_mb = (
        video_path.stat().st_size
        / (1024 * 1024)
    )

    if size_mb > 50:
        raise ValueError(
            f"El vídeo pesa {size_mb:.2f} MB. "
            "Telegram limita sendVideo a 50 MB."
        )

    with video_path.open("rb") as video_file:
        result = api_call(
            token,
            "sendVideo",
            data={
                "chat_id": chat_id,
                "caption": build_caption(metadata),
                "supports_streaming": "true",
                "reply_markup": json.dumps(
                    review_keyboard(),
                    ensure_ascii=False,
                ),
            },
            files={
                "video": (
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


def read_subtitles(path):
    """
    Lee los subtítulos.

    Formato nuevo:

        start|end|speaker|text

    Ejemplo:

        0.000|2.500|kuraimure|Hola chicos

    También acepta el formato antiguo:

        start|end|text

    En ese caso se asigna automáticamente
    'kuraimure' como speaker para mantener
    compatibilidad con archivos antiguos.
    """

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

                speaker = speaker.strip()

                if not speaker:
                    speaker = DEFAULT_SPEAKER

            elif len(parts) == 3:

                start, end, text = parts

                speaker = DEFAULT_SPEAKER

            else:

                raise ValueError(
                    f"Línea de subtítulo no válida: {line}"
                )

            segments.append({
                "start": start,
                "end": end,
                "speaker": speaker,
                "text": text,
            })

    return segments


def write_subtitles(
    path,
    segments,
):
    """
    Guarda los subtítulos utilizando el formato:

        start|end|speaker|text
    """

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        for segment in segments:

            speaker = segment.get(
                "speaker",
                DEFAULT_SPEAKER,
            )

            if not speaker:
                speaker = DEFAULT_SPEAKER

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


def format_subtitles_for_telegram(
    segments,
):
    """
    Prepara la lista de subtítulos que se envía
    al usuario por Telegram.

    El speaker se muestra para poder saber qué color
    tiene cada frase.
    """

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

        speaker = segment.get(
            "speaker",
            DEFAULT_SPEAKER,
        )

        if not speaker:
            speaker = DEFAULT_SPEAKER

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
        "3. @speaker_3",
        "➡️ Cambia solo el color.",
        "",
        "✏️🎨 PARA CAMBIAR TEXTO + COLOR:",
        "",
        "3. @speaker_3 Texto corregido",
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
        "@speaker_2",
        "@speaker_3",
        "@speaker_4",
        "@speaker_5",
        "@speaker_6",
    ])

    return "\n".join(lines)


def parse_custom_time(value):
    """
    Formato:

    minutos.segundos

    Ejemplos:

    0.7  = 00:07
    0.12 = 00:12
    1.2  = 01:02
    1.15 = 01:15
    7    = 07:00
    7.5  = 07:05
    7.50 = 07:50
    """

    value = value.strip()

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


def parse_correction_line(line):
    """
    Formatos aceptados:

    Solo texto:

        3. Texto corregido

    Solo speaker/color:

        3. @speaker_3

    Texto + speaker/color:

        3. @speaker_3 Texto corregido

    Texto con tiempo:

        3. [0.4-0.5] Texto corregido

    Texto + speaker + tiempo:

        3. [0.4-0.5] @speaker_3 Texto corregido

    Nueva frase:

        2.1 Texto nuevo

    Nueva frase + speaker:

        2.1 @speaker_3 Texto nuevo

    Nueva frase con tiempo:

        2.1 [0.4-0.5] Texto nuevo

    Nueva frase con tiempo + speaker:

        2.1 [0.4-0.5] @speaker_3 Texto nuevo
    """

    line = line.strip()

    if not line:
        return None

    match = re.match(
        r"^(\d+)(?:\.(\d+))?\s*[\.\|]?\s*(.*)$",
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

    # ---------------------------------------------------------
    # TIEMPOS OPCIONALES
    # ---------------------------------------------------------

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

        content = time_match.group(3).strip()

    # ---------------------------------------------------------
    # SPEAKER OPCIONAL
    #
    # Ejemplos:
    #
    # @speaker_3
    # @speaker_3 Texto
    # ---------------------------------------------------------

    speaker = None

    speaker_match = re.match(
        r"^(@speaker_[A-Za-z0-9_-]+)"
        r"(?:\s+(.*))?$",
        content,
    )

    if speaker_match:

        speaker = speaker_match.group(1)[1:].strip()

        content = (
            speaker_match.group(2) or ""
        ).strip()

    return {
        "base_index": base_index,
        "insertion_index": insertion_index,
        "start": start,
        "end": end,
        "speaker": speaker,
        "text": content,
    }


def get_numeric_time(segment, key):
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
    """
    Reparte automáticamente el espacio disponible
    entre el subtítulo anterior y el siguiente.
    """

    previous_end = (
        get_numeric_time(
            previous_segment,
            "end",
        )
    )

    next_start = (
        get_numeric_time(
            next_segment,
            "start",
        )
        if next_segment is not None
        else previous_end + 3.0
    )

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

    duration = (
        usable / total
    )

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


def apply_corrections(
    segments,
    correction_text,
):
    """
    Aplica correcciones y permite cambiar:

        3. Texto corregido

    solo texto.

        3. @speaker_3

    solo speaker/color.

        3. @speaker_3 Texto corregido

    texto + speaker/color.

    También mantiene el sistema de inserciones:

        2.1 Texto
        2.2 Texto

    y tiempos manuales:

        2.1 [0.4-0.5] Texto
    """

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

    # ---------------------------------------------------------
    # ASEGURAR SPEAKER
    # ---------------------------------------------------------

    for segment in updated:

        speaker = segment.get(
            "speaker",
            DEFAULT_SPEAKER,
        )

        if not speaker:
            speaker = DEFAULT_SPEAKER

        segment["speaker"] = speaker

    changed = False

    # ---------------------------------------------------------
    # ASEGURAR ETIQUETAS BASE
    # ---------------------------------------------------------

    for index, segment in enumerate(
        updated,
        start=1,
    ):
        segment.setdefault(
            "_label",
            str(index),
        )

    # ---------------------------------------------------------
    # PRIMERO: CORRECCIONES NORMALES
    # ---------------------------------------------------------

    insertions = []

    for line in lines:

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

        # -----------------------------------------------------
        # INSERCIÓN JERÁRQUICA
        # -----------------------------------------------------

        if insertion_index is not None:

            # Una inserción puede tener solo speaker,
            # pero en ese caso no tendría sentido crear
            # un subtítulo sin texto.
            if not new_text:
                print(
                    f"No se puede insertar "
                    f"{base_index}.{insertion_index} "
                    f"sin texto."
                )
                continue

            insertions.append(
                {
                    "base_index": base_index,
                    "insertion_index": insertion_index,
                    "start": new_start,
                    "end": new_end,
                    "speaker": new_speaker,
                    "text": new_text,
                }
            )

            continue

        # -----------------------------------------------------
        # MODIFICAR SUBTÍTULO EXISTENTE
        # -----------------------------------------------------

        if base_index <= len(updated):

            segment = updated[
                base_index - 1
            ]

            # -------------------------------------------------
            # CAMBIO DE TIEMPO
            # -------------------------------------------------

            if new_start is not None:

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

            # -------------------------------------------------
            # CAMBIO DE SPEAKER
            # -------------------------------------------------

            if new_speaker is not None:

                segment["speaker"] = new_speaker

                changed = True

                print(
                    f"Speaker del subtítulo "
                    f"{base_index} cambiado a: "
                    f"{new_speaker}"
                )

            # -------------------------------------------------
            # CAMBIO DE TEXTO
            #
            # Si no hay texto pero sí speaker,
            # se conserva el texto existente.
            # -------------------------------------------------

            if new_text:

                segment["text"] = new_text

                changed = True

                print(
                    f"Texto del subtítulo "
                    f"{base_index} cambiado: "
                    f"{new_text}"
                )

            # -------------------------------------------------
            # ASEGURAR SPEAKER
            # -------------------------------------------------

            segment.setdefault(
                "speaker",
                DEFAULT_SPEAKER,
            )

            continue

        # -----------------------------------------------------
        # COMPATIBILIDAD CON EL SISTEMA ANTERIOR
        # -----------------------------------------------------

        if base_index == len(updated) + 1:

            if new_start is None or new_end is None:

                print(
                    f"No se puede añadir el "
                    f"subtítulo {base_index} sin tiempos."
                )

                continue

            if not new_text:

                print(
                    f"No se puede añadir el "
                    f"subtítulo {base_index} sin texto."
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

                speaker = new_speaker

            elif updated:

                speaker = updated[-1].get(
                    "speaker",
                    DEFAULT_SPEAKER,
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
                "_label": str(
                    base_index
                ),
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
            f"No se puede procesar la línea: {line}"
        )

    # ---------------------------------------------------------
    # PROCESAR INSERCIONES 2.1 / 2.2 / 3.1...
    # ---------------------------------------------------------

    grouped = {}

    for insertion in insertions:

        base_index = insertion[
            "base_index"
        ]

        grouped.setdefault(
            base_index,
            [],
        ).append(
            insertion
        )

    for base_index, group in grouped.items():

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

        # -----------------------------------------------------
        # ORDENAR 2.1, 2.2, 2.3...
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # SPEAKER POR DEFECTO DE LAS INSERCIONES
        #
        # Si no especificamos @speaker_X,
        # hereda el speaker anterior.
        # -----------------------------------------------------

        insertion_speaker = previous_segment.get(
            "speaker",
            DEFAULT_SPEAKER,
        )

        if not insertion_speaker:
            insertion_speaker = DEFAULT_SPEAKER

        # -----------------------------------------------------
        # VALIDAR ÍNDICES REPETIDOS
        # -----------------------------------------------------

        seen_indexes = set()

        for item in group:

            insertion_index = item[
                "insertion_index"
            ]

            if insertion_index in seen_indexes:

                print(
                    f"Índice duplicado: "
                    f"{base_index}.{insertion_index}"
                )

                continue

            seen_indexes.add(
                insertion_index
            )

        valid_group = [
            item
            for item in group
            if item["insertion_index"]
            in seen_indexes
        ]

        total = len(
            valid_group
        )

        if total == 0:
            continue

        # -----------------------------------------------------
        # CREAR LOS NUEVOS SEGMENTOS
        # -----------------------------------------------------

        new_segments = []

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

                final_speaker = item_speaker

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

        # -----------------------------------------------------
        # INSERTAR JUSTO DESPUÉS DEL SEGMENTO BASE
        # -----------------------------------------------------

        insertion_position = base_index

        updated[
            insertion_position:
            insertion_position
        ] = new_segments

        changed = True

    # ---------------------------------------------------------
    # ORDENAR POR TIEMPO
    # ---------------------------------------------------------

    updated.sort(
        key=lambda segment: float(
            segment["start"]
        )
    )

    return updated, changed


def update_review_state(
    path,
    status,
    correction=None,
):
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

    subprocess.run(
        command,
        check=True,
    )


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
    with metadata_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        metadata = json.load(file)

    segments = read_subtitles(
        subtitles_path
    )

    update_review_state(
        review_state_path,
        "pending",
    )

    offset = clear_pending_updates(
        token
    )

    message_id = send_video(
        token,
        chat_id,
        video_path,
        metadata,
    )

    print(
        "Vídeo enviado a Telegram para revisión."
    )

    deadline = (
        time.time()
        + timeout_seconds
    )

    waiting_for_correction = False

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

            if not waiting_for_correction:
                continue

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
                message.get("text", "")
                .strip()
            )

            if not correction_text:
                continue

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
                    "3. @speaker_3\n\n"
                    "Para cambiar texto + color:\n"
                    "3. @speaker_3 Texto corregido\n\n"
                    "Para añadir entre dos:\n"
                    "2.1 Texto nuevo\n"
                    "2.2 Otra frase\n\n"
                    "Para controlar el tiempo:\n"
                    "2.1 [0.4-0.5] Texto nuevo",
                )

                continue

            segments = updated_segments

            write_subtitles(
                subtitles_path,
                segments,
            )

            rerender_video(
                vertical_video_path,
                subtitles_path,
                video_path,
            )

            update_review_state(
                review_state_path,
                "revision_requested",
                correction_text,
            )

            update_review_state(
                review_state_path,
                "pending",
            )

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

    raise TimeoutError(
        "Se agotó el tiempo de espera "
        "de revisión de Telegram."
    )


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
        video_path=Path(sys.argv[1]),
        metadata_path=Path(sys.argv[2]),
        review_state_path=Path(sys.argv[3]),
        subtitles_path=Path(sys.argv[4]),
        vertical_video_path=Path(sys.argv[5]),
        timeout_seconds=int(sys.argv[6]),
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
