---
name: log-decision
description: "Record a decision the user has ALREADY made into Jupi (the team's decision platform) as a finalized, searchable entry — the title, the chosen path, and the rationale. Use whenever a choice gets settled and the user wants it captured: \"log this decision\", \"record that we're going with X\", a validated trade-off, a meeting outcome, an ADR-style note, or the conclusion of a discussion you just had together. Lean toward offering it the moment a decision crystallizes in conversation — decisions captured in the flow of work are the ones that stay searchable later; the ones everyone \"will write up afterward\" evaporate. This finalizes the decision in one step, so use it only for calls that are actually made, not open questions (for those, use submit-decision)."
---

# Log decision

## What this is for

A decision that lives only in a Slack thread or someone's memory is a decision the team will re-litigate in three months. This skill writes a settled decision into Jupi as a **FINALIZED** record — so it surfaces later via `search-decisions` with its rationale attached. Think of it as the "commit message" for a choice: quick to write in the moment, valuable forever after.

Use it for calls that are _made_. If the question is still open and someone else needs to decide, that's `submit-decision`, not this.

## The shape of the underlying tools (read this — it explains the one odd step)

Jupi's model is: a decision is created in `STARTED` state, then `finalize` closes it by recording which option(s) won. Crucially, **there is no MCP tool to add candidate options to a decision** — options normally get added by people working in the Jupi app. But `finalize` requires at least one selected option.

So to log an already-made decision in one shot, you synthesize the chosen option: you pass `finalize` an option whose `title` is the path that was chosen and whose `id` is a freshly generated UUID. The backend stores it as-is (it doesn't require the option to pre-exist). This is deliberate and fine for capture — just know that the resulting record's "selected option" was minted here rather than picked from a populated board. The decision's real value lives in the title and the `closingText` rationale, which are first-class.

## Tools you'll use

Provided by the Jupi MCP server (may appear namespaced as `mcp__Jupi__…` or `mcp__claude_ai_Jupi__…`):

- `create-decision-tool` — creates a STARTED decision. Pass `groupSlug`, `title`, and `description` (the context). **Omit `id` and `ownerId`**: the server generates the id and sets you (the authenticated caller) as owner — which also makes you the decision's maker, so you're allowed to finalize it. Returns `{ id, url, … }`.
- `finalize-decision-tool` — closes a STARTED decision. Pass `groupSlug`, `decisionId`, `selectedOptions` (≥1 of `{id, title}`), and `closingText` (the rationale). Caller must be the decision's maker — which you are, from the create step.

## Workspace setup

Read the workspace slug from `.claude/jupi.local.json` (gitignored):

```json
{ "workspace": "<group-slug>" }
```

If it's missing, ask for the slug, use it for this run, and offer to save it. Never commit this file.

## Workflow

1. **Pin down the three things worth recording**, from the conversation or by asking:
   - **title** — the decision, stated as a resolved choice ("Adopt Postgres for the events store", not "Which datastore?").
   - **chosen path** — what was actually decided; becomes the selected option's title. If two things were chosen, record several options.
   - **rationale** — _why_; becomes `closingText`. This is what makes the record worth keeping, so don't skip it. Pull it from the discussion if you can.
   - Optionally a **description** — extra context (links, the situation that prompted it). Goes in `create`'s `description`. **Format it as HTML** (`<p>`, `<ul>`/`<li>`, `<strong>`) — Jupi renders the description as rich text, not Markdown.

2. **Create** the decision:
   `create-decision-tool({ groupSlug, title, description? })`. Capture the returned `id` and `url`.

3. **Generate a UUID** for the synthetic option. Don't hand-fabricate one — produce a real v4 so it always validates, e.g. `uuidgen` or `python3 -c "import uuid; print(uuid.uuid4())"`.

4. **Finalize**:
   `finalize-decision-tool({ groupSlug, decisionId: <id from step 2>, selectedOptions: [{ id: <uuid from step 3>, title: <chosen path> }], closingText: <rationale> })`.

5. **Confirm** back to the user with the decision URL and a one-line summary of what was logged. The link is the receipt — always surface it.

## Example

**Input (from a conversation that just wrapped):** "Let's go with feature flags via the existing LaunchDarkly setup instead of building our own — log that."

**What you do:**

- title: `Use LaunchDarkly for feature flags rather than an in-house system`
- chosen path (option title): `Adopt existing LaunchDarkly setup`
- closingText: `Already integrated and paid for; in-house flags would cost weeks for no added capability we need now. Revisit only if per-seat pricing becomes a problem at scale.`
- create → finalize with a generated option UUID → report the URL.

## Guardrails

- **Only for decisions that are made.** Finalizing implies closure. If it's still open or needs someone else's sign-off, stop and use `submit-decision` instead.
- **Always include rationale.** A logged decision with no `closingText` is barely better than no record — future-you won't know _why_. If the user gives you a bare title, ask for the reasoning before finalizing.
- **One decision per call.** If the user rattles off several distinct decisions, log them separately so each is independently searchable.
- **Surface the URL.** It's how the user verifies and shares what was captured.
