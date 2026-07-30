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

It also opens the turn's telemetry trace, because it already computes the
ideation classification and a second hook recomputing the same regex would
drift from this one within a week. That classification is the recall
denominator: it is emitted on *every* turn, including the turns where no skill
fires, since those are exactly the turns a recall metric has to count.

The nudge is printed before any telemetry runs, and the telemetry is wrapped in
its own handler. Nothing about the fail-open contract above changes: telemetry
can fail, hang, or be misconfigured without affecting the nudge or the prompt.
"""
import json
import re
import sys

import telemetry

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


TRACE_LINE = (
    "[jupi-skills] trace: {trace_id} — pass as `traceId` on any Jupi MCP tool "
    "call this turn."
)


def _open_turn(data: dict, prompt: str, nudged: bool) -> None:
    """Open the turn's trace. Never raises; the caller's output is already out.

    State is written only once the server has accepted the `open`, so a probe
    finding no state knows the turn does not exist server-side and stays quiet
    instead of collecting a 404 per event.
    """
    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return

    # Drop the previous turn's state first. Without this, a turn whose `open`
    # fails would leave the last successful turn's trace id in place and hang
    # this turn's skills off an already-closed trace.
    telemetry.delete_state(session_id)
    telemetry.sweep_stale_state()

    trace_id = telemetry.new_trace_id()
    status = telemetry.send_open(
        trace_id,
        session_id=session_id,
        ideation=bool(_PATTERN.search(prompt)),
        nudged=nudged,
        user_input=prompt,
    )
    if status != 202:
        return

    telemetry.write_state(
        session_id,
        {
            "trace_id": trace_id,
            "started_at": telemetry.utc_now(),
            "skill_events": 0,
        },
    )
    # Printed only on 202: a trace id the server never opened would be passed
    # to MCP tools that then find no turn to nest under.
    print(TRACE_LINE.format(trace_id=trace_id))


def main() -> int:
    data: dict = {}
    prompt = ""
    nudged = False
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        data = json.loads(raw)
        telemetry.debug_dump("UserPromptSubmit", data)
        prompt = data.get("prompt", "")
        if isinstance(prompt, str) and _PATTERN.search(prompt):
            print(NUDGE)
            nudged = True
    except Exception:
        # Fail open: never block or error a user prompt.
        return 0

    # Separate handler, after the nudge has already been printed. Telemetry is
    # not allowed to cost the nudge.
    try:
        telemetry.configure(data.get("cwd"))
        if isinstance(prompt, str) and telemetry.endpoint():
            _open_turn(data, prompt, nudged)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
