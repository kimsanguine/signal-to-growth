# Kakao Channel chatbot setup (Open Builder)

Use this before any verification step when the Kakao Channel chatbot does not
exist yet, or when a skill server is not yet registered. This creates the
channel and bot; it does not prove the connection works. Move to the
verification workflow in `SKILL.md` and the exercise in
`fixtures/public-dummy/providers/kakao-openbuilder/scenario-notes.md`
immediately after.

Kakao's console changes over time. Fetch each URL below before giving exact
click-by-click instructions, and tell the user when a screen no longer matches
what is described here rather than guessing.

## Setup checklist

1. **Business Channel.** Confirm the user already has admin rights on a Kakao
   Channel at [카카오톡 채널 관리자센터](https://center-pf.kakao.com/). A
   channel is a prerequisite, not the chatbot itself.
2. **Chatbot Admin Center account.** Sign up per the
   [준비 가이드](https://kakaobusiness.gitbook.io/main/tool/chatbot/start/prepare),
   then create one bot.
3. **Development channel.** Connect a development channel under `설정 → 챗봇
   관리` before touching a production channel. A production channel requires
   the bot to have been deployed at least once — do not promise it can be
   connected before that.
4. **Blocks.** Design the block that should receive the inquiry.
   - Prefer a **fallback block** over a keyword-matched block when the goal is
     "every message the customer sends should reach the skill server,"
     because a keyword block only fires on configured utterances and silently
     misses everything else. This was the actual root cause of an inquiry
     going unanswered in past runs: a channel that looked "connected" because
     a welcome/FAQ block worked, while real inquiries fell outside every
     configured keyword and got a generic FAQ reply instead of reaching the
     skill.
   - A block with parameter extraction is unnecessary for this connector —
     connect the skill directly to a block action.
5. **Skill registration.** Under the bot's `스킬 → 생성`:
   - Name it descriptively (e.g. `<product>-cs-intake`).
   - URL: the real deployed skill-server endpoint. Localhost does not work —
     Kakao's servers must reach it over public HTTPS.
   - Custom header: `x-api-key`. **This is not a Kakao Developers app key or
     REST API key** — it is an arbitrary shared secret the connector owner
     invents and sets identically on both sides (the skill server's
     environment and this Kakao skill config). Confusing it with a Kakao
     Developers key was the single most common setup mistake observed across
     runs of this exercise.
   - Do not ask the user to paste the secret value into chat or a document.
     Have them set it directly in both places (hosting secret store, Kakao
     skill config) and confirm only that it is set, per
     `references/approval-boundaries.md`.
6. **Connect block to skill.** Attach the skill to the fallback block's
   action, not to a parameter-form action.
7. **Deploy the bot.** A skill or block change does not take effect until the
   bot is deployed again.
8. **Skill test (Admin Center).** Use the built-in skill-test feature to send
   a synthetic utterance and inspect the request/response preview before
   testing on a real channel. This exercises the same 5-second synchronous
   `version=2.0` JSON contract as the fixtures in
   `fixtures/public-dummy/providers/kakao-openbuilder/`.

## What "connected" does not mean

- Deploying the bot or passing the skill test in isolation is not verification.
  Confirm the round trip by reading it back from wherever the connector writes
  it (the actual stored `cs-events.jsonl`/database record), not from the
  Admin Center's own "success" indicator alone.
- A working welcome/FAQ block does not prove the fallback path works. Send an
  utterance that matches no configured keyword and confirm it still reaches
  the skill server.
- A green deploy or a 200 response from the skill server is a tool signal, not
  proof of the full path. Read the actual normalized event back before
  reporting the channel as connected, per this skill's own stop condition:
  "Do not claim that a channel is connected, live, or operational from
  documentation, fixture, build, or credential issuance alone."

## Common failure modes observed

- **Secret rotated without re-verification.** After changing a hosting
  provider's "sensitive" environment variable, the new value cannot always be
  read back through the hosting CLI/API even by the owner — that is by
  design, not a bug. Verify with a live request immediately after rotating,
  rather than trusting that the write succeeded.
- **Response budget exceeded.** The 5-second deadline covers the full skill
  round trip (Kakao-to-server network time, TLS, body parsing, verification,
  normalization, and storage), not just the storage write. A design that
  budgets the full 5 seconds for one write leaves no margin for the rest.
- **Treating a deploy as done.** "Deployed" and "verified" are different
  claims. Confirm by observing the real target (server logs and the stored
  record), not by re-reading the deploy tool's own success message.

## Official sources

- [챗봇 관리자센터 준비 가이드](https://kakaobusiness.gitbook.io/main/tool/chatbot/start/prepare)
- [봇 설정과 개발 채널](https://kakaobusiness.gitbook.io/main/tool/chatbot/main_notions/bot_setting)
- [스킬 만들기](https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/make_skill)
- [SkillPayload와 응답 JSON](https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/answer_json_format)
- [Request payload와 X-Request-Id](https://kakaobusiness.gitbook.io/main/tool/chatbot/main_notions/setting_parameter)

Recheck each source's checked date in `references/providers-kr.md` before
relying on details not repeated here.
