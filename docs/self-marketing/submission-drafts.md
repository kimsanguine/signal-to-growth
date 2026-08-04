# 외부 등록 초안 — 제출 전 상태

- 작성일: 2026-08-04
- 상태: **초안. 제출하지 않았습니다.** PR 생성·폼 제출은 사람이 판단해 별도로 진행합니다.
- 이 문서의 목적: 제출에 필요한 내용을 미리 만들어 두고, 각 대상의 수용 조건을
  실제로 확인해 "지금 내도 되는가"를 판정 가능한 상태로 남기는 것.
- 관찰 표기는 이 저장소의 다른 감사 산출물과 같습니다 — `observed`는 직접 확인한
  것, `unknown`은 확인하지 못한 것, 사람 판단이 필요한 항목은 그렇게 적습니다.

## 요약 판정

| 대상 | 제출 가능 | 막는 것 |
|---|---|---|
| llms-txt-hub | 조건부 가능 | 등록 단위가 "웹사이트"인데 우리에겐 저장소밖에 없음 — 사람 판단 필요 |
| awesome-claude-skills | **불가** | 대상 저장소 특정 안 됨 + star 하한 미달 + AI 보조 제출 금지 |

---

## 1. llms-txt-hub

### 확인한 사실 (2026-08-04, `observed`)

- 기여 경로는 두 개다: 웹 폼 제출, 또는 `packages/content/data/websites/` 아래에
  `.mdx` 파일을 추가하는 PR.
- 자동 생성 파일은 직접 수정하면 거부된다. 추가할 파일은 `.mdx` 하나뿐이다.
- frontmatter 필드는 `name`, `description`, `website`, `llmsUrl`,
  `llmsFullUrl`, `category`, `publishedAt`, `priority`, `featured`.
- `priority`와 `featured`는 필수가 아니다. 기존 등록 중 두 필드를 생략한 항목이
  실재한다. **우리가 스스로 `high`나 `featured: true`를 적지 않는다.**
- `category: 'developer-tools'`는 실재하는 값이다(기존 등록에서 확인).
- 우리 llms.txt와 저장소 페이지 모두 HTTP 200으로 응답한다(직접 curl 확인).

### 확인하지 못한 것 (`unknown`)

- `category` 허용값의 전체 목록. `developer-tools`가 유효하다는 것만 확인했고
  더 맞는 값이 있는지는 확인하지 않았다.
- 심사 기준과 소요 시간.

### 사람이 판단할 것

이 목록의 등록 단위는 **웹사이트**입니다. 우리에게는 별도 사이트가 없고
llms.txt는 저장소 파일로만 존재합니다. `website`에 저장소 URL을,
`llmsUrl`에 raw URL을 적는 것이 이 목록의 취지에 맞는지는 제출자가 정할
문제입니다. `docs/self-marketing/recommendations.md`의 R6이 이미 같은 이유로
"없는 표면을 먼저 만들지 말 것"을 권고하고 있으므로, 이 판단은 그 권고와
함께 읽어야 합니다. `llmsFullUrl`은 우리에게 해당 파일이 없으므로 생략합니다.

### 제출용 파일 초안

경로: `packages/content/data/websites/signal-to-growth-llms-txt.mdx`

```mdx
---
name: 'Signal to Growth'
description: 'Agent Skills that keep customer quotes, growth decisions, and outcomes traceable to their sources, with external writes disabled until a human approves.'
website: 'https://github.com/kimsanguine/signal-to-growth'
llmsUrl: 'https://raw.githubusercontent.com/kimsanguine/signal-to-growth/main/llms.txt'
category: 'developer-tools'
publishedAt: '2026-08-04'
---

# Signal to Growth

Eleven portable Agent Skills that turn customer interviews, support signals, and
behavioral metrics into growth decisions a person approved. One `skills/` source
is referenced by a Claude Code manifest and an OpenAI Codex manifest.

## Key Focus Areas

- Reference integrity from a customer quote through to a measured outcome
- Human approval boundaries for sending, publishing, deploying, and deleting
- JSON Schema artifact contracts instead of conversational memory

## About llms.txt Implementation

The file states what this repository does not contain before it states what it
does: there is no real customer data, no adoption numbers, and no performance
claims, and its fixtures are synthetic. It also records that the project has
not passed its own release gate, so an answer engine citing it has the
limitations in the same file as the summary.
```

