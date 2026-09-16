import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { getAccessToken } from "../auth/storage";
import type { FacilityOption } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type DirectoryFacility = FacilityOption & {
  facility_code?: string | null;
  county?: string | null;
  sub_county?: string | null;
  facility_type?: string | null;
  keph_level?: string | number | null;
  owner?: string | null;
  operation_status?: string | null;
  registration_number?: string | null;
  source?: "local" | "kmhfr";
};

type KmhfrRecord = Record<string, unknown>;

const PAGE_SIZE = 100;
const KMHFR_ENDPOINTS = [
  "https://api.kmhfr.health.go.ke/api/public/facilities/",
  "https://api.kmhfr.health.go.ke/api/facilities/facilities/",
];

function textValue(item: KmhfrRecord, ...keys: string[]): string | null {
  for (const key of keys) {
    const raw = item[key];
    const value = raw && typeof raw === "object"
      ? ((raw as Record<string, unknown>).name ?? (raw as Record<string, unknown>).label ?? (raw as Record<string, unknown>).value ?? (raw as Record<string, unknown>).code)
      : raw;
    if (value !== undefined && value !== null && String(value).trim()) return String(value).trim();
  }
  return null;
}

function normalizeKmhfrRecord(item: KmhfrRecord): DirectoryFacility | null {
  const id = textValue(item, "id", "uuid");
  const name = textValue(item, "name", "facility_official_name", "official_name", "facility_name");
  if (!name) return null;
  const code = textValue(item, "code", "mfl_code", "facility_code", "facility_code_number");
  return {
    facility_id: `kmhfr:${id || code || name}`,
    facility_name: name,
    facility_code: code,
    registration_number: textValue(item, "registration_number", "registrationNo"),
    county: textValue(item, "county", "county_name"),
    sub_county: textValue(item, "sub_county", "subcounty", "sub_county_name"),
    facility_type: textValue(item, "facility_type_name", "facility_type", "type"),
    keph_level: textValue(item, "keph_level", "keph_level_name", "level"),
    owner: textValue(item, "owner", "owner_name", "facility_owner"),
    operation_status: textValue(item, "operation_status_name", "operation_status", "status") || "ACTIVE",
    source: "kmhfr",
  };
}

async function searchOfficialKmhfr(search: string): Promise<DirectoryFacility[]> {
  const term = search.trim();
  if (!term) return [];
  for (const endpoint of KMHFR_ENDPOINTS) {
    try {
      const url = new URL(endpoint);
      url.searchParams.set("search", term);
      url.searchParams.set("page_size", String(PAGE_SIZE));
      url.searchParams.set("page", "1");
      const response = await fetch(url.toString(), {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(8000),
      });
      if (!response.ok) continue;
      const payload: unknown = await response.json();
      const results = Array.isArray(payload)
        ? payload
        : payload && typeof payload === "object" && Array.isArray((payload as KmhfrRecord).results)
          ? (payload as KmhfrRecord).results as unknown[]
          : payload && typeof payload === "object" && (payload as KmhfrRecord).data && typeof (payload as KmhfrRecord).data === "object" && Array.isArray(((payload as KmhfrRecord).data as KmhfrRecord).results)
            ? ((payload as KmhfrRecord).data as KmhfrRecord).results as unknown[]
            : [];
      const normalized = results
        .filter((item): item is KmhfrRecord => Boolean(item && typeof item === "object"))
        .map(normalizeKmhfrRecord)
        .filter((item): item is DirectoryFacility => Boolean(item));
      if (normalized.length) return normalized;
    } catch {
      // The Ministry registry is sometimes unreachable from cloud hosts. The browser
      // can still reach it in many networks, so try the alternate public endpoint.
    }
  }
  return [];
}

