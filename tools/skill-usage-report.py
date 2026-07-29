#!/usr/bin/env python3
"""Offline trigger-rate report for the jupi-skills decision skills.

Reads local Claude Code transcripts (~/.claude/projects/**/*.jsonl) and answers
the question that matters before any live telemetry is built: *when the user was
doing the work these skills exist for, did the skills actually fire?*

Four numbers come out of it:

  recall      of prompts that look like ideation/strategy work, how many were
              followed by a `search-decisions` fire before the next prompt
  precision   of `search-decisions` fires, how many landed on a prompt that
              looked like ideation (a rough read on over-firing)
  funnel      of skill fires, how many reached a real Jupi MCP write
  volume      per-skill counts, and how often the ideation nudge was present

The ideation heuristic is imported directly from hooks/ideation_nudge.py rather
than copied, so the report always measures the same rule the hook enforces.

Everything is read-only and stays on this machine. Nothing is uploaded.

Usage:
    python3 tools/skill-usage-report.py
    python3 tools/skill-usage-report.py --samples 10     # show missed prompts
    python3 tools/skill-usage-report.py --json           # machine-readable
    python3 tools/skill-usage-report.py --since 2026-07-01
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# --- the skills and MCP tools we care about ---------------------------------

# Skill names as they appear in Skill tool calls, matched on the suffix after
# the plugin prefix so `jupi-skills:log-decision` and a bare `log-decision`
# both count.
TRACKED_SKILLS = {"search-decisions", "log-decision", "submit-decision"}

# The skill whose job is to fire during ideation. Recall is measured against it.
IDEATION_SKILL = "search-decisions"

# MCP tool suffixes that represent real work reaching Jupi. The server prefix
# varies by surface (mcp__claude_ai_Jupi__, mcp__plugin_jupi_Jupi__,
# mcp__<connector-uuid>__), so only the suffix is matched.
# Keep these exhaustive against the Jupi MCP. A missing entry does not error --
# it silently drops the call from the funnel, which reads as "the skill never
# reached Jupi". Every tool the server exposes belongs in one of the two sets.
JUPI_READ_TOOLS = {
    "search-decisions-tool",
    "get-decision",
    "extract-decision-insights-tool",
}
JUPI_WRITE_TOOLS = {
    "create-decision-tool",
    "add-decision-options-tool",
    "add-option-actions-tool",
    "finalize-decision-tool",
    "update-decision-tool",
    "update-decision-members-tool",
    "update-decision-option-tool",
    "update-option-action-tool",
    "delete-decision-option-tool",
    "delete-option-action-tool",
    "mark-option-action-done-tool",
    "archive-decision-tool",
}
JUPI_TOOLS = JUPI_READ_TOOLS | JUPI_WRITE_TOOLS

MCP_PREFIX = re.compile(r"^mcp__[^_]*(?:_[^_]+)*?__")

NUDGE_MARKER = "This prompt looks like upstream ideation"


def _tool_suffix(name: str) -> str:
    """mcp__plugin_jupi_Jupi__create-decision-tool -> create-decision-tool"""
    if not name.startswith("mcp__"):
        return name
    parts = name.split("__")
    return parts[-1] if parts else name


def _skill_suffix(name: str) -> str:
    """jupi-skills:log-decision -> log-decision"""
    return name.rsplit(":", 1)[-1] if name else name


# --- ideation heuristic, imported from the hook -----------------------------


def load_ideation_pattern(repo_root: Path) -> re.Pattern:
    """Import the live regex from the hook so report and hook never diverge."""
    hook = repo_root / "plugins" / "jupi-skills" / "hooks" / "ideation_nudge.py"
    if not hook.exists():
        sys.exit(f"error: cannot find the nudge hook at {hook}\n"
                 "Run this from the jupi-skills repo, or pass --hook <path>.")
    spec = importlib.util.spec_from_file_location("ideation_nudge", hook)
    module = importlib.util.module_from_spec(spec)
    # The hook's module body only compiles a regex; importing it is side-effect free.
    spec.loader.exec_module(module)
    return module._PATTERN


# --- transcript parsing -----------------------------------------------------


@dataclass
class Prompt:
    session: str
    project: str
    ts: datetime | None
    text: str
    is_ideation: bool
    nudged: bool
    skills: list[str] = field(default_factory=list)   # skills fired in this turn
    jupi_reads: int = 0
    jupi_writes: int = 0


def _parse_ts(raw) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


# Machine-generated content that lands in `user` entries but was never typed by
# the user: slash-command expansions, injected skill bodies, hook and command
# output. These must be excluded or they inflate the ideation denominator — the
# injected text of a PRD skill trips the ideation regex without a human ever
# having asked for anything.
_NOT_A_PROMPT = (
    "<command-name>",
    "<command-message>",
    "<local-command-stdout>",
    "<user-memory-input>",
    "<task-notification>",
    "Base directory for this skill:",
    "Caveat: The messages below were generated",
)


def _prompt_text(content) -> str | None:
    """Return the user's typed text, or None if this isn't a real prompt.

    User entries also carry tool results, slash-command expansions and injected
    skill bodies; none of those are prompts and none may reach the denominator.
    """
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        texts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                return None  # tool plumbing, not a prompt
            if block.get("type") == "text":
                texts.append(block.get("text") or "")
        text = "\n".join(t for t in texts if t)
    else:
        return None

    text = text.strip()
    if not text:
        return None
    if any(marker in text for marker in _NOT_A_PROMPT):
        return None
    # Strip system-reminder blocks, which carry instructions rather than intent.
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S).strip()
    return text or None


def iter_entries(root: Path):
    """Yield (path, parsed_json) for every transcript line under root."""
    for path in sorted(root.rglob("*.jsonl")):
        try:
            with path.open(errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield path, json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue


def collect(root: Path, pattern: re.Pattern, since: datetime | None) -> tuple[list[Prompt], Counter, dict]:
    """Walk transcripts and attribute each skill/MCP call to the prompt it followed.

    Attribution window: a tool call belongs to the most recent user prompt in
    the same session. Sidechain (subagent) entries carry no user prompts of
    their own, so their tool calls attribute to the parent session's open turn.
    """
    prompts: list[Prompt] = []
    open_turn: dict[str, Prompt] = {}     # session id -> most recent prompt
    skill_fires = Counter()
    stats = {
        "files": 0,
        "sessions": set(),
        "orphan_skill_fires": 0,          # fired with no preceding prompt
        "skipped_pre_since": 0,
    }
    seen_files = set()

    for path, entry in iter_entries(root):
        if path not in seen_files:
            seen_files.add(path)
            stats["files"] += 1

        etype = entry.get("type")
        if etype not in ("user", "assistant"):
            continue

        session = entry.get("sessionId") or str(path)
        stats["sessions"].add(session)
        ts = _parse_ts(entry.get("timestamp"))
        message = entry.get("message") or {}
        content = message.get("content")

        if etype == "user" and not entry.get("isSidechain"):
            text = _prompt_text(content)
            if text is None:
                continue
            if since and ts and ts < since:
                stats["skipped_pre_since"] += 1
                open_turn.pop(session, None)
                continue
            project = path.parent.name if path.parent.name != "projects" else path.stem
            p = Prompt(
                session=session,
                project=project,
                ts=ts,
                text=text,
                is_ideation=bool(pattern.search(text)),
                nudged=NUDGE_MARKER in text,
            )
            prompts.append(p)
            open_turn[session] = p
            continue

        # assistant entry: look for tool calls and attribute them
        if not isinstance(content, list):
            continue
        turn = open_turn.get(session)
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name") or ""

            if name == "Skill":
                skill = _skill_suffix((block.get("input") or {}).get("skill") or "")
                if skill in TRACKED_SKILLS:
                    skill_fires[skill] += 1
                    if turn is None:
                        stats["orphan_skill_fires"] += 1
                    else:
                        turn.skills.append(skill)
            elif name.startswith("mcp__"):
                suffix = _tool_suffix(name)
                if suffix in JUPI_TOOLS and turn is not None:
                    if suffix in JUPI_WRITE_TOOLS:
                        turn.jupi_writes += 1
                    else:
                        turn.jupi_reads += 1

    stats["sessions"] = len(stats["sessions"])
    return prompts, skill_fires, stats


# --- reporting --------------------------------------------------------------


def build_report(prompts: list[Prompt], skill_fires: Counter, stats: dict) -> dict:
    ideation = [p for p in prompts if p.is_ideation]
    fired_on_ideation = [p for p in ideation if IDEATION_SKILL in p.skills]
    missed = [p for p in ideation if IDEATION_SKILL not in p.skills]

    all_fires = [p for p in prompts if IDEATION_SKILL in p.skills]
    fires_off_ideation = [p for p in all_fires if not p.is_ideation]

    any_skill = [p for p in prompts if p.skills]
    reached_jupi = [p for p in any_skill if p.jupi_reads or p.jupi_writes]
    reached_write = [p for p in any_skill if p.jupi_writes]

    def pct(n, d):
        return round(100.0 * n / d, 1) if d else None

    by_project = defaultdict(lambda: {"prompts": 0, "ideation": 0, "fired": 0})
    for p in prompts:
        row = by_project[p.project]
        row["prompts"] += 1
        row["ideation"] += int(p.is_ideation)
        row["fired"] += int(IDEATION_SKILL in p.skills)

    return {
        "corpus": {
            "files": stats["files"],
            "sessions": stats["sessions"],
            "prompts": len(prompts),
            "prompts_before_since": stats["skipped_pre_since"],
        },
        "recall": {
            "ideation_prompts": len(ideation),
            "fired": len(fired_on_ideation),
            "missed": len(missed),
            "rate_pct": pct(len(fired_on_ideation), len(ideation)),
        },
        "precision": {
            "total_fires": len(all_fires),
            "on_ideation": len(all_fires) - len(fires_off_ideation),
            "off_ideation": len(fires_off_ideation),
            "rate_pct": pct(len(all_fires) - len(fires_off_ideation), len(all_fires)),
        },
        "funnel": {
            "skill_invocations": len(any_skill),
            "reached_jupi_mcp": len(reached_jupi),
            "reached_write": len(reached_write),
            "completion_pct": pct(len(reached_jupi), len(any_skill)),
        },
        "skill_fires": dict(skill_fires),
        "nudge": {
            "prompts_with_nudge": sum(1 for p in prompts if p.nudged),
        },
        "orphan_skill_fires": stats["orphan_skill_fires"],
        "by_project": dict(by_project),
        "_missed": missed,   # objects, stripped before JSON output
    }


def _bar(pct_value, width=24):
    if pct_value is None:
        return "n/a"
    filled = int(round(width * pct_value / 100))
    return "█" * filled + "·" * (width - filled) + f" {pct_value:.1f}%"


def print_report(r: dict, samples: int) -> None:
    c = r["corpus"]
    print("\njupi-skills — offline trigger report")
    print("=" * 58)
    print(f"corpus   {c['files']} transcripts · {c['sessions']} sessions · {c['prompts']} user prompts")
    if c["prompts_before_since"]:
        print(f"         ({c['prompts_before_since']} prompts excluded by --since)")

    print("\nRECALL — did search-decisions fire on ideation work?")
    rec = r["recall"]
    if rec["ideation_prompts"]:
        print(f"  {_bar(rec['rate_pct'])}")
        print(f"  {rec['fired']} fired / {rec['ideation_prompts']} ideation-flagged prompts "
              f"({rec['missed']} missed)")
    else:
        print("  no ideation-flagged prompts in this corpus")

    print("\nPRECISION — when it fired, was it ideation work?")
    pr = r["precision"]
    if pr["total_fires"]:
        print(f"  {_bar(pr['rate_pct'])}")
        print(f"  {pr['on_ideation']} on-signal / {pr['total_fires']} total fires "
              f"({pr['off_ideation']} off-signal)")
    else:
        print("  search-decisions never fired in this corpus")

    print("\nFUNNEL — did an invoked skill reach Jupi?")
    fn = r["funnel"]
    if fn["skill_invocations"]:
        print(f"  {_bar(fn['completion_pct'])}")
        print(f"  {fn['skill_invocations']} invocations → {fn['reached_jupi_mcp']} touched the MCP "
              f"→ {fn['reached_write']} wrote something")
    else:
        print("  no tracked skill invocations in this corpus")

    print("\nVOLUME")
    if r["skill_fires"]:
        for name, count in sorted(r["skill_fires"].items(), key=lambda kv: -kv[1]):
            print(f"  {count:4}  {name}")
    else:
        print("     0  (no tracked skills fired)")
    print(f"  {r['nudge']['prompts_with_nudge']:4}  prompts carrying the ideation nudge")
    if r["orphan_skill_fires"]:
        print(f"  {r['orphan_skill_fires']:4}  fires with no attributable prompt (subagent//resumed)")

    rows = [(k, v) for k, v in r["by_project"].items() if v["ideation"]]
    if rows:
        print("\nBY PROJECT (ideation-flagged prompts only)")
        for name, v in sorted(rows, key=lambda kv: -kv[1]["ideation"])[:10]:
            label = name if len(name) <= 38 else "…" + name[-37:]
            print(f"  {v['fired']:3}/{v['ideation']:<3} fired   {label}")

    if samples and r["_missed"]:
        print(f"\nMISSED OPPORTUNITIES (first {min(samples, len(r['_missed']))})")
        print("-" * 58)
        for p in r["_missed"][:samples]:
            when = p.ts.strftime("%Y-%m-%d") if p.ts else "unknown"
            snippet = " ".join(p.text.split())
            if len(snippet) > 150:
                snippet = snippet[:150] + "…"
            print(f"  [{when}] {snippet}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projects", type=Path,
                    default=Path.home() / ".claude" / "projects",
                    help="transcript root (default: ~/.claude/projects)")
    ap.add_argument("--hook", type=Path, default=None,
                    help="path to ideation_nudge.py (default: found from repo root)")
    ap.add_argument("--since", type=str, default=None,
                    help="only count prompts on/after this date, e.g. 2026-07-01")
    ap.add_argument("--samples", type=int, default=5,
                    help="how many missed prompts to print (0 to hide)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    if args.hook:
        spec = importlib.util.spec_from_file_location("ideation_nudge", args.hook)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        pattern = module._PATTERN
    else:
        pattern = load_ideation_pattern(repo_root)

    since = None
    if args.since:
        try:
            since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
        except ValueError:
            sys.exit(f"error: --since must be ISO date like 2026-07-01, got {args.since!r}")

    if not args.projects.exists():
        sys.exit(f"error: no transcript directory at {args.projects}")

    prompts, fires, stats = collect(args.projects, pattern, since)
    report = build_report(prompts, fires, stats)

    if args.json:
        missed = report.pop("_missed")
        report["missed_samples"] = [
            {"date": p.ts.isoformat() if p.ts else None,
             "project": p.project,
             "text": " ".join(p.text.split())[:300]}
            for p in missed[: args.samples or 0]
        ]
        print(json.dumps(report, indent=2))
    else:
        print_report(report, args.samples)
    return 0


if __name__ == "__main__":
    sys.exit(main())
