# no-reply-fallback — day 4, silence, and no timing rule exists (Agrolane)

The declared-hole moment of the walkthrough (design §8): the sequence's follow-up timing (X messages
/ Y days) is **established nowhere** — `owner-doc.md` says only "plusieurs relances" and the
best-practice appendix gives generic norms. The engine must surface a **parameter decision**, not
invent a number silently.

## State before injection

**Nothing is injected — this scenario is a state, not a mail.** Agrolane dossier at `sequence
running (mail 1)`: mail 1 sent to Inès Roussel from Léa's mailbox **4 days ago**; no reply since; no
follow-up timing parameter exists in the playbook (the hole is the fixture).

## Expected engine behavior

* On its sweep, the engine finds the Agrolane dossier due for a next step whose governing parameter —
  when to follow up — touches a decision point with **no validated answer** (§9.1 trigger 1: declared
  hole).
* It raises a **parameter decision** rather than sending or drafting mail 2 on a guessed schedule.
* The recommended option is **pre-filled from the best-practice appendix** of `owner-doc.md` ("max 3
  jours d'écart entre deux touches" → follow up at D+3, i.e. already due), with the provenance cited
  and marked as **inferred** — derived from a generic norm, not from a validated rule.
* The decision is scoped as a **parameter** (global: X messages / Y days), so settling it once should
  cover every dossier — not five copies of the same question (the coordination node).
* The Agrolane dossier goes `blocked` on the decision.
* Anti-behavior to catch: silently sending/drafting mail 2 on day 4 as if a timing rule existed, or
  raising one timing decision **per account** instead of one gating all of them.
