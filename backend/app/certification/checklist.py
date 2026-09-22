"""Structured DHA-style certification evidence catalogue.

Aligned to public DHA certification themes:
- Security, Privacy & Confidentiality
- Information Exchange & Interoperability
- Functionality / clinical safety
- Public-health / operational reporting

This is an evidence map for auditors — not a certificate.
"""

from __future__ import annotations

CERTIFICATION_DOMAINS = [
    {
        "domain": "SECURITY",
        "title": "Security, integrity and access control",
        "controls": [
            {
                "id": "SEC-01",
                "name": "Authentication",
                "status": "IMPLEMENTED",
                "evidence": ["JWT facility + patient auth", "/api/v1/auth", "patient password reset tokens"],
            },
            {
                "id": "SEC-02",
                "name": "Authorisation (RBAC)",
                "status": "IMPLEMENTED",
                "evidence": ["require_permission dependencies", "facility-scoped queries"],
            },
            {
                "id": "SEC-03",
                "name": "Transport security headers",
                "status": "IMPLEMENTED",
                "evidence": [
                    "SecurityHeadersMiddleware",
                    "HSTS in production",
                    "X-Frame-Options DENY",
                    "no-store Cache-Control",
                ],
            },
            {
                "id": "SEC-04",
                "name": "Audit trail",
                "status": "IMPLEMENTED",
                "evidence": ["audit.record_audit", "redacted metadata via security.privacy"],
            },
            {
                "id": "SEC-05",
                "name": "Secrets handling",
                "status": "IMPLEMENTED",
                "evidence": ["env-based tokens", "redact_sensitive on logs/audit"],
            },
        ],
    },
    {
        "domain": "PRIVACY",
        "title": "Privacy & Data Protection Act 2019 alignment",
        "controls": [
            {
                "id": "PRI-01",
                "name": "Purpose limitation on HIE export",
                "status": "IMPLEMENTED",
                "evidence": ["purpose_of_use TREATMENT|PAYMENT|PUBLICHEALTH|OPERATIONS"],
            },
            {
                "id": "PRI-02",
                "name": "Sensitive disease consent",
                "status": "IMPLEMENTED",
                "evidence": ["SensitiveDiseaseConsent", "consent_given + digital signature"],
            },
            {
                "id": "PRI-03",
                "name": "Citizen access to own record",
                "status": "IMPLEMENTED",
                "evidence": ["/api/v1/citizen/timeline", "access-history", "charges"],
            },
            {
                "id": "PRI-04",
                "name": "Identifier hashing",
                "status": "IMPLEMENTED",
                "evidence": ["Person.national_id_hash", "no plain national_id on Person"],
            },
            {
                "id": "PRI-05",
                "name": "Privacy-safe request paths in logs",
                "status": "IMPLEMENTED",
                "evidence": ["privacy_safe_path"],
            },
        ],
    },
    {
        "domain": "INTEROPERABILITY",
        "title": "Information exchange & HIE readiness",
        "controls": [
            {
                "id": "IOP-01",
                "name": "FHIR-shaped patient summary",
                "status": "IMPLEMENTED",
                "evidence": ["GET /api/v1/hie/Patient/{id}/$summary"],
            },
            {
                "id": "IOP-02",
                "name": "Referral package + inbound validation",
                "status": "IMPLEMENTED",
                "evidence": ["/api/v1/hie/referral-package", "/api/v1/hie/inbound"],
            },
            {
                "id": "IOP-03",
                "name": "SHA/DHA AfyaLink connector",
                "status": "IMPLEMENTED_MOCK_AND_LIVE",
                "evidence": ["/api/v1/sha-dha/*", "docs/SHA_DHA_AFYALINK_INTEGRATION.md"],
            },
            {
                "id": "IOP-04",
                "name": "CapabilityStatement",
                "status": "IMPLEMENTED",
                "evidence": ["GET /api/v1/hie/metadata"],
            },
        ],
    },
    {
        "domain": "FUNCTIONALITY",
        "title": "Clinical & hospital operating functions",
        "controls": [
            {
                "id": "FUN-01",
                "name": "Identity confidence + membership",
                "status": "IMPLEMENTED",
                "evidence": ["/api/v1/identity/*"],
            },
            {
                "id": "FUN-02",
                "name": "Clinical safety at prescribe time",
                "status": "IMPLEMENTED",
                "evidence": ["/api/v1/clinical-safety/check"],
            },
            {
                "id": "FUN-03",
                "name": "Lab & imaging intelligence",
                "status": "IMPLEMENTED",
                "evidence": ["lab-intelligence", "imaging-intelligence"],
            },
            {
                "id": "FUN-04",
                "name": "Hospital journey integrity",
                "status": "IMPLEMENTED",
                "evidence": ["/api/v1/hospital-os/integrity"],
            },
            {
                "id": "FUN-05",
                "name": "Claims quality pre-flight",
                "status": "IMPLEMENTED",
                "evidence": ["claims-financing quality", "claim preflight"],
            },
        ],
    },
    {
        "domain": "GOVERNANCE",
        "title": "Attribution, transparency, national readiness",
        "controls": [
            {
                "id": "GOV-01",
                "name": "Developer attribution",
                "status": "IMPLEMENTED",
                "evidence": ["BAHATI GAD WANGWE in footer and meta tags"],
            },
            {
                "id": "GOV-02",
                "name": "National readiness endpoint",
                "status": "IMPLEMENTED",
                "evidence": ["GET /api/v1/national/readiness"],
            },
            {
                "id": "GOV-03",
                "name": "Certification evidence API",
                "status": "IMPLEMENTED",
                "evidence": ["GET /api/v1/certification/evidence"],
            },
        ],
    },
]


def summarise_checklist() -> dict:
    total = 0
    implemented = 0
    for domain in CERTIFICATION_DOMAINS:
        for c in domain["controls"]:
            total += 1
            if str(c["status"]).startswith("IMPLEMENTED"):
                implemented += 1
    return {
        "domains": len(CERTIFICATION_DOMAINS),
        "controls_total": total,
        "controls_implemented": implemented,
        "completion_ratio": round(implemented / total, 3) if total else 0,
        "certificate": None,
        "note": "Evidence map only — DHA issues official certificates after assessment",
        "developer": "BAHATI GAD WANGWE",
    }
