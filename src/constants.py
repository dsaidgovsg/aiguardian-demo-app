import os

from dotenv import load_dotenv

load_dotenv(os.getenv("ENV_FILE"), override=True)

# General
PRODUCT = os.getenv("PRODUCT")
VERSION = os.environ.get("VERSION", "0")
ENV = os.getenv("ENV", "stg")
SG_TZ = "Asia/Singapore"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
