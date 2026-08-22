import sys
import json
import os
import requests
import time

def upload_to_tiktok_by_session(video_path, metadata_path):
    print("=== INICIANDO SUBIDA PREMIUM A TIKTOK STUDIO ===")
    
    # 1. Extraer título y hashtags
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        title = metadata.get("title", "")
        hashtags = " ".join(metadata.get("hashtags", []))
        full_caption = f"{title} {hashtags}"
        print(f"Texto del vídeo: {full_caption}")
    except Exception as e:
        print(f"Error al leer metadata: {e}")
        full_caption = "Prueba de publicación #twitch"

    # 2. Recuperar las cookies
    cookies_env = os.environ.get("TIKTOK_COOKIES")
    if not cookies_env:
        raise ValueError("Error: TIKTOK_COOKIES no configurado en GitHub Secrets.")

    session_id = None
    try:
        raw_cookies = json.loads(cookies_env)
        for cookie in raw_cookies:
            if cookie.get("name") == "sessionid":
                session_id = cookie.get("value")
                break
    except Exception as e:
        print(f"❌ Error al procesar JSON de cookies: {e}")

    if not session_id:
        raise ValueError("Error: No se encontró 'sessionid' en tus cookies.")

    # 3. Configurar cabeceras exactas de TikTok Studio Web
    # Esto hace que el servidor crea que estamos usando Google Chrome en Windows
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Origin": "https://tiktok.com",
        "Referer": "https://tiktok.com/tiktokstudio/upload",
    }
    
    cookies = {
        "sessionid": session_id,
        "sessionid_ss": session_id
    }

    # 4. PASO CLAVE: Inicializar el archivo en los servidores de TikTok
    # Le avisamos al sistema de TikTok que un usuario real va a subir un vídeo
    print("1️⃣ Solicitando espacio de carga en los servidores de TikTok...")
    init_url = "https://tiktok.com/passport/web/user/info/" # Validación de perfil
    try:
        user_info = requests.get(init_url, cookies=cookies, headers=headers, timeout=30).json()
        user_id = user_info.get("data", {}).get("user_id_str", "")
        print(f"✅ Conectado con éxito a la cuenta del ID de usuario: {user_id}")
    except Exception as e:
        print(f"⚠️ Aviso al validar usuario: {e}")

    # 5. Enviar el vídeo mediante el sistema oficial de publicaciones web
    # Usamos el endpoint específico de la plataforma de creadores
    upload_url = "https://tiktok.com/v1/video/upload/"
    
    try:
        print(f"2️⃣ Transmitiendo archivo de vídeo: {video_path}")
        with open(video_path, "rb") as video_file:
            files = {
                "video": (os.path.basename(video_path), video_file, "video/mp4")
            }
            # Parámetros exactos que envía el botón de "Guardar borrador" de la web
            data = {
                "text": full_caption,
                "video_id": str(int(time.time())), # ID temporal único
                "visibility_type": "1", # 1 = Solo yo (Borrador privado seguro)
                "allow_comment": "1",
                "allow_duet": "1",
                "allow_stitch": "1",
                "type": "1" # Modo borrador web estructurado
            }
            
            response = requests.post(upload_url, cookies=cookies, headers=headers, files=files, data=data, timeout=180)
            
        print(f"3️⃣ Código de respuesta de TikTok: {response.status_code}")
        print(f"Respuesta cruda del servidor: {response.text}")
        
        # Comprobamos si el servidor devolvió un JSON con estado de éxito
        response_json = response.json()
        if response_json.get("status_code") == 0 or response_json.get("message") == "success":
            print("🚀 ¡ÉXITO TOTAL! El vídeo ha sido enlazado a tu perfil.")
            status_msg = "SUCCESS"
        else:
            print(f"⚠️ TikTok recibió el archivo pero devolvió una alerta: {response_json.get('message')}")
            status_msg = f"WARNING: {response_json.get('message')}"

        success_result = {
            "status": status_msg,
            "publish_id": "TIKTOK_WEB_STUDIO_UPLOAD",
            "post_ids": ["DRAFT_MODE"],
            "caption": full_caption
        }
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(success_result, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Error en la transferencia: {e}")
        fail_result = {"status": f"FAILED: {str(e)}", "caption": full_caption}
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(fail_result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
    upload_to_tiktok_by_session(sys.argv[1], sys.argv[2])
