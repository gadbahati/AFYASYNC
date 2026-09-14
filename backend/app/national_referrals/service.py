from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.audit.service import record_audit
from app.facilities.models import Department, Facility
from app.national_referrals.metrics_schemas import (
    NationalReferralAging,
    NationalReferralMetricsResponse,
    NationalReferralRouteMetric,
)
from app.national_referrals.schemas import (
    NationalReferralItem,
    NationalReferralPriorityCount,
    NationalReferralResponse,
    NationalReferralStatusCount,
)
from app.referrals.models import Referral

MAX_LIMIT = 200
MAX_OFFSET = 10000
MAX_ROUTE_ROWS = 100
ACTIVE_STATUSES = ("CREATED", "SENT", "ACCEPTED", "IN_PROGRESS")


def _normalise(value: str | None) -> str | None:
    value = value.strip() if value else None
    return value or None


def _start_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _end_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


def _referral_conditions(source, destination, county, status, priority, start_date, end_date):
    conditions = [source.status == "ACTIVE", destination.status == "ACTIVE"]
    if county:
        conditions.append((source.county == county) | (destination.county == county))
    if status:
        conditions.append(Referral.status == status)
    if priority:
        conditions.append(Referral.priority == priority)
    if start_date:
        conditions.append(Referral.created_at >= _start_datetime(start_date))
    if end_date:
        conditions.append(Referral.created_at <= _end_datetime(end_date))
    return conditions


def get_national_referrals(db: Session, *, actor_user_id: UUID, county: str | None = None, status: str | None = None, priority: str | None = None, start_date: date | None = None, end_date: date | None = None, limit: int = 100, offset: int = 0) -> NationalReferralResponse:
    limit = min(max(limit, 1), MAX_LIMIT)
    offset = min(max(offset, 0), MAX_OFFSET)
    county_value = _normalise(county)
    status_value = _normalise(status)
    priority_value = _normalise(priority)
    source = aliased(Facility)
    destination = aliased(Facility)
    department = aliased(Department)
    conditions = _referral_conditions(source, destination, county_value, status_value, priority_value, start_date, end_date)
    base = select(Referral.id).join(source, source.id == Referral.source_facility_id).join(destination, destination.id == Referral.destination_facility_id).where(*conditions)
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    status_rows = db.execute(select(Referral.status, func.count(Referral.id)).join(source, source.id == Referral.source_facility_id).join(destination, destination.id == Referral.destination_facility_id).where(*conditions).group_by(Referral.status).order_by(Referral.status.asc())).all()
    priority_rows = db.execute(select(Referral.priority, func.count(Referral.id)).join(source, source.id == Referral.source_facility_id).join(destination, destination.id == Referral.destination_facility_id).where(*conditions).group_by(Referral.priority).order_by(Referral.priority.asc())).all()
    rows = db.execute(select(Referral, source, destination, department).join(source, source.id == Referral.source_facility_id).join(destination, destination.id == Referral.destination_facility_id).outerjoin(department, department.id == Referral.destination_department_id).where(*conditions).order_by(Referral.created_at.desc(), Referral.id.asc()).offset(offset).limit(limit)).all()
    items = [NationalReferralItem(id=referral.id, referral_id=referral.referral_id, source_facility_id=source.id, source_facility_code=source.facility_id, source_facility_name=source.name, source_county=source.county, destination_facility_id=destination.id, destination_facility_code=destination.facility_id, destination_facility_name=destination.name, destination_county=destination.county, destination_department_id=department.id if department and department.facility_id == destination.id else None, destination_department_name=department.name if department and department.facility_id == destination.id and department.status == "ACTIVE" else None, priority=referral.priority, status=referral.status, created_at=referral.created_at, updated_at=referral.updated_at) for referral, source, destination, department in rows]
    record_audit(db, action="VIEW_NATIONAL_REFERRALS", resource_type="NATIONAL_REFERRALS", result="SUCCESS", user_id=actor_user_id, metadata={"county_filter": county_value, "status_filter": status_value, "priority_filter": priority_value, "start_date": start_date.isoformat() if start_date else None, "end_date": end_date.isoformat() if end_date else None, "limit": limit, "offset": offset, "returned": len(items)}, commit=True)
    return NationalReferralResponse(items=items, total=total, limit=limit, offset=offset, status_counts=[NationalReferralStatusCount(status=str(status), count=int(count)) for status, count in status_rows], priority_counts=[NationalReferralPriorityCount(priority=str(priority), count=int(count)) for priority, count in priority_rows])


