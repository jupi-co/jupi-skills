# jupi-skills

The source of truth for the **Agent Skills that talk to Jupi** — the team's decision platform. Install once; updates flow automatically.

These skills let an agent (in Claude Code, Cowork, or Cursor) work with your team's decisions through the **Jupi MCP**:

| Skill | What it does |
|---|---|
| **search-decisions** | Surface prior decisions related to what you're working on — precedents and contradictions. Read-only. |
| **log-decision** | Record a decision you've **already made** as a finalized, searchable entry (title + chosen path + rationale). |
| **submit-decision** | Open a decision you **can't settle alone** and assign it to the right decider. Creates but never finalizes. |

All three are bundled in a single plugin, `jupi-skills`.

---

## The Jupi MCP

The skills call the **Jupi MCP server** at `https://apis.jupi.co/mcp` (tools appear as `mcp__Jupi__…`, or `mcp__claude_ai_Jupi__…` when connected via claude.ai — the skills handle both).

**Claude Code & Cowork — nothing to do.** The `jupi-skills` plugin **bundles the Jupi MCP**, so installing the plugin (below) also registers and starts the server automatically. No `.mcp.json` and no claude.ai connector required.

**Cursor — add it manually** (Cursor doesn't read plugins, so it won't get the bundled server). Create or edit `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "Jupi": { "url": "https://apis.jupi.co/mcp" }
  }
}
```

Then reload the window. (A global `~/.cursor/mcp.json` works too if you want it in every project.)

### Workspace config (per project)

The skills target a Jupi **workspace slug**. Put it in `.claude/jupi.local.json` (gitignored — never commit it):

```json
{
  "workspace": "<your-group-slug>",
  "contacts": {
    "Eng Lead": "22222222-2222-4222-8222-222222222222"
  }
}
```

- `workspace` — required; used as `groupSlug` on every Jupi call.
- `contacts` — optional name→Jupi-user-UUID map used by **submit-decision** to assign a decider without re-typing UUIDs.

If the file is missing, the skills ask for the slug and offer to save it.

---

## Install

### Claude Code & Cowork (plugin marketplace)

```
/plugin marketplace add jupi-co/jupi-skills@release
/plugin install jupi-skills@jupi-skills
```

CLI equivalent (handy for scripting / Cowork setup):

```bash
claude plugin marketplace add jupi-co/jupi-skills@release
claude plugin install jupi-skills@jupi-skills
```

Invoke a skill (namespaced by plugin):

```
/jupi-skills:search-decisions
/jupi-skills:log-decision
/jupi-skills:submit-decision
```

They also auto-trigger from natural phrasing — e.g. "have we decided X?" (search), "log that we're going with Y" (log), "escalate this to the eng lead" (submit).

> **Why `@release`?** Consumers track the `release` branch, not `main`. Day-to-day edits land on `main`; a change ships to you only when it's promoted to `release`. There are no version numbers — the effective version is the commit SHA at `release`, so every promotion is one clean update.

### Auto-update

Enable **per-marketplace auto-update** for `jupi-skills` in the `/plugin` interface. Because this repo is public, no token is needed — Claude Code pulls the latest at session start and reinstalls changed plugins. Without auto-update, refresh manually:

```
/plugin marketplace update jupi-skills
```

### Cursor (no marketplace — same SKILL.md folders)

Cursor doesn't read `marketplace.json`; it consumes the skill folders directly. Two paths:

- **GitHub install (auto-synced):** install a skill folder by its repo path, e.g. `jupi-co/jupi-skills` → `plugins/jupi-skills/skills/search-decisions`. Stays synced with this repo.
- **Manual copy:** copy a skill folder into the project's `.cursor/skills/<skill>/` (or `.claude/skills/<skill>/`, which Cursor also reads), then reload the window (Cmd/Ctrl+Shift+P → "Developer: Reload Window").

Cursor is project-scoped — add the skills per project.

> **Cursor needs the MCP too.** The bundled Jupi MCP only ships to Claude Code/Cowork. In Cursor, also add it manually to `.cursor/mcp.json` (see [The Jupi MCP](#the-jupi-mcp) above) — without it the skills load but their Jupi calls have nothing to call.

### Optional: pre-wire install for a consuming repo

A repo that wants these skills available to everyone who clones it can add to its `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "jupi-skills": {
      "source": { "source": "github", "repo": "jupi-co/jupi-skills", "ref": "release" }
    }
  },
  "enabledPlugins": {
    "jupi-skills@jupi-skills": true
  }
}
```

This is opt-in by the consuming repo, not something this marketplace controls.

---

## Repo layout

```
.claude-plugin/marketplace.json        the catalog
plugins/jupi-skills/
  .claude-plugin/plugin.json           plugin manifest (no version — by design)
  skills/
    search-decisions/SKILL.md
    log-decision/SKILL.md
    submit-decision/SKILL.md
.github/workflows/validate.yml         CI: validates catalog + plugin on every PR/push
CONTRIBUTING.md                        how to add/edit a skill and ship it
```

## Versioning

Deliberately **none**. No `version` field anywhere → the version resolves to the source commit SHA, so updates ship with zero release bookkeeping. See [CONTRIBUTING.md](CONTRIBUTING.md) for the `main` → `release` flow.

## License

[MIT](LICENSE).
