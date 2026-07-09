---
name: setup
description: "Onboard Auto-Jupi — pick the brain folder, connect Jupi (required) and the other tools, pre-authorize them, build a big initial context, schedule the two local routines, and fire the first run. Use when the user runs /jupi:setup or asks to set up / install / onboard Auto-Jupi."
disable-model-invocation: true
---

# Auto-Jupi — Setup (onboarding)

This is the **`/jupi:setup`** onboarding. It wires Auto-Jupi to run **locally** against a personal **brain folder** on this machine, with **zero manual confirmation** at run time.

> **Posture — sell the payoff at EVERY step (this is not IT config).** Auto-Jupi exists to **automate the user's work** and **learn how they operate**, so they're left with only the decisions. Frame each step as *work being lifted off their plate*, never as configuration: at every tool, permission, and routine, say concretely **what time and effort disappear** once it's on — "an AI that does your job and understands how you work." Warm and concrete, never bureaucratic.

> **The mental model.** The **plugin** = the engine (shared code). The **brain folder** = this user's private DATA (context, decisions, patterns). Two local routines then run on a schedule: `update-context` *learns* (daily) and `act-and-decide` *acts* (every 10 min).

> **Idempotent.** Every step **re-checks** and **only fixes what's missing**. Safe to re-run. Report a per-step status: ✅ already OK / 🔧 fixed / ⚠️ needs the user.

