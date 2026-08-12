# setup-playbook-jupi — eval set (scaffold)

> Shared rules: [`evals/README.md`](../../README.md) · plugin-level notes: [`../README.md`](../README.md).

**Scaffold (TECH-477) — no cases yet.** This set will hold the **extraction smoke evals** (design §11,
items 2 + 12): given a fictional owner document + reporting-spreadsheet fixture, the bootstrap creates
the playbook store with the §7 doc skeleton, the account dossiers, and entries correctly split
`inferred` vs `declared` with declared holes ("not established") — and nothing extracted lands as
validated/pre-authorized (§4).

No `trigger-eval.json`, mirroring `setup-proactive-jupi`: the skill is `disable-model-invocation` by
design, so there is nothing to trigger-tune.
