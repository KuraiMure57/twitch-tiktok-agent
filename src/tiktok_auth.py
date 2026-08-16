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
returned_state = None


def generate_code_verifier():
    """
    Generate a PKCE code verifier using characters
    allowed by RFC 7636.
    """

    allowed_characters = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "-._~"
    )

    return "".join(
        secrets.choice(allowed_characters)
        for _ in range(64)
    )


def generate_code_challenge(code_verifier):
    """
    Generate the PKCE S256 code challenge required
    by the TikTok Desktop Login Kit flow.
    """

    return hashlib.sha256(
        code_verifier.encode("ascii")
    ).hexdigest()


class CallbackHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        global authorization_code
        global authorization_error
        global returned_state

        parsed = urlparse(self.path)

        print()
        print("Callback received:")
        print(f"Path: {parsed.path}")

        # Ignore browser favicon requests.
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if parsed.path != "/callback":
            authorization_error = (
                f"Unexpected callback path: {parsed.path}"
            )

            self.send_response(404)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.end_headers()

            self.wfile.write(
                b"Invalid callback path."
            )

            return

        params = parse_qs(
            parsed.query,
            keep_blank_values=True
        )

        print(
            "Parameters received: "
            f"{', '.join(params.keys())}"
        )

        # TikTok returned an OAuth error.
        if "error" in params:
            error = params.get(
                "error",
                ["Unknown error"]
            )[0]

            description = params.get(
                "error_description",
                [error]
            )[0]

            authorization_error = (
                f"{error}: {description}"
            )

            self.send_response(400)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.end_headers()

            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>TikTok Authorization Error</title>
</head>
<body>
    <h2>TikTok authorization failed</h2>
    <p>{description}</p>
    <p>You can close this window.</p>
</body>
</html>
"""

            self.wfile.write(
                html.encode("utf-8")
            )

            return

        # TikTok did not return an authorization code.
        if "code" not in params:
            authorization_error = (
                "TikTok did not return an authorization code."
            )

            self.send_response(400)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.end_headers()

            self.wfile.write(
                b"TikTok did not return an authorization code."
            )

            return

        # Store the authorization code.
        authorization_code = params["code"][0]

        # Store the returned OAuth state.
        returned_state = params.get(
            "state",
            [None]
        )[0]

        print(
            "Authorization code received from callback."
        )

        # Tell the browser that authorization succeeded.
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )
        self.end_headers()

        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>TikTok Authorization</title>
</head>
<body>
    <h2>TikTok authorization successful.</h2>
    <p>You can close this browser window.</p>
</body>
</html>
"""

        self.wfile.write(
            html.encode("utf-8")
        )

    def log_message(self, format, *args):
        print(
            f"[HTTP] {self.address_string()} "
            f"{format % args}"
        )


