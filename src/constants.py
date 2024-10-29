import json
import os

from dotenv import load_dotenv

from datatypes.llm_profile import LLMProfile

load_dotenv(os.getenv("ENV_FILE"), override=True)

# General
PRODUCT = os.getenv("PRODUCT")
VERSION = os.environ.get("VERSION", "0")
ENV = os.getenv("ENV", "stg")
REGION = os.getenv("REGION", "us-east-1")
SG_TZ = "Asia/Singapore"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

LLM_PROFILES = [
    LLMProfile(**profile)
    for profile in json.loads(os.getenv("LLM_PROFILES", "[]"))
]
