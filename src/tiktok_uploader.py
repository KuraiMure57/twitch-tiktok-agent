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

    # 3. Automatización del navegador con técnicas de evasión avanzada
    try:
        with sync_playwright() as p:
            print("Iniciando navegador virtual en modo VENTANA REAL (headless=False) camuflado...")
            
            # Forzamos headless=False. Al usar xvfb-run en GitHub Actions, la ventana
            # se renderiza en el monitor virtual de Linux sin dar errores visuales.
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled", # Oculta la marca de robot
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--use-fake-ui-for-media-stream"
                ]
            )
            
            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="es-ES",
                timezone_id="Europe/Madrid"
            )
            
            # Camuflaje extra borrando el rastro de la automatización en el navegador
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("Inyectando cookies de sesión...")
            context.add_cookies(cookies)
            page = context.new_page()

            print("Entrando a la página de carga de TikTok Studio...")
            page.goto("https://tiktok.com", wait_until="commit")
            
            print("Esperando estabilización de scripts internos...")
            time.sleep(15)

            # Comprobación de seguridad de login
            if "login" in page.url or "passive_login" in page.url:
                print("❌ ERROR: TikTok nos redirigió a la página de Login. Las cookies han caducado.")
                page.screenshot(path="debug_tiktok.png")
                raise Exception("Sesión no iniciada. Cookies inválidas o expiradas.")

            # Simulación de interacción humana básica para disparar la carga de la interfaz
            print("Simulando clics e interacciones de usuario en la pantalla...")
            try:
                page.mouse.move(300, 300)
                time.sleep(1)
                page.mouse.click(300, 300) # Clic de cortesía en zona segura de la web
                time.sleep(3)
            except Exception as e:
                print(f"⚠️ Nota: No se completó la interacción simulada: {e}")

            print("Buscando la zona de carga de archivos...")
            file_input = None
            
            # Intento de localización iterativo y resistente
            try:
                # Esperamos un margen prudencial a que el selector aparezca integrado
                page.wait_for_selector('input[type="file"]', timeout=25000)
                file_input = page.locator('input[type="file"]').first
                print("✅ Zona de carga localizada con éxito en el documento raíz.")
            except Exception:
                print("⚠️ No se encontró en la raíz. Escaneando estructuras dinámicas anidadas...")
                # Inspección de frames por si la interfaz está incrustada
                for frame in page.frames:
                    if frame.locator('input[type="file"]').count() > 0:
                        file_input = frame.locator('input[type="file"]').first
                        print(f"✅ Zona de carga localizada en el marco secundario: {frame.url}")
                        break

            if not file_input:
                print("❌ ERROR CRÍTICO: No se localizó el cargador de vídeos en la web.")
                print("📸 Actualizando captura de pantalla 'debug_tiktok.png'...")
                page.screenshot(path="debug_tiktok.png")
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
        print(f"❌ Error inesperado durante la automatización: {e}")
        fail_result = {"status": f"FAILED: {str(e)}", "caption": full_caption}
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(fail_result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
    upload_to_tiktok(sys.argv[1], sys.argv[2])
