import {createContext,useContext,useMemo,useState,type ReactNode} from "react";
import type {WorkspaceId} from "./workspaces";
const KEY="afyasync.workspace";
const SCOPE_KEY="afyasync.context-scope";
export type ContextScope="facility"|"network"|"county"|"national";
type State={workspace:WorkspaceId;setWorkspace:(id:WorkspaceId)=>void;scope:ContextScope;setScope:(scope:ContextScope)=>void};
const C=createContext<State|null>(null);
function initialScope():ContextScope{const v=sessionStorage.getItem(SCOPE_KEY);return (["facility","network","county","national"] as string[]).includes(v||"")?v as ContextScope:"facility";}
function initial():WorkspaceId{const v=sessionStorage.getItem(KEY);return (["operations","people","connect","finance","public-health","compliance","resilience","intelligence"] as string[]).includes(v||"")?v as WorkspaceId:"operations";}
export function WorkspaceProvider({children}:{children:ReactNode}){const [workspace,setValue]=useState<WorkspaceId>(initial);
 const [scope,setScopeValue]=useState<ContextScope>(initialScope);const setWorkspace=(id:WorkspaceId)=>{sessionStorage.setItem(KEY,id);setValue(id)};
 const setScope=(value:ContextScope)=>{sessionStorage.setItem(SCOPE_KEY,value);setScopeValue(value)};return <C.Provider value={useMemo(()=>({workspace,setWorkspace,scope,setScope}),[workspace,scope])}>{children}</C.Provider>}
export function useWorkspace(){const v=useContext(C);if(!v)throw new Error("useWorkspace must be used within WorkspaceProvider");return v}
