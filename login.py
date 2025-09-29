import requests
import logging
import os

# first endpoint where you login with wifirst credentials
LOGIN_PAGE = "https://portal-front.wifirst.net/api/sessions"
# second endpoint where you authenticate with the wifirst provided credentials
HTML_LOGIN_PAGE = "https://wireless.wifirst.net/goform/HtmlLoginRequest"
# get the fragments id
SETTINGS_PAGE = "https://portal-front.wifirst.net/api/settings?force_production=false"
# get the token for login
TOKEN_PAGE = "https://wireless.wifirst.net/index.txt"


def get_token():
    token = requests.get(TOKEN_PAGE).text
    logging.info(f'Fetched token: {token}')
    return token


def get_fragment():
    r = requests.get(SETTINGS_PAGE)
    logging.info("Fetched settings page")
    fragment = next(x for x in r.json().get('fragments')
                    if x['template'] == 'end_user_coupon_signin')
    logging.info(
        f'Extracted fragment with id "{fragment["id"]}" from settings page')

    return fragment['id']


def get_payload1(email, password):
    return {"email": email,
            "password": password,
            "box_token": get_token(),
            "fragment_id": get_fragment()}
            
def get_payload1_force(email, password):
    payload = get_payload1(email, password)
    payload["force"] = True
    return payload

def get_payload2(response):
    return {
        "username": response['radius'].get('login'),
        "password": response['radius'].get('password'),
        "success_url": "https://portal-selfcare.wifirst.net/",
        "error_url": "https://portal-front.wifirst.net/connect-error",
        "update_session": 0
    }


def login(email, password):
    logging.info(f'Logging in as {email}')
    resp = requests.post(LOGIN_PAGE, get_payload1(email, password))
    status = resp.status_code
    resp = resp.json()
    print(resp) # for future me (Efe): this started failing due to Wifirst error saying connected device limit reached (but on the web form this can be bypassed...)
    if status == 401 and resp["error"]["code"] == "usage_exceeded":
        isForce = input("You've reached maximum number of connected devices, would you like to force and drop the oldest connected device? ([y]/n) ").strip().lower()
        if isForce and isForce != "y":
            logging.error("WiFi login aborted due to too many connected devices on your account")
            sys.exit(1)
        # retry the login post request with the "force" flag this time
        resp = requests.post(LOGIN_PAGE, get_payload1_force(email, password)).json()
    logging.info(
        f'Successfully logged in and got wifirst credentials: {resp["radius"].get("login")} with password {resp["radius"].get("password")}')
    requests.post(HTML_LOGIN_PAGE, get_payload2(resp))


if __name__ == "__main__":
    try:
        login(os.environ["WIFIRST_EMAIL"], os.environ["WIFIRST_PASSWD"])
    except requests.exceptions.ConnectionError:
        logging.error("You are not connected to the wifirst network")
        sys.exit(1)
