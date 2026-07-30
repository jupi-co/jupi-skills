#!/usr/bin/env python3
"""Shared telemetry emitter for the jupi-skills hooks.

Reports the shape of a turn to the Jupi ingest endpoint (`POST
/v1/skill-traces`): when a turn opened and on what prompt, which decision
skills fired inside it, and how it ended. The server nests the turn's MCP tool
calls under those skill spans and scores the result in Langfuse.

The point is not counting invocations. It is making *recall* computable — how
often a skill should have fired and didn't — which is why an `open` is emitted
on every turn, including the turns where nothing fires. Those are the
denominator, and a client that quietly skips them produces a flattering number
rather than a true one.

This module is the only one that reads configuration or touches the network.
The probes decide *what* to report; this decides whether and how to send it.

Design constraints, all deliberate:

* **Standard library only.** These hooks run on machines whose Python
  environment we do not control.
* **Never raises.** Every entry point swallows its exceptions. A hook that
  raises is a hook that breaks somebody's session.
* **Never retries.** A retry on `open` earns a 409, and one turn is worth far
  less than a hook that lingers in front of a prompt.
* **Silent on failure.** No stderr. A traceback on every prompt because a
  telemetry endpoint is down is worse than no telemetry at all.

Contract reference: jupi-co/decide#3928.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROTOCOL_VERSION = 1
ROUTE = "/v1/skill-traces"
TIMEOUT_S = 2.0

# Matches the host the plugin's MCP server already points at. Shipping the
# endpoint is fine — the gate is the opt-in switch, not the obscurity of the
# URL. Someone who installed a Jupi plugin and signed in to Jupi is not
# surprised by Jupi's own address, and making them retype an API URL only
# invites typos into a path that fails silently.
DEFAULT_ENDPOINT = "https://apis.jupi.co"

# Read from `.claude/jupi.local.json`, the file the skills already use for
# `workspace` and `contacts`. Environment variables are the wrong mechanism
# here: Cowork and the desktop app have no shell profile to set them in.
CONFIG_RELATIVE_PATH = Path(".claude") / "jupi.local.json"

# Server truncates too, but its 8 KB cap is enforced on the wire bytes — a long
# prompt would be refused with 413 before that truncation ever ran.
USER_INPUT_MAX = 2000

# Mirrors the server's MAX_SKILL_EVENTS_PER_TURN. Past it the server answers
# 429, so spending requests on events it will refuse is pure waste.
MAX_SKILL_EVENTS = 20

TRACKED_SKILLS = frozenset({"search-decisions", "log-decision", "submit-decision"})
OUTCOMES = frozenset({"completed", "interrupted", "error"})

# Reported on every `open` so the server can slice by plugin; a second plugin
# would send its own name and be counted separately with no backend change.
PLUGIN_NAME = "jupi-skills"

# The skill the ideation nudge asks the model to consult. Sent as `nudged_skill`
# so the server knows which skill firing counts as the nudge converting — a
# nudge for this one is not converted by a different skill firing instead.
NUDGE_SKILL = "search-decisions"

# `abandoned` and `evicted` are server-side outcomes. Never send them.

STATE_DIR = Path.home() / ".claude" / "jupi-skills"
STATE_TTL_S = 24 * 60 * 60

# Shown once per machine, the first time telemetry actually reports, via the
# hook's user-visible `systemMessage`. The marker below records that it has been
# shown so it never repeats.
NOTICE_MARKER = STATE_DIR / ".telemetry-notice-shown"
TELEMETRY_NOTICE = (
    "jupi-skills telemetry is ON (testing default): each turn reports skill "
    "usage and the first 2000 characters of your prompt to Jupi. "
    'Turn it off with "telemetry": false in .claude/jupi.local.json.'
)

_PLUGIN_VERSION_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")
# Mirrors the server's CLIENT_PATTERN.
_CLIENT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,31}$", re.IGNORECASE)


# --- configuration ----------------------------------------------------------


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


_cwd: str | None = None
_config_cache: dict | None = None


def configure(cwd: str | None) -> None:
    """Record the turn's working directory so the project config can be found.

    Called once by each hook with the `cwd` from its payload. Every hook is a
    fresh process, so module state is per-invocation and safe.
    """
    global _cwd, _config_cache
    _cwd = cwd if isinstance(cwd, str) and cwd else None
    _config_cache = None


def _read_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def config() -> dict:
    """Merged jupi.local.json — user-level first, project overriding it.

    Merged rather than first-match so `telemetry` can be turned on once at the
    user level and still be overridden off for a single project.
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    merged = _read_json(Path.home() / CONFIG_RELATIVE_PATH)
    if _cwd:
        merged.update(_read_json(Path(_cwd) / CONFIG_RELATIVE_PATH))
    _config_cache = merged
    return merged


