from datetime import date, datetime, time, timezone
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


def get_national_referrals(
    db: Session,
    *,
    actor_user_id: UUID,
    county: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> NationalReferralResponse:
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

    status_rows = db.execute(
        select(Referral.status, func.count(Referral.id)).join(source, source.id == Referral.source_facility_id).join(destination, destination.id == Referral.destination_facility_id).where(*conditions).group_by(Referral.status).order_by(Referral.status.asc())
    ).all()
    priority_rows = db.execute(
        select(Referral.priority, func.count(Referral.id)).join(source, source.id == Referral.source_facility_id).join(destination, destination.id == Referral.destination_facility_id).where(*conditions).group_by(Referral.priority).order_by(Referral.priority.asc())
    ).all()

    rows = db.execute(
        select(Referral, source, destination, department)
        .join(source, source.id == Referral.source_facility_id)
        .join(destination, destination.id == Referral.destination_facility_id)
        .outerjoin(department, department.id == Referral.destination_department_id)
        .where(*conditions)
        .order_by(Referral.created_at.desc(), Referral.id.asc())
        .offset(offset).limit(limit)
    ).all()

    items = [
        NationalReferralItem(
            id=referral.id,
            referral_id=referral.referral_id,
            source_facility_id=source.id,
            source_facility_code=source.facility_id,
            source_facility_name=source.name,
            source_county=source.county,
            destination_facility_id=destination.id,
            destination_facility_code=destination.facility_id,
            destination_facility_name=destination.name,
            destination_county=destination.county,
            destination_department_id=department.id if department and department.facility_id == destination.id else None,
            destination_department_name=department.name if department and department.facility_id == destination.id and department.status == "ACTIVE" else None,
            priority=referral.priority,
            status=referral.status,
            created_at=referral.created_at,
            updated_at=referral.updated_at,
        )
        for referral, source, destination, department in rows
    ]

    record_audit(db, action="VIEW_NATIONAL_REFERRALS", resource_type="NATIONAL_REFERRALS", result="SUCCESS", user_id=actor_user_id, metadata={"county_filter": county_value, "status_filter": status_value, "priority_filter": priority_value, "start_date": start_date.isoformat() if start_date else None, "end_date": end_date.isoformat() if end_date else None, "limit": limit, "offset": offset, "returned": len(items)}, commit=True)
    return NationalReferralResponse(items=items, total=total, limit=limit, offset=offset, status_counts=[NationalReferralStatusCount(status=str(status), count=int(count)) for status, count in status_rows], priority_counts=[NationalReferralPriorityCount(priority=str(priority), count=int(count)) for priority, count in priority_rows])


def get_national_referral_metrics(
    db: Session,
    *,
    actor_user_id: UUID,
    county: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> NationalReferralMetricsResponse:
    county_value = _normalise(county)
    source = aliased(Facility)
    destination = aliased(Facility)
    conditions = _referral_conditions(source, destination, county_value, None, None, start_date, end_date)

    rows = db.execute(
        select(Referral.status, Referral.created_at, source, destination)
        .join(source, source.id == Referral.source_facility_id)
        .join(destination, destination.id == Referral.destination_facility_id)
        .where(*conditions)
    ).all()

    total = len(rows)
    active_statuses = {"CREATED", "SENT", "ACCEPTED", "IN_PROGRESS"}
    completed = sum(1 for status, _, _, _ in rows if status == "COMPLETED")
    declined = sum(1 for status, _, _, _ in rows if status == "DECLINED")
    active = sum(1 for status, _, _, _ in rows if status in active_statuses)
    responded = sum(1 for status, _, _, _ in rows if status in {"ACCEPTED", "DECLINED", "COMPLETED"})
    accepted = sum(1 for status, _, _, _ in rows if status in {"ACCEPTED", "IN_PROGRESS", "COMPLETED"})
    acceptance_rate = round((accepted / responded) * 100, 2) if responded else 0.0
    completion_rate = round((completed / total) * 100, 2) if total else 0.0

    now = datetime.now(timezone.utc)
    buckets = {"<24h": 0, "24–72h": 0, "3–7d": 0, ">7d": 0}
    for status, created_at, _, _ in rows:
        if status not in active_statuses:
            continue
        created = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        hours = max(0.0, (now - created).total_seconds() / 3600)
        if hours < 24:
            buckets["<24h"] += 1
        elif hours < 72:
            buckets["24–72h"] += 1
        elif hours < 168:
            buckets["3–7d"] += 1
        else:
            buckets[">7d"] += 1

    route_map: dict[tuple[UUID, UUID], dict[str, object]] = {}
    for status, _, src, dst in rows:
        key = (src.id, dst.id)
        metric = route_map.setdefault(key, {"source": src, "destination": dst, "total": 0, "active": 0, "completed": 0, "declined": 0})
        metric["total"] = int(metric["total"]) + 1
        if status in active_statuses:
            metric["active"] = int(metric["active"]) + 1
        elif status == "COMPLETED":
            metric["completed"] = int(metric["completed"]) + 1
        elif status == "DECLINED":
            metric["declined"] = int(metric["declined"]) + 1

    routes = []
    for metric in sorted(route_map.values(), key=lambda value: (-int(value["active"]), -int(value["total"]), str(value["source"].facility_id), str(value["destination"].facility_id)))[:MAX_ROUTE_ROWS]:
        src = metric["source"]
        dst = metric["destination"]
        routes.append(NationalReferralRouteMetric(source_facility_id=str(src.id), source_facility_code=src.facility_id, source_facility_name=src.name, destination_facility_id=str(dst.id), destination_facility_code=dst.facility_id, destination_facility_name=dst.name, total=int(metric["total"]), active=int(metric["active"]), completed=int(metric["completed"]), declined=int(metric["declined"])))

    record_audit(db, action="VIEW_NATIONAL_REFERRAL_METRICS", resource_type="NATIONAL_REFERRAL_METRICS", result="SUCCESS", user_id=actor_user_id, metadata={"county_filter": county_value, "start_date": start_date.isoformat() if start_date else None, "end_date": end_date.isoformat() if end_date else None, "total": total, "route_count": len(routes)}, commit=True)
    return NationalReferralMetricsResponse(total=total, active=active, completed=completed, declined=declined, acceptance_rate=acceptance_rate, completion_rate=completion_rate, aging=[NationalReferralAging(bucket=bucket, count=count) for bucket, count in buckets.items()], routes=routes)
