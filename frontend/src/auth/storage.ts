const ACCESS_KEY = "afyasync.access_token";
const REFRESH_KEY = "afyasync.refresh_token";
const FACILITY_KEY = "afyasync.facility_id";
const FACILITY_NAME_KEY = "afyasync.facility_name";
const ACCOUNT_TYPE_KEY = "afyasync.account_type";
const REMEMBER_KEY = "afyasync.remember";
const REMEMBERED_USER_KEY = "afyasync.remembered_username";

// Authentication tokens are intentionally kept in sessionStorage only. The
// remember-me preference persists only the username, never bearer credentials.
const store = (): Storage => sessionStorage;

function read(key: string): string | null {
  return sessionStorage.getItem(key);
}

export function getAccessToken(): string | null { return read(ACCESS_KEY); }
export function getRefreshToken(): string | null { return read(REFRESH_KEY); }
export function getFacilityId(): string | null { return read(FACILITY_KEY); }
export function getFacilityName(): string | null { return read(FACILITY_NAME_KEY); }
export function getAccountType(): "patient" | "staff" | null {
  const v = read(ACCOUNT_TYPE_KEY);
  return v === "patient" || v === "staff" ? v : null;
}
export function getRememberedUsername(): string | null { return localStorage.getItem(REMEMBERED_USER_KEY); }
export function isRememberMeEnabled(): boolean { return localStorage.getItem(REMEMBER_KEY) === "1"; }

/** Legacy compatibility: AfyaSync never enables demo-mode data. */
export function isDemoMode(): false { return false; }

export function setRememberMe(enabled: boolean, username?: string): void {
  if (enabled) {
    localStorage.setItem(REMEMBER_KEY, "1");
    if (username) localStorage.setItem(REMEMBERED_USER_KEY, username);
  } else {
    localStorage.removeItem(REMEMBER_KEY);
    localStorage.removeItem(REMEMBERED_USER_KEY);
  }
}

export function setSession(tokens: {
  access_token: string;
  refresh_token?: string | null;
  facility_id?: string | null;
  facility_name?: string | null;
  account_type?: "patient" | "staff" | null;
}): void {
  const s = store();
  for (const storage of [sessionStorage, localStorage]) {
    storage.removeItem(ACCESS_KEY);
    storage.removeItem(REFRESH_KEY);
    storage.removeItem(FACILITY_KEY);
    storage.removeItem(FACILITY_NAME_KEY);
    storage.removeItem(ACCOUNT_TYPE_KEY);
  }
  s.setItem(ACCESS_KEY, tokens.access_token);
  if (tokens.refresh_token) s.setItem(REFRESH_KEY, tokens.refresh_token);
  if (tokens.facility_id) s.setItem(FACILITY_KEY, tokens.facility_id);
  if (tokens.facility_name) s.setItem(FACILITY_NAME_KEY, tokens.facility_name);
  if (tokens.account_type) s.setItem(ACCOUNT_TYPE_KEY, tokens.account_type);
}

export function clearSession(): void {
  for (const storage of [sessionStorage, localStorage]) {
    storage.removeItem(ACCESS_KEY);
    storage.removeItem(REFRESH_KEY);
    storage.removeItem(FACILITY_KEY);
    storage.removeItem(FACILITY_NAME_KEY);
    storage.removeItem(ACCOUNT_TYPE_KEY);
  }
}
