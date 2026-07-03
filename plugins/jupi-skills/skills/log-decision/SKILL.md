---
name: log-decision
description: "Record a decision the user has ALREADY made into Jupi (the team's decision platform) as a finalized, searchable entry — the title, the chosen path, and the rationale. Use whenever a choice gets settled and the user wants it captured: \"log this decision\", \"record that we're going with X\", a validated trade-off, a meeting outcome, an ADR-style note, or the conclusion of a discussion you just had together. This spans any ideation or strategy work, not just product — a feature direction, but equally a GTM call, a pricing choice, a hire, an org or ops change. When such work is exploratory (brainstorming, weighing options, ideating), wait: nothing is decided until the exploration concludes, so only offer to log once the brainstorming phase has actually landed on a direction — never mid-stream while ideas are still in play. At that closing moment, lean toward offering it: decisions captured in the flow of work stay searchable later, while the ones everyone \"will write up afterward\" evaporate. This finalizes the decision in one step, so use it only for calls that are actually made, not open questions (for those, use submit-decision)."
---

# Log decision

## What this is for

A decision that lives only in a Slack thread or someone's memory is a decision the team will re-litigate in three months. This skill writes a settled decision into Jupi as a **FINALIZED** record — so it surfaces later via `search-decisions` with its rationale attached. Think of it as the "commit message" for a choice: quick to write in the moment, valuable forever after.

Use it for calls that are _made_. If the question is still open and someone else needs to decide, that's `submit-decision`, not this.

## The shape of the underlying tools

Jupi's model is: a decision is created in `STARTED` state with options on its board, then `finalize` closes it by recording which option(s) won. To log an already-made decision, you walk that same path in one sitting: create the decision, create the chosen path as a **real option on the board**, then finalize selecting it. The record reads exactly like a decision made in the app — a populated board with the winner marked — and its rationale lives in `closingText`.

## Tools you'll use

Provided by the Jupi MCP server (may appear namespaced as `mcp__Jupi__…` or `mcp__claude_ai_Jupi__…`):

- `create-decision-tool` — creates a STARTED decision. Pass `groupSlug`, `title`, `description` (the context), and `allowWorkspaceContributions: false`. **Omit `id` and `ownerId`**: the server generates the id and sets you (the authenticated caller) as owner — which also makes you the decision's maker, so you're allowed to finalize it. Returns `{ id, url, … }`.
  - `allowWorkspaceContributions: false` is the default here: a logged decision is your own record, so it's created owner-only and does **not** notify the workspace. Omit it (or pass `true`) only when the user explicitly wants the logged decision visible to everyone in the workspace.
- `add-decision-options-tool` — puts options on the decision board, exactly as if added by hand in the app. Pass `groupSlug`, `decisionId`, and `options` (each `{ title, description }` — `title` plain text, `description` HTML). Returns the created options **with their server-side `id`s** — you need those for finalize.
- `finalize-decision-tool` — closes a STARTED decision. Pass `groupSlug`, `decisionId`, `selectedOptions` (≥1 of `{id, title}` — the ids returned by `add-decision-options-tool`), and `closingText` (the rationale). Caller must be the decision's maker — which you are, from the create step.

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

2. **Create** the decision (owner-only by default):
   `create-decision-tool({ groupSlug, title, description?, allowWorkspaceContributions: false })`. Capture the returned `id` and `url`.

3. **Create the chosen option on the board** (before finalizing — a FINALIZED decision no longer accepts options):
   `add-decision-options-tool({ groupSlug, decisionId: <id from step 2>, options: [{ title: <chosen path>, description: <one or two sentences on what this path is, as HTML> }] })`.
   If several things were chosen, pass several options in the same call. Capture the returned option `id`(s).

4. **Finalize**, selecting the option(s) you just created:
   `finalize-decision-tool({ groupSlug, decisionId: <id from step 2>, selectedOptions: [{ id: <option id from step 3>, title: <chosen path> }], closingText: <rationale> })`.

5. **Confirm** back to the user with the decision URL and a one-line summary of what was logged. The link is the receipt — always surface it.

## Example

**Input (from a conversation that just wrapped):** "Let's go with feature flags via the existing LaunchDarkly setup instead of building our own — log that."

**What you do:**

- title: `Use LaunchDarkly for feature flags rather than an in-house system`
- chosen path (option title): `Adopt existing LaunchDarkly setup`, option description: `<p>Ship flags through the LaunchDarkly account we already run instead of building our own toggle system.</p>`
- closingText: `Already integrated and paid for; in-house flags would cost weeks for no added capability we need now. Revisit only if per-seat pricing becomes a problem at scale.`
- create → add the chosen option to the board → finalize selecting its returned id → report the URL.

## Guardrails

- **Only for decisions that are made.** Finalizing implies closure. If it's still open or needs someone else's sign-off, stop and use `submit-decision` instead.
- **Let brainstorming finish first.** Ideation and strategy work moves through a divergent phase where options are floated, reshaped, and discarded — nothing is settled yet, even when the user sounds enthusiastic about an idea mid-stream. Logging then captures a decision that wasn't actually made and clutters the record with false history. Hold off until the exploration converges: the user signals they've landed (\"ok, we're going with…\", \"decided\", \"let's lock that in\"), or the discussion has clearly resolved. When in doubt whether the brainstorm is done, ask before logging rather than freezing a tentative idea.
- **Always include rationale.** A logged decision with no `closingText` is barely better than no record — future-you won't know _why_. If the user gives you a bare title, ask for the reasoning before finalizing.
- **One decision per call.** If the user rattles off several distinct decisions, log them separately so each is independently searchable.
- **Surface the URL.** It's how the user verifies and shares what was captured.