def get_national_referral_metrics(db: Session, *, actor_user_id: UUID, county: str | None = None, start_date: date | None = None, end_date: date | None = None) -> NationalReferralMetricsResponse:
    county_value = _normalise(county)
    source = aliased(Facility)
    destination = aliased(Facility)
    conditions = _referral_conditions(source, destination, county_value, None, None, start_date, end_date)
    base = select(Referral.id).join(source, source.id == Referral.source_facility_id).join(destination, destination.id == Referral.destination_facility_id).where(*conditions).subquery()
    total = int(db.scalar(select(func.count()).select_from(base)) or 0)

    status_counts = dict(db.execute(select(Referral.status, func.count(Referral.id)).join(source, source.id == Referral.source_facility_id).join(destination, destination.id == Referral.destination_facility_id).where(*conditions).group_by(Referral.status)).all())
    active = sum(int(status_counts.get(status, 0)) for status in ACTIVE_STATUSES)
    completed = int(status_counts.get("COMPLETED", 0))
    declined = int(status_counts.get("DECLINED", 0))
    responded = sum(int(status_counts.get(status, 0)) for status in ("ACCEPTED", "IN_PROGRESS", "COMPLETED", "DECLINED"))
    accepted = sum(int(status_counts.get(status, 0)) for status in ("ACCEPTED", "IN_PROGRESS", "COMPLETED"))
    acceptance_rate = round(accepted * 100 / responded, 2) if responded else 0.0
    completion_rate = round(completed * 100 / total, 2) if total else 0.0

    now = datetime.now(timezone.utc)
    age_base = _referral_conditions(source, destination, county_value, None, None, start_date, end_date)
    def age_count(lower: datetime | None, upper: datetime | None = None) -> int:
        age_conditions = [*age_base, Referral.status.in_(ACTIVE_STATUSES)]
        if lower is not None:
            age_conditions.append(Referral.created_at >= lower)
        if upper is not None:
            age_conditions.append(Referral.created_at < upper)
        return int(db.scalar(select(func.count(Referral.id)).join(source, source.id == Referral.source_facility_id).join(destination, destination.id == Referral.destination_facility_id).where(*age_conditions)) or 0)

    buckets = [
        ("<24h", age_count(now - timedelta(hours=24), None)),
        ("24–72h", age_count(now - timedelta(hours=72), now - timedelta(hours=24))),
        ("3–7d", age_count(now - timedelta(days=7), now - timedelta(hours=72))),
        (">7d", age_count(None, now - timedelta(days=7))),
    ]

    route_rows = db.execute(
        select(source.id, source.facility_id, source.name, destination.id, destination.facility_id, destination.name, Referral.status, func.count(Referral.id))
        .join(source, source.id == Referral.source_facility_id).join(destination, destination.id == Referral.destination_facility_id)
        .where(*conditions).group_by(source.id, source.facility_id, source.name, destination.id, destination.facility_id, destination.name, Referral.status)
    ).all()
    route_map: dict[tuple[UUID, UUID], dict[str, object]] = {}
    for src_id, src_code, src_name, dst_id, dst_code, dst_name, status, count in route_rows:
        key = (src_id, dst_id)
        metric = route_map.setdefault(key, {"source": (src_id, src_code, src_name), "destination": (dst_id, dst_code, dst_name), "total": 0, "active": 0, "completed": 0, "declined": 0})
        count = int(count)
        metric["total"] = int(metric["total"]) + count
        if status in ACTIVE_STATUSES: metric["active"] = int(metric["active"]) + count
        elif status == "COMPLETED": metric["completed"] = int(metric["completed"]) + count
        elif status == "DECLINED": metric["declined"] = int(metric["declined"]) + count
    routes = []
    for metric in sorted(route_map.values(), key=lambda value: (-int(value["active"]), -int(value["total"]), str(value["source"][1]), str(value["destination"][1])))[:MAX_ROUTE_ROWS]:
        src_id, src_code, src_name = metric["source"]
        dst_id, dst_code, dst_name = metric["destination"]
        routes.append(NationalReferralRouteMetric(source_facility_id=str(src_id), source_facility_code=src_code, source_facility_name=src_name, destination_facility_id=str(dst_id), destination_facility_code=dst_code, destination_facility_name=dst_name, total=int(metric["total"]), active=int(metric["active"]), completed=int(metric["completed"]), declined=int(metric["declined"])))

    record_audit(db, action="VIEW_NATIONAL_REFERRAL_METRICS", resource_type="NATIONAL_REFERRAL_METRICS", result="SUCCESS", user_id=actor_user_id, metadata={"county_filter": county_value, "start_date": start_date.isoformat() if start_date else None, "end_date": end_date.isoformat() if end_date else None, "total": total, "route_count": len(routes)}, commit=True)
    return NationalReferralMetricsResponse(total=total, active=active, completed=completed, declined=declined, acceptance_rate=acceptance_rate, completion_rate=completion_rate, aging=[NationalReferralAging(bucket=bucket, count=count) for bucket, count in buckets], routes=routes)
