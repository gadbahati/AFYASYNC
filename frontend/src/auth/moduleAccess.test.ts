/** Lightweight contract checks for path matching (run under vitest if configured). */
import { isPathAllowed, normalizePath } from "./moduleAccess";

export function runModuleAccessChecks(): void {
  if (normalizePath("/claims/") !== "/claims") throw new Error("normalize");
  if (!isPathAllowed("/workspace", [])) throw new Error("workspace always");
  if (!isPathAllowed("/", [])) throw new Error("dashboard always");
  if (!isPathAllowed("/patients/1", ["/patients"])) throw new Error("prefix");
  if (isPathAllowed("/claims", ["/patients"])) throw new Error("deny claims");
  if (isPathAllowed("/x", null) !== true) throw new Error("null means loading allow");
}
