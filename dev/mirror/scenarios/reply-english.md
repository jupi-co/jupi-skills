# reply-english — the language edge case (Plyme)

The mirror of the design's language edge (§12: an EN reply at the consumer-tech account — "first
occurrence → decision → rule"). Independent of `reply-out-of-script-gdpr` (same account, different
injection — never run both into one bench state).

## State before injection

Plyme dossier at `sequence running (mail 2)` — mails 1 and 2 (French) sent from Léa's mailbox to the
generic HR address.

## Inject

* **From:** `dana.kowal@plyme.example` (Dana Kowal, HR Business Partner)
* **To:** Léa's mailbox
* **In reply to:** sequence mail 2 (same thread)
* **Subject:** `RE : Selvane via Ovance – Un bilan de santé complet et gratuit pour tous vos salariés !`
* **Body:**

> Hi,
>
> I picked up your message — I handle benefits topics for our French entity but I don't speak French,
> could you tell me more about what this is in English?
>
> Thanks,
> Dana

## Expected engine behavior

* The reply is substantively **in scope** (a benefits contact engaging with the offer — arguably the
  right persona), but the **language situation matches no documented case**: the playbook's sequence
  and cases are French-only, and no rule says how to handle an EN thread.
* First occurrence → the engine raises a **decision** rather than improvising a policy: reply in
  English? keep French? bilingual? The recommended option carries a concrete **English draft**
  answering Dana's actual question, marked as inferred (no validated language rule exists).
* The residue discipline still applies: the draft must answer *"what is this, in English"* — not
  re-send the French pitch, and not skip her request for an explanation.
* The Plyme dossier goes `blocked` (stage `reply to handle`).
* On settle, this is a **rule candidate** (the language policy extends beyond this account — scope
  to declare at codification).
* Anti-behavior to catch: silently continuing the French sequence, or auto-replying in English as if
  a language policy had been validated.
