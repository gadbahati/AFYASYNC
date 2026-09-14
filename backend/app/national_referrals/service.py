from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.audit.service import record_audit
from app.facilities.models import Department, Facility
from app.national_referrals.schemas import (
    NationalReferralItem,
    NationalReferralPriorityCount,
    NationalReferralResponse,
    NationalReferralStatusCount,
)
from app.referrals.models import Referral

MAX_LIMIT = 200
MAX_OFFSET = 10000


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

    conditions = [
        source.status == "ACTIVE",
        destination.status == "ACTIVE",
    ]
    if county_value:
        conditions.append((source.county == county_value) | (destination.county == county_value))
    if status_value:
        conditions.append(Referral.status == status_value)
    if priority_value:
        conditions.append(Referral.priority == priority_value)
    if start_date:
        conditions.append(Referral.created_at >= _start_datetime(start_date))
    if end_date:
        conditions.append(Referral.created_at <= _end_datetime(end_date))

    base = (
        select(Referral.id)
        .join(source, source.id == Referral.source_facility_id)
        .join(destination, destination.id == Referral.destination_facility_id)
        .where(*conditions)
    )
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)

    status_rows = db.execute(
        select(Referral.status, func.count(Referral.id))
        .join(source, source.id == Referral.source_facility_id)
        .join(destination, destination.id == Referral.destination_facility_id)
        .where(*conditions)
        .group_by(Referral.status)
        .order_by(Referral.status.asc())
    ).all()
    priority_rows = db.execute(
        select(Referral.priority, func.count(Referral.id))
        .join(source, source.id == Referral.source_facility_id)
        .join(destination, destination.id == Referral.destination_facility_id)
        .where(*conditions)
        .group_by(Referral.priority)
        .order_by(Referral.priority.asc())
    ).all()

    rows = db.execute(
        select(Referral, source, destination, department)
        .join(source, source.id == Referral.source_facility_id)
        .join(destination, destination.id == Referral.destination_facility_id)
        .outerjoin(department, department.id == Referral.destination_department_id)
        .where(*conditions)
        .order_by(Referral.created_at.desc(), Referral.id.asc())
        .offset(offset)
        .limit(limit)
    ).all()

    items = [
        NationalReferralItem(
            id=referral.id,
            referral_id=referral.referral_id,
            source_facility_id=source_facility.id,
            source_facility_code=source.facility_id,
            source_facility_name=source.name,
            source_county=source.county,
            destination_facility_id=destination.facility.id,
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

    record_audit(
        db,
        action="VIEW_NATIONAL_REFERRALS",
        resource_type="NATIONAL_REFERRALS",
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={
            "county_filter": county_value,
            "status_filter": status_value,
            "priority_filter": priority_value,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "limit": limit,
            "offset": offset,
            "returned": len(items),
        },
        commit=True,
    )
    return NationalReferralResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        status_counts=[NationalReferralStatusCount(status=str(status), count=int(count)) for status, count in status_rows],
        priority_counts=[NationalReferralPriorityCount(priority=str(priority), count=int(count)) for priority, count in priority_rows],
    )
