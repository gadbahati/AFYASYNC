# Phase 19 — Appointment fairness & capacity (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Implemented + hardened

---

## Problem

Walk-in and portal bookings can overfill a department, double-book a patient, or let later requests jump the queue.

## Solution

| Control | Behaviour |
|---------|-----------|
| `department_capacity` | Max/day, slot minutes, open/close hours, max pending |
| Slot check | Past times blocked; outside hours blocked; day full; near-slot clash |
| Patient double-book | Same patient + dept + day blocked |
| Pending queue | Department/facility pending caps |
| Fair list | FIFO pending + high-usage advisory (does not auto-block) |

## APIs

| Method | Path |
|--------|------|
| `GET` | `/api/v1/appointments/capacity/slots?department_id=&day=YYYY-MM-DD` |
| `GET` | `/api/v1/appointments/capacity/pending-fair` |
| `PUT` | `/api/v1/appointments/capacity/department/{id}` |

Enforced on staff `create_appointment` and portal accept/reschedule.

Migration: `0077_department_capacity`.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
