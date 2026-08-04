# Kakao dead-letter 조회·재처리 runbook

## Scope

이 문서는 `public.kakao_cs_dead_letters_test` 한 테이블에만 적용됩니다.
합성(synthetic) Kakao 테스트 이벤트 중 **Supabase가 영구적으로 거부한 것**이
여기 저장됩니다. 프로덕션 고객 대화용으로 승인된 테이블이 아닙니다.

보존·삭제 절차는 [retention runbook](kakao-test-retention.md)을 따릅니다.
이 문서는 조회와 재처리만 다룹니다.

## 이 테이블에 무엇이 들어오는가

`kakao_skill_server`는 저장 실패를 두 갈래로 나눕니다
(`src/signal_growth/kakao_skill_server.py` 모듈 docstring 참조).

| 실패 성격 | 예외 | HTTP 응답 | dead-letter 행 |
|---|---|---|---|
| contract (영구 거부) | `SupabaseWriteRejected` 등 `ValueError` 계열 | 200 (dead-letter 저장 성공 시) | **기록됨** |
| availability (일시 장애) | `TransportError` | 503 | 기록 안 됨 |
| unknown (미분류) | 그 외 예외 | 503 | 기록 안 됨 |

HTTP 상태 분류는 `supabase_sink._classify_status`가 담당합니다.
`>= 500`과 `408·425·429`는 availability, 나머지 4xx는 contract입니다.

따라서 **정상 운영 중이라면 이 테이블에는 `failure_class = 'contract'` 행만
존재해야 합니다.** `availability`나 `unknown` 행이 보이면 그것 자체가 이상
신호입니다(아래 에스컬레이션 참조).

dead-letter 저장까지 실패하면 행은 생기지 않고 서버가 503으로 실패를 닫습니다.
그 경우 증거는 구조화 로그(`outcome="dropped_without_storage"`)에만 남습니다.

## 접근 권한

마이그레이션 `20260804090000_create_kakao_cs_dead_letters_test.sql` 기준:

- `anon`·`authenticated`는 grant가 회수되어 있고 RLS 정책도 `false`입니다.
  브라우저 키로는 조회할 수 없습니다.
- `service_role`에는 `insert, select`만 부여됩니다. **`update`·`delete`는
  부여되지 않았습니다.** 서비스 키로는 행을 지우거나 고칠 수 없습니다.
- 따라서 삭제·수정이 필요한 작업은 Supabase Dashboard SQL Editor에서
  사람이 실행해야 합니다. 이는 의도된 제약입니다.

## 조회

### 1) 최근 dead-letter 요약

```sql
select failure_class, error_type, status_code, count(*), max(created_at) as last_seen
from public.kakao_cs_dead_letters_test
group by failure_class, error_type, status_code
order by last_seen desc;
```

`failure_class, created_at` 인덱스가 있으므로 class 기준 조회는 저렴합니다.

### 2) 특정 시간대 목록

`canonical_event`는 선택하지 마세요. 리댁션된 값이지만 익명화가 아니므로
운영 조회 기본에서 제외합니다(로그 정책과 동일한 이유).

```sql
select event_id, provider_event_id, failure_class, error_type, status_code,
       received_at, created_at, expires_at
from public.kakao_cs_dead_letters_test
where created_at >= now() - interval '24 hours'
order by created_at desc;
```

### 3) 단건 상세 (재처리 판단 시에만)

```sql
select event_id, failure_class, error_type, status_code, approval_ref, canonical_event
from public.kakao_cs_dead_letters_test
where event_id = 'CSE-...';
```

`error_type`은 예외 **클래스명만** 저장됩니다. 예외 메시지는 페이로드나
키가 섞일 수 있어 저장하지 않습니다. 원인 상세가 더 필요하면 같은 시각의
구조화 로그(`failure_class`, `status_code`, `outcome`)를 함께 봅니다.

## failure_class별 대응

### `contract` — 기본 경로

의미: 같은 요청을 그대로 재시도하면 영원히 실패합니다. 재시도가 아니라
**원인 수정**이 필요합니다. `status_code`로 갈라집니다.

| status_code | 흔한 원인 | 조치 |
|---|---|---|
| 400·422 | canonical event가 테이블 제약(체크·타입·NOT NULL) 위반 | 정규화/스키마 쪽 결함. 코드 수정 없이 재처리 금지 |
| 401·403 | 서비스 키 무효·권한 회수·RLS 변경 | 자격증명·grant 확인. 키 교체는 사람 승인 필요 |
| 404 | 테이블명·프로젝트 URL 오설정 | `SUPABASE_KAKAO_EVENTS_TABLE` 등 환경변수 확인 |
| 409 | 제약 충돌 | 이벤트 테이블은 `on_conflict=event_id`로 중복을 무시하므로 드묾. 발생 시 스키마 변경 이력 확인 |

