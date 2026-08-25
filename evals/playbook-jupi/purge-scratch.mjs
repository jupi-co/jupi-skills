#!/usr/bin/env node
// Purge the playbook-jupi eval scratch — ONE teardown for all three sets.
// Reuses the bench reset core (same tenant guard: refuses any tenant not
// prefixed dev-/eval-), so an eval purge is physically unable to touch a real
// tenant even on the shared project — and the dev project holds nothing real
// anyway.
//
// Usage:  JUPI_USER_ID=eval-<set> NEON_CONN_STRING=… node evals/playbook-jupi/purge-scratch.mjs
//         (or rely on the scratch workspace's config walk — cwd matters)
import { reset } from "../../dev/reset.mjs";
import { neonSql, resolveBenchConfig } from "../../dev/bench-lib.mjs";

const { connString, userId } = resolveBenchConfig();
const sql = await neonSql(connString);
const counts = await reset(sql, userId);
const total = Object.values(counts).reduce((a, b) => a + b, 0);
console.log(`purged eval tenant '${userId}': ${total} rows`, counts);
