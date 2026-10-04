"""Phase 135 — complete clinical orders when department work finishes.

Developed by BAHATI GAD WANGWE.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.order_models import ClinicalOrder
from app.clinical.order_service import order_to_dict

_LAB_RE = re.compile(r"linked_lab_order=([0-9a-fA-F-]{36})")
_RX_RE = re.compile(r"linked_prescription=([0-9a-fA-F-]{36})")


def _complete_row(
    db: Session,
    row: ClinicalOrder,
    *,
    actor_user_id: UUID | None,
    reason: str,
) -> ClinicalOrder | None:
    if row.status in {"COMPLETED", "CANCELLED"}:
        return None
    note = f"[DEPT_SYNC] {reason}"
    row.status = "COMPLETED"
    row.notes = f"{row.notes}\n{note}".strip() if row.notes else note
    row.updated_at = datetime.now(timezone.utc)
    record_audit(
        db,
        action="CLINICAL_ORDER_DEPT_SYNC",
        resource_type="CLINICAL_ORDER",
        resource_id=str(row.id),
        result="COMPLETED",
        user_id=actor_user_id,
        facility_id=row.facility_id,
        patient_id=row.patient_id,
        metadata={"reason": reason[:200]},
        commit=False,
    )
    return row


def sync_from_lab_order(
    db: Session,
    *,
    lab_order_id: UUID,
    actor_user_id: UUID | None = None,
    reason: str = "Lab results verified",
    commit: bool = True,
) -> list[dict]:
    """Complete clinical orders that were forwarded to this lab order."""
    lid = str(lab_order_id)
    rows = list(
        db.scalars(
            select(ClinicalOrder).where(
                ClinicalOrder.order_type == "LAB",
                ClinicalOrder.status.in_(["ORDERED", "IN_PROGRESS"]),
                ClinicalOrder.notes.isnot(None),
                ClinicalOrder.notes.contains(lid),
            )
        ).all()
    )
    done = []
    for row in rows:
        if lid not in (row.notes or ""):
            continue
        m = _LAB_RE.search(row.notes or "")
        if m and m.group(1).lower() != lid.lower():
            continue
        updated = _complete_row(db, row, actor_user_id=actor_user_id, reason=reason)
        if updated:
            done.append(order_to_dict(updated))
    if done and commit:
        db.commit()
    return done


def sync_from_prescription(
    db: Session,
    *,
    prescription_id: UUID,
    actor_user_id: UUID | None = None,
    reason: str = "Prescription dispensed",
    commit: bool = True,
) -> list[dict]:
    """Complete clinical orders that were forwarded to this prescription."""
    pid = str(prescription_id)
    rows = list(
        db.scalars(
            select(ClinicalOrder).where(
                ClinicalOrder.order_type == "PHARMACY",
                ClinicalOrder.status.in_(["ORDERED", "IN_PROGRESS"]),
                ClinicalOrder.notes.isnot(None),
                ClinicalOrder.notes.contains(pid),
            )
        ).all()
    )
    done = []
    for row in rows:
        m = _RX_RE.search(row.notes or "")
        if m and m.group(1).lower() != pid.lower():
            continue
        if pid not in (row.notes or ""):
            continue
        updated = _complete_row(db, row, actor_user_id=actor_user_id, reason=reason)
        if updated:
            done.append(order_to_dict(updated))
    if done and commit:
        db.commit()
    return done


def sync_clinical_order(
    db: Session,
    *,
    order_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    """Manually re-check department status for one clinical order."""
    row = db.get(ClinicalOrder, order_id)
    if row is None:
        raise ValueError("ORDER_NOT_FOUND")
    if row.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")

    notes = row.notes or ""
    completed: list[dict] = []

    if row.order_type == "LAB":
        m = _LAB_RE.search(notes)
        if m:
            from app.laboratory.models import LabOrder, LabOrderItem, LabResult

            lab_id = UUID(m.group(1))
            lab = db.get(LabOrder, lab_id)
            if lab and lab.status in {"COMPLETED", "RESULTED", "VERIFIED"}:
                completed = sync_from_lab_order(
                    db,
                    lab_order_id=lab_id,
                    actor_user_id=actor_user_id,
                    reason=f"Lab status={lab.status}",
                    commit=True,
                )
            elif lab:
                items = list(db.scalars(select(LabOrderItem).where(LabOrderItem.lab_order_id == lab.id)).all())
                if items:
                    all_done = True
                    for it in items:
                        res = db.scalar(select(LabResult).where(LabResult.lab_order_item_id == it.id))
                        if res is None or getattr(res, "status", None) != "VERIFIED":
                            all_done = False
                            break
                    if all_done:
                        completed = sync_from_lab_order(
                            db,
                            lab_order_id=lab_id,
                            actor_user_id=actor_user_id,
                            reason="All lab results verified",
                            commit=True,
                        )

    elif row.order_type == "PHARMACY":
        m = _RX_RE.search(notes)
        if m:
            from app.pharmacy.models import Prescription

            rx_id = UUID(m.group(1))
            rx = db.get(Prescription, rx_id)
            if rx and rx.status == "DISPENSED":
                completed = sync_from_prescription(
                    db,
                    prescription_id=rx_id,
                    actor_user_id=actor_user_id,
                    reason="Prescription dispensed",
                    commit=True,
                )

    db.refresh(row)
    return {
        "order": order_to_dict(row),
        "synced": completed,
        "developer": "BAHATI GAD WANGWE",
    }