### PR 설명 초안

```text
Title: Add Signal to Growth llms.txt

Adds one .mdx entry under packages/content/data/websites/.

- Project: eleven portable Agent Skills for evidence-driven product growth, MIT licensed.
- llms.txt: served from the repository's default branch, verified reachable on 2026-08-04.
- Note: this project has no separate marketing site. `website` points at the
  repository, which is the surface the llms.txt describes. If the list requires a
  standalone domain, close this PR and I will resubmit when one exists.
- The llms.txt states the project's limits (synthetic fixtures, no adoption
  numbers, release gate not passed) alongside its summary, so a model citing it
  gets the caveats too.

No auto-generated files were edited.
```

---

## 2. awesome-claude-skills

### 확인한 사실 (2026-08-04, `observed`)

`awesome-claude-skills`라는 이름의 저장소가 여러 개 있고 관리 주체가 다릅니다.
"awesome-claude-skills에 제출"이라는 지시만으로는 대상이 특정되지 않습니다.
아래 조사는 awesome list 규약을 따르는 저장소 한 곳(별 약 1.4만)의 기여
가이드를 읽은 결과이며, 다른 저장소는 조건이 다를 수 있습니다.

그 저장소의 수용 조건 중 우리 상태로 판정 가능한 것:

| 조건 | 우리 상태 | 판정 |
|---|---|---|
| GitHub star 10개 이상 (미달 시 자동 close) | **0개** (API로 직접 확인) | **불충족** |
| AI 보조로 생성·제출한 PR 금지 | 이 초안은 AI 보조로 작성됨 | **불충족** |
| SKILL.md 한 개를 넘는 실체가 있을 것 | 스킬 11개 + 계약 20종 + 테스트 | 충족 |
| SaaS 유입 경로가 아닐 것 | 외부 서버 요청 없음, MIT, 로컬 실행 | 충족 |
| 문서(README 또는 SKILL.md) 보유 | 보유 | 충족 |

### 판정: 지금 제출하지 마세요

두 개가 하드 게이트입니다.

1. **star 0개.** 가이드는 10개 미만이면 자동으로 닫는다고 명시합니다. 지금 내면
   내용과 무관하게 닫힙니다.
2. **AI 보조 제출 금지.** 이 문서를 포함해 초안이 AI 보조로 작성됐습니다. 이
   조항을 우회해 제출하는 것은 상대 저장소의 명시적 요청을 어기는 일이므로,
   제출한다면 사람이 직접 다시 쓰는 것이 전제입니다.

star는 시간과 실사용으로만 오르는 값이고, 사서 올릴 값이 아닙니다. 이 항목은
저장소가 실제로 쓰인 뒤에 재검토하는 것이 맞습니다.

### 조건이 충족됐을 때 쓸 한 줄 초안

목록 형식은 굵게 표시한 링크 뒤에 하이픈과 한 문장 설명을 붙인 한 줄입니다.
카테고리는 커뮤니티 스킬 쪽입니다.

```markdown
- **[Signal to Growth](https://github.com/kimsanguine/signal-to-growth)** - Eleven skills that keep customer quotes traceable from interview to outcome, with sending and publishing disabled until a human approves.
```

제출 시 함께 밝힐 것: 저자가 곧 제출자라는 점, MIT 라이선스, 그리고 이 저장소가
아직 자체 릴리스 게이트를 통과하지 않았다는 점. 마지막 항목을 감추면 우리
저장소가 스스로에게 요구하는 정직성 기준을 우리가 어기는 셈입니다.

---

## 제출 전 최종 체크

- [ ] 등록 단위가 웹사이트인 목록에 저장소 URL을 적을지 사람이 판정했는가
- [ ] `category` 값이 대상 저장소의 현재 허용 목록에 있는지 재확인했는가
- [ ] 링크가 제출 시점에도 200으로 응답하는지 다시 확인했는가
- [ ] awesome list 쪽은 star 조건과 AI 보조 조항이 해소됐는가
- [ ] 초안 문구에 실사용자 수·성과 수치처럼 우리가 갖지 않은 근거가 들어가지 않았는가
