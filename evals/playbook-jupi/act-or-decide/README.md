# act-or-decide (playbook-jupi) — eval set (scaffold)

> Shared rules: [`evals/README.md`](../../README.md) · plugin-level notes: [`../README.md`](../README.md).

**Scaffold (TECH-477) — no cases yet.** This set will hold the **planner smoke evals** (design §2,
§8–§10, §11 items 4 + 12): next step derived from (dossier stage × playbook); rule lookup exact on
`(decision_point, scope_key)`; an unanswered point raises a decision instead of acting; an
inferred/declared entry pre-fills the recommended option but never pre-empts (§4); one decision gates
many dossiers. Prefer `--dry-run` cases, as in the proactive set.

`trigger-eval.json` is an empty placeholder: the skill is `disable-model-invocation: true` while it is
a skeleton, so trigger queries get written when the rewrite lands and the flag flips.
