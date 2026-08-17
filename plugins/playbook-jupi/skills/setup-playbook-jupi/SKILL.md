---
name: setup-playbook-jupi
description: >-
  Bootstrap (cold-start) a Playbook-Jupi workspace — the one-time setup that turns the owner's declared
  process into the run's frame. Creates the playbook store (a new Notion process page, owner-editable),
  creates the playbook's tracked dossiers from the owner's declared source (for a sales pilot: accounts
  from a reporting spreadsheet), and runs the playbook extraction over the owner's own documents —
  lifecycle, decision points, inferred/declared entries plus declared holes, none of it pre-authorized.
  Run once per workspace (re-runnable to refresh). Not for: running the process (act-or-decide),
  watching inbound (refresh-backlog), or setting up an open-world proactive-jupi workspace
  (setup-proactive-jupi).
disable-model-invocation: true
---

# setup-playbook-jupi — bootstrap a closed-world Playbook-Jupi workspace

> **Scaffold (TECH-477) — not yet runnable.** This skill is a skeleton: headings + decided design,
> bodies TODO. If invoked, say exactly that and stop — do not improvise a bootstrap from the headings.
> Bodies land with the bootstrap/extraction ticket (build plan §11, item 2).

Playbook-Jupi runs a **declared process**: the user's playbook defines the frame — what is in scope,
which dossiers are tracked, and the lifecycle they traverse; every hole in the playbook surfaces as a
Jupi decision; validated decisions become rules. **The playbook is the prior, decisions are the
evidence, rules are the posterior** (design §1). This skill takes a workspace from zero to **ready to
run the process**: store connected, dossiers created, playbook extracted — mostly declared ignorance on
day 1, and that is the point (§2).

Fork note: sibling of `setup-proactive-jupi`, rewritten for the closed world. The Neon schema apply and
the `shared/` helpers (`db.mjs`, `ensure-deps.sh`, `apply-schema.mjs`) are reused as-is (§11).

## Connect the stores — three stores, three roles (§7)

TODO. The decided split: the **playbook doc** (a Notion process page) = current content + the human
view, owner-authoritative — the owner can edit it; Jupi writes it only through `act-post-decision` on
finalized decisions. **Jupi decisions** = provenance and history — the "why" of every version.
**Neon** = the application ledger. Structured state (per-entry status, version, evidence, provenance)
lives in Jupi/Neon from day one; Notion only ever renders it (§15.2).

## Create the playbook store — the Notion process page (§7)

TODO. Create a **new Notion process page** with the doc skeleton: §1 Funnel (stages + terminal
states) · §2 Decision points & rules (the heart: id · question · scope · current answer *or* "not
established" · status · evidence) · §3 Assets · §4 Vigilance rules (tripwires) · §5 Never-seen /
out-of-scope log · §6 Changelog (generated from decisions).

## Create the dossiers from the owner's declared source (§8)

TODO. The unit of work is the **dossier** — the playbook's tracked item, a long-lived object traversing
the declared lifecycle. What the items are and where they come from is the owner's declaration (the
closed world: exactly the declared set, no discovery) — for the pilot, accounts read from a reporting
spreadsheet. Minimal V1 per design: one Neon `tasks` row per item (`pb-create-dossier {label, attrs}`
— the source's columns become attrs; `shared/playbook.mjs`, §11 item 3).

## Run the playbook extraction (§2–§4)

TODO. Extract the playbook from the owner's own documents into the store: the **lifecycle** (the stage
list the dossiers traverse — written as the reserved `lifecycle-stages` entry via `pb-declare-stages`;
the engine ships no lifecycle of its own), the
**decision points** (each with a stable id and a declared scope axis), and entries by provenance —
`inferred` (LLM-derived from sparse sources) vs `declared` (extracted verbatim and unambiguously from
the owner's doc) (§3). An unanswered point reads **"not established — I will ask every time"** (§2).
Extraction can be aggressive because wrongness is cheap: an entry never pre-empts a decision — it only
pre-fills the recommended option, provenance cited — until the owner validates it (§4; the rule-status
read-side gate is its own ticket, §11 item 1).

## Schedule the routines (§13)

TODO. Two triggers, split by latency class: `catchup` (business-hours sentinel, cheap no-op exit) and
`daily` (full funnel sweep). Routine split + run lease land with §11 item 13; human entry points
(catch-up-now, process-this-reply) with item 14.
