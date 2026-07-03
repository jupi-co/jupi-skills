# jupi-skills

The source of truth for the **Agent Skills that talk to Jupi** — the team's decision platform. Install once; updates flow automatically.

These skills let an agent (in Claude Code, Cowork, or Cursor) work with your team's decisions through the **Jupi MCP**:

| Skill | What it does |
|---|---|
| **search-decisions** | Surface prior decisions related to what you're working on — precedents and contradictions. Read-only. |
| **log-decision** | Record a decision you've **already made** as a finalized, searchable entry (title + chosen path + rationale). |
| **submit-decision** | Open a decision you **can't settle alone** and assign it to the right decider. Creates but never finalizes. |

All three are bundled in a single plugin, `jupi-skills`.

> The skills call the **Jupi MCP server** (`https://apis.jupi.co/mcp`). In Claude Code & Cowork it's **bundled with the plugin** — nothing to install separately. Cursor needs it added manually (see [Cursor](#cursor)).

---

## Install

### Claude Code & Cowork (plugin marketplace)

```
/plugin marketplace add jupi-co/jupi-skills
/plugin install jupi-skills@jupi-skills
```

CLI equivalent (handy for scripting / Cowork setup):

```bash
claude plugin marketplace add jupi-co/jupi-skills
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

> **Versioning:** none, by design. Consumers track `main` (the default branch); the effective version is its latest commit SHA. Every commit that lands on `main` is one clean update for everyone — no version bumps, no release bookkeeping. So keep `main` shippable.

### Testing unreleased changes (`jupi-skills-staging`)

The catalog also exposes a `jupi-skills-staging` plugin that tracks the
`staging` branch instead of `main` — use it to try a change before it merges.

Point `staging` at the branch you want to test, then install:

    git branch -f staging origin/<pr-branch> && git push -f origin staging
    /plugin install jupi-skills-staging@jupi-skills

It installs under its own namespace (`/jupi-skills-staging:…`), so it runs
alongside the production plugin. Refresh the plugin after each push to
`staging`. The branch is disposable — don't develop on it.

### Local development: test a branch-specific build (zip upload)

When you're developing a plugin (e.g. `jupi`) and want to try your **local,
branch-specific** version in Cowork without pushing anything or touching
`staging`, use the repo's packaging tooling. It rebuilds an uploadable
`dist/<name>.zip` on every commit, which you then add through Cowork's
**Local uploads**.

One-time per clone — enable the git hook:

```bash
bash scripts/install-hooks.sh
```

Then the flow is:

1. **Iterate** on your branch as usual.
2. **Commit** your changes (a *local* commit is enough — no push needed). The
   `post-commit` hook validates the plugin and regenerates `dist/jupi.zip`
   (and `dist/jupi-skills.zip`) from the new `HEAD`.
3. In **Claude Cowork → Customize → Plugins → Personal → Local uploads**, add
   `dist/jupi.zip`. Walkthrough video: https://cleanshot.com/share/vyFr6Xrf

The zip is a deterministic archive whose **root** contains
`.claude-plugin/plugin.json` (plugin contents at the archive root, not nested
under a folder) — the shape Cowork's uploader expects. Keep the `.zip`
extension; the uploader rejects `.plugin` files even though the picker lists
them.

Handy commands (also driven by the `package-jupi-plugin` dev skill — just say
"build the jupi zip"):

```bash
bash scripts/validate-plugin.sh        # manifest + no-XML-tags-in-description checks
bash scripts/package-plugin.sh jupi    # build just dist/jupi.zip
bash scripts/package-plugin.sh         # build every plugin under plugins/
```

`dist/` is gitignored — it's a build output, never committed. This tooling
lives outside `plugins/`, so it's never shipped inside a plugin.

### Auto-update

Enable **per-marketplace auto-update** for `jupi-skills` in the `/plugin` interface. Because this repo is public, no token is needed — Claude Code pulls the latest at session start and reinstalls changed plugins. Without auto-update, refresh manually:

```
/plugin marketplace update jupi-skills
```

### Cursor

Cursor doesn't read `marketplace.json` or load Claude Code plugins, so it can't use the marketplace above. Install the same skills straight from this repo with the open [`skills` CLI](https://github.com/vercel-labs/skills) (one installer, works across Cursor and ~80 other agents):

```bash
# from your project root — installs all three into .agents/skills/ (which Cursor reads)
npx -y skills add jupi-co/jupi-skills --skill '*' -a cursor

# pull the latest from this repo anytime
npx -y skills update
```

- **Scope:** project by default (lands in the repo, shareable with the team); add `-g` to install globally for all your projects. Add `--copy` to vendor independent copies instead of symlinking to a canonical store.
- After install, reload the window (Cmd/Ctrl+Shift+P → "Developer: Reload Window") if Cursor doesn't pick the skills up immediately.

No-CLI alternatives:

- **Settings UI (auto-synced):** Cursor → Settings → Rules → Add Rule → **Remote Rule (GitHub)** → paste `https://github.com/jupi-co/jupi-skills`. Per-user; stays synced with this repo.
- **Manual copy:** copy a skill folder into `.cursor/skills/<skill>/` (or `.claude/skills/<skill>/`, which Cursor also reads), then reload.

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
      "source": { "source": "github", "repo": "jupi-co/jupi-skills", "ref": "main" }
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

Deliberately **none**. No `version` field anywhere → the version resolves to the latest commit SHA on `main`, so updates ship with zero release bookkeeping. See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow.

## License

[MIT](LICENSE).
