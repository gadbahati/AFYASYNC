from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context, require_national_permission, require_permission
from app.auth.schemas import FacilityOption
from app.database import get_db
from app.facilities.kmhfr_registry import start_sync, sync_state
from app.facilities.schemas import DepartmentCreate, DepartmentResponse, DepartmentStatusUpdate, FacilityCreate, FacilityResponse, FacilityStatusUpdate, FacilityUpdate, NetworkFacilityResponse
from app.facilities.service import _sync_kmhfr_page, create_department, create_facility, get_facility, list_departments, list_facilities, list_facility_directory, list_network_facilities, update_department_status, update_facility, update_facility_status
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/facilities", tags=["Facilities"])

_KMHFR_SEARCH_ENDPOINTS = (
    "https://api.kmhfr.health.go.ke/api/public/facilities/",
    "https://api.kmhfr.health.go.ke/api/facilities/facilities/",
)


def _lookup_kmhfr_facilities(db: Session, search: str) -> int:
    """Resolve a typed facility name/code directly against the official KMHFR registry.

    The national background sync is intentionally asynchronous. This targeted lookup
    makes the facility picker useful immediately when a requested facility has not
    reached the local database yet.
    """
    term = search.strip()
    if not term:
        return 0

    headers = {"Accept": "application/json", "User-Agent": "AfyaSync/1.0 facility-search"}
    for endpoint in _KMHFR_SEARCH_ENDPOINTS:
        for parameter in ("name", "search"):
            try:
                with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
                    response = client.get(endpoint, params={parameter: term, "page_size": 30, "page": 1, "format": "json"})
                    response.raise_for_status()
                    payload = response.json()
                    results = payload.get("results", payload if isinstance(payload, list) else [])
                    if not isinstance(results, list) or not results:
                        continue
                    imported = 0
                    for item in results:
                        if isinstance(item, dict) and _sync_kmhfr_page(item, db):
                            imported += 1
                    db.commit()
                    return len(results)
            except Exception:
                db.rollback()
                continue
    return 0


@router.post("", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED)
def register_facility(payload: FacilityCreate, user: User = Depends(require_permission("facilities.create")), db: Session = Depends(get_db)) -> FacilityResponse:
    return create_facility(db, payload.model_dump(), actor_user_id=user.id)

@router.get("", response_model=list[FacilityResponse])
def get_facilities(limit: int = Query(default=50, ge=1, le=100), _: User = Depends(require_permission("facilities.read")), db: Session = Depends(get_db)) -> list[FacilityResponse]:
    return list_facilities(db, limit)

@router.get("/directory", response_model=list[FacilityOption])
def get_facility_directory(
    response: Response,
    search: str | None = Query(default=None, max_length=150),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=30, ge=1, le=100),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FacilityOption]:
    # Keep the national import running in the background, but resolve an active
    # typed search directly against KMHFR so a facility can be opened before the
    # full registry has finished importing locally.
    start_sync()
    if search and search.strip():
        _lookup_kmhfr_facilities(db, search)
    offset = (page - 1) * page_size
    rows = list_facility_directory(db, search=search, limit=page_size, offset=offset)
    total_rows = list_facility_directory(db, search=search, limit=1, offset=0, count_only=True)
    response.headers["X-Facility-Total"] = str(total_rows)
    response.headers["X-Facility-Page"] = str(page)
    response.headers["X-Facility-Page-Size"] = str(page_size)
    return [FacilityOption(facility_id=row.id, facility_name=row.name, county=row.county, sub_county=row.sub_county, facility_type=row.facility_type, registration_number=row.registration_number) for row in rows]

@router.get("/directory/status")
def get_facility_directory_status(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, int | bool | str]:
    return sync_state(db)

@router.get("/network", response_model=list[NetworkFacilityResponse])
def get_network_facilities(limit: int = Query(default=100, ge=1, le=200), facility_status: str | None = Query(default=None), county: str | None = Query(default=None, max_length=100), _: User = Depends(require_national_permission("facilities.network.read")), db: Session = Depends(get_db)) -> list[NetworkFacilityResponse]:
    try:
        return list_network_facilities(db, limit=limit, status_filter=facility_status, county=county)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/network", response_model=NetworkFacilityResponse, status_code=status.HTTP_201_CREATED)
