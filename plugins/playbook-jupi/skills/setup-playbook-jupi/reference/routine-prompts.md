# The two routine prompts — template + the rule that governs them

Read this in the scheduling step, before creating or updating either routine. The governing
rule is proactive-setup's, unchanged: **the prompt carries what setup owns; a store holds only
what a run writes.** A prompt is written once and read forever, so it may carry only things that
stay true indefinitely — budgets, refs, thresholds pass; dates, counts, "currently", last run's
numbers never do (they fail silently: a routine repeating a stale caveat reads exactly like one
reasoning correctly).

## Boot: materialize the config — no secret in it, one folder

The first thing a routine does is write the config it carries to
`./.playbook-jupi/config.local.json` in its own working directory, so every invoked skill's
walk-up finds it. **The config holds no secret**: data access goes through the `pb-*` tools on
the installed Jupi connector, authenticated by the connector itself — nothing in the prompt can
leak a credential, and there is nothing to rotate. The file is scratch, derived from the prompt,
gone with the container — never state.

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

## Config (carried — write it to ./.playbook-jupi/config.local.json before anything else;
## it contains no secret)
{
  "jupiWorkspace": "<slug>",
  "watchedSource": "<addr>", "dossierSource": "<ref>", "projectionTarget": "<path>",
  "inboundStage": "<stage>", "crawlWindowDays": <n>, "leaseMinutes": <n, default 10>,
  "guardrails": <the guardrails block, verbatim from config.local.json>
}

## Run
1. Write the config file. Load the pb-* tools from the installed Jupi connector via
   ToolSearch. THE LEASE, before any work: for each run name — catchup, daily, go,
   process-reply (the human entry points hold the same lease) — call pb-run-last (1).
   If any run is still 'running' and started less than leaseMinutes ago, STOP — output one
   line ("live run in progress, yielding") and open no run record. (A stalled run — running
   but older than leaseMinutes — does NOT hold the lease; say you are taking over from it.)
2. Open your run record: pb-run-open (catchup). Read pb-run-last (catchup, 1) — if the
   previous run failed or stalled, open your report by saying so.
3. THE CHEAP NO-OP CHECK — two reads, then exit if quiet:
   a. pb-list-blocked → collect gating decision ids → get-decision each: any newly
      FINALIZED?
   b. One filtered search on the watched source newer than the backlog cursor: any new
      inbound?
   Neither → close the run (pb-run-close, ok, "no-op: nothing settled, nothing inbound")
   and STOP. This exit must stay cheap — boot plus these two reads, nothing else.
4. When there IS work: run act-post-decision (carries out what was settled, unblocks),
   then refresh-backlog (attaches the new inbound), then act-or-decide restricted to the
   dossiers just unblocked or just attached — not the full sweep; the daily owns that.
5. Close the run record honestly (pb-run-close: ok | degraded [{"what","cost"}] |
   failed "<why>"). Never close 'ok' over a tool that didn't answer.
6. When step 4 ran, end with the user's version of the report — ONE stitched narrative
   (rules: act-or-decide's reference/REPORTING.md, §the user's version: assistant voice,
   the user's language, no engine vocabulary): what moved, decisions waiting (with links),
   the over-to-you checklist, what was left. You are unattended, so the full technical
   run logs DO render in the narration above it — this transcript is the only durable
   record — and the summary stays complete against the run's facts (every dossier
   touched, every open handoff, every cut). (A no-op exit at step 3 needs none of this —
   its one line is the report.)
```

## The daily prompt (full sweep)

```
Run Playbook-Jupi's daily routine. You are running unattended — never wait for input:
if something is missing, close the run record saying so and stop.

## Config (carried — write it to ./.playbook-jupi/config.local.json before anything else;
## it contains no secret)
<same carried config block as the catchup — keep the two identical>

## Run
1. Write the config file. Load the pb-* tools via ToolSearch. Same lease check as the
   catchup (pb-run-last on each name; yield to a live run younger than leaseMinutes).
   Then pb-run-open (daily); read pb-run-last (daily, 1) and mention a bad previous run.
2. act-post-decision — carry out everything settled since last run.
3. refresh-backlog — full sweep of the watched source from the cursor.
4. act-or-decide — the full planner pass over every open dossier: next steps, due
   follow-ups (timing entries), decisions, handoff checklist.
5. On Fridays only: the playbook review — re-render the projection from the rows, and
   report the playbook's state in the run summary: holes still open, entries by status,
   evidence tallies, anything suspended, codifications ripe by recurrence — and the
   ledger's open questions: every application still at outcome 'unknown'
   (pb-list-applications, outcome unknown), listed so the owner can answer in one
   message ("the <point> draft on <dossier>: as-is, edited, or dropped?"). You are
   unattended — LIST them, never guess an outcome.
   Also on Fridays, IF a memory connector is present: run update-brain once, full mode,
   bounded budget — the weekly refresh that keeps what Jupi knows about the people and
   companies in these dossiers from going stale. No connector → skip it silently; the
   playbook does not depend on it.
6. Close the run record honestly, as above.
7. End with the user's version of the report — ONE stitched narrative (rules:
   act-or-decide's reference/REPORTING.md, §the user's version: assistant voice, the
   user's language, no engine vocabulary): what moved, decisions waiting (with links),
   the over-to-you checklist, what was left. On Fridays the playbook review's findings
   join it in the same plain language (what's still open for you to settle, what got
   stronger, what I'm waiting to hear about). You are unattended, so the full technical
   run logs DO render in the narration above it — this transcript is the only durable
   record — and the summary stays complete against the run's facts (every dossier
   touched, every open handoff, every cut).
```

## Naming — load-bearing, and it must not collide with proactive's routines

The scheduler's reconcile matches on the exact name (the API gives no stable key). Fixed
strings, no cadence or version in them — and distinct from the proactive pair, which may run
on the same account:

- `Playbook-Jupi — catchup`
- `Playbook-Jupi — daily`

One-line `description` field (required, plain language, phrased to match the cron you set —
fill `<name>` from the reserved `playbook-name` entry at scheduling time; a rename refreshes
them on the next scheduling re-run):
- catchup → "Through the workday, Jupi carries out what you've settled on « <name> » and picks
  up new replies within the hour."
- daily → "Once a day, Jupi runs the whole « <name> » playbook: follow-ups due, next steps per
  dossier, and anything that needs your call."

## Nothing to rotate

The prompts carry no secret — access is the connector's OAuth, revoked and restored on the
Jupi side, never by editing a routine. Re-running the bootstrap's scheduling step is only ever
about *content* (cadence, config values, the playbook's name in the descriptions), and it
updates both routines in place — never a hand-edit of two task definitions.
