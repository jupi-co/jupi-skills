# Working in `jupi-skills/`

Conventions for any Claude session working in this repo. The *workflow* — branching, adding a skill, validating, shipping — is [CONTRIBUTING.md](CONTRIBUTING.md); this file is the things that aren't obvious from the tree.

## What this repo is

A **plugin marketplace** (`.claude-plugin/marketplace.json`) shipping two plugins that are related but not interchangeable:

| | `plugins/jupi-skills/` | `plugins/proactive-jupi/` |
|---|---|---|
| What | Three decision skills **you** invoke: `search-decisions`, `log-decision`, `submit-decision` | The engine that runs **on a schedule** and works your backlog |
| Also carries | `hooks/` — turn telemetry + the ideation nudge | `shared/` — the Neon layer (`db.mjs`, `schema.sql`) |
| Depends on | nothing | `jupi-skills` (declared in its manifest) |

Supporting trees: `evals/` (skill eval suites), `tools/` (validate/package/install-hooks), `docs/` (architecture diagrams + the engine's design docs), `.githooks/` (opt-in post-commit validate + package).

## Rules that apply to both plugins

- **Merging to `main` *is* shipping.** No version field anywhere, so the effective version is the latest commit SHA and every landed commit updates every consumer. Keep `main` shippable; never force-push it.
- **A skill never references files outside its own plugin directory.** Plugins are copied to a cache on install and external paths won't resolve. (`proactive-jupi`'s `shared/` is fine — it's *inside* the plugin.)
- **Validate before a PR:** `claude plugin validate` on the catalog and each plugin (what CI runs), plus `tools/validate-plugin.sh` for the two rules Cowork enforces and `claude plugin validate` doesn't — no XML-like tags in a skill description, and descriptions ≤ 1024 chars.
- **Log build/design decisions to Jupi** as finalized records as they're made.

## `jupi-skills` — the decision skills

- **The hooks are user-visible, not internal.** `hooks/hooks.json` wires four of them into every consumer's session: `ideation_nudge.py` (UserPromptSubmit — injects a reminder to consult `search-decisions` when a prompt looks like ideation), `skill_probe.py` (PostToolUse on `Skill`), `close_probe.py` (Stop), and `telemetry.py`, the shared emitter that POSTs turn shape to `apis.jupi.co`. Changing what a hook sends changes what every installed session sends — treat it as a product change and update the [README](README.md#usage-telemetry) disclosure with it.
- **Telemetry is on by default** during the current testing phase and includes the first 2000 chars of each prompt. `"telemetry": false` in `.claude/jupi.local.json` turns it off; `JUPI_SKILLS_TELEMETRY=off` overrides for one session.
- **Config:** `.claude/jupi.local.json` (workspace slug + optional contacts map). A user-level `~/.claude/jupi.local.json` merges with the project one, project winning.

## `proactive-jupi` — the engine

*Ported from the `jupi-co/proactive` repo this plugin was migrated out of. Full rationale in [docs/proactive-jupi/IMPLEMENTATION-PLAN.md](docs/proactive-jupi/IMPLEMENTATION-PLAN.md); paths are relative to this repo's root.*

### The model — don't conflate these
- **Signal** = ephemeral trigger (email, meeting, Slack ping, issue, PR, doc). Never persisted.
- **Task** = the *input*, one unit of the backlog.
- **Action** = a *unit of execution*. **One task can fan out into several parallel actions.**
- **Decision** = a Jupi trade-off, raised only when act-or-decide can't safely act.
- **Rule** = a resolved rule-decision (*when X, always Y*), approved by an owner.
- **Fact** = knowledge about people/orgs/projects, in Supermemory.

### State homes (authoritative)
*(This section is about the **end user's** workspace — the repo setup runs in — not about this one.)*

Setup runs **inside the user's existing repo** where there is one, so everything Proactive-Jupi owns is namespaced under a single **`.proactive-jupi/`** data folder at the workspace root — it must not scatter files across the user's tree. **That folder is the copy a human edits, not the copy a routine reads:** a scheduled routine carries its config in its own prompt and materializes it into its own working directory, so nothing at run time depends on the folder existing. Which is also why no skill writes run logs or reports to disk — they're returned, and the run itself is recorded in Neon `routine_runs`. **That includes the instance config: `.proactive-jupi/config.local.json`** (gitignored; the secret-bearing Neon string + resolved `jupiUserId`). The **only** thing this plugin puts in a user's `.claude/` is harness-owned `settings.json` (which *must* live there). Keeping config under `.proactive-jupi/` consolidates all plugin-owned state in one place and sidesteps environments (e.g. the Cowork device bridge) that refuse writes into `.claude/`.
- **Facts → Supermemory.** Only `update-brain` writes them.
- **Backlog + actions → Neon** (`plugins/proactive-jupi/shared/schema.sql`); each action carries `decision_id`/`option_id` (no separate registry). **Every row is keyed by `user_id` = the Jupi user id** (`jupiUserId`, resolved once at setup) — **Jupi is the reference for identity**, and the same id keys the brain's Supermemory container tag `user_<jupiUserId>`, so Jupi, Neon, and Supermemory share one identity. The project-scoped conn string is a physical boundary; `user_id` is the row-level one (a shared DB separates users by it). Every query filters by `user_id`.
- **Asset Map → `.proactive-jupi/assets.md`** (hand-editable; read in full).
- **Decisions + lifecycle (`STARTED → FINALIZED → EXECUTED`) → Jupi.**

### Golden rules
- **Prefer an installed MCP connector over API-key config** for any service; never ask connector-vs-key when a connector is already present. A skill must not prompt for a concern another skill owns (e.g. the Supermemory container tag belongs to `update-brain`, hard-coded — not asked in setup).
- `act-or-decide` **reads** Facts, never writes them (delegates to `update-brain`).
- **Noise control = confidence × risk gate, not volume caps.** Draft = low risk → act. External send / sensitive recipient (peer < manager < CEO < external) = high risk → decide.
- **Value-based task selection lives INSIDE act-or-decide** (the coordination-node pass). Only the cheap Scorer is upstream.
- **Closing loop:** the execution trace on the signal *is* the notification; plus at most one optional EXECUTED ping (email/Slack/none).
- **Guardrails:** default conservative (draft-only) until trust builds. No external side-effect until a decision is settled and runs through the closing loop.

### Setup-skill parity
`setup-proactive-jupi` re-implements Nick's proven `jupi:setup` (external — `../jupi-skills-beta/plugins/jupi/skills/setup/SKILL.md`, not in this repo). When editing it, diff against that reference so nothing regresses silently. Capabilities to preserve: **Jupi is the blocking gate** (probe → loop until it answers, never continue without it) · **discover the user's stack** (ask their role/tools — never a hardcoded menu) · **inventory before asking** (a tool is connected iff its calls resolve here; the session can't read "Customize" connectors, so ask to enable-in-Customize before any redundant OAuth) · **pre-authorize for unattended runs** (`dontAsk` settings.json) · **user-visible scheduled routines** · **narrate per-step progress** (✅/🔧/⚠️) · **front-load everything human-gated** (all config keys, OAuth consents, stack questions, *and* the Neon credential+egress probe complete in an attended prelude behind a `✋ needs-you done` boundary; steps after it run unattended and must never introduce a fresh prompt). Routines are **cloud-scheduled and carry their own config** — the rule and the template are in the skill's `reference/routine-prompt.md`; the rationale is [IMPLEMENTATION-PLAN](docs/proactive-jupi/IMPLEMENTATION-PLAN.md) §12.
