from app.facilities.service import facility_activation_readiness


def test_activation_readiness_requires_identity_geography_identifier_and_department():
    class Facility:
        id = "facility"
        status = "APPLICATION"
        name = "Test Facility"
        facility_type = "HOSPITAL"
        county = "Kirinyaga"
        sub_county = "Kirinyaga Central"
        registration_number = "MFL-123"
        license_number = None

    class Department:
        status = "ACTIVE"

    class Scalar:
        def __init__(self, value): self.value = value
        def all(self): return self.value

    class DB:
        def get(self, model, ident): return Facility()
        def scalars(self, stmt): return Scalar([Department()])

    result = facility_activation_readiness(DB(), "facility")
    assert result["ready"] is True
    assert all(result["checks"].values())
