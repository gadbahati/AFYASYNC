"""Template-only safe messaging catalogue.

Patients may only send approved templates with constrained slots.
This reduces free-text leakage of sensitive data and keeps threads auditable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SLOT_PATTERN = re.compile(r"\{([a-z_]+)\}")


@dataclass(frozen=True)
class MessageTemplate:
    code: str
    label: str
    body: str  # may contain {slot} placeholders
    audience: str  # PATIENT | FACILITY | BOTH
    slots: tuple[str, ...] = ()
    max_slot_len: int = 80


# Patient-origin templates only (hard allow-list)
PATIENT_TEMPLATES: dict[str, MessageTemplate] = {
    t.code: t
    for t in (
        MessageTemplate(
            code="APPT_FOLLOW_UP",
            label="Follow up on appointment request",
            body="I am following up on my appointment request. Please advise on the next step.",
            audience="PATIENT",
        ),
        MessageTemplate(
            code="CHANGE_PREFERRED_DATE",
            label="Request a different preferred date",
            body="Please consider a different preferred date: {preferred_date}.",
            audience="PATIENT",
            slots=("preferred_date",),
        ),
        MessageTemplate(
            code="CONFIRM_ATTENDANCE",
            label="Confirm I will attend",
            body="I confirm that I will attend the offered appointment time.",
            audience="PATIENT",
        ),
        MessageTemplate(
            code="NEED_RESCHEDULE",
            label="Need to reschedule",
            body="I need to reschedule my visit. Please share available options.",
            audience="PATIENT",
        ),
        MessageTemplate(
            code="LAB_RESULTS_QUERY",
            label="Ask about lab results",
            body="Please let me know when my laboratory results are ready for review.",
            audience="PATIENT",
        ),
        MessageTemplate(
            code="MEDICATION_QUERY",
            label="Question about medication",
            body="I have a question about a medication prescribed at your facility. Please advise.",
            audience="PATIENT",
        ),
        MessageTemplate(
            code="BRING_DOCUMENTS",
            label="What documents should I bring?",
            body="Please confirm which documents I should bring to my visit.",
            audience="PATIENT",
        ),
        MessageTemplate(
            code="GENERAL_CARE_HELP",
            label="General care coordination help",
            body="I need help coordinating my care with your facility. Please contact me through this channel.",
            audience="PATIENT",
        ),
    )
}

FACILITY_TEMPLATES: dict[str, MessageTemplate] = {
    t.code: t
    for t in (
        MessageTemplate(
            code="FACILITY_ACK",
            label="Acknowledge message",
            body="We received your message and will respond during working hours.",
            audience="FACILITY",
        ),
        MessageTemplate(
            code="FACILITY_APPT_REMINDER",
            label="Appointment reminder",
            body="Reminder: please attend your scheduled visit on {appointment_when}. Bring your ID and Afya card if available.",
            audience="FACILITY",
            slots=("appointment_when",),
        ),
        MessageTemplate(
            code="FACILITY_BRING_ID",
            label="Bring identification",
            body="Please bring a valid national ID or passport and your SHA membership details if any.",
            audience="FACILITY",
        ),
        MessageTemplate(
            code="FACILITY_RESULTS_READY",
            label="Results ready",
            body="Your results are ready. Please visit the facility or open your patient portal for next steps.",
            audience="FACILITY",
        ),
        MessageTemplate(
            code="FACILITY_CALL_RECEPTION",
            label="Contact reception",
            body="Please contact the facility reception during working hours for further assistance.",
            audience="FACILITY",
        ),
        MessageTemplate(
            code="FACILITY_OFFER_SLOT",
            label="Offer appointment slot",
            body="We can offer you an appointment on {appointment_when}. Reply via the portal to confirm or request a change.",
            audience="FACILITY",
            slots=("appointment_when",),
        ),
    )
}


def list_templates_for(sender_type: str) -> list[dict]:
    catalog = PATIENT_TEMPLATES if sender_type == "PATIENT" else FACILITY_TEMPLATES
    return [
        {
            "code": t.code,
            "label": t.label,
            "body": t.body,
            "slots": list(t.slots),
            "max_slot_len": t.max_slot_len,
        }
        for t in catalog.values()
    ]


def render_template(
    *,
    sender_type: str,
    template_code: str,
    slots: dict[str, str] | None,
) -> tuple[str, str]:
    """Return (template_code, rendered_body) or raise ValueError with stable code."""
    catalog = PATIENT_TEMPLATES if sender_type == "PATIENT" else FACILITY_TEMPLATES
    code = (template_code or "").strip().upper()
    tpl = catalog.get(code)
    if tpl is None:
        raise ValueError("UNKNOWN_TEMPLATE")

    values = {k: (v or "").strip() for k, v in (slots or {}).items()}
    for slot in tpl.slots:
        if slot not in values or not values[slot]:
            raise ValueError("SLOT_REQUIRED")
        if len(values[slot]) > tpl.max_slot_len:
            raise ValueError("SLOT_TOO_LONG")
        # Reject control chars / obvious dump attempts
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", values[slot]):
            raise ValueError("SLOT_INVALID")

    # Disallow extra slots
    for k in values:
        if k not in tpl.slots:
            raise ValueError("UNKNOWN_SLOT")

    body = tpl.body
    for slot in tpl.slots:
        body = body.replace("{" + slot + "}", values[slot])

    # Safety: no leftover placeholders
    if SLOT_PATTERN.search(body):
        raise ValueError("TEMPLATE_RENDER_ERROR")

    return code, body
