---
name: plan-customer-reach
description: "Plan consent-aware customer research recruitment and draft-only outreach without sending messages. Use when defining interview segments, recruiting participants, selecting channels, or preparing 고객 인터뷰 대상자·모집·컨택 초안."
---

# Plan Customer Reach

Create a research recruitment plan that separates who to learn from, why their experience matters, and what requires human approval.

## Inputs

Require:

- a research question;
- candidate segment hypotheses;
- inclusion and exclusion criteria;
- channel and capacity constraints;
- consent, privacy, incentive, and retention policies.

If the research question asks which feature people want, restate it around a past behavior or unresolved decision before planning recruitment.

## Workflow

1. Define the decision the research will inform.
2. Describe candidate segments by recent behavior, context, and role. Do not define a segment only by demographics.
3. Separate B2B buyer, user, approver, and administrator roles when they can experience different jobs.
4. State inclusion, exclusion, and sampling-bias risks.
5. Choose channels based on where the target behavior is observable.
6. Draft a short invitation that states purpose, time, incentive, data use, and voluntary participation.
7. Create a recruitment log with status, consent state, and no unnecessary personal data.
8. Stop at drafts. Ask for explicit approval before any email, direct message, form submission, or public post.

## Boundaries

- Let the model propose segments, channels, and wording.
- Use deterministic checks for required consent fields, duplicated candidates, private-data patterns, and `external_send=false`.
- Require a person to approve targets, incentives, channel rules, and every external send.
- Do not invent response-rate benchmarks or treat a participant count as universal evidence sufficiency.
- Do not scrape or enrich private contact information.

## Outputs

Create:

- `reach-plan.json`
- `contact-drafts.md`
- `recruitment-log.csv`

Read [references/output-contract.md](references/output-contract.md) before writing them.

## Stop conditions

Stop and report the missing decision when:

- consent or retention policy is absent;
- the segment cannot be connected to the research question;
- recruitment depends on restricted data;
- an invitation makes a product or payment promise;
- the user asks to send without naming targets and approving the final draft.

## Verification

Run:

```bash
python3 scripts/stg.py scan-privacy contact-drafts.md
```

Confirm that every external action remains a draft and that observed facts, assumptions, and recommendations are labeled separately.
