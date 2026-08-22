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

    # 3. TRADUCTOR DE FORMATO EN MEMORIA: Extraemos los valores clave
    try:
        raw_cookies = json.loads(cookies_env)
        
        # Mapeamos los nombres y valores directamente a un diccionario de sesión de Python
        session_cookies = {}
        for cookie in raw_cookies:
            name = cookie.get("name")
            value = cookie.get("value")
            if name and value:
                session_cookies[name] = value
        
        print("✅ Diccionario de autenticación estructurado en memoria correctamente.")
    except Exception as e:
        raise ValueError(f"Error al procesar el JSON de tus cookies: {e}")

    # 4. Ajuste estricto de rutas de Python e invocación nativa en memoria
    try:
        print("🚀 Conectando de forma directa con los servidores de ingesta de TikTok...")
        
        # Salvaguardamos los paths para evitar el conflicto del nombre de tu archivo
        original_path = list(sys.path)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path = [p for p in sys.path if p != current_dir and p != os.getcwd() and p != ""]
        
        # Importamos de forma limpia el módulo principal de subidas de internet
        from tiktok_uploader.upload import upload_video
        
        # Restauramos las rutas estándar de tu agente de IA
        sys.path = original_path
        
        # Ejecutamos la subida oficial por fragmentos (Chunks)
        # Pasamos el diccionario plano 'session_cookies' directamente al parámetro cookies
        upload_video(
            filename=video_path,
            description=full_caption,
            cookies=session_cookies, # 👈 Inyección directa en memoria sin archivos de texto intermediarios
            headless=True
        )
        
        print("✅ ¡VÍDEO PROCESADO CON ÉXITO! Comprueba la carpeta de borradores de tu móvil.")
        
        success_result = {
            "status": "SUCCESS",
            "publish_id": "COMMUNITY_UPLOADER_DIRECT_MEMORY",
            "post_ids": ["DRAFT_MODE"],
            "caption": full_caption
        }
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(success_result, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Error durante el proceso de transferencia: {e}")
        fail_result = {"status": f"FAILED: {str(e)}", "caption": full_caption}
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(fail_result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
    upload_to_tiktok_automated(sys.argv[1], sys.argv[2])
