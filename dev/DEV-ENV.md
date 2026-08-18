# DEV-ENV — the mirror dev bench runbook

The persistent bench every playbook-jupi PR demos on (TECH-486). **Hybrid tier 1**, decided Aug 10:
**real dev Gmail** (email is the hard part — threading, message-ids, reply parsing, attach; faking it
would test nothing) · **Sheet/Notion as local files** (`dev/mirror/accounts.csv`, a local projection
file) · **Calendar deferred**. The fake world it runs is [`dev/mirror/`](mirror/README.md) — read that
README's cast and zero-real-entities rule first.

## Safety model (why this can't touch anything real)

| Layer | Mechanism |
|---|---|
| Neon | A **separate, empty dev project** (decided Aug 17 — physical isolation, so even a misfilled config cannot reach real data; create it in the Neon console, e.g. `playbook-dev`). On top of it, the synthetic tenant **`dev-mirror`** as defense in depth — every verb filters by `user_id`, and `seed`/`reset` **refuse any tenant not prefixed `dev-`/`eval-`** (guard inside the core functions, not just the CLI). NOT a Neon branch: a branch copies the parent's real data into the dev environment, which defeats the point |
| Jupi decisions | Workspace **`test`** only (from config `jupiWorkspace`) — never a real workspace |
| Outbound mail | Every fixture address is **`.example`** (RFC-reserved, unresolvable) — even a mistaken real send goes nowhere; and V1 is draft-gated anyway |
| Secrets & identities | The Neon string and the **dev mailbox address live only in your local gitignored config** (`.playbook-jupi/`); the repo carries placeholders. Nothing derived from real pilot data ever lands in this repo |

## One-time setup

**Human steps** (do these first — nothing else blocks on them):

1. **Create the dev Google account** — the mirror operator's mailbox ("Léa Marchal"'s stand-in). Pick
   any address; it stays out of the repo — it will live only in your local config (step 3).
2. **Connect its Gmail** to the Claude account that runs dev sessions (claude.ai → connectors), so the
   bench sessions can read and draft in that mailbox.
3. **Verify the Jupi `test` workspace answers**: call `search-decisions-tool` with `groupSlug: "test"`
   — `{"items":[]}` (or items) = OK; `Group <slug> not found` = KO.

**Machine steps** (from the repo root):

```bash
cp dev/config.template.json .playbook-jupi/config.local.json
# … then fill <neon-conn-string> and <dev-mailbox> in the copy (gitignored)
```

```bash
bash plugins/playbook-jupi/shared/ensure-deps.sh
```

```bash
node plugins/playbook-jupi/shared/apply-schema.mjs
```

First time only — a fresh apply on the empty dev project (idempotent; safe to re-run anytime). Then:

```bash
node dev/seed.mjs
```

Declares the pilot lifecycle (`to-qualify → contact-identified → sequence-running → reply-to-handle →
call-booked | phone-fallback` — pilot content, declared by the seed exactly as a bootstrap would
declare it) and creates the 5 dossiers from the mirror's reporting sheet, entering at `to-qualify`.

**Or run the real bootstrap instead of the seed**: `/playbook-jupi:setup-playbook-jupi` in a dev
session — the agentic path: it extracts the playbook from the mirror's docs (decision points,
declared/inferred entries, **holes**), creates the dossiers from the same source, and renders the
projection to `projectionTarget`. The seed stays the fast mechanical path (no extraction, no
projection); both are idempotent and they compose — seed first, bootstrap enriches.

## Who plays whom

| Mirror role | Played by | Where |
|---|---|---|
| **Claire Bonnaire** (owner, decider) | you | settles decisions in the Jupi `test` workspace |
| **Léa Marchal** (ops) | the dev mailbox | outreach runs from it; drafts appear there; she "sends" |
| **The prospect** | you, from any external mailbox you control | injects scenario replies into the dev mailbox |

## Run one cycle (walkthrough run 1)

The full cycle, with per-step status — the bench predates the Phase-2 skill rewrites, so drive the
not-yet-live steps by hand with the CLI verbs and the honest table below:

| # | Step | How | Status |
|---|---|---|---|
| 1 | Seed the world | `node dev/seed.mjs` | ✅ live |
| 2 | Inspect it | `node plugins/playbook-jupi/shared/playbook.mjs pb-list-dossiers` · `pb-get-stages` · `pb-list-entries` | ✅ live |
| 3 | Plan: 2 [BR] decisions gate all 5 dossiers | `/playbook-jupi:act-or-decide` (start with `--dry-run` — classifies and reports, writes nothing) | ✅ live (TECH-489/491/492) |
| 4 | Settle as Claire, rule written, drafts land in the dev Gmail | settle in the `test` workspace, then `/playbook-jupi:act-post-decision` (already shipped) executes the chosen option | ✅ live |
| 5 | Inject a prospect reply | open a file in [`mirror/scenarios/`](mirror/scenarios/), send its mail (sender persona, subject, body) from your external mailbox **to the dev mailbox** — reply in-thread when a thread exists, else send it standalone as the scenario specifies | ✅ live (the mail lands, visible in Gmail) |
| 6 | Attach: inbound → its dossier, stage advances | inbound-watch rewrite | ⏳ TECH-487 (until then: `pb-set-stage <id> reply-to-handle` by hand) |
| 7 | Classify + next step vs the scenario's "expected engine behavior" block | the planner's inbound path: tripwires first, then the residue test, out-of-script as a first-class outcome | ✅ live (TECH-489/491/492) |
| 8 | Reset and replay | `node dev/reset.mjs` → `node dev/seed.mjs` → identical world | ✅ live |

The **< 30 min replay** target: steps 1–2–5–6(hand)–8 today; the full 1→8 loop as TECH-487/489 land —
each of those PRs must demo on this bench and flips its row to ✅.

## Reset semantics

`node dev/reset.mjs` purges **everything the bench tenant owns** in Neon (dossiers, entries, cursors,
frontier, run records — actions cascade). It does **not** touch the Jupi `test` workspace (leftover
decisions there are harmless, per the evals convention) nor the dev mailbox (clean threads by hand
when they get in the way — the bench never automates mail deletion). Both scripts are idempotent;
re-seeding never resets a dossier's stage (`pb-create-dossier`'s guarantee), so a mid-cycle re-seed
refreshes descriptions without losing progress — full rewind is always reset → seed.

## Rules when touching the bench

- **Zero real entities** in anything committed — the mapping and the canonical grep list live in a
  private comment on TECH-483 (deliberately not in this public repo); run that grep over `dev/`
  before any PR touching it.
- **Never commit** `.playbook-jupi/` (gitignored), the dev mailbox address, or any output derived
  from real pilot documents.
- The bench writes only under its tenant, its workspace, its mailbox — if you catch a command about
  to do otherwise, that's a bug in the bench, file it.

## Troubleshooting

- `Neon driver not installed` → `bash plugins/playbook-jupi/shared/ensure-deps.sh` (Node ≥ 18 required).
- `no Neon connection string` / placeholder errors → fill `.playbook-jupi/config.local.json` (step 3).
- `bench refuses tenant '…'` → the guard working as intended: bench commands only run under a
  `dev-`/`eval-` tenant; fix `jupiUserId` in the local config, never the guard.
- `SELECT` hangs / egress errors → Neon is HTTPS/443 via the serverless driver; if a sandbox blocks
  it, allowlist `*.neon.tech` (same fix as the proactive setup's step 1).
- `Group test not found` → the Jupi `test` workspace isn't reachable from this account — re-run the
  human step 3 probe before blaming the bench.
