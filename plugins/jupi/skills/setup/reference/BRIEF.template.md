# Auto-Jupi — Framing Brief

> **Status: Alpha, highly iterative.** The brief, the ontology, the prompts and the scope are hypotheses under test — critique and modify them freely to improve.
> **V1 scope**: build/maintain the context + **list candidate actions and decisions**, **without execution** and **without Jupi posting** until further notice.
> **Shared reference document** for both modes (`update-context` and `act-and-decide`).
> **Working dir**: the workspace this file lives in (the CWD where the routines run). All data paths below are relative to it.

---

## 1. North Star

> **Auto-Jupi automates the user's work (and eventually that of all their colleagues) by focusing them solely on the individual or collective decisions that will then be made in Jupi.**

The first big goal is to be able to do things before the user has needed to do them or to ask. For that we need context — which we go look for — and decisions. Hence the motto: **act or decide**.

Everything else — reading, drafting, planning, following up — stays on Auto-Jupi's side. The user only has to arbitrate when an arbitration is truly necessary. It's the opposite of a chatbot: Auto-Jupi doesn't ask open questions, it poses **structured decisions in Jupi** — *"A or B?"* — with all the context already done and the resulting actions clearly listed.

**The Grail: coordination nodes.** The Action ↔ Decision relationship is **many-to-many**. A decision that unblocks **several** Actions at once is a *coordination node* — a single arbitration that unties several things. It's the purest form of the North Star. Auto-Jupi **actively** seeks these nodes rather than atomizing into 1 Action → 1 decision.

**The full cycle — the closing loop.** Auto-Jupi doesn't stop at *creating* decisions: it **closes the loop** and becomes a system that runs.

```
act-and-decide creates a decision (each option = an executable action)
        │
        ▼
the user settles it in Jupi        ◄── the only interface point
        │
        ▼
next run: BEFORE hunting, act-and-decide looks at its PILE of created
decisions → for each CLOSED decision, it executes the action of the chosen option
        │
        ├─► the execution requires a new arbitration? → it creates a new decision (recursive)
        └─► otherwise, action done → then it hunts a new action
```

Deep consequence: **an option is not a description for the human, it's a conditional program.** When the agent writes *« Auto-jupi will send the email to X saying Y »*, it writes **the instruction its future self will execute**; the user, by settling, *« executes »* the program. This is the North Star fully realized: the user **arbitrates nothing else**; Auto-Jupi detects, contextualizes, asks for the arbitration, **and executes** — in a loop, recursively.

---

## 2. Architecture: two separate modes + a contract

Auto-Jupi is split into **two independent subjects** (here, two skills) that communicate through **a single interface: `context/`**.

```
                 ┌────────────────────┐
   tools  ─────► │   update-context   │ ──── writes ──►  ┌────────────┐
 (Gmail, Cal,    │  (full | targeted) │ ◄─── calls ───   │  context/  │
  Drive, Linear, └────────────────────┘    (targeted)    │ (interface)│
  GitHub, Jupi)                                            └─────┬──────┘
                                                                 │ reads
                                                          ┌──────▼──────────┐
                                                          │  act-and-decide │ ──► actions + decisions
                                                          └─────────────────┘        ready to post
```

### 2.1 `update-context` — produces the knowledge
Builds and **updates** what we know about the user and their environment. Two modes:
- **`full`** — big periodic run: broad reading of the tools, refreshes the whole context.
- **`targeted`** — called by `act-and-decide` with a precise request (*"who is this person / this project / this company?"*), focused lookup, writes the file, hands back.

### 2.2 `act-and-decide` — consumes the knowledge, produces the arbitrations **and executes**
Works **one action at a time**. At each run it starts by **draining its pile** (executing the decisions it created and that the user has closed), then hunts **one** new action and presents it as a **ready-to-post Jupi Decision** — each option carrying **the executable action** it entails (cf §1, closing loop). **Read-only** on the context; can **order** an `update-context targeted` when it hits a gap. **Owns its own objects** — Patterns, created Decisions (the pile), Actions — in its own space, **never in `context/`**. *(The multi-action batch / 4 dimensions / coordination nodes is a later orchestration layer; the robust unit is the single-action one.)*

### 2.3 The contract (golden rules)
1. **`context/` is the single interface** between the two modes.
2. **`update-context` is the ONLY writer of `context/`.** `act-and-decide` **never** writes it — it reads, and delegates any writing via a `targeted` call. (→ a single writer = no desync between the two sessions.)
3. **The schema is not fixed.** It evolves. The context carries its **own living description** in `context/_ontology.md`, regenerated by `update-context` at each run.
4. **Schema-on-read.** `act-and-decide` reads `context/_ontology.md` **first** and adapts; it never assumes a hard-coded structure.

---

## 3. Ontology (model, philosophy)

**Two families of objects, two distinct owners.** This is the system's fundamental boundary.

**A. CONTEXT objects (the knowledge)** — produced and maintained by `update-context`, live in `context/`. Their living schema is in `context/_ontology.md`.

