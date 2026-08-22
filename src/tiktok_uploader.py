import math
import os
import sys
from pathlib import Path

import requests


TIKTOK_UPLOAD_INIT_URL = (
    "https://open.tiktokapis.com/"
    "v2/post/publish/inbox/video/init/"
)

CHUNK_SIZE = 10 * 1024 * 1024


class TikTokUploadError(RuntimeError):
    pass


def get_access_token():
    access_token = os.environ.get(
        "TIKTOK_ACCESS_TOKEN"
    )

    if not access_token:
        raise TikTokUploadError(
            "Falta la variable TIKTOK_ACCESS_TOKEN."
        )

    return access_token


def initialize_inbox_upload(
    access_token,
    video_path,
):
    video_size = video_path.stat().st_size

    total_chunks = math.ceil(
        video_size / CHUNK_SIZE
    )

    payload = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": CHUNK_SIZE,
            "total_chunk_count": total_chunks,
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    print(
        "Inicializando subida a TikTok Inbox..."
    )

    response = requests.post(
        TIKTOK_UPLOAD_INIT_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )

    print(
        f"TikTok init HTTP {response.status_code}"
    )

    if not response.ok:
        print(
            "RESPUESTA DE TIKTOK:"
        )
        print(response.text)

        raise TikTokUploadError(
            "TikTok rechazó la inicialización "
            f"de la subida: "
            f"{response.status_code}"
        )

    data = response.json()

    error = data.get("error", {})

    if error.get("code") != "ok":
        raise TikTokUploadError(
            "TikTok devolvió un error: "
            f"{data}"
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
        raise TikTokUploadError(
            "TikTok no devolvió publish_id."
        )

    if not upload_url:
        raise TikTokUploadError(
            "TikTok no devolvió upload_url."
        )

    print(
        f"Upload inicializado correctamente."
    )

    print(
        f"publish_id: {publish_id}"
    )

    return publish_id, upload_url


def upload_video(
    upload_url,
    video_path,
):
    video_size = video_path.stat().st_size

    print(
        f"Subiendo vídeo a TikTok "
        f"({video_size / (1024 * 1024):.2f} MB)..."
    )

    with video_path.open(
        "rb"
    ) as video_file:

        chunk_number = 0

        while True:

            chunk = video_file.read(
                CHUNK_SIZE
            )

            if not chunk:
                break

            chunk_size = len(chunk)

            start = (
                chunk_number
                * CHUNK_SIZE
            )

            end = (
                start
                + chunk_size
                - 1
            )

            headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(
                    chunk_size
                ),
                "Content-Range": (
                    f"bytes {start}-{end}/"
                    f"{video_size}"
                ),
            }

            print(
                f"Subiendo bloque "
                f"{chunk_number + 1}: "
                f"{start}-{end}"
            )

            response = requests.put(
                upload_url,
                headers=headers,
                data=chunk,
                timeout=300,
            )

            print(
                f"TikTok upload HTTP "
                f"{response.status_code}"
            )

            if response.status_code not in (
                200,
                201,
                204,
            ):
                print(
                    "RESPUESTA DE TIKTOK:"
                )
                print(
                    response.text
                )

                raise TikTokUploadError(
                    "TikTok rechazó la subida "
                    f"del vídeo: "
                    f"{response.status_code}"
                )

            chunk_number += 1

    print(
        "Vídeo enviado correctamente "
        "a TikTok."
    )


def upload_to_tiktok_inbox(
    video_path,
):
    video_path = Path(
        video_path
    )

    if not video_path.exists():
        raise FileNotFoundError(
            f"No existe el vídeo: "
            f"{video_path}"
        )

    if video_path.stat().st_size == 0:
        raise TikTokUploadError(
            "El vídeo está vacío."
        )

    access_token = get_access_token()

    publish_id, upload_url = (
        initialize_inbox_upload(
            access_token,
            video_path,
        )
    )

    upload_video(
        upload_url,
        video_path,
    )

    print()
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
        "TikTok lo enviará al Inbox para "
        "continuar la edición desde la app."
    )
    print(
        f"publish_id: {publish_id}"
    )
    print(
        "======================================"
    )

    return publish_id


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Uso:"
        )

        print(
            "python src/tiktok_uploader.py "
            "<video.mp4>"
        )

        sys.exit(1)

    video_path = Path(
        sys.argv[1]
    )

    try:

        publish_id = (
            upload_to_tiktok_inbox(
                video_path
            )
        )

        print()
        print(
            f"Resultado: {publish_id}"
        )

    except Exception as error:

        print()
        print(
            "❌ ERROR AL SUBIR A TIKTOK"
        )
        print(
            str(error)
        )

        sys.exit(1)
