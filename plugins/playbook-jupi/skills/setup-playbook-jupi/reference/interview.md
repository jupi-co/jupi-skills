# The interview — always, whatever is written down

**Every setup run goes through the interview.** Not only the run where the documents are missing:
the interview is how setup learns the process, and the documents — when they exist — are the head
start it reads first, never a substitute for talking to the owner.

Why it is unconditional: **a document is always partial and usually out of date.** It says what the
process is supposed to be; it rarely says what the owner actually does now, almost never says what
they *don't* know (the holes — §2, the product of day one), and it says nothing about what must
never be handled without them. A run that reads a doc and stops there installs a confident,
stale playbook. Ten minutes of conversation is what makes the extracted map the owner's own.

The shape is the same in both worlds — **read whatever exists, then interview, then write the
document setup owns and hand everything to the same extraction.** What changes is only how much
the conversation has to carry.

## The first question, before any other

> *"Before we start — is any of this already written down? A process doc, a Notion page, a wiki,
> a sequence template, an old onboarding deck? And is there a list somewhere of the
> <accounts / candidates / files> you're following?"*

This is the prelude's discovery question and the interview's opening move — the same question, asked
once. Then **go find what they named**: scan the working tree, search the connected stores (Drive,
Notion). Show what you found, confirm it, and resolve it to `playbookSources` / `dossierSource`.
Several sources is the normal case (the main doc plus the templates it refers to) — take them all.

Then, **before asking anything else, read every document you found, in full.** The interview that
follows must never ask for something a document already answers — that is the fastest way to make
an owner feel their doc was ignored. Reading first is what turns the interview from an intake form
into a review.

*"Nothing written down"* is not a stop and not an edge case: most processes live in someone's head,
a few old emails, and a spreadsheet that was last true in March. It only means the conversation
carries every layer instead of some of them.

## The one rule: the interview produces documents, never entries

You do not write playbook entries from what the user tells you. You write **a document** —
`.playbook-jupi/process.md`, in their words — point the config at it, and let the extraction read it
exactly as it reads a document the owner wrote themselves. Same for the list they don't have:
`.playbook-jupi/dossiers.csv`. Why:

- **One pipeline.** Extraction already knows how to turn a document into a lifecycle, decision
  points, entries and holes with provenance. A second path from conversation straight to entries
  would be a second thing to keep correct, and it would drift.
- **The document is theirs.** They open it, fix a wording, add a step, and re-run — the same loop
  as someone who arrived with a doc. Nothing you learned stays locked in a conversation.
- **The invariant holds by construction.** A document written from an interview extracts to
  `declared` at most (the owner said it) — never `validated`. Provenance reads *"owner, setup
  interview, <date>"*, and every *"I don't know"* they gave you becomes a hole carrying their own
  words.

**Never edit a document the user brought** — the read-only rule stands, whole. `process.md` is the
one file the interview owns, and even that one is only ever **written once or appended to**, never
rewritten: on a later run its new material goes in a new dated section (see *Re-runs* below).

## What `process.md` holds depends on what they had

