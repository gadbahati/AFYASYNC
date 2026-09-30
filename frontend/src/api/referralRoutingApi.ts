import { getAccessToken } from "../auth/storage";
const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
function apiBase(){if(!baseUrl||baseUrl.includes("localhost")||baseUrl.includes("127.0.0.1"))throw new Error("API_BASE_URL_NOT_CONFIGURED");return baseUrl.replace(/\/$/,"");}
export async function getReferralRoutingOptions(payload:{service_code:string;county?:string;network_code?:string;day?:string;limit?:number}){
 const token=getAccessToken();if(!token)throw new Error("AUTH_REQUIRED");
 const response=await fetch(`${apiBase()}/api/v1/referral-routing/options`,{method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},body:JSON.stringify(payload)});
 if(!response.ok)throw new Error(response.status===403?"PERMISSION_DENIED":"REFERRAL_ROUTING_REQUEST_FAILED");
 return response.json();
}
