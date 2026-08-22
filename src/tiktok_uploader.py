import sys
import json
import os
import time
from playwright.sync_api import sync_playwright

def upload_to_tiktok(video_path, metadata_path):
    # 1. Leer y formatear los metadatos generados
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        title = metadata.get("title", "")
        hashtags = " ".join(metadata.get("hashtags", []))
        full_caption = f"{title} {hashtags}"
    except Exception as e:
        print(f"Error al leer metadata.json: {e}")
        full_caption = "Prueba de publicación #twitch"

    # 2. Recuperar las cookies secretas
    cookies_json = os.environ.get("TIKTOK_COOKIES")
    if not cookies_json:
        result_err = {"status": "FAILED", "caption": full_caption}
        with open("tiktok_result.json", "w") as f:
            json.dump(result_err, f)
        raise ValueError("Error: TIKTOK_COOKIES no está configurado en GitHub Secrets.")

    cookies = json.loads(cookies_json)

    # 3. Automatización del navegador con Playwright
    try:
        with sync_playwright() as p:
            print("Iniciando navegador virtual...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.add_cookies(cookies)
            page = context.new_page()

            print("Entrando a TikTok Creator Studio...")
            page.goto("https://tiktok.com", wait_until="networkidle")
            time.sleep(3)

            print(f"Subiendo archivo de vídeo: {video_path}")
            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(video_path)
            
            print("Esperando procesamiento del vídeo...")
            page.wait_for_selector("text=Eliminar", timeout=60000) 

            print("Escribiendo título y hashtags...")
            editor = page.locator('.public-DraftEditor-content')
            editor.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(full_caption)
            time.sleep(2)

            print("Guardando en borradores...")
            draft_button = page.locator('button:has-text("Guardar borrador")')
            if draft_button.is_visible():
                draft_button.click()
            else:
                page.locator('button:has-text("Publicar")').click()

            page.wait_for_selector("text=Cargado correctamente", timeout=30000)
            print("🚀 ¡Vídeo guardado en borradores correctamente!")
            browser.close()

            # Guardamos el archivo de éxito que el workflow va a leer al final
            success_result = {
                "status": "SUCCESS",
                "publish_id": "PLAYWRIGHT_B_01",
                "post_ids": ["DRAFT_MODE"],
                "caption": full_caption
            }
            with open("tiktok_result.json", "w", encoding="utf-8") as f:
                json.dump(success_result, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Ocurrió un error durante la ejecución de Playwright: {e}")
        fail_result = {"status": f"FAILED: {str(e)}", "caption": full_caption}
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(fail_result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # Capturamos los argumentos enviados desde el comando del workflow
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
        
    video_arg = sys.argv[1]
    metadata_arg = sys.argv[2]
    
    upload_to_tiktok(video_arg, metadata_arg)
