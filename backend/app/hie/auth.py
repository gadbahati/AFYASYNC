"""Phase 167: HIE OAuth2 client-credentials token handling."""
from __future__ import annotations
import os
import threading
import time
import httpx

_lock=threading.Lock()
_cached_token: str|None=None
_cached_expiry=0.0

def get_hie_access_token() -> str|None:
    global _cached_token, _cached_expiry
    now=time.time()
    if _cached_token and now < _cached_expiry - 30: return _cached_token
    token_url=os.getenv("HIE_AUTH_TOKEN_URL","").strip()
    client_id=os.getenv("HIE_CLIENT_ID","").strip()
    client_secret=os.getenv("HIE_CLIENT_SECRET","").strip()
    if not (token_url and client_id and client_secret): return None
    with _lock:
        now=time.time()
        if _cached_token and now < _cached_expiry - 30: return _cached_token
        timeout=float(os.getenv("HIE_AUTH_TIMEOUT_SECONDS","15"))
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response=client.post(token_url,data={"grant_type":"client_credentials","client_id":client_id,"client_secret":client_secret},headers={"Accept":"application/json"})
        response.raise_for_status()
        data=response.json()
        token=str(data.get("access_token") or "").strip()
        if not token: raise RuntimeError("HIE_AUTH_TOKEN_MISSING")
        expires_in=int(data.get("expires_in") or 300)
        _cached_token=token
        _cached_expiry=time.time()+max(60,expires_in)
        return token

def clear_hie_token_cache() -> None:
    global _cached_token,_cached_expiry
    with _lock:
        _cached_token=None; _cached_expiry=0.0
