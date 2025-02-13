import json
import os
import time
from typing import List
from typing import Literal
from typing import Tuple

import requests
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from libs.logging_helper import logger

# Load secrets from ENV
AIP_SENTINEL_API_KEY = os.getenv("AIP_SENTINEL_API_KEY")
AIP_SENTINEL_ENDPOINT = os.getenv("AIP_SENTINEL_ENDPOINT")


sentinel_checks = [
    # {
    #     "type": "lionguard",
    #     "subtype": "binary",
    #     "threshold": 0.8,
    #     "message": "Binary message detected and logged.",
    # },
    {
        "type": "lionguard",
        "subtype": "hateful",
        "threshold": 0.8,
        "message": "Hateful message detected and logged.",
    },
    {
        "type": "lionguard",
        "subtype": "harassment",
        "threshold": 0.8,
        "message": "Harassment detected and logged.",
    },
    {
        "type": "lionguard",
        "subtype": "public_harm",
        "threshold": 0.8,
        "message": "Public harm detected and logged.",
    },
    {
        "type": "lionguard",
        "subtype": "self_harm",
        "threshold": 0.8,
        "message": "Self harm detected and logged.",
    },
    {
        "type": "lionguard",
        "subtype": "sexual",
        "threshold": 0.8,
        "message": "Sexual content detected and logged.",
    },
    {
        "type": "lionguard",
        "subtype": "toxic",
        "threshold": 0.8,
        "message": "Toxic content detected and logged.",
    },
    {
        "type": "lionguard",
        "subtype": "violent",
        "threshold": 0.8,
        "message": "Violent content detected and logged.",
    },
    {
        "type": "promptguard",
        "subtype": "jailbreak",
        "threshold": 0.8,
        "message": "Jailbreak attempt detected and logged.",
    },
    {
        "type": "off-topic-2",
        "subtype": "off-topic",
        "threshold": 0.8,
        "message": "Off-topic message detected and logged.",
    },
]


def validate(
    text: str,
    filters: List[
        Literal["lionguard"] | Literal["promptguard"] | Literal["off-topic-2"]
    ] = [
        "lionguard",
        "promptguard",
        "off-topic-2",
    ],
    params: dict = {},
) -> Tuple[bool, str | None]:
    """
    Validate using AIP Sentinel API

    # Sample output from the API
    {
      "outputs": {
        "lionguard": {
          "binary": 0,
          "hateful": 0,
          "harassment": 0,
          "public_harm": 0,
          "self_harm": 0,
          "sexual": 0,
          "toxic": 0,
          "violent": 0
        },
        "promptguard": {
          "jailbreak": 0.9804580807685852
        },
        "off-topic-2": {
          "off-topic": 0.28574493527412415
        },
        "request_id": "1f8e8089-b71b-4054-881b-ee727f46f3c2"
      }
    }

    Args:
        text:
        filters:
        params:

    Returns: True if passed, False if failed, and error message if failed

    """
    sentinel_check_result = call_sentinel_api(
        text=text,
        filters=filters,
        params=params,
    )

    errors: List[str] = []
    for check in sentinel_checks:
        if (
            sentinel_check_result["outputs"]
            .get(check["type"], {})
            .get(check["subtype"], 0)
            > check["threshold"]
        ):
            errors.append(str(check["message"]))
    if errors:
        # first_error = errors[0]
        # return False, (
        #     f"{first_error}{' ' if len(errors) > 1 else ''}"
        #     f"{' '.join(errors[1:])} detected and logged."
        # )
        return False, errors[0]

    return True, None


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

    start = time.time()

    # Make the POST request
    response = requests.post(
        url=AIP_SENTINEL_ENDPOINT, headers=HEADERS, data=json.dumps(payload)
    )

    logger.info(
        {
            "msg": "Sentinel API response",
            "response": response.text,
            "response_headers": response.headers,
            "duration": time.time() - start,
        }
    )

    if response.status_code != 200:
        raise Exception(
            f"Sentinel API responds with code {response.status_code}: "
            f"{response.text}"
        )

    return response.json()
