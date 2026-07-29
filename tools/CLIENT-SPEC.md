# Spec — client hooks for skill traces

Status: ready to implement
Scope: `plugins/jupi-skills/hooks/`
Server: [decide#3928](https://github.com/jupi-co/decide/pull/3928) — `POST /v1/skill-traces`
Related: [HOOK-TELEMETRY-SPEC.md](HOOK-TELEMETRY-SPEC.md) (joint design), [OBSERVABILITY.md](OBSERVABILITY.md)

This spec is written against the merged server contract, not the earlier joint
draft. Where the two disagree, the server wins — it exists.

## 0. Deltas from the joint spec

Anyone working from `HOOK-TELEMETRY-SPEC.md` must apply these:

| Changed | Now |
|---|---|
| `install_id` | **Removed entirely.** Sending it is a 400 — unknown fields are rejected. |
| Success status | **202**, not 200. |
| Duplicate `open` | **409** (the joint spec didn't cover it). |
| Oversize body | **413**, and *not* the JSON error envelope — it comes from express's `finalhandler`. |
| `user_input` | Optional. Server sanitises control chars and truncates to 2000 **code points**. |
| Per-install quota | Gone. Server evicts the oldest turn instead of refusing a new one. |
| `plugin_version` | **Optional.** Omit it when no sha is resolvable; the turn still counts. |
| `client` | **Not an enum** — any name matching `/^[a-z0-9][a-z0-9_.-]{0,31}$/i`. Send `unknown` rather than guessing. |
| Timestamp skew | **No longer bounded.** A skewed clock no longer silently zeroes a machine's telemetry. |
| `v` | Accepts `1 … CURRENT`. Older clients keep reporting after a v2 ships; newer ones are rejected. |

## 1. Files

```
plugins/jupi-skills/hooks/
  telemetry.py          NEW  — config, trace id, turn state, POST. Only network caller.
  ideation_nudge.py     EDIT — emits `open`, prints the trace line
  skill_probe.py        NEW  — PostToolUse(Skill) → `skill`
  close_probe.py        NEW  — Stop → `close`
  hooks.json            EDIT — registers the two new hooks
```

`telemetry.py` is the only module that reads config or touches the network. The
probes decide *what* to report; it decides *whether and how* to send.

## 2. The wire contract

`POST {JUPI_TELEMETRY_URL}/v1/skill-traces`, `Content-Type: application/json`,
no auth header. Three shapes on one route, discriminated by `event`.

### 2.1 `open`

```jsonc
{
  "v": 1,
  "event": "open",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",   // 32 lowercase hex, not all-zero
  "plugin_version": "489e80e",                       // OPTIONAL, /^[0-9a-f]{7,40}$/
  "client": "unknown",                               // /^[a-z0-9][a-z0-9_.-]{0,31}$/i
  "started_at": "2026-07-29T10:14:02.511Z",          // ISO-8601 UTC
  "ideation": true,
  "nudged": true,
  "user_input": "…"                                  // optional, ≤2000 code points
}
```

### 2.2 `skill`

```jsonc
{
  "v": 1,
  "event": "skill",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "skill": "search-decisions",     // search-decisions|log-decision|submit-decision ONLY
  "at": "2026-07-29T10:14:09.204Z"
}
```

### 2.3 `close`

```jsonc
{
  "v": 1,
  "event": "close",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "ended_at": "2026-07-29T10:14:31.882Z",
  "duration_ms": 29371,            // integer, 0 … 86_400_000
  "outcome": "completed"           // completed|interrupted|error
}
```

`abandoned` and `evicted` are **server-side outcomes**. Never send them.

### 2.4 Response handling

| Status | Meaning | Client action |
|---|---|---|
| 202 | accepted | mark turn reportable |
| 400 | malformed — a client bug | **do not retry**; drop the turn |
| 404 | `skill`/`close` for an unopened trace | **do not retry**; drop the turn |
| 409 | duplicate `open` or `close` | **do not retry**; already recorded |
| 413 | body too large — not a JSON envelope | **do not retry**; truncate harder |
| 5xx / timeout | transient | drop silently; **no retry queue** |

**Nothing is ever retried.** A retry on `open` earns a 409, and the value of any
single turn is far below the cost of a hook that lingers.

## 3. Behaviour

### 3.1 `open` — `UserPromptSubmit`, inside `ideation_nudge.py`

Order matters:

1. Read stdin, classify with the existing `_PATTERN`.
2. **Print the nudge** if it matches — unchanged, first, always.
3. If telemetry is off, stop here.
4. Generate `trace_id = os.urandom(16).hex()`.
5. Write turn state (§4.2).
6. POST `open`. On non-202, mark the turn **not reportable** and record that.
7. Print the trace line.

The nudge prints before any of this and inside its own path, so the existing
fail-open contract is untouched: telemetry cannot delay or suppress it.

The trace line, appended to stdout:

```
[jupi-skills] trace: 4bf92f3577b34da6a3ce929d0e0e4736 — pass as `traceId` on any Jupi MCP tool call this turn.
```

Print it **only after a 202**. A trace id the server never opened would be
passed to MCP tools that then find no turn to nest under — noise, not data.

`user_input` is the raw prompt, truncated client-side to 2000 code points
(`''.join(list(prompt)[:2000])` — slicing code points, not UTF-16 units, so a
surrogate pair is never split). The server truncates too, but the 8 KB body cap
is enforced on the **wire bytes**: a long prompt would 413 before the server's
own truncation ever ran.

### 3.2 `skill` — `PostToolUse`, matcher `Skill`, in `skill_probe.py`

1. Read `tool_input.skill` from the hook payload, e.g. `jupi-skills:log-decision`.
2. Take the suffix after `:`.
3. **If it is not one of the three tracked skills, exit 0 silently.** Other
   plugins' skill names must never leave the machine — and the server would 400
   anyway.
4. Load turn state. No state, or turn not reportable → exit 0.
5. POST `skill` with `at` = now.

Cap at 20 skill events per turn client-side, matching the server's
`MAX_SKILL_EVENTS_PER_TURN`, so a runaway loop doesn't spend the turn's budget
on requests that will be dropped anyway.

### 3.3 `close` — `Stop`, in `close_probe.py`

1. Load turn state. Missing or not reportable → exit 0.
2. `duration_ms` = now − `started_at`, clamped to 0 … 86_400_000.
3. POST `close`.
4. **Delete the state file regardless of the response.** This is what makes
   close idempotent: a second `Stop` finds no state and stays quiet instead of
   collecting a 409.

`outcome` mapping is the one thing needing verification — see §6.1. Until then,
send `completed`.

## 4. `telemetry.py`

### 4.1 Configuration

| Variable | Required | Meaning |
|---|---|---|
| `JUPI_SKILLS_TELEMETRY` | yes | `on` enables. Anything else, including unset, disables. |
| `JUPI_TELEMETRY_URL` | yes | Base URL. No default ships in the plugin. |

Both must be present or every hook is a no-op. A plugin that phones home to a
baked-in address on install is not something we ship.

### 4.2 Turn state

`~/.claude/jupi-skills/turn-<sha256(session_id)[:16]>.json`, mode `0600`:

```json
{"trace_id": "…", "started_at": "…", "reportable": true, "skill_events": 0}
```

Keyed by session so concurrent worktrees never collide. Written at `open`,
deleted at `close`. Sweep files older than 24h during `open` — a crashed client
leaves orphans, and the directory must not grow without bound.

`reportable: false` records that `open` failed, so the later probes skip
straight out instead of earning a 404 each.

### 4.3 Transport

- `urllib.request` from the stdlib. **No third-party dependencies** — the hook
  runs on machines whose Python environment we do not control.
- 2s timeout, total.
- Every exception swallowed. A hook that raises is a hook that breaks someone's
  session.
- Never write to stderr on failure. A visible traceback on every prompt because
  a telemetry endpoint is down is worse than no telemetry.

### 4.4 `plugin_version`

Optional, and must match `/^[0-9a-f]{7,40}$/` when sent — a git sha, not `1.2.0`.

Claude Code installs plugins to a path ending in the commit sha:

```
~/.claude/plugins/cache/jupi-skills/jupi-skills/7ff21ab9bf26
```

So derive it from `basename(CLAUDE_PLUGIN_ROOT)` when that basename matches the
pattern. When it does not — a local checkout, a dev symlink — fall back to a
`VERSION` file in the plugin root.

If neither yields a valid sha, **omit the field and send the turn anyway**. The
server made it optional exactly so a dev install still counts; a turn of unknown
build is worth far more than no turn. Never substitute a placeholder — a
fabricated sha silently poisons every per-version comparison later.

### 4.5 `client`

Any name matching `/^[a-z0-9][a-z0-9_.-]{0,31}$/i` — deliberately not an enum,
because a hook cannot detect its surface.

**Default to `unknown`.** A confidently wrong `claude_code` on every Cowork turn
is worse than an honest `unknown`, because nothing would ever reveal it as
wrong. `$JUPI_TELEMETRY_CLIENT` overrides it where the surface is known — a
wrapper that only ever runs under one of them.

## 5. `hooks.json`

The existing `UserPromptSubmit` block is unchanged — `ideation_nudge.py` gains
the open internally. Two blocks are added:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/ideation_nudge.py\"",
            "timeout": 10,
            "statusMessage": "Checking for prior Jupi decisions…"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/skill_probe.py\"",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/close_probe.py\"",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

No `statusMessage` on the probes — they must be invisible in normal use.

## 6. Verify before building

### 6.1 `Stop` payload — how to tell `interrupted` from `error`

`Stop` fires on interrupt and error as well as clean completion, but whether the
payload distinguishes them is unconfirmed. Dump one:

```bash
# temporary Stop hook
cat >> /tmp/stop-payload.jsonl
```

Then run three sessions: clean, Ctrl-C, and one ending in an error. If no field
separates them, send `completed` always and note that `outcome` carries no
signal — better than guessing wrong and reporting `error` for every interrupt.

### 6.2 `client` detection

Same method: dump a `UserPromptSubmit` payload and its environment from Claude
Code and from Cowork, and diff. If nothing distinguishes them, `client` needs an
env var the user sets, or it stays hardcoded and unreliable.

### 6.3 Does `UserPromptSubmit` fire more than once per turn?

If it can — a resumed session, a queued prompt — a second `open` on the same
`trace_id` earns a 409, and a *new* `trace_id` silently orphans the first turn.
Generating the id fresh per invocation (§3.1) is correct either way, but confirm
so the 409 handling is deliberate rather than accidental.

## 7. Acceptance criteria

- [ ] With `JUPI_SKILLS_TELEMETRY` unset: no request, no state file, and the
      nudge output is byte-for-byte what it is on `main`
- [ ] A prompt with telemetry on: `open` returns 202 and the trace line prints
- [ ] `open` failing (endpoint down, 400, 5xx): **the nudge still prints**, no
      trace line, and the later probes make no request at all
- [ ] `telemetry.py` raising on import does not stop the nudge printing
- [ ] Invoking `search-decisions` sends exactly one `skill` event
- [ ] Invoking a **non-Jupi** skill sends nothing — no other plugin's skill name
      leaves the machine
- [ ] A turn with no skill invocation still produces `open` + `close` — this is
      the denominator, and it is the criterion most likely to be quietly broken
- [ ] Two `Stop`s for one turn produce one `close`, not a 409
- [ ] A 3000-char prompt is truncated client-side; the request is not 413
- [ ] An emoji at position 1999 is not split into a lone surrogate
- [ ] No payload contains `install_id`
- [ ] An endpoint stalling for 10s delays the turn by at most ~2s
- [ ] Concurrent sessions in two worktrees keep separate state files
- [ ] No `plugin_version` is ever sent that isn't a real sha

## 8. Build order

1. `telemetry.py` — config, state, POST. Point `JUPI_TELEMETRY_URL` at the
   preview deploy and drive it from a scratch script before any hook exists.
2. §6.1 and §6.2 payload dumps.
3. `ideation_nudge.py` open + trace line.
4. `skill_probe.py`, `close_probe.py`, `hooks.json`.
5. End-to-end against preview, following the PR's test list — especially its
   case 2 (`open` → `close` with no skill), which is the denominator.
6. Compare a week of Langfuse traces against
   `skill-usage-report.py --since <date>`. Broad agreement on skill fires;
   disagreement means one of them is wrong.

## 9. Release blockers, not code

- Privacy-policy and plugin-README disclosure that prompt text is captured. This
  is broader than what customers already send: existing tracing records
  decisions they *chose* to log, whereas this is everything typed in the turn.
- The PR's own note that `SCHEDULES_ENABLED` and the `install_id` removal must
  be settled server-side before the client can be trusted against production.
