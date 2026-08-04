# Output contract

## `visual-prompts.md`

For each prompt include:

- the prompt ID and the single claim ID it depicts;
- the claim state carried from the ledger;
- the surface and aspect ratio it is intended for;
- the prompt text itself, describing only what the claim asserts;
- the on-screen text, with any limitation that must stay visible;
- what the image must not show, including invented data, screenshots, logos, faces, and testimonials;
- the person who must approve the visual claim before a render.

A prompt with no claim ID is not an output of this skill.

## `video-script.md`

Structure the script as beats. For each beat include:

- the beat number and its purpose;
- the claim IDs spoken or shown in it;
- narration wording and on-screen text kept separate;
- the limitation or counterevidence the beat must not omit;
- the intended runtime, marked as an estimate.

Keep the brief's `question` as the opening and the brief's `cta` as the close. When `cta` is null, close without one and say why.

## `fanout-coverage.md`

Trace the fanout back to the brief:

- the `brief_id` and the draft this fanout reuses;
- each ledger claim marked reused, skipped, or ineligible, with the reason;
- claims held back because they are not public or not approved;
- surfaces requested in `planned_outputs` that were not produced;
- the approvals a person must give before any render or publication.

Skipping a claim is a decision to record, not a gap to hide.

## Completion gate

Every prompt and beat names an existing claim ID, no claim state was upgraded, every stated limitation survived the format change, and no image, video, or published asset was created.
