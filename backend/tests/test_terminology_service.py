from app.hie.terminology_service import search_concepts

def test_terminology_model_round_trip(db_session):
    from app.hie.terminology_service import upsert_concept, validate_code, upsert_mapping, map_code
    c=upsert_concept(db_session,data={
        "system":"https://fhir.dha.go.ke/terminology/CodeSystem/test",
        "version":"1.0.0","code":"TEST-001","display":"Test concept",
        "source":"TEST"
    },actor_user_id=None)
    db_session.flush()
    assert validate_code(db_session,c.system,c.code,"1.0.0").id == c.id
    m=upsert_mapping(db_session,data={
        "source_system":"https://local.example/cs","source_code":"L1",
        "target_system":c.system,"target_code":c.code,
        "equivalence":"equivalent","provenance":{"source":"test"}
    },actor_user_id=None)
    db_session.flush()
    assert map_code(db_session,"https://local.example/cs","L1",c.system)[0].id == m.id
    assert search_concepts(db_session,system=c.system,code=c.code)[0].display == "Test concept"
