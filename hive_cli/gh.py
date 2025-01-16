import logging
from urllib.parse import parse_qs

import requests

_LOGGER = logging.getLogger(__name__)

CLIENT_ID = "Iv23liyWGa2XGgyWYqBj"
TIMEOUT = 5


def request_code() -> tuple[str, str, str]:
    _LOGGER.info("Requesting codes from GitHub..")
    res = requests.post(
        "https://github.com/login/device/code",
        data={"client_id": CLIENT_ID},
        timeout=TIMEOUT,
    )
    data = parse_qs(res.text)
    return data["user_code"][0], data["device_code"][0], data["verification_uri"][0]


def get_access_token(device_code: str) -> str | None:
    res = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "device_code": device_code,
            "client_id": CLIENT_ID,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        },
        timeout=TIMEOUT,
    )
    data = parse_qs(res.text)
    if "access_token" not in data:
        _LOGGER.error("Could not get access token: %s", data)
        return None
    return data.get("access_token")[0]
