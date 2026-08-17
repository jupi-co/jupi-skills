# reply-pivot — "not the right person, see Mme X" (Nodaviz)

The documented-case moment of the walkthrough (design §8): a reply matching a case written in
`owner-doc.md` ("Ce n'est pas moi, voyez avec X") that has **never been validated** — a `declared`
entry, so it still costs one decision on first application (§9.1 trigger 2), but a one-click one.

## State before injection

Nodaviz dossier at `sequence running (mail 1)` — mail 1 of the Ovance sequence sent to Hugo Ferrand
from Léa's mailbox.

## Inject

* **From:** `hugo.ferrand@nodaviz.example` (Hugo Ferrand)
* **To:** Léa's mailbox
* **In reply to:** sequence mail 1 (same thread)
* **Subject:** `RE : Selvane via Ovance – Un bilan de santé complet et gratuit pour tous vos salariés !`
* **Body:**

> Bonjour,
>
> Ce n'est pas moi qui gère ces sujets — je vous invite à voir avec Mme Delorme, notre DRH adjointe,
> c'est elle qui suit la complémentaire santé.
>
> Bonne journée,
> Hugo Ferrand

## Expected engine behavior

* The reply is classified as the **documented case** "Ce n'est pas moi, voyez avec X" from
  `owner-doc.md` — the residue test passes (every material element of the mail is explained by the
  case; the new contact's name is the case's X).
* Because the case is `declared` but **never validated**, the engine does **not** act silently: it
  raises an **instance decision** (§9.1 trigger 2) with the recommended option pre-filled — pivot the
  sequence to Mme Delorme — and the provenance cited (the owner-doc case list).
* The recommended option carries the concrete pivot **draft** (mail 1 re-addressed to Mme Delorme,
  same thread context), ready to read. No mail is sent; no draft leaves Léa's mailbox by itself.
* The Nodaviz dossier goes `blocked` on that decision (stage `reply to handle`).
* On settle, **codification is proposed** (this case's first instance): next occurrence of the same
  case should draft directly under the validated rule.
* Anti-behavior to catch: silently sending or drafting to Mme Delorme with no decision, or treating
  the reply as a decline.
