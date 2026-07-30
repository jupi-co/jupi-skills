#!/usr/bin/env python3
"""Stop hook for the jupi-skills plugin.

Closes the turn's trace, which is what triggers the server's scoring —
`fired`, `reached_write`, and `nudge_converted`. A turn never closed is swept
as `abandoned` after 30 minutes, so a missing close costs the turn its
outcome but not its existence.

The state file is deleted whatever the response. That is what makes closing
idempotent: a second `Stop` finds no state and stays quiet rather than
collecting a 409.

The payload also carries `last_assistant_message`. It is deliberately not sent:
the metrics need to know whether a skill fired, not what was said, and shipping
replies would widen this from "the prompt that opened the turn" to the whole
conversation.

Fails open and silent: any error exits 0 with no output.
"""
import json
import sys
from datetime import datetime

import telemetry


# `stop_reason` -> our outcome enum. `max_tokens` and `tool_use` both mean the
# turn stopped short of finishing, which is what `interrupted` records; a turn
# cut off mid-tool-use has not had the chance to invoke a skill it was heading
# for, so it must be distinguishable from one that simply chose not to.
_OUTCOME_BY_STOP_REASON = {
    "end_turn": "completed",
    "max_tokens": "interrupted",
    "tool_use": "interrupted",
}


def _outcome(data: dict) -> str:
    """Map the host's `stop_reason` onto the server's outcome enum.

    Unrecognised or missing values fall back to `completed` rather than
    guessing. A new `stop_reason` we have never seen should not turn every
    affected turn into a reported failure, and the fallback keeps this
    forward-compatible without a plugin update.
    """
    reason = data.get("stop_reason")
    if isinstance(reason, str):
        return _OUTCOME_BY_STOP_REASON.get(reason, "completed")
    return "completed"


def _duration_ms(started_at: str) -> int:
    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    now = datetime.now(started.tzinfo)
    return int((now - started).total_seconds() * 1000)


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        data = json.loads(raw)
        telemetry.debug_dump("Stop", data)
        telemetry.configure(data.get("cwd"))

        if not telemetry.endpoint():
            return 0

        session_id = data.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            return 0

        state = telemetry.read_state(session_id)
        if not state:
            return 0

        trace_id = state.get("trace_id")
        started_at = state.get("started_at")
        if not isinstance(trace_id, str) or not isinstance(started_at, str):
            telemetry.delete_state(session_id)
            return 0

        try:
            duration_ms = _duration_ms(started_at)
        except ValueError:
            duration_ms = 0

        telemetry.send_close(trace_id, duration_ms, _outcome(data))
        # Unconditional: the turn is over either way, and a stale file would
        # attach the next turn's skills to a trace the server has closed.
        telemetry.delete_state(session_id)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
