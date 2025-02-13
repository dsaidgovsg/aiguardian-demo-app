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
    guardrails: dict,
    additional_params: dict | None,
) -> Tuple[bool, str | None]:
    sentinel_check_result = call_sentinel_api(
        text=text,
        guardrails=guardrails,
        additional_params=additional_params,
    )

    failed_guardrails: List[str] = []

    for guardrail, result in sentinel_check_result["results"].items():
        if result["score"] > 0.95:
            failed_guardrails.append(f'{guardrail} ({result["score"]:.4f})')
    if failed_guardrails:
        return False, (
            f"{'These validations failed: '.join(failed_guardrails[1:])}. Revise your prompt or check with our technical support."  # noqa: E501
        )
        # return False, errors[0]

    return True, None


@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def call_sentinel_api(
    text: str,
    guardrails: dict,
    additional_params: dict | None,
):
    start = time.time()

    # Set url & headers
    url = f'{os.environ["SENTINEL_BASE_URL"]}/api/v1/validate'
    headers = {
        "x-api-key": os.environ["SENTINEL_API_KEY"],
        "Content-Type": "application/json",
    }

    payload = json.dumps(
        {"text": text, "guardrails": guardrails, **(additional_params or {})}
    )

    logger.debug(
        {
            "msg": "Calling Sentinel API",
            "payload": payload,
        }
    )

    response = requests.request("POST", url, headers=headers, data=payload)

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
