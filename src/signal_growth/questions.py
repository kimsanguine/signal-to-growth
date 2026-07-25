"""Lint interview questions for common evidence-quality risks."""

from __future__ import annotations

import re
from dataclasses import dataclass


RULES = {
    "leading": [
        re.compile(r"원하시죠|필요하시죠|불편하셨죠|좋겠죠"),
        re.compile(r"\b(?:don't you think|wouldn't you agree)\b", re.I),
    ],
    "hypothetical": [
        re.compile(r"만약.+라면|사용하시겠|쓸 것 같|구매하시겠"),
        re.compile(r"\b(?:would you|will you|imagine if)\b", re.I),
    ],
    "solution-first": [
        re.compile(r"원하는 기능|필요한 기능|어떤 기능을"),
        re.compile(r"\b(?:what feature|which feature)\b", re.I),
    ],
    "compound": [
        re.compile(r"\?.+\?"),
        re.compile(r"(?:그리고|또한).+\?"),
    ],
}


@dataclass(frozen=True)
class QuestionIssue:
    line: int
    rule: str

    def render(self) -> str:
        return f"line {self.line}: {self.rule} question risk"


def lint_questions(text: str) -> list[QuestionIssue]:
    issues: list[QuestionIssue] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if "?" not in line and "까" not in line and "나요" not in line:
            continue
        for rule, patterns in RULES.items():
            if any(pattern.search(line) for pattern in patterns):
                issues.append(QuestionIssue(line=line_number, rule=rule))
    return issues
