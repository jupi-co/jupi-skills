# The playbook contract — entries, the gate, dossiers

What the **`pb-*` tools on the Jupi connector** guarantee to their consumers (the extraction
skill, the planner, `act-post-decision`, the dev bench). The tools are served by Jupi's backend
(the `playbook` module — spec: JUPI-604); the tables live in Jupi's own database, and this file is
the semantic contract the skills program against. Design references ("§N") point to the internal
plugin-design doc.

## What a playbook is — and what the engine is not

A playbook plays three roles at once: a **guide** (decision points and their rules — exact lookup,
hole → decision), a **memory** (validated decisions enrich it), and a **frame** (it defines what is
in scope for a run at all: pointed at a mailbox, the engine only picks up what the playbook makes
relevant — everything else is out-of-frame by construction, to report, never to invent work from).
The closed world is the *user's* world: **their setup — their playbook — defines the frame of the
run**, including what the tracked items are and what lifecycle those items traverse. An outreach
pilot tracks accounts through a funnel; a hiring playbook tracks candidates; a contract-review
playbook tracks contracts; a pure inbound-triage playbook may track nothing long-lived at all (it
runs on ordinary transient tasks plus entries — no dossier machinery required).

**The engine-vocabulary rule** (what keeps this file honest, PR after PR): the engine knows exactly
four kinds of thing — *dossiers* (tracked items), a *declared lifecycle*, *entries*, and
*decisions*. Any word that comes from an owner's document — account, sequence, reply, insurer,
candidate, contract — is playbook **content**, and belongs in fixtures, playbook stores, and attrs,
never in engine enums, verb names, or field names. If a future change wants to add such a word to
the engine, the answer is an attr or an entry, not a column.

## Identity and tenancy — the connector is the boundary

Every tool call is **scoped server-side by the authenticated Jupi user** — the OAuth principal of
the connector, the same `jupiUserId` that keys the brain's Supermemory container tag. No tool
takes or accepts a user id from the caller; there is no connection string, no credential in any
config or prompt, and no client-side query to scope. (This replaces the old honor-system client
scoping over a shared Neon project — the auth boundary is the physical boundary now.) A skill that
needs the id itself — the brain's container tag — reads it from `get-current-user-tool`, never
from config.

## The one invariant everything rests on (§4)

**A rule's authority comes from a human, never from extraction.** Entries enter the store two ways —
extraction (`inferred`/`declared`) and finalized decisions (`validated`) — and the two must never be
confusable at read time:

- **`pb-get-rule`** (`point_id`, optional `scope_key`) is the ONLY lookup an act path may consult.
  It returns entries at `status='validated'` and nothing else — a `pb-get-rule` hit means "the
  owner authorized this" by construction. Exact match on `(point_id, scope_key)`; the caller
  decides its own fallback order (scoped first, then `'global'`) by calling twice.
- **`pb-list-entries`** is the read for everything else: enumerating declared holes to raise,
  fetching `inferred`/`declared` entries to **pre-fill a decision's recommended option** (provenance
  cited). Nothing returned by `pb-list-entries` authorizes an act — a planner using it for that is
  violating the contract, whatever its confidence.

The write side mirrors it, enforced by the server: `pb-upsert-entry` with incoming
`inferred`/`declared` creates or refreshes extraction-owned rows but is refused (`applied: false`)
on a row whose status is `validated`/`suspended`. Those rows move only through the decision path —
an upsert with incoming `status: 'validated'` (what `act-post-decision` performs when a rule-scale
decision settles) — or an explicit `pb-set-status` (suspension, §6).

## Entry semantics

- **One row per `(user, point_id, scope_key)`** — server-enforced unicity. A declared hole and its
  future answer are the same row at different lifecycle states, never two rows.
- **`answer` absent = a declared hole** ("not established — I will ask every time", §2). A hole is a
  real entry: it carries the question and scope axis so the planner can raise the right decision.
- **`answer_kind`** is the §5 terminal-state vocabulary: `rule` ("when X, always Y") · `always_ask`
  (validated case-by-case — it pre-empts *re-proposing codification*, not the decision itself) ·
  `delegated` (the owner handed the choice over; pre-empts like a rule, provenance records that the
  *discretion* was granted).
