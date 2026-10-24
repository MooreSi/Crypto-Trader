"""Small process and filesystem helpers with no dependencies above utils/."""
from __future__ import annotations

import re
from pathlib import Path


def repo_root() -> Path:
    """The checkout this process is running from."""
    return Path(__file__).resolve().parents[3]


#: Anything that looks like a 64-hex private key, with or without 0x. A log
#: line that carried one would put a trading key into a diagnostics bundle.
_KEYLIKE = re.compile(r"(0x)?[0-9a-fA-F]{64}")


def scrub_log_secrets(text: str) -> str:
    """Redact private-key-shaped strings before text leaves this machine."""
    return _KEYLIKE.sub("[redacted-key]", text)
