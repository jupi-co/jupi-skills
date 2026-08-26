# playbook-jupi — eval sets (scaffold)

Eval sets for the `playbook-jupi` plugin's **rewritten** skills. They are nested under
`evals/playbook-jupi/` because the skill names (`refresh-backlog`, `act-or-decide`) collide with the
proactive-jupi sets at the repo root; `run-eval.sh` takes the nested form as the skill argument:

```bash
./evals/run-eval.sh layout playbook-jupi/act-or-decide
```

> **Status: cases filled (TECH-499)** — extraction (4), planner smoke (6), inbound watch (4), plus
> trigger sets for the two auto-invocable skills, all reusing the `dev/mirror/` scenarios' expected
> behaviors. Teardown: `purge-scratch.mjs` (one script for all three sets — the bench reset core
> with its synthetic-tenant guard). Run per `evals/README.md`: layout → executor subagents
> (with_skill + baseline) → grade → benchmark → view; **dry-run cases first, never perform mode.**

The **copied-verbatim** skills (`execute-action`, `act-post-decision`, `update-brain`) get no sets
here: they are byte-synced copies of the proactive-jupi originals (see the `synced from
proactive-jupi@…` marker in each), so the existing root-level sets cover them.

**Isolation + teardown rules are shared — read [`evals/README.md`](../README.md) first.** Everything
there applies unchanged (same Neon `eval:` prefix + synthetic `jupiUserId`, same Supermemory scratch
container, same Jupi test workspace, same no-tool-writes rule). One addition once cases exist: fixture
dossiers and playbook stores must be fictional — never a real account, contact, or customer document.
Per-set purge scripts arrive with the cases.

## The sets

| Skill | Trigger eval | Behavioral | What it covers |
|---|---|---|---|
| [`setup-playbook-jupi`](setup-playbook-jupi/) | ⛔ n/a (`disable-model-invocation` by design) | ✅ 4 cases | Extraction (holes incl. the deliberate doc ambiguities, zero validated), per-row dossier stages, idempotence + owner-protection, injection resistance |
| [`refresh-backlog`](refresh-backlog/) | ✅ | ✅ 4 cases | Attach to the right dossier, unmatched reported never created, ambiguous = no write, cursor honesty on unreachable source |
| [`act-or-decide`](act-or-decide/) | ✅ | ✅ 6 cases | Run-1 = 2 [BR] 0 drafts (dry-run writes nothing), the gate discriminates, GDPR = forced out-of-script + tripwire, pivot stays one-click, unvalidated tripwires bind, budget cuts never silent |
