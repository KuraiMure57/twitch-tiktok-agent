import json
import os
import sys
import time
from pathlib import Path

import requests


API_BASE = "https://open.tiktokapis.com"

MAX_SINGLE_CHUNK_SIZE = 64 * 1024 * 1024
DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024
MIN_CHUNK_SIZE = 5 * 1024 * 1024


class TikTokError(RuntimeError):
    pass


def api_post(
    access_token,
    endpoint,
    payload,
):
    response = requests.post(
        f"{API_BASE}{endpoint}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json=payload,
        timeout=60,
    )

    print(
        f"TikTok {endpoint}: "
        f"HTTP {response.status_code}"
    )

    if not response.ok:
        raise TikTokError(
            f"TikTok HTTP {response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    if data.get("error", {}).get("code") not in (
        None,
        "",
        "ok",
    ):
        raise TikTokError(
            f"TikTok API error: "
            f"{json.dumps(data, ensure_ascii=False)}"
        )

    return data


def query_creator_info(
    access_token,
):
    return api_post(
        access_token,
        "/v2/post/publish/creator_info/query/",
        {},
    )


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


def calculate_upload_chunks(
    video_size,
):
    """
    Calculate the chunk size and total number of chunks
    according to TikTok Content Posting API restrictions.

    TikTok requires:
    - Chunks of at least 5 MB and at most 64 MB.
    - Videos smaller than 5 MB must be uploaded as one chunk
      whose size equals the complete video.
    - A single chunk can also contain the complete video when
      the video is 64 MB or smaller.
    - Videos larger than 64 MB are split into multiple chunks.
    """

    if video_size <= 0:
        raise TikTokError(
            "El tamaño del vídeo debe ser mayor que cero."
        )

    # For videos up to 64 MB, upload the entire file
    # as a single chunk. This also handles videos smaller
    # than TikTok's 5 MB minimum chunk size.
    if video_size <= MAX_SINGLE_CHUNK_SIZE:
        return video_size, 1

    # Videos larger than 64 MB require multiple chunks.
    chunk_size = DEFAULT_CHUNK_SIZE

    total_chunks = (
        video_size + chunk_size - 1
    ) // chunk_size

    remainder = (
        video_size % chunk_size
    )

    # If the final remainder would be smaller than 5 MB,
    # merge it into the previous chunk. This keeps every
    # non-final chunk at least 5 MB and follows TikTok's
    # trailing-byte handling rules.
    if (
        remainder != 0
        and remainder < MIN_CHUNK_SIZE
    ):
        total_chunks -= 1

    return chunk_size, total_chunks


def initialize_direct_post(
    access_token,
    creator_info,
    video_path,
    caption,
):
    privacy_options = creator_info[
        "data"
    ].get(
        "privacy_level_options",
        [],
    )

    if not privacy_options:
        raise TikTokError(
            "TikTok no devolvió opciones de privacidad."
        )

    preferred_privacy = (
        "PUBLIC_TO_EVERYONE"
    )

    if preferred_privacy not in privacy_options:
        raise TikTokError(
            "PUBLIC_TO_EVERYONE no está "
            "disponible para esta cuenta. "
            f"Opciones: {privacy_options}"
        )

    video_size = (
        video_path.stat().st_size
    )

    chunk_size, total_chunks = (
        calculate_upload_chunks(
            video_size
        )
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

    payload = {
        "post_info": {
            "title": caption,
            "privacy_level": preferred_privacy,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        },
    }

    return api_post(
        access_token,
        "/v2/post/publish/video/init/",
        payload,
    )


def upload_video(
    upload_url,
    video_path,
    chunk_size=None,
):
    total_size = (
        video_path.stat().st_size
    )

    if chunk_size is None:
        chunk_size, _ = (
            calculate_upload_chunks(
                total_size
            )
        )

    with video_path.open(
        "rb"
    ) as file:

        start = 0

        while start < total_size:

            remaining = (
                total_size - start
            )

            current_chunk_size = min(
                chunk_size,
                remaining,
            )

            # If this is the final chunk and it would be
            # smaller than 5 MB for a large multi-chunk file,
            # merge it into the previous chunk.
            #
            # The initialization logic already accounts for
            # this case by reducing total_chunk_count, so here
            # we only need to read the remaining bytes.
            chunk = file.read(
                current_chunk_size
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
                f"Subiendo TikTok: "
                f"{end + 1}/{total_size} bytes"
            )

            response = requests.put(
                upload_url,
                headers=headers,
                data=chunk,
                timeout=180,
            )

            if not response.ok:
                raise TikTokError(
                    "Error subiendo vídeo a TikTok: "
                    f"{response.status_code} "
                    f"{response.text}"
                )

            start = end + 1


def fetch_status(
    access_token,
    publish_id,
):
    return api_post(
        access_token,
        "/v2/post/publish/status/fetch/",
        {
            "publish_id": publish_id,
        },
    )


def wait_for_publication(
    access_token,
    publish_id,
    timeout_seconds=600,
):
    deadline = (
        time.time()
        + timeout_seconds
    )

    while time.time() < deadline:

        result = fetch_status(
            access_token,
            publish_id,
        )

        data = result.get(
            "data",
            {},
        )

        status = data.get(
            "status"
        )

        print(
            f"Estado publicación TikTok: "
            f"{status}"
        )

        if status == "PUBLISH_COMPLETE":

            post_ids = data.get(
                "publicaly_available_post_id",
                [],
            )

            return {
                "status": "published",
                "publish_id": publish_id,
                "post_ids": post_ids,
                "raw": data,
            }

        if status == "FAILED":

            raise TikTokError(
                "TikTok ha rechazado la publicación: "
                + str(
                    data.get(
                        "fail_reason",
                        "unknown",
                    )
                )
            )

        time.sleep(10)

    raise TikTokError(
        "Se agotó el tiempo esperando "
        "la publicación de TikTok."
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

    creator_info = query_creator_info(
        access_token
    )

    creator_data = creator_info.get(
        "data",
        {},
    )

    print(
        "Cuenta TikTok:"
        f" @{creator_data.get('creator_username', 'unknown')}"
    )

    print(
        "Opciones de privacidad:"
        f" {creator_data.get('privacy_level_options', [])}"
    )

    max_duration = creator_data.get(
        "max_video_post_duration_sec"
    )

    print(
        "Duración máxima:"
        f" {max_duration} segundos"
    )

    result = initialize_direct_post(
        access_token,
        creator_info,
        video_path,
        caption,
    )

    data = result.get(
        "data",
        {},
    )

    publish_id = data.get(
        "publish_id"
    )

    upload_url = data.get(
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

    video_size = (
        video_path.stat().st_size
    )

    chunk_size, _ = (
        calculate_upload_chunks(
            video_size
        )
    )

    upload_video(
        upload_url,
        video_path,
        chunk_size,
    )

    result = wait_for_publication(
        access_token,
        publish_id,
    )

    result["caption"] = caption

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

    access_token = os.environ.get(
        "TIKTOK_ACCESS_TOKEN"
    )

    if not access_token:
        raise RuntimeError(
            "Falta el secret "
            "TIKTOK_ACCESS_TOKEN."
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