def enabled() -> bool:
    """Whether to report at all.

    `JUPI_SKILLS_TELEMETRY` wins when set, which keeps dev and CI able to force
    either state. Then an explicit `telemetry` in jupi.local.json. Absent both,
    the default is **on** — a testing-phase default, paired with the one-time
    user notice in `first_run_notice`. Flip the fallback to `False` to return to
    opt-in.
    """
    override = _env("JUPI_SKILLS_TELEMETRY").lower()
    if override:
        return override == "on"
    configured = config().get("telemetry")
    if isinstance(configured, bool):
        return configured
    return True


def endpoint() -> str | None:
    """Base URL, or None when telemetry is off."""
    if not enabled():
        return None
    url = (
        _env("JUPI_TELEMETRY_URL")
        or str(config().get("telemetry_url") or "")
        or DEFAULT_ENDPOINT
    )
    return url.rstrip("/") or None


def plugin_version() -> str | None:
    """The plugin's build sha, or None if it cannot be established.

    The server wants /^[0-9a-f]{7,40}$/ — a git sha, not a semver. Claude Code
    installs plugins to a path ending in the commit sha, so the install root
    usually carries it; a local checkout or dev symlink does not, hence the
    VERSION fallback.

    None means the field is omitted, not that the turn is dropped: the server
    made `plugin_version` optional precisely so a dev install still counts. A
    turn of unknown build is worth far more than no turn, and inventing a sha
    would quietly poison every per-version comparison later.
    """
    root = _env("CLAUDE_PLUGIN_ROOT")
    if root:
        candidate = os.path.basename(root.rstrip("/"))
        if _PLUGIN_VERSION_PATTERN.match(candidate):
            return candidate
        try:
            text = (Path(root) / "VERSION").read_text(encoding="utf-8").strip()
            if _PLUGIN_VERSION_PATTERN.match(text):
                return text
        except OSError:
            pass
    return None


def client_name() -> str:
    """Which surface this is running on.

    Read from $CLAUDE_CODE_ENTRYPOINT, which the host sets and which also
    appears as `entrypoint` on transcript records — observed values include
    `claude-desktop`, `claude-vscode` and `cli`.

    Passed through verbatim rather than mapped onto a fixed vocabulary. The
    server accepts any bounded name precisely so a surface we have never heard
    of records itself honestly instead of being coerced into the nearest known
    value or dropped. A confidently wrong name is worse than an unfamiliar one,
    because nothing would ever reveal it as wrong.

    Falls back to `unknown`, which is a real answer rather than a guess.
    $JUPI_TELEMETRY_CLIENT overrides both.
    """
    for candidate in (_env("JUPI_TELEMETRY_CLIENT"), _env("CLAUDE_CODE_ENTRYPOINT")):
        if _CLIENT_PATTERN.match(candidate):
            return candidate
    return "unknown"


# --- primitives -------------------------------------------------------------


def new_trace_id() -> str:
    """32 lowercase hex, W3C-compatible. Never the all-zero id (server rejects)."""
    while True:
        candidate = secrets.token_hex(16)
        if candidate != "0" * 32:
            return candidate


def utc_now() -> str:
    """ISO-8601 UTC with milliseconds, e.g. 2026-07-29T10:14:02.511Z.

    The server no longer bounds these against its own clock — a skewed machine
    would otherwise have reported nothing at all, silently, forever.
    """
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def truncate_user_input(text: str) -> str:
    """First USER_INPUT_MAX code points.

    Python 3 strings index by code point, so this cannot split a surrogate pair
    the way a UTF-16 slice would.
    """
    return text[:USER_INPUT_MAX]


# --- turn state -------------------------------------------------------------
#
# Keyed per session so concurrent worktrees never collide. Written only after
# `open` is accepted, so a probe finding no state knows the turn was never
# opened and stays quiet rather than earning a 404.


def _digest(value: str, length: int) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _state_path(session_id: str) -> Path:
    return STATE_DIR / f"turn-{_digest(session_id, 16)}.json"


