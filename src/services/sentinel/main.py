import json
import os
from typing import List
from typing import Literal

import requests
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from libs.logging_helper import logger

# Load secrets from ENV
AIP_SENTINEL_API_KEY = os.getenv("AIP_SENTINEL_API_KEY")
AIP_SENTINEL_ENDPOINT = os.getenv("AIP_SENTINEL_ENDPOINT")


@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def call_sentinel_api(
    text: str,
    filters: List[
        Literal["lionguard"] | Literal["promptguard"] | Literal["off-topic-2"]
    ] = [
        "lionguard",
        "promptguard",
        "off-topic-2",
    ],
    params: dict = {},
):
    # Set header
    HEADERS = {
        "x-api-key": AIP_SENTINEL_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "filters": filters,
        "text": text,
        "params": params,
    }

    logger.debug(
        {
            "msg": "Calling Sentinel API",
            "payload": payload,
        }
    )

    # Make the POST request
    response = requests.post(
        url=AIP_SENTINEL_ENDPOINT, headers=HEADERS, data=json.dumps(payload)
    )

    if response.status_code != 200:
        raise Exception(
            f"Sentinel API responds with code {response.status_code}: "
            f"{response.text}"
        )

    return response.json()
