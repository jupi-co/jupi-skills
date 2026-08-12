#!/usr/bin/env node
// Playbook-Jupi — playbook + dossier data-access helper (shared).
//
// The playbook-specific sibling of db.mjs. db.mjs is BYTE-PARITY-LOCKED with
// proactive-jupi (CI enforces it), so everything the fork adds lives here:
// the playbook_entries verbs (with the §4 read-side gate) and the dossier
// verbs (stage on tasks). Same discipline as db.mjs: a thin, parameterized
// wrapper — schema.sql (same dir) is the authoritative schema; every verb
// uses bound parameters and is scoped by user_id automatically.
//
// THE READ-SIDE GATE (design §4 — the invariant this file exists to hold):
//   `pb-get-rule` is the ONE lookup the planner's act path may consult, and it
//   returns ONLY status='validated' entries (any answer_kind, including a
//   validated 'delegated' or 'always_ask'). 'inferred'/'declared' entries
//   NEVER come out of it — they are reachable solely via `pb-list-entries`,
//   whose results may pre-fill a decision's recommended option (provenance
//   cited) and never authorize an act. Contract: shared/playbook-contract.md.
//
// Usage:  node playbook.mjs <verb> [args...]
//   ── playbook entries (TECH-484) ──
//   pb-upsert-entry '<json>'                 → { id, status, version, applied }
//       json: point_id (required), scope_key (default 'global'), question?,
//             scope_axis?, answer? (omit/null = declared hole), answer_kind?
//             ('rule'|'always_ask'|'delegated'), status? ('inferred'|'declared'|
//             'validated'; default 'inferred'), provenance?
//       Write-side protection: an incoming 'inferred'/'declared' never
//       overwrites an existing 'validated'/'suspended' row → { applied: false }.
//       Incoming 'validated' (the finalized-[BR] path) always applies and bumps
//       version.
//   pb-get-rule     <point_id> [scope_key]   → { entry } | null      (THE GATE)
//   pb-list-entries [--status <s>] [--point <id>]  → [ {entry}, … ]
//   pb-set-status   <id> <status>            → { id, status, version }
//       (→ 'validated' bumps version — re-validation is vN+1, §6)
//   pb-add-evidence <id> <evidence|counter>  → { id, evidence_count, counter_evidence_count }
//   ── dossiers (TECH-485) ──
//   pb-create-dossier '<json>'               → { id, prior_stage, stage }
//       json: account (required), insurer?, broker?, contact_name?,
//             contact_title?, contact_email?, notes?, stage? (default 'to-qualify')
//       One tasks row per account (signal_type='dossier', stable signal_ref);
//       idempotent — re-seeding refreshes the summary but never resets stage.
//   pb-set-stage    <task_id> <stage> [detail]  → { id, stage, stage_detail }
//   pb-list-dossiers [--stage <s>]           → [ {dossier}, … ]
//
// Config resolution — same walk as db.mjs, one difference: this plugin's home
// folder is `.playbook-jupi/`, and `.proactive-jupi/` is accepted as a fallback
// so one config file can serve both this helper and the parity-locked db.mjs
// (the copied-verbatim skills still read the latter path) during the pilot.
//   1. $NEON_CONN_STRING / $DATABASE_URL  and  $JUPI_USER_ID
//   2. walk up from cwd: .playbook-jupi/config.local.json, then
//      .proactive-jupi/config.local.json → "neonConnString" / "jupiUserId"
//
// Output: JSON on stdout. Errors: JSON {error} on stderr, exit 1.

import { readFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

export const STAGES = [
  "to-qualify",
  "contact-identified",
  "sequence-running",
  "reply-to-handle",
  "call-booked",
  "phone-fallback",
];
export const ENTRY_STATUSES = ["inferred", "declared", "validated", "suspended"];
export const ANSWER_KINDS = ["rule", "always_ask", "delegated"];

const clean = (v) => (v && !String(v).includes("<") ? v : null);

// The nearest config walking up from cwd — .playbook-jupi/ preferred,
// .proactive-jupi/ accepted (see header). Parsed once; null when none.
let _workspaceConfig;
function loadWorkspaceConfig() {
  if (_workspaceConfig !== undefined) return _workspaceConfig;
  let dir = process.cwd();
  _workspaceConfig = null;
  outer: for (let i = 0; i < 8; i++) {
    for (const folder of [".playbook-jupi", ".proactive-jupi"]) {
      const p = join(dir, folder, "config.local.json");
      if (existsSync(p)) {
        try {
          _workspaceConfig = JSON.parse(readFileSync(p, "utf8"));
        } catch (e) {
          throw new Error(
            `${p} is not valid JSON (${e.message}). Note it is parsed strictly — '//' comments are not allowed; the '_'-prefixed keys in the template are the comment convention.`,
          );
        }
        break outer;
      }
    }
    const up = dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return _workspaceConfig;
}

function loadConfig() {
  const cfg = loadWorkspaceConfig() || {};
  const connString =
    process.env.NEON_CONN_STRING || process.env.DATABASE_URL || clean(cfg.neonConnString);
  const userId = process.env.JUPI_USER_ID || clean(cfg.jupiUserId);
  if (!connString)
    throw new Error(
      "no Neon connection string: set $NEON_CONN_STRING or add neonConnString to .playbook-jupi/config.local.json",
    );
  if (!userId)
    throw new Error(
      "no tenant id: set $JUPI_USER_ID or add jupiUserId to .playbook-jupi/config.local.json",
    );
  return { connString, userId };
}

async function getDb() {
  if (typeof fetch === "undefined") {
    throw new Error(
      `Neon's serverless driver needs a global fetch, absent on Node ${process.version}. ` +
        `Use Node ≥18 (e.g. \`nvm use 20\`) before running the routines.`,
    );
  }
  let neon;
  try {
    ({ neon } = await import("@neondatabase/serverless"));
  } catch {
    throw new Error(
      "@neondatabase/serverless not installed — run `bash ensure-deps.sh` in plugins/playbook-jupi/shared",
    );
  }
  const cfg = loadConfig();
  const raw = neon(cfg.connString);
  return {
    sql: { query: (text, params) => withRetry(() => raw.query(text, params)) },
    userId: cfg.userId,
  };
}

// Transient-fault retry — same rationale and shape as db.mjs: a scheduled run
// has nobody to re-run it, so retry what is genuinely transient and nothing else.
const RETRY_ATTEMPTS = 3;
const RETRY_BASE_MS = 400;
function isTransient(e) {
  const m = String(e?.message || e).toLowerCase();
  return /dns|fetch failed|network|socket|econnreset|etimedout|enotfound|eai_again|\b(502|503|504)\b|timed? ?out/.test(
    m,
  );
}
async function withRetry(fn) {
  let last;
  for (let attempt = 1; attempt <= RETRY_ATTEMPTS; attempt++) {
    try {
      return await fn();
    } catch (e) {
      if (!isTransient(e) || attempt === RETRY_ATTEMPTS) throw e;
      last = e;
      await new Promise((r) => setTimeout(r, RETRY_BASE_MS * 2 ** (attempt - 1)));
    }
  }
  throw last;
}

// Stable dossier ref from the account name: lowercase, runs of non-alphanumerics
// → '-'. Same rule as db.mjs's decision slugifier so there is one convention.
export function dossierRef(account) {
  const slug = String(account ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  if (!slug) throw new Error("pb-create-dossier: `account` must yield a non-empty slug");
  return `dossier:${slug}`;
}

// One readable line per known attribute. The attrs deliberately live in the
// summary TEXT (`key: value` lines) — TECH-485 is a column and verbs, no new
// table; whether broker/insurer earn structured columns is the planner
// ticket's call (it is the consumer that would read them).
function dossierSummary(d) {
  const lines = [`Account dossier — ${d.account}.`];
  if (d.insurer) lines.push(`insurer: ${d.insurer}`);
  if (d.broker) lines.push(`broker: ${d.broker}`);
  const contact = [d.contact_name, d.contact_title, d.contact_email].filter(Boolean).join(" · ");
  if (contact) lines.push(`contact: ${contact}`);
  if (d.notes) lines.push(`notes: ${d.notes}`);
  return lines.join("\n");
}

// Minimal `--flag value` parser for the list verbs. Unknown flags error loudly —
// a silently ignored filter would return the UNfiltered set, which reads fine
// and is wrong.
function parseFlags(args, allowed) {
  const out = {};
  for (let i = 0; i < args.length; i += 2) {
    const flag = String(args[i] ?? "");
    if (!flag.startsWith("--") || !allowed.includes(flag.slice(2)))
      throw new Error(`unknown or malformed flag '${flag}' (allowed: ${allowed.map((f) => `--${f}`).join(", ")})`);
    if (args[i + 1] === undefined) throw new Error(`flag '${flag}' needs a value`);
    out[flag.slice(2)] = args[i + 1];
  }
  return out;
}

export const VERBS = {
  // ── playbook entries ─────────────────────────────────────────────────────
  // Insert or update the (point, scope) entry. Write-side protection mirrors
  // the read-side gate: extraction (inferred/declared) may create and refresh
  // its own rows, but never touch a row the owner validated or suspended —
  // those move only through the decision path (incoming 'validated') or an
  // explicit pb-set-status. Incoming 'validated' bumps version (vN → vN+1).
  async "pb-upsert-entry"(sql, [jsonArg], userId) {
    const e = JSON.parse(jsonArg);
    if (!e.point_id) throw new Error("pb-upsert-entry: `point_id` is required");
    const status = e.status ?? "inferred";
    if (!ENTRY_STATUSES.includes(status) || status === "suspended")
      throw new Error(
        `pb-upsert-entry: status must be inferred|declared|validated (suspension goes through pb-set-status), got '${status}'`,
      );
    if (e.answer_kind != null && !ANSWER_KINDS.includes(e.answer_kind))
      throw new Error(`pb-upsert-entry: answer_kind must be ${ANSWER_KINDS.join("|")}, got '${e.answer_kind}'`);
    const rows = await sql.query(
      `insert into playbook_entries
         (user_id, point_id, scope_key, question, scope_axis, answer, answer_kind, status, version, provenance)
       values ($1, $2, $3, $4, $5, $6, $7, $8, case when $8 = 'validated' then 1 else 0 end, $9)
       on conflict (user_id, point_id, scope_key) do update
         set question    = coalesce(excluded.question, playbook_entries.question),
             scope_axis  = coalesce(excluded.scope_axis, playbook_entries.scope_axis),
             answer      = excluded.answer,
             answer_kind = excluded.answer_kind,
             status      = excluded.status,
             version     = case when excluded.status = 'validated'
                                then playbook_entries.version + 1
                                else playbook_entries.version end,
             provenance  = coalesce(excluded.provenance, playbook_entries.provenance),
             updated_at  = now()
         where excluded.status = 'validated'
            or playbook_entries.status not in ('validated','suspended')
       returning id, status, version`,
      [
        userId,                    // $1
        e.point_id,                // $2
        e.scope_key ?? "global",   // $3
        e.question ?? null,        // $4
        e.scope_axis ?? null,      // $5
        e.answer ?? null,          // $6
        e.answer_kind ?? null,     // $7
        status,                    // $8
        e.provenance ?? null,      // $9
      ],
    );
    if (!rows[0]) {
      // The conflict row is validated/suspended and the incoming write wasn't
      // validated — protected. Say so instead of pretending it landed.
      const cur = await sql.query(
        `select id, status, version from playbook_entries
          where user_id = $1 and point_id = $2 and scope_key = $3`,
        [userId, e.point_id, e.scope_key ?? "global"],
      );
      return { ...cur[0], applied: false, reason: "existing entry is validated/suspended — only the decision path (status 'validated') or pb-set-status may change it" };
    }
    return { ...rows[0], applied: true };
  },

  // THE GATE (§4). Exact match on (point, scope); ONLY validated entries come
  // out — any answer_kind (a validated 'delegated' pre-empts like a rule; a
  // validated 'always_ask' tells the planner the case-by-case IS the answer).
  // The planner falls back scoped→'global' by calling twice; the verb stays dumb.
  async "pb-get-rule"(sql, [pointId, scopeKey], userId) {
    if (!pointId) throw new Error("pb-get-rule: usage `pb-get-rule <point_id> [scope_key]`");
    const rows = await sql.query(
      `select id, point_id, scope_key, question, scope_axis, answer, answer_kind,
              status, version, provenance, evidence_count, counter_evidence_count, updated_at
         from playbook_entries
        where user_id = $1 and point_id = $2 and scope_key = $3 and status = 'validated'`,
      [userId, pointId, scopeKey ?? "global"],
    );
    return rows[0] ?? null;
  },

  // Everything, or everything at one status / one point — the read the planner
  // uses to enumerate holes and fetch inferred/declared entries to PRE-FILL a
  // decision's recommended option. Never an authorization path.
  async "pb-list-entries"(sql, args, userId) {
    const f = parseFlags(args, ["status", "point"]);
    if (f.status && !ENTRY_STATUSES.includes(f.status))
      throw new Error(`--status must be ${ENTRY_STATUSES.join("|")}, got '${f.status}'`);
    return sql.query(
      `select id, point_id, scope_key, question, scope_axis, answer, answer_kind,
              status, version, provenance, evidence_count, counter_evidence_count, updated_at
         from playbook_entries
        where user_id = $1
          and ($2::text is null or status = $2)
          and ($3::text is null or point_id = $3)
        order by point_id, scope_key`,
      [userId, f.status ?? null, f.point ?? null],
    );
  },

  // Lifecycle transitions (§3/§6): validate, suspend, re-validate. Transition
  // TO 'validated' bumps version — a re-validation or amendment is vN+1.
  async "pb-set-status"(sql, [id, status], userId) {
    if (!ENTRY_STATUSES.includes(status))
      throw new Error(`pb-set-status: status must be ${ENTRY_STATUSES.join("|")}, got '${status}'`);
    const rows = await sql.query(
      `update playbook_entries
          set status = $3,
              version = case when $3 = 'validated' then version + 1 else version end,
              updated_at = now()
        where id = $1 and user_id = $2
      returning id, point_id, scope_key, status, version`,
      [id, userId, status],
    );
    return rows[0] ?? { id: null, error: "no such playbook entry for this user" };
  },

  // The evidence ledger's counters (§3). 'evidence' = a consistent application /
  // confirmation; 'counter' = an edit or contradiction (§6's suspension path
  // reads counter_evidence_count when it lands).
  async "pb-add-evidence"(sql, [id, kind], userId) {
    if (!["evidence", "counter"].includes(kind))
      throw new Error(`pb-add-evidence: kind must be evidence|counter, got '${kind}'`);
    const rows = await sql.query(
      `update playbook_entries
          set evidence_count         = evidence_count + case when $3 = 'evidence' then 1 else 0 end,
              counter_evidence_count = counter_evidence_count + case when $3 = 'counter' then 1 else 0 end,
              updated_at = now()
        where id = $1 and user_id = $2
      returning id, point_id, scope_key, evidence_count, counter_evidence_count`,
      [id, userId, kind],
    );
    return rows[0] ?? { id: null, error: "no such playbook entry for this user" };
  },

  // ── dossiers ─────────────────────────────────────────────────────────────
  // One long-lived tasks row per account (design §8). Idempotent on the account:
  // re-running a seed refreshes the descriptive summary but never resets a
  // dossier's stage or status — progress belongs to the funnel, not the seed.
  async "pb-create-dossier"(sql, [jsonArg], userId) {
    const d = JSON.parse(jsonArg);
    if (!d.account) throw new Error("pb-create-dossier: `account` is required");
    const stage = d.stage ?? "to-qualify";
    if (!STAGES.includes(stage))
      throw new Error(`pb-create-dossier: stage must be one of ${STAGES.join("|")}, got '${stage}'`);
    const rows = await sql.query(
      `with prior as (
         select stage from tasks where user_id = $1 and signal_type = 'dossier' and signal_ref = $2
       )
       insert into tasks (user_id, signal_type, signal_ref, short_label, summary,
                          status, external, stage, stage_updated_at)
       values ($1, 'dossier', $2, $3, $4, 'open', true, $5, now())
       on conflict (user_id, signal_type, signal_ref) do update
         set short_label = excluded.short_label,
             summary     = excluded.summary,
             updated_at  = now()
       returning id, stage, (select stage from prior) as prior_stage`,
      [userId, dossierRef(d.account), d.account, dossierSummary(d), stage],
    );
    const r = rows[0];
    return { id: r.id, prior_stage: r.prior_stage ?? null, stage: r.stage };
  },

  // Move a dossier along the funnel. Guarded to dossier rows — staging an
  // ordinary task is a bug, not a feature. `detail` replaces (or clears) the
  // free-detail field on every transition: it describes THIS stage (the mail
  // index while sequence-running), so carrying it across stages would lie.
  async "pb-set-stage"(sql, [taskId, stage, detail], userId) {
    if (!STAGES.includes(stage))
      throw new Error(`pb-set-stage: stage must be one of ${STAGES.join("|")}, got '${stage}'`);
    const rows = await sql.query(
      `update tasks
          set stage = $3, stage_detail = $4, stage_updated_at = now(), updated_at = now()
        where id = $1 and user_id = $2 and signal_type = 'dossier'
      returning id, short_label, stage, stage_detail`,
      [taskId, userId, stage, detail ?? null],
    );
    return rows[0] ?? { id: null, error: "no such dossier for this user (pb-set-stage only moves signal_type='dossier' rows)" };
  },

  // The funnel read: this tenant's dossiers, optionally at one stage. Carries
  // status + gating_decision_ids so the caller sees blocked-ness without a
  // second query; ordered by account for a stable listing.
  async "pb-list-dossiers"(sql, args, userId) {
    const f = parseFlags(args, ["stage"]);
    if (f.stage && !STAGES.includes(f.stage))
      throw new Error(`--stage must be one of ${STAGES.join("|")}, got '${f.stage}'`);
    return sql.query(
      `select id, short_label as account, stage, stage_detail, stage_updated_at,
              status, gating_decision_ids, summary, signal_ref, updated_at
         from tasks
        where user_id = $1 and signal_type = 'dossier'
          and ($2::text is null or stage = $2)
        order by short_label`,
      [userId, f.stage ?? null],
    );
  },
};

async function main() {
  const [verb, ...args] = process.argv.slice(2);
  const fn = VERBS[verb];
  if (!fn) {
    process.stderr.write(
      JSON.stringify({ error: `unknown verb '${verb}'`, verbs: Object.keys(VERBS) }) + "\n",
    );
    process.exit(1);
  }
  const { sql, userId } = await getDb();
  const out = await fn(sql, args, userId);
  process.stdout.write(JSON.stringify(out) + "\n");
}

// Only run the CLI when invoked as one — VERBS and the helpers are exported so
// a Node consumer (the dev bench's seed, a test harness) can import them and
// inject its own sql adapter.
const invokedDirectly =
  process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

if (invokedDirectly) {
  main().catch((e) => {
    process.stderr.write(JSON.stringify({ error: String(e.message || e) }) + "\n");
    process.exit(1);
  });
}
