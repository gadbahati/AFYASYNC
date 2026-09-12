import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError } from "../api/client";
import type { FacilityOption } from "../api/types";
import {
  clearSession,
  getAccessToken,
  getFacilityId,
  getFacilityName,
  getRefreshToken,
  setSession,
} from "./storage";

type AuthState = {
  ready: boolean;
  username: string | null;
  facilityId: string | null;
  facilityName: string | null;
  pendingFacilities: FacilityOption[] | null;
  login: (username: string, password: string) => Promise<"ready" | "select_facility">;
  selectFacility: (facility: FacilityOption) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [facilityId, setFacilityId] = useState<string | null>(getFacilityId());
  const [facilityName, setFacilityName] = useState<string | null>(getFacilityName());
  const [pendingFacilities, setPendingFacilities] = useState<FacilityOption[] | null>(null);

  useEffect(() => {
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

  const login = useCallback(async (user: string, password: string) => {
    const result = await api.login(user, password);
    if ("requires_facility_selection" in result && result.requires_facility_selection) {
      setSession({ access_token: result.access_token });
      setUsername(user);
      setPendingFacilities(result.facilities);
      setFacilityId(null);
      setFacilityName(null);
      return "select_facility";
    }
    setSession({
      access_token: result.access_token,
      refresh_token: result.refresh_token,
    });
    // Single-facility login: resolve facility name for UI
    try {
      const facilities = await api.facilities();
      if (facilities.length === 1) {
        setSession({
          access_token: result.access_token,
          refresh_token: result.refresh_token,
          facility_id: facilities[0].facility_id,
          facility_name: facilities[0].facility_name,
        });
        setFacilityId(facilities[0].facility_id);
        setFacilityName(facilities[0].facility_name);
      }
    } catch {
      // facility context still present in JWT even if list fails
    }
    const me = await api.me();
    setUsername(me.data.username);
    setPendingFacilities(null);
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
    const me = await api.me();
    setUsername(me.data.username);
  }, []);

  const logout = useCallback(async () => {
    const refresh = getRefreshToken();
    if (refresh) {
      try {
        await api.logout(refresh);
      } catch (err) {
        if (!(err instanceof ApiError)) throw err;
      }
    }
    clearSession();
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
      login,
      selectFacility,
      logout,
    }),
    [ready, username, facilityId, facilityName, pendingFacilities, login, selectFacility, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
