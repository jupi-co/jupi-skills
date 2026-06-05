# jupi-skills

The source of truth for the **Agent Skills that talk to Jupi** — the team's decision platform. Install once; updates flow automatically.

These skills let an agent (in Claude Code, Cowork, or Cursor) work with your team's decisions through the **Jupi MCP**:

| Skill | What it does |
|---|---|
| **search-decisions** | Surface prior decisions related to what you're working on — precedents and contradictions. Read-only. |
| **log-decision** | Record a decision you've **already made** as a finalized, searchable entry (title + chosen path + rationale). |
| **submit-decision** | Open a decision you **can't settle alone** and assign it to the right decider. Creates but never finalizes. |

All three are bundled in a single plugin, `jupi-skills`.

> The skills call the **Jupi MCP server** (`https://apis.jupi.co/mcp`). In Claude Code & Cowork it's **bundled with the plugin** — nothing to install separately. Cursor needs it added manually (see [Cursor](#cursor-no-marketplace--same-skillmd-folders)).

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

The plugin **bundles the Jupi MCP**, so it's registered automatically when the plugin installs — no separate MCP setup, no `.mcp.json`, no claude.ai connector. On first use, approve the one-time authentication prompt.

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

**Cursor also needs the MCP.** Plugins don't reach Cursor, so the bundled server doesn't apply here — add the Jupi MCP once to `.cursor/mcp.json` (or global `~/.cursor/mcp.json`), then reload the window. Without it the skills load but their Jupi calls have nothing to reach.

```json
{
  "mcpServers": {
    "Jupi": { "url": "https://apis.jupi.co/mcp" }
  }
}
```

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

## Configuration: point the skills at your workspace

Once installed, the skills need to know which Jupi **workspace** to act on. Put the slug in `.claude/jupi.local.json` at the root of the project you're working in (gitignored — never commit it):

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

If the file is missing, the skills just ask for the slug and offer to save it — so this is optional convenience, not a blocker.

---

## Repo layout

```
.claude-plugin/marketplace.json        the catalog
plugins/jupi-skills/
  .claude-plugin/plugin.json           plugin manifest (no version — by design)
  .mcp.json                            bundled Jupi MCP (auto-registers on install)
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
