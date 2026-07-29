# Skill observability — implementation brief

Hand this to whoever builds the observability layer for `jupi-skills`. It states
the goal, the design decision already made, the three layers to build, and the
non-obvious gotchas that cost time if rediscovered from scratch.

## The question we're answering

Not "how many times did the skill run". The skills only pay off if they fire
**during the work they exist for**. So the metric that matters is trigger
quality:

| Metric | Definition | Where it's measured |
|---|---|---|
| **Recall** | of prompts that are ideation/strategy work, % where `search-decisions` fired | transcripts / hooks |
| **Precision** | of `search-decisions` fires, % that landed on real ideation | transcripts / hooks |
| **Funnel** | of skill invocations, % that reached a real Jupi MCP write | MCP server (authoritative) |
| **Nudge lift** | recall with the `ideation_nudge` hook active vs. without | hooks |

Recall is the one to optimize. A skill that never fires is worth nothing, and
model-judgment triggering under-fires on open-ended ideation — which is exactly
why `hooks/ideation_nudge.py` exists.

## Build order (decided)

1. **MCP server-side telemetry — do this first.**
   Every real outcome already hits the Jupi API. Add `source`, `client`, and
   `client_version` to the tool-call payloads and log them. Free, tamper-proof,
   needs zero user setup, and covers Claude Code *and* claude.ai *and* Cowork
   alike. Blind spot: only sees successes — a skill that loaded and got
   abandoned is invisible, which is what layer 2 is for.

2. **Transcript miner — already built.** See `tools/skill-usage-report.py`.
   Read-only, local, retroactive. This is the only layer that can measure the
   **negative case**: the user was clearly ideating and nothing fired. Run it
   before and after every trigger-wording change.

3. **Hooks — last, and opt-in only.** `PostToolUse` with matcher `Skill` fires
   on every invocation (`{"name":"Skill","input":{"skill":"jupi-skills:log-decision"}}`).
   Pair with `UserPromptSubmit` for the denominator and `SessionStart`/`SessionEnd`
   for sessionization. See the consent rules below before shipping this to anyone.

Deliberately **not** doing: asking the model to self-report usage from inside
`SKILL.md`. It's unreliable, the model forgets, and it burns context on every run.

## Gotchas found the hard way

These were all hit while building the miner. They apply to the hook layer too.

- **The MCP server prefix is not stable.** The same tool appears as
  `mcp__claude_ai_Jupi__search-decisions-tool`, `mcp__plugin_jupi_Jupi__…`, and
  `mcp__<connector-uuid>__…` depending on surface. **Match on the suffix after
  the last `__`**, never the full name. A UUID-prefixed filter silently
  under-counts by surface, which reads as "adoption is low on Cowork".

- **`user` transcript entries are not all user prompts.** They also carry tool
  results, slash-command expansions (`<command-name>`), injected skill bodies
  (`Base directory for this skill:`), task notifications, and local command
  output. Counting these inflates the ideation denominator — an injected PRD
  skill body trips the ideation regex with no human having asked anything. The
  miner filters these in `_NOT_A_PROMPT`; extend that list rather than working
  around it.

- **Attribution needs a window.** A tool call belongs to the most recent user
  prompt *in the same session*. Sidechain (subagent) entries carry no prompts of
  their own, so their tool calls must attribute to the parent session's open
  turn — otherwise subagent skill fires look like orphans.

- **Import the ideation regex, don't copy it.** The miner imports `_PATTERN`
  from `hooks/ideation_nudge.py` so the report always measures the same rule the
  hook enforces. Two copies drift within a week and then the numbers mean
  nothing.

- **Transcripts predate the plugin.** Most of the local corpus was recorded
  before these skills existed, and `enabledPlugins` was empty. Always scope with
  `--since` to the date the plugin actually went live, or the baseline is
  meaningless.

## Consent rules for the hook layer (non-negotiable)

`jupi-skills` is a **distributed** plugin — hooks run on other people's machines.
A hook that phones home is a consent decision, not just an engineering one.

- Off by default. Enable via an explicit env var (e.g. `JUPI_SKILLS_TELEMETRY=1`).
- Ship **names, timestamps, and outcomes only**. Never prompt text, never file
  paths, never tool arguments.
- Hash the session id; don't send anything that re-identifies a user's work.
- Document exactly what is collected in the plugin README, and make the local
  log file readable so users can see what would be sent.
- Fail open and fail silent. `ideation_nudge.py` is the model here — any error
  exits 0 with no output so it can never block a prompt.

## Acceptance criteria

- [ ] Jupi API records `source`/`client`/`client_version` on every decision write
- [ ] `skill-usage-report.py` runs clean against a corpus scoped with `--since`
- [ ] Recall is reported per-surface (Claude Code vs. claude.ai vs. Cowork)
- [ ] A trigger-wording change can be measured before/after from one command
- [ ] Hook telemetry is opt-in, content-free, and documented in the README

## Running the miner

```bash
python3 tools/skill-usage-report.py --since 2026-07-01 --samples 10
```

`--json` for machine-readable output, `--projects` to point at a different
transcript root, `--samples 0` to suppress the missed-prompt excerpts (they
contain raw prompt text — keep them local, don't paste them into tickets).
