---
name: setup
description: "Onboard Auto-Jupi — wire MCP auth, write permissions, create the local workspace, seed the context, and schedule the daily local routines. Use when the user runs /auto-jupi:setup or asks to set up / install / onboard Auto-Jupi."
disable-model-invocation: true
---

# Auto-Jupi — Setup (onboarding)

This is the **`/auto-jupi:setup`** onboarding. It wires Auto-Jupi to run **locally** as two daily routines (Cowork desktop scheduled tasks) against a **working folder** on this machine, with **zero manual confirmation** at run time.

> **V1 choice: LOCAL execution via Cowork.** A scheduled Cowork task accepts a **working folder** → it runs **on the user's machine**, with a **persistent filesystem**. The state (`context/`, `decisions/`, `patterns/`, `runs/`) lives **on disk**, in the working folder — **no git needed** to persist state between runs. (Constraint: the machine must be on at run time.)

> **Idempotent.** Every step **re-checks** and **only fixes what's missing**. Safe to run repeatedly. Report a per-step status (✅ already OK / 🔧 fixed / ⚠️ needs the user).

> **Paths.** Everything Auto-Jupi reads/writes is **relative to the working folder** (the workspace / CWD), never to the plugin (the plugin is copied to a cache on install). The templates this skill copies live in `reference/` inside this skill folder; their **destinations** are in the working folder.

---

