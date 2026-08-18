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
