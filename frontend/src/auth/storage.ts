const ACCESS_KEY = "afyasync.access_token";
const REFRESH_KEY = "afyasync.refresh_token";
const FACILITY_KEY = "afyasync.facility_id";
const FACILITY_NAME_KEY = "afyasync.facility_name";

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_KEY);
}

export function getFacilityId(): string | null {
  return sessionStorage.getItem(FACILITY_KEY);
}

export function getFacilityName(): string | null {
  return sessionStorage.getItem(FACILITY_NAME_KEY);
}

export function setSession(tokens: {
  access_token: string;
  refresh_token?: string | null;
  facility_id?: string | null;
  facility_name?: string | null;
}): void {
  sessionStorage.setItem(ACCESS_KEY, tokens.access_token);
  if (tokens.refresh_token) {
    sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  }
  if (tokens.facility_id) {
    sessionStorage.setItem(FACILITY_KEY, tokens.facility_id);
  }
  if (tokens.facility_name) {
    sessionStorage.setItem(FACILITY_NAME_KEY, tokens.facility_name);
  }
}

export function clearSession(): void {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  sessionStorage.removeItem(FACILITY_KEY);
  sessionStorage.removeItem(FACILITY_NAME_KEY);
}
