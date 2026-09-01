# Reporting — the run log and the user's version

Every run reports the same substance to two audiences. The **run log** is the technical record —
for us, the bench, the routines' transcripts. The **user's version** is what a person reads: the
**default final message** of every surface a human sees — a direct planner run, `/go`, "process
this reply", and a scheduled routine's closing summary alike. Same blocks, same content, different
words. The shape is fixed here rather than left to judgement because on the reference test the
readable version simply didn't exist: the run answered in engine vocabulary — dossier ids, stages,
clusters, tripwires — and the person it was for could not use a word of it.

## The run log — the technical report

The accountability artifact — but **availability, not ceremony, is the requirement, so where it is
rendered depends on who is waiting**. An **unattended run** (a scheduled routine, the bench) always
renders it in the transcript before the closing summary — that transcript is the only durable
record. An **attended run** renders it only under `--technical`, on request afterwards, or in
`--dry-run` (where the report IS the deliverable); otherwise the narration stays the lean
per-stage lines and the user gets their version without sitting through tables they won't read.
Returned, never written to a file (a scheduled run has no workspace folder anyone will read; a
local reader is already in the conversation).

1. **The dossier table** — one row per dossier in the window: **dossier · stage · next step ·
   verdict (ACT rule_ref / DECIDE link / WAIT-blocked / tripwire) · what happened**.
2. **Deferred** — every budget cut, with its leverage (dossiers unblocked) and why this one. Not
   optional: "nothing deferred" is written out rather than left as an absent table — a budget that
   trimmed clusters reads exactly like a quiet run otherwise.
3. **☐ Handoffs — over to you** — every open `tool: handoff` row, new and outstanding alike:
   title · what Jupi prepared · dossier link · how long it has been waiting.
4. **Guardrail events** — tripwire hits, out-of-script classifications, unmatched inbound the
   watch reported.
5. **Gaps — what you didn't know** — every entity or fact you needed while framing a step or a
   decision and didn't have: *"who <person> at <org> is"*, *"whether <company> is already a
   customer"*. One line each, named concretely, **whether or not a brain is connected** — with
   one, it's what the brain couldn't answer; without one, it's what a brain would have answered.
   Empty is written out. This is the only measure of what missing context actually costs, and it
   is the evidence behind keeping, adding, or dropping the memory connector.
6. **Footer** — `mode` · `decisionBudget` · what this run left for the next one.

`--dry-run`: the report IS the deliverable — say the window is as-of the last real refresh.

## The user's version — the default final message

You report as an **assistant** to the person you work for: clear, direct, factual. What matters,
in this order — that they understand in one read **what was done**, **what awaits them**, and
**what is on their side**. Low verbosity: the essentials, nothing else.

Same four blocks as the log, said in their words:

1. **What moved** — one sentence per dossier, **by its label**, never an id and never a stage
   name: *"For Alpha, the contact is identified."* Name the artifact they'll find: *"a reply
   draft is waiting in your Gmail."* Nothing moved → say so, one line.
2. **Decisions waiting on you** — each title as it reads in Jupi, **a link they can click**, and
   what settling it unblocks (*"this one also unblocks two other accounts"*). Near the top, never
   compressed to a count.
3. **Over to you** — the handoff checklist, one line per item: who · what · what Jupi prepared
   and where. *"The contact for Beta is still to be found — that one is on your side."*
4. **Left for next time** — deferrals and cuts, **naming the limit when a limit did the cutting**
   (*"I stop at 5 decisions a run; 6 qualified today"*) — that is how they learn a setting is
   too low.

The rules that make it land:

- **The user's language** — the language of the owner's playbook documents (in conversation, the
  language they are speaking). Never the skills' English by default.
- **No engine vocabulary**: dossier ids, stage, cluster, tripwire, residue, ACT/DECIDE, rule_ref,
  entry, point. A tripwire hit reads *"I stopped short and I'm asking you first"*; an
  out-of-script reads *"this mail falls outside the playbook — here is the question it raises."*
- **Numbers only where they change what the reader would do** — "6 left for next time" earns its
  place; a parse confidence of 0.62 doesn't.
- **`--dry-run` = conditional everywhere** — *"what I'd handle"*, *"the decisions I'd put to
  you"*. Nothing has been done; past tense would claim work that didn't happen, and this report
  is often the first thing an owner ever reads from Jupi.
- **Complete against the run's facts**: every dossier touched, every open handoff, every cut made
  must appear — and blocks 3 and 4 appear even when empty (one line each), because they are the
  ones the reader most needs and would never think to ask for. The user's version may be shorter
  than a run log in words, never in facts.
- **Close on posture, not config**: *"I'm in draft mode — nothing goes out without you."*

## Composition — how an orchestrating run reports

`go`, `process-reply` and the scheduled routines invoke several skills and end with **one** user's
version, never a stack of per-skill reports: stitch the invoked skills' user versions into a
single narrative in block order 1→4, deduplicating dossiers touched by more than one skill.
`act-post-decision` (orchestrator-facing — its summary is written for the caller) returns its
short technical summary; the orchestrator restates it into block 1. The invoked skills' technical
reports follow the surface rule above: rendered in full in an unattended transcript, available on
request in an attended one.

## The technical channel — `--technical`

What must never be traded away is the log's **availability**, not its unconditional rendering: an
attended run holds every fact in its own context, so materializing the tables before every summary
would only make the user wait through output they won't read (§run log — attended runs default to
the lean narration). The channels:

- **`--technical` on an invocation** (accepted by `act-or-decide`; `go` and `process-reply` pass
  it through like `--dry-run`) → the final message IS the full run log; no user's version required.
- **In conversation** — "show me the technical detail" after any run renders the current run's
  log, faithfully, from the same session's context.
- **Routines have no switch and need none**: an unattended transcript always carries the full run
  log above the closing summary — debugging a scheduled run means opening it.
