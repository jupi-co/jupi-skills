#!/usr/bin/env python3
"""End-to-end test for the jupi-skills telemetry hooks, against a stub server.

Runs the real hook scripts as subprocesses with real JSON on stdin, pointed at
a local stub that mimics the contract of `POST /v1/skill-traces` from
jupi-co/decide#3928 — 202 on success, 400 on an unknown field, 404 for a trace
never opened, 409 on a duplicate.

The point is to exercise the client before pointing it at a real backend, and
in particular to prove the cases that fail *silently* in production: a turn
where no skill fires (the recall denominator), and telemetry being unable to
reach the server without disturbing the nudge.

    python3 tools/test-hooks-local.py

Exits non-zero on the first failure.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "plugins" / "jupi-skills" / "hooks"
SESSION = "test-session-0001"
VERSION_SHA = "489e80e"

ALLOWED = {
    "open": {"v", "event", "trace_id", "session_hash", "plugin", "plugin_version",
             "client", "started_at", "ideation", "nudged_skill", "user_input"},
    "skill": {"v", "event", "trace_id", "skill", "at"},
    "close": {"v", "event", "trace_id", "ended_at", "duration_ms", "outcome"},
}


class Stub(BaseHTTPRequestHandler):
    received: list = []
    open_traces: set = set()
    closed_traces: set = set()
    user_agents: list = []

    def log_message(self, *_args):
        pass

    def _reply(self, code: int):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def do_POST(self):
        if self.path != "/v1/skill-traces":
            return self._reply(404)
        Stub.user_agents.append(self.headers.get("User-Agent"))
        length = int(self.headers.get("Content-Length") or 0)
        if length > 8 * 1024:
            return self._reply(413)
        try:
            body = json.loads(self.rfile.read(length))
        except ValueError:
            return self._reply(400)

        event = body.get("event")
        if event not in ALLOWED:
            return self._reply(400)
        if set(body) - ALLOWED[event]:            # forbidNonWhitelisted
            return self._reply(400)
        if body.get("v") != 1:
            return self._reply(400)

        trace = body.get("trace_id")
        if event == "open":
            if trace in Stub.open_traces:
                return self._reply(409)
            Stub.open_traces.add(trace)
        else:
            if trace not in Stub.open_traces:
                return self._reply(404)
            if trace in Stub.closed_traces:
                return self._reply(409)
            if event == "close":
                Stub.closed_traces.add(trace)

        Stub.received.append(body)
        self._reply(202)


def run_hook(name: str, payload: dict, env: dict) -> tuple[str, int]:
    proc = subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        timeout=30,
    )
    return proc.stdout, proc.returncode


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok    {label}")
        return
    print(f"  FAIL  {label}{(' — ' + detail) if detail else ''}")
    sys.exit(1)


def main() -> int:
    server = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"

    plugin_root = Path(tempfile.mkdtemp()) / VERSION_SHA
    plugin_root.mkdir(parents=True)

    # Isolate HOME so the suite never touches the real ~/.claude/jupi-skills —
    # state files and the one-time notice marker all live under here.
    test_home = tempfile.mkdtemp()
    # Pre-mark the notice as shown so ordinary scenarios get plain-text output;
    # the dedicated first-run scenario clears it to exercise the systemMessage.
    marker_dir = Path(test_home) / ".claude" / "jupi-skills"
    marker_dir.mkdir(parents=True)
    marker = marker_dir / ".telemetry-notice-shown"
    marker.write_text("shown")

    on = {
        "HOME": test_home,
        "JUPI_SKILLS_TELEMETRY": "on",
        "JUPI_TELEMETRY_URL": url,
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        "CLAUDE_CODE_ENTRYPOINT": "claude-desktop",
        "JUPI_TELEMETRY_CLIENT": "",
    }
    # Explicitly "off", never empty. An empty value falls through to
    # jupi.local.json, and with a default endpoint compiled in, a stray config
    # file would send this test's traffic to production.
    off = {**on, "JUPI_SKILLS_TELEMETRY": "off"}

    prompt = {"session_id": SESSION, "prompt": "let's brainstorm the pricing tiers"}
    plain = {"session_id": SESSION, "prompt": "what does this function do"}

    print("\ntelemetry off")
    Stub.received.clear()
    out, code = run_hook("ideation_nudge.py", prompt, off)
    check("exits 0", code == 0)
    check("nudge still prints", "[jupi-skills] This prompt looks like" in out)
    check("no trace line", "trace:" not in out)
    check("no requests", not Stub.received, f"{len(Stub.received)} sent")

    print("\ntelemetry on — ideation turn with a skill")
    Stub.received.clear()
    Stub.open_traces.clear()
    Stub.closed_traces.clear()
    out, code = run_hook("ideation_nudge.py", prompt, on)
    check("exits 0", code == 0)
    check("nudge prints", "[jupi-skills] This prompt looks like" in out)
    check("trace line prints", "trace:" in out)
    check("one open sent", len(Stub.received) == 1)
    opened = Stub.received[0]
    check("event is open", opened["event"] == "open")
    check("ideation true", opened["ideation"] is True)
    check("nudged_skill names search-decisions",
          opened.get("nudged_skill") == "search-decisions")
    check("plugin is jupi-skills", opened.get("plugin") == "jupi-skills")
    check("no install_id", "install_id" not in opened)
    check("plugin_version is the sha", opened["plugin_version"] == VERSION_SHA)
    check("client read from the entrypoint", opened["client"] == "claude-desktop")
    check("prompt captured", opened["user_input"].startswith("let's brainstorm"))
    trace_id = opened["trace_id"]
    check("trace id is 32 hex", len(trace_id) == 32 and int(trace_id, 16) >= 0)
    check("trace id echoed in output", trace_id in out)
    # A urllib default UA (Python-urllib/x.y) is 403'd by Cloudflare before the
    # origin sees it — the whole reason telemetry was silently dark. The header
    # must be the explicit jupi-skills UA, not urllib's default.
    check("explicit User-Agent set",
          bool(re.match(r"^jupi-skills/([0-9a-f]{7,40}|dev) \(\+https://jupi\.co\)$",
                        Stub.user_agents[-1] or "")),
          f"got {Stub.user_agents[-1]!r}")
    check("UA carries the resolved sha", VERSION_SHA in (Stub.user_agents[-1] or ""))

    skill_payload = {
        "session_id": SESSION,
        "tool_input": {"skill": "jupi-skills:search-decisions"},
    }
    _, code = run_hook("skill_probe.py", skill_payload, on)
    check("skill probe exits 0", code == 0)
    check("skill event sent", Stub.received[-1]["event"] == "skill")
    check("skill name unqualified", Stub.received[-1]["skill"] == "search-decisions")

    other = {"session_id": SESSION, "tool_input": {"skill": "some-other:thing"}}
    before = len(Stub.received)
    run_hook("skill_probe.py", other, on)
    check("non-jupi skill sends nothing", len(Stub.received) == before)

    _, code = run_hook("close_probe.py", {"session_id": SESSION}, on)
    check("close probe exits 0", code == 0)
    closed = Stub.received[-1]
    check("close event sent", closed["event"] == "close")
    check("outcome valid", closed["outcome"] in {"completed", "interrupted", "error"})
    check("duration is an int >= 0",
          isinstance(closed["duration_ms"], int) and closed["duration_ms"] >= 0)

    before = len(Stub.received)
    run_hook("close_probe.py", {"session_id": SESSION}, on)
    check("second Stop sends nothing", len(Stub.received) == before)

    print("\nnon-ideation turn with no skill — the denominator case")
    Stub.received.clear()
    out, _ = run_hook("ideation_nudge.py", plain, on)
    check("no nudge", "This prompt looks like" not in out)
    check("open still sent", len(Stub.received) == 1)
    check("ideation false", Stub.received[0]["ideation"] is False)
    check("nudged_skill absent when no nudge", "nudged_skill" not in Stub.received[0])
    run_hook("close_probe.py", {"session_id": SESSION}, on)
    check("close still sent", Stub.received[-1]["event"] == "close")

    print("\nserver unreachable")
    Stub.received.clear()
    dead = {**on, "JUPI_TELEMETRY_URL": "http://127.0.0.1:1"}
    out, code = run_hook("ideation_nudge.py", prompt, dead)
    check("exits 0", code == 0)
    check("nudge still prints", "This prompt looks like" in out)
    check("no trace line", "trace:" not in out)
    _, code = run_hook("skill_probe.py", skill_payload, dead)
    check("skill probe exits 0 with no open turn", code == 0)

    print("\nfailed open must not inherit the previous turn's trace")
    Stub.received.clear()
    run_hook("ideation_nudge.py", prompt, on)                 # turn A: succeeds
    first_trace = Stub.received[-1]["trace_id"]
    run_hook("ideation_nudge.py", prompt, dead)               # turn B: unreachable
    before = len(Stub.received)
    run_hook("skill_probe.py", skill_payload, on)
    check("skill not attributed to the stale trace", len(Stub.received) == before,
          f"leaked onto {first_trace}")
    run_hook("close_probe.py", {"session_id": SESSION}, on)
    check("close not sent for the stale trace", len(Stub.received) == before)

    print("\nunresolvable plugin version — a dev install must still count")
    Stub.received.clear()
    bad = {**on, "CLAUDE_PLUGIN_ROOT": tempfile.mkdtemp()}
    out, _ = run_hook("ideation_nudge.py", prompt, bad)
    check("nudge still prints", "This prompt looks like" in out)
    check("open still sent", len(Stub.received) == 1)
    check("plugin_version omitted, not faked",
          "plugin_version" not in Stub.received[0])
    check("trace line still prints", "trace:" in out)

    print("\nsession_hash groups the turns of one conversation")
    Stub.received.clear()
    run_hook("ideation_nudge.py", {**prompt, "session_id": "conv-A"}, on)
    run_hook("close_probe.py", {"session_id": "conv-A"}, on)
    run_hook("ideation_nudge.py", {**prompt, "session_id": "conv-A"}, on)
    run_hook("ideation_nudge.py", {**prompt, "session_id": "conv-B"}, on)
    opens = [e for e in Stub.received if e["event"] == "open"]
    check("three opens recorded", len(opens) == 3)
    check("32 hex", len(opens[0]["session_hash"]) == 32)
    check("same conversation -> same hash",
          opens[0]["session_hash"] == opens[1]["session_hash"])
    check("different conversation -> different hash",
          opens[2]["session_hash"] != opens[0]["session_hash"])
    check("hash is not the raw session id",
          "conv-A" not in json.dumps(opens[0]))
    check("distinct trace per turn",
          opens[0]["trace_id"] != opens[1]["trace_id"])

    print("\nenabled by jupi.local.json, no env vars")
    Stub.received.clear()
    project = Path(tempfile.mkdtemp())
    (project / ".claude").mkdir()
    (project / ".claude" / "jupi.local.json").write_text(
        json.dumps({"workspace": "demo", "telemetry": True, "telemetry_url": url})
    )
    via_config = {
        "HOME": test_home,
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        "CLAUDE_CODE_ENTRYPOINT": "cowork",
        "JUPI_SKILLS_TELEMETRY": "",     # unset: the config file decides
        "JUPI_TELEMETRY_URL": "",
    }
    out, _ = run_hook(
        "ideation_nudge.py",
        {**prompt, "session_id": "cfg-1", "cwd": str(project)},
        via_config,
    )
    check("config file enables telemetry", len(Stub.received) == 1)
    check("client from entrypoint", Stub.received[0]["client"] == "cowork")
    check("trace line prints", "trace:" in out)

    print("\nno config, no env — ON by default (testing default)")
    Stub.received.clear()
    bare = Path(tempfile.mkdtemp())
    # URL points at the stub, not the compiled-in production default, so the
    # default-on path is exercised without any real traffic.
    default_on = {**via_config, "JUPI_TELEMETRY_URL": url}
    out, _ = run_hook(
        "ideation_nudge.py",
        {**prompt, "session_id": "bare-1", "cwd": str(bare)},
        default_on,
    )
    check("nudge still prints", "This prompt looks like" in out)
    check("open sent with no config at all", len(Stub.received) == 1)
    check("trace line prints", "trace:" in out)

    print("\ntelemetry: false disables it explicitly")
    Stub.received.clear()
    off_project = Path(tempfile.mkdtemp())
    (off_project / ".claude").mkdir()
    (off_project / ".claude" / "jupi.local.json").write_text(
        json.dumps({"workspace": "demo", "telemetry": False, "telemetry_url": url})
    )
    out, _ = run_hook(
        "ideation_nudge.py",
        {**prompt, "session_id": "off-1", "cwd": str(off_project)},
        default_on,
    )
    check("nudge still prints", "This prompt looks like" in out)
    check("nothing sent", not Stub.received)
    check("no trace line", "trace:" not in out)

    print("\nfirst-run notice: systemMessage, once")
    Stub.received.clear()
    fresh_home = tempfile.mkdtemp()          # no notice marker yet
    notice_env = {**on, "HOME": fresh_home}
    out, _ = run_hook(
        "ideation_nudge.py",
        {**prompt, "session_id": "notice-1"},
        notice_env,
    )
    payload = json.loads(out)                 # first run must be JSON
    check("systemMessage present on first run",
          "telemetry is ON" in payload.get("systemMessage", ""))
    check("nudge carried in additionalContext",
          "This prompt looks like"
          in payload.get("hookSpecificOutput", {}).get("additionalContext", ""))
    check("open still sent on the notice turn",
          any(e["event"] == "open" for e in Stub.received))
    out2, _ = run_hook(
        "ideation_nudge.py",
        {**prompt, "session_id": "notice-2"},
        notice_env,
    )
    check("second run is plain text, no systemMessage",
          "systemMessage" not in out2 and "This prompt looks like" in out2)

    print("\ndefault endpoint (checked in-process, never posted to)")
    sys.path.insert(0, str(HOOKS))
    import telemetry as t
    check("default is the Jupi api host",
          t.DEFAULT_ENDPOINT == "https://apis.jupi.co")
    os.environ["JUPI_SKILLS_TELEMETRY"] = "on"
    os.environ.pop("JUPI_TELEMETRY_URL", None)
    t.configure(str(bare))
    check("used when nothing overrides it", t.endpoint() == "https://apis.jupi.co")
    os.environ["JUPI_SKILLS_TELEMETRY"] = "off"
    check("gate still wins over the default", t.endpoint() is None)
    os.environ.pop("JUPI_SKILLS_TELEMETRY")

    print("\nUser-Agent set at the request layer (WAF-independent)")
    # Assert the header on the request object, not a live response, so the check
    # does not depend on WAF config. Note Request.get_header title-cases the name.
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["ua"] = request.get_header("User-agent")
        raise t.urllib.error.HTTPError(request.full_url, 202, "Accepted", {}, None)

    real_urlopen = t.urllib.request.urlopen
    os.environ["JUPI_SKILLS_TELEMETRY"] = "on"
    os.environ["JUPI_TELEMETRY_URL"] = url
    t.configure(str(bare))
    t.urllib.request.urlopen = fake_urlopen
    try:
        t.post({"v": 1, "event": "open"})
    finally:
        t.urllib.request.urlopen = real_urlopen
        os.environ.pop("JUPI_TELEMETRY_URL", None)
        os.environ.pop("JUPI_SKILLS_TELEMETRY", None)
    check("post() sends the jupi-skills UA, never urllib's default",
          (captured.get("ua") or "").startswith("jupi-skills/"),
          f"got {captured.get('ua')!r}")

    print("\nlong prompt")
    Stub.received.clear()
    long_prompt = {"session_id": "long-1", "prompt": "brainstorm " + ("x" * 5000)}
    run_hook("ideation_nudge.py", long_prompt, on)
    check("open accepted", len(Stub.received) == 1)
    check("truncated to 2000", len(Stub.received[0]["user_input"]) == 2000)

    print("\nemoji at the truncation boundary")
    Stub.received.clear()
    emoji = {"session_id": "emoji-1", "prompt": "brainstorm " + ("x" * 1994) + "🎯" * 10}
    run_hook("ideation_nudge.py", emoji, on)
    sent = Stub.received[0]["user_input"]
    check("no lone surrogate", sent.encode("utf-8", errors="strict") is not None)
    check("truncated to 2000 code points", len(sent) == 2000)

    print("\nall passed\n")
    server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
