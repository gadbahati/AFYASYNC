import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api/client";

type Household = {
  id: string; head_person_id: string; head_name: string; head_afya_id?: string | null;
  label?: string | null; county?: string | null; status: string; member_count: number;
};
type Membership = {
  id: string; membership_number?: string | null; status: string; scheme_code?: string | null;
  employer_name?: string | null; effective_from?: string | null; effective_to?: string | null;
};
type Member = {
  id: string; person_id: string; afya_id?: string | null; name: string; phone?: string | null;
  status: string; relationship_to_head: string; is_dependant: boolean; effective_from?: string | null;
  memberships: Membership[];
};
type HouseholdDetail = Household & { members: Member[] };
type Patient = { id: string; afya_id: string; first_name: string; middle_name?: string | null; last_name: string; phone?: string | null };

const errorText = (e: unknown) => e instanceof ApiError ? (e.message || e.code) : "Request failed";

export function HouseholdWalletPage() {
  const [households, setHouseholds] = useState<Household[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selected, setSelected] = useState<HouseholdDetail | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [showMembership, setShowMembership] = useState<string | null>(null);
  const [headId, setHeadId] = useState("");
  const [label, setLabel] = useState("");
  const [county, setCounty] = useState("");
  const [memberPersonId, setMemberPersonId] = useState("");
  const [relationship, setRelationship] = useState("CHILD");
  const [dependant, setDependant] = useState(true);
  const [membershipNumber, setMembershipNumber] = useState("");
  const [schemeCode, setSchemeCode] = useState("");
  const [employer, setEmployer] = useState("");

  const load = async (term = search) => {
    setLoading(true); setError(null);
    try {
      const [hh, people] = await Promise.all([api.identityHouseholds(term), api.listPatients(100, 0)]);
      setHouseholds(hh || []);
      setPatients(people?.items || []);
    } catch (e) { setError(errorText(e)); }
    finally { setLoading(false); }
  };

  useEffect(() => { void load(""); }, []);

  const openHousehold = async (id: string) => {
    setDetailLoading(true); setError(null);
    try { setSelected(await api.identityHousehold(id)); }
    catch (e) { setError(errorText(e)); }
    finally { setDetailLoading(false); }
  };

  const availablePeople = useMemo(
    () => patients.filter(p => !selected?.members.some(m => m.person_id === p.id)),
    [patients, selected],
  );

  const create = async (e: FormEvent) => {
    e.preventDefault(); setError(null); setNotice(null);
    try {
      const result = await api.createHousehold({ head_person_id: headId, label: label || undefined, county: county || undefined });
      setShowCreate(false); setHeadId(""); setLabel(""); setCounty("");
      setNotice("Household created successfully."); await load(""); await openHousehold(result.id);
    } catch (err) { setError(errorText(err)); }
  };

  const addMember = async (e: FormEvent) => {
    e.preventDefault(); if (!selected) return;
    setError(null); setNotice(null);
    try {
      await api.addHouseholdMember(selected.id, { person_id: memberPersonId, relationship_to_head: relationship, is_dependant: dependant });
      setShowAdd(false); setMemberPersonId(""); setNotice("Family member added."); await openHousehold(selected.id); await load(search);
    } catch (err) { setError(errorText(err)); }
  };

  const addMembership = async (e: FormEvent) => {
    e.preventDefault(); const personId = showMembership; if (!personId) return;
    setError(null); setNotice(null);
    try {
      await api.createMembership({ person_id: personId, membership_number: membershipNumber || undefined, scheme_code: schemeCode || undefined, employer_name: employer || undefined });
      setShowMembership(null); setMembershipNumber(""); setSchemeCode(""); setEmployer("");
      setNotice("Coverage membership linked to the family member."); if (selected) await openHousehold(selected.id);
    } catch (err) { setError(errorText(err)); }
  };

  return <div>
    <header className="page-header">
      <div><h1>Household health wallet</h1><p className="muted">One facility-scoped view of a household, its members, dependants and linked coverage memberships.</p></div>
      <div className="actions"><button className="button" onClick={() => setShowCreate(true)}>Create household</button><button className="button secondary" onClick={() => void load(search)}>Refresh</button></div>
    </header>

    {error && <div className="error" role="alert">{error}</div>}
    {notice && <div className="info-box">{notice}</div>}

    <div className="grid-2">
      <section className="card">
        <div className="card-header"><div><h2>Households</h2><p className="muted small">{households.length} visible at this facility</p></div></div>
        <div style={{display:"flex",gap:8,marginBottom:14}}>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search family, head or phone" style={{flex:1}} />
          <button className="button secondary" onClick={() => void load(search)}>Search</button>
        </div>
        {loading ? <p className="muted">Loading households…</p> : households.length === 0 ? <div className="info-box">No household records found for this facility.</div> :
          <div className="table-wrap"><table><thead><tr><th>Household</th><th>Head</th><th>Members</th><th></th></tr></thead><tbody>
            {households.map(h => <tr key={h.id}><td><strong>{h.label || "Family household"}</strong><div className="muted small">{h.county || "County not recorded"}</div></td><td>{h.head_name}<div className="muted small">{h.head_afya_id || "Afya ID unavailable"}</div></td><td>{h.member_count}</td><td><button className="button secondary" onClick={() => void openHousehold(h.id)}>Open wallet</button></td></tr>)}
          </tbody></table></div>}
      </section>

      <section className="card">
        {detailLoading ? <p className="muted">Loading household wallet…</p> : !selected ? <div><h2>Family wallet</h2><p className="muted">Select a household to view members, dependants and coverage.</p></div> :
          <div>
            <div className="card-header"><div><h2>{selected.label || "Family household"}</h2><p className="muted">{selected.county || "County not recorded"} · {selected.member_count} active member(s)</p></div><button className="button" onClick={() => setShowAdd(true)}>Add member</button></div>
            <div className="table-wrap"><table><thead><tr><th>Member</th><th>Relationship</th><th>Coverage</th><th></th></tr></thead><tbody>
              {selected.members.map(m => <tr key={m.id}><td><strong>{m.name}</strong><div className="muted small">{m.afya_id || "Afya ID unavailable"}{m.phone ? " · " + m.phone : ""}</div></td><td><span className="status-pill">{m.relationship_to_head}</span>{m.is_dependant && <div className="muted small">Dependant</div>}</td><td>{m.memberships.length ? m.memberships.map(x => <div key={x.id}><strong>{x.membership_number || "Membership"}</strong><div className="muted small">{x.scheme_code || "Scheme not specified"} · {x.status}</div></div>) : <span className="muted">No linked membership</span>}</td><td><button className="button secondary" onClick={() => setShowMembership(m.person_id)}>Link coverage</button></td></tr>)}
            </tbody></table></div>
            <div className="info-box" style={{marginTop:14}}>The wallet groups household membership information; it does not replace payer verification or benefit adjudication at the point of care.</div>
          </div>}
      </section>
    </div>

    {showCreate && <div className="modal-backdrop"><div className="modal"><h2>Create household</h2><form onSubmit={create}>
      <label>Household head<select value={headId} onChange={e => setHeadId(e.target.value)} required><option value="">Select patient</option>{patients.map(p => <option key={p.id} value={p.id}>{p.first_name} {p.last_name} — {p.afya_id}</option>)}</select></label>
      <label>Household label<input value={label} onChange={e => setLabel(e.target.value)} placeholder="e.g. Bahati family" /></label>
      <label>County<input value={county} onChange={e => setCounty(e.target.value)} placeholder="e.g. Kirinyaga" /></label>
      <div className="actions"><button type="button" className="button secondary" onClick={() => setShowCreate(false)}>Cancel</button><button className="button">Create</button></div>
    </form></div></div>}

    {showAdd && selected && <div className="modal-backdrop"><div className="modal"><h2>Add family member</h2><form onSubmit={addMember}>
      <label>Person<select value={memberPersonId} onChange={e => setMemberPersonId(e.target.value)} required><option value="">Select patient</option>{availablePeople.map(p => <option key={p.id} value={p.id}>{p.first_name} {p.last_name} — {p.afya_id}</option>)}</select></label>
      <label>Relationship<select value={relationship} onChange={e => setRelationship(e.target.value)}><option>CHILD</option><option>SPOUSE</option><option>PARENT</option><option>DEPENDANT</option><option>OTHER</option></select></label>
      <label style={{display:"flex",gap:8,alignItems:"center"}}><input type="checkbox" checked={dependant} onChange={e => setDependant(e.target.checked)} /> Dependant</label>
      <div className="actions"><button type="button" className="button secondary" onClick={() => setShowAdd(false)}>Cancel</button><button className="button">Add member</button></div>
    </form></div></div>}

    {showMembership && <div className="modal-backdrop"><div className="modal"><h2>Link coverage membership</h2><p className="muted small">This creates a membership record for the selected person. Payer verification remains a separate workflow.</p><form onSubmit={addMembership}>
      <label>Membership number<input value={membershipNumber} onChange={e => setMembershipNumber(e.target.value)} placeholder="Membership number" /></label>
      <label>Scheme code<input value={schemeCode} onChange={e => setSchemeCode(e.target.value)} placeholder="Scheme / package code" /></label>
      <label>Employer<input value={employer} onChange={e => setEmployer(e.target.value)} placeholder="Optional employer" /></label>
      <div className="actions"><button type="button" className="button secondary" onClick={() => setShowMembership(null)}>Cancel</button><button className="button">Link membership</button></div>
    </form></div></div>}
  </div>;
}
