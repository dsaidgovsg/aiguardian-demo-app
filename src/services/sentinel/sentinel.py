import json
import os
import time
from typing import List
from typing import Tuple

import requests
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from libs.logging_helper import logger

# Load Sentinel Server details from Env Variables
SENTINEL_BASE_URL = os.getenv("SENTINEL_BASE_URL")
SENTINEL_API_KEY = os.getenv("SENTINEL_API_KEY")

if not SENTINEL_BASE_URL or not SENTINEL_API_KEY:
    raise Exception(
        "Missing SENTINEL_BASE_URL / SENTINEL_API_KEY in environment variables"
    )


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
        if result["score"] >= 0.95:
            failed_guardrails.append(f'{guardrail} ({result["score"]:.3f})')
    if failed_guardrails:
        return False, (
            f"These validations failed: {' '.join(failed_guardrails[0:])}. Revise your prompt or check with our technical support."  # noqa: E501
        )

    return True, None


@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def call_sentinel_api(
    text: str,
    guardrails: dict,
    additional_params: dict | None,
):
    start = time.time()

    # Set url & headers
    url = f"{SENTINEL_BASE_URL}/api/v1/validate"
    headers = {
        "x-api-key": SENTINEL_API_KEY,
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
            "response_headers": response.headers.lower_items(),
            "duration": time.time() - start,
        }
    )

    if response.status_code != 200:
        raise Exception(
            f"Sentinel API responds with code {response.status_code}: "
            f"{response.text}"
        )

    return response.json()
