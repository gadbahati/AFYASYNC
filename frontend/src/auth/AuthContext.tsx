import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError } from "../api/client";
import type { AuthMe, FacilityOption, FacilitySelectionRequired, LoginResult, TokenResponse } from "../api/types";
import {
  clearSession,
  getAccessToken,
  getAccountType,
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
  accountType: "patient" | "staff" | null;
  pendingFacilities: FacilityOption[] | null;
  login: (username: string, password: string) => Promise<"ready" | "select_facility">;
  patientLogin: (identifier: string, password: string) => Promise<void>;
  patientRegister: (payload: {
    afya_id: string;
    password: string;
    phone?: string;
    email?: string;
  }) => Promise<void>;
  selectFacility: (facility: FacilityOption) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);
const AUTH_EXPIRED_EVENT = "afyasync:auth-expired";

function isFacilitySelectionRequired(result: LoginResult): result is FacilitySelectionRequired {
  return "requires_facility_selection" in result && result.requires_facility_selection === true;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [facilityId, setFacilityId] = useState<string | null>(getFacilityId());
  const [facilityName, setFacilityName] = useState<string | null>(getFacilityName());
  const [accountType, setAccountType] = useState<"patient" | "staff" | null>(getAccountType());
  const [pendingFacilities, setPendingFacilities] = useState<FacilityOption[] | null>(null);

  useEffect(() => {
    const onAuthExpired = () => {
      clearSession();
      setUsername(null);
      setFacilityId(null);
      setFacilityName(null);
      setAccountType(null);
      setPendingFacilities(null);
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, onAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onAuthExpired);
  }, []);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setReady(true);
      return;
    }
    const type = getAccountType();
    api.me()
      .then((me: AuthMe) => {
        setUsername(me.data.username);
        setFacilityId(getFacilityId());
        setFacilityName(getFacilityName());
        setAccountType(type ?? (getFacilityId() ? "staff" : "patient"));
      })
      .catch(() => {
        clearSession();
        setUsername(null);
        setFacilityId(null);
        setFacilityName(null);
        setAccountType(null);
      })
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (user: string, password: string) => {
    const result = await api.login(user, password);
    if (isFacilitySelectionRequired(result)) {
      setSession({ access_token: result.access_token, account_type: "staff" });
      setUsername(user);
      setAccountType("staff");
      setPendingFacilities(result.facilities);
      setFacilityId(null);
      setFacilityName(null);
      return "select_facility";
    }

    const tokens: TokenResponse = result;
    setSession({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      account_type: "staff",
    });
    try {
      const facilities = await api.facilities();
      if (facilities.length === 1) {
        setSession({
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
          facility_id: facilities[0].facility_id,
          facility_name: facilities[0].facility_name,
          account_type: "staff",
        });
        setFacilityId(facilities[0].facility_id);
        setFacilityName(facilities[0].facility_name);
      }
    } catch {
      // Facility context may already be carried by the authenticated session.
    }
    const me: AuthMe = await api.me();
    setUsername(me.data.username);
    setAccountType("staff");
    setPendingFacilities(null);
    return "ready";
  }, []);

  const patientLogin = useCallback(async (identifier: string, password: string) => {
    const tokens = await api.patientLogin(identifier, password);
    setSession({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      account_type: "patient",
    });
    setFacilityId(null);
    setFacilityName(null);
    setAccountType("patient");
    setPendingFacilities(null);
    const me: AuthMe = await api.me();
    setUsername(me.data.username);
  }, []);

  const patientRegister = useCallback(
    async (payload: { afya_id: string; password: string; phone?: string; email?: string }) => {
      const tokens = await api.patientRegister(payload);
      setSession({
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        account_type: "patient",
      });
      setFacilityId(null);
      setFacilityName(null);
      setAccountType("patient");
      setPendingFacilities(null);
      const me: AuthMe = await api.me();
      setUsername(me.data.username);
    },
    []
  );

  const selectFacility = useCallback(async (facility: FacilityOption) => {
    const tokens = await api.selectFacility(facility.facility_id);
    setSession({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      facility_id: facility.facility_id,
      facility_name: facility.facility_name,
      account_type: "staff",
    });
    setFacilityId(facility.facility_id);
    setFacilityName(facility.facility_name);
    setAccountType("staff");
    setPendingFacilities(null);
    const me: AuthMe = await api.me();
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
    setAccountType(null);
    setPendingFacilities(null);
  }, []);

  const value = useMemo(
    () => ({
      ready,
      username,
      facilityId,
      facilityName,
      accountType,
      pendingFacilities,
      login,
      patientLogin,
      patientRegister,
      selectFacility,
      logout,
    }),
    [
      ready,
      username,
      facilityId,
      facilityName,
      accountType,
      pendingFacilities,
      login,
      patientLogin,
      patientRegister,
      selectFacility,
      logout,
    ]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
