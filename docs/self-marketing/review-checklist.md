# Review checklist — 자기 랜딩 카피 초안

- 대상: `content-brief.md`, `claim-ledger.jsonl`, `draft.md`
- 작성일: 2026-08-04
- 상태: 사람 검토 대기. 아래 항목이 모두 통과하기 전에는 README 통합·게시 금지.

체크 상태 표기: `[x]` 자동/직접 확인함, `[ ]` 사람 검토 필요.

## 1. 정확성

- [x] 모든 material claim이 `claim-ledger.jsonl`에 ID로 등록돼 있다
      (17건 + 정정 1건 = 18줄).
- [x] 각 claim에 저장소 내 `file:line` locator가 하나 이상 있다.
- [x] `observed` / `reported` / `inferred` / `recommended` / `unknown`이 서로
      구분돼 있다.
- [x] 남에게 들은 값(테스트 수, 평가 점수)은 `observed`가 아니라 `reported`로
      기록했다 — 이번 실행에서 테스트·평가를 재실행하지 않았다.
- [x] 2026-08-04에 주요 locator를 `sed -n`으로 표본 검증했다. 1건(
      CLM-20260804-003의 `docs/approval-boundaries.md` 범위)이 어긋나 있었고,
      원본 줄을 고치지 않고 CLM-20260804-018 정정 레코드를 append했다.
- [ ] locator의 줄 번호가 **검토 시점**의 파일과 여전히 일치한다.
      (파일이 바뀌면 줄 번호가 밀린다. Wave 3 통합 직전에 재확인할 것.)
- [ ] `inferred` 항목(CLM-20260804-015)의 해석에 검토자가 동의한다.

## 2. Evidence reference

- [x] 지어낸 고객 인용문이 없다.
- [x] 사용자 수·도입 사례·성과 수치가 없다 (CLM-20260804-017에 unknown으로 명시).
- [x] 출처 없는 benchmark가 없다 (policies/default-policy.json:53과 일치).
- [x] `claim-ledger.jsonl`은 `append-record` 경로로만 작성했다 — 직접 덮어쓰지
      않았고, 이 저장소의 append-only 규칙을 실제로 통과했다.
- [ ] `refresh_by`가 설정된 3건(CLM-...-008/009/010)의 갱신 담당자를 지정했다.

## 3. Privacy

- [x] `scan-privacy docs/self-marketing/draft.md` → 발견 없음 (2026-08-04 실행).
- [x] `scan-privacy docs/self-marketing/content-brief.md` → 발견 없음.
- [x] 실제 고객 데이터·credential·계정 식별자·비공개 URL을 넣지 않았다.
- [ ] 검토자가 육안으로도 내부 전용 정보가 없음을 확인했다
      (`scan-privacy`는 완전한 DLP가 아니다 — CLM-20260804-012).

## 4. Brand / tone

- [x] 한국어 본문, 기술 용어·식별자는 원문 유지.
- [x] 과장 표현("완벽", "업계 최고", "프로덕션 준비 완료")을 쓰지 않았다.
- [ ] 검토자가 A안/B안 중 하나를 선택했다 (또는 병합안을 지정했다).
- [ ] 상단 카피의 한계 단락을 유지하기로 합의했다.

## 5. Legal

- [x] 타 저장소의 고유 scoring 공식·문구를 복제하지 않았다.
- [x] 경쟁 제품에 대한 단정적 우열 주장이 없다.
- [ ] MIT 라이선스·저작자 표기와 충돌하는 문구가 없는지 검토자가 확인했다.

## 6. Commercial claim

- [x] 가격·환불·SLA·지원 범위에 대한 약속이 없다.
- [x] "도입하면 성장한다" 류의 결과 보장 문구가 없다.
- [ ] 향후 로드맵을 확정 약속처럼 읽히게 쓰지 않았는지 검토자가 확인했다.

## 7. CTA

- [x] 단일 CTA(`/run-growth-loop` preview 1회)로 좁혔다.
- [x] 뉴스레터·문의 폼·상담 유도 등 수신 경로가 없는 CTA를 만들지 않았다.
- [x] CTA가 파일을 바꾸지 않는 preview임을 명시했다.

## 8. 최종 게시 승인

- [ ] **사람 승인**: README.md 상단 교체안을 승인한다 (Wave 3 콘텐츠 통합).
- [ ] **사람 승인**: `llms.txt`를 저장소 루트에 유지한다.
- [ ] **사람 승인**: 외부 게시(블로그·SNS·릴리스 노트)로 확장한다면 그 범위와
      대상을 별도로 지정한다. 이 초안은 그 승인을 포함하지 않는다.
- [ ] **사람 승인 영역 / 이번 실행에서 하지 않음**: git tag, GitHub Release.

## 중단 조건 확인

`skills/draft-evidence-content/SKILL.md:54`의 stop condition 대비:

| 조건 | 상태 |
|---|---|
| 핵심 claim이 근거 없음 | 해당 없음 — 17건 모두 locator 연결 |
| 논증에 restricted evidence가 필요함 | 해당 없음 — 공개 파일만 사용 |
| 출처가 낡았고 갱신 불가 | 해당 없음 — 3건은 `refresh_by`로 표시 |
| 최종 승인 대상 없이 게시 요청됨 | 해당 없음 — 게시하지 않았음 |
