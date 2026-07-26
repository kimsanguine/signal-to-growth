# Korean CS provider setup checklist

- 확인일: 2026-07-26
- 목적: `Signal to Growth`의 계정 없는 P0 실습 이후, 승인된 test account로 P1 read-only 왕복을 검증한다.
- 기본 경계: 이 문서는 계정과 채널을 준비하는 절차다. 메시지 자동 발송, 운영 채널 변경, 실제 고객 데이터 수집을 승인하지 않는다.

## 1. 권장 경로

가장 짧은 실제 검증 경로는 다음과 같다.

```text
Kakao Business Channel
  → Channel Talk의 Kakao 앱에서 상담톡 연결
  → Channel Talk UserChat
  → Channel Talk Open API와 webhook을 read-only로 수집
  → Signal to Growth canonical event
```

이 경로에서는 Channel Talk가 카카오 상담톡 연동 파트너 역할을 한다. 카카오 상담 원문을 가져오기 위해 별도의 NHN Cloud·SOLAPI·Bizppurio 발송 API를 동시에 계약할 필요가 없다.

이미 Happytalk 등 다른 상담톡 파트너를 사용 중이면 강의 때문에 이동하지 않는다. 기존 파트너를 유지하고 해당 provider adapter를 다음 구현 대상으로 선택한다.

## 2. 지금 계정 없이 할 수 있는 것

다음은 사용자가 준비할 항목이 없다.

- Naver TalkTalk·Channel Talk·Kakao 상태 public dummy fixture 실행
- event 인증 수준 표시
- canonical event 정규화
- PII redaction
- deterministic event ID와 중복 제거
- high-risk route와 reply draft
- delivery state transition 검증
- Claude Code·Codex의 공통 artifact 정적 검증

실제 credential을 만들기 전에 이 단계가 모두 통과해야 한다.

## 3. Channel Talk read-only 준비

### 3.1 계정과 권한

1. 기존 Channel Talk 채널을 사용하거나 test용 채널을 만든다.
2. 설정을 변경할 계정에 채널 관리자 권한이 있는지 확인한다.
3. 실제 고객 상담이 있는 운영 채널보다 별도 test 채널을 우선한다.

### 3.2 Open API credential

Channel Talk 관리자에서 다음 메뉴를 연다.

```text
채널 설정
→ 보안·개발
→ API 관리
→ 새 인증 키 만들기
```

생성 후 다음 두 값을 비밀 저장소에 보관한다.

- Access Key
- Access Secret

Access Secret은 생성 완료 후 다시 확인할 수 없을 수 있으므로 즉시 승인된 password manager나 secret manager에 저장한다.

금지:

- Git repository, issue, 메신저, 강의 화면에 값 복사
- `.env.example`에 실제 값 저장
- 운영 credential을 수강생에게 배포

Signal to Growth artifact에는 실제 값 대신 다음과 같은 reference만 기록한다.

```text
secret://channel-talk/test/access-key
secret://channel-talk/test/access-secret
```

공식 문서:

- [Channel Talk Open API](https://developers.channel.io/en/categories/Open-API-060776bd)
- [Webhook setup](https://developers.channel.io/en/articles/Getting-started-f2a30b58)

### 3.3 Webhook

```text
채널 설정
→ 보안·개발
→ Webhook 관리
→ Webhook 만들기
```

초기 설정:

- 이름: `signal-to-growth-test`
- URL: 별도로 준비한 HTTPS test endpoint
- User chat·event notification: ON
- Group chat notification: OFF
- 연락처 변경 notification: OFF

legacy webhook은 URL query의 token을 사용한다. App Function의 `X-Signature` HMAC과 같은 인증 방식으로 간주하지 않는다. token도 secret manager에 저장하고 repository에는 secret reference만 둔다.

## 4. Kakao 상담톡을 Channel Talk에 연결

### 4.1 Kakao Business Channel

1. [카카오톡 채널 관리자센터](https://center-pf.kakao.com/)에서 채널을 만들거나 기존 채널을 선택한다.
2. `관리 → 비즈니스 채널 신청`에서 비즈니스 인증을 신청한다.
3. 사업자등록증과 업종별 필수 서류를 준비한다.
4. 신청자는 채널 마스터여야 하며, 제출 서류와 관리자 정보가 일치해야 한다.
5. 채널 정보에 고객센터 연락처를 입력한다.
6. `프로필 → 프로필 설정 → 공개 설정`에서 채널 공개를 켠다.
7. 연동 전 카카오톡 채널 관리자센터의 진행 중인 1:1 상담을 마무리한다.

Channel Talk의 현재 안내는 비즈니스 인증 심사에 영업일 기준 3~5일이 걸릴 수 있다고 설명한다.

공식 가이드:

- [Channel Talk의 Kakao 비즈니스 인증 안내](https://docs.channel.io/help/ko/articles/%EB%B9%84%EC%A6%88%EB%8B%88%EC%8A%A4-%EC%9D%B8%EC%A6%9D-1b9e3eb9)
- [Kakao Channel 공식 안내](https://business.kakao.com/info/kakaotalkchannel/)

### 4.2 Channel Talk에서 상담톡 선택

Channel Talk에서 다음을 진행한다.

```text
채널 설정
→ 앱스토어
→ 카카오
→ 연동
```

입력·확인 항목:

- 카카오톡 채널 검색용 ID
- 사업자 category
- 사용할 기능: `상담톡`만 우선 ON
- 카카오 채널 관리자 휴대폰 번호
- 관리자 카카오톡으로 받은 인증번호

P1 read-only 검증에서는 알림톡과 브랜드 메시지 발송을 활성화하지 않는다.

주의:

- 상담톡은 동시에 여러 상담 파트너에 연결할 수 없다.
- Happytalk 등 다른 파트너에 이미 연결돼 있으면 해지·이관 전에 운영 영향과 진행 중 상담을 확인한다.
- 연결 후 새 카카오 상담은 카카오 채널 관리자센터가 아니라 Channel Talk에서 관리한다.
- Channel Talk 안내상 상담톡 연결 자체와 별개로, 상담원이 실제 답변하면 사용량 비용이 발생할 수 있다.

공식 가이드:

- [Channel Talk Kakao 연동](https://docs.channel.io/help/ko/articles/%EC%B9%B4%EC%B9%B4%EC%98%A4%ED%86%A1-%EC%97%B0%EB%8F%99%ED%95%98%EA%B8%B0-04f5721d)

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
2. Channel Talk test 채널 사용 가능 여부:
3. Kakao Business Channel 보유 여부와 인증 상태:
4. Kakao 상담톡이 현재 연결된 파트너:
5. Naver TalkTalk test account 생성 여부:
6. 알림톡 상태 demo에 사용할 기존 공식 딜러:
7. 외부 HTTPS test endpoint 준비 가능 여부:
```

보내지 말아야 할 것:

- Access Key와 Access Secret
- webhook token·private callback URL
- Kakao 관리자 전화번호와 인증번호
- 사업자등록증
- 고객 전화번호·상담 원문
- provider account ID

## 8. P1 완료 증거

계정 생성만으로 연동 완료라고 판단하지 않는다.

1. approved test connection의 healthcheck
2. test 고객 문의 1건
3. provider webhook의 수신 시각
4. 같은 conversation의 read-only API 조회
5. webhook과 backfill이 하나의 canonical event로 합쳐짐
6. 일반 log에 고객 원문·전화번호·secret이 없음
7. reply/send 호출 0건

이 일곱 항목이 확인돼야 `provider test connected`와 `inbound verified` 상태를 기록한다.
