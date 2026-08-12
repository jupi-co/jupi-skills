# dev/mirror — the fake closed-world for the pilot bench

A 1:1 mirror of the pilot's real use case with **every entity renamed** — content, not code. It is what
the dev bench (TECH-486) seeds from and what the smoke evals (TECH-499) reuse. It lives outside
`plugins/` for the same reason `evals/` does: fixtures must never travel in the packaged `.plugin`.

The engine under test is `plugins/playbook-jupi`. The design references in this pack ("design §N")
point to the internal plugin-design doc; the walkthrough moments in `scenarios/` mirror its §8.

## The zero-real-entities rule

**Nothing under `dev/mirror/` may name a real entity from the pilot** — not the client, the people,
the partner or broker brands, the insurers, the pilot accounts, nor any real URL (scheduler, video,
site). Fake companies are invented names with no evident real-world collision; fake domains all use
`.example` (RFC-reserved, unresolvable by design — a fixture address can never reach a real mailbox).

**The real → fake mapping table and the canonical grep list are deliberately NOT in this repo** (it is
public). They live in a private comment on the Linear ticket
[TECH-483](https://linear.app/jupi-co/issue/TECH-483/) — before committing any change to this
directory, run the grep command from that comment over `dev/mirror/` and require **zero hits**.

## The cast (fake side)

| Fake | Role in the mirror |
|---|---|
| **Selvane** | The health-prevention service doing the outreach (the sender company) |
| **Claire Bonnaire** | Cofounder of Selvane — the process owner and decider; the 45-min kickoff is hers |
| **Léa Marchal** | Ops — the outreach runs from her mailbox; the 15-min qualification call is hers |
| **Ovance (HGA)** | The partner offer through which target companies already have Selvane access |
| **Previa** / **Assurial** | The two complémentaires santé behind the Ovance offer |
| **Delmon Conseil** | The broker shared by all 5 pilot accounts (the contactability decision's scope) |
| **Nodaviz · Plyme · Agrolane · Ferval Industries · Modessa** | The 5 pilot accounts (`accounts.csv`) |

## Files

| File | Mirrors | Feeds |
|---|---|---|
| `accounts.csv` | The owner's reporting spreadsheet (the 5 pilot accounts) | Dossier creation (bench seed; later the bootstrap skill) |
| `owner-doc.md` | The owner's own process doc — **the extraction source** | Playbook extraction (personas, documented cases, best practices — holes included) |
| `sequence-partner.md` | The 3-mail reference sequence for the Ovance (HGA) partner | Sequence instantiation + adaptation per partner |
| `scenarios/*.md` | One scripted moment of the design-§8 walkthrough each | Bench injection + eval assertions (each file: the mail to inject + the expected engine behavior) |

## Scenarios

Each scenario is **independent** — inject one at a time into a clean bench state; they are not a
single timeline (two of them target the same account on purpose, mirroring the real walkthrough).

| Scenario | Account | The moment it scripts |
|---|---|---|
| `reply-pivot` | Nodaviz | "Not the right person, see Mme X" — a case documented in `owner-doc.md`, never validated |
| `reply-left-company` | Modessa | "I've left the company" — documented case, ask who replaced them |
| `reply-out-of-script-gdpr` | Plyme | Polite decline **plus** "who gave you our contact details?" — the residue-test + tripwire case |
| `reply-positive-booking` | Ferval Industries | Positive reply — booking is a non-draftable engaging act |
| `no-reply-fallback` | Agrolane | Day 4, no reply, no follow-up timing established — parameter decision |
| `reply-english` | Plyme | An English reply — language edge case, first occurrence raises a decision |

## Don't over-polish

The mirror keeps the real world's imperfections **on purpose** — they are what the engine is tested
on: `owner-doc.md` never states the follow-up timing (X messages / Y days is a declared hole), its
contactability note is vague and names no broker (debatable `inferred` material, not a rule), mail 3
links a one-pager that does not exist, and the insurer per account is sometimes uncertain. Fixing
these "bugs" breaks the fixtures. When in doubt, keep it messy and let the review decide.