> **Paths.** Everything Auto-Jupi reads/writes is **relative to the brain folder** (the workspace / CWD), never to the plugin (it's copied to a cache on install). The templates this skill copies live in `reference/`.

---

## Step 1 — Pick the brain folder

**Do not rely on the current directory** — it's undefined when launched from Cowork. **Strongly suggest an absolute path in the home dir:**

> **`~/brain-of-<first-name>/`** — e.g. `~/brain-of-nick/`

Ask the user's first name if you don't know it; let them override the path if they want. **Create the folder if missing.** Use it as `<workspace>` from here on — **all later paths are relative to it.**

---

## Step 2 — Jupi connection (REQUIRED — blocking)

Jupi is Auto-Jupi's **only interface** — nothing works without it. Probe it with a read-only `search-decisions-tool` call (1 result).

- **Answers ✅** → record it, go to Step 3.
- **Fails ✗** → **STOP.** Show the user this, verbatim, then **re-probe** — loop until ✅, **do not continue without Jupi**:

> **Connect Jupi (required):**
> 1. **Create your Jupi account** — go to **https://jupi.co** and sign up (or sign in if you already have one).
> 2. **Connect the Jupi MCP in Claude** — open **Settings → Connectors → Add**, paste the URL **`https://apis.jupi.co/mcp`**, click **Connect**, and authorize with your Jupi account.
> 3. Tell me when it's done — I'll re-test. **We don't move on until Jupi answers.**

---

## Step 3 — Connect the user's tools (no assumptions — discover their stack)

**Make no assumption about their stack.** Keep selling the payoff at every single one:

> **"Connect this and the work you do inside it moves to me. Skip it and I just can't create that value for you here."**

**A. First — see what's already connected.** Inspect which MCP servers / connectors are already live and tell the user what you can already see. **Build on that — never re-ask for a tool that's already connected.**

**B. The essentials everyone has — one at a time, ASK before assuming:**
1. **Email** — ask *"What's your email engine?"* (Gmail, Outlook / Microsoft 365, other) and guide them to connect **that** one. → *"I triage your inbox: the mails to answer or act on surface to you, the rest I handle."*
2. **Calendar** — connect it. → *"I prep your meetings, catch conflicts, block the slots you need."*
3. **File / doc storage** — ask *"Where do you share files?"* (Google Drive, Dropbox, OneDrive, Notion…) and connect it. → *"I read the docs behind your decisions."*

**C. Then the work-specific tools — this is where the value compounds.** Ask plainly:

> **"What's your job, and which tools do you work in day to day?"**

From the answer, name the concrete tools and guide them to connect **each** — e.g. a PM / eng → Linear / Jira / GitHub; sales → the CRM (Salesforce / HubSpot); a designer → Figma; support → the helpdesk (Zendesk / Intercom); ops → the spreadsheets / DB. **Push here:** the more work tools connected, the more of their *actual job* Auto-Jupi takes over — so for each tool they name, spell out the work that disappears once it's on.

**For each tool:** read-only probe → if missing, give the payoff + guide the connect (OAuth / Connectors) → re-probe until ✅. Nothing here blocks setup (only Jupi, Step 2, does) — but **every skipped tool is value left on the table**, so don't let them skip lightly.

---

## Step 4 — Pre-authorize the tools (remove the "Allow" button)

By default, every tool call pops an **"Allow"** prompt. A **routine can't click it** → it would hang. So the routines must run **unattended**:

1. **Detect the current mode first.** If this machine already runs in a global bypass / `dontAsk` mode, **say so and skip** — nothing to write.
2. Otherwise write/merge `<workspace>/.claude/settings.json`:
   - `permissions.defaultMode: "dontAsk"` (auto-allow the allowlist, refuse the rest — safer than full bypass).
   - `permissions.allow`: the **real** MCP server ids (resolve them from the live connections — **do not** hardcode placeholder UUIDs, they differ per machine) + `Bash(gh:*)`, `Read`, `Write`, `Edit`, `Bash(git:*)`.
3. **Idempotent merge** — union the allow list, don't clobber other keys.

---

## Step 5 — Build the workspace structure

In `<workspace>`, create the data tree. **Idempotent**: only create what's missing; **never overwrite** an existing `BRIEF.md` or `context/_ontology.md` (they may hold edits / live data).

- copy `reference/BRIEF.template.md` → `<workspace>/BRIEF.md` (only if absent)
- copy `reference/ontology.template.md` → `<workspace>/context/_ontology.md` (only if absent)
- create dirs: `context/{people,orgs,goals,projects,processes,tools}/` · `act-and-decide/{patterns,decisions,runs}/` · `update-context/`

---

## Step 6 — Build the initial context (a BIG first crawl)

Run the crawler **hard** to populate the brain: invoke **`/jupi:update-context full`** in `<workspace>`.

This first run should be **exhaustive** — drain the whole backlog, profile **every** person / org / project / process / tool reachable (with provenance), and generate `context/_ontology.md`. **The richer this seed, the better every later decision.** If some MCPs are unconnected, note them and do the most with what's reachable.

---

## Step 7 — Schedule the two LOCAL routines (visible to the user)

Create **two** routines, each bound to `<workspace>` as its working folder. **They must be VISIBLE and controllable by the user** → create them in **Claude Desktop → Code → Routines** (a "scheduled task" system the user can't see in that UI is NOT acceptable). If you can't write there programmatically, **hand the user the exact steps + content** and have them create each one:

| Routine | Command | Schedule |
|---|---|---|
| **Context refresh** | `/jupi:update-context full` | **daily, early morning** — `0 6 * * *` |
| **Act & decide** | `/jupi:act-and-decide` | **every 10 minutes** — `*/10 * * * *` |

Per routine: *New routine → **Local** → working folder = `<workspace>` → command above → schedule above → save.* The refresh learns once a day; **act-and-decide runs every 10 min** to handle things as they arrive.

> Local routines = **persistent filesystem**: the state lives in `<workspace>` between runs (no git needed). The machine must be on at run time.

---

## Step 8 — Fire the first act-and-decide

Run **`/jupi:act-and-decide`** once, now, so the user sees a real result come out the other end: a **private decision in Jupi** — or, if the server doesn't yet expose the privacy flag (`allowWorkspaceContributions`), a clear **"nothing posted, here's why"** (the guardrail). Either way the user sees the loop work end-to-end.

---

## Final report

Per step: the **brain folder**; **Jupi** status (the blocker); **other tools** connected vs skipped (+ capability lost); **permission mode** (detected/written); the **workspace tree**; the **big seed** result (files created, unreachable tools); the **two routines** (created, or the UI steps handed over); and the **first act-and-decide** outcome. Flag anything still needing the user (OAuth, manual routine creation).
