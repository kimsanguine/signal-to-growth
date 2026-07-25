---
name: run-switch-interview
description: "Design and guide a behavior-based Switch Interview around a real past decision, timeline, and Four Forces. Use when preparing or conducting customer discovery, JTBD interviews, 전환 인터뷰, or correcting leading and hypothetical questions."
---

# Run Switch Interview

Reconstruct what happened before, during, and after a real choice. Prefer remembered events, actions, trade-offs, and context over feature opinions.

## Inputs

Require:

- participant role and relevant behavior;
- research question;
- recording and note-taking consent state;
- known product relationship;
- session duration and interviewer constraints.

## Workflow

1. Confirm consent and describe how notes or recordings will be used.
2. Anchor the conversation in the most recent real event.
3. Reconstruct the timeline: first thought, passive looking, active looking, decision, purchase or commitment, and consumption.
4. Explore Push, Pull, Anxiety, and Habit with neutral follow-ups.
5. Ask what the participant did before, who else influenced the decision, and what evidence they used.
6. Record contradictions, missing dates, and memory uncertainty rather than resolving them silently.
7. Close by checking the timeline with the participant. Do not ask for a feature wishlist as the main evidence.

## Question rules

- Ask one question at a time.
- Prefer “What happened next?” and “Can you take me back to that day?”
- Replace future intention with the most similar past behavior.
- Replace solution-leading wording with problem context and coping behavior.
- Separate B2B buyer, user, approver, and procurement influence.

## Boundaries

- Let the model propose neutral questions and follow-up probes.
- Use the question linter to find configured leading, hypothetical, compound, and solution-first patterns.
- Require a human interviewer to handle rapport, consent, sensitive context, and follow-up judgment.
- Never fabricate a participant answer or fill a timeline gap with a likely story.

## Outputs

Create:

- `interview-guide.md`
- `timeline-notes.md`
- `follow-up-questions.md`

Read [references/output-contract.md](references/output-contract.md) before writing them.

## Stop conditions

Stop when consent is unclear, the participant is under pressure, sensitive information exceeds the agreed scope, or the session has no identifiable past event.

## Verification

Run:

```bash
python3 scripts/stg.py lint-questions interview-guide.md
python3 scripts/stg.py scan-privacy timeline-notes.md
```

Treat linter results as review prompts, not automatic evidence-quality judgments.
