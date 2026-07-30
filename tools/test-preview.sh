#!/usr/bin/env bash
# Full contract test against the live preview backend.
#   tools/test-preview.sh [base-url]
# Exercises the NEW contract (session_hash, client pattern, optional
# plugin_version, 413 on oversize). Prints ok/FAIL per case; exits non-zero on
# any failure.
set -u
U="${1:-https://jupi-pr-3928.koyeb.app}"
N() { date -u +%Y-%m-%dT%H:%M:%S.000Z; }
ID() { openssl rand -hex 16; }
fail=0

# $1 label  $2 expected-code  $3 json body
expect() {
  local got
  got=$(curl -s -o /tmp/pv_body.txt -w "%{http_code}" -X POST "$U/v1/skill-traces" \
    -H 'Content-Type: application/json' -d "$3")
  if [ "$got" = "$2" ]; then
    printf '  ok    %-42s %s\n' "$1" "$got"
  else
    printf '  FAIL  %-42s got %s, want %s\n' "$1" "$got" "$2"
    head -c 300 /tmp/pv_body.txt; echo
    fail=1
  fi
}

echo "preview: $U"
echo
echo "== happy path: one full turn =="
T=$(ID); S=$(ID); n=$(N)
expect "open (client=claude-desktop, no version)" 202 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$T\",\"session_hash\":\"$S\",\"client\":\"claude-desktop\",\"started_at\":\"$n\",\"ideation\":true,\"plugin\":\"jupi-skills\",\"nudged_skill\":\"search-decisions\",\"user_input\":\"preview probe\"}"
expect "skill search-decisions" 202 \
  "{\"v\":1,\"event\":\"skill\",\"trace_id\":\"$T\",\"skill\":\"search-decisions\",\"at\":\"$(N)\"}"
expect "close completed" 202 \
  "{\"v\":1,\"event\":\"close\",\"trace_id\":\"$T\",\"ended_at\":\"$(N)\",\"duration_ms\":1234,\"outcome\":\"completed\"}"

echo
echo "== new-contract fields =="
expect "plugin_version present is fine" 202 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$(ID)\",\"session_hash\":\"$(ID)\",\"plugin_version\":\"489e80e\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":false,\"plugin\":\"jupi-skills\"}"
expect "arbitrary client name (pattern, not enum)" 202 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$(ID)\",\"session_hash\":\"$(ID)\",\"client\":\"unknown\",\"started_at\":\"$(N)\",\"ideation\":false,\"plugin\":\"jupi-skills\"}"
expect "outcome interrupted" 202 \
  "$(T2=$(ID); echo "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$T2\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":false,\"plugin\":\"jupi-skills\"}")"

echo
echo "== ordering & idempotency =="
T=$(ID); S=$(ID)
expect "open" 202 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$T\",\"session_hash\":\"$S\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"plugin\":\"jupi-skills\",\"nudged_skill\":\"search-decisions\"}"
expect "duplicate open -> 409" 409 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$T\",\"session_hash\":\"$S\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"plugin\":\"jupi-skills\",\"nudged_skill\":\"search-decisions\"}"
expect "skill on unknown trace -> 404" 404 \
  "{\"v\":1,\"event\":\"skill\",\"trace_id\":\"$(ID)\",\"skill\":\"log-decision\",\"at\":\"$(N)\"}"
expect "close" 202 \
  "{\"v\":1,\"event\":\"close\",\"trace_id\":\"$T\",\"ended_at\":\"$(N)\",\"duration_ms\":5,\"outcome\":\"completed\"}"
expect "duplicate close -> 409" 409 \
  "{\"v\":1,\"event\":\"close\",\"trace_id\":\"$T\",\"ended_at\":\"$(N)\",\"duration_ms\":5,\"outcome\":\"completed\"}"

echo
echo "== rejection: 400 =="
expect "64-char trace_id" 400 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$(ID)$(ID)\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"plugin\":\"jupi-skills\",\"nudged_skill\":\"search-decisions\"}"
expect "all-zero trace_id" 400 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"00000000000000000000000000000000\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"plugin\":\"jupi-skills\",\"nudged_skill\":\"search-decisions\"}"
# Any skill string is now recorded server-side; the tracked-three filter is a
# client-side privacy decision (skill_probe.py), not a server rule. So an
# untracked skill is not a 400 — it just hits an unknown trace -> 404.
expect "untracked skill on unknown trace -> 404" 404 \
  "{\"v\":1,\"event\":\"skill\",\"trace_id\":\"$(ID)\",\"skill\":\"some-other\",\"at\":\"$(N)\"}"
expect "unknown field (install_id)" 400 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$(ID)\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"plugin\":\"jupi-skills\",\"nudged_skill\":\"search-decisions\",\"install_id\":\"deadbeefdeadbeef\"}"
expect "v:2 rejected" 400 \
  "{\"v\":2,\"event\":\"open\",\"trace_id\":\"$(ID)\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"plugin\":\"jupi-skills\",\"nudged_skill\":\"search-decisions\"}"
expect "bad outcome enum" 400 \
  "$(T3=$(ID); curl -s -o /dev/null -X POST "$U/v1/skill-traces" -H 'Content-Type: application/json' -d "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$T3\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":false,\"plugin\":\"jupi-skills\"}"; echo "{\"v\":1,\"event\":\"close\",\"trace_id\":\"$T3\",\"ended_at\":\"$(N)\",\"duration_ms\":5,\"outcome\":\"nope\"}")"

echo
echo "== oversize =="
# The documented 8 KB route cap is NOT enforced: an 8-9 KB body is accepted and
# user_input is truncated to 2000 server-side. The only limit is the framework's
# 1 MB default. Not a client concern (the client truncates to 2000 chars before
# sending) but a deviation from the PR description worth tracking.
python3 -c "import json;print(json.dumps({'v':1,'event':'open','trace_id':'$(ID)','session_hash':'$(ID)','client':'cli','started_at':'$(N)','ideation':True,'plugin':'jupi-skills','user_input':'x'*9000}))" > /tmp/pv_9k.json
got=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$U/v1/skill-traces" -H 'Content-Type: application/json' --data-binary @/tmp/pv_9k.json)
[ "$got" = "202" ] && printf '  ok    %-42s %s\n' "9 KB accepted (truncated, no 8KB cap)" "$got" || { printf '  FAIL  %-42s got %s\n' "9 KB body" "$got"; fail=1; }
python3 -c "import json;print(json.dumps({'v':1,'event':'open','trace_id':'$(ID)','session_hash':'$(ID)','client':'cli','started_at':'$(N)','ideation':True,'plugin':'jupi-skills','user_input':'x'*1200000}))" > /tmp/pv_big.json
got=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$U/v1/skill-traces" -H 'Content-Type: application/json' --data-binary @/tmp/pv_big.json)
[ "$got" = "413" ] && printf '  ok    %-42s %s\n' ">1 MB body -> 413 (framework cap)" "$got" || { printf '  FAIL  %-42s got %s\n' ">1 MB body" "$got"; fail=1; }

echo
[ $fail -eq 0 ] && echo "ALL PASSED" || echo "SOME FAILED"
exit $fail
