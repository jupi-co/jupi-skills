# Spec — skill traces via a Jupi ingest endpoint

Status: ready to implement
Scope: `plugins/jupi-skills/hooks/` + `decide/apps/backend`
Related: [OBSERVABILITY.md](OBSERVABILITY.md), [skill-usage-report.py](skill-usage-report.py)

## 1. Decisions taken

| # | Decision |
|---|---|
| 1 | **Customer-ready build.** Ingest endpoint is unauthenticated, protected by strict payload validation and rate limits. |
| 2 | **Context injection** for correlation: the hook prints the trace id, Jupi MCP tools accept an optional `traceId`. |
| 3 | `traceId` **is added** to the public tool input schemas. |
| 4 | `userId` on Langfuse traces is real user identity from the OAuth `sub`. Accepted; already true today. |
| 5 | **One trace per turn**, not per skill invocation. |
| 6 | **Skills are their own span level**, between the turn and its MCP calls. |
| 7 | Prompt text is **always sent**. One code path, no auth branch — abuse is handled by install linking (§2). |

### Why per-turn (5)

Per-invocation traces would exist only when a skill fires, so Langfuse would
never see the turns where nothing fired and **recall would be uncomputable** —
the entire point of this layer. Per-turn also captures ordering when two skills
fire, and opens from `UserPromptSubmit`, whose stdout reaches model context.

### Why skills need their own level (6)

Inferring "the skill fired" from its MCP calls misses **a skill that fires and
calls nothing** — `search-decisions` finding nothing, or failing before it
reaches the server. Without a skill span that case is indistinguishable from
never firing, which is precisely the distinction being measured. The span also
gives per-skill latency and lets one turn's two skills be told apart.

## 2. Prompt text and install linking (7)

`user_input` (first 2000 chars of the prompt) is sent on every `open`, with no
auth branch. It is the highest-value field here — it is what lets you read *why*
a skill did or didn't fire rather than infer it from a boolean.

### 2.1 The gap this leaves

An open endpoint accepting free text is a place anyone can write arbitrary
content into your Langfuse: spam, storage cost, and strings your team later
reads. And **the hook asserts no identity** — it carries only `install_id`, which
the client generates. There is no user on that request to check.

### 2.2 Install linking — the mechanism that makes the check real

A user only becomes knowable when an **authenticated MCP call** arrives carrying
the same `traceId`. That call has an OAuth `sub`. So:

1. `open` arrives with an unknown `install_id` → accept, store as **unlinked**,
   under a tight per-IP quota.
2. An authenticated MCP call arrives with a `traceId` belonging to that install →
   record `install_id → userId`. The install is now **linked**.
3. Linked installs get the normal quota. Unlinked installs that produce no
   authenticated call within 24h are purged and their IP quota tightened.

An `install_id` is client-chosen and forgeable, so it is a grouping key, never a
security boundary — linkage is what carries trust, and only the OAuth `sub`
establishes it.

### 2.3 The trap to avoid

Do **not** gate persistence on linkage. The turns worth the most are the ones
where no skill fired and therefore no MCP call happened — an install that is
genuinely quiet looks exactly like an unlinked one for as long as it stays quiet.
Discarding unlinked traces would delete the denominator and silently restore the
0%-recall illusion this whole layer exists to dispel. Quarantine and rate-limit
them; do not drop them.

### 2.4 Two standing rules

- **Treat `user_input` as untrusted** wherever it is later displayed or fed to a
  model. It arrives unauthenticated, so it is attacker-controllable by
  construction — escape it in any UI, and never let it reach a prompt as
  instructions.
- **Disclose it.** Prompt text is broader than what customers already send you:
  `TraceMcpTool` records decisions they chose to log, whereas this is everything
  typed in the turn. That belongs in the privacy policy and the plugin README in
  plain words.

## 3. What already exists

`decide/apps/backend/src/monitoring/traceMcpTool.decorator.ts` wraps all 16 MCP
tools with `startActiveObservation(toolName, …)`, recording input, output,
`level: 'ERROR'` + `statusMessage` on failure, and `mcpClientId`/`mcpClientName`
metadata. `LangfuseService` runs `@langfuse/otel`'s span processor under `NodeSDK`.

MCP calls are **already traced** — each merely starts its own root trace for lack
of a parent. The work is parenting, not instrumenting.

