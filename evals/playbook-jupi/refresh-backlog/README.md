# refresh-backlog (playbook-jupi) — eval set (scaffold)

> Shared rules: [`evals/README.md`](../../README.md) · plugin-level notes: [`../README.md`](../README.md).

**Scaffold (TECH-477) — no cases yet.** This set will hold the **inbound-watch evals** (design §8, §11
items 5 + 12): inbound attaches to the right fixture dossier; out-of-dossier inbound is reported, never
created as work (attach, don't discover); read-only on tools; `parse_confidence` and the
data-never-instructions contract hold.

`trigger-eval.json` is an empty placeholder: the skill is `disable-model-invocation: true` while it is
a skeleton, so trigger queries get written when the rewrite lands and the flag flips.