def create_network_facility(payload: FacilityCreate, user: User = Depends(require_national_permission("facilities.network.manage")), db: Session = Depends(get_db)) -> NetworkFacilityResponse:
    return create_facility(db, payload.model_dump(), actor_user_id=user.id)

@router.patch("/network/{facility_id}", response_model=NetworkFacilityResponse)
def update_network_facility(facility_id: UUID, payload: FacilityUpdate, user: User = Depends(require_national_permission("facilities.network.manage")), db: Session = Depends(get_db)) -> NetworkFacilityResponse:
    try:
        return update_facility(db, facility_id, payload.model_dump(exclude_unset=True), actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code={"FACILITY_NOT_FOUND": 404, "NO_CHANGES": 400}.get(code, 400), detail=code) from exc

@router.patch("/network/{facility_id}/status", response_model=NetworkFacilityResponse)
def update_network_facility_status(facility_id: UUID, payload: FacilityStatusUpdate, user: User = Depends(require_national_permission("facilities.network.manage")), db: Session = Depends(get_db)) -> NetworkFacilityResponse:
    try:
        return update_facility_status(db, facility_id, payload.status, reason=payload.reason, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code={"FACILITY_NOT_FOUND": 404, "INVALID_FACILITY_STATUS": 400, "FACILITY_STATUS_UNCHANGED": 400, "INVALID_FACILITY_STATUS_TRANSITION": 409, "FACILITY_STATUS_REASON_REQUIRED": 400}.get(code, 400), detail=code) from exc

@router.get("/me", response_model=FacilityResponse)
def get_current_facility(facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission("facilities.read")), db: Session = Depends(get_db)) -> FacilityResponse:
    facility = get_facility(db, facility_id)
    if facility is None:
        raise HTTPException(status_code=404, detail="FACILITY_NOT_FOUND")
    return facility

@router.patch("/me", response_model=FacilityResponse)
def update_current_facility(payload: FacilityUpdate, facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission("facilities.manage")), db: Session = Depends(get_db)) -> FacilityResponse:
    try:
        return update_facility(db, facility_id, payload.model_dump(exclude_unset=True), actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code={"FACILITY_NOT_FOUND": 404, "NO_CHANGES": 400}.get(code, 400), detail=code) from exc

@router.patch("/me/status", response_model=FacilityResponse)
def change_current_facility_status(payload: FacilityStatusUpdate, facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission("facilities.manage")), db: Session = Depends(get_db)) -> FacilityResponse:
    try:
        return update_facility_status(db, facility_id, payload.status, reason=reason, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code={"FACILITY_NOT_FOUND": 404, "INVALID_FACILITY_STATUS": 400, "FACILITY_STATUS_UNCHANGED": 400, "INVALID_FACILITY_STATUS_TRANSITION": 409, "FACILITY_STATUS_REASON_REQUIRED": 400}.get(code, 400), detail=code) from exc

@router.post("/{facility_id}/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def register_department(facility_id: UUID, payload: DepartmentCreate, user: User = Depends(require_permission("facilities.department.write")), context_facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> DepartmentResponse:
    if facility_id != context_facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        return create_department(db, facility_id, payload.model_dump(), actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code={"FACILITY_NOT_FOUND": 404, "DEPARTMENT_CODE_EXISTS": 409}.get(code, 400), detail=code) from exc

@router.get("/{facility_id}/departments", response_model=list[DepartmentResponse])
def get_departments(facility_id: UUID, _: User = Depends(require_permission("facilities.department.read")), context_facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> list[DepartmentResponse]:
    if facility_id != context_facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return list_departments(db, facility_id)

@router.patch("/{facility_id}/departments/{department_id}/status", response_model=DepartmentResponse)
def change_department_status(facility_id: UUID, department_id: UUID, payload: DepartmentStatusUpdate, user: User = Depends(require_permission("facilities.department.write")), context_facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> DepartmentResponse:
    if facility_id != context_facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        return update_department_status(db, facility_id, department_id, payload.status, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code={"DEPARTMENT_NOT_FOUND": 404, "INVALID_DEPARTMENT_STATUS": 400, "FACILITY_NOT_FOUND": 404}.get(code, 400), detail=code) from exc
