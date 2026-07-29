#!/usr/bin/env python3
"""PostToolUse hook (matcher: `Skill`) for the jupi-skills plugin.

Reports that a decision skill fired, so the turn's trace gains a
`skill:<name>` span and the MCP calls that follow can nest under it.

Without this the only evidence a skill ran would be the MCP calls it made — so
a skill that fires and calls nothing (`search-decisions` finding nothing, or
failing before it reaches the server) would be indistinguishable from one that
never fired. That is precisely the distinction being measured, which is why a
skill span with no children is a signal rather than noise.

Only the three jupi-skills decision skills are ever reported. Another plugin's
skill name must not leave the machine.

Fails open and silent: any error exits 0 with no output.
"""
import json
import sys

import telemetry


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        data = json.loads(raw)
        telemetry.debug_dump("PostToolUse:Skill", data)

        if not telemetry.endpoint():
            return 0

        tool_input = data.get("tool_input")
        if not isinstance(tool_input, dict):
            return 0
        qualified = tool_input.get("skill")
        if not isinstance(qualified, str) or not qualified:
            return 0

        # `jupi-skills:log-decision` -> `log-decision`. A bare name works too.
        skill = qualified.rsplit(":", 1)[-1]
        if skill not in telemetry.TRACKED_SKILLS:
            return 0

        session_id = data.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            return 0

        # No state means `open` was never accepted for this turn. Reporting
        # anyway would only collect a 404.
        state = telemetry.read_state(session_id)
        if not state:
            return 0
        trace_id = state.get("trace_id")
        if not isinstance(trace_id, str):
            return 0

        fired = int(state.get("skill_events") or 0)
        if fired >= telemetry.MAX_SKILL_EVENTS:
            return 0

        status = telemetry.send_skill(trace_id, skill)
        if status == 202:
            state["skill_events"] = fired + 1
            telemetry.write_state(session_id, state)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
