# Korean CS provider setup checklist

- 확인일: 2026-07-26
- 목적: `Signal to Growth`의 계정 없는 P0 실습 이후, 승인된 test account로 P1 read-only 왕복을 검증한다.
- 기본 경계: 이 문서는 계정과 채널을 준비하는 절차다. 메시지 자동 발송, 운영 채널 변경, 실제 고객 데이터 수집을 승인하지 않는다.

## 1. 권장 경로

강의의 가장 짧은 실제 검증 경로는 다음과 같다.

```text
Kakao Business Channel
  → Kakao Chatbot Admin Center bot
  → Kakao i Open Builder skill request
  → public HTTPS skill server
  → verify → normalize → redact → dedupe
  → fixed safe skill response
  → Signal to Growth canonical event
```

이 경로는 `Kakao Channel chatbot E2E`다. 상담톡, 알림톡, native
Channel 1:1 상담 이력 API가 아니다. 공개 문서로 요청·응답 계약을 확인할
수 있고 별도 Channel Talk Open API key 없이 시험할 수 있어 강의 본편에
적합하다.

Channel Talk adapter는 제품에 유지한다. 다만 실제 Open API key가 필요한
실습은 유료 plan 전제이므로 강의에서는 확장 구조만 소개한다.

## 2. 지금 계정 없이 할 수 있는 것

다음은 사용자가 준비할 항목이 없다.

- Kakao Open Builder·Naver TalkTalk·Channel Talk·Kakao 상태 public dummy fixture 실행
- event 인증 수준 표시
- canonical event 정규화
- PII redaction
- deterministic event ID와 중복 제거
- high-risk route와 reply draft
- delivery state transition 검증
- Claude Code·Codex의 공통 artifact 정적 검증

실제 credential을 만들기 전에 이 단계가 모두 통과해야 한다.

## 3. Kakao Channel chatbot E2E 준비

### 3.1 계정과 bot

