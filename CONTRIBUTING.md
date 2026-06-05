# Contributing

This repo is the single source of truth for the Jupi Agent Skills. It carries **no version numbers** on purpose — the effective version of each plugin is the commit SHA on the branch consumers track. Keep that in mind; the rules below exist to make it work.

## Branch model

- **`main`** — active development. Consumers do **not** track this. Do day-to-day work here (or on feature branches off it).
- **`release`** — what consumers track (`jupi-co/jupi-skills@release`). A change reaches users only when it lands here.

Because any commit on `release` becomes a new version for every consumer:

1. **One shippable change per promotion to `release`.** Squash noisy/unrelated work first.
2. **Keep `release` history append-only — never force-push.** Consumers' background auto-update does a `git pull`; it must always fast-forward.

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
5. When ready to ship, promote `main` → `release`.

## Edit a skill

Change the files, PR into `main`, promote to `release` when ready. **Do not** add version numbers.

## Hard rules

- **No `version` field** in `plugin.json` or in any `marketplace.json` plugin entry. Setting it pins consumers to that string and silently stops their updates.
- **No skill references files outside its plugin directory.**
- **Marketplace and plugin `name`s are kebab-case** and must not impersonate official/reserved names (`anthropic-*`, `claude-code-*`, `agent-skills`, `official-*`). Keep the marketplace `name` (`jupi-skills`) stable — each user registers one marketplace per name.

## Local validation

Before opening a PR, run the same checks CI runs:

```bash
claude plugin validate .                       # the catalog
claude plugin validate plugins/jupi-skills     # the plugin (checks SKILL.md frontmatter)
```

CI (`.github/workflows/validate.yml`) runs these on every PR and push to `main`/`release`, blocking a broken catalog or malformed `SKILL.md` frontmatter from reaching `release`.

## Promote to release

When `main` is ready to ship:

```bash
git checkout release
git merge --ff-only main    # keep release history linear / append-only
git push origin release
git checkout main
```

Consumers with auto-update enabled pick it up on their next session start. No version bump.