status_code가 `null`인 contract 행은 HTTP 거부가 아니라 코드가 던진
`ValueError`(예: approval_ref 형식 위반)입니다. 설정 결함으로 다룹니다.

### `availability` — 여기 있으면 안 되는 값

availability 실패는 저장하지 않고 503으로 닫는 설계입니다. 이 값의 행이
있다면 (a) 분류 로직이 바뀌었거나 (b) 다른 경로가 이 테이블에 쓰고 있다는
뜻입니다. 재처리 대상이 아니라 **조사 대상**입니다.

### `unknown`

동일하게 조사 대상입니다. 미분류 실패는 재시도가 무의미하다는 증거가 없어
availability처럼 다루도록 되어 있고, 마찬가지로 저장 경로가 없습니다.

## 재처리 판단 기준

**자동 재처리(replay) 도구는 구현되어 있지 않습니다.** 이 저장소에는
dead-letter 행을 이벤트 테이블로 되돌리는 코드가 없습니다. 재처리는 사람이
판단하고 사람이 실행하는 절차입니다.

재처리 전 네 가지를 모두 만족해야 합니다.

1. **원인이 수정되었다.** 코드·스키마·설정 중 무엇을 고쳤는지 특정할 수
   있어야 합니다. "다시 해보면 될 것 같다"는 근거가 아닙니다.
2. **수정이 실제로 반영되었다.** 배포 성공 신호가 아니라, 새 이벤트가
   이벤트 테이블에 정상 적재되는 것을 관측했습니다.
3. **대상 행이 특정되었다.** `event_id` 목록과 건수를 미리 적어둡니다.
4. **승인 근거가 있다.** `approval_ref`를 기록합니다.

재처리 자체는 `canonical_event`를 이벤트 테이블에 다시 insert하는 것입니다.
이벤트 테이블은 `on_conflict=event_id`(`resolution=ignore-duplicates`)로
동작하므로 같은 이벤트를 두 번 넣어도 중복 행이 생기지 않습니다.

```sql
-- Dashboard SQL Editor에서 사람이 실행. 대상 event_id를 명시적으로 나열합니다.
insert into public.kakao_cs_events_test
  (event_id, provider, provider_event_id, received_at, approval_ref, canonical_event)
select d.event_id, d.provider, d.provider_event_id, d.received_at,
       d.approval_ref, d.canonical_event
from public.kakao_cs_dead_letters_test d
where d.event_id in ('CSE-...')
on conflict (event_id) do nothing;
```

컬럼 목록은 `20260726023000_create_kakao_cs_events_test.sql`과
`20260726023030_add_kakao_event_governance.sql` 기준입니다. `provider`·
`provider_event_id`·`received_at`은 NOT NULL이라 생략할 수 없습니다.
`created_at`·`expires_at`은 기본값이 채우므로, 재처리된 행은 원래 수신
시각이 아니라 **재처리 시점 기준으로 7일 보존 창이 새로 시작**됩니다.

재처리 후:

- 이벤트 테이블에서 해당 `event_id`가 조회되는지 직접 확인합니다.
- dead-letter 행은 **삭제하지 않습니다.** 실패 이력은 retention 정책의
  `expires_at`에 따라 만료되도록 둡니다. 조기 삭제가 필요하면 retention
  runbook의 승인 절차를 따릅니다.

### 재처리하지 않는 경우

- 원인을 특정하지 못했다 → 재처리 금지. 같은 실패를 반복 생성할 뿐입니다.
- `failure_class`가 `availability`·`unknown`이다 → 재처리가 아니라 조사.
- 400·422인데 정규화 코드가 그대로다 → 재처리해도 같은 제약에 걸립니다.

## 에스컬레이션

다음 중 하나라도 해당하면 혼자 처리하지 말고 사람에게 알립니다.

1. **`availability` 또는 `unknown` 행이 존재한다.** 설계상 생길 수 없는
   행이므로 분류 로직이나 미승인 쓰기 경로를 의심합니다.
2. **`dropped_without_storage`가 로그에 있다.** dead-letter 저장까지 실패한
   상태로, 이벤트가 어디에도 남지 않았을 수 있습니다.
3. **401·403이 반복된다.** 자격증명·권한 문제이며 키 교체는 되돌리기 어려운
   작업이라 사람 승인이 필요합니다.
4. **단시간에 행이 급증한다.** 개별 이벤트 결함이 아니라 스키마·배포 회귀일
   가능성이 큽니다.
5. **테이블 권한·RLS를 바꿔야 한다고 판단된다.** 이 저장소의 승인 경계상
   스키마·권한 변경은 자동 실행 대상이 아닙니다.

에스컬레이션 시 함께 전달할 것: 조회 요약 결과(1번 쿼리), 대상 `event_id`
건수, 관측한 `status_code`·`error_type`, 최근 배포·마이그레이션 이력.
`canonical_event` 본문은 기본적으로 포함하지 않습니다.
