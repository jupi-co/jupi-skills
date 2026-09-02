# The interview — when the documents don't exist yet

Read this when the prelude's discovery finds **no process document, no list of tracked items, or
only part of either**. A user with nothing written down is the normal case, not an edge case: most
processes live in someone's head, a few old emails, and a spreadsheet that was last true in March.
Setup's job is then to **write the documents from a conversation** — and hand them to the same
extraction every other setup runs.

## The one rule: the interview produces documents, never entries

You do not write playbook entries from what the user tells you. You write **their document** —
`.playbook-jupi/process.md` (their process, in their words, as they described it) and
`.playbook-jupi/dossiers.csv` (what they are following) — point the config at them, and let the
extraction read them exactly as it reads a document the owner wrote themselves. Why:

- **One pipeline.** Extraction already knows how to turn a document into a lifecycle, decision
  points, entries and holes with provenance. A second path from conversation straight to entries
  would be a second thing to keep correct, and it would drift.
- **The document is theirs.** They open it, fix a wording, add a step, and re-run — the same loop
  as someone who arrived with a doc. Nothing you learned stays locked in a conversation.
- **The invariant holds by construction.** A document written from an interview extracts to
  `declared` at most (the owner said it) — never `validated`. Provenance reads *"owner, setup
  interview, <date>"*, and every *"I don't know"* they gave you becomes a hole carrying their own
  words.

**Never edit a document that exists** — the read-only rule stands. Where they have *part* of it (a
sequence template but no process, a spreadsheet but no doc), you write only what is missing, and
the config lists both: theirs and yours. On a re-run where `process.md` already exists, there is
no interview — extraction re-reads it; offer to extend it only if they ask.

## Posture

- **One question at a time, in their language, about their work.** Never a form, never a list of
  fields to fill.
- **Propose, then have them correct.** After two answers you know enough to draft the steps back:
  *"so it goes A → B → C, and it ends either booked or dropped — what am I missing?"* Correcting a
  draft is faster for them than filling a blank, and a wrong guess costs one "no".
- **"I don't know" is an answer — say so.** *"Then I'll ask you the first time it comes up — that
  is what the playbook is for."* Never push for an answer they don't have. The hole is the product
  (§2): on day one the playbook is mostly declared ignorance.
- **Bounded.** About twelve questions, ten to fifteen minutes. Once you have the frame, the
  steps, and the question each step raises, stop — the rest surfaces as decisions. Offer to go on
  only if they want to.
- **Their words, kept.** A step is named the way they named it; an item is called what they call
  it. You are writing their document, not translating it into ours.

## The questions — each one feeds a layer the extraction needs

**The frame** — what this is, and what one item is.

1. *"Describe the process in a few sentences — what sets it off, and what does 'done' look like?"*
   → the playbook's name (their phrase for it — step 4 of the prelude proposes it back), the
   purpose, the terminal states.
2. *"What is the thing you follow through it — an account, a candidate, a contract, a request?
   Give me one real example, with what you know about it."* → the item noun (their word: it is
   what the readable playbook and every report will use) and the example's attributes, which become
   the columns of the list.
3. *"Who decides when a question comes up that nobody has settled? And who does the day-to-day?"*
   → the owner (whom decisions go to) and the operator (whose mailbox is watched, who reads the
   reports).

**The lifecycle.**

4. *"Walk me through one from start to finish — what are the steps?"* → the stages, in order.
   Draft them back; let them rename and reorder.
5. *"Where can it end — the good ways and the bad ones?"* → the terminal states.
6. *"At which step does something come **in** that you have to react to — a reply, a document, a
   signal?"* → the inbound stage. (Setup writes `inboundStage` from it after extraction.)

**The decision points** — for each step, in turn.

7. *"At <step>, what is the question you ask yourself? How do you usually answer it — and does the
   answer depend on who it is: per client, per partner, the same for everyone?"* → the point, its
   scope axis, and either a `declared` answer or a hole. **"It depends" / "case by case" is a hole
   with a scope axis** — write it as exactly that.
8. *"What has happened that wasn't the happy path — replies you've had, surprises, dead ends?"* →
   the documented cases (a reply catalogue is the classic instance).

**The assets.**

9. *"What do you already have — a template, a sequence, a link you send, a document you attach?"*
   → asset entries. Anything they *would need* and don't have is a hole (the booking link that
   doesn't exist yet) — name it.

**The vigilance.**

10. *"What must never be handled without you — subjects, people, situations where you want to be
    asked every single time?"* → the domain tripwires, in their words. The generic ones are seeded
    regardless.

**The list.**

11. *"Which ones are you following right now? Name them, with what you know."* → the rows. **None
    yet is fine**: write the empty list with the columns from question 2, and say the process
    starts the moment the first row is in it. Never a stop.

**Timing** — usually the biggest hole.

12. *"How long do you wait before following up, and how many times?"* → a timing entry — or, very
    often, *"I don't know"* → the hole the daily routine raises on the first follow-up that comes
    due.

## Writing `process.md`

Their document, not a transcript. Sections mirror what they told you: the objective, the item and
who is involved, the steps with their names, what to do at each step *as they said it*, the cases
they have seen, what they have, what they never want handled alone, timing. **Keep their
uncertainties in the text**: *"no rule yet — case by case"* is a sentence the extraction turns
into a hole with a scope axis; deleting it would turn a known unknown into an unknown one. Head
the file with one line saying it was written from the setup conversation on <date> and is theirs
to edit — a re-run re-extracts it.

## Writing `dossiers.csv`

One row per item they named: `label` first, then the attribute columns from question 2 in the
order they gave them, `notes` last for anything free-form. No empty rows. No items → the header
line alone, with the columns, and the sentence in the report.

## Then

Point `playbookSources` at `process.md` (plus any document they did have) and `dossierSource` at
`dossiers.csv`, write the config, and continue the prelude — the name (step 4, proposing the
phrase from question 1), the brain, the routines. **Extraction runs unchanged.**
