import base64
import hashlib
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests


AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

REDIRECT_URI = "http://127.0.0.1:8080/callback"
SCOPES = "user.info.basic,video.publish"

HOST = "127.0.0.1"
PORT = 8080

authorization_code = None
authorization_error = None


def generate_code_verifier():
    return secrets.token_urlsafe(64)


def generate_code_challenge(code_verifier):
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global authorization_code
        global authorization_error

        parsed = urlparse(self.path)

        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        params = parse_qs(parsed.query)

        if "error" in params:
            authorization_error = params.get(
                "error_description",
                params.get("error", ["Unknown TikTok error"]),
            )[0]

            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()

            html = """
            <html>
                <body>
                    <h2>TikTok authorization failed.</h2>
                    <p>You can close this window.</p>
                </body>
            </html>
            """

            self.wfile.write(html.encode("utf-8"))
            return

        if "code" not in params:
            authorization_error = "TikTok did not return an authorization code."

            self.send_response(400)
            self.end_headers()
            self.wfile.write(
                b"TikTok did not return an authorization code."
            )
            return

        authorization_code = params["code"][0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        html = """
        <html>
            <body>
                <h2>TikTok authorization successful.</h2>
                <p>You can close this browser window and return to the terminal.</p>
            </body>
        </html>
        """

        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        return


def exchange_code_for_tokens(client_key, client_secret, code, code_verifier):
    response = requests.post(
        TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        },
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        },
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        response.raise_for_status()
        raise RuntimeError(
            f"TikTok returned an invalid response: {response.text}"
        )

    if response.status_code != 200:
        raise RuntimeError(
            "TikTok token exchange failed:\n"
            f"HTTP {response.status_code}\n"
            f"{data}"
        )

    if "error" in data:
        raise RuntimeError(
            "TikTok token exchange failed:\n"
            f"{data}"
        )

    return data


def main():
    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET")

    if not client_key:
        raise RuntimeError(
            "Missing TIKTOK_CLIENT_KEY environment variable."
        )

    if not client_secret:
        raise RuntimeError(
            "Missing TIKTOK_CLIENT_SECRET environment variable."
        )

    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(32)

    params = {
        "client_key": client_key,
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    authorization_url = f"{AUTH_URL}?{urlencode(params)}"

    server = HTTPServer(
        (HOST, PORT),
        CallbackHandler,
    )

    print()
    print("=" * 70)
    print("TikTok OAuth authorization")
    print("=" * 70)
    print()
    print(f"Redirect URI: {REDIRECT_URI}")
    print(f"Scopes: {SCOPES}")
    print()
    print("Opening TikTok authorization in your browser...")
    print()

    threading.Thread(
        target=server.serve_forever,
        daemon=True,
    ).start()

    webbrowser.open(authorization_url)

    timeout_seconds = 300
    started = time.time()

    while (
        authorization_code is None
        and authorization_error is None
        and time.time() - started < timeout_seconds
    ):
        time.sleep(0.5)

    server.shutdown()
    server.server_close()

    if authorization_error:
        raise RuntimeError(
            f"TikTok authorization failed: {authorization_error}"
        )

    if authorization_code is None:
        raise RuntimeError(
            "Timed out waiting for TikTok authorization."
        )

    print("Authorization code received.")
    print("Exchanging authorization code for tokens...")
    print()

    tokens = exchange_code_for_tokens(
        client_key=client_key,
        client_secret=client_secret,
        code=authorization_code,
        code_verifier=code_verifier,
    )

    print("=" * 70)
    print("TOKENS RECEIVED")
    print("=" * 70)
    print()

    print(f"open_id: {tokens.get('open_id')}")
    print(f"scope: {tokens.get('scope')}")
    print(f"expires_in: {tokens.get('expires_in')}")
    print(f"refresh_expires_in: {tokens.get('refresh_expires_in')}")
    print()

    print("REFRESH TOKEN:")
    print(tokens.get("refresh_token"))
    print()

    print("ACCESS TOKEN:")
    print(tokens.get("access_token"))
    print()

    print("=" * 70)
    print("IMPORTANT")
    print("=" * 70)
    print(
        "Do not commit these tokens to GitHub or put them in source code."
    )
    print(
        "We will store the refresh token as a GitHub Actions secret."
    )


if __name__ == "__main__":
    main()
