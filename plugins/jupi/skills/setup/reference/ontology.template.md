# Living ontology of the Auto-Jupi context

> **This file describes what `context/` actually contains, here and now.**
> Maintained by `update-context` (regenerated at each `full` run, patched on `targeted`). Read **first** by `act-and-decide` (schema-on-read).
> The schema is **not fixed** — this page is the source of truth of the current schema.

- **State**: **EMPTY** — seeded by `/setup`, not yet populated. The first `update-context full` run will fill the inventory and counts below.
- **Maintained by**: `update-context` · **Consumed by**: `act-and-decide`

---

## What `context/` contains (persisted types)

| Folder | Type | Files | Role |
|---|---|---|---|
| `people/` | Person | 0 | The user + interlocutors + colleagues |
| `orgs/` | Org | 0 | Company + pilots + linked entities |
| `projects/` | Project | 0 | Linear projects, repos, pilots, GTM |
| `processes/` | Process | 0 | Recurrent process / method — descriptive |
| `tools/` | Tool | 0 | Stack tools + Auto-Jupi's access on each (action surface) |

**Total: 0 entity files** (the first `full` run populates them, with an `_index.md` per folder).

**Goals (Goal)**: not a folder — **co-located per entity** in `<type>/<slug>.goals.md` (twin collection of the file).

> **The context contains ONLY knowledge** (Person, Org, Goal, Project, Process, Tool). Pattern, Action, Decision, Rule belong to `act-and-decide` — see below.

Plus:
- `_compiled-context.md` — compact reloadable summary.
- _(Freshness and exploration tracking: `update-context/coverage.md` and `update-context/backlog.md`.)_

---

## Fields per type (target YAML frontmatter)

**Person** (`people/<slug>.md`)
```
type, id, name, status, email, role, org [[wikilink]], reports_to [[wikilink]]|null,
interaction_frequency (high|medium|low), circle (1|2|3),
confidence (confirmed|inferred), sources[], created_at, updated_at
```

**Org** (`orgs/<slug>.md`)
```
type, id, name, status, confidence, sources[], created_at, updated_at
```

**Co-located goals** (`<type>/<slug>.goals.md` — collection per entity)
```
File frontmatter: type: goals, entity [[wikilink]], updated_at
Each goal = a section: status (active|done), timeframe (annual|quarterly|focus|informal),
contributes_to [[goal-id]]|—, confidence (confirmed|inferred), sources[]. Statement + KPIs in the body.
```

**Project** (`projects/<slug>.md`)
```
type, id, name, status (active|done|dormant), owner [[wikilink]],
contributes_to [[goal-wikilink]], confidence, sources[], created_at, updated_at
```

**Process** (`processes/<slug>.md`)
```
type, id, name, status, scope (org|team|personal), cadence, owner [[wikilink]]|null,
confidence (confirmed|inferred), sources[], created_at, updated_at
```

**Tool** (`tools/<slug>.md`)
```
type, id, name, status, category, access (read | read+write | full | none),
access_via (mcp:<uuid> | gh-cli | none), used_by [[wikilink]]|null,
confidence (confirmed|inferred), sources[], created_at, updated_at
```

**Provenance — two levels (all files)**
- File level: `sources[]` (frontmatter) + `confidence: confirmed|inferred`.
- Fact level: **inline** provenance in the body — `role: X (src: ..., confirmed|deduced)`. Never propagate a deduction as a certainty.

---

## What does NOT live in `context/` (ontological reminder)

These objects belong to **`act-and-decide`** (or to Jupi) — the context never contains them:
- **Pattern** — persistent watchlist of `act-and-decide` (`act-and-decide/patterns/`).
- **Action** — output of `act-and-decide` per run (`act-and-decide/runs/`).
- **Decision** — lives in **Jupi** (never replicated). Queried via `search-decisions-tool`.
- **Rule** — lives in **Jupi** as the resolution of a finalized type 2/4 decision.
- **Signal** — ephemeral (email, event, issue, PR). Never persisted.

---

## Relations (expressed as `[[wikilinks]]` in the bodies)

- Person `member_of` Org · Person `reports_to` Person
- Person `owns` Goal / Project
- Goal `contributes_to` Goal (parent/child) · Project `contributes_to` Goal
