"""seed an initial Kenya referral facility directory for the AfyaSync pilot

Revision ID: 0063_seed_kenya_facility_directory
Revises: 0062_restore_runtime_clinical_tables
"""

from alembic import op
import sqlalchemy as sa

revision = "0063_seed_kenya_facility_directory"
down_revision = "0062_restore_runtime_clinical_tables"
branch_labels = None
depends_on = None

# These are an initial operational directory, not a claim that AfyaSync is the
# official KMHFL registry. Official KMHFL identifiers can be added through the
# national facility-management workflow as the integration is established.
FACILITIES = [
    ("AFYA-NAT-KNHTRH", "Kenyatta National Teaching and Referral Hospital", "NATIONAL_REFERRAL", "Nairobi", None),
    ("AFYA-NAT-KUTRRH", "Kenyatta University Teaching, Research and Referral Hospital", "NATIONAL_REFERRAL", "Nairobi", None),
    ("AFYA-NAT-MATHARI", "Mathari National Teaching and Referral Hospital", "NATIONAL_REFERRAL", "Nairobi", None),
    ("AFYA-NAT-MTRH", "Moi Teaching and Referral Hospital", "NATIONAL_REFERRAL", "Uasin Gishu", None),
    ("AFYA-NAT-JOOTRH", "Jaramogi Oginga Odinga Teaching and Referral Hospital", "REFERRAL_HOSPITAL", "Kisumu", None),
    ("AFYA-REF-COAST", "Coast General Teaching and Referral Hospital", "REFERRAL_HOSPITAL", "Mombasa", None),
    ("AFYA-REF-KISII", "Kisii Teaching and Referral Hospital", "REFERRAL_HOSPITAL", "Kisii", None),
    ("AFYA-REF-KAKAMEGA", "Kakamega County General Teaching and Referral Hospital", "REFERRAL_HOSPITAL", "Kakamega", None),
    ("AFYA-REF-KERUGOYA", "Kerugoya Level 5 County Referral Hospital", "REFERRAL_HOSPITAL", "Kirinyaga", None),
    ("AFYA-REF-NYERI", "Nyeri County Referral Hospital", "REFERRAL_HOSPITAL", "Nyeri", None),
    ("AFYA-REF-NAKURU", "Nakuru Level 5 Hospital", "REFERRAL_HOSPITAL", "Nakuru", None),
    ("AFYA-REF-MACHAKOS", "Machakos Level 5 Hospital", "REFERRAL_HOSPITAL", "Machakos", None),
    ("AFYA-REF-MBAGATHI", "Mbagathi County Hospital", "REFERRAL_HOSPITAL", "Nairobi", None),
    ("AFYA-SCH-NAITIRI", "Naitiri Sub County Hospital", "SUB_COUNTY_HOSPITAL", "Bungoma", "Bungoma North"),
    ("AFYA-SCH-KIANYAGA", "Kianyaga Sub-County Hospital", "SUB_COUNTY_HOSPITAL", "Kirinyaga", "Kirinyaga East"),
    ("AFYA-SCH-KIMBIMBI", "Kimbimbi Sub-County Hospital", "SUB_COUNTY_HOSPITAL", "Kirinyaga", "Kirinyaga South"),
    ("AFYA-SCH-SAGANA", "Sagana Sub County Hospital", "SUB_COUNTY_HOSPITAL", "Kirinyaga", "Kirinyaga West"),
    ("AFYA-SCH-RUNYENJES", "Runyenjes Sub County Hospital", "SUB_COUNTY_HOSPITAL", "Embu", "Runyenjes"),
    ("AFYA-SCH-LUNGALUNGA", "Lungalunga Sub County Hospital", "SUB_COUNTY_HOSPITAL", "Kwale", "Lunga Lunga"),
    ("AFYA-SCH-KIPKELION", "Kipkelion Sub County Hospital", "SUB_COUNTY_HOSPITAL", "Kericho", "Kipkelion West"),
    ("AFYA-SCH-TOT", "Tot Sub County Hospital", "SUB_COUNTY_HOSPITAL", "Elgeyo Marakwet", "Marakwet East"),
    ("AFYA-SCH-EMALI", "Emali Sub County Hospital", "SUB_COUNTY_HOSPITAL", "Makueni", "Kibwezi West"),
    ("AFYA-SCH-KIRWARA", "Kirwara Sub County Hospital", "SUB_COUNTY_HOSPITAL", "Murang'a", "Gatanga"),
    ("AFYA-SCH-SUBA", "Suba Sub County Hospital", "SUB_COUNTY_HOSPITAL", "Homa Bay", "Suba South"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for code, name, facility_type, county, sub_county in FACILITIES:
        exists = bind.execute(sa.text("SELECT 1 FROM facilities WHERE facility_id = :code LIMIT 1"), {"code": code}).first()
        if exists:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO facilities (id, facility_id, name, facility_type, county, sub_county, status) "
                "VALUES (gen_random_uuid(), :code, :name, :type, :county, :sub_county, 'ACTIVE')"
            ),
            {"code": code, "name": name, "type": facility_type, "county": county, "sub_county": sub_county},
        )
    bind.commit()


def downgrade() -> None:
    bind = op.get_bind()
    codes = [row[0] for row in FACILITIES]
    bind.execute(sa.text("DELETE FROM facilities WHERE facility_id = ANY(:codes)"), {"codes": codes})
    bind.commit()
