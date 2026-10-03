import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { WORKSPACES } from "../workspaces/workspaces";
import { api } from "../api/client";
import { isPathAllowed } from "../auth/moduleAccess";

type Result = { label: string; path: string; workspace: string; hint: string };

export function GlobalCommand() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [allowedWorkspaces, setAllowedWorkspaces] = useState<string[]>(["operations"]);
  const [allowedPaths, setAllowedPaths] = useState<string[] | null>(null);
  const [catalogPaths, setCatalogPaths] = useState<string[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .contextOverview()
      .then((v: any) => {
        if (Array.isArray(v?.allowed_workspaces)) setAllowedWorkspaces(v.allowed_workspaces);
        const paths = v?.module_actions?.allowed_paths;
        const catalog = v?.module_actions?.catalog_paths;
        setAllowedPaths(Array.isArray(paths) ? paths : null);
        setCatalogPaths(Array.isArray(catalog) ? catalog : []);
        setIsAdmin(Boolean(v?.authorization?.system_administrator || v?.module_actions?.is_admin));
      })
      .catch(() => {
        /* keep defaults; palette stays usable for shell paths */
      });
  }, []);

  const canOpen = (path: string) =>
    isAdmin || isPathAllowed(path, allowedPaths, catalogPaths);

  const results = useMemo<Result[]>(() => {
    const term = q.trim().toLowerCase();
    const inWorkspace = WORKSPACES.filter((w) => allowedWorkspaces.includes(w.id));
    const all = inWorkspace.flatMap((w) =>
      w.links
        .filter(([path]) => canOpen(path))
        .map(([path, label]) => ({
          label,
          path,
          workspace: w.label,
          hint: "Authorized module",
        })),
    );
    if (!term) return all.slice(0, 8);
    return all
      .filter((x) => (x.label + " " + x.path + " " + x.workspace).toLowerCase().includes(term))
      .slice(0, 12);
  }, [q, allowedWorkspaces, allowedPaths, catalogPaths, isAdmin]);

  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(true);
        setTimeout(() => ref.current?.focus(), 0);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, []);

  return (
    <>
      <button
        type="button"
        aria-label="Open command search"
        onClick={() => {
          setOpen(true);
          setTimeout(() => ref.current?.focus(), 0);
        }}
        style={{
          position: "fixed",
          right: 22,
          top: 14,
          zIndex: 30,
          border: "1px solid rgba(148,163,184,.35)",
          borderRadius: 10,
          padding: "8px 12px",
          background: "rgba(255,255,255,.94)",
          cursor: "pointer",
        }}
      >
        ⌘K Search
      </button>
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          onClick={() => setOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 40,
            background: "rgba(15,23,42,.45)",
            display: "flex",
            justifyContent: "center",
            alignItems: "flex-start",
            paddingTop: "10vh",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "min(680px,92vw)",
              background: "#fff",
              borderRadius: 14,
              boxShadow: "0 20px 60px rgba(0,0,0,.25)",
              overflow: "hidden",
            }}
          >
            <input
              ref={ref}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search authorized AfyaSync modules…"
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "18px",
                fontSize: 17,
                border: 0,
                borderBottom: "1px solid #e2e8f0",
                outline: "none",
              }}
            />
            {results.map((r) => (
              <button
                key={r.path + r.label}
                type="button"
                onClick={() => {
                  setOpen(false);
                  navigate(r.path);
                }}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "13px 18px",
                  border: 0,
                  borderBottom: "1px solid #f1f5f9",
                  background: "#fff",
                  cursor: "pointer",
                }}
              >
                <strong>{r.label}</strong>
                <span style={{ display: "block", fontSize: 12, opacity: 0.65 }}>
                  {r.workspace} · {r.path} · {r.hint}
                </span>
              </button>
            ))}
            {!results.length && (
              <div style={{ padding: 20 }}>No matching authorized module found.</div>
            )}
            <div style={{ padding: "9px 18px", fontSize: 12, opacity: 0.6 }}>
              Ctrl/Cmd + K · results limited to your RBAC profile · Developed by BAHATI GAD WANGWE
            </div>
          </div>
        </div>
      )}
    </>
  );
}
