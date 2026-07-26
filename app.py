"""Vercel-recognized WSGI entry point for the Kakao test integration."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from signal_growth.hosted_app import HostedKakaoApplication  # noqa: E402


app = HostedKakaoApplication()
