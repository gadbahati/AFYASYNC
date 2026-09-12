const ACCESS_KEY = "afyasync.access_token";
const REFRESH_KEY = "afyasync.refresh_token";
const FACILITY_KEY = "afyasync.facility_id";
const FACILITY_NAME_KEY = "afyasync.facility_name";
const REMEMBER_KEY = "afyasync.remember";
const REMEMBERED_USER_KEY = "afyasync.remembered_username";

function store(): Storage {
  return localStorage.getItem(REMEMBER_KEY) === "1" ? localStorage : sessionStorage;
}

function read(key: string): string | null {
  return localStorage.getItem(key) ?? sessionStorage.getItem(key);
}

export function getAccessToken(): string | null {
  return read(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return read(REFRESH_KEY);
}

export function getFacilityId(): string | null {
  return read(FACILITY_KEY);
}

export function getFacilityName(): string | null {
  return read(FACILITY_NAME_KEY);
}

export function getRememberedUsername(): string | null {
  return localStorage.getItem(REMEMBERED_USER_KEY);
}

export function isRememberMeEnabled(): boolean {
  return localStorage.getItem(REMEMBER_KEY) === "1";
}

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
}): void {
  const s = store();
  // Keep a single source of truth for tokens
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  sessionStorage.removeItem(FACILITY_KEY);
  sessionStorage.removeItem(FACILITY_NAME_KEY);
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(FACILITY_KEY);
  localStorage.removeItem(FACILITY_NAME_KEY);

  s.setItem(ACCESS_KEY, tokens.access_token);
  if (tokens.refresh_token) s.setItem(REFRESH_KEY, tokens.refresh_token);
  if (tokens.facility_id) s.setItem(FACILITY_KEY, tokens.facility_id);
  if (tokens.facility_name) s.setItem(FACILITY_NAME_KEY, tokens.facility_name);
}

export function clearSession(): void {
  for (const storage of [sessionStorage, localStorage]) {
    storage.removeItem(ACCESS_KEY);
    storage.removeItem(REFRESH_KEY);
    storage.removeItem(FACILITY_KEY);
    storage.removeItem(FACILITY_NAME_KEY);
  }
}
