---
name: go
description: >-
  Playbook-Jupi's catch-up-now button — an accelerator, never a gate (the scheduled catchup
  guarantees progress anyway; this makes the common case instant). It has NO logic of its own: it
  plays the exact catchup path — carry out what was just settled (act-post-decision), attach any new
  inbound (refresh-backlog), then re-plan only the dossiers just unblocked or just awakened
  (act-or-decide, restricted). Idempotent by construction — running it right after a finalization,
  or twice in a row, double-executes nothing. Use when the user wants effects now: "/go", "go",
  "carry out what we just settled", "I finalized — apply it", "catch up now". Not for: a full
  planner sweep (act-or-decide), one specific reply (process-reply), or setup (setup-playbook-jupi).
disable-model-invocation: false
---

# go — carry out what we just settled, now

A thin trigger over the catchup path. **You add no reasoning of your own** — every judgment
belongs to the skills you invoke; your job is sequence, lease, and run record.

1. **The lease** (same rule as the routines — `reference/routine-prompts.md` in
   `setup-playbook-jupi`): `db.mjs run-last <name> 1` for each of `catchup`, `daily`, `go`,
   `process-reply`. A live run younger than `leaseMinutes` (config, default 10) → say "a run is
   already working — it will pick this up" and stop. A stalled one → take over, and say so.
2. `db.mjs run-open go` — the run record is what makes you visible to the lease and to `run-last`.
3. **The catchup path, exactly**: `act-post-decision` (everything FINALIZED since last run is
   carried out, dossiers unblocked) → `refresh-backlog` (new inbound attached) → `act-or-decide`
   **restricted to the dossiers just unblocked or just attached** — the daily owns full sweeps.
4. `db.mjs run-close <id>` honestly (`ok` | `degraded` | `failed`), then end with **one stitched
   user's version** of everything the invoked skills did (rules: act-or-decide's
   `reference/REPORTING.md`, §Composition — assistant voice, the user's language) — handoff
   checklist included. The skills' run logs stay in the narration, available on request.

Nothing here writes anything the invoked skills don't; a `--dry-run` or `--technical` request
passes through to `act-or-decide` untouched (`--technical` makes the run logs the final message —
the debugging channel).