export function FacilitySelectPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [facilities, setFacilities] = useState<DirectoryFacility[]>(auth.pendingFacilities || []);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  async function loadDirectory(search: string, targetPage = 1, showSpinner = true): Promise<DirectoryFacility[]> {
    if (showSpinner) setLoading(true);
    try {
      const rows = await api.facilityDirectory(search, targetPage, PAGE_SIZE);
      const next = rows as DirectoryFacility[];
      if (next.length || !search.trim()) {
        setFacilities(next.map((facility) => ({ ...facility, source: "local" })));
        setPage(targetPage);
        setError(null);
        return next;
      }
      const official = await searchOfficialKmhfr(search);
      setFacilities(official);
      setPage(1);
      setError(null);
      return official;
    } catch (err) {
      if (search.trim()) {
        const official = await searchOfficialKmhfr(search);
        if (official.length) {
          setFacilities(official);
          setPage(1);
          setError(null);
          return official;
        }
      }
      setError(err instanceof ApiError ? err.message || err.code : "Unable to load facilities.");
      return [];
    } finally {
      if (showSpinner) setLoading(false);
    }
  }

  useEffect(() => {
    if (!auth.ready || !auth.username || !getAccessToken()) return;
    void loadDirectory("", 1);
  }, [auth.ready, auth.username]);

  if (!auth.ready) return <div className="auth-page"><div className="card auth-card"><p className="muted">Preparing facility selection…</p></div></div>;
  if (!auth.username || !getAccessToken()) return <Navigate to="/login" replace />;
  if (auth.facilityId && !auth.pendingFacilities) return <Navigate to="/" replace />;

  async function choose(facility: DirectoryFacility) {
    if (selecting) return;
    setSelecting(facility.facility_id);
    setError(null);
    try {
      let selected = facility;
      if (facility.source === "kmhfr") {
        const created = await api.addDirectoryFacility({
          name: facility.facility_name,
          facility_type: facility.facility_type || "HEALTH_FACILITY",
          registration_number: facility.registration_number || facility.facility_code || null,
          county: facility.county || null,
          sub_county: facility.sub_county || null,
        });
        selected = { ...facility, ...created, source: "local" };
      }
      await auth.selectFacility(selected);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Unable to open this facility.");
      setSelecting(null);
    }
  }

  async function searchFacilities(event: React.FormEvent) {
    event.preventDefault();
    const value = query.trim();
    setSubmittedQuery(value);
    await loadDirectory(value, 1);
  }

  async function addAsNewFacility() {
    const name = submittedQuery.trim();
    if (!name || adding || selecting) return;
    setAdding(true);
    setError(null);
    try {
      const created = await api.addDirectoryFacility({ name });
      await choose(created as DirectoryFacility);
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Unable to add this facility.");
    } finally {
      setAdding(false);
    }
  }

  async function changePage(nextPage: number) {
    if (nextPage < 1 || loading) return;
    await loadDirectory(submittedQuery, nextPage);
  }

  const canGoNext = facilities.length === PAGE_SIZE && !facilities.some((facility) => facility.source === "kmhfr");
  const firstResult = facilities.length ? (page - 1) * PAGE_SIZE + 1 : 0;
  const lastResult = (page - 1) * PAGE_SIZE + facilities.length;

  return (
    <main className="auth-page" aria-label="Facility selection" style={{ padding: "24px 14px", alignItems: "flex-start" }}>
      <section className="card" style={{ width: "min(1600px, 100%)", padding: 24, overflow: "hidden" }}>
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ marginBottom: 8 }}>Select facility</h1>
          <p className="muted" style={{ margin: 0 }}>Choose the hospital or health facility where you are working.</p>
        </div>

        <form onSubmit={searchFacilities} style={{ marginBottom: 22 }}>
          <label htmlFor="facility-search" style={{ display: "block", fontWeight: 700, marginBottom: 8 }}>Find your hospital or facility</label>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <input
              id="facility-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type your hospital or facility name and press Enter…"
              aria-label="Hospital or facility name"
              autoComplete="off"
              autoFocus
              style={{ flex: "1 1 560px", minWidth: 0, height: 50, padding: "0 16px", border: "1px solid #cbd5e1", borderRadius: 11, fontSize: 15 }}
            />
            <button type="submit" disabled={loading || selecting !== null} style={{ height: 50, padding: "0 28px", border: 0, borderRadius: 11, fontWeight: 700 }}>{loading ? "Finding…" : "Continue"}</button>
          </div>
          <p className="muted" style={{ margin: "8px 0 0", fontSize: 12 }}>Press Enter after typing the facility name. Your matching facility will appear below; select <strong>Open facility</strong> to continue.</p>
        </form>

        {error && <div className="error" role="alert" style={{ marginBottom: 16 }}>{error}</div>}

        {loading ? (
          <div className="card" style={{ padding: 28, textAlign: "center" }}><p className="muted" style={{ margin: 0 }}>Finding facilities…</p></div>
        ) : facilities.length === 0 ? (
          <div className="card" style={{ padding: 28, textAlign: "center" }}>
            <strong>No facility found</strong>
            <p className="muted" style={{ marginBottom: submittedQuery ? 16 : 0 }}>Try the hospital name, MFL code, county, sub-county or facility type.</p>
            {submittedQuery && (
              <button type="button" onClick={() => void addAsNewFacility()} disabled={adding} style={{ minHeight: 42, padding: "0 20px", fontWeight: 700 }}>
                {adding ? "Adding…" : `Add "${submittedQuery}" as a new facility`}
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="facility-directory-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
              {facilities.map((facility) => (
                <article key={facility.facility_id} onClick={() => void choose(facility)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); void choose(facility); } }} role="button" tabIndex={0} aria-label={`Open ${facility.facility_name}`} style={{ border: "1px solid #e2e8f0", borderRadius: 12, padding: 14, background: "#fff", cursor: selecting ? "wait" : "pointer", minWidth: 0 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start" }}>
                    <h2 style={{ fontSize: 15, lineHeight: 1.3, margin: 0, overflowWrap: "anywhere" }}>{facility.facility_name}</h2>
                    <span style={{ fontSize: 10, fontWeight: 700, whiteSpace: "nowrap", padding: "4px 7px", borderRadius: 999, background: "#f1f5f9" }}>{facility.operation_status || "ACTIVE"}</span>
                  </div>
                  <div style={{ display: "grid", gap: 5, marginTop: 10, fontSize: 12 }}>
                    <div><span className="muted">MFL:</span> {facility.facility_code || facility.registration_number || "—"}</div>
                    <div><span className="muted">Type:</span> {facility.facility_type || "—"}</div>
                    <div><span className="muted">KEPH:</span> {facility.keph_level ? `Level ${facility.keph_level}` : "—"}</div>
                    <div><span className="muted">Location:</span> {facility.county || "—"}{facility.sub_county ? ` • ${facility.sub_county}` : ""}</div>
                    <div><span className="muted">Owner:</span> {facility.owner || "—"}</div>
                  </div>
                  <button type="button" onClick={(event) => { event.stopPropagation(); void choose(facility); }} disabled={Boolean(selecting)} style={{ marginTop: 12, width: "100%", minHeight: 38 }}>{selecting === facility.facility_id ? "Opening…" : "Open facility"}</button>
                </article>
              ))}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap", marginTop: 18 }}>
              <span className="muted">Showing {firstResult}–{lastResult} on page {page}</span>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <button type="button" disabled={page === 1 || loading} onClick={() => void changePage(page - 1)}>Previous</button>
                <strong style={{ padding: "8px 6px" }}>Page {page}</strong>
                <button type="button" disabled={!canGoNext || loading} onClick={() => void changePage(page + 1)}>Next</button>
              </div>
            </div>
          </>
        )}
      </section>
      <style>{`@media (max-width: 1250px) { .facility-directory-grid { grid-template-columns: repeat(3, minmax(0, 1fr)) !important; } } @media (max-width: 900px) { .facility-directory-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; } } @media (max-width: 600px) { .facility-directory-grid { grid-template-columns: 1fr !important; } }`}</style>
    </main>
  );
}
