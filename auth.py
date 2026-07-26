"""Gmail OAuth via a manual loopback authorization-code flow.

Google's device-code flow rejects sensitive scopes like Gmail, so we can't
use that here. Instead we use the standard "installed app" flow but skip
actually running a local server (this container has no browser reachable
from your machine): we generate the consent URL, you complete it in your
own browser, and paste back the resulting redirect URL. The redirect target
(http://localhost:8080/...) won't load anything on your machine — that's
expected, just copy the URL from the address bar once it fails to connect.

Usage:
  python auth.py start            Print the URL to open in your browser
  python auth.py finish <url>     Paste the redirect URL (or just the code)
                                   to complete auth and save token.json
"""
import json
import sys
import urllib.parse

import requests

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "http://localhost:8080/"
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def load_client_config():
    with open(CREDENTIALS_FILE) as f:
        data = json.load(f)
    key = "installed" if "installed" in data else "web"
    return data[key]["client_id"], data[key]["client_secret"]


def start():
    client_id, _ = load_client_config()
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    print("\nOpen this URL in your browser and approve access:\n")
    print(url)
    print(
        "\nAfter approving, the browser will try to load "
        "http://localhost:8080/?code=... and fail to connect. That's "
        "expected. Copy the full URL from the address bar and run:\n"
        "  python auth.py finish \"<pasted url>\"\n"
    )


def extract_code(raw):
    if raw.startswith("http"):
        query = urllib.parse.urlparse(raw).query
        params = urllib.parse.parse_qs(query)
        if "error" in params:
            raise SystemExit(f"Authorization error: {params['error'][0]}")
        if "code" not in params:
            raise SystemExit("No 'code' parameter found in that URL.")
        return params["code"][0]
    return raw  # assume they pasted the bare code


def finish(raw):
    client_id, client_secret = load_client_config()
    code = extract_code(raw)

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
    )
    payload = resp.json()
    if resp.status_code != 200:
        raise SystemExit(f"Token exchange failed: {payload}")

    token_data = {
        "token": payload["access_token"],
        "refresh_token": payload.get("refresh_token"),
        "token_uri": TOKEN_URL,
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES,
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    if not payload.get("refresh_token"):
        print(
            "Warning: no refresh_token returned. If you've authorized this "
            "app before, revoke access at "
            "https://myaccount.google.com/permissions and run 'start' again "
            "to force a fresh consent screen."
        )

    print(f"Saved credentials to {TOKEN_FILE}. You're authorized.")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("start", "finish"):
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "start":
        start()
    else:
        if len(sys.argv) < 3:
            print("Usage: python auth.py finish \"<pasted url or code>\"")
            sys.exit(1)
        finish(sys.argv[2])


if __name__ == "__main__":
    main()
