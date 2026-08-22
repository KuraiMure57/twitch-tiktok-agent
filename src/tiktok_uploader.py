import json
import os
import sys
from pathlib import Path

import requests


API_BASE = "https://open.tiktokapis.com"
OAUTH_TOKEN_URL = f"{API_BASE}/v2/oauth/token/"
INBOX_UPLOAD_URL = (
    f"{API_BASE}/v2/post/publish/inbox/video/init/"
)

CHUNK_SIZE = 10 * 1024 * 1024


class TikTokError(RuntimeError):
    pass


def get_access_token_from_refresh_token():
    client_key = os.environ.get(
        "TIKTOK_CLIENT_KEY"
    )

    client_secret = os.environ.get(
        "TIKTOK_CLIENT_SECRET"
    )

    refresh_token = os.environ.get(
        "TIKTOK_REFRESH_TOKEN"
    )

    if not client_key:
        raise TikTokError(
            "Falta el secret TIKTOK_CLIENT_KEY."
        )

    if not client_secret:
        raise TikTokError(
            "Falta el secret TIKTOK_CLIENT_SECRET."
        )

    if not refresh_token:
        raise TikTokError(
            "Falta el secret TIKTOK_REFRESH_TOKEN."
        )

    print(
        "Solicitando nuevo access token de TikTok..."
    )

    response = requests.post(
        OAUTH_TOKEN_URL,
        headers={
            "Content-Type": (
                "application/x-www-form-urlencoded"
            ),
        },
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=60,
    )

    print(
        "TikTok OAuth refresh: "
        f"HTTP {response.status_code}"
    )

    if not response.ok:
        raise TikTokError(
            "TikTok OAuth refresh falló: "
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    if data.get("error"):
        raise TikTokError(
            "TikTok OAuth devolvió un error: "
            f"{json.dumps(data, ensure_ascii=False)}"
        )

    access_token = data.get(
        "access_token"
    )

    if not access_token:
        raise TikTokError(
            "TikTok OAuth no devolvió access_token."
        )

    if data.get("refresh_token"):
        print(
            "TikTok ha devuelto un nuevo "
            "refresh token. Será necesario "
            "actualizar el GitHub Secret "
            "TIKTOK_REFRESH_TOKEN posteriormente."
        )

    print(
        "Access token de TikTok obtenido "
        "correctamente."
    )

    return access_token


def clean_hashtags(
    metadata,
):
    hashtags = metadata.get(
        "hashtags",
        [],
    )

    if not isinstance(hashtags, list):
        hashtags = []

    cleaned = []

    for hashtag in hashtags:

        if not isinstance(hashtag, str):
            continue

        hashtag = hashtag.strip()

        if not hashtag:
            continue

        if not hashtag.startswith("#"):
            hashtag = f"#{hashtag}"

        if hashtag not in cleaned:
            cleaned.append(hashtag)

    return cleaned


def optimize_hashtags(
    metadata,
):
    """
    Orden definitivo:

    1. Juego
    2. Contexto
    3. Gaming
    4. Twitch
    5. KuraiMure57

    Máximo 5 hashtags.
    """

    original = clean_hashtags(
        metadata
    )

    game = []
    context = []
    gaming = []
    twitch = []
    brand = []

    for hashtag in original:

        lower = hashtag.lower()

        if lower in (
            "#twitch",
            "#kuraimure57",
        ):
            continue

        if lower in (
            "#gaming",
            "#tiktokgaming",
        ):
            gaming.append(
                "#Gaming"
            )
            continue

        if lower in (
            "#gamingfails",
            "#gamingfail",
            "#funnygaming",
            "#rage",
            "#scarygaming",
            "#horror",
            "#wtf",
            "#fail",
        ):
            context.append(
                hashtag
            )
            continue

        game.append(
            hashtag
        )

    result = []

    def add_unique(items):
        for item in items:
            if item not in result:
                result.append(item)

    add_unique(game)

    add_unique(context)

    if gaming:
        add_unique(
            ["#Gaming"]
        )
    else:
        add_unique(
            ["#Gaming"]
        )

    add_unique(
        ["#Twitch"]
    )

    add_unique(
        ["#KuraiMure57"]
    )

    return result[:5]


def build_caption(
    metadata,
):
    title = str(
        metadata.get(
            "title",
            "",
        )
    ).strip()

    if not title:
        raise TikTokError(
            "metadata.json no contiene un título."
        )

    hashtags = optimize_hashtags(
        metadata
    )

    caption = title

    if hashtags:
        caption += "\n\n"
        caption += " ".join(
            hashtags
        )

    return caption


def validate_video(
    video_path,
):
    if not video_path.exists():
        raise FileNotFoundError(
            f"No existe el vídeo: {video_path}"
        )

    if video_path.stat().st_size == 0:
        raise TikTokError(
            "El vídeo está vacío."
        )

    if video_path.suffix.lower() != ".mp4":
        raise TikTokError(
            "TikTok uploader espera un MP4."
        )


def initialize_inbox_upload(
    access_token,
    video_path,
):
    video_size = (
        video_path.stat().st_size
    )

    chunk_size = min(
        CHUNK_SIZE,
        video_size,
    )

    total_chunks = (
        (video_size + chunk_size - 1)
        // chunk_size
    )

    payload = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        }
    }

    print("")
    print(
        "===== TIKTOK INBOX UPLOAD ====="
    )

    print(
        "Inicializando subida a TikTok Inbox..."
    )

    print(
        f"Tamaño vídeo: {video_size} bytes"
    )

    print(
        f"Tamaño chunk: {chunk_size} bytes"
    )

    print(
        f"Número de chunks: {total_chunks}"
    )

    response = requests.post(
        INBOX_UPLOAD_URL,
        headers={
            "Authorization": (
                f"Bearer {access_token}"
            ),
            "Content-Type": (
                "application/json; charset=UTF-8"
            ),
        },
        json=payload,
        timeout=60,
    )

    print(
        "TikTok Inbox init: "
        f"HTTP {response.status_code}"
    )

    if not response.ok:
        raise TikTokError(
            "TikTok rechazó la inicialización "
            "del Inbox upload: "
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    if data.get("error", {}).get(
        "code"
    ) not in (
        None,
        "",
        "ok",
    ):
        raise TikTokError(
            "TikTok API error al inicializar "
            "Inbox upload: "
            f"{json.dumps(data, ensure_ascii=False)}"
        )

    result = data.get(
        "data",
        {},
    )

    publish_id = result.get(
        "publish_id"
    )

    upload_url = result.get(
        "upload_url"
    )

    if not publish_id:
        raise TikTokError(
            "TikTok no devolvió publish_id."
        )

    if not upload_url:
        raise TikTokError(
            "TikTok no devolvió upload_url."
        )

    print(
        f"Publish ID: {publish_id}"
    )

    print(
        "Upload URL recibida correctamente."
    )

    print(
        "================================"
    )

    return {
        "publish_id": publish_id,
        "upload_url": upload_url,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
    }


def upload_video(
    upload_url,
    video_path,
    chunk_size,
):
    total_size = (
        video_path.stat().st_size
    )

    with video_path.open(
        "rb"
    ) as file:

        start = 0
        chunk_number = 0

        while start < total_size:

            chunk = file.read(
                chunk_size
            )

            if not chunk:
                break

            end = (
                start
                + len(chunk)
                - 1
            )

            headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(
                    len(chunk)
                ),
                "Content-Range": (
                    f"bytes {start}-{end}/"
                    f"{total_size}"
                ),
            }

            print(
                f"Subiendo TikTok Inbox: "
                f"chunk {chunk_number + 1} "
                f"→ {end + 1}/{total_size} bytes"
            )

            response = requests.put(
                upload_url,
                headers=headers,
                data=chunk,
                timeout=300,
            )

            print(
                "TikTok upload: "
                f"HTTP {response.status_code}"
            )

            if not response.ok:
                raise TikTokError(
                    "Error subiendo vídeo "
                    "a TikTok Inbox: "
                    f"{response.status_code} "
                    f"{response.text}"
                )

            start = end + 1
            chunk_number += 1

    if start != total_size:
        raise TikTokError(
            "La subida del vídeo no se "
            "completó correctamente."
        )

    print("")
    print(
        "Vídeo subido completamente "
        "a TikTok Inbox."
    )