## 4. Trace shape

```
trace  "turn"                       tags: ideation, nudged, client, plugin
├── event  turn_started
├── span   skill:search-decisions            ← hook-reported
│   └── obs   search-decisions-tool          ← existing decorator, now parented
├── span   skill:log-decision
│   ├── obs   create-decision-tool
│   └── obs   add-decision-options-tool
└── event  turn_ended                        scores: fired, reached_write, nudge_converted
```

A skill span with no child observation is the signal that was previously
invisible: fired, did nothing.

## 5. Client — hooks

Three calls, one endpoint, discriminated by `event`.

### 5.1 `open` — `UserPromptSubmit` (in `ideation_nudge.py`)

```jsonc
POST /v1/skill-traces
{
  "v": 1, "event": "open",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "install_id": "8f14e45fceea167a",
  "plugin_version": "489e80e",
  "client": "claude_code",
  "started_at": "2026-07-29T10:14:02.511Z",
  "ideation": true,
  "nudged": true,
  "user_input": "…"        // first 2000 chars of the prompt
}
```

Emitted on **every** turn, including turns where no skill fires — that is the
recall denominator. Then, appended to the nudge output:

```
[jupi-skills] trace: 4bf92f3577b34da6a3ce929d0e0e4736 — pass as `traceId` on any Jupi MCP tool call this turn.
```

POST **after** the nudge prints, in its own `try/except`. The nudge's fail-open
contract is unchanged.

### 5.2 `skill` — `PostToolUse`, matcher `Skill` (new `skill_probe.py`)

```jsonc
{
  "v": 1, "event": "skill",
  "trace_id": "…", "install_id": "…",
  "skill": "search-decisions",
  "at": "2026-07-29T10:14:09.204Z"
}
```

Ignore any skill outside the tracked three — other plugins' skills are none of
our business and must not be transmitted. `trace_id` is read from the turn state
file written at open.

### 5.3 `close` — `Stop` (new `close_probe.py`)

```jsonc
{
  "v": 1, "event": "close",
  "trace_id": "…", "install_id": "…",
  "ended_at": "…", "duration_ms": 29371,
  "outcome": "completed"        // completed | interrupted | error
}
```

`Stop` fires on interrupt and error as well as clean completion, so `outcome` is
reported rather than inferred. The 30-minute expiry (§6.4) remains only for
genuinely lost turns, e.g. a crashed client.

### 5.4 Client rules

- Never send file paths, tool arguments, or tool responses. Prompt text is sent,
  truncated to 2000 chars.
- `install_id`: random, generated once, `0600` at
  `~/.claude/jupi-skills/install.json`. Not a user id, not derived from one.
- Turn state at `~/.claude/jupi-skills/turn-<hashed-session>.json`, keyed per
  session so concurrent worktrees don't collide. Deleted on close; sweep files
  older than 7 days at open.
- Gate on `JUPI_SKILLS_TELEMETRY=on` **and** `JUPI_TELEMETRY_URL`. No default
  endpoint in the plugin.
- 2s timeout, fire-and-forget, silent failure.

## 6. Backend

### 6.1 Validation — reject with 400, never partially accept

- `v` = `1`; `event` ∈ `open` | `skill` | `close`
- `trace_id` `/^[0-9a-f]{32}$/`, not all-zero; `install_id` `/^[0-9a-f]{16}$/`
- `plugin_version` `/^[0-9a-f]{7,40}$/`
- `client` ∈ `claude_code` | `claude_ai` | `cowork` | `cursor`
- `skill` ∈ `search-decisions` | `log-decision` | `submit-decision`
- `ideation`, `nudged` boolean; timestamps ISO-8601 UTC within ±5 min
- `duration_ms` integer 0…86_400_000; `outcome` ∈ `completed` | `interrupted` | `error`
- `user_input` — string, ≤ 2000 chars, valid UTF-8, control characters stripped.
  Truncate rather than reject on length; a long prompt is not an error.
- **unknown fields rejected**; body ≤ 8 KB

### 6.2 Ordering and abuse

- `skill` or `close` for an unknown `trace_id` → 404, do not create implicitly.
  Otherwise the open endpoint is a trace-creation primitive for anyone.
