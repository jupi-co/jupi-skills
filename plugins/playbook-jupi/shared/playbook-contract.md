# The playbook contract — entries, the gate, dossiers

What `shared/playbook.mjs` guarantees to its consumers (the extraction skill, the funnel planner,
`act-post-decision`, the dev bench). schema.sql (same dir) is the authoritative schema; design
references ("§N") point to the internal plugin-design doc. db.mjs is byte-parity-locked with
proactive-jupi, which is why everything here lives in a sibling file.

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
`status: 'validated'` (what `act-post-decision` performs when a `[BR]` decision settles) — or an
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
  `validated` (a finalized `[BR]` decision) ⇄ `suspended` (counter-evidence sent it back to
  case-by-case, §6 — automatic downward is allowed; upward always requires the owner).
- **`version`**: 0 = never validated; every transition TO `validated` bumps it (`pb-upsert-entry`
  with validated, or `pb-set-status … validated`) — a re-validation or amendment is vN+1 (§6). The
  full "why" of each version is the decision trail in Jupi; Neon keeps the counter, not the story.
- **`evidence_count` / `counter_evidence_count`** (`pb-add-evidence <id> evidence|counter`): the §3
  ledger's tallies. Displayed confidence is *derived* from these — there is deliberately no stored
  score. The suspension path (its own ticket) reads `counter_evidence_count`.

## Dossier semantics (§8)

- A dossier is a `tasks` row: `signal_type='dossier'`, `signal_ref='dossier:<account-slug>'`,
  `status='open'`, plus the fork's `stage` column. The existing machinery applies unchanged: a
  decision gates it via `gating_decision_ids` + `status='blocked'`, and `act-post-decision` unblocks
  it — nothing dossier-specific to build there.
- **Stages**: `to-qualify → contact-identified → sequence-running → reply-to-handle → call-booked |
  phone-fallback`. `stage_detail` is stage-local free detail (the mail index while
  `sequence-running`); `pb-set-stage` replaces it on every transition so it can't lie across stages.
- **`pb-create-dossier` is seed-idempotent**: keyed on the account slug, a re-run refreshes the
  descriptive summary but never resets `stage` or `status` — funnel progress belongs to the funnel.
- Account attributes (insurer, broker, contact) currently live as `key: value` lines in the
  dossier's `summary` — TECH-485 is deliberately "a column and verbs, no new table". If the planner
  needs them structurally for scope keys (`broker=X`), promoting them to columns is that ticket's
  call.
- **Priority is derived, never stored**: the planner ranks from stage (a waiting reply > a due
  follow-up > nothing). Dossier rows carry no score; proactive's scoring model is not ported.

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
