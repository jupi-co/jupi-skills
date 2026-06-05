---
name: search-decisions
description: "Surface prior decisions recorded in Jupi (the team's decision platform) that relate to what the user is working on, and report their insights, chosen outcomes, and any contradictions with the current direction. Use this whenever the user is loading context for a piece of work — starting a project, drafting a spec/PRD, prepping for a meeting, reviewing an architectural or product choice — or asks anything like \"have we decided X?\", \"what did we choose for Y?\", \"is there prior art on Z?\", \"why did we go with…\". Lean toward using it proactively at the start of any substantial task: a two-second check against past decisions prevents re-litigating settled questions and catches conflicts early. Read-only — it never changes anything in Jupi."
---

# Search decisions

## What this is for

Jupi is where this team records decisions — the alternatives weighed, the rationale, who decided, and what was learned. A lot of that knowledge is invisible at the moment you need it: you're about to spec a feature or argue an approach, and the question was already settled (or deliberately left open) weeks ago. This skill pulls that history back into view before you commit to a direction.

The payoff is twofold: **precedent** (a past decision that supports or informs what you're doing) and **contradiction** (a finalized decision your current direction would violate). Surfacing the second one early is the whole point — it's much cheaper to notice a conflict now than in review.

## Tools you'll use

Both are provided by the Jupi MCP server. Depending on how it's connected they may appear namespaced (e.g. `mcp__Jupi__search-decisions-tool` or `mcp__claude_ai_Jupi__search-decisions-tool`) — use whichever the environment exposes.

- `search-decisions-tool` — hybrid semantic + keyword search over a workspace's STARTED and FINALIZED decisions. Returns ranked `items`, each with `id`, `title`, `description?`, `status`, `relevanceScore`, and `insights` (`{fact, quote, authors, chunkId}`). Inputs: `query` (required), `groupSlug` or `groupId`, `topK` (default 10, max 50).
- `get-decision` — full state of one decision: Postgres fields plus the live document (`savedOptions`, `skippedOptions`, `criteria`, `decisionComments`), `selectedOptionIds`, `closingText`, `summary`, `insights`. Inputs: `decisionId` (required), `groupSlug` or `groupId`.

Note `search-decisions-tool` already returns insights, so you often don't need `get-decision` at all. Reach for `get-decision` only on the handful of results worth a deep look — to read the actual options considered, the criteria, or the closing rationale.

## Workspace setup

Both tools need a workspace. Read it from `.claude/jupi.local.json` (gitignored):

```json
{ "workspace": "<group-slug>" }
```

If the file or its `workspace` key is missing, ask the user for their Jupi workspace slug, use it for this run, and offer to save it to that file so you don't have to ask again. Never commit this file (it's already covered by `.gitignore`).

## How to run a search

1. **Turn the user's context into a query.** Use the actual topic, not a literal echo of their sentence — feature name, subsystem, product area, the specific question. If the work spans a few distinct themes, run a search per theme rather than one vague query; semantic search rewards specificity.
2. **Call `search-decisions-tool`** with the workspace slug. Leave `topK` at the default unless the user wants a broad sweep.
3. **Decide what's worth a deeper read.** Skim titles, statuses, and `relevanceScore`. For the genuinely relevant hits (typically the top few, or anything clearly on-topic), call `get-decision` to pull options, criteria, and `closingText`. Don't fan out `get-decision` across every result — it's wasteful and buries the signal.
4. **Cross-reference against what the user is doing right now.** This is the part that adds value beyond a raw search. For each relevant decision ask: does this _support_ the current direction (precedent) or _conflict_ with it (contradiction)? A FINALIZED decision whose chosen option is the opposite of what the user is about to do is the headline finding — say so plainly.

For a FINALIZED decision, the chosen option ids are in `selectedOptionIds`; resolve them to titles via `savedOptions` (from `get-decision`) so you can report _what_ was chosen, not just an id. The rationale is in `closingText`.

## What to report

Lead with the conclusion, not a list. Use this shape:

```
Found N related decision(s) in <workspace>.

⚠️ Contradiction — "<title>" (FINALIZED)
   Chose: <selected option>. Rationale: <closingText, condensed>.
   Your current direction (<what they're doing>) conflicts with this.

✓ Precedent — "<title>" (FINALIZED)
   Chose: <selected option>. Key insight: "<quote>" — <author>.

◻ Open / related — "<title>" (STARTED)
   Still in progress. Relevant because <reason>; insights so far: <fact>.

<one-line takeaway: safe to proceed / reconcile with decision X / loop in Y>
```

Rules of thumb that keep this useful:

- **Insights over titles.** A title tells the user nothing they couldn't guess. Quote the `fact`/`quote` and attribute it (`authors`) so they can judge for themselves.
- **Include both STARTED and FINALIZED.** An in-progress decision on the same topic is often the most important thing to surface — it means the question is live and the user should join it, not start a parallel one.
- **No matches is a real answer.** If nothing relevant comes back, say so — that's useful (the ground is clear), not a failure. Don't stretch weak matches into false precedents.
- **Stay read-only.** This skill never creates or finalizes anything. If the user then wants to record a decision, hand off to `log-decision`; to open one for someone else to decide, `submit-decision`.
