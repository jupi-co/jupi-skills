---
name: package-jupi-plugin
description: Build the uploadable Cowork/Claude Code plugin zip(s) for this repo and keep the packaging git hook installed. Use when someone says "package the plugin", "build the jupi zip", "rebuild the plugin artifact", "install the build hook", or asks to produce the .zip to upload into Cowork. Repo dev tooling only — not shipped inside any plugin.
---

# Packaging the jupi plugin

This repo ships plugins under `plugins/<name>/`. The uploadable artifact is a
zip whose ROOT contains `.claude-plugin/plugin.json` (plugin contents at the
archive root, not nested under an extra folder).

## Build
- All plugins: `bash scripts/package-plugin.sh`
- One plugin: `bash scripts/package-plugin.sh jupi`
- Output: `dist/<name>.zip` (gitignored build artifact).

## Validate
Run `bash scripts/validate-plugin.sh`. It fails if any manifest is unreadable
or any skill `description` contains angle-bracket tags like `<request>` —
Cowork rejects those with "SKILL.md description cannot contain XML tags". Fix
by replacing `<...>` with `[...]` in the description.

## Auto-build on commit
Run `bash scripts/install-hooks.sh` once per clone. After that, the
`post-commit` hook validates the commit that just landed (surfacing any
XML-tag regression as a warning) and regenerates `dist/*.zip` from the new
`HEAD`. There is no pre-commit hook — validation runs post-commit only, so it
reports rather than blocks; run `validate-plugin.sh` yourself before committing
if you want to catch a bad description first.

## Uploading
In Claude Desktop → Cowork → Customize → Plugins → Personal → the + next to
"Local uploads", select `dist/jupi.zip`. Keep the `.zip` extension; the
uploader currently rejects `.plugin` files at the backend even though the file
picker lists them.