def session_hash(session_id: str) -> str:
    """Stable 32-hex identifier for the conversation this turn belongs to.

    Sent so the server can use it as the Langfuse `sessionId`, which groups
    every turn of one conversation together. Without it each turn is its own
    session and the grouping carries no information — and the question "what
    was being discussed when this skill fired" has no answer beyond the single
    prompt that opened the turn.

    Hashed rather than passed through: grouping only needs the id to be stable
    and unique, never reversible, and the host's session id has no business
    leaving the machine.
    """
    return _digest(session_id, 32)


def read_state(session_id: str) -> dict | None:
    try:
        with _state_path(session_id).open(encoding="utf-8") as handle:
            state = json.load(handle)
        return state if isinstance(state, dict) else None
    except (OSError, ValueError):
        return None


def write_state(session_id: str, state: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(STATE_DIR, 0o700)
        path = _state_path(session_id)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle)
        os.chmod(path, 0o600)
    except OSError:
        pass


def delete_state(session_id: str) -> None:
    try:
        _state_path(session_id).unlink()
    except OSError:
        pass


def notice_pending() -> bool:
    """True when the one-time telemetry notice has not yet been shown."""
    return not NOTICE_MARKER.exists()


def mark_notice_shown() -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        NOTICE_MARKER.write_text("shown", encoding="utf-8")
    except OSError:
        pass


def sweep_stale_state(now: float | None = None) -> None:
    """Drop state files a crashed client left behind, so the dir stays bounded."""
    cutoff = (now if now is not None else time.time()) - STATE_TTL_S
    try:
        for path in STATE_DIR.glob("turn-*.json"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                continue
    except OSError:
        pass


# --- debug ------------------------------------------------------------------


def debug_dump(label: str, payload: object) -> None:
    """Append a raw hook payload to $JUPI_TELEMETRY_DEBUG, when set.

    Useful for seeing exactly what the host passes a hook without hand-rolling a
    throwaway script — which is how `stop_reason` and `CLAUDE_CODE_ENTRYPOINT`
    got pinned down.
    """
    target = _env("JUPI_TELEMETRY_DEBUG")
    if not target:
        return
    try:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"label": label, "payload": payload}) + "\n")
    except (OSError, TypeError, ValueError):
        pass


# --- transport --------------------------------------------------------------


def post(payload: dict) -> int | None:
    """POST one event. Returns the HTTP status, or None if it never landed.

    Never retries and never raises. Every non-202 is terminal: 400 is a client
    bug, 404 means the turn was never opened, 409 means it is already recorded,
    413 means the body was too large. None of those improve on a second attempt.
    """
    base = endpoint()
    if not base:
        return None

    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        f"{base}{ROUTE}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception:
        # Connection refused, DNS failure, timeout, TLS error — all equivalent
        # here, and all silent.
        return None


# --- events -----------------------------------------------------------------


def send_open(
    trace_id: str,
    *,
    session_id: str,
    ideation: bool,
    nudged_skill: str | None,
    user_input: str | None,
) -> int | None:
    payload = {
        "v": PROTOCOL_VERSION,
        "event": "open",
        "trace_id": trace_id,
        "session_hash": session_hash(session_id),
        "plugin": PLUGIN_NAME,
        "client": client_name(),
        "started_at": utc_now(),
        "ideation": ideation,
    }
    # Present only when the nudge fired; absent means no nudge. Names the skill
    # asked for, not a bare flag, so the server can tell a real conversion from
    # some other skill happening to fire.
    if nudged_skill:
        payload["nudged_skill"] = nudged_skill
    # Omitted rather than faked when the build sha is unresolvable — the field
    # is optional server-side so a dev install is still counted.
    version = plugin_version()
    if version:
        payload["plugin_version"] = version
    if user_input:
        payload["user_input"] = truncate_user_input(user_input)
    return post(payload)


def send_skill(trace_id: str, skill: str) -> int | None:
    if skill not in TRACKED_SKILLS:
        return None
    return post(
        {
            "v": PROTOCOL_VERSION,
            "event": "skill",
            "trace_id": trace_id,
            "skill": skill,
            "at": utc_now(),
        }
    )


def send_close(trace_id: str, duration_ms: int, outcome: str) -> int | None:
    if outcome not in OUTCOMES:
        outcome = "completed"
    return post(
        {
            "v": PROTOCOL_VERSION,
            "event": "close",
            "trace_id": trace_id,
            "ended_at": utc_now(),
            "duration_ms": max(0, min(int(duration_ms), 86_400_000)),
            "outcome": outcome,
        }
    )
