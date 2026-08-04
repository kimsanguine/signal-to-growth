# Output contract

## `release-notes.jsonl`

Follow `contracts/release-note.schema.json`. Append one immutable record per
release note. A correction is a new record whose `supersedes` names the earlier
`release_id`, never an edit to the earlier line.

Require `release_ref`, at least one change, the release-level
`internal_summary`, and the append chain fields written by `append-record`.

Every change item requires `change_ref` and `change_source`. `change_source` is
one of `human_provided`, `git_log`, or `changelog` — there is no value for a
change a model produced without a source, because such a change may not be
recorded at all.

`internal_summary` on a change is the team's own wording, kept verbatim.
`customer_summary` is its translation and stays null until translated. The
release-level `customer_summary` may be null while `status` is `draft`, but
must be non-empty once `status` is `awaiting_human_review` or `approved`: a
person cannot review wording that is not there.

`link_state` types every link. `human_confirmed` requires that the linked
decision or signal names this change, or that a person confirmed the link in a
later user turn. `model_inferred` is a proposal a reviewer may reject.
`none` requires both `signal_ids` and `decision_ids` to be empty, and a change
carrying either must not be `none`.

`publication_action_id` is null unless a person recorded a publishing action in
`actions.jsonl`. When set it must name an action declared as an external write,
so the send is governed by the action and approval contracts. A release note
never records that a send happened.

## `customer-announcement-draft.md`

The customer-facing wording as a draft. Cover only changes that have a
`customer_summary`, state what the customer can now do or what stopped going
wrong, and keep the release reference visible so a reader can check the note
against the release. Mark the draft state and the fact that nothing has been
sent. Do not include internal-only changes, planned work, or performance claims
that no metric record supports.

## `unlinked-changes.md`

Changes whose `link_state` is `none`, plus changes held back as internal-only,
each with its `change_ref` and why it is unlinked. This file is the honest half
of the note: it shows how much of the release answered no recorded customer
signal. An empty file is a claim that every shipped change traced to a signal,
so state that explicitly rather than omitting the file.

## Completion gate

The note is a draft until a person approves the wording in a later user turn.
Approval of the wording is not authority to send. Sending requires an approved
external-write action under `contracts/action.schema.json` and a scoped human
record in `approvals.jsonl`.
