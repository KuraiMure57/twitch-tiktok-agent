import sys
import json
import os
from tiktok_uploader.upload import upload_video

def upload_to_tiktok_automated(video_path, metadata_path):
    print("=== INICIANDO SUBIDA AUTOMATIZADA CON TIKTOK-UPLOADER ===")
    
    # 1. Extraer título y hashtags
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

    # 3. Crear un archivo temporal de cookies en el servidor de GitHub Actions.
    # La librería necesita leer las cookies desde un archivo físico de texto plano.
    cookies_file_path = "temp_tiktok_cookies.json"
    try:
        cookies_data = json.loads(cookies_env)
        with open(cookies_file_path, "w", encoding="utf-8") as f:
            json.dump(cookies_data, f, indent=2)
        print("💾 Archivo temporal de cookies estructurado con éxito.")
    except Exception as e:
        raise ValueError(f"Error al procesar el JSON de tus cookies: {e}")

    # 4. Lanzar la subida por fragmentos nativa (Garantiza que aparezca en tu móvil)
    try:
        print("🚀 Transmitiendo vídeo troceado de forma segura hacia los servidores de TikTok...")
        
        # Ejecutamos la función de la librería oficial
        # - Usamos headless=True para que corra ligero en GitHub
        # - Pasamos la descripción completa de tu IA
        upload_video(
            filename=video_path,
            description=full_caption,
            cookies=cookies_file_path,
            headless=True
        )
        
        print("✅ ¡VÍDEO ENVIADO CON ÉXITO! Comprueba la carpeta de borradores de tu móvil.")
        
        # Escribimos el reporte final para tu Workflow
        success_result = {
            "status": "SUCCESS",
            "publish_id": "COMMUNITY_UPLOADER_LIB",
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
        # Por seguridad borramos el archivo de cookies del servidor al terminar
        if os.path.exists(cookies_file_path):
            os.remove(cookies_file_path)
            print("🧹 Archivo temporal de cookies destruido de forma segura.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
    upload_to_tiktok_automated(sys.argv[1], sys.argv[2])
