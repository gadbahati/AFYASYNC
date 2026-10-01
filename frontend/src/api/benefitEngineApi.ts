import { getAccessToken } from "../auth/storage";
const base=import.meta.env.VITE_API_BASE_URL as string|undefined;
async function call(path:string,init:RequestInit={}){const token=getAccessToken();if(!base||!token)throw new Error("AUTH_REQUIRED");const res=await fetch(base.replace(/\/$/,"")+path,{...init,headers:{"Content-Type":"application/json",Authorization:"Bearer "+token,...(init.headers||{})}});if(!res.ok){const b=await res.json().catch(()=>({}));throw new Error(b.detail||"BENEFIT_ENGINE_REQUEST_FAILED")}return res.json()}
export const quoteBenefit=(payload:unknown)=>call("/api/v1/benefit-engine/quote",{method:"POST",body:JSON.stringify(payload)});
