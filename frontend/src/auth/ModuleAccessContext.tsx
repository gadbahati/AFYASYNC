import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { useAuth } from "./AuthContext";
import { isPathAllowed } from "./moduleAccess";

type ModuleAccessState = {
  ready: boolean;
  allowedPaths: string[] | null;
  catalogPaths: string[];
  isAdmin: boolean;
  isAllowed: (pathname: string) => boolean;
  refresh: () => void;
};

const ModuleAccessContext = createContext<ModuleAccessState | null>(null);

export function ModuleAccessProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const [ready, setReady] = useState(false);
  const [allowedPaths, setAllowedPaths] = useState<string[] | null>(null);
  const [catalogPaths, setCatalogPaths] = useState<string[]>([]);
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
        const catalog = v?.module_actions?.catalog_paths;
        setAllowedPaths(Array.isArray(paths) ? paths : []);
        setCatalogPaths(Array.isArray(catalog) ? catalog : []);
        setIsAdmin(Boolean(v?.authorization?.system_administrator || v?.module_actions?.is_admin));
      })
      .catch(() => {
        if (!cancelled) {
          setAllowedPaths(null);
          setCatalogPaths([]);
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
      catalogPaths,
      isAdmin,
      isAllowed: (pathname: string) =>
        isAdmin ? true : isPathAllowed(pathname, allowedPaths, catalogPaths),
      refresh: () => setTick((n) => n + 1),
    }),
    [ready, allowedPaths, catalogPaths, isAdmin],
  );

  return <ModuleAccessContext.Provider value={value}>{children}</ModuleAccessContext.Provider>;
}

export function useModuleAccess(): ModuleAccessState {
  const ctx = useContext(ModuleAccessContext);
  if (!ctx) {
    return {
      ready: true,
      allowedPaths: null,
      catalogPaths: [],
      isAdmin: false,
      isAllowed: () => true,
      refresh: () => undefined,
    };
  }
  return ctx;
}
