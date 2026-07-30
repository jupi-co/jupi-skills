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
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$T\",\"session_hash\":\"$S\",\"client\":\"claude-desktop\",\"started_at\":\"$n\",\"ideation\":true,\"nudged\":true,\"user_input\":\"preview probe\"}"
expect "skill search-decisions" 202 \
  "{\"v\":1,\"event\":\"skill\",\"trace_id\":\"$T\",\"skill\":\"search-decisions\",\"at\":\"$(N)\"}"
expect "close completed" 202 \
  "{\"v\":1,\"event\":\"close\",\"trace_id\":\"$T\",\"ended_at\":\"$(N)\",\"duration_ms\":1234,\"outcome\":\"completed\"}"

echo
echo "== new-contract fields =="
expect "plugin_version present is fine" 202 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$(ID)\",\"session_hash\":\"$(ID)\",\"plugin_version\":\"489e80e\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":false,\"nudged\":false}"
expect "arbitrary client name (pattern, not enum)" 202 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$(ID)\",\"session_hash\":\"$(ID)\",\"client\":\"unknown\",\"started_at\":\"$(N)\",\"ideation\":false,\"nudged\":false}"
expect "outcome interrupted" 202 \
  "$(T2=$(ID); echo "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$T2\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":false,\"nudged\":false}")"

echo
echo "== ordering & idempotency =="
T=$(ID); S=$(ID)
expect "open" 202 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$T\",\"session_hash\":\"$S\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"nudged\":true}"
expect "duplicate open -> 409" 409 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$T\",\"session_hash\":\"$S\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"nudged\":true}"
expect "skill on unknown trace -> 404" 404 \
  "{\"v\":1,\"event\":\"skill\",\"trace_id\":\"$(ID)\",\"skill\":\"log-decision\",\"at\":\"$(N)\"}"
expect "close" 202 \
  "{\"v\":1,\"event\":\"close\",\"trace_id\":\"$T\",\"ended_at\":\"$(N)\",\"duration_ms\":5,\"outcome\":\"completed\"}"
expect "duplicate close -> 409" 409 \
  "{\"v\":1,\"event\":\"close\",\"trace_id\":\"$T\",\"ended_at\":\"$(N)\",\"duration_ms\":5,\"outcome\":\"completed\"}"

echo
echo "== rejection: 400 =="
expect "64-char trace_id" 400 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$(ID)$(ID)\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"nudged\":true}"
expect "all-zero trace_id" 400 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"00000000000000000000000000000000\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"nudged\":true}"
expect "untracked skill" 400 \
  "{\"v\":1,\"event\":\"skill\",\"trace_id\":\"$(ID)\",\"skill\":\"some-other\",\"at\":\"$(N)\"}"
expect "unknown field (install_id)" 400 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$(ID)\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"nudged\":true,\"install_id\":\"deadbeefdeadbeef\"}"
expect "v:2 rejected" 400 \
  "{\"v\":2,\"event\":\"open\",\"trace_id\":\"$(ID)\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"nudged\":true}"
expect "bad outcome enum" 400 \
  "$(T3=$(ID); curl -s -o /dev/null -X POST "$U/v1/skill-traces" -H 'Content-Type: application/json' -d "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$T3\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":false,\"nudged\":false}"; echo "{\"v\":1,\"event\":\"close\",\"trace_id\":\"$T3\",\"ended_at\":\"$(N)\",\"duration_ms\":5,\"outcome\":\"nope\"}")"

echo
echo "== oversize: expect 413 (documented) =="
BIG=$(python3 -c "print('x'*9000)")
expect "9 KB body" 413 \
  "{\"v\":1,\"event\":\"open\",\"trace_id\":\"$(ID)\",\"session_hash\":\"$(ID)\",\"client\":\"cli\",\"started_at\":\"$(N)\",\"ideation\":true,\"nudged\":true,\"user_input\":\"$BIG\"}"

echo
[ $fail -eq 0 ] && echo "ALL PASSED" || echo "SOME FAILED"
exit $fail
