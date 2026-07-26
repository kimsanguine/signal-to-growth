# Approval boundaries

Default every run to `dry-run`, `read-only`, and `draft-only`. Treat approval as a scoped artifact, not as a conversational implication.

## Safe default work

Allow without an external-write approval:

- inspect public official documentation;
- compare provider capabilities;
- validate public dummy fixtures offline;
- normalize, redact, deduplicate, and reconcile permitted offline inputs;
- query deterministic schemas and policy files;
- create connector artifacts and reply drafts with `external_write=false`;
- hand validated redacted events to `triage-customer-signals`;
- report unsupported, unconfirmed, and blocked capabilities.

Do not make a network call merely because the operation is described as read-only. Require an approved connection and user-authorized scope for real-account access.

## Connection approval

Require explicit approval before:

- reading a real provider account or test tenant;
- creating, changing, enabling, disabling, or rotating a webhook;
- storing or using a credential reference;
- changing IP allowlists, callback URLs, or secret paths;
- starting a backfill against real customer data;
- changing retention or processing-basis configuration;
- claiming a provider round trip as verified.

Require the connection approval to identify:

- approval ID and human approver;
- connection, provider, product, environment, and tenant;
- allowed read operations and data window;
- secret reference and owner, without the secret value;
- retention and processing-basis references;
- permitted test identities or synthetic-data boundary;
- start and expiry time;
- rollback or disable owner.

## External-write approval

Require a separate, current, scoped human approval before:

- replying or sending a message;
- handing a conversation to a counselor or reclaiming it;
- assigning a counselor or team;
- adding, removing, or replacing tags;
- closing, snoozing, blocking, or deleting a conversation or customer;
- registering or changing a template or sender profile;
- enabling SMS or LMS fallback;
- expanding recipients or using production customer data;
- making a billing, refund, account, deletion, or contractual action;
- publishing, deploying, or changing a production integration.

Bind approval to:

- the exact action and provider operation;
- environment, connection, conversation, and recipient or approved test cohort;
- content or immutable content hash;
- product, sender, template, and variables when applicable;
- purpose, risk class, and processing basis;
- allowed attempt count and fallback policy;
- approver and expiry;
- required status reconciliation.

Reject an approval that is broad, expired, missing a human approver, or does not cover the current content and target.

## Draft boundary

- Set every generated response to `status=draft`, `approval_id=null`, and `external_write=false`.
- Preserve the source event IDs and risk class.
- Expire stale drafts before they can be approved.
- Regenerate approval when content, target, template variables, session, or provider changes.
- Do not interpret “looks good,” an earlier approval, or a successful test as approval for a new external write.

## High-risk boundary

Route these classes to a human owner and keep sending disabled:

- safety or vulnerable-person risk;
- legal, privacy, or security incident;
- billing, refund, or payment dispute;
- account access or data deletion;
- threat, harassment, or abuse;
- contract, price, SLA, or remedy promise.

Allow the model to draft neutral internal notes. Do not let the model approve or execute the response.

## Kakao gates

### ConsultTalk

Require:

- the contracted dealer and counselor system;
- confirmed active session;
- verified conversation and customer references;
- allowed reply type;
- redacted approved content;
- scoped human approval.

Block the reply when session state is absent, inactive, expired, or derived from an AlimTalk event.

### AlimTalk

Require:

- contracted official dealer;
- approved sender profile;
- approved template and exact variables;
- informational message purpose;
- recipient basis and approved test or production scope;
- separate human approval for the send;
- callback or polling reconciliation plan.

Do not use an AlimTalk approval to authorize ConsultTalk, Brand Message, or fallback SMS.

### Channel 1:1 chat

Treat native operator chat as a separate surface. Require an explicit migration and access decision before routing it through a dealer-operated consultation system.

## Completion rule

Report:

- the artifacts created;
- the approval state;
- the network and account scope actually used;
- whether any external write occurred;
- the highest verification level reached;
- every blocked or unconfirmed capability.

Never report “sent,” “connected,” “live,” or “operational” from a draft, API response example, credential, local test, or deployment alone.
