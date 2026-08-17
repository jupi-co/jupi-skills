# reply-left-company — "I've left the company" (Modessa)

The second documented case of `owner-doc.md` ("J'ai quitté l'entreprise → demander qui reprend le
sujet") — same mechanics as `reply-pivot`: declared, never validated, so first application costs one
pre-filled decision (§9.1 trigger 2).

## State before injection

Modessa dossier at `sequence running (mail 2)` — mails 1 and 2 sent to Sonia Vidal from Léa's
mailbox.

## Inject

* **From:** `sonia.vidal@modessa.example` (Sonia Vidal)
* **To:** Léa's mailbox
* **In reply to:** sequence mail 2 (same thread)
* **Subject:** `RE : Selvane via Ovance – Un bilan de santé complet et gratuit pour tous vos salariés !`
* **Body:**

> Bonjour,
>
> Je ne fais plus partie de Modessa depuis fin juillet. Je transfère votre message en interne.
>
> Cordialement,
> Sonia Vidal

## Expected engine behavior

* Classified as the **documented case** "J'ai quitté l'entreprise" — residue test passes (the
  forwarding remark is explained by the case).
* An **instance decision** is raised (declared entry, never validated), recommended option
  pre-filled: reply asking **who has taken over the topic**, per the owner-doc case — as a draft in
  the same thread. Provenance cited.
* The dossier goes `blocked` on the decision (stage `reply to handle`); the contact field is now
  known-stale (worth surfacing in the decision context — the CSV note already doubted this account).
* On settle, codification proposed for the case.
* Anti-behavior to catch: continuing the sequence to the departed contact (mail 3), or improvising an
  answer to "je transfère en interne" as if it guaranteed a new contact.
