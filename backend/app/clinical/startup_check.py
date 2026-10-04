"""Phase 138 — optional clinical integrity check at import time.

Developed by BAHATI GAD WANGWE.
"""
import logging

logger = logging.getLogger("afyasync.clinical")


def run_clinical_startup_checks() -> None:
    try:
        from app.clinical.path_hardening import assert_department_services_loaded

        report = assert_department_services_loaded()
        logger.info("clinical_department_services_ok %s", report)
    except Exception as exc:
        # Log loudly but do not crash the whole app — operators can fix empty modules
        logger.error("CLINICAL_DEPARTMENT_SERVICE_CHECK_FAILED: %s", exc)
