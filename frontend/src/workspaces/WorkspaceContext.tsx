import {createContext,useContext,useMemo,useState,type ReactNode} from "react";
import type {WorkspaceId} from "./workspaces";
const KEY="afyasync.workspace";
type State={workspace:WorkspaceId;setWorkspace:(id:WorkspaceId)=>void};
const C=createContext<State|null>(null);
function initial():WorkspaceId{const v=sessionStorage.getItem(KEY);return (["operations","people","connect","finance","public-health","compliance","resilience","intelligence"] as string[]).includes(v||"")?v as WorkspaceId:"operations";}
export function WorkspaceProvider({children}:{children:ReactNode}){const [workspace,setValue]=useState<WorkspaceId>(initial);const setWorkspace=(id:WorkspaceId)=>{sessionStorage.setItem(KEY,id);setValue(id)};return <C.Provider value={useMemo(()=>({workspace,setWorkspace}),[workspace])}>{children}</C.Provider>}
export function useWorkspace(){const v=useContext(C);if(!v)throw new Error("useWorkspace must be used within WorkspaceProvider");return v}
