# 학습자 시작 안내

이 안내의 기본 경로는 Claude Code plugin과 read-only preview입니다. Python CLI는
선택형 검증 도구이며, preview를 받기 위한 선행 조건이 아닙니다.

## 설치와 버전 확인

1. Claude Code에서 다음을 순서대로 실행합니다.

   ```text
   /plugin marketplace add kimsanguine/signal-to-growth
   /plugin install signal-to-growth@signal-to-growth
   /reload-plugins
   ```

2. 새 세션을 열고 `/run-growth-loop`를 실행합니다.
3. 설치된 plugin의 버전은 Claude Code의 `/plugin` 화면에서 확인합니다. GitHub의
   repository release 또는 로컬 checkout의 버전은 설치된 cache 버전을 증명하지 않습니다.
4. 새 preview가 six labeled parts를 반환하지 않거나 skill 목록에 없다면, install과
   reload를 다시 실행한 뒤 새 세션에서 확인합니다. 그래도 해결되지 않으면 그 상태를
   `not verified`로 남기고, 화면의 오류 문구와 설치된 버전만 기록합니다.

## 첫 preview

```text
/run-growth-loop

fixtures/public-dummy/artifacts를 학습 모드로 점검해줘.
파일을 바꾸지 말고 다음 skill 하나와 이유를 보여줘.
AI가 제안할 것, 사람이 결정할 것, 검증됨과 미확인을 분리해줘.
```

## preview가 돌려주는 여섯 항목

정상 응답은 아래 여섯 개를 라벨과 함께 분리해 보여줍니다. 위 3~4단계의 버전 확인은
이 목록을 대조 기준으로 씁니다.

1. **읽은 입력(inputs read)** — 어떤 artifact·파일을 실제로 읽었는가
2. **모델 해석(model interpretation)** — AI가 그 입력을 어떻게 읽었는가
3. **결정론적으로 검증된 사실(deterministically verified facts)** — CLI·schema로 확인된 것
4. **미검증·차단된 사실(unverified or blocked facts)** — 확인하지 못했거나 막힌 것
5. **사람이 결정해야 할 항목(decisions that require a person)** — AI가 대신 정하지 않는 것
6. **제안된 파일 변경과 다음 skill 하나(proposed changes + next skill)** — 이유를 함께

여섯 개가 다 오지 않거나 라벨이 없다면 preview가 아니라 설치·버전 문제일 가능성이
큽니다. 그 상태는 `not verified`로 남기고 install/reload를 다시 실행합니다.

이 호출은 파일을 만들거나 바꾸지 않아야 합니다. 다음 단계에서 artifact를 만들고 싶다면
preview 결과에 나온 파일 이름과 범위를 검토한 뒤, **다음 사용자 메시지**에서 apply 권한을
명시합니다.

## 사람 태그에서 멈추는 이유

`evidence.jsonl`의 `strength=awaiting_human_tag`는 AI가 evidence를 정리했지만
사람이 강도를 아직 검토하지 않았다는 뜻입니다. 이 상태의 evidence는 signal, decision,
outcome의 근거로 쓸 수 없습니다. 원문·locator·반증을 검토한 사람이 strength와
`approved_by`를 채운 뒤에만 다음 전문 skill으로 진행합니다.

## 선택형 Python 검증

Python 3.11 이상을 이미 사용할 수 있을 때만 다음을 실행합니다.

```bash
signal-to-growth validate-artifacts fixtures/public-dummy/artifacts
signal-to-growth next-step fixtures/public-dummy/artifacts
```

### `signal-to-growth`와 `python3 scripts/stg.py`의 관계

같은 CLI를 부르는 두 형식이며 결과는 동일합니다. `signal-to-growth`는
`pip install -e .`로 설치했을 때 생기는 console script이고,
`python3 scripts/stg.py`는 설치 없이 저장소 checkout만으로 같은 진입점을
실행하는 wrapper입니다. 각 skill의 `SKILL.md`가 wrapper 형식으로 안내하는 이유는
읽는 사람이 패키지를 설치했다고 가정할 수 없기 때문입니다. 설치했다면 앞의 형식을,
설치 전이라면 뒤의 형식을 쓰세요. 위 명령은 아래처럼 바꿔 써도 같습니다.

```bash
python3 scripts/stg.py validate-artifacts fixtures/public-dummy/artifacts
python3 scripts/stg.py next-step fixtures/public-dummy/artifacts
```

CLI를 실행하지 못하면 preview 자체가 실패한 것은 아닙니다. deterministic 검증만
`not verified`로 남기고, 설치·입력·사람 승인 상태를 분리해 기록합니다.