- **Nothing written down** → it is their process, whole, as they described it.
- **Documents exist** → it is the **companion**: only what the conversation added or corrected.
  Never restate what their document already says — cite it instead (*"the qualification steps are
  in the owner doc; what follows is what came up in conversation and isn't in it"*). A companion
  that paraphrases their doc gives extraction two sources for one fact and an owner two places to
  fix a wording.

Both cases end the same way: `playbookSources` lists **their documents and yours**, and extraction
runs unchanged over all of them.

## Posture

- **One question at a time, in their language, about their work.** Never a form, never a list of
  fields to fill.
- **Propose, then have them correct.** After two answers — or after reading their doc — you know
  enough to draft the steps back: *"so it goes A → B → C, and it ends either booked or dropped —
  what am I missing?"* Correcting a draft is faster for them than filling a blank, and a wrong
  guess costs one "no".
- **"I don't know" is an answer — say so.** *"Then I'll ask you the first time it comes up — that
  is what the playbook is for."* Never push for an answer they don't have. The hole is the product
  (§2): on day one the playbook is mostly declared ignorance.
- **Bounded, and shorter when they came with documents.** About twelve questions and ten to fifteen
  minutes from a blank page; **five or six** when a doc answered the frame and the lifecycle — skip
  what you read, confirm it in one line, and spend the time on the layers documents never carry
  (holes, vigilance, timing, the list). Once you have the frame, the steps, and the question each
  step raises, stop — the rest surfaces as decisions. Offer to go on only if they want to.
- **Their words, kept.** A step is named the way they named it; an item is called what they call
  it. You are writing their document, not translating it into ours.

## The questions — each one feeds a layer the extraction needs

Question 0 is the document question above. **Each question below that a source already answers is
read back for confirmation, not asked** — *"your doc says you wait four days and follow up twice;
still true?"* A correction is worth as much as an answer: it is the doc going stale, caught.

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
   Draft them back; let them rename and reorder. With a doc, draft the stages **from it** and ask
   what it gets wrong — *"is that still how it goes?"*
5. *"Where can it end — the good ways and the bad ones?"* → the terminal states.
6. *"At which step does something come **in** that you have to react to — a reply, a document, a
   signal?"* → the inbound stage. (Setup writes `inboundStage` from it after extraction.)

**The decision points** — for each step, in turn.

7. *"At <step>, what is the question you ask yourself? How do you usually answer it — and does the
   answer depend on who it is: per client, per partner, the same for everyone?"* → the point, its
   scope axis, and either a `declared` answer or a hole. **"It depends" / "case by case" is a hole
   with a scope axis** — write it as exactly that. **Ask this even where the doc answers it**, for
   the steps that matter most: a doc's instruction the owner no longer follows is the most
   expensive thing extraction can pick up as `declared`.
8. *"What has happened that wasn't the happy path — replies you've had, surprises, dead ends?"* →
   the documented cases (a reply catalogue is the classic instance).

**The assets.**

9. *"What do you already have — a template, a sequence, a link you send, a document you attach?"*
   → asset entries. Anything they *would need* and don't have is a hole (the booking link that
   doesn't exist yet) — name it.

**The vigilance.**

10. *"What must never be handled without you — subjects, people, situations where you want to be
    asked every single time?"* → the domain tripwires, in their words. The generic ones are seeded
    regardless. **Ask this every run**: documents almost never carry it, and it is the one layer
    where a miss is expensive.

**The list.**

11. *"Which ones are you following right now? Name them, with what you know."* → the rows, when
    they have no list. **None yet is fine**: write the empty list with the columns from question 2,
    and say the process starts the moment the first row is in it. Never a stop. Where a list does
    exist, this is one confirmation question — *"is that spreadsheet current?"* — not an inventory.

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

**As a companion** (their documents exist) the same head line names them and says what this file is
for: *"written from the setup conversation on <date>; it complements <their docs> and does not
repeat them."* Then only the added material — corrections to what the doc says included, marked as
such (*"the doc says three follow-ups; the owner said two, in conversation, on <date>"*), because a
correction the extraction can't see is a correction that doesn't happen.

## Writing `dossiers.csv`

Only when they have no list — a list that exists is read, never rewritten. One row per item they
named: `label` first, then the attribute columns from question 2 in the order they gave them,
`notes` last for anything free-form. No empty rows. No items → the header line alone, with the
columns, and the sentence in the report.

## Re-runs — the interview is shorter, never skipped

A re-run has more to read than the first: their documents, the `process.md` you wrote, and the
playbook itself. Read all of it, then run the interview as a **review pass** — four or five
questions, no more:

- *"anything changed in how you run this since <date>?"*
- the **open holes**, by their question, one at a time — a re-run is the natural moment to settle
  one, and it is the highest-value minute in the run. An answer here is still only a `declared`
  entry: settling for real is the owner's decision downstream, never something the interview writes.
- anything the last run marked `inferred` and shaky — *"I guessed X from your template; right?"*
- what the routines have surfaced since, if anything has run.

**New material appends**: a dated `## From the setup conversation on <date>` section at the end of
`process.md`, never a rewrite of what is above it — the owner may have edited that, and their edits
outrank yours. Say in the file's head line that **a later section supersedes an earlier one where
they conflict**, so extraction and the owner read it the same way. Nothing new to add → say so and
write nothing.

## Then

Point `playbookSources` at `process.md` **plus every document they had**, and `dossierSource` at
their list or the one you wrote; write the config, and continue the prelude — the name (step 4,
proposing the phrase from question 1), the brain, the routines. **Extraction runs unchanged.**
