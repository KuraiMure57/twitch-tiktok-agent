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
        print(f"Error al leer metadata.json (usando texto por defecto): {e}")
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
        
        # === BLOQUE DE LIMPIEZA DE SAMESITE ===
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

    # 3. Automatización del navegador con Playwright
    try:
        with sync_playwright() as p:
            print("Iniciando navegador virtual (Chromium Headless)...")
            browser = p.chromium.launch(headless=True)
            
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            print("Inyectando cookies de sesión...")
            context.add_cookies(cookies)
                
            page = context.new_page()

            # 🌐 ¡AQUÍ ESTÁ LA CORRECCIÓN CLAVE! Vamos directos a la zona de creadores
            print("Entrando a la página de carga de TikTok Studio...")
            page.goto("https://tiktok.com", wait_until="domcontentloaded")
            time.sleep(12) # Damos un buen margen para que cargue la interfaz de subida

            # Comprobación de seguridad: Ver si nos redirigió al login
            if "login" in page.url:
                print("❌ ERROR: TikTok nos redirigió a la página de Login. Las cookies han caducado o no son válidas.")
                raise Exception("Sesión no iniciada. Cookies inválidas.")

            print("Buscando la zona de carga de archivos (intentando múltiples métodos)...")
            file_input = None
            
            # Método 1: Buscar en el documento principal
            try:
                file_input = page.locator('input[type="file"]').first
                file_input.wait_for(state="attached", timeout=10000)
                print("✅ Zona de carga localizada en el documento principal.")
            except Exception:
                print("⚠️ No se encontró el input estándar en la página principal. Probando selectores alternativos...")

            # Método 2: Buscar dentro de posibles iframes
            if not file_input:
                try:
                    for frame in page.frames:
                        input_in_frame = frame.locator('input[type="file"]').first
                        if input_in_frame.count() > 0:
                            file_input = input_in_frame
                            print(f"✅ Zona de carga localizada dentro de un frame: {frame.name or frame.url}")
                            break
                except Exception as frame_err:
                    print(f"⚠️ Error al escanear los frames de la página: {frame_err}")

            # Método 3: Selector alternativo por atributo
            if not file_input:
                try:
                    file_input = page.locator('input[accept*="video"]').first
                    file_input.wait_for(state="attached", timeout=10000)
                    print("✅ Zona de carga localizada mediante el selector de tipo de archivo ('accept').")
                except Exception:
                    print("❌ Error crítico: Ha sido imposible encontrar la zona de carga.")
                    print("📸 Guardando captura de pantalla de depuración en 'debug_tiktok.png'...")
                    page.screenshot(path="debug_tiktok.png")
                    raise Exception("No se pudo interactuar con la zona de subida de TikTok Studio.")

            print(f"Subiendo archivo de vídeo: {video_path}")
            file_input.set_input_files(video_path)
            
            print("Esperando a que el vídeo termine de procesarse en los servidores de TikTok...")
            page.wait_for_selector("text=Eliminar", timeout=120000) 

            print("Escribiendo el título y los hashtags de la IA...")
            editor = page.locator('.public-DraftEditor-content')
            editor.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(full_caption)
            time.sleep(2)

            print("Guardando el vídeo en la sección de borradores...")
            draft_button = page.locator('button:has-text("Guardar borrador")')
            
            if draft_button.is_visible():
                draft_button.click()
            else:
                print("Botón específico de borrador no visto, intentando con botón alternativo...")
                page.locator('button:has-text("Publicar")').click()

            page.wait_for_selector("text=Cargado correctamente", timeout=30000)
            print("🚀 ¡ÉXITO! El vídeo se ha guardado en tus borradores de TikTok de forma pública.")
            
            browser.close()

            # Guardamos el archivo de reporte final para el flujo de GitHub
            success_result = {
                "status": "SUCCESS",
                "publish_id": "PLAYWRIGHT_AUTOMATION_DRAFT",
                "post_ids": ["DRAFT_MODE"],
                "caption": full_caption
            }
            with open("tiktok_result.json", "w", encoding="utf-8") as f:
                json.dump(success_result, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante la ejecución: {e}")
        fail_result = {"status": f"FAILED: {str(e)}", "caption": full_caption}
        with open("tiktok_result.json", "w", encoding="utf-8") as f:
            json.dump(fail_result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
        
    video_arg = sys.argv[1]
    metadata_arg = sys.argv[2]
    
    upload_to_tiktok(video_arg, metadata_arg)
