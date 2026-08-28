---
name: process-reply
description: >-
  Playbook-Jupi's "process this reply" gesture — the operator saw a mail land and wants it handled
  now, without waiting for the scheduled catchup. It has NO logic of its own: it runs the inbound
  watch (refresh-backlog — sweep, match, attach), then the planner (act-or-decide) restricted to
  the ONE dossier the reply attached to — classification, guardrails (tripwires, residue test) and
  next step for that dossier only, nothing else touched. An accelerator, never a gate. Use when a
  specific inbound should be handled immediately: "process this reply", "a reply just came in from
  X — handle it", "traite cette réponse", "deal with this mail". Not for: the whole backlog
  (act-or-decide or /go), carrying out settled decisions (act-post-decision), or Facts
  (update-brain).
disable-model-invocation: false
---

# process-reply — one inbound, handled now

A thin trigger over the watch + planner, scoped to a single dossier. **You add no reasoning of
your own** — classification, guardrails and the next step all belong to the skills you invoke.

1. **The lease** (same four names, same rule as `go`), then `db.mjs run-open process-reply`.
2. **`refresh-backlog`** — the normal sweep: it attaches the new inbound to its dossier (or
   reports it `unmatched`/`ambiguous`). If the user pointed at a specific mail, make sure the sweep
   window covers it; you never bypass the watch's matching by attaching by hand.
3. **Identify the target dossier** = the one the watch just attached the reply to. Unmatched →
   report exactly that (the watch's summary says why) and stop — do not invent an attachment.
   Ambiguous → surface the candidates to the user and stop.
4. **`act-or-decide` restricted to that one dossier** — the full inbound path applies (tripwires
   first, residue test, out-of-script as a first-class outcome), but no other dossier is planned,
   touched, or reported beyond one context line.
5. **The outcome question (§6, declarative V1)** — the operator is right here, which makes this
   the cheapest moment: if this dossier carries applications with outcome `unknown`
   (`playbook.mjs pb-list-applications --outcome unknown`, filter to this dossier), ask in one
   line — *"the draft that preceded this reply: sent as-is, edited, or dropped?"* — and record it:
   `pb-note-outcome <id> <as_is|edited|abandoned> "<who>"` (append `severe` for a genuine
   incident). **If the verb returns `suspended: true`, the entry just went back to case-by-case
   automatically (§6 — down is the conservative direction): raise the [BR] amendment decision NOW**
   (template 5 — re-validate as-is / amend / retire), anchored on this concrete case, and say in
   the report that the rule is suspended pending the owner's call. No answer → leave it `unknown`,
   never guess.
6. `db.mjs run-close <id>` honestly, then end with the user's version for that one dossier
   (rules: act-or-decide's `reference/REPORTING.md` — assistant voice, the user's language): the
   question now waiting with its clickable link, or *"a draft is ready in …"*, or the over-to-you
   line — plus any outcome recorded and any suspension raised, said plainly. The planner's run log
   stays in the narration; `--technical` passes through and makes it the final message.
