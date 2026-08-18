# Tripwires — the generic seed (§10.4)

Vigilance rules: **enumerated danger categories that force a human even when a case seems to
match.** A tripwire never says what to do — it says *"human required here."* It **overrides
confidence**: a validated rule covering the situation does not neutralize a tripwire hit; the
planner raises a decision regardless, quoting the triggering content in full.

They live as playbook entries (`point_id: "tripwire-<slug>"`) with the same lifecycle as everything
else — the owner can validate, add, or suspend them. The bootstrap seeds the generic list below and
derives **domain-specific ones from the owner's own documents** (every playbook's world has its own
sensitive topics — a health service's medical questions, a legal playbook's privileged material…);
those carry the doc as provenance.

## The generic categories

| slug | Fires when the inbound/content involves… |
|---|---|
| `tripwire-legal-data` | legal exposure, regulatory topics, or any "who gave you my data / where did you get my contact" question (GDPR-class) |
| `tripwire-anger` | anger, a complaint, or a threat — however politely worded |
| `tripwire-never-again` | any variant of "never contact me again" / unsubscribe demands |
| `tripwire-press` | press, media, or anyone identifying as a journalist |
| `tripwire-competitor` | a named competitor appearing in the exchange |
| `tripwire-partner-direct` | a partner/intermediary the process normally goes *through* writing to us directly (relationship risk) |
| `tripwire-insider` | someone from the client's own organization unexpectedly in the loop |

## How the planner applies them (§10.3–10.5)

A tripwire hit on attached inbound → **forced decision**, the triggering message quoted in full,
zero auto-draft — even in perform mode, even with a validated rule in hand. Stable is fine;
**unreviewed is not**: every hit lands in the run report.

**Unvalidated tripwires fire too — deliberately.** Tripwires are read via `pb-list-entries`, not
through `pb-get-rule`, and an `inferred`/`declared` tripwire binds exactly like a validated one.
This is the read-side gate's mirror image, not an exception to it: the gate protects the authority
to *act*; a tripwire is the opposite of that authority, so letting an unconfirmed one fire is the
conservative direction — its worst case is one unnecessary question.

## How tripwires evolve (the §6 asymmetry, inverted)

A business rule authorizes, so *adding* one is the dangerous direction and always requires the
owner. A tripwire forbids autonomy, so its dangerous direction is **removal** — and the evolution
rules invert accordingly:

- **Adding is cheap, instant, ceremony-free.** When the owner states a no-go in conversation
  ("never do X without asking me", "that topic is off-limits"), write it as a tripwire entry **on
  the spot** — `status: validated` (the owner saying it IS the authorization — §15.2's chat path),
  provenance "owner instruction, conversation <date/ref>". A **non-owner** stating one → write it
  `declared` (it fires immediately anyway, see above) and raise a suggestion decision so the owner
  can validate or retire it (§15.4: everyone suggests, the owner validates).
- **A settled out-of-script can codify as a tripwire** — when the settlement reveals a standing
  no-go rather than a "when X do Y", the codify option writes `tripwire-<slug>`, not a rule (see
  the out-of-script template).
- **Weakening only ever goes through the owner.** Narrowing, suspending, or retiring a tripwire is
  an amendment decision the owner finalizes — never a planner judgment, never a re-extraction
  overwrite (the write-side protection already refuses extraction writes on validated entries; the
  skill-level rule extends it: the planner never weakens a tripwire of any status on its own).
