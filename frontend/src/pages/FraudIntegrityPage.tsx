import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function FraudIntegrityPage(){
 const [scan,setScan]=useState<any>(null); const [cases,setCases]=useState<any[]>([]); const [days,setDays]=useState("30"); const [message,setMessage]=useState("");
 const load=async()=>{try{const s=await api.fraudIntegrityScan(Number(days));setScan(s);setCases(await api.fraudIntegrityCases());}catch(e){setMessage(e instanceof Error?e.message:String(e));}};
 useEffect(()=>{load()},[]);
 const openCase=async(signal:any)=>{try{await api.fraudIntegrityCreateCase({signal});await load();}catch(e){setMessage(e instanceof Error?e.message:String(e));}};
 const resolve=async(id:string,status:string)=>{try{await api.fraudIntegrityResolveCase(id,{status,note:"Reviewed in fraud integrity workspace"});await load();}catch(e){setMessage(e instanceof Error?e.message:String(e));}};
 return <div className="page"><h1>Fraud, Waste & Abuse Intelligence</h1><p>Investigative signals across claims, adjudication and settlement. Signals are not automatic findings of fraud.</p>
 <section className="card"><label>Window <select value={days} onChange={e=>setDays(e.target.value)}><option>30</option><option>60</option><option>90</option></select></label><button onClick={load}>Run integrity scan</button>{message&&<p>{message}</p>}</section>
 {scan&&<section className="card"><h2>Integrity posture</h2><p>Score: <strong>{scan.integrity_score}</strong> · Band: <strong>{scan.band}</strong></p><p>Claims scanned: {scan.claims_scanned} · Signals: {scan.signal_count} · High: {scan.high_severity} · Medium: {scan.medium_severity}</p><div>{(scan.signals||[]).map((s:any,i:number)=><div key={i} className="card"><strong>{s.code}</strong> · {s.severity}<p>{s.message}</p><button onClick={()=>openCase(s)}>Open investigation case</button></div>)}</div></section>}
 <section className="card"><h2>Investigation cases</h2>{cases.map(c=><div className="card" key={c.id}><strong>{c.case_number}</strong> · {c.signal_code} · {c.severity} · {c.status}<p>{c.summary}</p>{c.status==="OPEN"&&<><button onClick={()=>resolve(c.id,"MONITORING")}>Monitor</button> <button onClick={()=>resolve(c.id,"CONFIRMED")}>Confirm</button> <button onClick={()=>resolve(c.id,"DISMISSED")}>Dismiss</button></>}</div>)}</section></div>
}