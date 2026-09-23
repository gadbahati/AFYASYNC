"""Training, SOP packs & help content APIs."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import require_permission
from app.rbac.models import User
from app.training.content import HELP_TOPICS, SOP_PACKS, TRAINING_MODULES

router = APIRouter(prefix="/api/v1/training", tags=["Training"])


@router.get("/sops")
def list_sops(
    user: User = Depends(require_permission("reports.read")),
    audience: str | None = Query(default=None, max_length=40),
):
    _ = user
    packs = SOP_PACKS
    if audience:
        a = audience.strip().lower()
        packs = [p for p in packs if a in [x.lower() for x in p.get("audience", [])]]
    return {"count": len(packs), "sops": packs, "developer": "BAHATI GAD WANGWE"}


@router.get("/sops/{sop_id}")
def get_sop(
    sop_id: str,
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    for p in SOP_PACKS:
        if p["id"].upper() == sop_id.strip().upper():
            return p
    raise HTTPException(status_code=404, detail="SOP_NOT_FOUND")


@router.get("/modules")
def list_modules(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return {"count": len(TRAINING_MODULES), "modules": TRAINING_MODULES, "developer": "BAHATI GAD WANGWE"}


@router.get("/help")
def help_topics(
    user: User = Depends(require_permission("reports.read")),
    q: str | None = Query(default=None, max_length=80),
):
    _ = user
    topics = HELP_TOPICS
    if q:
        needle = q.strip().lower()
        topics = [
            t
            for t in topics
            if needle in t["q"].lower() or needle in t["a"].lower() or needle in t["id"].lower()
        ]
    return {"count": len(topics), "topics": topics, "developer": "BAHATI GAD WANGWE"}


@router.get("/catalog")
def full_catalog(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return {
        "sops": SOP_PACKS,
        "modules": TRAINING_MODULES,
        "help": HELP_TOPICS,
        "developer": "BAHATI GAD WANGWE",
    }