1. [카카오톡 채널 관리자센터](https://center-pf.kakao.com/)에서 만든 채널의 마스터 권한을 확인한다.
2. [챗봇 관리자센터 준비 가이드](https://kakaobusiness.gitbook.io/main/tool/chatbot/start/prepare)에 따라 회원 가입한다.
3. 카카오톡 채널 챗봇 bot을 하나 만든다.
4. 실제 운영 고객과 분리할 수 있으면 개발 채널을 준비한다.
5. `설정 → 챗봇 관리`에서 개발 채널을 연결한다. 운영 채널은 bot을 한 번 이상 배포해야 연결할 수 있다.

비즈니스 채널 인증과 개발 채널 생성 가능 여부는 현재 계정 화면에서
확인한다. 채널을 만들었다는 사실만으로 bot 연결과 E2E가 완료된 것은
아니다.

### 3.2 Skill server

챗봇 관리자센터의 bot에서 `스킬 → 생성`으로 이동해 다음을 설정한다.

- 스킬명: `signal-to-growth-test`
- URL 또는 Test URL: 승인된 public HTTPS endpoint
- 헤더: `x-api-key`
- 테스트 헤더: 운영 값과 분리한 test secret

카카오는 skill request를 `HTTP POST` JSON으로 보내며 local URL은 사용할
수 없다. skill server는 5초 안에 `version=2.0` JSON 응답을 반환해야 한다.
`X-Request-Id`는 canonical event identity에 사용한다.

secret 값은 password manager 또는 hosting secret store에 저장한다. repository,
교안, 이슈, 채팅에는 값 대신 `secret://kakao-openbuilder/test/api-key` 같은
reference만 남긴다.

공식 문서:

- [봇 설정과 개발 채널](https://kakaobusiness.gitbook.io/main/tool/chatbot/main_notions/bot_setting)
- [스킬 만들기](https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/make_skill)
- [SkillPayload와 응답 JSON](https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/answer_json_format)
- [Request payload와 X-Request-Id](https://kakaobusiness.gitbook.io/main/tool/chatbot/main_notions/setting_parameter)

### 3.3 Block과 E2E

1. 문의를 받을 시나리오와 block을 만든다.
2. block의 동작에 `signal-to-growth-test` skill을 연결한다.
3. skill 테스트에서 synthetic 발화를 보내 요청과 응답 미리보기를 확인한다.
4. 개발 채널에서 같은 발화를 두 번 보내 각 요청의 `X-Request-Id`가 다른지 확인한다.
5. endpoint에서 정규화된 두 event와 fixed acknowledgement를 확인한다.
6. 고객 identifier·발화 원문·secret이 일반 log에 남지 않았는지 확인한다.

이 단계의 응답은 고정된 test acknowledgement만 허용한다. LLM 생성 답변,
환불·가격·계정 약속, 외부 API 발송은 포함하지 않는다.

## 4. Channel Talk 선택형 준비

Channel Talk adapter와 다음 capability는 제품에 유지한다.

- message webhook 정규화
- UserChat/message read-only backfill
- webhook/backfill dedupe
- reply, assignment, tag mutation 차단

다만 2026-07-26 실제 관리자 화면에서 Open API key 발급에 유료 결제가
필요한 것으로 확인됐다. 따라서:

- 강의 본편 실습과 수강생 준비물에서 제외한다.
- architecture와 paid connector 확장 사례로만 소개한다.
- 이미 유료 plan과 test 채널이 있는 팀만 선택형 검증을 진행한다.
- 가격과 entitlement는 변경될 수 있으므로 실제 적용 시 다시 확인한다.

공식 문서:

- [Channel Talk Open API](https://developers.channel.io/en/categories/Open-API-060776bd)
- [Webhook setup](https://developers.channel.io/en/articles/Getting-started-f2a30b58)

## 5. Naver TalkTalk 선택형 test account

강의의 P0는 fixture만으로 완료된다. 실제 Naver event를 확인하려면 다음을 추가로 진행한다.

1. [Naver TalkTalk 파트너센터](https://partner.talk.naver.com/)에 로그인한다.
2. `내계정관리 → 새로운 톡톡 계정 만들기`를 선택한다.
3. test 목적이면 개인 계정을 선택하고 프로필명 앞에 `[테스트]`를 추가한다.
4. 검수 완료 후 `개발자도구 → 챗봇API 설정`에서 신청과 약관 동의를 진행한다.
5. 이벤트를 받을 HTTPS URL을 Webhook에 등록한다.
6. 필요한 inbound event만 선택한다.

read-only inbound 검증에는 Send API의 `Authorization` key가 필요하지 않다. 답변·발송을 구현하는 P2에서만 별도 발급한다.

공식 문서:

- [Naver TalkTalk Chat Bot API V1](https://github.com/navertalk/chatbot-api)

## 6. 카카오 발송 상태 adapter 선택형 준비

알림톡 전달 상태나 simulator를 교안에 포함할 때만 공식 딜러 한 곳을 선택한다.

선택 우선순위:

1. 현재 회사가 이미 계약한 provider
2. 실제 발송 없는 Bizppurio simulator
3. SOLAPI webhook test
4. NHN Cloud polling

Bizppurio 실제 API를 선택하면 별도로 확인할 항목:

- 검수용 계정과 운영 계정 분리
- API 호출 고정 IP 등록
- Kakao sender profile
- 승인된 template
- webhook 또는 polling 결과 수신 방식

[Bizppurio simulator](https://bizppurio.github.io/sandbox/)는 실제 메시지를 보내지 않으므로 강의용 상태 흐름 확인에 사용할 수 있다. simulator 화면의 예시 전화번호나 예시 token을 실제 credential로 취급하지 않는다.

## 7. 사용자에게서 필요한 회신

다음 정보만 회신한다. secret은 보내지 않는다.

```text
1. 기존 CS 도구:
2. Kakao Business Channel의 비즈니스 인증 상태:
3. 챗봇 관리자센터 가입과 bot 생성 여부:
4. 개발 채널 생성·연결 가능 여부:
5. public HTTPS endpoint 배포 승인 여부와 선호 hosting:
6. Channel Talk 유료 Open API 이용 여부:
7. Naver TalkTalk test account 생성 여부:
8. 알림톡 상태 demo에 사용할 기존 공식 딜러:
```

보내지 말아야 할 것:

- Access Key와 Access Secret
- Kakao skill `x-api-key`
- webhook token·private callback URL
- Kakao 관리자 전화번호와 인증번호
- 사업자등록증
- 고객 전화번호·상담 원문
- provider account ID

## 8. P1 완료 증거

계정 생성만으로 연동 완료라고 판단하지 않는다.

1. 승인된 Kakao development channel과 bot 연결
2. Chatbot Admin Center의 skill test 성공
3. 개발 채널에서 synthetic 문의 1건
4. `X-Request-Id`를 가진 request 수신
5. canonical event 정규화와 fixed `version=2.0` 응답
6. 같은 발화 2회가 서로 다른 request identity로 기록됨
7. 일반 log에 사용자 identifier·발화 원문·secret이 없음
8. ConsultTalk·AlimTalk·외부 Send API 호출 0건

이 여덟 항목이 확인돼야 `kakao chatbot test connected`와 `inbound verified`
상태를 기록한다. Channel Talk는 별도의 선택형 검증 상태로 관리한다.
