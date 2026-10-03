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

/**
 * Match a location against allowed path prefixes from GET /context module_actions.
 * If allowedPaths is null (not loaded), treat as allowed so we do not flash denials.
 */
export function isPathAllowed(pathname: string, allowedPaths: string[] | null): boolean {
  if (allowedPaths === null) return true;
  const path = normalizePath(pathname);
  if ((ALWAYS_ALLOWED_PATHS as readonly string[]).includes(path)) return true;
  return allowedPaths.some((p) => {
    const prefix = normalizePath(p);
    if (prefix === "/") return path === "/";
    return path === prefix || path.startsWith(prefix + "/");
  });
}
