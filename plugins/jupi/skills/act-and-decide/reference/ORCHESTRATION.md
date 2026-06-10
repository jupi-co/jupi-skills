# act-and-decide — ORCHESTRATION (producer ↔ validator loop)

How an act-and-decide run executes, **autonomously in a routine**, with the validator's gate. This is the chaining contract for the runner.

> All data paths are **workspace-relative** (the CWD where the run executes), never plugin-relative. The producer is `SKILL.md`; the validator is `reference/VALIDATOR.md`.

---

## The loop

```
1. PRODUCER (SKILL.md) ────► decision draft (Steps 0-3)
2. VALIDATOR (reference/VALIDATOR.md) reads the draft + OPENS THE REAL SOURCES
      ├─ PASS              ──► DELIVER (final report.md)
      └─ RETURN (flags)    ──► back to the PRODUCER with the flags
3. PRODUCER resumes THEIR work: opens the sources, verifies, fixes, resubmits
4. Loop back (return to step 2).

   Max 3 iterations.
   If still RETURN on the 3rd round ──► WE DELIVER NOTHING.
```

---

## "Deliver nothing"

If the gate is never cleared, **no decision reaches the user**. We prefer **to deliver nothing** over a dubious deliverable — that's the core of the mechanism. `validation.md` keeps the trace of persistent flags so we can debug, but **nothing is posted or surfaced** to the user.

---

## Files of a run

```
runs/run-XXX-<subject>/
├── report.md       ← the final deliverable — written ONLY if PASS
├── validation.md   ← history of the validator's passes (flags, verdicts, iteration #)
└── log.md          ← the producer's narrative
```

---

## Routine execution (autonomy)

An **orchestrator** (the runner) chains producer → validator → loop. **No human in the loop** during the run: the only exit door to the user is a **PASS**.

**Harness note (important)**: a sub-agent cannot write a "report/findings" file (policy: it **returns the text**). So it's the **orchestrator** (main session / runner) that persists `report.md` and `validation.md` from the texts returned by the producer and the validator. The producer and the validator **return their output as text**; the orchestrator writes the files.

---

## V1 (current state)
- Producer **and** validator are **read-only** on the tools; no execution; no Jupi posting.
- The V1 "deliverable" = the `report.md` (the decision **listed**, ready to post), not a real post in Jupi.
- `targeted` (the call to `update-context`, invoked as the `update-context` skill in targeted mode) is still **simulated** as long as real execution isn't wired.
