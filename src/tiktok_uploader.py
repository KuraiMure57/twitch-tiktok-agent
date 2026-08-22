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

    # 3. Automatización del navegador con técnicas de evasión de bots
    try:
        with sync_playwright() as p:
            print("Iniciando navegador virtual con argumentos anti-detección...")
            
            # Lanzamos el navegador añadiendo banderas para simular ser un Chrome de usuario estándar
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled", # Oculta navigator.webdriver
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            
            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="es-ES",
                timezone_id="Europe/Madrid"
            )
            
            # Scripts de inyección de camuflaje extra antes de que cargue la web
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("Inyectando cookies de sesión...")
            context.add_cookies(cookies)
            page = context.new_page()

            print("Entrando a la página de carga de TikTok Studio...")
            page.goto("https://tiktok.com", wait_until="commit")
            
            # Esperamos de forma progresiva comprobando la URL
            print("Esperando renderizado de la interfaz...")
            time.sleep(15)

            # Comprobación de seguridad de login
            if "login" in page.url or "passive_login" in page.url:
                print("❌ ERROR: TikTok nos redirigió a la página de Login. Las cookies han caducado.")
                page.screenshot(path="debug_tiktok.png")
                raise Exception("Sesión no iniciada. Cookies inválidas.")

            print("Buscando la zona de carga de archivos...")
            file_input = None
            
            # Intentamos localizar el input mediante selectores alternativos resistentes
            try:
                # Esperamos a que la web dibuje algún input en la pantalla
                page.wait_for_selector('input[type="file"]', timeout=20000)
                file_input = page.locator('input[type="file"]').first
                print("✅ Zona de carga localizada con éxito.")
            except Exception:
                print("⚠️ No se encontró el input primario. Intentando rastreo por frames secundarios...")
                for frame in page.frames:
                    if frame.locator('input[type="file"]').count() > 0:
                        file_input = frame.locator('input[type="file"]').first
                        print("✅ Zona de carga localizada dentro de un sub-frame.")
                        break

            if not file_input:
                print("❌ ERROR CRÍTICO: No se localizó el cargador de vídeos.")
                print("📸 Guardando captura de pantalla de depuración en 'debug_tiktok.png'...")
                page.screenshot(path="debug_tiktok.png")
                raise Exception("Bloqueo de seguridad detectado o interfaz web no encontrada.")

            print(f"Subiendo archivo de vídeo: {video_path}")
            file_input.set_input_files(video_path)
            
            print("Esperando procesamiento en los servidores de TikTok...")
            page.wait_for_selector("text=Eliminar", timeout=120000) 

            print("Escribiendo descripción y hashtags...")
            editor = page.locator('.public-DraftEditor-content')
            editor.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(full_caption)
            time.sleep(3)

            print("Guardando el vídeo en la sección de borradores...")
            draft_button = page.locator('button:has-text("Guardar borrador")')
            if draft_button.is_visible():
                draft_button.click()
            else:
                page.locator('button:has-text("Publicar")').click()

            page.wait_for_selector("text=Cargado correctamente", timeout=30000)
            print("🚀 ¡ÉXITO! Guardado en borradores.")
            
            browser.close()

            success_result = {
                "status": "SUCCESS",
                "publish_id": "PLAYWRIGHT_AUTOMATION_DRAFT",
                "post_ids": ["DRAFT_MODE"],
                "caption": full_caption
            }
            with open("tiktok_result.json", "w", encoding="utf-8") as f:
                json.dump(success_result, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        fail_result = {"status": f"FAILED: {str(e)}", "caption": full_caption}
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(fail_result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
    upload_to_tiktok(sys.argv[1], sys.argv[2])
