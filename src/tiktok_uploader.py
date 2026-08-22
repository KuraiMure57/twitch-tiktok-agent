import sys
import json
import os

def upload_to_tiktok_automated(video_path, metadata_path):
    print("=== INICIANDO SUBIDA AUTOMATIZADA CON TIKTOK-UPLOADER ===")
    
    # 1. Extraer título y hashtags de la metadata
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        title = metadata.get("title", "")
        hashtags = " ".join(metadata.get("hashtags", []))
        full_caption = f"{title} {hashtags}"
        print(f"Texto configurado para el vídeo: {full_caption}")
    except Exception as e:
        print(f"Error al leer metadata (usando texto por defecto): {e}")
        full_caption = "Prueba de publicación #twitch"

    # 2. Recuperar el secreto de las cookies de tu GitHub
    cookies_env = os.environ.get("TIKTOK_COOKIES")
    if not cookies_env:
        raise ValueError("Error: TIKTOK_COOKIES no está configurado en GitHub Secrets.")

    # 3. TRADUCTOR DE FORMATO: Adaptamos tus cookies al formato estricto de la librería
    cookies_file_path = "temp_tiktok_cookies.json"
    try:
        raw_cookies = json.loads(cookies_env)
        
        # Estructuramos el diccionario con el formato exacto que pide 'tiktok-uploader'
        formatted_cookies = {}
        for cookie in raw_cookies:
            name = cookie.get("name")
            value = cookie.get("value")
            if name and value:
                formatted_cookies[name] = value

        # Guardamos el archivo con el formato traducido que la librería sí entiende
        with open(cookies_file_path, "w", encoding="utf-8") as f:
            json.dump(formatted_cookies, f, indent=2)
        print("💾 Archivo temporal de cookies traducido y estructurado con éxito.")
    except Exception as e:
        raise ValueError(f"Error al procesar y formatear tus cookies: {e}")

    # 4. Forzamos a Python a importar la librería externa de internet
    try:
        print("🚀 Transmitiendo vídeo troceado de forma segura hacia los servidores de TikTok...")
        
        # Limpiamos las rutas para evitar el conflicto del nombre del archivo
        original_path = list(sys.path)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path = [p for p in sys.path if p != current_dir and p != os.getcwd() and p != ""]
        
        from tiktok_uploader.upload import upload_video
        
        # Restauramos las rutas normales de tu agente
        sys.path = original_path
        
        # Ejecutamos la subida oficial por fragmentos (Chunks)
        # Pasamos el archivo traducido. Al ver los nombres planos, validará la sesión al instante.
        upload_video(
            filename=video_path,
            description=full_caption,
            cookies=cookies_file_path,
            headless=True
        )
        
        print("✅ ¡VÍDEO ENVIADO CON ÉXITO! Comprueba la carpeta de borradores de tu móvil.")
        
        success_result = {
            "status": "SUCCESS",
            "publish_id": "COMMUNITY_UPLOADER_LIB_FINAL_STABLE",
            "post_ids": ["DRAFT_MODE"],
            "caption": full_caption
        }
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(success_result, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Error durante el proceso automatizado de subida: {e}")
        fail_result = {"status": f"FAILED: {str(e)}", "caption": full_caption}
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(fail_result, f, ensure_ascii=False, indent=2)
            
    finally:
        # Borramos el archivo temporal por estricta seguridad
        if os.path.exists(cookies_file_path):
            os.remove(cookies_file_path)
            print("🧹 Archivo temporal de cookies destruido de forma segura.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
    upload_to_tiktok_automated(sys.argv[1], sys.argv[2])
