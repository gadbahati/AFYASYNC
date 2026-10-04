import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError } from "../api/client";
import type { AuthMe, FacilityOption, FacilitySelectionRequired, GovernmentOrganizationOption, GovernmentSelectionRequired, LoginResult, TokenResponse } from "../api/types";
import {
  clearSession,
  getAccessToken,
  getAccountType,
  getFacilityId,
  getFacilityName,
  getOrganizationId,
  getPortalType,
  getRefreshToken,
  setSession,
} from "./storage";

type AuthState = {
  ready: boolean;
  username: string | null;
  facilityId: string | null;
  facilityName: string | null;
  accountType: "patient" | "staff" | null;
  portalType: "patient" | "facility" | "government" | null;
  organizationId: string | null;
  governmentOrganization: GovernmentOrganizationOption | null;
  contextScope: "facility" | "network" | "county" | "national";
  pendingFacilities: FacilityOption[] | null;
  pendingGovernmentOrganizations: GovernmentOrganizationOption[] | null;
  login: (username: string, password: string) => Promise<"ready" | "select_facility">;
  governmentLogin: (username: string, password: string) => Promise<"ready" | "select_organization">;
  selectGovernmentOrganization: (organization: GovernmentOrganizationOption) => Promise<void>;
  patientLogin: (identifier: string, password: string) => Promise<void>;
  patientRegister: (payload: {
    afya_id: string;
    password: string;
    first_name?: string;
    last_name?: string;
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
  const [portalType, setPortalType] = useState<"patient" | "facility" | "government" | null>(getPortalType());
  const [organizationId, setOrganizationId] = useState<string | null>(getOrganizationId());
  const [governmentOrganization, setGovernmentOrganization] = useState<GovernmentOrganizationOption | null>(null);
  const [pendingGovernmentOrganizations, setPendingGovernmentOrganizations] = useState<GovernmentOrganizationOption[] | null>(null);
  const [contextScope, setContextScope] = useState<"facility" | "network" | "county" | "national">("facility");
  const [pendingFacilities, setPendingFacilities] = useState<FacilityOption[] | null>(null);

  useEffect(() => {
    const onAuthExpired = () => {
      clearSession();
      setUsername(null);
      setFacilityId(null);
      setFacilityName(null);
      setAccountType(null);
      setPortalType(null);
      setOrganizationId(null);
      setGovernmentOrganization(null);
      setPendingGovernmentOrganizations(null);
      setContextScope("facility");
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
        setPortalType(getPortalType() ?? (getFacilityId() ? "facility" : "patient"));
        setOrganizationId(getOrganizationId());
      })
      .catch(() => {
        clearSession();
        setUsername(null);
        setFacilityId(null);
        setFacilityName(null);
        setAccountType(null);
        setPortalType(null);
        setOrganizationId(null);
        setGovernmentOrganization(null);
        setPendingGovernmentOrganizations(null);
        setContextScope("facility");
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
    setContextScope("facility");
    setPendingFacilities(null);
    return "ready";
  }, []);

  const governmentLogin = useCallback(async (user: string, password: string) => {
    const result = await api.governmentLogin(user, password) as TokenResponse | GovernmentSelectionRequired;
    if ("requires_government_organization_selection" in result && result.requires_government_organization_selection) {
      setSession({ access_token: result.access_token, account_type: "staff", portal_type: "government" });
      setUsername(user);
      setAccountType("staff");
      setPortalType("government");
      setOrganizationId(null);
      setGovernmentOrganization(null);
      setPendingGovernmentOrganizations(result.organizations);
      return "select_organization";
    }
    const tokens = result as TokenResponse;
    setSession({ access_token: tokens.access_token, refresh_token: tokens.refresh_token, account_type: "staff", portal_type: "government" });
    const me = await api.governmentMe();
    const data = me.data;
    const org: GovernmentOrganizationOption = {
      organization_id: data.organization_id,
      organization_name: data.organization_name,
      organization_type: data.organization_type,
      scope_level: data.scope_level,
      role_code: data.role_code,
    };
    setUsername(data.username);
    setAccountType("staff");
    setPortalType("government");
    setOrganizationId(data.organization_id);
    setGovernmentOrganization(org);
    setPendingGovernmentOrganizations(null);
    setFacilityId(null);
    setFacilityName(null);
    return "ready";
  }, []);

  const selectGovernmentOrganization = useCallback(async (organization: GovernmentOrganizationOption) => {
    const tokens = await api.selectGovernmentOrganization(organization.organization_id);
    setSession({ access_token: tokens.access_token, refresh_token: tokens.refresh_token, account_type: "staff", portal_type: "government", organization_id: organization.organization_id });
    setPortalType("government");
    setAccountType("staff");
    setOrganizationId(organization.organization_id);
    setGovernmentOrganization(organization);
    setFacilityId(null);
    setFacilityName(null);
    setPendingGovernmentOrganizations(null);
    const me = await api.governmentMe();
    setUsername(me.data.username);
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
    setPortalType("patient");
    setOrganizationId(null);
    setGovernmentOrganization(null);
    setPendingGovernmentOrganizations(null);
    setPendingFacilities(null);
    const me: AuthMe = await api.me();
    setUsername(me.data.username);
  }, []);

  const patientRegister = useCallback(
    async (payload: {
      afya_id: string;
      password: string;
      first_name?: string;
      last_name?: string;
      phone?: string;
      email?: string;
    }) => {
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
    setPortalType("facility");
    setOrganizationId(null);
    setGovernmentOrganization(null);
    setPendingGovernmentOrganizations(null);
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
    setPortalType(null);
    setOrganizationId(null);
    setGovernmentOrganization(null);
    setPendingGovernmentOrganizations(null);
    setPendingFacilities(null);
  }, []);

  const value = useMemo(
    () => ({
      ready,
      username,
      facilityId,
      facilityName,
      accountType,
      contextScope,
      pendingFacilities,
      portalType,
      organizationId,
      governmentOrganization,
      pendingGovernmentOrganizations,
      login,
      governmentLogin,
      selectGovernmentOrganization,
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
      contextScope,
      pendingFacilities,
      portalType,
      organizationId,
      governmentOrganization,
      pendingGovernmentOrganizations,
      login,
      governmentLogin,
      selectGovernmentOrganization,
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
