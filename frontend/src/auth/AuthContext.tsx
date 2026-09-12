import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError } from "../api/client";
import type { FacilityOption, FacilitySelectionRequired, LoginResult, TokenResponse } from "../api/types";
import {
  DEMO_FACILITY_ID,
  DEMO_FACILITY_NAME,
  DEMO_USERNAME,
} from "../api/demoData";
import {
  clearSession,
  enableDemoMode,
  getAccessToken,
  getDemoUsername,
  getFacilityId,
  getFacilityName,
  getRefreshToken,
  isDemoMode,
  setSession,
} from "./storage";

type AuthState = {
  ready: boolean;
  username: string | null;
  facilityId: string | null;
  facilityName: string | null;
  pendingFacilities: FacilityOption[] | null;
  demoMode: boolean;
  login: (username: string, password: string) => Promise<"ready" | "select_facility">;
  enterDemoMode: () => void;
  selectFacility: (facility: FacilityOption) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

function isFacilitySelectionRequired(result: LoginResult): result is FacilitySelectionRequired {
  return "requires_facility_selection" in result && result.requires_facility_selection === true;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [facilityId, setFacilityId] = useState<string | null>(getFacilityId());
  const [facilityName, setFacilityName] = useState<string | null>(getFacilityName());
  const [pendingFacilities, setPendingFacilities] = useState<FacilityOption[] | null>(null);
  const [demoMode, setDemoMode] = useState(isDemoMode());

  useEffect(() => {
    if (isDemoMode()) {
      setDemoMode(true);
      setUsername(getDemoUsername() || DEMO_USERNAME);
      setFacilityId(getFacilityId() || DEMO_FACILITY_ID);
      setFacilityName(getFacilityName() || DEMO_FACILITY_NAME);
      setReady(true);
      return;
    }

    const token = getAccessToken();
    if (!token) {
      setReady(true);
      return;
    }
    api
      .me()
      .then((me) => {
        setUsername(me.data.username);
        setFacilityId(getFacilityId());
        setFacilityName(getFacilityName());
      })
      .catch(() => {
        clearSession();
        setUsername(null);
        setFacilityId(null);
        setFacilityName(null);
      })
      .finally(() => setReady(true));
  }, []);

  const enterDemoMode = useCallback(() => {
    enableDemoMode(DEMO_USERNAME, DEMO_FACILITY_ID, DEMO_FACILITY_NAME);
    setDemoMode(true);
    setUsername(DEMO_USERNAME);
    setFacilityId(DEMO_FACILITY_ID);
    setFacilityName(DEMO_FACILITY_NAME);
    setPendingFacilities(null);
  }, []);

  const login = useCallback(async (user: string, password: string) => {
    const result = await api.login(user, password);
    if (isFacilitySelectionRequired(result)) {
      setSession({ access_token: result.access_token });
      setUsername(user);
      setPendingFacilities(result.facilities);
      setFacilityId(null);
      setFacilityName(null);
      setDemoMode(false);
      return "select_facility";
    }

    const tokens: TokenResponse = result;
    setSession({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
    });
    try {
      const facilities = await api.facilities();
      if (facilities.length === 1) {
        setSession({
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
          facility_id: facilities[0].facility_id,
          facility_name: facilities[0].facility_name,
        });
        setFacilityId(facilities[0].facility_id);
        setFacilityName(facilities[0].facility_name);
      }
    } catch {
      // JWT may still carry facility context
    }
    const me = await api.me();
    setUsername(me.data.username);
    setPendingFacilities(null);
    setDemoMode(false);
    return "ready";
  }, []);

  const selectFacility = useCallback(async (facility: FacilityOption) => {
    const tokens = await api.selectFacility(facility.facility_id);
    setSession({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      facility_id: facility.facility_id,
      facility_name: facility.facility_name,
    });
    setFacilityId(facility.facility_id);
    setFacilityName(facility.facility_name);
    setPendingFacilities(null);
    setDemoMode(false);
    const me = await api.me();
    setUsername(me.data.username);
  }, []);

  const logout = useCallback(async () => {
    const refresh = getRefreshToken();
    if (refresh && !isDemoMode()) {
      try {
        await api.logout(refresh);
      } catch (err) {
        if (!(err instanceof ApiError)) throw err;
      }
    }
    clearSession();
    setDemoMode(false);
    setUsername(null);
    setFacilityId(null);
    setFacilityName(null);
    setPendingFacilities(null);
  }, []);

  const value = useMemo(
    () => ({
      ready,
      username,
      facilityId,
      facilityName,
      pendingFacilities,
      demoMode,
      login,
      enterDemoMode,
      selectFacility,
      logout,
    }),
    [ready, username, facilityId, facilityName, pendingFacilities, demoMode, login, enterDemoMode, selectFacility, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
