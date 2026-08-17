// Dev-bench shared plumbing (TECH-486) — config resolution + the Neon adapter
// for dev/seed.mjs and dev/reset.mjs. Repo tooling, not plugin code: it may
// import from plugins/playbook-jupi/shared/ (the packaged plugin never imports
// from here).
//
// Safety: everything in this file assumes the SHARED Neon project. The
// row-level boundary is the tenant, so the one non-negotiable is the synthetic-
// tenant guard — the bench must be physically unable to touch a real tenant's
// rows. assertBenchTenant() is that guard; seed and reset both call it inside
// their core functions (not just the CLI), so no import path bypasses it.

import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const REPO_ROOT = dirname(dirname(fileURLToPath(import.meta.url))); // dev/ → repo root
export const SHARED = join(REPO_ROOT, "plugins", "playbook-jupi", "shared");

export function assertBenchTenant(userId) {
  if (!/^(dev|eval)-/.test(String(userId ?? "")))
    throw new Error(
      `bench refuses tenant '${userId}': only synthetic tenants (prefix 'dev-' or 'eval-') may be seeded or purged — a real tenant's rows live in the same shared project.`,
    );
  return userId;
}

// Env first, then the repo-root .playbook-jupi/config.local.json (the bench's
// home; template at dev/config.template.json), then .proactive-jupi/ as the
// fallback playbook.mjs also accepts.
export function resolveBenchConfig() {
  let cfg = {};
  for (const folder of [".playbook-jupi", ".proactive-jupi"]) {
    const p = join(REPO_ROOT, folder, "config.local.json");
    if (existsSync(p)) {
      cfg = JSON.parse(readFileSync(p, "utf8"));
      break;
    }
  }
  const connString = process.env.NEON_CONN_STRING || process.env.DATABASE_URL || cfg.neonConnString;
  const userId = process.env.JUPI_USER_ID || cfg.jupiUserId;
  if (!connString || String(connString).includes("<"))
    throw new Error(
      "no Neon connection string: copy dev/config.template.json to .playbook-jupi/config.local.json and fill neonConnString (or set $NEON_CONN_STRING)",
    );
  if (!userId || String(userId).includes("<"))
    throw new Error("no tenant id: set jupiUserId in .playbook-jupi/config.local.json (or $JUPI_USER_ID)");
  return { connString, userId: assertBenchTenant(userId), cfg };
}

// The same (text, $n params) → rows adapter shape playbook.mjs builds — here
// from the driver ensure-deps.sh installed under the plugin's shared/.
export async function neonSql(connString) {
  const driverPath = join(SHARED, "node_modules", "@neondatabase", "serverless", "index.mjs");
  if (!existsSync(driverPath))
    throw new Error(`Neon driver not installed — run: bash ${join(SHARED, "ensure-deps.sh")}`);
  const { neon } = await import(pathToFileURL(driverPath).href);
  const raw = neon(connString);
  return { query: (text, params) => raw.query(text, params) };
}

// Minimal CSV parser (quoted fields, "" escapes, commas/newlines in quotes,
// CRLF) — enough for the mirror's reporting sheet, no dependency.
export function parseCsv(text) {
  const rows = [];
  let row = [], field = "", inQuotes = false;
  const s = String(text);
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inQuotes) {
      if (c === '"' && s[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') inQuotes = false;
      else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && s[i + 1] === "\n") i++;
      row.push(field); field = "";
      if (row.length > 1 || row[0] !== "") rows.push(row);
      row = [];
    } else field += c;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  const [header, ...rest] = rows;
  return rest.map((r) => Object.fromEntries(header.map((h, i) => [h.trim(), (r[i] ?? "").trim()])));
}
