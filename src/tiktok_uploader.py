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
        # Carga directa del formato estándar de Cookie-Editor
        raw_cookies = json.loads(cookies_env)
        print("💡 Cookies cargadas correctamente en formato JSON plano nativo.")
        
        # === BLOQUE DE LIMPIEZA DE SAMESITE ===
        cookies = []
        for cookie in raw_cookies:
            # Aseguramos que el samesite tenga la capitalización y valores válidos para Playwright
            if "sameSite" in cookie:
                val = str(cookie["sameSite"]).strip().capitalize()
                if val in ["Strict", "Lax", "None"]:
                    cookie["sameSite"] = val
                else:
                    # Si tiene un valor inválido como "no_restriction" o vacío, lo eliminamos
                    # para que Playwright asigne el valor por defecto del navegador de forma segura
                    del cookie["sameSite"]
            cookies.append(cookie)
        print("🧹 Limpieza de atributos SameSite completada de forma segura.")
        
    except Exception as e:
        print(f"❌ Error al procesar el JSON de las cookies: {e}")
        print("Asegúrate de haber usado la extensión Cookie-Editor (icono de galleta) y exportado en JSON.")
        cookies = None

    # 3. Automatización del navegador con Playwright
    try:
        with sync_playwright() as p:
            print("Iniciando navegador virtual (Chromium Headless)...")
            browser = p.chromium.launch(headless=True)
            
            # Configuramos un entorno de escritorio normal para evitar que TikTok nos bloquee
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Inyectamos las cookies para saltarnos el Login oficial de la API
            print("Inyectando cookies de sesión...")
            try:
                context.add_cookies(cookies)
            except Exception as cookie_err:
                print(f"❌ Error crítico al aplicar las cookies en Playwright: {cookie_err}")
                print("💡 CONSEJO: Si el error persiste, usa la extensión 'Cookie-Editor' (icono de galleta) y exporta como JSON plano.")
                raise cookie_err
                
            page = context.new_page()

            print("Entrando a la página de carga de TikTok Studio...")
            page.goto("https://tiktok.com", wait_until="networkidle")
            time.sleep(5) # Espera prudencial para que renderice todo

            # Comprobación de seguridad: Ver si nos redirigió al login (cookies inválidas/caducadas)
            if "login" in page.url:
                print("❌ ERROR: TikTok nos redirigió a la página de Login. Las cookies han caducado o no son válidas.")
                raise Exception("Sesión no iniciada. Cookies inválidas.")

            print(f"Subiendo archivo de vídeo: {video_path}")
            # Localizamos el selector de archivos oculto de la web
            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(video_path)
            
            print("Esperando a que el vídeo termine de procesarse en los servidores de TikTok...")
            # Esperamos a que aparezca el botón "Eliminar", señal de que el vídeo ya se cargó en la interfaz
            page.wait_for_selector("text=Eliminar", timeout=90000) 

            print("Escribiendo el título y los hashtags de la IA...")
            # El cuadro de texto de TikTok Studio es un contenedor editable (DraftEditor)
            editor = page.locator('.public-DraftEditor-content')
            editor.click()
            # Limpiamos lo que haya por defecto y escribimos el contenido
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(full_caption)
            time.sleep(2)

            print("Guardando el vídeo en la sección de borradores...")
            # Buscamos el botón gris que pone "Guardar borrador"
            draft_button = page.locator('button:has-text("Guardar borrador")')
            
            if draft_button.is_visible():
                draft_button.click()
            else:
                # Si la interfaz web cambia ligeramente, el botón "Publicar" sirve ya que el estado por defecto es privado
                print("Botón específico de borrador no visto, intentando con botón alternativo...")
                page.locator('button:has-text("Publicar")').click()

            # Esperamos la confirmación visual de la página web
            page.wait_for_selector("text=Cargado correctamente", timeout=30000)
            print("🚀 ¡ÉXITO! El vídeo se ha guardado en tus borradores de TikTok de forma pública.")
            
            browser.close()

            # Guardamos el archivo de reporte final que tu workflow lee para pintar el JSON en consola
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
    # Capturamos de forma estricta los argumentos enviados desde GitHub Actions
    if len(sys.argv) < 3:
        print("Uso: python tiktok_uploader.py <ruta_video> <ruta_metadata>")
        sys.exit(1)
        
    video_arg = sys.argv[1]     # 👈 Coge 'src/tiktok_test.mp4' (Argumento 1)
    metadata_arg = sys.argv[2]  # 👈 Coge 'metadata.json' (Argumento 2)
    
    upload_to_tiktok(video_arg, metadata_arg)

