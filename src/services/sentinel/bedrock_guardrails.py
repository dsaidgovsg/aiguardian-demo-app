import os
import time
from typing import Literal
from typing import Tuple

import boto3
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from constants import REGION
from libs.logging_helper import logger

client = boto3.client("bedrock-runtime", region_name=REGION)

# Load secrets from ENV
BEDROCK_GUARDRAIL_ARN = os.getenv("BEDROCK_GUARDRAIL_ARN")
BEDROCK_GUARDRAIL_VERSION = os.getenv("BEDROCK_GUARDRAIL_VERSION")

guardrail_checks = {
    "INSULTS": {
        "message": "Insults detected and logged.",
    },
    "HATE": {
        "message": "Hateful message detected and logged.",
    },
    "SEXUAL": {
        "message": "Sexual content detected and logged.",
    },
    "VIOLENCE": {
        "message": "Violence detected and logged.",
    },
    "MISCONDUCT": {
        "message": "Misconduct detected and logged.",
    },
    "PROMPT_ATTACK": {
        "message": "Prompt attack attempt detected and logged.",
    },
}


def validate(
    text: str,
    source: Literal["INPUT"] | Literal["OUTPUT"] = "INPUT",
) -> Tuple[bool, str | None]:
    """
    Validate using Bedrock Guardrails
    Args:
        text:
        source:

    Returns: True if passed, False if failed, and error message if failed

    """
    sentinel_check_result = call_bedrock_guardrails(
        text=text,
        source=source,
    )

    for result in (
        sentinel_check_result["assessments"][0]
        .get("contentPolicy", {})
        .get("filters", [])
    ):
        if (
            result["action"] == "BLOCKED"
            and result["type"] in guardrail_checks
        ):
            return False, guardrail_checks[result["type"]]["message"]

    return True, None


@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def call_bedrock_guardrails(
    text: str,
    source: Literal["INPUT"] | Literal["OUTPUT"] = "INPUT",
):
    payload = {
        "source": source,
        "content": [
            {"text": {"text": text}},
        ],
    }

    logger.debug(
        {
            "msg": "Calling Bedrock Guardrail",
            "payload": payload,
        }
    )

    start = time.time()

    response = client.apply_guardrail(
        guardrailIdentifier=BEDROCK_GUARDRAIL_ARN,
        guardrailVersion=BEDROCK_GUARDRAIL_VERSION,
        **payload,
    )

    logger.info(
        {
            "msg": "Bedrock Guardrail response",
            "response": response,
            "duration": time.time() - start,
        }
    )

    return response
