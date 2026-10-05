from uuid import uuid4
from app.hie.conformance import validate_kenya_core_resource

def test_phase190_triage_observation_has_verified_profile_and_fields():
    resource = {
        'resourceType':'Observation','id':f'triage-{uuid4()}',
        'meta':{'profile':['https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-observation|1.0.0']},
        'status':'final','category':[{'coding':[{'code':'survey'}]}],
        'code':{'coding':[{'system':'http://example.test/triage','code':'URGENT'}]},
        'subject':{'reference':'Patient/example'},
        'effectiveDateTime':'2026-10-05T00:00:00+00:00'
    }
    assert validate_kenya_core_resource(resource) == []

def test_phase190_triage_observation_rejects_unverified_profile():
    resource = {'resourceType':'Observation','id':'triage-example','meta':{'profile':['https://fhir.dha.go.ke/core/StructureDefinition/not-verified']},'status':'final','category':[{'coding':[{'code':'survey'}]}],'code':{'text':'Triage'},'subject':{'reference':'Patient/example'},'effectiveDateTime':'2026-10-05T00:00:00+00:00'}
    assert 'Observation_MISSING_KENYA_CORE_PROFILE' in validate_kenya_core_resource(resource)
