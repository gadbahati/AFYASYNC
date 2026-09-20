from re import fullmatch
from uuid import uuid4
import logging

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy import text

from app.admissions import models as admission_models
from app.admissions.router import router as admissions_router
from app.appointments import models as appointment_models
from app.appointments import capacity_models as appointment_capacity_models  # noqa: F401
from app.appointments.router import router as appointments_router
from app.audit import models as audit_models
from app.auth import models as auth_models
from app.auth import patient_models as patient_auth_models
from app.auth import router as auth_router
from app.auth.patient_router import router as patient_auth_router
from app.benefits import models as benefit_models
from app.benefits.router import router as benefits_router
from app.billing import models as billing_models
from app.billing.router import router as billing_router
from app.claims import models as claims_models
from app.claims.router import router as claims_router
from app.claims.preflight_router import router as claim_preflight_router
from app.clinical import models as clinical_models
from app.clinical.router import router as clinical_router
from app.config import settings
from app.consent import models as consent_models
from app.consent.router import router as consent_router
from app.coverage import models as coverage_models
from app.coverage.router import router as coverage_router
from app.coverage.sha_eligibility_router import router as sha_eligibility_router
from app.coverage.payer_admin_router import router as payer_network_router
from app.database import Base, SessionLocal, engine
from app.emergency import models as emergency_models
from app.emergency.router import router as emergency_router
from app.encounters import models as encounter_models
from app.encounters.router import router as encounters_router
from app.facilities import models as facility_models
from app.facilities.router import router as facilities_router
from app.facilities.kmhfr_registry import start_sync as start_kmhfr_national_sync, start_sync_retry_loop as start_kmhfr_retry_loop
from app.insight.router import router as insight_router
from app.integrations import models as integration_models
from app.integrations.router import router as integrations_router
from app.interoperability.router import router as interoperability_router
from app.interoperability.allergy_router import router as interoperability_allergy_router
from app.interoperability.patient_router import router as interoperability_patient_router
from app.laboratory import models as laboratory_models
from app.laboratory.router import router as laboratory_router
from app.maternity import models as maternity_models
from app.maternity.router import router as maternity_router
from app.child_health import models as child_health_models
from app.child_health.router import router as child_health_router
from app.blood_bank import models as blood_bank_models
from app.blood_bank.router import router as blood_bank_router
from app.patient_safety import models as patient_safety_models
from app.patient_safety.router import router as patient_safety_router
from app.dietetics import models as dietetics_models
from app.dietetics.router import router as dietetics_router
from app.infection_control import models as infection_control_models
from app.infection_control.router import router as infection_control_router
from app.notifications import models as notification_models
from app.notifications.router import router as notifications_router
from app.nursing import models as nursing_models
from app.nursing.router import router as nursing_router
from app.national_capacity.router import router as national_capacity_router
from app.care_gap.router import router as care_gap_router
from app.national_supply.router import router as national_supply_router
from app.national_supply.planning_router import router as national_supply_planning_router
from app.national_referrals.router import router as national_referrals_router
from app.observability.router import router as observability_router
from app.observability.service import runtime_metrics
from app.security.privacy import privacy_safe_path
from app.operations.router import router as operations_router
from app.patients import models as patient_models
from app.patients.national_identity_router import router as national_identity_router
from app.patients.router import router as patients_router
from app.patients.timeline_router import router as patient_timeline_router
from app.pharmacy import models as pharmacy_models
from app.pharmacy.router import router as pharmacy_router
from app.portal import messaging_models as portal_messaging_models
from app.portal.booking_router import facility_router as facility_booking_router
from app.portal.booking_router import patient_router as portal_booking_router
from app.portal.router import router as portal_router
from app.preauthorizations import models as preauthorization_models
from app.preauthorizations.router import router as preauthorizations_router
from app.rbac import models as rbac_models
from app.referrals import models as referral_models
from app.referrals.router import router as referrals_router
from app.reports.router import router as reports_router
from app.theatre import models as theatre_models
from app.theatre.router import router as theatre_router
from app.radiology import models as radiology_models
from app.radiology.router import router as radiology_router
from app.treat_abroad import models as treat_abroad_models
from app.treat_abroad import return_models as treat_abroad_return_models  # noqa: F401
from app.treat_abroad.router import router as treat_abroad_router
from app.continuity import models as continuity_models  # noqa: F401
from app.continuity.router import facility_router as continuity_facility_router
from app.continuity.router import portal_router as continuity_portal_router
from app.continuity.router import public_router as continuity_public_router
from app.wards import models as ward_models
from app.wards.router import router as wards_router
from app.wards.movement_router import router as ward_movement_router
from app.ussd import models as ussd_models  # noqa: F401
from app.ussd.router import lite_router as ussd_lite_router
from app.ussd.router import router as ussd_router

logger = logging.getLogger("afyasync.request")
app = FastAPI(title=settings.app_name, version=settings.app_version)

_REQUIRED_PROD_TABLES = (
    "patient_password_reset_tokens",
    "sensitive_categories",
    "sensitive_disease_consents",
    "approved_overseas_procedures",
    "overseas_treatment_cases",
    "appointment_requests",
    "department_capacity",
    "facility_messages",
    "continuity_cards",
    "ussd_pins",
    "ussd_sessions",
    "overseas_return_packages",
)
