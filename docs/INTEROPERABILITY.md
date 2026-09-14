# Interoperability boundary

AfyaSync exposes a deliberately narrow interoperability surface. External consumers receive only the minimum data required for the authorised operation, and national clinical access requires an explicit access reason.

## FHIR R4

- `GET /api/v1/interoperability/metadata` advertises the JSON/R4 capability surface.
- `GET /api/v1/interoperability/Patient/{patient_id}` returns a minimal Patient resource for a patient actively enrolled at the selected facility.
- `GET /api/v1/interoperability/Patient/{patient_id}/$summary?access_reason=...` returns a minimal clinical Bundle containing the patient and recent encounters from the selected facility.
- All interoperability reads are audited.
- FHIR endpoints are not a blanket cross-facility data export. RBAC and facility isolation remain mandatory.

## DHIS2 aggregate export

`GET /api/v1/interoperability/dhis2/data-value-set?period=YYYYMM` produces a DHIS2-compatible aggregate `dataValueSet` payload. It contains no patient-level data.

Production data-element and dataset identifiers must be supplied through deployment configuration:

- `DHIS2_DATASET_ID`
- `DHIS2_DATA_ELEMENT_ENCOUNTERS`
- `DHIS2_DATA_ELEMENT_REGISTERED_PATIENTS`
- `DHIS2_DATA_ELEMENT_INVOICES`
- `DHIS2_DATA_ELEMENT_PAYMENTS`
- `DHIS2_DATA_ELEMENT_CLAIMS`

Facility codes are used as DHIS2 orgUnit identifiers. These mappings must be validated against the authorised DHIS2 instance before a production submission workflow is enabled.

AfyaSync does not claim statutory interoperability certification merely because these payload shapes are implemented. Formal exchange specifications, credentials, approvals, endpoint allowlists, data-element mappings, and acceptance testing remain deployment/governance requirements.
