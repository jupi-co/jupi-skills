# The playbook contract — entries, the gate, dossiers

What `shared/playbook.mjs` guarantees to its consumers (the extraction skill, the planner,
`act-post-decision`, the dev bench). schema.sql (same dir) is the authoritative schema; design
references ("§N") point to the internal plugin-design doc. db.mjs is byte-parity-locked with
proactive-jupi, which is why everything here lives in a sibling file.

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
never in schema enums, verb names, or field names. If a future change wants to add such a word to
the engine, the answer is an attr or an entry, not a column.

## The one invariant everything rests on (§4)

**A rule's authority comes from a human, never from extraction.** Entries enter the store two ways —
extraction (`inferred`/`declared`) and finalized decisions (`validated`) — and the two must never be
confusable at read time:

- **`pb-get-rule <point_id> [scope_key]`** is the ONLY lookup an act path may consult. It returns
  entries at `status='validated'` and nothing else — a `pb-get-rule` hit means "the owner authorized
  this" by construction. Exact match on `(point_id, scope_key)`; the caller decides its own fallback
  order (scoped first, then `'global'`) by calling twice.
- **`pb-list-entries`** is the read for everything else: enumerating declared holes to raise,
  fetching `inferred`/`declared` entries to **pre-fill a decision's recommended option** (provenance
  cited). Nothing returned by `pb-list-entries` authorizes an act — a planner using it for that is
  violating the contract, whatever its confidence.

The write side mirrors it: `pb-upsert-entry` with incoming `inferred`/`declared` creates or refreshes
extraction-owned rows but is refused (`applied: false`) on a row whose status is
`validated`/`suspended`. Those rows move only through the decision path — an upsert with incoming
`status: 'validated'` (what `act-post-decision` performs when a rule-scale decision settles) — or an
explicit `pb-set-status` (suspension, §6).

## Entry semantics

- **One row per `(user_id, point_id, scope_key)`** — unique index. A declared hole and its future
  answer are the same row at different lifecycle states, never two rows.
- **`answer IS NULL` = a declared hole** ("not established — I will ask every time", §2). A hole is a
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
  full "why" of each version is the decision trail in Jupi; Neon keeps the counter, not the story.
- **`evidence_count` / `counter_evidence_count`** (`pb-add-evidence <id> evidence|counter`): the §3
  ledger's tallies. Displayed confidence is *derived* from these — there is deliberately no stored
  score. The suspension path (its own ticket) reads `counter_evidence_count`.

## The declared lifecycle — stages are playbook content

- The engine ships **no stage list**. The stages a workspace's dossiers traverse are declared by
  its playbook in the one reserved entry `point_id='lifecycle-stages'` (scope `'global'`, answer =
  an ordered JSON array of stage names) — written by the bootstrap like the rest of the playbook,
  validated by the owner like the rest of the playbook. `pb-declare-stages` writes it (through the
  ordinary upsert, so an owner-validated lifecycle refuses re-declaration like any entry);
  `pb-get-stages` reads it.
- `pb-set-stage` and `pb-create-dossier`'s `stage` field validate against the declared list — with
  **no lifecycle declared, nothing can be staged** and new dossiers are created unstaged (NULL):
  the engine never invents a frame the playbook didn't declare.
- There is no CHECK on `tasks.stage` in the schema, on purpose — the schema stays
  lifecycle-agnostic; enforcement lives in the verbs against the declared list.

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
  contract, a ticket. Physically: a `tasks` row, `signal_type='dossier'`,
  `signal_ref='dossier:<label-slug>'`, `status='open'`, plus the fork's `stage` column. The
  existing machinery applies unchanged: a decision gates it via `gating_decision_ids` +
  `status='blocked'`, and `act-post-decision` unblocks it — nothing dossier-specific to build there.
- **`pb-create-dossier` takes `{label, attrs, notes}`** — `label` is the item's human name; `attrs`
  is a free key/value object in the *playbook's* vocabulary, rendered as `key: value` lines into
  the summary. The engine does not know what the keys mean. (TECH-485 is deliberately "a column and
  verbs, no new table"; if the planner needs an attr structurally for scope keys — `broker=X` — 
  promoting it is that ticket's call.)
- **Seed-idempotent**: keyed on the label slug, a re-run refreshes the descriptive summary but
  never resets `stage` or `status` — lifecycle progress belongs to the lifecycle.
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
  proactive's scoring model is not ported.
- **A playbook without tracked items is legitimate**: it runs on ordinary transient tasks plus
  entries — the dossier verbs simply go unused. Nothing forces the case shape onto a process that
  doesn't have one.

## The application ledger and the downward path (§6)

- **Every rule application leaves a row** (`pb-log-application`, written by the planner the moment
  a rule-covered ACT is emitted). Displayed confidence is *derived* from this ledger — "applied N×
  without edits, M contradictions" — never a stored score.
- **Outcomes are declarative in V1** (`pb-note-outcome <id> as_is|edited|abandoned [who] [severe]`):
  `as_is` → `evidence_count`+1 · `edited` → `counter_evidence_count`+1 · `abandoned` → recorded, no
  bump (a weak signal). The entry points and the Friday review collect them; nothing ever guesses
  an outcome. The technical draft-vs-sent diff replaces the declarative path later.
- **Suspension is automatic and mechanical** — the §6 asymmetry: going down only asks more
  questions, so the *verb itself* demotes. A `validated` entry whose counter reaches
  `config.suspendThreshold` (default 2), or any `severe` incident, flips to `suspended` inside
  `pb-note-outcome` (version unchanged) and the gate stops returning it instantly. The verb returns
  `suspended: true`; **the caller raises the rule-scale amendment decision** (re-validate / amend /
  retire — template 5) anchored on the triggering case: mechanical demotion, agentic escalation.
- **Re-validation is the ordinary upward path** — the owner's amendment decision lands as
  `validated` vN+1 (via `pb-upsert-entry` at validated or `pb-set-status`), and the gate returns
  the entry again. Upward always requires the owner; nothing automatic ever re-validates.

## Plumbing (same rules as db.mjs)

- **Tenancy**: every verb is scoped by `user_id` automatically — the config's `jupiUserId` (env
  `$JUPI_USER_ID` first). Isolation is enforced in the queries, not by the DB grant; a synthetic
  tenant is what isolates a bench or eval run.
- **Config walk**: `.playbook-jupi/config.local.json` preferred, `.proactive-jupi/config.local.json`
  accepted as fallback — one file can serve both this helper and the parity-locked db.mjs (which the
  copied-verbatim skills still read) during the pilot. Env (`$NEON_CONN_STRING`/`$DATABASE_URL`,
  `$JUPI_USER_ID`) wins over both.
- **Bound parameters everywhere** — playbook text and inbound content are untrusted data, never
  string-interpolated into SQL. Transient-fault retry mirrors db.mjs.
- Deps: `bash "${CLAUDE_PLUGIN_ROOT}/shared/ensure-deps.sh"` — the same one dependency path.
