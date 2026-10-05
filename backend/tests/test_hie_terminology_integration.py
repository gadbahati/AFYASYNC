from app.hie.terminology_service import canonical_coding, upsert_concept, upsert_mapping

def test_canonical_coding_requires_explicit_mapping(db_session):
    assert canonical_coding(db_session, source_system="AFYASYNC:DIAGNOSIS", source_code="D-UNKNOWN") is None
    target="https://example.invalid/target"
    upsert_concept(db_session,data={"system":target,"code":"T-1","display":"Mapped concept","source":"TEST"},actor_user_id=None)
    upsert_mapping(db_session,data={"source_system":"AFYASYNC:DIAGNOSIS","source_code":"D-1","target_system":target,"target_code":"T-1","target_display":"Mapped concept","provenance":{"test":True}},actor_user_id=None)
    db_session.flush()
    coding=canonical_coding(db_session,source_system="AFYASYNC:DIAGNOSIS",source_code="D-1",display="Local")
    assert coding["system"] == target
    assert coding["code"] == "T-1"
