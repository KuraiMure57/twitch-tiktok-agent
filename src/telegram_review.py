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

            parts = line.split("|", 2)

            if len(parts) != 3:
                raise ValueError(
                    f"Línea de subtítulo no válida: {line}"
                )

            start, end, text = parts

            segments.append({
                "start": start,
                "end": end,
                "text": text,
            })

    return segments


def write_subtitles(
    path,
    segments,
):
    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        for segment in segments:
            file.write(
                f"{segment['start']}|"
                f"{segment['end']}|"
                f"{segment['text']}\n"
            )


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

        lines.append(
            f"{index}. {text}"
        )

    next_number = len(segments) + 1

    lines.extend([
        "",
        "✏️ PARA CORREGIR:",
        "",
        "1. Texto corregido",
        "2. Otro texto corregido",
        "",
        "➕ PARA AÑADIR TEXTO CON TIEMPOS:",
        "",
        f"{next_number}. [0.00-0.7] Texto nuevo",
        "",
        "⏱️ FORMATO DE TIEMPOS:",
        "Antes del punto = minutos",
        "Después del punto = segundos",
        "",
        "0.7 = 7 segundos",
        "0.12 = 12 segundos",
        "1.2 = 1 minuto y 2 segundos",
        "1.15 = 1 minuto y 15 segundos",
        "7 = 7 minutos",
        "7.50 = 7 minutos y 50 segundos",
        "",
        "Si no pones [inicio-fin],",
        "se mantienen los tiempos actuales.",
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

    1. Texto corregido

    2. Otro texto

    3. [0.00-0.7] Texto nuevo

    4. [1.2-1.15] Texto nuevo
    """

    line = line.strip()

    if not line:
        return None

    match = re.match(
        r"^(\d+)\s*[\.\|]?\s*(.*)$",
        line,
    )

    if not match:
        return None

    index = int(
        match.group(1)
    )

    content = match.group(2).strip()

    start = None
    end = None

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

    return (
        index,
        start,
        end,
        content,
    )


def apply_corrections(
    segments,
    correction_text,
):
    """
    Aplica correcciones y permite añadir
    nuevos subtítulos.

    Ejemplo:

    Si existen 2 subtítulos:

    1. Texto corregido
    2. Otro texto corregido
    3. [0.00-0.7] Texto nuevo

    El número 3 crea un nuevo segmento.
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

    changed = False

    for line in lines:

        parsed = parse_correction_line(
            line
        )

        if parsed is None:
            continue

        (
            index,
            new_start,
            new_end,
            new_text,
        ) = parsed

        # -------------------------------------------------
        # MODIFICAR UN SUBTÍTULO EXISTENTE
        # -------------------------------------------------

        if index <= len(updated):

            segment = updated[index - 1]

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

            segment["text"] = new_text

            changed = True

            continue

        # -------------------------------------------------
        # AÑADIR UN NUEVO SUBTÍTULO
        # -------------------------------------------------

        if index == len(updated) + 1:

            if new_start is None or new_end is None:

                print(
                    f"No se puede añadir el "
                    f"subtítulo {index} sin tiempos."
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

            updated.append({
                "start": format_seconds(
                    start_value
                ),
                "end": format_seconds(
                    end_value
                ),
                "text": new_text,
            })

            changed = True

            print(
                f"Nuevo subtítulo añadido: "
                f"{index}. "
                f"{new_start}-{new_end} "
                f"{new_text}"
            )

            continue

        # -------------------------------------------------
        # NÚMERO INCORRECTO
        # -------------------------------------------------

        print(
            f"No se puede procesar la línea: {line}"
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
                    "Para corregir:\n"
                    "1. Texto corregido\n\n"
                    "Para añadir texto nuevo:\n"
                    "3. [0.00-0.7] Texto nuevo",
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
