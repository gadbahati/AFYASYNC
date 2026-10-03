import {createContext,useContext,useMemo,useState,type ReactNode} from "react";
import type {WorkspaceId} from "./workspaces";
const KEY="afyasync.workspace";
const SCOPE_KEY="afyasync.context-scope";
const TENANT_KEY="afyasync.tenant-id";
export type ContextScope="facility"|"network"|"county"|"national";
type State={workspace:WorkspaceId;setWorkspace:(id:WorkspaceId)=>void;scope:ContextScope;setScope:(scope:ContextScope)=>void;tenantId:string|null;setTenantId:(id:string|null)=>void};
const C=createContext<State|null>(null);
function initialScope():ContextScope{const v=sessionStorage.getItem(SCOPE_KEY);return (["facility","network","county","national"] as string[]).includes(v||"")?v as ContextScope:"facility";}
function initialTenant():string|null{return sessionStorage.getItem(TENANT_KEY)}
function initial():WorkspaceId{const v=sessionStorage.getItem(KEY);return (["operations","people","connect","finance","public-health","compliance","resilience","intelligence"] as string[]).includes(v||"")?v as WorkspaceId:"operations";}
export function WorkspaceProvider({children}:{children:ReactNode}){const [workspace,setValue]=useState<WorkspaceId>(initial); const [tenantId,setTenantValue]=useState<string|null>(initialTenant);
 const [scope,setScopeValue]=useState<ContextScope>(initialScope);const setWorkspace=(id:WorkspaceId)=>{sessionStorage.setItem(KEY,id);setValue(id)};
 const setScope=(value:ContextScope)=>{sessionStorage.setItem(SCOPE_KEY,value);setScopeValue(value)}; const setTenantId=(id:string|null)=>{if(id)sessionStorage.setItem(TENANT_KEY,id);else sessionStorage.removeItem(TENANT_KEY);setTenantValue(id)};return <C.Provider value={useMemo(()=>({workspace,setWorkspace,scope,setScope,tenantId,setTenantId}),[workspace,scope,tenantId])}>{children}</C.Provider>}
export function useWorkspace(){const v=useContext(C);if(!v)throw new Error("useWorkspace must be used within WorkspaceProvider");return v}
