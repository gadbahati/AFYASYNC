# Security Policy

## Scope

AfyaSync handles sensitive healthcare and financing workflows. Security defects are treated as high priority, particularly defects that could expose patient records, credentials, payer data, or cross-facility information.

## Reporting

Do not publish suspected vulnerabilities, credentials, patient information, or exploit details in public issues. Report security concerns privately to the repository owner/maintainer through an authorized private channel.

When reporting, include:

- affected component or endpoint;
- reproducible steps or a minimal proof of concept;
- expected versus actual security boundary;
- potential impact; and
- any logs or identifiers needed to investigate, with sensitive data redacted.

## Response expectations

Maintainers should triage reports, contain active exposure, preserve relevant audit evidence, patch the defect, add a regression test where practical, and document any required credential rotation or data-protection response.

Security testing must use synthetic/non-production data unless an explicitly authorized assessment says otherwise.
