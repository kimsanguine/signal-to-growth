---
name: osmu-fanout
description: "Reuse one approved content brief and its claim ledger as visual prompts and a video script outline, keeping every frame traceable to a claim ID. Use when turning an existing evidence-backed draft into 이미지 프롬프트, 영상 스크립트, 카드뉴스 개요, or other 원소스 멀티유즈 재사용. Do not use for writing the original draft, rendering images or video, publishing to a channel, or describing a scene the claim ledger does not support."
---

# OSMU Fanout

One brief, several surfaces, one evidence trail. Fan out the content that already passed review instead of inventing a second version of the story for each channel.

## Inputs

Require:

- a `content-brief.json` that validates against `contracts/content-brief.schema.json`;
- the draft (`draft.md`) and claim ledger (`claim-ledger.jsonl`) written from that brief;
- the surfaces requested in the brief's `planned_outputs`;
- locale, brand, and legal constraints for on-screen text;
- the person who owns the topic and the render decision.

The brief is the input contract, not something this skill writes. If it does not exist or does not validate, stop and say so rather than reconstructing the topic from the draft.

## Workflow

1. Validate the brief and confirm the draft was written from the same `brief_id`.
2. Select the claims eligible for reuse: `public: true` with a named approver.
3. Give every visual prompt exactly one claim ID as its subject, and describe only what that claim already asserts.
4. Keep the claim state in the prompt. An `inferred` or `recommended` claim may not be drawn as an observed scene, a screenshot, a chart, or a customer photo.
5. Write the video script as beats, each beat naming the claim IDs it speaks and the on-screen text it needs.
6. Carry the brief's `limitations` into both surfaces. A sample of three does not become a trend line because the format changed.
7. Record which claims were reused, which were deliberately skipped, and why, so a reader can tell coverage from omission.
8. List what a person must approve before any render, and stop at text.

## Boundaries

- Let the model propose composition, framing, pacing, narration wording, and beat order.
- Use deterministic checks for brief validity, claim ID existence, claim state, and public eligibility.
- Require a person to approve visual claims, brand and legal wording, and the decision to render at all.
- **This skill does not create image or video files.** It produces prompts and a script outline; rendering happens later, outside this skill, with a tool the person chooses.
- Do not invent a scene, a metric on a chart, a screenshot, a logo, a face, or a testimonial that no claim supports.
- Do not upgrade a claim state to make a stronger picture, and do not drop a limitation because it is hard to fit on screen.
- Do not publish, schedule, or send anything.

## Outputs

Create:

- `visual-prompts.md`
- `video-script.md`
- `fanout-coverage.md`

Read [references/output-contract.md](references/output-contract.md) before writing them.

## Stop conditions

Stop when the brief is missing or invalid, the draft and the brief disagree on the topic, no claim is publicly eligible, a requested visual needs a claim the ledger does not hold, or a render or publish is requested without a person's approval in a later user turn.

## Verification

Run:

```bash
python3 scripts/stg.py validate-artifacts <artifact-directory>
python3 scripts/stg.py scan-privacy <artifact-directory>/visual-prompts.md
python3 scripts/stg.py scan-privacy <artifact-directory>/video-script.md
```

Require every prompt and every beat to name at least one claim ID that exists in `claim-ledger.jsonl`, and require no rendered file to have been created.
