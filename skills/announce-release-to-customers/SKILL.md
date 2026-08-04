---
name: announce-release-to-customers
description: "Turn a deterministic change list into a customer-language release note draft and link each change to the customer signal or growth decision it answers. Use when a release has shipped and needs 릴리스 노트, 출시 안내, or 변경 안내 written from a git log, CHANGELOG, or human-provided list. Do not use for inventing a change list, deciding what to build, or sending the announcement to customers."
---

# Announce Release to Customers

Describe a release that already happened, in words a customer can act on, with
each item traceable both backwards to the commit that produced it and forwards
to the customer signal it answers.

Two failure modes shape this skill. A release note written from a model's
impression of a codebase announces work nobody shipped. A release note written
only from commit subjects tells customers about refactors they cannot see. The
change list is therefore an input, and the translation is the work.

## Inputs

Require:

- the release reference: a tag, a version, or a commit range;
- a change list obtained deterministically, each item carrying its own
  reference — a commit hash, a merge request, or a CHANGELOG heading;
- the artifact directory holding `signals.jsonl` and `decisions.jsonl`, when a
  run exists to link against;
- the intended audience and channel, as a statement of intent only.

Obtain the change list by one of three means and record which one was used:

```bash
git log --no-merges --pretty=format:'%h %s' <previous-tag>..<release-tag>
```

reading the release section of `CHANGELOG.md`, or accepting a list the person
provides. There is no fourth means. If none is available, stop and say so
rather than reconstructing the release from the working tree.

## Workflow

1. Record the release reference and how the change list was obtained.
2. Copy each change into `internal_summary` verbatim, keeping the team's own
   words as the source text a reviewer can compare the translation against.
3. Translate each change into customer language: what the customer can now do,
   or what stopped going wrong. Do not translate a change whose effect on the
   customer cannot be stated — mark it internal-only instead and leave it out
   of the customer summary.
4. Read `signals.jsonl` and `decisions.jsonl` and propose, per change, the
   signal or decision it answers.
5. Type every link with `link_state`. Use `human_confirmed` only when the
   linked decision or signal itself names this change, or a person confirms the
   link in a later user turn. Use `model_inferred` when the link comes from
   reading both records and judging them related. Use `none` when the change
   answers no recorded signal, and list it in `unlinked-changes.md`.
6. Write the release-level `internal_summary` from the change list and the
   release-level `customer_summary` as its translation.
7. Keep `status` at `draft` or `awaiting_human_review`. A person moves it to
   `approved` in a later user turn.
8. Leave `publication_action_id` null unless a person has recorded a publishing
   action. Sending is an external write and belongs to that action's approval,
   not to this note.
9. Append the note. Correct a published note by appending a new one that
   supersedes it, never by editing the earlier record.

## Boundaries

- This skill does not invent changes and does not send anything. Every entry
  comes from a git log, a CHANGELOG, or a person, and the draft stays a file.
- Let the model translate developer language into customer language and propose
  which signal a change answers.
- Use deterministic checks for the change list, IDs, reference resolution,
  status transitions, and append-only history.
- Require a person to approve the wording, and require the existing external
  write boundary for any send.
- Do not treat a `model_inferred` link as evidence that the release answered a
  customer need. It is a hypothesis for a reviewer to accept or reject.
- Do not describe a change as an outcome. Shipping a change is not evidence
  that it worked; that judgement belongs to the metric and outcome records.
- Do not restate an unreleased roadmap item, a planned feature, or a decision
  that has not shipped.
- Do not write pricing, refund, contract, or other sensitive-topic wording from
  scratch. `policies/default-policy.json` restricts those topics to
  pre-approved templates, so route them to a person instead.

## Outputs

Create or append:

- `release-notes.jsonl`
- `customer-announcement-draft.md`
- `unlinked-changes.md`

Read [references/output-contract.md](references/output-contract.md) before writing them.

Add every new record to `release-notes.jsonl` with the `append-record` command,
never by writing or editing the file:

```bash
python3 scripts/stg.py append-record <artifact-directory>/release-notes.jsonl '<json-object>'
```

It takes an exclusive lock and hash-chains each line to the one before it, so a
later reader can tell whether an announcement was rewritten after the fact. In a
packaged runtime the same command is `signal-to-growth append-record`.

## Stop conditions

Stop when no deterministic change list is available, when a change carries no
reference, when a linked signal or decision ID does not resolve, when the
customer effect of a change cannot be stated without guessing, or when the
request is to send rather than to draft.

## Verification

Keep `signals.jsonl`, `decisions.jsonl`, and `release-notes.jsonl` together,
then run:

```bash
python3 scripts/stg.py validate-artifacts artifacts/
```

Report the change count, how many changes carry a `human_confirmed` link, how
many carry a `model_inferred` link, and how many carry none. A note in which
every change is linked deserves more suspicion than one that reports gaps.
