import sys
import json
import os

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
        print(f"Error al leer metadata: {e}")
        full_caption = "Prueba de publicación #twitch"

    # 2. Recuperar el secreto de las cookies de tu GitHub
    cookies_env = os.environ.get("TIKTOK_COOKIES")
    if not cookies_env:
        raise ValueError("Error: TIKTOK_COOKIES no está configurado en GitHub Secrets.")

    # 3. CONVERTIDOR ESTRICTO A FORMATO NETSCAPE (El que exige la librería)
    cookies_file_path = "cookies_netscape.txt"
    try:
        raw_cookies = json.loads(cookies_env)
        
        # Escribimos las cabeceras estándar de un archivo Netscape cookies
        with open(cookies_file_path, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# http://haxx.se\n")
            f.write("# This is a generated file! Do not edit.\n\n")
            
            for cookie in raw_cookies:
                domain = cookie.get("domain", ".tiktok.com")
                # Aseguramos formato correcto de banderas booleanas para Netscape
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = cookie.get("path", "/")
                secure = "TRUE" if cookie.get("secure", False) else "FALSE"
                # Expiración por defecto si no viene dada
                expiration = str(int(cookie.get("expiration", 0)))
                if expiration == "0":
                    expiration = str(int(cookie.get("expiry", 0)))
                if expiration == "0":
                    expiration = str(int(sys.maxsize / 100000000)) # Tiempo lejano futuro
                    
                name = cookie.get("name")
                value = cookie.get("value")
                
                if name and value:
                    # Estructura de pestañas separadas por tabuladores (\t) obligatoria
                    f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")
                    
        print("💾 Archivo temporal convertido a formato Netscape cookies (.txt) con éxito.")
    except Exception as e:
        raise ValueError(f"Error al convertir cookies al formato Netscape: {e}")

    # 4. Ajuste de rutas e invocación de la librería externa
    try:
        print("🚀 Enviando vídeo troceado hacia la cola de ingesta de TikTok...")
        
        # Evitamos el conflicto del nombre local limpiando sys.path
        original_path = list(sys.path)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path = [p for p in sys.path if p != current_dir and p != os.getcwd() and p != ""]
        
        from tiktok_uploader.upload import upload_video
        
        sys.path = original_path
        
        # Ejecutamos la subida oficial pasándole la ruta del archivo de texto plano creado
        upload_video(
            filename=video_path,
            description=full_caption,
            cookies=cookies_file_path, # 👈 Ruta del archivo .txt compatible
            headless=True
        )
        
        print("✅ ¡VÍDEO ENVIADO CON ÉXITO! Comprueba tu cuenta en unos minutos.")
        
        success_result = {
            "status": "SUCCESS",
            "publish_id": "COMMUNITY_UPLOADER_NETSCAPE_TXT",
            "post_ids": ["DRAFT_MODE"],
            "caption": full_caption
        }
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(success_result, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Error durante la ejecución del proceso: {e}")
        fail_result = {"status": f"FAILED: {str(e)}", "caption": full_caption}
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(fail_result, f, ensure_ascii=False, indent=2)
            
    finally:
        # Limpieza del archivo creado por seguridad
        if os.path.exists(cookies_file_path):
            os.remove(cookies_file_path)
            print("🧹 Archivo cookies_netscape.txt eliminado con éxito.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
    upload_to_tiktok_automated(sys.argv, sys.argv)
