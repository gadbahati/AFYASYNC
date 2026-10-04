import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const app = fs.readFileSync(path.join(root, "src/pages/../App.tsx"), "utf8");
const workspaces = fs.readFileSync(path.join(root, "src/workspaces/workspaces.ts"), "utf8");
const portal = fs.readFileSync(path.join(root, "src/pages/PatientPortalHomePage.tsx"), "utf8");

const routePattern = /\[\s*"([^"]+)"\s*,\s*"[^"]+"\s*\]/g;
const workspaceRoutes = [...workspaces.matchAll(routePattern)].map((m) => m[1]);
const appRoutes = new Set([...app.matchAll(/path="([^"]+)"/g)].map((m) => m[1]));

const required = new Set([
  ...workspaceRoutes,
  ...[...portal.matchAll(/to="(\/portal(?:\/[^"]+)?)"/g)].map((m) => m[1]),
  "/government",
  "/government/*",
]);

const missing = [...required].filter((route) => !appRoutes.has(route));
if (missing.length) {
  console.error("Missing registered frontend routes:");
  for (const route of missing) console.error(` - ${route}`);
  process.exit(1);
}
console.log(`Route integrity check passed: ${required.size} required routes registered.`);
