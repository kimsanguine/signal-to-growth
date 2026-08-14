"""Render `harness/decisions.jsonl` as a readable public decision log.

The gate log is append-only and machine-shaped: one JSON object per line, with
`decision_id`, verdict, reasons, and the trigger that reopens it. That shape is
right for validation and wrong for a reader deciding whether to trust this
repository, so this module projects it into Markdown.

The projection is derived, never authored. `runtime/decision-log.md` is generated
from the gate log and a test compares the two, so the published page cannot
drift into saying something the ledger does not.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


HEADER = """# Decision log

이 문서는 `harness/decisions.jsonl`을 사람이 읽는 형태로 렌더링한 결과입니다.
직접 편집하지 마세요. 갱신은 다음 명령으로 합니다.

```bash
python3 scripts/render_decision_log.py
```

기록 원본은 append-only이므로 이 문서도 기록 순서(오래된 것부터)를 그대로
따릅니다. 판정이 바뀌면 앞선 항목을 고치지 않고 새 항목을 추가하며, 새 항목이
어떤 판정을 대체하는지는 `대체 대상`에 남습니다.

각 항목은 판정(`decision`), 그 판정을 뒤집는 조건(`review_trigger`), 그리고
관측된 결과(`outcome`)를 분리해 적습니다. 결과가 `아직 관측되지 않음`이면 그
판정은 아직 검증된 것이 아니라 기록된 것입니다.
"""

VERDICT_LABELS = {
    "build": "build (진행)",
    "hold": "hold (보류)",
    "pivot": "pivot (전환)",
}


def _verdict(record: Mapping[str, Any]) -> str:
    verdict = str(record.get("decision", ""))
    return VERDICT_LABELS.get(verdict, verdict)


def _optional(value: Any, absent: str) -> str:
    if value is None or value == "":
        return absent
    return str(value)


def _render_record(record: Mapping[str, Any]) -> list[str]:
    lines = [
        f"## {record.get('decision_id', '(decision_id 없음)')}",
        "",
        f"- 판정: **{_verdict(record)}**",
        f"- 기록 시각: {_optional(record.get('recorded_at'), '(없음)')}",
        f"- 대상 gate: {_optional(record.get('gate'), '(없음)')}"
        f" / project: {_optional(record.get('project'), '(없음)')}",
        f"- 점수: {_optional(record.get('score'), '해당 없음')}",
        f"- 대체 대상: {_optional(record.get('supersedes'), '없음 (선행 판정을 대체하지 않음)')}",
        f"- 관측된 결과: {_optional(record.get('outcome'), '아직 관측되지 않음')}",
        "",
        "**판정 근거**",
        "",
    ]
    reasons = record.get("reasons")
    if isinstance(reasons, Sequence) and not isinstance(reasons, str) and reasons:
        lines.extend(f"- {reason}" for reason in reasons)
    else:
        lines.append("- (기록된 근거 없음)")
    lines.extend(
        [
            "",
            "**재검토 조건**",
            "",
            f"{_optional(record.get('review_trigger'), '(기록된 재검토 조건 없음)')}",
        ]
    )
    scope_note = record.get("scope_note")
    if scope_note:
        lines.extend(["", "**범위 경계**", "", str(scope_note)])
    return lines


def render_decision_log(records: Sequence[Mapping[str, Any]]) -> str:
    """Return the Markdown projection of gate-decision `records`, in file order."""
    sections = [HEADER.rstrip("\n")]
    if not records:
        sections.append("\n기록된 판정이 없습니다.")
        return "\n".join(sections) + "\n"
    for record in records:
        sections.append("\n" + "\n".join(_render_record(record)))
    return "\n".join(sections) + "\n"
