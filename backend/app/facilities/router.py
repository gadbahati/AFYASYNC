from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context, require_national_permission, require_permission
from app.auth.schemas import FacilityOption
from app.database import get_db
from app.facilities.kmhfr_registry import start_sync, sync_state
from app.facilities.schemas import DepartmentCreate, DepartmentResponse, DepartmentStatusUpdate, FacilityCreate, FacilityQuickCreate, FacilityResponse, FacilityStatusUpdate, FacilityUpdate, NetworkFacilityResponse
from app.facilities.service import _sync_kmhfr_page, create_department, create_directory_facility, create_facility, get_facility, list_departments, list_facilities, list_facility_directory, list_network_facilities, update_department_status, update_facility, update_facility_status
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/facilities", tags=["Facilities"])

_KMHFR_SEARCH_ENDPOINTS = (
    "https://api.kmhfr.health.go.ke/api/public/facilities/",
    "https://api.kmhfr.health.go.ke/api/facilities/facilities/",
)


def _lookup_kmhfr_facilities(db: Session, search: str) -> int:
    """Look up the typed term in the official KMHFR registry and hydrate the local directory."""
    term = search.strip()
    if not term:
        return 0

    headers = {"Accept": "application/json", "User-Agent": "AfyaSync/1.0 facility-search"}
    # KMHFR's public registry supports full-text `search`. Do not use the
    # legacy `name` parameter first: some registry deployments ignore it and
    # return the first page, which made AfyaSync appear to find only local rows.
    for endpoint in _KMHFR_SEARCH_ENDPOINTS:
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
                response = client.get(endpoint, params={"search": term, "page_size": 100, "page": 1})
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict):
                    results = payload.get("results", [])
                elif isinstance(payload, list):
                    results = payload
                else:
                    results = []
                if not isinstance(results, list):
                    continue
                hydrated = 0
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    normalized = {
                        "id": item.get("id") or item.get("uuid"),
                        "code": item.get("code") or item.get("mfl_code") or item.get("facility_code") or item.get("facility_code_number"),
                        "name": item.get("name") or item.get("facility_official_name") or item.get("official_name") or item.get("facility_name"),
                        "county": item.get("county") or item.get("county_name"),
                        "sub_county": item.get("sub_county") or item.get("subcounty") or item.get("sub_county_name"),
                        "facility_type": item.get("facility_type_name") or item.get("facility_type") or item.get("type"),
                        "operation_status": item.get("operation_status_name") or item.get("operation_status") or item.get("status"),
                    }
                    name_text = " ".join(str(value) for value in normalized.values() if value is not None).lower()
                    search_tokens = [token for token in term.lower().split() if len(token) > 1]
                    if search_tokens and not all(token in name_text for token in search_tokens):
                        continue
                    if _sync_kmhfr_page(normalized, db):
                        hydrated += 1
                db.commit()
                return hydrated
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

@router.post("/directory", response_model=FacilityOption, status_code=status.HTTP_201_CREATED)
def add_directory_facility(payload: FacilityQuickCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> FacilityOption:
    """Let a user add a facility straight from the 'Select facility' search
    screen when it isn't already in the directory. No facility context is
    required yet since this runs before the user has picked one."""
    facility = create_directory_facility(db, payload.model_dump(), actor_user_id=user.id)
    return FacilityOption(facility_id=facility.id, facility_name=facility.name, county=facility.county, sub_county=facility.sub_county, facility_type=facility.facility_type, registration_number=facility.registration_number)

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
        raise HTTPException(status_code={"FACILITY_NOT_FOUND": 404, "INVALID_FACILITY_STATUS": 400, "FACILITY_STATUS_UNCHANGED": 400, "FACILITY_STATUS_REASON_REQUIRED": 400}.get(code, 400), detail=code) from exc

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
        return update_facility_status(db, facility_id, payload.status, reason=payload.reason, actor_user_id=user.id)
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