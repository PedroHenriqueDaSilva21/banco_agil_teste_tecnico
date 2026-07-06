

from __future__ import annotations

import logging
import os
import re
from logging.handlers import RotatingFileHandler


_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "flow.log")
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3


_NOISY_LOGGERS = [
    "boto3", "botocore", "urllib3", "httpx", "httpcore",
    "mcp", "anyio", "asyncio", "s3transfer",
]


_FORMATTER = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-5s | %(name)-30s | tid=%(thread_id)-36s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_FALLBACK_FORMATTER = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-5s | %(name)-30s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class _ThreadIdFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "thread_id"):
            record.thread_id = "-"
        return True




def configure_logging() -> None:
    os.makedirs(_LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(logging.DEBUG)

    tid_filter = _ThreadIdFilter()

    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_FORMATTER)
    file_handler.addFilter(tid_filter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(_FORMATTER)
    console_handler.addFilter(tid_filter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def mask_cpf(cpf: str) -> str:
    digits = re.sub(r"\D", "", cpf or "")
    if len(digits) == 11:
        return f"***.***.***-{digits[-2:]}"
    return "***"


def mask_date(date: str) -> str:
    if not date:
        return "***"

    m = re.match(r"(\d{2})[/\-](\d{2})[/\-](\d{4})$", date.strip())
    if m:
        return f"**/**/{m.group(3)}"

    m = re.match(r"(\d{4})[/\-](\d{2})[/\-](\d{2})$", date.strip())
    if m:
        return f"{m.group(1)}-**-**"

    return "***"
