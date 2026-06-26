#!/usr/bin/env python3
"""UserPromptSubmit hook for the jupi-skills plugin.

Pure model-judgment skill triggering under-fires on open-ended ideation:
the model treats "let's brainstorm X" as something it can do unaided and
skips the decision skills. This hook is a lightweight, deterministic nudge —
when a prompt looks like upstream ideation or strategy work, it injects a
short reminder so the model consults `search-decisions` *before* ideas
harden, and reserves `log-decision` for when the exploration has actually
landed.

It does no work itself and calls no model: just a keyword gate. On a match
it prints a nudge to stdout (added to context); otherwise it stays silent.
Designed to fail open — any error exits 0 with no output so it can never
block a prompt.
"""
import json
import re
import sys

# Phrases that signal upstream ideation / strategy work. Kept deliberately
# ideation-leaning so the nudge fires on the work Pierre does (brainstorming
# features, plans, and directions) rather than on every prompt. Matched as
# whole words/phrases, case-insensitively.
IDEATION_SIGNALS = [
    # ways people open a brainstorm
    r"brainstorm", r"ideat(e|ing|ion)", r"riff(ing)?", r"thinking (through|about)",
    r"think through", r"work through", r"figur(e|ing) out", r"what if we",
    r"explor(e|ing) (whether|the idea|options|a|how)", r"sketch(ing)? (out|a)",
    r"weigh(ing)? (the )?(options|pros)", r"pros and cons", r"toss(ing)? around",
    r"shap(e|ing) (a|the) (new |)?(feature|concept|plan|direction|strategy)",
    # framing a decision still being formed
    r"should we\b", r"do we (want|need) to\b", r"trying to decide",
    r"going back and forth", r"on the fence", r"leaning toward",
    # upstream artifacts / strategy domains
    r"\bnew feature\b", r"\bnew concept\b", r"\broadmap\b", r"\bprd\b",
    r"spec(cing)? (out|this)", r"writ(e|ing) (a|the) spec", r"\bspec for the\b",
    r"go-to-market", r"\bgtm\b", r"\bpositioning\b",
    r"\bpricing (tiers|model|strategy)\b", r"\borg design\b",
    r"\bstrategy (memo|offsite|doc)\b", r"prepping for", r"prep(ping)? my thinking",
]

_PATTERN = re.compile("|".join(IDEATION_SIGNALS), re.IGNORECASE)

NUDGE = (
    "[jupi-skills] This prompt looks like upstream ideation or strategy work. "
    "Before generating ideas, consider the `search-decisions` skill to surface any "
    "prior Jupi decisions or recorded business insights that bound this direction, so "
    "new ideas stay compatible with what the team has already settled. "
    "Do NOT log anything yet: reserve `log-decision` for when this exploration has "
    "actually converged on a chosen direction, not while ideas are still in play."
)


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        data = json.loads(raw)
        prompt = data.get("prompt", "")
        if isinstance(prompt, str) and _PATTERN.search(prompt):
            print(NUDGE)
    except Exception:
        # Fail open: never block or error a user prompt.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
