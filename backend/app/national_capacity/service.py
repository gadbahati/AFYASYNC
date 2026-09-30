from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment, Queue, QueueEntry
from app.audit.service import record_audit
from app.emergency.models import EmergencyVisit
from app.facilities.models import Department, Facility
from app.national_capacity.schemas import NationalCapacityFacility, NationalCapacityResponse
from app.wards.models import Bed, Ward


_ACTIVE_APPOINTMENT_STATUSES = ("SCHEDULED", "CONFIRMED")
_ACTIVE_EMERGENCY_STATUSES = ("WAITING", "TRIAGED", "IN_TREATMENT")


def get_national_capacity(db: Session, *, actor_user_id: UUID, county: str | None = None) -> NationalCapacityResponse:
    county_value = county.strip() if county else None
    if county_value == "":
        county_value = None
    facility_conditions = [Facility.status == "ACTIVE"]
    if county_value:
        facility_conditions.append(Facility.county == county_value)

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=7)
    active_facilities = int(db.scalar(select(func.count(Facility.id)).where(*facility_conditions)) or 0)
    active_departments = int(db.scalar(select(func.count(Department.id)).join(Facility, Facility.id == Department.facility_id).where(*facility_conditions, Department.status == "ACTIVE")) or 0)
    scheduled_appointments = int(db.scalar(select(func.count(Appointment.id)).join(Facility, Facility.id == Appointment.facility_id).where(*facility_conditions, Appointment.appointment_at >= now, Appointment.appointment_at <= horizon, Appointment.status.in_(_ACTIVE_APPOINTMENT_STATUSES))) or 0)
    waiting_queue_entries = int(db.scalar(select(func.count(QueueEntry.id)).join(Queue, Queue.id == QueueEntry.queue_id).join(Facility, Facility.id == Queue.facility_id).where(*facility_conditions, Queue.status == "ACTIVE", QueueEntry.status == "WAITING")) or 0)

    facility_rows = db.execute(select(Facility.id, Facility.facility_id, Facility.name, Facility.county).where(*facility_conditions).order_by(Facility.name.asc(), Facility.id.asc())).all()
    facility_ids = [row[0] for row in facility_rows]

    department_counts = dict(db.execute(select(Department.facility_id, func.count(Department.id)).where(Department.facility_id.in_(facility_ids), Department.status == "ACTIVE").group_by(Department.facility_id)).all()) if facility_ids else {}
    appointment_counts = dict(db.execute(select(Appointment.facility_id, func.count(Appointment.id)).where(Appointment.facility_id.in_(facility_ids), Appointment.appointment_at >= now, Appointment.appointment_at <= horizon, Appointment.status.in_(_ACTIVE_APPOINTMENT_STATUSES)).group_by(Appointment.facility_id)).all()) if facility_ids else {}
    waiting_counts = dict(db.execute(select(Queue.facility_id, func.count(QueueEntry.id)).join(QueueEntry, QueueEntry.queue_id == Queue.id).where(Queue.facility_id.in_(facility_ids), Queue.status == "ACTIVE", QueueEntry.status == "WAITING").group_by(Queue.facility_id)).all()) if facility_ids else {}

    bed_counts: dict[UUID, tuple[int, int, int]] = {}
    if facility_ids:
        bed_rows = db.execute(
            select(
                Ward.facility_id,
                func.count(Bed.id),
                func.sum(case((Bed.status == "AVAILABLE", 1), else_=0)),
                func.sum(case((Bed.status == "OCCUPIED", 1), else_=0)),
            )
            .join(Bed, Bed.ward_id == Ward.id)
            .where(Ward.facility_id.in_(facility_ids), Ward.status == "ACTIVE")
            .group_by(Ward.facility_id)
        ).all()
        bed_counts = {facility_id: (int(total or 0), int(available or 0), int(occupied or 0)) for facility_id, total, available, occupied in bed_rows}

    emergency_counts: dict[UUID, int] = {}
    if facility_ids:
        emergency_rows = db.execute(
            select(EmergencyVisit.facility_id, func.count(EmergencyVisit.id))
            .where(EmergencyVisit.facility_id.in_(facility_ids), EmergencyVisit.status.in_(_ACTIVE_EMERGENCY_STATUSES))
            .group_by(EmergencyVisit.facility_id)
        ).all()
        emergency_counts = dict(emergency_rows)

    total_beds = sum(values[0] for values in bed_counts.values())
    available_beds = sum(values[1] for values in bed_counts.values())
    occupied_beds = sum(values[2] for values in bed_counts.values())
    emergency_waiting = sum(int(value or 0) for value in emergency_counts.values())

    facilities = [
        NationalCapacityFacility(
            facility_id=str(facility_id),
            facility_code=facility_code,
            facility_name=facility_name,
            county=facility_county,
            departments=int(department_counts.get(facility_id, 0)),
            scheduled_appointments=int(appointment_counts.get(facility_id, 0)),
            waiting_queue_entries=int(waiting_counts.get(facility_id, 0)),
            total_beds=bed_counts.get(facility_id, (0, 0, 0))[0],
            available_beds=bed_counts.get(facility_id, (0, 0, 0))[1],
            occupied_beds=bed_counts.get(facility_id, (0, 0, 0))[2],
            emergency_waiting=int(emergency_counts.get(facility_id, 0) or 0),
        )
        for facility_id, facility_code, facility_name, facility_county in facility_rows
    ]
    record_audit(
        db,
        action="VIEW_NATIONAL_CAPACITY",
        resource_type="NATIONAL_CAPACITY",
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={
            "county_filter": county_value,
            "facility_count": len(facilities),
            "appointment_horizon_days": 7,
            "includes_bed_capacity": True,
            "includes_emergency_load": True,
        },
        commit=True,
    )
    return NationalCapacityResponse(
        active_facilities=active_facilities,
        active_departments=active_departments,
        scheduled_appointments=scheduled_appointments,
        waiting_queue_entries=waiting_queue_entries,
        total_beds=total_beds,
        available_beds=available_beds,
        occupied_beds=occupied_beds,
        emergency_waiting=emergency_waiting,
        facilities=facilities,
    )

