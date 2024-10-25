import json
import logging
import os
import sys
import traceback
from datetime import datetime

from pydantic.v1.json import pydantic_encoder

from constants import PRODUCT

__all__ = ["logger"]


class JSONFormatter(logging.Formatter):
    def format(self, record):
        record.msg = json.dumps(
            {
                "process": f"{record.process} {record.processName}",
                "time": datetime.utcnow().isoformat(
                    sep=" ", timespec="milliseconds"
                ),
                "level": record.levelname,
                "file": record.filename,
                "line": record.lineno,
                "func": record.funcName,
                "msg": record.msg,
                **(
                    {"error_trace": traceback.format_exc()}
                    if record.levelname == "ERROR"
                    else {}
                ),
            },
            default=pydantic_encoder,
        )
        return super().format(record)


class JSONMessageFormatter(logging.Formatter):
    def format(self, record):
        record.msg = "{} | {} | {} | {} | {} | {} | {} {}".format(
            datetime.utcnow().isoformat(sep=" ", timespec="milliseconds"),
            f"{record.process} {record.processName}",
            record.levelname,
            record.filename,
            record.lineno,
            record.funcName,
            (
                json.dumps(record.msg, default=pydantic_encoder)
                if isinstance(record.msg, dict)
                else record.msg
            ),
            (
                f"\n{traceback.format_exc()}"
                if record.levelname == "ERROR"
                else ""
            ),
        )
        return super().format(record)


stdout_log = logging.StreamHandler(sys.stdout)
if os.getenv("LOG_FORMAT") == "json":
    stdout_log.setFormatter(JSONFormatter())
else:
    stdout_log.setFormatter(JSONMessageFormatter())

logging.basicConfig(force=True, handlers=[stdout_log])

logger = logging.getLogger(PRODUCT)

# Configure log levels (what to filter to outputs).
logger.setLevel(os.getenv("LOG_LEVEL", "DEBUG"))
# logging.getLogger("openai").setLevel(os.getenv("LOG_LEVEL", "DEBUG"))
