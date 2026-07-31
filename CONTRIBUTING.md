# Contributing

This repo is the single source of truth for the Jupi Agent Skills. It carries **no version numbers** on purpose — the effective version of each plugin is the latest commit SHA on `main`. Keep that in mind; the rules below exist to make it work.

## Branch model

Dead simple: **`main` is the reference branch consumers track** (`jupi-co/jupi-skills`). There's no separate `release` branch — whatever is on `main` is what everyone gets.

Because any commit on `main` becomes a new version for every consumer:

1. **Keep `main` shippable.** Land one coherent change at a time and squash noisy/unrelated work. Use feature branches + PRs for anything non-trivial.
2. **Never force-push `main`.** Consumers' background auto-update does a `git pull`; it must always fast-forward.

## Add a skill

1. Create `plugins/jupi-skills/skills/<new-skill>/SKILL.md` with frontmatter:
   ```markdown
   ---
   name: <kebab-case-name>
   description: <what it does + when to use it — this is what the agent matches on to auto-invoke. Be specific; include trigger phrasing like "Use when…">
   ---
   <instructions>
   ```
   - The skill's name comes from its **folder** containing `SKILL.md`.
   - Add `disable-model-invocation: true` to make a skill run **only** when called explicitly via `/jupi-skills:<name>`, never auto-triggered.
   - Keep `SKILL.md` focused; push long material into a sibling `reference/` folder so it loads on demand.
2. **Keep each skill self-contained.** Do not reference files outside the plugin directory (e.g. `../shared`) — plugins are copied to a cache on install and external paths won't resolve. Use a `reference/` subfolder inside the skill.
3. If you're adding a **new plugin** (not just a skill in the existing one), also add `plugins/<plugin>/.claude-plugin/plugin.json` (**no `version`**) and a one-line entry in `.claude-plugin/marketplace.json`.
4. Open a PR into `main`. CI validates (see below).
5. Merge it — merging to `main` **is** shipping.

## Edit a skill

Change the files, PR into `main`, merge when CI is green. **Do not** add version numbers.

## Hard rules

- **No `version` field** in `plugin.json` or in any `marketplace.json` plugin entry. Setting it pins consumers to that string and silently stops their updates.
- **No skill references files outside its plugin directory.**
- **Marketplace and plugin `name`s are kebab-case** and must not impersonate official/reserved names (`anthropic-*`, `claude-code-*`, `agent-skills`, `official-*`). Keep the marketplace `name` (`jupi-skills`) stable — each user registers one marketplace per name.

## Local validation

Before opening a PR, run the same checks CI runs:

```bash
claude plugin validate .                       # the catalog
claude plugin validate plugins/jupi-skills     # a plugin (checks SKILL.md frontmatter)
claude plugin validate plugins/proactive-jupi
```

`tools/validate-plugin.sh` runs an extra pass over **every** plugin under `plugins/*` — it catches XML-like tags and over-1024-char descriptions in `SKILL.md` files, which Cowork's validator rejects but `claude plugin validate` does not.

CI (`.github/workflows/validate.yml`) runs `claude plugin validate` on the catalog and every plugin on each PR and push to `main`, blocking a broken catalog or malformed `SKILL.md` frontmatter from landing.

### Optional: build the uploadable zips

`tools/install-hooks.sh` wires a `post-commit` hook (`core.hooksPath .githooks`) that validates and rebuilds `dist/<plugin>.zip` from each commit — the artifacts Cowork uploads. `dist/` is gitignored; the hook is opt-in per clone.

## Shipping

There's no promote step. Merge to `main` and you've shipped — consumers with auto-update enabled pick it up on their next session start. No version bump.