## Legend
- **[auto]** — the skill does it, no user action.
- **[user]** — only the user can do it (the skill guides, can't act on their behalf).
- **[auto/guided]** — the skill scripts it if possible, otherwise gives exact UI steps.

---

## Step 0 — Confirm the working folder

Confirm with the user which **working folder** is the Auto-Jupi workspace. Default to the current working directory (CWD) unless they name another. **All subsequent paths are relative to this folder.** Use it as `<workspace>` throughout.

---

## Step 1 — Diagnose MCP connections  [auto]

Auto-Jupi uses these MCP servers (plus the `gh` CLI). Run a **read-only** test call against each to confirm it's connected and authenticated. Tool names may appear namespaced depending on how each MCP is connected — use whichever the environment exposes.

| Tool | Server | Read-only probe |
|---|---|---|
| **Gmail** | `mcp__532ce0b8-…` | `list_labels` (or a 1-result `search_threads`) |
| **Google Calendar** | `mcp__b1eb8a8f-…` | `list_calendars` |
| **Google Drive** | `mcp__ca719720-…` | `list_recent_files` (1 result) |
| **Linear** | `mcp__d9204e40-…` | `list_teams` |
| **Jupi** | `mcp__1ad07158-…` (bundled in this plugin's `.mcp.json`) | `search-decisions-tool` (1 result) |
| **GitHub** | `gh` CLI | `Bash(gh auth status)` |

**Report**: a table of **connected ✅** vs **missing ⚠️**. Don't fail the whole setup if one is missing — record it and continue; the workspace and permissions can still be set up.

> Allowlisting an MCP does **not** authenticate it. Authentication is a separate, interactive OAuth flow (Step 2). In a local desktop setup the MCPs are usually **already authenticated** and **shared across Claude Desktop tabs** → often nothing to redo.

---

## Step 2 — Connect the missing MCPs  [user]

For every server flagged **missing** in Step 1, **guide the user to connect it** (OAuth, one click each). **The skill cannot authenticate on their behalf** — this is the only truly manual action.

- Point them to the Connectors / MCP settings, one server at a time.
- After they connect each one, **re-run the Step 1 probe** for that server to confirm it now answers.
- Loop until all required servers are ✅ (or the user explicitly chooses to proceed without one — note which Auto-Jupi capabilities will be degraded).

---

## Step 3 — Write `.claude/settings.json`  [auto]

Write `<workspace>/.claude/settings.json` so the routines run with **no manual confirmation** but only for pre-approved tools.

- **`permissions.defaultMode: "dontAsk"`** — auto-allows only the allowlisted tools, **refuses the rest** (safer than `bypassPermissions`).
- **`permissions.allow`** — the MCP tools Auto-Jupi needs + `Bash(gh:*)` + file + git.

**Idempotent merge**: if the file exists, read it, **union** the allow list and set `defaultMode` — don't clobber unrelated keys the user may have added.

Target content (adjust the MCP server prefixes to match how they're connected on this machine):

```json
{
  "permissions": {
    "defaultMode": "dontAsk",
    "allow": [
      "mcp__532ce0b8-6cf3-…",
      "mcp__b1eb8a8f-…",
      "mcp__ca719720-…",
      "mcp__d9204e40-…",
      "mcp__1ad07158-…",
      "Bash(gh:*)",
      "Read",
      "Write",
      "Edit",
      "Bash(git:*)"
    ]
  }
}
```

> Use the **server-level** MCP prefix (e.g. `mcp__<server-id>__*`) so all of that server's tools are covered. An agent can **read** its own `settings.json` to self-diagnose, but the effective mode isn't always detectable purely at runtime — if needed, add a small hook.

---

## Step 4 — Create the workspace structure  [auto]

In `<workspace>`, create the data tree the skills read/write. **Idempotent**: only create what's missing; never overwrite an existing `BRIEF.md` or `context/_ontology.md` (they may hold the user's edits / live data).

1. **Seed framing** (copy only if the destination doesn't already exist):
   - `reference/BRIEF.template.md` → `<workspace>/BRIEF.md`
   - `reference/ontology.template.md` → `<workspace>/context/_ontology.md`
2. **Empty dirs** (create if missing):
   - `context/{people,orgs,goals,projects,processes,tools}/`
   - `act-and-decide/{patterns,decisions,runs}/`
   - `update-context/`
3. Optionally drop a `.gitkeep` in each empty dir so the structure survives if the workspace is a git repo.

After this step the workspace looks like:

```
<workspace>/
├── BRIEF.md                       (from template)
├── context/
│   ├── _ontology.md               (from template — blank schema)
│   └── people/ orgs/ goals/ projects/ processes/ tools/
├── update-context/                (coverage.md / backlog.md / runs/ filled by the first run)
└── act-and-decide/
    └── patterns/ decisions/ runs/
```

---

## Step 5 — Seed the context  [auto]

Run the context crawler once to populate the workspace: **invoke `/auto-jupi:update-context full`** in `<workspace>`.

- This drains the seeded backlog, profiles the user's people/orgs/projects/processes/tools (with provenance), and **regenerates `context/_ontology.md`** with the real inventory.
- If some MCPs were left unconnected in Step 2, the run notes the unreachable tools in its run-log and does the most with what's reachable.
- **Idempotent**: re-running setup re-invokes `full`, which is additive (enrich, don't clobber).

---

## Step 6 — Schedule the two daily LOCAL routines  [auto/guided]

Create **two** daily Cowork desktop **scheduled tasks**, each bound to `<workspace>` as its working folder:

| Routine | Command | When |
|---|---|---|
| Context refresh | `/auto-jupi:update-context full` | daily (e.g. early morning) |
| Act & decide | `/auto-jupi:act-and-decide` | daily (e.g. after the refresh) |

Order them so the context refresh runs **before** act-and-decide.

**Prefer scripting** via the `/schedule` mechanism (the scheduled-tasks tooling): create each task pointing at `<workspace>` with the command above. **Idempotent**: list existing scheduled tasks first; if a routine with the same command + working folder already exists, update it instead of creating a duplicate.

**If not scriptable**, give the user this exact 4-step UI flow (per routine):
1. Open Claude Desktop → the **Cowork** tab → **Scheduled tasks** (new task).
2. Set the **working folder** to `<workspace>`.
3. Set the **command/prompt** to the routine command (e.g. `/auto-jupi:update-context full`).
4. Set the **schedule** (daily, chosen time) and save. Repeat for the second routine, scheduled slightly later.

> These run **locally** with a persistent filesystem, so the state lives in `<workspace>` between runs — no git required. The machine must be on at the scheduled time.

---

## Final report

Summarize, per step: MCP diagnosis (connected vs missing, and what the user still needs to connect), whether `settings.json` was written/merged, the workspace tree created, the result of the seeding `full` run (files created, unreachable tools), and the two scheduled routines (created/updated, or the UI steps handed to the user). Flag anything that still needs the user (OAuth, manual scheduling).
