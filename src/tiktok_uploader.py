import sys
import json
import os
import time
from playwright.sync_api import sync_playwright

def upload_to_tiktok(video_path, metadata_path):
    print("=== INICIANDO PROCESO DE SUBIDA A TIKTOK ===")
    
    # 1. Leer y formatear los metadatos generados
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        title = metadata.get("title", "")
        hashtags = " ".join(metadata.get("hashtags", []))
        full_caption = f"{title} {hashtags}"
        print(f"Texto del vídeo configurado: {full_caption}")
    except Exception as e:
        print(f"Error al leer metadata.json: {e}")
        full_caption = "Prueba de publicación #twitch"

    # 2. Recuperar y procesar las cookies secretas
    cookies_env = os.environ.get("TIKTOK_COOKIES")
    if not cookies_env:
        result_err = {"status": "FAILED", "caption": full_caption}
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(result_err, f)
        raise ValueError("Error: TIKTOK_COOKIES no está configurado en GitHub Secrets.")

    try:
        raw_cookies = json.loads(cookies_env)
        print("💡 Cookies cargadas correctamente en formato JSON plano nativo.")
        cookies = []
        for cookie in raw_cookies:
            if "sameSite" in cookie:
                val = str(cookie["sameSite"]).strip().capitalize()
                if val in ["Strict", "Lax", "None"]:
                    cookie["sameSite"] = val
                else:
                    del cookie["sameSite"]
            cookies.append(cookie)
        print("🧹 Limpieza de atributos SameSite completada de forma segura.")
    except Exception as e:
        print(f"❌ Error al procesar el JSON de las cookies: {e}")
        cookies = None

    # 3. Automatización del navegador con contexto persistente (Camuflaje de PC real)
    try:
        with sync_playwright() as p:
            print("Iniciando navegador virtual con perfil persistente de usuario...")
            
            # Creamos un directorio temporal en el servidor para simular el almacenamiento de un navegador real
            user_data_dir = os.path.join(os.getcwd(), "tiktok_user_data")
            
            context = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False, # Modo ventana real (dentro de xvfb)
                args=[
                    "--disable-blink-features=AutomationControlled", # Esconde la bandera de webdriver
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--no-first-run",
                ],
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                locale="es-ES",
                timezone_id="Europe/Madrid"
            )
            
            # Forzamos la desactivación de la propiedad robot en la ventana
            page = context.pages[0] if context.pages else context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("Inyectando cookies de sesión en el perfil activo...")
            context.add_cookies(cookies)

            print("Entrando a la página de carga de TikTok Studio...")
            page.goto("https://tiktok.com", wait_until="commit")
            
            print("Esperando estabilización de la interfaz de carga...")
            time.sleep(15)

            # Comprobación de seguridad: Ver si nos echó a la pantalla de Login
            if "login" in page.url or "passive_login" in page.url:
                print("❌ ERROR: TikTok nos redirigió a la página de Login. Las cookies han caducado.")
                page.screenshot(path="debug_tiktok.png")
                raise Exception("Sesión no iniciada. Cookies inválidas o expiradas.")

            # Hacemos una captura preventiva para ver qué está cargando exactamente la web
            page.screenshot(path="debug_tiktok.png")

            print("Buscando la zona de carga de archivos...")
            file_input = None
            try:
                page.wait_for_selector('input[type="file"]', timeout=20000)
                file_input = page.locator('input[type="file"]').first
                print("✅ Zona de carga localizada con éxito en el documento raíz.")
            except Exception:
                print("⚠️ No se encontró en la raíz. Escaneando marcos secundarios...")
                for frame in page.frames:
                    if frame.locator('input[type="file"]').count() > 0:
                        file_input = frame.locator('input[type="file"]').first
                        print(f"✅ Zona de carga localizada en el sub-frame: {frame.url}")
                        break

            if not file_input:
                print("❌ ERROR CRÍTICO: No se localizó el casillero de carga de vídeos.")
                raise Exception("Bloqueo de seguridad persistente o cambio de interfaz estructural.")

            print(f"Subiendo archivo de vídeo: {video_path}")
            file_input.set_input_files(video_path)
            
            print("Esperando procesamiento del clip en los servidores de TikTok...")
            page.wait_for_selector("text=Eliminar", timeout=120000) 

            print("Escribiendo descripción y hashtags generados...")
            editor = page.locator('.public-DraftEditor-content')
            editor.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(full_caption)
            time.sleep(3)

            print("Guardando el vídeo final en borradores...")
            draft_button = page.locator('button:has-text("Guardar borrador")')
            if draft_button.is_visible():
                draft_button.click()
            else:
                page.locator('button:has-text("Publicar")').click()

            page.wait_for_selector("text=Cargado correctamente", timeout=30000)
            print("🚀 ¡ÉXITO COMPLETO! Clip subido y disponible en tus borradores públicos de TikTok.")
            
            context.close()

            success_result = {
                "status": "SUCCESS",
                "publish_id": "PLAYWRIGHT_AUTOMATION_DRAFT",
                "post_ids": ["DRAFT_MODE"],
                "caption": full_caption
            }
            with open("tiktok_result.json", "w", encoding="utf-8") as f:
                json.dump(success_result, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Error inesperado durante la automatización: {e}")
        fail_result = {"status": f"FAILED: {str(e)}", "caption": full_caption}
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(fail_result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
    upload_to_tiktok(sys.argv[1], sys.argv[2])
