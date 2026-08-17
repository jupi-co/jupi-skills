#!/usr/bin/env node
// Dev-bench seed (TECH-486): the mirror's fake world → the shared Neon project,
// under the synthetic bench tenant. Idempotent — safe to re-run; re-seeding
// refreshes descriptive fields but never resets a dossier's stage or status
// (that guarantee lives in pb-create-dossier itself).
//
// Two writes, in order:
//   1. Declare the PILOT lifecycle (pb-declare-stages) — the six stages are
//      pilot CONTENT and this file is pilot content's code-side companion,
//      which is why the list lives here and in dev/mirror/, never in the
//      engine (see shared/playbook-contract.md, the engine-vocabulary rule).
//      If the lifecycle entry was later validated by the owner, re-declaration
//      is refused by the write-side protection — reported, not an error.
//   2. One dossier per row of the mirror's reporting sheet
//      (dev/mirror/accounts.csv): the sheet's columns become free attrs; the
//      engine doesn't know what they mean.
//
// Usage: node dev/seed.mjs          (config: .playbook-jupi/config.local.json or env)

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { VERBS } from "../plugins/playbook-jupi/shared/playbook.mjs";
import { assertBenchTenant, neonSql, parseCsv, resolveBenchConfig, REPO_ROOT } from "./bench-lib.mjs";

// The pilot mirror's lifecycle — content, not engine (mirrors design §8).
export const PILOT_STAGES = [
  "to-qualify",
  "contact-identified",
  "sequence-running",
  "reply-to-handle",
  "call-booked",
  "phone-fallback",
];

// Core, injectable for tests: sql is the (text, $n params) → rows adapter.
export async function seed(sql, userId, { csvPath, stages = PILOT_STAGES, provenance = "dev/seed.mjs — pilot mirror" } = {}) {
  assertBenchTenant(userId);
  const lifecycle = await VERBS["pb-declare-stages"](sql, [JSON.stringify(stages), provenance], userId);
  const rows = parseCsv(readFileSync(csvPath, "utf8"));
  const dossiers = [];
  for (const row of rows) {
    const { account, notes, ...rest } = row;
    if (!account) continue;
    const attrs = Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== ""));
    const r = await VERBS["pb-create-dossier"](
      sql,
      [JSON.stringify({ label: account, attrs, notes: notes || undefined })],
      userId,
    );
    dossiers.push({ label: account, ...r });
  }
  return { lifecycle, dossiers };
}

async function main() {
  const { connString, userId, cfg } = resolveBenchConfig();
  const sql = await neonSql(connString);
  const csvPath = join(REPO_ROOT, cfg.accountsSource || "dev/mirror/accounts.csv");
  const out = await seed(sql, userId, { csvPath });
  const lc = out.lifecycle;
  console.log(
    lc.applied
      ? `lifecycle declared (v${lc.version}): ${PILOT_STAGES.join(" → ")}`
      : `lifecycle left as-is (owner-validated, v${lc.version}) — re-declaration refused by design`,
  );
  for (const d of out.dossiers)
    console.log(`dossier ${d.prior_stage === null ? "created" : "refreshed"}: ${d.label} [${d.stage ?? "unstaged"}]`);
  console.log(`seeded ${out.dossiers.length} dossiers under tenant '${userId}'. Re-run anytime — idempotent.`);
}

const invokedDirectly =
  process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invokedDirectly) {
  main().catch((e) => {
    console.error(String(e.message || e));
    process.exit(1);
  });
}
