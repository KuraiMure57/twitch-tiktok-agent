import json
import os
import sys
import time
from pathlib import Path

import requests


API_BASE = "https://open.tiktokapis.com"
OAUTH_TOKEN_URL = f"{API_BASE}/v2/oauth/token/"


class TikTokError(RuntimeError):
    pass


def get_access_token_from_refresh_token():
    client_key = os.environ.get("TIKTOK_CLIENT_KEY")
    client_secret = os.environ.get("TIKTOK_CLIENT_SECRET")
    refresh_token = os.environ.get("TIKTOK_REFRESH_TOKEN")

    if not client_key:
        raise TikTokError("Falta el secret TIKTOK_CLIENT_KEY.")

    if not client_secret:
        raise TikTokError("Falta el secret TIKTOK_CLIENT_SECRET.")

    if not refresh_token:
        raise TikTokError("Falta el secret TIKTOK_REFRESH_TOKEN.")

    print("Solicitando nuevo access token de TikTok...")

    response = requests.post(
        OAUTH_TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=60,
    )

    print(f"TikTok OAuth refresh: HTTP {response.status_code}")

    if not response.ok:
        raise TikTokError(
            f"TikTok OAuth refresh falló: HTTP {response.status_code}: {response.text}"
        )

    data = response.json()

    if data.get("error"):
        raise TikTokError(
            f"TikTok OAuth devolvió un error: {json.dumps(data, ensure_ascii=False)}"
        )

    access_token = data.get("access_token")

    if not access_token:
        raise TikTokError("TikTok OAuth no devolvió access_token.")

    if data.get("refresh_token"):
        print(
            "TikTok ha devuelto un nuevo refresh token. Será necesario "
            "actualizar el GitHub Secret TIKTOK_REFRESH_TOKEN posteriormente."
        )

    print("Access token de TikTok obtenido correctamente.")

    return access_token


def api_post(access_token, endpoint, payload):
    response = requests.post(
        f"{API_BASE}{endpoint}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json=payload,
        timeout=60,
    )

    print(f"TikTok {endpoint}: HTTP {response.status_code}")

    if not response.ok:
        raise TikTokError(f"TikTok HTTP {response.status_code}: {response.text}")

    data = response.json()

    if data.get("error", {}).get("code") not in (None, "", "ok"):
        raise TikTokError(
            f"TikTok API error: {json.dumps(data, ensure_ascii=False)}"
        )

    return data


def query_creator_info(access_token):
    return api_post(
        access_token,
        "/v2/post/publish/creator_info/query/",
        {},
    )


def clean_hashtags(metadata):
    hashtags = metadata.get("hashtags", [])

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


def optimize_hashtags(metadata):
    """
    Orden definitivo:

    1. Juego
    2. Contexto
    3. Gaming
    4. Twitch
    5. KuraiMure57

    Máximo 5 hashtags.
    """

    original = clean_hashtags(metadata)

    game = []
    context = []
    gaming = []
    twitch = []
    brand = []

    for hashtag in original:
        lower = hashtag.lower()

        if lower in ("#twitch", "#kuraimure57"):
            continue

        if lower in ("#gaming", "#tiktokgaming"):
            gaming.append("#Gaming")
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
            context.append(hashtag)
            continue

        game.append(hashtag)

    result = []

    def add_unique(items):
        for item in items:
            if item not in result:
                result.append(item)

    add_unique(game)
    add_unique(context)

    if gaming:
        add_unique(["#Gaming"])
    else:
        add_unique(["#Gaming"])

    add_unique(["#Twitch"])
    add_unique(["#KuraiMure57"])

    return result[:5]


def build_caption(metadata):
    title = str(metadata.get("title", "")).strip()

    if not title:
        raise TikTokError("metadata.json no contiene un título.")

    hashtags = optimize_hashtags(metadata)

    caption = title

    if hashtags:
        caption += "\n\n"
        caption += " ".join(hashtags)

    return caption


def validate_video(video_path):
    if not video_path.exists():
        raise FileNotFoundError(f"No existe el vídeo: {video_path}")

    if video_path.stat().st_size == 0:
        raise TikTokError("El vídeo está vacío.")

    if video_path.suffix.lower() != ".mp4":
        raise TikTokError("TikTok uploader espera un MP4.")


def initialize_direct_post(access_token, creator_info, video_path, caption):
    """
    Inicializa la subida hacia el endpoint de la bandeja de entrada (Inbox/Borradores).
    Esto permite a cuentas públicas usar el bot sin requerir una auditoría de la API.
    Nota: Se omiten títulos y configuraciones de interacción ya que el endpoint de Inbox
    no los acepta en el payload de inicialización.
    """
    video_size = video_path.stat().st_size
    chunk_size = video_size
    total_chunks = 1

    payload = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        },
    }

    print("Inicializando subida en modo Borrador (TikTok Inbox API)...")

    # Cambiado al endpoint correcto para enviar a borradores / bandeja de entrada
    return api_post(
        access_token,
        "/v2/post/publish/inbox/video/init/",
        payload,
    )


def upload_video(upload_url, video_path, chunk_size=None):
    total_size = video_path.stat().st_size

    if chunk_size is None:
        chunk_size = total_size

    with video_path.open("rb") as file:
        start = 0

        while start < total_size:
            chunk = file.read(chunk_size)

            if not chunk:
                break

            end = start + len(chunk)

            headers = {
                "Content-Range": f"bytes {start}-{end-1}/{total_size}",
                "Content-Type": "video/mp4",
            }

            response = requests.put(
                upload_url,
                headers=headers,
                data=chunk,
                timeout=60,
            )

            print(
                f"Chunk {start}-{end-1}/{total_size}: HTTP {response.status_code}"
            )

            if response.status_code not in (200, 201, 308):
                raise TikTokError(
                    f"Subida de chunk falló: HTTP {response.status_code}: {response.text}"
                )

            start = end


def main():
    if len(sys.argv) < 3:
        print(f"Uso: {sys.argv[0]} <ruta_video> <ruta_metadata_json>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    metadata_path = Path(sys.argv[2])

    try:
        validate_video(video_path)

        with metadata_path.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

        caption = build_caption(metadata)

        print("\n===== TIKTOK CAPTION =====")
        print(caption)
        print("==========================\n")

        access_token = get_access_token_from_refresh_token()
        creator_info = query_creator_info(access_token)

        account_name = creator_info.get("data", {}).get("username", "Desconocida")
        print(f"Cuenta TikTok: @{account_name}")

        init_data = initialize_direct_post(
            access_token, creator_info, video_path, caption
        )

        upload_url = init_data.get("data", {}).get("upload_url")
        if not upload_url:
            raise TikTokError("No se recibió la URL de subida de TikTok.")

        print("Subiendo vídeo...")
        upload_video(upload_url, video_path)
        print("Vídeo enviado correctamente a los borradores de TikTok.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
