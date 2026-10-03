/** Phase 100 — shared path authorization helpers (UI route guards).
 *  Backend module_actions remains the source of truth.
 *  Developed by BAHATI GAD WANGWE
 */

/** Paths every authenticated facility user may open. */
export const ALWAYS_ALLOWED_PATHS = ["/", "/workspace"] as const;

export function normalizePath(path: string): string {
  const raw = (path || "/").split("?")[0].split("#")[0];
  if (!raw || raw === "/") return "/";
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

function matchesPrefix(path: string, prefix: string): boolean {
  const p = normalizePath(prefix);
  if (p === "/") return path === "/";
  return path === p || path.startsWith(p + "/");
}

/**
 * Match a location against module_actions from GET /context.
 * - allowedPaths === null → still loading → allow (avoid denial flash)
 * - path always-allowed → allow
 * - if catalogPaths provided and path is not in catalog → allow (uncatalogued)
 * - otherwise path must match an allowed prefix
 */
export function isPathAllowed(
  pathname: string,
  allowedPaths: string[] | null,
  catalogPaths?: string[] | null,
): boolean {
  if (allowedPaths === null) return true;
  const path = normalizePath(pathname);
  if ((ALWAYS_ALLOWED_PATHS as readonly string[]).includes(path)) return true;

  if (Array.isArray(catalogPaths) && catalogPaths.length > 0) {
    const governed = catalogPaths.some((c) => matchesPrefix(path, c));
    if (!governed) return true;
  }

  return allowedPaths.some((p) => matchesPrefix(path, p));
}