def search_service_capacity(
    db: Session,
    *,
    actor_user_id: UUID,
    service_code: str | None = None,
    network_code: str | None = None,
    county: str | None = None,
    day: datetime | None = None,
    limit: int = 100,
) -> list[dict]:
    """National service-level capacity view using provider-network services and appointment capacity."""
    from app.provider_network.models import ProviderNetworkMembership, ProviderNetworkService
    from app.appointments.capacity_models import DepartmentCapacity

    target_day = (day or datetime.now(timezone.utc)).date()
    start = datetime(target_day.year, target_day.month, target_day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    conditions = [
        Facility.status == "ACTIVE",
        ProviderNetworkService.status == "ACTIVE",
        ProviderNetworkMembership.participation_status == "ACTIVE",
    ]
    if service_code:
        conditions.append(ProviderNetworkService.service_code == service_code.strip())
    if network_code:
        conditions.append(ProviderNetworkService.network_code == network_code.strip())
    if county:
        conditions.append(Facility.county.ilike(county.strip()))

    stmt = (
        select(
            ProviderNetworkService,
            Facility,
            Department,
            DepartmentCapacity,
        )
        .join(Facility, Facility.id == ProviderNetworkService.facility_id)
        .join(
            ProviderNetworkMembership,
            (ProviderNetworkMembership.facility_id == ProviderNetworkService.facility_id)
            & (ProviderNetworkMembership.network_code == ProviderNetworkService.network_code),
        )
        .outerjoin(
            Department,
            (Department.facility_id == ProviderNetworkService.facility_id)
            & (Department.code == ProviderNetworkService.department_code),
        )
        .outerjoin(
            DepartmentCapacity,
            (DepartmentCapacity.facility_id == ProviderNetworkService.facility_id)
            & (DepartmentCapacity.department_id == Department.id)
            & (DepartmentCapacity.status == "ACTIVE"),
        )
        .where(*conditions)
        .order_by(Facility.name.asc(), ProviderNetworkService.service_name.asc())
        .limit(min(max(limit, 1), 200))
    )
    rows = db.execute(stmt).all()
    result = []
    for service, facility, department, capacity_rule in rows:
        if department is None:
            booked = 0
            maximum = 0
            remaining = 0
            slot_minutes = None
        else:
            maximum = int(capacity_rule.max_appointments_per_day) if capacity_rule else 40
            slot_minutes = int(capacity_rule.slot_minutes) if capacity_rule else 30
            booked = int(
                db.scalar(
                    select(func.count(Appointment.id)).where(
                        Appointment.facility_id == facility.id,
                        Appointment.department_id == department.id,
                        Appointment.appointment_at >= start,
                        Appointment.appointment_at < end,
                        Appointment.status.in_(("SCHEDULED", "CONFIRMED", "CHECKED_IN", "IN_PROGRESS")),
                    )
                )
                or 0
            )
            remaining = max(0, maximum - booked)
        result.append({
            "facility_id": str(facility.id),
            "facility_code": facility.facility_id,
            "facility_name": facility.name,
            "county": facility.county,
            "network_code": service.network_code,
            "service_code": service.service_code,
            "service_name": service.service_name,
            "department": department.name if department else None,
            "department_id": str(department.id) if department else None,
            "date": target_day.isoformat(),
            "booked": booked,
            "daily_capacity": maximum,
            "remaining": remaining,
            "slot_minutes": slot_minutes,
            "referral_required": bool(service.referral_required),
            "tariff_amount": str(service.tariff_amount) if service.tariff_amount is not None else None,
            "currency": service.currency,
            "availability": "AVAILABLE" if remaining > 0 else ("NO_CAPACITY_CONFIGURED" if department is None else "FULL"),
        })
    record_audit(
        db,
        action="SEARCH_NATIONAL_SERVICE_CAPACITY",
        resource_type="NATIONAL_SERVICE_CAPACITY",
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={"service_code": service_code, "network_code": network_code, "county": county, "date": target_day.isoformat(), "result_count": len(result)},
        commit=True,
    )
    return result
