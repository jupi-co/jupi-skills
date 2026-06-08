---
name: submit-decision
description: "Open a decision in Jupi (the team's decision platform) that the user can't settle alone and hand it to the right person to decide. Use whenever a question needs someone else's call — a blocker in a spec, an unresolved trade-off, anything needing a lead's or owner's sign-off — or when the user says \"ask X to decide this\", \"escalate this\", \"this needs approval from…\", \"raise this with the team\". Lean toward offering it the moment an open question surfaces that isn't the user's to close: capturing it as an assigned decision (with framing) beats leaving it buried in a doc where it stalls. This creates the decision and assigns a decider but deliberately does NOT finalize it — closing it is the assignee's job (for decisions the user has already made themselves, use log-decision instead)."
---

# Submit decision

## What this is for

Some questions aren't yours to close. The trade-off needs the eng lead's call; the scope cut needs the PM's sign-off; the compliance angle needs legal. Left in a doc, these stall — nobody owns them and they rot as comments. This skill turns an open question into a real, **assigned** decision in Jupi: framed with enough context for the decider to act, owned by you, and waiting on the right person to finalize.

The line between this and `log-decision`: log records a call _you've made_; submit opens a call _someone else makes_. This skill never finalizes — doing so would put words in the decider's mouth.

## Tool you'll use

`create-decision-tool` from the Jupi MCP server (may appear namespaced as `mcp__Jupi__…` or `mcp__claude_ai_Jupi__…`). There is intentionally **no** `finalize` step here.

Inputs you'll pass:

- `groupSlug` — the workspace.
- `title` — the question, sharply stated.
- `description` — the framing (see below). This is mandatory in spirit: a decision with no context is a decision the assignee can't act on.
- `makerId` — the **Jupi user UUID** of the person who should decide. They become the decision's _maker_ (the only role allowed to finalize); you (the authenticated caller) are recorded as _owner_.
- `private` — pass **`true`** (the default for this skill). The decision is visible only to you (owner) and the assigned `makerId` — who can always see and finalize it — so submitting it does **not** notify or expose it to the whole workspace. This keeps a targeted hand-off targeted. Pass `false` only when the user explicitly wants everyone in the workspace to see and weigh in.
- Omit `id` and `ownerId` — the server generates the id and sets you as owner.

Returns `{ id, url, makerId, … }`.

## Getting the assignee's UUID (the one manual step)

There is no MCP tool to look people up by name or email, so `makerId` has to be a UUID the user supplies. To make this bearable across repeated use, keep a small contacts map in `.claude/jupi.local.json` (gitignored) alongside the workspace:

```json
{
  "workspace": "<group-slug>",
  "contacts": {
    "Jane Doe": "11111111-1111-4111-8111-111111111111",
    "Eng Lead": "22222222-2222-4222-8222-222222222222"
  }
}
```

Resolve the assignee like this:

1. If the user names someone in `contacts`, use that UUID.
2. Otherwise ask the user for the person's Jupi user UUID, proceed, and offer to save it under their name in `contacts` so it's a name next time, not a UUID.

If `workspace` is missing too, ask for it and offer to save. Never commit this file.

## Framing the question (the `description`)

A good submission gives the decider everything they need and nothing they have to chase. Put this in `description`:

- **Context** — what prompted the question, in a sentence or two.
- **Options** — the alternatives you can see, if any, and their trade-offs.
- **Your lean** — what you'd do and why, if you have a view. (A lean helps; it doesn't pre-empt — they still decide.)
- **What's needed to decide** — the missing input, or what "done" looks like.

**Format the `description` as HTML** — Jupi renders it as rich text, not Markdown. Use `<p>` for paragraphs, `<ul>`/`<li>` for the options, and `<strong>` for the labels (Context / Options / Lean / Needed). Don't send Markdown or bare newlines.

A naked question ("Postgres or Dynamo?") wastes the decider's time and usually bounces back. Spend the extra two sentences.

## Workflow

1. **Resolve the workspace** slug from `.claude/jupi.local.json` (prompt + offer to save if missing).
2. **Resolve `makerId`** via the contacts flow above.
3. **Write the framing** into a `description` (as HTML) covering context / options / lean / what's needed.
4. **Create** the decision (private by default — owner + assignee only):
   `create-decision-tool({ groupSlug, title, description, makerId, private: true })`.
5. **Stop there — do not finalize.** Report back the decision `url` and who it's assigned to, and tell the user to share the link with that person (the decider opens it in Jupi to weigh in and close it).

## Example

**Input:** "I can't decide whether the new export runs sync or async — that's the eng lead's call. Raise it."

**What you do:**

- title: `Export pipeline: synchronous or async job?`
- makerId: from `contacts["Eng Lead"]` (or ask, then offer to save).
- description (HTML):
  ```html
  <p><strong>Context:</strong> the new CSV export can take 30s+ for large workspaces, which blocks the request thread.</p>
  <p><strong>Options:</strong></p>
  <ul>
    <li>(a) Keep it synchronous — simplest, but risks timeouts and ties up a worker.</li>
    <li>(b) Move to an async job with a download-ready notification — more moving parts, needs the job queue.</li>
  </ul>
  <p><strong>My lean:</strong> (b) — we already run the queue for ingestion and the UX is better.</p>
  <p><strong>Needed:</strong> your call on whether the added complexity is worth it now, or we ship (a) and revisit.</p>
  ```
- create (no finalize) → report URL + "assigned to Eng Lead; send them the link."

## Guardrails

- **Never finalize.** Finalization is the assignee's decision, full stop. If the user has actually already decided, you want `log-decision`, not this.
- **No naked questions.** If the user hasn't given you enough to frame it, ask for the context before creating — an unframed decision just bounces back to them.
- **One question per submission**, each assigned to its right decider — don't bundle unrelated calls into one decision.
