import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { useAuth } from "./AuthContext";
import { isPathAllowed } from "./moduleAccess";

type ModuleAccessState = {
  ready: boolean;
  allowedPaths: string[] | null;
  isAdmin: boolean;
  isAllowed: (pathname: string) => boolean;
  refresh: () => void;
};

const ModuleAccessContext = createContext<ModuleAccessState | null>(null);

export function ModuleAccessProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const [ready, setReady] = useState(false);
  const [allowedPaths, setAllowedPaths] = useState<string[] | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!auth.ready || !auth.facilityId || auth.accountType === "patient") {
      setReady(true);
      setAllowedPaths(null);
      return;
    }
    let cancelled = false;
    setReady(false);
    api
      .contextOverview()
      .then((v: any) => {
        if (cancelled) return;
        const paths = v?.module_actions?.allowed_paths;
        setAllowedPaths(Array.isArray(paths) ? paths : []);
        setIsAdmin(Boolean(v?.authorization?.system_administrator || v?.module_actions?.is_admin));
      })
      .catch(() => {
        if (!cancelled) {
          // Fail closed for navigation only after error: allow shell paths via isPathAllowed helpers
          setAllowedPaths([]);
        }
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [auth.ready, auth.facilityId, auth.accountType, tick]);

  const value = useMemo<ModuleAccessState>(
    () => ({
      ready,
      allowedPaths,
      isAdmin,
      isAllowed: (pathname: string) => isPathAllowed(pathname, isAdmin ? null : allowedPaths),
      refresh: () => setTick((n) => n + 1),
    }),
    [ready, allowedPaths, isAdmin],
  );

  return <ModuleAccessContext.Provider value={value}>{children}</ModuleAccessContext.Provider>;
}

export function useModuleAccess(): ModuleAccessState {
  const ctx = useContext(ModuleAccessContext);
  if (!ctx) {
    return {
      ready: true,
      allowedPaths: null,
      isAdmin: false,
      isAllowed: () => true,
      refresh: () => undefined,
    };
  }
  return ctx;
}
