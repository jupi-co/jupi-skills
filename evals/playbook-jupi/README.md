# playbook-jupi — eval sets (scaffold)

Eval sets for the `playbook-jupi` plugin's **rewritten** skills. They are nested under
`evals/playbook-jupi/` because the skill names (`refresh-backlog`, `act-or-decide`) collide with the
proactive-jupi sets at the repo root; `run-eval.sh` takes the nested form as the skill argument:

```bash
./evals/run-eval.sh layout playbook-jupi/act-or-decide
```

> **Status: scaffolded with the plugin (TECH-477), cases TODO.** The skills these sets target are
> skeletons (`disable-model-invocation: true` until their rewrites land), so there is nothing to run
> yet. Extraction + planner smoke evals land with the evals item of the build plan (§11, item 12);
> trigger sets get filled when the two auto-invocable skills flip to `disable-model-invocation: false`.

The **copied-verbatim** skills (`execute-action`, `act-post-decision`, `update-brain`) get no sets
here: they are byte-synced copies of the proactive-jupi originals (see the `synced from
proactive-jupi@…` marker in each), so the existing root-level sets cover them.

**Isolation + teardown rules are shared — read [`evals/README.md`](../README.md) first.** Everything
there applies unchanged (same Neon `eval:` prefix + synthetic `jupiUserId`, same Supermemory scratch
container, same Jupi test workspace, same no-tool-writes rule). One addition once cases exist: fixture
dossiers and playbook stores must be fictional — never a real account, contact, or customer document.
Per-set purge scripts arrive with the cases.

## The sets

| Skill | Trigger eval | Behavioral | What will land here (design §) |
|---|---|---|---|
| [`setup-playbook-jupi`](setup-playbook-jupi/) | ⛔ n/a (`disable-model-invocation` by design) | TODO | Extraction smoke: funnel + decision points + inferred/declared entries + declared holes from a fixture doc (§2–§4, §11.2) |
| [`refresh-backlog`](refresh-backlog/) | TODO | TODO | Inbound watch: attach-don't-discover, out-of-dossier inbound reported not created (§8) |
| [`act-or-decide`](act-or-decide/) | TODO | TODO | Planner smoke: next step from (stage × playbook), exact rule lookup on (decision_point, scope_key), holes → decisions (§2, §8–§10) |
