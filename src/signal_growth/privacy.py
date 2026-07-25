"""Detect likely private data without echoing matched values."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "korean-mobile": re.compile(r"(?<!\d)01[016789][-\s]?\d{3,4}[-\s]?\d{4}(?!\d)"),
    "international-phone": re.compile(r"(?<!\d)\+\d{1,3}[-\s]?\d{2,4}[-\s]?\d{3,4}[-\s]?\d{4}(?!\d)"),
    "api-key": re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[opusr]_[A-Za-z0-9]{16,})\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
}


@dataclass(frozen=True)
class PrivacyFinding:
    kind: str
    line: int

    def render(self, path: Path) -> str:
        return f"{path}:{self.line}: possible {self.kind}"


def scan_text(text: str) -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for kind, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append(PrivacyFinding(kind=kind, line=line_number))
    return findings


def scan_path(path: Path) -> list[PrivacyFinding]:
    return scan_text(path.read_text(encoding="utf-8"))