- Duplicate `close` → 409.
- Rate-limit per `install_id` **and** per IP. `install_id` is client-generated
  and trivially forged, so it is a grouping key, not a security boundary — see
  §2.2 for what actually carries trust.
- Unlinked installs (§2.2) get a tight per-IP quota; linked installs the normal
  one. Quarantine, never discard — §2.3.
- Cap concurrent open traces per `install_id`; cap skill events per trace.

### 6.3 Parenting

Store `{trace_id, install_id, root_span_id, skill_spans[], opened_at}`, TTL 30 min.

Add to each input schema in `packages/types/src/mcp/*.schema.ts`:

```ts
traceId: z.string().regex(/^[0-9a-f]{32}$/).optional()
```

Two verified facts shape this:

- **No schema uses `.strict()`**, so Zod *strips* unknown keys rather than
  rejecting them. An undeclared `traceId` would be silently removed in
  validation and the decorator, reading parsed input, would never see it. The
  edits are mandatory — by stripping, not rejection, so the failure is silent.
- **All 9 input schemas end in `.refine()`**, making them `ZodEffects`, which has
  no `.extend()`. A registration-time helper does not work; `traceId` goes in
  each inner `z.object({…})` before its `.refine()`.

9 files, one field each. The 16 `@TraceMcpTool` sites share these schemas.

In `TraceMcpTool`: when `input.traceId` matches an open trace, parent the
observation under that trace's **most recent skill span**, falling back to the
trace root if none. Otherwise fall through unchanged — everything recorded today
stays identical, only the parent moves.

### 6.4 Langfuse model

- **trace** `name: "turn"`, `sessionId: trace_id`, `userId` from OAuth `sub`,
  `tags: ["plugin:jupi-skills", "client:<client>", "ideation:<bool>", "nudged:<bool>"]`
- **span per skill** `name: "skill:<skill>"`
- **observations** MCP calls, parented under their skill span
- **scores** at close: `fired` 0/1, `reached_write` 0/1, `nudge_converted` 0/1
  (on `nudged: true` only)
- Unclosed after 30 min → `outcome: abandoned`

Recall is one query: traces tagged `ideation:true`, grouped by `fired`.

## 7. Acceptance criteria

- [ ] Every turn produces a trace, **including turns where no skill fires**
- [ ] A skill that fires and makes no MCP call still appears as a skill span —
      the case this design exists to catch
- [ ] MCP calls nest under their skill span, not the trace root
- [ ] A call with no `traceId` records unparented, today's behaviour unchanged
- [ ] An install that produces traces but never an authenticated MCP call is
      **retained**, not discarded — §2.3, the denominator depends on it
- [ ] An authenticated MCP call links `install_id → userId`, and the install
      moves to the normal quota
- [ ] `user_input` over 2000 chars is truncated, not rejected
- [ ] Stored `user_input` is escaped wherever it is displayed — it is
      attacker-controllable by construction
- [ ] `skill`/`close` for an unknown `trace_id` → 404; duplicate `close` → 409
- [ ] Malformed payloads (bad hex, unknown field, stale timestamp, oversize)
      each 400
- [ ] `outcome` is `interrupted` on Ctrl-C and `error` on failure — not inferred
- [ ] Skills outside the tracked three are never transmitted
- [ ] With `JUPI_SKILLS_TELEMETRY` unset, no request and the nudge unchanged
- [ ] A broken emitter does not stop the nudge printing
- [ ] A 2s endpoint stall does not delay the turn

## 8. Build order

1. Endpoint + store + validation. Exercise with `curl`; no client yet.
2. `TraceMcpTool` parenting + `traceId` on the 9 schemas.
3. `ideation_nudge.py` open + context line.
4. `skill_probe.py`, `close_probe.py`, `hooks.json`.
5. Install linking + quotas (§2.2). Can follow the first traces — it is an
   abuse control, not a correctness one.
6. Run a week, then compare against `skill-usage-report.py --since <date>`. The
   two should broadly agree on skill fires; disagreement means one is wrong, and
   finding out which is worth more than either number alone.

## 9. Remaining unknown

**Concurrent turns sharing an `install_id`** (two worktrees at once). The
explicit `traceId` handles correlation; the per-session state file (§5.4) handles
the client side. Verify once both exist rather than designing further for it.
