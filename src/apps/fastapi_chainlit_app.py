import os
import time

from chainlit.utils import mount_chainlit

from apps.fastapi_app import app
from constants import ENV
from constants import PRODUCT
from constants import VERSION
from libs.logging_helper import logger

start_time = time.time()
logger.info(f"Starting {PRODUCT}-{ENV} app v{VERSION}")

app_file = os.environ.get("CHAINLIT_APP_FILE", "default_app.py")
path = os.environ.get("CHAINLIT_ROOT_PATH", "")

if not os.getenv("CHAINLIT_AUTH_SECRET"):
    from chainlit.secret import random_secret

    os.environ["CHAINLIT_AUTH_SECRET"] = random_secret()


logger.info(f"Mounting chainlit app {app_file} on path {path}")
mount_chainlit(
    app=app,
    target=os.path.join(os.path.dirname(__file__), "..", app_file),
    path=path,
)

logger.info(f"Server started in {time.time() - start_time:.2f}s")
