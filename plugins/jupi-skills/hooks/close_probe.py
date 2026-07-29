#!/usr/bin/env python3
"""Stop hook for the jupi-skills plugin.

Closes the turn's trace, which is what triggers the server's scoring —
`fired`, `reached_write`, and `nudge_converted`. A turn never closed is swept
as `abandoned` after 30 minutes, so a missing close costs the turn its
outcome but not its existence.

The state file is deleted whatever the response. That is what makes closing
idempotent: a second `Stop` finds no state and stays quiet rather than
collecting a 409.

Fails open and silent: any error exits 0 with no output.
"""
import json
import sys
from datetime import datetime

import telemetry


def _outcome(_data: dict) -> str:
    """Always `completed`, pending CLIENT-SPEC.md §6.1.

    `Stop` fires on interrupt and on error as well as clean completion, but
    whether its payload distinguishes them is unverified. Guessing would report
    `error` for every Ctrl-C, so this reports the one value that is never
    actively wrong and leaves `outcome` carrying no signal until the payload is
    dumped (set $JUPI_TELEMETRY_DEBUG and run the three cases).
    """
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