| Type | Role | Where it lives |
|---|---|---|
| **Person** | user + interlocutors + colleagues (`circle` field 1/2/3) | `context/people/` |
| **Org** | company + teams + pilots + prospects | `context/orgs/` |
| **Goal** | goals / focus — **co-located per entity** in `<entity>.goals.md` (any methodology) | `context/<type>/<slug>.goals.md` |
| **Project** | Linear project, repo, initiative, deal | `context/projects/` |
| **Process** | recurrent process / method — descriptive ("how they work") | `context/processes/` |
| **Tool** | stack tool + Auto-Jupi's access on each (its action surface) | `context/tools/` |

**B. ACTION objects (the arbitration)** — produced and **owned by `act-and-decide`**, never in `context/`.

| Type | Role | Where it lives |
|---|---|---|
| **Pattern** | observed recurrence, persistent watchlist candidate for a rule | `act-and-decide/patterns/` |
| **Action** | **concrete instance** to execute once — never a behavior | `act-and-decide/runs/` (output per run) |
| **Decision** | Jupi decision (types 1-5) | **Jupi** (never replicated) |
| **Rule** | *"when X, always Y"* — resolution of a type 2/4 decision | **Jupi** |

**C. Ephemeral**: **Signal** (email, event, issue, PR, new doc) — never persisted.

**Critical principle — Action = instance, never behavior.** If an Action is named *"codify X"*, *"auto-route Y"*, *"cascade Z"* → it's a Rule in the making: go through a Pattern, and the Action becomes **the most recent instance** of that pattern. Without a concrete instance, no Action — the Pattern stays on the watchlist.

**Lifecycle of a Decision + the pile.** A Decision goes through `proposed → posted (in Jupi) → closed (the user settles an option) → executed`. The canonical decision **lives in Jupi**, but `act-and-decide` keeps a **local registry** in `act-and-decide/decisions/` — **it's not a replica**: for each created decision it stores the `jupi_decision_id`, the status, and above all **the action-instructions per option** (*what Auto-jupi will do depending on the chosen option*). This registry is the **priority pile** that the agent **drains first** at each run (cf §1). The resolution (which option) is read in Jupi; the instruction to execute is in the registry.

---

## 4. Jupi decisions — principles and taxonomy

**Principles (meta-instructions, applied by `act-and-decide`)**
1. **COO/EA** — Auto-Jupi has already read everything, weighed everything. The user sees *"A, B or C?"* with the minimum context to settle. Everything else goes back to Auto-Jupi.
2. **Action-first** — **always** start from the candidate Actions, score them, select a diverse batch, **then** generate the decisions that unblock them.
3. **Scoring** of each Action: `frequency_potential` × `impact_potential` (low/medium/high).
4. **Bundling mandatory** — a rule-decision (type 2/4) is **always** bundled to an immediately unblockable action, visible in the description. No theoretical codification.
5. **Always an attached action** — **even a big strategic arbitration** (type 5) must carry a concrete action. Never an abstract arbitration without an action.
6. **Batch diversity** — 4 dimensions: personal / impactful / recurrent / collective.
7. **Many-to-many & coordination nodes** — actively seek the single decision that unblocks several Actions.
8. **Generic rule phrasing** — type 2/4 contains a marker *"always / from now on / in general"*.
9. **Search-first** — before any new decision, `search-decisions-tool` to verify it hasn't already been settled (anti-duplicate, anti-fatigue).

**Taxonomy (5 types)**

| # | Type | Target | Object |
|---|---|---|---|
| 1 | Action choice — solo | user | one-off confirmation |
| 2 | Rule codification — solo | user | *"when X, always Y?"* — always bundled |
| 3 | Action choice — collective | user + others | multi-party confirmation |
| 4 | Rule codification — collective | team | recodes the team's work — always bundled |
| 5 | Alpha catch-all | user (escalation) | *"I can't classify"* — with an attached action (cf principle 5) |

---

## 5. Scope & interface

- **Tools**: Gmail · Google Calendar · Google Drive · Linear · GitHub · Jupi.
- **User V1**: the workspace owner, on their own stack.
- **Single user interface: Jupi.** No chat, no email, no DM. Only structured Jupi decisions. *(V1: we **list** them, we don't post them.)*

---

## 6. Guardrails (V1)

- ❌ No action executed (no mail sent, commit, Linear comment, doc creation).
- ❌ No Jupi posting. `search-decisions-tool` read-only; never `create-decision-tool` nor `finalize-decision-tool`.
- ✅ Free reading via the MCPs. Free writing in `context/` (update-context) and in the run folders.

---

## 7. Repo structure (in the workspace)

```
<workspace>/
├── BRIEF.md                  ← this file (shared framing)
├── context/                  ← INTERFACE: update-context writes, act-and-decide reads
│   ├── _ontology.md          ← living ontology (schema-on-read)
│   ├── _compiled-context.md
│   └── people/ orgs/ projects/ processes/ tools/
├── update-context/           ← data for the update-context skill
│   └── coverage.md  backlog.md  runs/
└── act-and-decide/           ← data for the act-and-decide skill
    └── patterns/  decisions/  runs/
```

The **behavior** of each mode lives in the plugin skills (`update-context`, `act-and-decide`), invoked by hand or by the daily routine. This workspace holds only the **data**.
