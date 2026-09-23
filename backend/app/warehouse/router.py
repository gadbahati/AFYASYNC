"""National warehouse views & CSV export APIs."""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.rbac.models import User
from app.warehouse.service import (
    county_fact_table,
    export_csv,
    national_fact_summary,
    warehouse_catalog,
)

router = APIRouter(prefix="/api/v1/warehouse", tags=["Warehouse"])


@router.get("/catalog")
def catalog(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return warehouse_catalog()


@router.get("/facts")
def facts(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=1, le=365),
):
    _ = user
    return national_fact_summary(db, days=days)


@router.get("/county-facts")
def county_facts(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=1, le=365),
):
    _ = user
    rows = county_fact_table(db, days=days)
    return {
        "count": len(rows),
        "rows": rows,
        "developer": "BAHATI GAD WANGWE",
    }


@router.get("/export/county-facts.csv")
def export_county_csv(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=1, le=365),
):
    _ = user
    rows = county_fact_table(db, days=days)
    csv_body = export_csv(
        rows,
        fieldnames=[
            "county",
            "active_facilities",
            "encounters_all_time",
            "claims_in_window",
            "window_days",
        ],
    )
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="afyasync_county_facts.csv"'
        },
    )
