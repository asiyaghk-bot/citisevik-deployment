import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main

def test_dataset_and_seed():
    main.init_db()
    assert len(main.DATA['cells']) == 208
    assert len(main.DATA['roads']) == 3558
    assert len(main.all_rows('projects')) >= 5
    assert len(main.all_rows('cases')) >= 40

def test_spatial_screening():
    projects=main.all_rows('projects'); cases=main.all_rows('cases')
    assert isinstance(main.hotspots(cases,projects),list)
    assert isinstance(main.clashes(projects),list)
    assert 0 <= main.priority(main.DATA['cells'][0],cases) <= 1

def test_response_engine():
    q={'id':'TEST-1','category':'pot','lo':projects_loc()[0],'la':projects_loc()[1],'source':'citizen'}
    plan=main.build_plan(q,main.all_rows('cases')+[q],main.all_rows('projects'))
    assert plan['lead']['dept']=='roads'
    assert plan['immediate'] and plan['permanent'] and plan['verification']
    assert 'must not wait' in plan['caveat']

def projects_loc():
    return main.frac(.62,.70)

def test_intervention_and_budget_api_logic():
    result=main.interventions(0,'balanced')
    assert len(result['options'])==4
    budget=main.budget(main.BudgetIn(budget_lakh=100,horizon_months=12,focus='balanced'))
    assert budget['allocated_lakh'] <= 100

def test_added_coordination_and_validation_features():
    main.init_db()
    projects=main.all_rows('projects')
    assert any(p['type']=='pipeline' for p in projects)
    cmp=main.interventions(0,'balanced')
    assert cmp['separate_works_cost_lakh']==68
    assert cmp['coordinated_cost_lakh']==62
    assert cmp['avoided_rework_lakh']==6
    assert all(o['score_breakdown'] for o in cmp['options'])
    check=main.validation_check()
    assert check['checked']==3 and 0 <= check['matched'] <= 3

def test_workflow_requires_acknowledgement_before_start():
    from fastapi.testclient import TestClient
    main.init_db()
    client=TestClient(main.app)
    case=next(q for q in main.all_rows('cases') if q['status']=='submitted')
    r=client.post(f"/api/cases/{case['id']}/action",headers={'X-Role':'officer','X-Dept':case['lead_dept']},json={'action':'start'})
    assert r.status_code==409
    r=client.post(f"/api/cases/{case['id']}/action",headers={'X-Role':'officer','X-Dept':case['lead_dept']},json={'action':'acknowledge'})
    assert r.status_code==200 and r.json()['status']=='acknowledged'
    r=client.post(f"/api/cases/{case['id']}/action",headers={'X-Role':'officer','X-Dept':case['lead_dept']},json={'action':'start'})
    assert r.status_code==200 and r.json()['status']=='in_progress'

def test_citizen_tracking_requires_private_code_and_hides_staff_data():
    from fastapi.testclient import TestClient
    main.init_db()
    client=TestClient(main.app)
    lo,la=main.frac(.55,.55)
    created=client.post('/api/cases',headers={'X-Role':'citizen'},json={'category':'wl','description':'Waterlogging near road junction','lo':lo,'la':la})
    assert created.status_code==200
    case=created.json()['case']
    assert case.get('tracking_token')
    denied=client.get(f"/api/cases/{case['id']}",headers={'X-Role':'citizen'})
    assert denied.status_code==404
    allowed=client.get(f"/api/cases/{case['id']}?token={case['tracking_token']}",headers={'X-Role':'citizen'})
    assert allowed.status_code==200
    assert 'plan' not in allowed.json()
    assert client.get('/api/projects',headers={'X-Role':'citizen'}).status_code==403