- **`status`** lifecycle (§3): `inferred` (LLM-derived from sparse sources) → `declared` (verbatim
  and unambiguous from the owner's doc — same authority as inferred in V1, cheaper to confirm) →
  `validated` (a finalized rule-scale decision) ⇄ `suspended` (counter-evidence sent it back to
  case-by-case, §6 — automatic downward is allowed; upward always requires the owner).
- **`version`**: 0 = never validated; every transition TO `validated` bumps it (`pb-upsert-entry`
  with validated, or `pb-set-status … validated`) — a re-validation or amendment is vN+1 (§6). The
  full "why" of each version is the decision trail in Jupi; the store keeps the counter, not the
  story.
- **`evidence_count` / `counter_evidence_count`** (`pb-add-evidence`, `evidence|counter`): the §3
  ledger's tallies. Displayed confidence is *derived* from these — there is deliberately no stored
  score. The suspension path reads `counter_evidence_count`.

## The declared lifecycle — stages are playbook content

- The engine ships **no stage list**. The stages a workspace's dossiers traverse are declared by
  its playbook in the one reserved entry `point_id='lifecycle-stages'` (scope `'global'`, answer =
  an ordered JSON array of stage names) — written by the bootstrap like the rest of the playbook,
  validated by the owner like the rest of the playbook. `pb-declare-stages` writes it (through the
  ordinary upsert, so an owner-validated lifecycle refuses re-declaration like any entry);
  `pb-get-stages` reads it.
- `pb-set-stage` and `pb-create-dossier`'s `stage` field validate against the declared list — with
  **no lifecycle declared, nothing can be staged** and new dossiers are created unstaged:
  the engine never invents a frame the playbook didn't declare.

## Reserved entries — the point ids the engine reads by convention

Three point families are reserved; everything else in the store is the playbook's own vocabulary.

- **`lifecycle-stages`** (above) — the declared lifecycle.
- **`playbook-name`** (scope `'global'`) — the playbook's human name, proposed from the owner's
  documents and confirmed in setup's prelude; it stays extraction-owned (`declared`), provenance
  says who confirmed it. Consumers: the planner's decision contexts (*"as part of the playbook
  « <name> »"*) and the reports. Absent → consumers say "this playbook" and flag the gap — a
  missing name never blocks a run. Renaming is one ordinary upsert; nothing else to rotate.
- **`tripwire-*`** — the vigilance entries (seeded at setup, extended any time; see the planner's
  `tripwires.md` for how they bind).

## Dossier semantics (§8)

- A dossier is **the playbook's tracked item** — for the pilot an account, elsewhere a candidate, a
  contract, a ticket. Physically: a task row, `signal_type='dossier'`,
  `signal_ref='dossier:<label-slug>'`, `status='open'`, plus a `stage`. The
  existing machinery applies unchanged: a decision gates it via `gating_decision_ids` +
  `status='blocked'`, and `act-post-decision` unblocks it — nothing dossier-specific to build there.
- **`pb-create-dossier` takes `{label, attrs, notes}`** — `label` is the item's human name; `attrs`
  is a free key/value object in the *playbook's* vocabulary, rendered as `key: value` lines into
  the summary. The engine does not know what the keys mean.
- **Seed-idempotent** (server-enforced): keyed on the label slug, a re-run refreshes the
  descriptive summary but never resets `stage` or `status` — lifecycle progress belongs to the
  lifecycle.
- `stage_detail` is stage-local free detail (a sequence's current step index); `pb-set-stage`
  replaces it on every transition so it can't lie across stages.
- **Attaching inbound** (`pb-attach-signal`) is the inbound watch's single write: the signal's
  permalink lands in `signal_url` (the dossier's *current* signal), the match certainty in
  `parse_confidence`, and the stage move it causes travels with it (validated against the declared
  lifecycle; the attached thread/message id becomes `stage_detail` — at an "inbound to handle"
  stage, the detail IS which thread to handle). The dossier's `signal_ref` is its identity key and
  never changes; the watch stores **pointers, never bodies** — the planner re-reads the thread from
  the source at plan time.
- **Priority is derived, never stored**: the planner ranks from stage. Dossier rows carry no score;
  proactive's scoring model is not part of this engine.
- **A playbook without tracked items is legitimate**: it runs on ordinary transient tasks plus
  entries — the dossier tools simply go unused. Nothing forces the case shape onto a process that
  doesn't have one.

## The application ledger and the downward path (§6)

- **Every rule application leaves a row** (`pb-log-application`, written by the planner the moment
  a rule-covered ACT is emitted). Displayed confidence is *derived* from this ledger — "applied N×
  without edits, M contradictions" — never a stored score.
- **Outcomes are declarative in V1** (`pb-note-outcome`: `as_is|edited|abandoned`, optional
  `noted_by`/`severe`): `as_is` → `evidence_count`+1 · `edited` → `counter_evidence_count`+1 ·
  `abandoned` → recorded, no bump (a weak signal). The entry points and the Friday review collect
  them; nothing ever guesses an outcome.
- **Suspension is automatic and mechanical, server-side** — the §6 asymmetry: going down only asks
  more questions, so the *tool itself* demotes. A `validated` entry whose counter reaches the
  suspend threshold (default 2), or any `severe` incident, flips to `suspended` inside
  `pb-note-outcome` (version unchanged) and the gate stops returning it instantly. The tool returns
  `suspended: true`; **the caller raises the rule-scale amendment decision** (re-validate / amend /
  retire — template 5) anchored on the triggering case: mechanical demotion, agentic escalation.
- **Re-validation is the ordinary upward path** — the owner's amendment decision lands as
  `validated` vN+1 (via `pb-upsert-entry` at validated or `pb-set-status`), and the gate returns
  the entry again. Upward always requires the owner; nothing automatic ever re-validates.

## Serving — how skills reach the tools

- The tools live on the **installed Jupi connector** (the same server as the decision tools —
  `create-decision-tool`, `get-decision`, `search-decisions-tool`). Load them via **ToolSearch by
  logical name** (`pb-get-rule`, `pb-list-dossiers`, …); the runtime resolves the server, which may
  appear namespaced. No process to run, no dependency to install, nothing to apply to a database.
- Untrusted content (playbook text, inbound signals) is data in tool arguments — the server binds
  it; nothing is ever interpolated into a query on either side.
- Eval/bench isolation is a backend concern (deferred — the `is_eval` flag on cursors survives;
  the tenant story under OAuth identity lands with the backend's staging/test accounts).
