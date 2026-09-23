"""Static training / SOP catalogue — versioned content for help API."""

SOP_PACKS = [
    {
        "id": "SOP-PATIENT-LOGIN",
        "title": "Patient portal login & Afya ID",
        "audience": ["patient", "front_desk"],
        "steps": [
            "Open AfyaSync and choose Patient",
            "Create account with Afya ID / SHA ID or sign in",
            "Use reset code via phone or email if locked out",
            "Never share password; facility staff never ask for it",
        ],
    },
    {
        "id": "SOP-BOOKING",
        "title": "Appointment booking (patient ↔ facility)",
        "audience": ["patient", "reception"],
        "steps": [
            "Patient selects hospital and department",
            "Facility receives request and replies with date or deny",
            "Both sides use messaging for clarifications",
        ],
    },
    {
        "id": "SOP-SENSITIVE-CONSENT",
        "title": "Sensitive disease disclosure consent",
        "audience": ["clinician", "patient"],
        "steps": [
            "Ask patient if diagnosis may be shared network-wide",
            "Patient signs on screen if agreeing",
            "If declined, record stays local and does not pop on other facilities",
        ],
    },
    {
        "id": "SOP-CLAIMS-PREFLIGHT",
        "title": "Claims preflight before SHA submit",
        "audience": ["claims_officer", "billing"],
        "steps": [
            "Run claim preflight and fix RED/AMBER items",
            "Check fraud-integrity facility-scan for outliers",
            "Submit only GREEN or justified AMBER claims",
        ],
    },
    {
        "id": "SOP-NOTIFIABLE",
        "title": "Notifiable disease reporting",
        "audience": ["clinician", "public_health"],
        "steps": [
            "Report suspected case under Surveillance",
            "Update classification when lab confirms",
            "Close after public-health acknowledgement",
        ],
    },
    {
        "id": "SOP-AMBULANCE",
        "title": "Ambulance request status flow",
        "audience": ["er", "dispatch"],
        "steps": [
            "REQUESTED → DISPATCHED → EN_ROUTE → ARRIVED → COMPLETED",
            "Update status only from authorised staff",
            "Link patient when identity is known",
        ],
    },
    {
        "id": "SOP-ONBOARDING",
        "title": "Facility go-live checklist",
        "audience": ["facility_admin"],
        "steps": [
            "Call onboarding facility-kit until GREEN",
            "Run reliability readiness-matrix",
            "Train staff on SOPs above before cutover",
        ],
    },
]

HELP_TOPICS = [
    {
        "id": "HELP-AFYA-ID",
        "q": "What is an Afya ID?",
        "a": "Your AfyaSync identity used to sign in and link care across facilities, subject to consent rules.",
    },
    {
        "id": "HELP-SHA",
        "q": "Does AfyaSync replace SHA?",
        "a": "AfyaSync is built to interoperate with SHA eligibility and claims while running as a full hospital + citizen platform. Live SHA credentials are configured by operators.",
    },
    {
        "id": "HELP-PRIVACY",
        "q": "Who can see my sensitive diagnoses?",
        "a": "Only after you consent and sign. Without consent, that detail is not shared when another hospital searches your ID.",
    },
    {
        "id": "HELP-SUPPORT",
        "q": "Who developed AfyaSync?",
        "a": "Developed by BAHATI GAD WANGWE. Copyright AfyaSync 2026.",
    },
]

TRAINING_MODULES = [
    {
        "id": "TRN-CITIZEN",
        "title": "Citizen portal basics",
        "duration_minutes": 20,
        "sop_ids": ["SOP-PATIENT-LOGIN", "SOP-BOOKING", "SOP-SENSITIVE-CONSENT"],
    },
    {
        "id": "TRN-CLAIMS",
        "title": "Claims quality & integrity",
        "duration_minutes": 45,
        "sop_ids": ["SOP-CLAIMS-PREFLIGHT"],
    },
    {
        "id": "TRN-EMERGENCY",
        "title": "ER, telemedicine & ambulance",
        "duration_minutes": 30,
        "sop_ids": ["SOP-AMBULANCE"],
    },
    {
        "id": "TRN-ADMIN",
        "title": "Facility administrator go-live",
        "duration_minutes": 60,
        "sop_ids": ["SOP-ONBOARDING", "SOP-NOTIFIABLE"],
    },
]
