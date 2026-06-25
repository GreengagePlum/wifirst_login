#!/usr/bin/env python

import requests
import logging
import os
import sys

# Setup basic logging to stdout so systemd journal catches it cleanly
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# first endpoint where you login with wifirst credentials
LOGIN_PAGE = "https://portal-front.wifirst.net/api/sessions"
# second endpoint where you authenticate with the wifirst provided credentials
HTML_LOGIN_PAGE = "https://wireless.wifirst.net/goform/HtmlLoginRequest"
# get the fragments id
SETTINGS_PAGE = "https://portal-front.wifirst.net/api/settings?force_production=false"
# get the token for login
TOKEN_PAGE = "https://wireless.wifirst.net/index.txt"


def is_already_online():
    """Checks if internet access is active using a lightweight captive portal check."""
    try:
        # gstatic returns a 204 No Content if internet is fully functional.
        # If intercepted by a captive portal, it returns a 200 or 302 redirect.
        response = requests.get(
            "http://connectivitycheck.gstatic.com/generate_204", timeout=4
        )
        return response.status_code == 204
    except requests.exceptions.RequestException:
        return False


def get_token():
    token = requests.get(TOKEN_PAGE).text
    logging.info(f"Fetched token: {token}")
    return token


def get_fragment():
    r = requests.get(SETTINGS_PAGE)
    logging.info("Fetched settings page")
    fragment = next(
        x
        for x in r.json().get("fragments")
        if x["template"] == "end_user_coupon_signin"
    )
    logging.info(f'Extracted fragment with id "{fragment["id"]}" from settings page')

    return fragment["id"]


def get_payload1(email, password):
    return {
        "email": email,
        "password": password,
        "box_token": get_token(),
        "fragment_id": get_fragment(),
    }


def get_payload1_force(email, password):
    payload = get_payload1(email, password)
    payload["force"] = True
    return payload


def get_payload2(response):
    return {
        "username": response["radius"].get("login"),
        "password": response["radius"].get("password"),
        "success_url": "https://portal-selfcare.wifirst.net/",
        "error_url": "https://portal-front.wifirst.net/connect-error",
        "update_session": 0,
    }


def login(email, password):
    if is_already_online():
        logging.info("Internet connection is healthy. No login required.")
        return

    logging.info(
        f"Internet connection down or captive portal detected. Logging in as {email}"
    )
    resp = requests.post(LOGIN_PAGE, get_payload1(email, password))
    status = resp.status_code
    resp = resp.json()

    if status == 401 and resp["error"]["code"] == "usage_exceeded":
        logging.warning(
            "Device limit reached. Headless mode active: automatically forcing oldest device drop."
        )
        resp = requests.post(LOGIN_PAGE, get_payload1_force(email, password)).json()

    logging.info(
        f"Successfully authenticated. Applying credentials to hardware gateway..."
    )
    requests.post(HTML_LOGIN_PAGE, get_payload2(resp))
    logging.info("Gateway authentication payload delivered.")


if __name__ == "__main__":
    if "WIFIRST_EMAIL" not in os.environ or "WIFIRST_PASSWD" not in os.environ:
        logging.error("Missing environment variables WIFIRST_EMAIL or WIFIRST_PASSWD")
        sys.exit(1)

    try:
        login(os.environ["WIFIRST_EMAIL"], os.environ["WIFIRST_PASSWD"])
    except requests.exceptions.ConnectionError:
        logging.error("You are not connected to the wifirst network")
        sys.exit(1)
