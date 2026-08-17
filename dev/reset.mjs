#!/usr/bin/env node
// Dev-bench reset (TECH-486): purge EVERYTHING the bench tenant owns in the
// shared Neon project, so `node dev/seed.mjs` reproduces an identical world.
// Idempotent — an empty tenant purges to an empty tenant.
//
// Scope is the tenant, full stop: tasks (dossiers AND transient rows — actions
// cascade via FK), playbook_entries, crawl_state, crawl_frontier, routine_runs.
// The synthetic-tenant guard makes it physically unable to touch a real
// tenant's rows; there is deliberately no --tenant flag — the tenant comes
// from config, same as every other bench command.
//
// What it does NOT touch: the Jupi test workspace (decisions there are
// harmless leftovers, per the evals convention) and the dev mailbox (drafts
// and threads are cleaned by hand when they get in the way — Gmail has no
// safe bulk-delete over MCP, and the bench must never automate deletion).
//
// Usage: node dev/reset.mjs          (config: .playbook-jupi/config.local.json or env)

import { pathToFileURL } from "node:url";
import { assertBenchTenant, neonSql, resolveBenchConfig } from "./bench-lib.mjs";

// Core, injectable for tests: sql is the (text, $n params) → rows adapter.
export async function reset(sql, userId) {
  assertBenchTenant(userId);
  const purge = async (table) =>
    (await sql.query(`delete from ${table} where user_id = $1 returning 1`, [userId])).length;
  // tasks first: its FK cascade removes the tenant's actions with it.
  const counts = {
    tasks: await purge("tasks"),
    playbook_entries: await purge("playbook_entries"),
    crawl_state: await purge("crawl_state"),
    crawl_frontier: await purge("crawl_frontier"),
    routine_runs: await purge("routine_runs"),
  };
  return counts;
}

async function main() {
  const { connString, userId } = resolveBenchConfig();
  const sql = await neonSql(connString);
  const counts = await reset(sql, userId);
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  for (const [table, n] of Object.entries(counts)) if (n) console.log(`purged ${n} ${table}`);
  console.log(`tenant '${userId}' reset (${total} rows). \`node dev/seed.mjs\` rebuilds the identical world.`);
}

const invokedDirectly =
  process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invokedDirectly) {
  main().catch((e) => {
    console.error(String(e.message || e));
    process.exit(1);
  });
}
