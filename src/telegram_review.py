import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


DEFAULT_TIMEOUT_SECONDS = 2 * 60 * 60
POLL_TIMEOUT_SECONDS = 20


class TelegramError(RuntimeError):
    pass


def api_call(token: str, method: str, data=None, files=None):
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

    response.raise_for_status()
    payload = response.json()

    if not payload.get("ok"):
        raise TelegramError(
            f"Telegram API error in {method}: {payload}"
        )

    return payload["result"]


def clear_pending_updates(token: str) -> int | None:
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


def build_caption(metadata: dict) -> str:
    title = metadata.get("title") or "Clip para revisión"
    hook = metadata.get("hook") or ""
    description = metadata.get("description") or ""
    hashtags = metadata.get("hashtags") or []
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
    token: str,
    chat_id: str,
    video_path: Path,
    metadata: dict,
) -> int:
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
    token: str,
    callback_id: str,
    text: str,
) -> None:
    api_call(
        token,
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id,
            "text": text,
        },
    )


def edit_review_message(
    token: str,
    chat_id: str,
    message_id: int,
    caption: str,
) -> None:
    api_call(
        token,
        "editMessageCaption",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "caption": caption,
            "reply_markup": json.dumps(
                {"inline_keyboard": []}
            ),
        },
    )


def send_message(
    token: str,
    chat_id: str,
    text: str,
) -> None:
    api_call(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
        },
    )


def read_subtitles(path: Path) -> list[dict]:
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
    path: Path,
    segments: list[dict],
) -> None:
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
    segments: list[dict],
) -> str:
    lines = [
        "📝 Subtítulos actuales:",
        "",
    ]

    for index, segment in enumerate(
        segments,
        start=1,
    ):
        lines.append(
            f"{index}. "
            f"{segment['start']} → "
            f"{segment['end']}: "
            f"{segment['text']}"
        )

    lines.extend([
        "",
        "Envía la corrección así:",
        "1|Texto corregido",
        "2|Otro texto corregido",
        "",
        "Si solo hay un subtítulo, también puedes "
        "enviar directamente el texto nuevo.",
    ])

    return "\n".join(lines)


def apply_corrections(
    segments: list[dict],
    correction_text: str,
) -> tuple[list[dict], bool]:
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

    if (
        len(updated) == 1
        and "|" not in lines[0]
    ):
        updated[0]["text"] = lines[0]
        return updated, True

    changed = False

    for line in lines:
        if "|" not in line:
            continue

        index_text, new_text = line.split(
            "|",
            1,
        )

        try:
            index = int(index_text.strip())
        except ValueError:
            continue

        if not 1 <= index <= len(updated):
            continue

        new_text = new_text.strip()

        if not new_text:
            continue

        updated[index - 1]["text"] = new_text
        changed = True

    return updated, changed


def update_review_state(
    path: Path,
    status: str,
    correction: str | None = None,
) -> None:
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
    tiktok_video: Path,
    subtitles: Path,
    output_video: Path,
) -> None:
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
    token: str,
    offset: int | None,
) -> list[dict]:
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
    token: str,
    chat_id: str,
    video_path: Path,
    metadata_path: Path,
    review_state_path: Path,
    subtitles_path: Path,
    vertical_video_path: Path,
    timeout_seconds: int,
) -> str:
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
                    ).get("id", "")
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
                ).get("id", "")
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
                    "No he podido interpretar "
                    "la corrección.\n\n"
                    "Ejemplo:\n"
                    "1|¿Pero qué acaba de pasar?",
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
                "corrección. Revísalo de nuevo.",
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
