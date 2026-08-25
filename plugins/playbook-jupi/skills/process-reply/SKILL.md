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
5. `db.mjs run-close <id>` honestly, and return the planner's verdict for that dossier — the
   decision link, the draft trace, or the handoff line.
