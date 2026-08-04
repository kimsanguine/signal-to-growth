"""Vercel-recognized WSGI entry point for the Kakao test integration."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from signal_growth.hosted_app import HostedKakaoApplication  # noqa: E402
from signal_growth.observability import LOGGER_NAME  # noqa: E402


# Configuring handlers is the host application's job, not the library's.
# Without this the ingest logs would depend on logging's lastResort fallback,
# which drops anything below WARNING and is easy to lose on a platform change.
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(message)s")
logging.getLogger(LOGGER_NAME).setLevel(logging.INFO)

app = HostedKakaoApplication()