def exchange_code_for_tokens(
    client_key,
    client_secret,
    code,
    code_verifier,
):
    print(
        "Sending authorization code to "
        "TikTok token endpoint..."
    )

    response = requests.post(
        TOKEN_URL,
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded",
            "Cache-Control":
                "no-cache",
        },
        data={
            "client_key":
                client_key,

            "client_secret":
                client_secret,

            "code":
                code,

            "grant_type":
                "authorization_code",

            "redirect_uri":
                REDIRECT_URI,

            "code_verifier":
                code_verifier,
        },
        timeout=30,
    )

    try:
        data = response.json()

    except ValueError:
        raise RuntimeError(
            "TikTok returned a non-JSON response:\n"
            f"HTTP {response.status_code}\n"
            f"{response.text}"
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

    global authorization_code
    global authorization_error
    global returned_state

    client_key = os.getenv(
        "TIKTOK_CLIENT_KEY"
    )

    client_secret = os.getenv(
        "TIKTOK_CLIENT_SECRET"
    )

    if not client_key:
        raise RuntimeError(
            "Missing TIKTOK_CLIENT_KEY "
            "environment variable."
        )

    if not client_secret:
        raise RuntimeError(
            "Missing TIKTOK_CLIENT_SECRET "
            "environment variable."
        )

    # ---------------------------------------------------------
    # Generate PKCE values.
    # ---------------------------------------------------------

    code_verifier = generate_code_verifier()

    code_challenge = generate_code_challenge(
        code_verifier
    )

    # OAuth state prevents CSRF attacks.
    state = secrets.token_urlsafe(32)

    print()
    print("=" * 70)
    print("TikTok OAuth authorization")
    print("=" * 70)
    print()

    print(
        f"Code verifier length: "
        f"{len(code_verifier)}"
    )

    print(
        f"Code challenge length: "
        f"{len(code_challenge)}"
    )

    print(
        f"Redirect URI: "
        f"{REDIRECT_URI}"
    )

    print(
        f"Scopes: "
        f"{SCOPES}"
    )

    print()

    # ---------------------------------------------------------
    # Build TikTok authorization URL.
    # ---------------------------------------------------------

    params = {
        "client_key":
            client_key,

        "response_type":
            "code",

        "scope":
            SCOPES,

        "redirect_uri":
            REDIRECT_URI,

        "state":
            state,

        "code_challenge":
            code_challenge,

        "code_challenge_method":
            "S256",
    }

    authorization_url = (
        f"{AUTH_URL}?{urlencode(params)}"
    )

    # ---------------------------------------------------------
    # Start the local callback server.
    # ---------------------------------------------------------

    try:
        server = HTTPServer(
            (HOST, PORT),
            CallbackHandler
        )

    except OSError as error:
        raise RuntimeError(
            f"Could not start callback server "
            f"on {HOST}:{PORT}.\n"
            f"{error}"
        )

    print(
        "Local callback server started."
    )

    print(
        f"Listening on "
        f"http://{HOST}:{PORT}/callback"
    )

    print()

    server_thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )

    server_thread.start()

    # ---------------------------------------------------------
    # Open TikTok authorization.
    # ---------------------------------------------------------

    print(
        "Opening TikTok authorization "
        "in your browser..."
    )

    print()

    webbrowser.open(
        authorization_url
    )

    # ---------------------------------------------------------
    # Wait for the OAuth callback.
    # ---------------------------------------------------------

    timeout_seconds = 300

    started = time.time()

    while (
        authorization_code is None
        and authorization_error is None
        and time.time() - started
        < timeout_seconds
    ):
        time.sleep(0.25)

    # ---------------------------------------------------------
    # Stop accepting new requests.
    #
    # Do NOT call server.shutdown() from the main thread here.
    # It can block while serve_forever() is still running.
    # ---------------------------------------------------------

    server.server_close()

    # ---------------------------------------------------------
    # Check authorization result.
    # ---------------------------------------------------------

    if authorization_error:
        raise RuntimeError(
            "TikTok authorization failed:\n"
            f"{authorization_error}"
        )

    if authorization_code is None:
        raise RuntimeError(
            "Timed out waiting for TikTok "
            "authorization callback."
        )

    # ---------------------------------------------------------
    # Validate OAuth state.
    # ---------------------------------------------------------

    if returned_state != state:
        raise RuntimeError(
            "Invalid OAuth state returned by TikTok."
        )

    print()
    print(
        "Authorization callback received "
        "successfully."
    )

    print(
        "OAuth state validated successfully."
    )

    print()

    # ---------------------------------------------------------
    # Exchange authorization code for tokens.
    # ---------------------------------------------------------

    tokens = exchange_code_for_tokens(
        client_key=
            client_key,

        client_secret=
            client_secret,

        code=
            authorization_code,

        code_verifier=
            code_verifier,
    )

    # ---------------------------------------------------------
    # Display token information.
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("TOKENS RECEIVED")
    print("=" * 70)
    print()

    print(
        f"open_id: "
        f"{tokens.get('open_id')}"
    )

    print(
        f"scope: "
        f"{tokens.get('scope')}"
    )

    print(
        f"expires_in: "
        f"{tokens.get('expires_in')}"
    )

    print(
        f"refresh_expires_in: "
        f"{tokens.get('refresh_expires_in')}"
    )

    print()

    print(
        "REFRESH TOKEN:"
    )

    print(
        tokens.get("refresh_token")
    )

    print()

    print(
        "ACCESS TOKEN:"
    )

    print(
        tokens.get("access_token")
    )

    print()

    print("=" * 70)
    print("IMPORTANT")
    print("=" * 70)

    print(
        "Do not commit these tokens to GitHub."
    )

    print(
        "The refresh token will later be stored "
        "as a GitHub Actions secret."
    )


if __name__ == "__main__":
    main()
