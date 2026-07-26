"""Gmail OAuth via the device-code flow.

Standard "installed app" OAuth expects a browser on the same machine to catch
a localhost redirect. This container has no browser, so we use Google's
device-authorization flow instead: we print a URL + short code, you approve
on any device with a browser, and this process polls until the token lands.

Requires credentials.json (an OAuth client of type "TVs and Limited Input
devices") in this directory. Never committed — see .gitignore.
"""
import json
import time
import sys

import requests

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def load_client_config():
    with open(CREDENTIALS_FILE) as f:
        data = json.load(f)
    # credentials.json for this client type nests under "installed" or "web"
    key = "installed" if "installed" in data else "web"
    return data[key]["client_id"], data[key]["client_secret"]


def request_device_code(client_id):
    resp = requests.post(
        DEVICE_CODE_URL,
        data={"client_id": client_id, "scope": " ".join(SCOPES)},
    )
    resp.raise_for_status()
    return resp.json()


def poll_for_token(client_id, client_secret, device_code, interval):
    while True:
        time.sleep(interval)
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        payload = resp.json()
        if resp.status_code == 200:
            return payload
        error = payload.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        raise RuntimeError(f"Device auth failed: {payload}")


def main():
    client_id, client_secret = load_client_config()
    device = request_device_code(client_id)

    print("\nTo authorize this tool, open:")
    print(f"  {device['verification_url']}")
    print(f"and enter this code: {device['user_code']}\n")
    print("Waiting for approval...")

    token = poll_for_token(
        client_id, client_secret, device["device_code"], device["interval"]
    )

    token_data = {
        "token": token["access_token"],
        "refresh_token": token.get("refresh_token"),
        "token_uri": TOKEN_URL,
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES,
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    if not token.get("refresh_token"):
        print(
            "Warning: no refresh_token returned. If this app was already "
            "authorized before, revoke access at "
            "https://myaccount.google.com/permissions and re-run to force "
            "a fresh consent (refresh tokens are only issued on first consent)."
        )

    print(f"Saved credentials to {TOKEN_FILE}. You're authorized.")


if __name__ == "__main__":
    main()