def publish(
    access_token,
    video_path,
    metadata_path,
):
    video_path = Path(
        video_path
    )

    metadata_path = Path(
        metadata_path
    )

    validate_video(
        video_path
    )

    with metadata_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        metadata = json.load(
            file
        )

    caption = build_caption(
        metadata
    )

    print("")
    print(
        "===== TIKTOK CAPTION ====="
    )

    print(caption)

    print(
        "=========================="
    )

    print("")
    print(
        "El caption se conserva "
        "en los metadatos."
    )

    print(
        "TikTok Inbox permitirá "
        "continuar la edición desde la app."
    )

    upload = initialize_inbox_upload(
        access_token,
        video_path,
    )

    publish_id = upload[
        "publish_id"
    ]

    upload_url = upload[
        "upload_url"
    ]

    chunk_size = upload[
        "chunk_size"
    ]

    upload_video(
        upload_url,
        video_path,
        chunk_size,
    )

    result = {
        "status": "uploaded_to_inbox",
        "published": False,
        "publish_id": publish_id,
        "caption": caption,
    }

    print("")
    print(
        "======================================"
    )
    print(
        "✅ VÍDEO SUBIDO A TIKTOK INBOX"
    )
    print(
        "======================================"
    )
    print(
        "El vídeo NO se ha publicado."
    )
    print(
        "Puedes continuar la edición "
        "desde la aplicación de TikTok."
    )
    print(
        f"Publish ID: {publish_id}"
    )
    print(
        "======================================"
    )

    return result


if __name__ == "__main__":

    if len(sys.argv) != 3:

        print(
            "Uso:"
            " python src/tiktok_uploader.py"
            " final_tiktok.mp4"
            " metadata.json"
        )

        sys.exit(1)

    access_token = (
        get_access_token_from_refresh_token()
    )

    video_path = Path(
        sys.argv[1]
    )

    metadata_path = Path(
        sys.argv[2]
    )

    result = publish(
        access_token,
        video_path,
        metadata_path,
    )

    with open(
        "tiktok_result.json",
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("")
    print(
        "===== RESULTADO TIKTOK ====="
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    print(
        "============================="
    )
