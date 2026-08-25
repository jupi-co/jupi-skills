# The two routine prompts — template + the rule that governs them

Read this in the scheduling step, before creating or updating either routine. The governing
rule is proactive-setup's, unchanged: **the prompt carries what setup owns; a store holds only
what a run writes.** A prompt is written once and read forever, so it may carry only things that
stay true indefinitely — budgets, refs, thresholds pass; dates, counts, "currently", last run's
numbers never do (they fail silently: a routine repeating a stale caveat reads exactly like one
reasoning correctly).

## Boot: materialize, don't hunt — into BOTH folders

The first thing a routine does is write the config it carries to
`./.playbook-jupi/config.local.json` **and** `./.proactive-jupi/config.local.json` in its own
working directory. Both, always: `playbook.mjs` walks either, but the parity-locked `db.mjs`
(gating, cursors, run records, the verbatim-copied skills) only walks `.proactive-jupi/` —
found live on the bench; a routine that writes one copy stalls on its first `db.mjs` call.
Both files are scratch, derived from the prompt, gone with the container — never state.

## Why two routines (§13)

Not one wake-up — the funnel knows what it waits for, and each class has its own latency:
a settled decision must be carried out in **minutes** (perceived trust), a reply within the
business hour, a due follow-up the same day, bookkeeping weekly. So: a cheap **catchup**
sentinel on business hours, and one **daily** full sweep. Human entry points and the future
finalize-webhook invoke the same idempotent paths — the cron is the safety net, never the gate.

## The catchup prompt (sentinel — business hours, 30–60 min cadence)

```
Run Playbook-Jupi's catchup routine. You are running unattended — never wait for input:
if something is missing, close the run record saying so and stop.

## Config (carried — write it to ./.playbook-jupi/config.local.json AND
## ./.proactive-jupi/config.local.json before anything else)
{
  "jupiWorkspace": "<slug>", "jupiUserId": "<id>", "neonConnString": "<conn>",
  "watchedSource": "<addr>", "dossierSource": "<ref>", "projectionTarget": "<path>",
  "inboundStage": "<stage>", "crawlWindowDays": <n>, "leaseMinutes": <n, default 10>,
  "guardrails": <the guardrails block, verbatim from config.local.json>
}

## Run
1. Write both config files. THE LEASE, before any work: for each routine name below, run
   node "${CLAUDE_PLUGIN_ROOT}/shared/db.mjs" run-last <name> 1
   If any run is still 'running' and started less than leaseMinutes ago, STOP — output one
   line ("live run in progress, yielding") and open no run record. (A stalled run — running
   but older than leaseMinutes — does NOT hold the lease; say you are taking over from it.)
2. Open your run record: db.mjs run-open catchup. Read run-last catchup 1 — if the previous
   run failed or stalled, open your report by saying so.
3. THE CHEAP NO-OP CHECK — two reads, then exit if quiet:
   a. db.mjs list-blocked → collect gating decision ids → get-decision each: any newly
      FINALIZED?
   b. One filtered search on the watched source newer than the backlog cursor: any new
      inbound?
   Neither → close the run (run-close <id> ok - "no-op: nothing settled, nothing inbound")
   and STOP. This exit must stay cheap — boot plus these two reads, nothing else.
4. When there IS work: run act-post-decision (carries out what was settled, unblocks),
   then refresh-backlog (attaches the new inbound), then act-or-decide restricted to the
   dossiers just unblocked or just attached — not the full sweep; the daily owns that.
5. Close the run record honestly (ok | degraded '[{"what","cost"}]' | failed - "<why>").
   Never close 'ok' over a tool that didn't answer.
```

## The daily prompt (full sweep)

```
Run Playbook-Jupi's daily routine. You are running unattended — never wait for input:
if something is missing, close the run record saying so and stop.

## Config (carried — write it to ./.playbook-jupi/config.local.json AND
## ./.proactive-jupi/config.local.json before anything else)
<same carried config block as the catchup — keep the two identical>

## Run
1. Write both config files. Same lease check as the catchup (run-last on both names;
   yield to a live run younger than leaseMinutes). Then run-open daily; read run-last
   daily 1 and mention a bad previous run.
2. act-post-decision — carry out everything settled since last run.
3. refresh-backlog — full sweep of the watched source from the cursor.
4. act-or-decide — the full planner pass over every open dossier: next steps, due
   follow-ups (timing entries), decisions, handoff checklist.
5. On Fridays only: the playbook review — re-render the projection from the rows, and
   report the playbook's state in the run summary: holes still open, entries by status,
   evidence tallies, anything suspended, codifications ripe by recurrence.
6. Close the run record honestly, as above.
```

## Naming — load-bearing, and it must not collide with proactive's routines

The scheduler's reconcile matches on the exact name (the API gives no stable key). Fixed
strings, no cadence or version in them — and distinct from the proactive pair, which may run
on the same account:

- `Playbook-Jupi — catchup`
- `Playbook-Jupi — daily`

One-line `description` field (required, plain language, phrased to match the cron you set):
- catchup → "Through the workday, Jupi carries out what you've settled and picks up new
  replies within the hour."
- daily → "Once a day, Jupi runs the whole playbook: follow-ups due, next steps per dossier,
  and anything that needs your call."

## Rotation

`neonConnString` is the one secret in a prompt and the one rotation point: rotating it means
re-running the bootstrap's scheduling step, which updates both routines in place — never a
hand-edit of two task definitions.
