# Approval boundaries

## Safe default

Skills may inspect permitted inputs, analyze, validate, and create local drafts. They do not gain authority to act outside the workspace.

## Human approval required

- send email or direct message;
- submit a form;
- publish or comment publicly;
- spend budget or promise an incentive;
- change billing, refund, or account state;
- delete customer or production data;
- deploy;
- expose internal or restricted evidence;
- approve evidence strength;
- approve a growth decision or target.

## Required approval record

Record:

- approver;
- target;
- action;
- timestamp;
- artifact version;
- constraints;
- rollback or stop condition when applicable.

Approval for a draft does not authorize later variants or a different target.

## Failure handling

When authority or evidence is missing:

1. preserve safe partial work;
2. record the blocker;
3. state what can still be done locally;
4. ask for the smallest missing decision;
5. resume from the recorded state.
