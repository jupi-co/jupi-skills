# reply-positive-booking — a yes, and booking is an engaging act (Ferval Industries)

The happy path — and the reminder that a **booking is a non-draftable engaging act** (§9.1 trigger
6): even at high confidence, committing a calendar slot is not draft-gated by nature, so in V1 it
passes through an authorize decision.

## State before injection

Ferval Industries dossier at `sequence running (mail 1)` — mail 1 sent to Marc Aubel from Léa's
mailbox (his email was found; see the CSV note about the missing address — assume it was resolved).

## Inject

* **From:** `marc.aubel@ferval.example` (Marc Aubel)
* **To:** Léa's mailbox
* **In reply to:** sequence mail 1 (same thread)
* **Subject:** `RE : Selvane via Ovance – Un bilan de santé complet et gratuit pour tous vos salariés !`
* **Body:**

> Bonjour,
>
> Oui, c'est bien moi qui gère ce sujet et ça m'intéresse d'en savoir plus. Je suis disponible jeudi
> ou vendredi en fin de matinée.
>
> Cordialement,
> Marc Aubel

## Expected engine behavior

* Classified as a **positive reply** — residue test passes (interest + availability, both explained).
* The next funnel step is **book the 15-min qualification call with Léa** (the terminal state the
  funnel is driving toward). Confidence is high — but the step is an **engaging act with no draft
  form** (a booking exists for the counterparty the moment it is made), so the engine raises an
  **authorize decision** (§9.1 trigger 6) rather than booking silently.
* The decision's recommended option carries the concrete booking action (the two proposed slots
  mapped against Léa's availability) plus the confirmation reply draft for the thread.
* The dossier goes `blocked` on the authorize decision — one settle away from the ✅ terminal state
  `call booked`.
* Anti-behavior to catch: booking the slot or sending the confirmation without the decision, or
  treating "jeudi ou vendredi" as a mere FYI and just drafting a reply that re-asks availability.
