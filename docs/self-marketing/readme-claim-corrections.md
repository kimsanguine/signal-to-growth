# README 크로스런타임 클레임 정정 — 각주 초안

- 작성일: 2026-08-04
- 상태: **문구 초안만**. README.md를 수정하지 않았고, 훅·어댑터 구현도 하지
  않았습니다. 구현은 자동화·에이전트개발 담당 영역입니다.
- 통합: Wave 3 콘텐츠

## 왜 정정이 필요한가

README의 두 곳이 "하나의 소스, 두 런타임"을 원칙 수준에서 서술합니다.
manifest가 같은 `skills/` 소스를 가리킨다는 건 사실입니다
(`.claude-plugin/plugin.json:19`, `.codex-plugin/plugin.json:19`).

문제는 **안전장치까지 두 런타임에서 같다고 읽힌다**는 점입니다. 실제로는
append-only 산출물 덮어쓰기를 막는 PreToolUse 훅이 Claude Code 쪽에만
있습니다 (`hooks/hooks.json:3-5`). Codex manifest에는 hooks 키가 없습니다
(`.codex-plugin/plugin.json:1-39`). 게다가 두 런타임의 30-case 호출 parity는
아직 검증되지 않았습니다 (`eval/summary.md:40-51`).

이 저장소가 파는 것이 "검증 상태를 정확히 쓰는 습관"이므로, 이 간극을 남겨
두면 제품 주장과 문서가 서로를 반박합니다.

---

## 정정 1 — README 49행 「핵심 원칙 5」

### 현재 문구

> 5. **One source, two adapters** — 공통 스킬을 유지하고 플랫폼별 manifest만 분리합니다.

### 제안 A (권장) — 본문 한 줄 + 각주

> 5. **One source, two adapters** — 공통 스킬을 유지하고 플랫폼별 manifest만
>    분리합니다. 다만 런타임이 제공하는 안전장치는 아직 동일하지 않습니다.[^runtime-parity]
>
> [^runtime-parity]: append-only 산출물의 덮어쓰기를 차단하는 PreToolUse 훅은
> 현재 Claude Code에만 구현돼 있습니다(`hooks/hooks.json`). Codex에서는 같은
> 규칙이 `SKILL.md`의 지시와 `append-record` CLI로만 유지되며, 도구 수준의
> 강제는 아직 없습니다. Codex 대응은 진행 중입니다. 두 런타임의 30-case
> 호출 parity 역시 미검증 상태입니다([Evaluation summary](../../eval/summary.md)).

> **경로 주의**: 위 각주의 링크는 이 파일 위치(`docs/self-marketing/`) 기준
> `../../eval/summary.md`입니다. README.md에 옮길 때는 `eval/summary.md`로
> 바꾸세요. `tests/test_docs.py`가 상대 링크 실존을 검사하므로, 경로를 고치지
> 않으면 통합 시 테스트가 깨집니다.

### 제안 B — 원칙 문구 자체를 좁힘

> 5. **One source, two adapters** — 스킬 정의와 산출물 계약은 공통 소스
>    하나에서 나오고, 플랫폼별 manifest만 분리합니다. 런타임별 훅과 강제
>    수준은 별도로 기록합니다.[^runtime-parity]

제안 A를 권장합니다. 원칙 문장의 표어(One source, two adapters)는 그대로
살아 있어야 다른 문서·교안과 어긋나지 않습니다.

---

## 정정 2 — README 528~535행 「경쟁 제품과 다른 점」

### 현재 문구 (534행)

> - 한 source에서 Claude Code·Codex로 배포

### 제안

> - 한 source에서 Claude Code·Codex로 배포 (런타임별 강제 수준은 아직
>   다릅니다[^runtime-parity])

같은 각주를 재사용합니다. 목록 항목 안에서 길게 설명하면 나머지 다섯 항목과
리듬이 깨집니다.

### 함께 볼 것 — 530행

> - 인터뷰 quote에서 outcome까지의 reference integrity

이 항목은 정정이 필요 없습니다. reference integrity는 CLI와 schema가
런타임과 무관하게 강제하기 때문입니다(`src/signal_growth/contracts.py`,
`contracts/*.schema.json`). 훅에만 의존하는 항목과 구분해서 남겨 두세요.

---

## 톤 기준

각주를 쓸 때 지킬 것:

- **결함 고백이 아니라 범위 서술로 쓴다.** "아직 안 됩니다"가 아니라
  "현재 여기까지 구현됐고 저쪽은 진행 중"으로.
- **"진행 중"을 날짜 약속으로 바꾸지 않는다.** 일정은 사람이 정할 영역이고,
  이 저장소는 릴리스 게이트를 통과하지 않은 상태입니다.
- **Codex를 열등한 런타임으로 서술하지 않는다.** 없는 것은 Codex의 능력이
  아니라 이 저장소의 어댑터 구현입니다.
- **"Claude Code에서만 안전하다"로 읽히지 않게 한다.** 승인 경계·정책·schema
  검증은 두 런타임 공통이고, 차이는 훅이라는 한 층입니다.

## 이 문서가 하지 않은 것

- README.md 수정 — Wave 3 담당자 영역
- Codex 쪽 훅 또는 동등 강제 장치 구현 — 자동화·에이전트개발 담당 영역
- "Codex 대응 진행 중"의 실제 작업 항목 생성 — 담당자 배정은 사람 결정

## 근거

| 주장 | 근거 |
|---|---|
| 두 manifest가 같은 `skills/` 소스를 가리킨다 | `.claude-plugin/plugin.json:19`, `.codex-plugin/plugin.json:19` |
| append-only 훅은 Claude Code PreToolUse에만 등록됐다 | `hooks/hooks.json:3-5` |
| Codex manifest에 hooks 키가 없다 | `.codex-plugin/plugin.json:1-39` |
| append-only 대상은 13종 JSONL이다 | `src/signal_growth/append_only.py:22-38` |
| 훅 없이도 `append-record` CLI 경로는 동작한다 | `src/signal_growth/append_only.py:172-181` |
| 두 런타임 호출 parity가 미검증이다 | `eval/summary.md:40-51` |

같은 근거가 `claim-ledger.jsonl`의 CLM-20260804-002, -006, -007, -010에도
등록돼 있습니다.
