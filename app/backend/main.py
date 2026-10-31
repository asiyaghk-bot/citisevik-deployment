from __future__ import annotations
import json, math, os, sqlite3, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'frontend/public/citisevik_data.json').read_text())
W,S,E,N=DATA['bbox']; K=math.cos((S+N)/2*math.pi/180); M=111320
DB=Path(__file__).with_name('citisevik.sqlite3')
DEPTS={
'roads':dict(id='roads',name='Roads / Ward Engineering',short='ROADS',color='#2563eb',lead_for=['pot'],sla_ack_hours=24,sla_resolve_days=7,handoff_to=['swd','wss','traffic','planning']),
'swd':dict(id='swd',name='Storm Water Drains',short='SWD',color='#0d9488',lead_for=['wl','drn'],sla_ack_hours=12,sla_resolve_days=5,handoff_to=['roads','wss','env','planning']),
'wss':dict(id='wss',name='Water Supply / Sewerage',short='WSS',color='#0284c7',lead_for=[],sla_ack_hours=24,sla_resolve_days=7,handoff_to=['roads','swd']),
'traffic':dict(id='traffic',name='Traffic Police / Traffic Engineering',short='TRAFFIC',color='#d97706',lead_for=[],sla_ack_hours=8,sla_resolve_days=3,handoff_to=['roads','planning']),
'env':dict(id='env',name='Environment / Solid Waste',short='ENV',color='#65a30d',lead_for=['dust'],sla_ack_hours=24,sla_resolve_days=7,handoff_to=['roads','swd','planning']),
'planning':dict(id='planning',name='Planning / Project Coordination',short='PLAN',color='#7c3aed',lead_for=[],sla_ack_hours=48,sla_resolve_days=14,handoff_to=['roads','swd','wss','traffic','env'])}
TYPE={'demolish':('DM','Demolish and rebuild'),'road':('RD','Road repair'),'bridge':('BR','Bridge'),'park':('PK','Park'),'drain':('DR','Drainage upgrade'),'pipeline':('WP','Water pipeline replacement'),'telecom':('TC','Telecom duct / cable work')}
CAT={'pot':'Pothole / damaged road','wl':'Waterlogging','drn':'Blocked drain','dust':'Construction dust'}

def now(): return datetime.now(timezone.utc)
def iso(d): return d.isoformat()
def dist(a,b,c,d): return math.hypot((a-c)*K*M,(b-d)*M)
def frac(x,y): return W+(E-W)*x,S+(N-S)*y
def ym(s):
 try: y,m=map(int,s.split('-')[:2]); return y*12+m
 except: return None
def point_seg_dist_m(lon,lat,a,b):
    # Local equirectangular point-to-segment distance in metres.
    x=(lon-a[0])*K*M; y=(lat-a[1])*M
    bx=(b[0]-a[0])*K*M; by=(b[1]-a[1])*M
    den=bx*bx+by*by
    t=0 if den==0 else max(0,min(1,(x*bx+y*by)/den))
    return math.hypot(x-t*bx,y-t*by)
def nearest_water_m(lon,lat):
    best=float('inf'); found=False
    for line in DATA.get('water_lines',[]):
        if len(line)<2: continue
        found=True
        for a,b in zip(line,line[1:]): best=min(best,point_seg_dist_m(lon,lat,a,b))
    for poly in DATA.get('water_polys',[]):
        if len(poly)<2: continue
        found=True
        # Point-in-polygon; distance to polygon boundary otherwise.
        inside=False
        for a,b in zip(poly,poly[1:]+poly[:1]):
            if ((a[1]>lat)!=(b[1]>lat)) and lon < (b[0]-a[0])*(lat-a[1])/(b[1]-a[1]+1e-15)+a[0]: inside=not inside
            best=min(best,point_seg_dist_m(lon,lat,a,b))
        if inside: best=0
    return round(best) if found and math.isfinite(best) else None
for _cell in DATA['cells']:
    _cell['cx']=(_cell['b'][0]+_cell['b'][2])/2
    _cell['cy']=(_cell['b'][1]+_cell['b'][3])/2
    _cell['water_distance_m']=nearest_water_m(_cell['cx'],_cell['cy'])

def cell_at(lo,la):
 return min(DATA['cells'],key=lambda c:dist(lo,la,(c['b'][0]+c['b'][2])/2,(c['b'][1]+c['b'][3])/2))
# Derive modelled indices, clearly labelled as screening proxies.
_ev=[c['elev'] for c in DATA['cells'] if c['elev'] is not None]; emin=min(_ev); emax=max(_ev); mb=max(1,max(c['bn'] for c in DATA['cells'])); mm=max(1,max(c['ml'] for c in DATA['cells']))
for c in DATA['cells']:
 c['cx']=(c['b'][0]+c['b'][2])/2;c['cy']=(c['b'][1]+c['b'][3])/2
 low=.5 if c['elev'] is None else 1-(c['elev']-emin)/((emax-emin) or 1); bu=min(1,c['ba']/.5)
 water=c.get('water_distance_m')
 water_term=(1-min(1,water/1000)) if water is not None else 0
 c['fl']=.38*low+.22*max(0,1-c['wd']/600)+.25*bu+.15*water_term if any(x['wd']<9999 for x in DATA['cells']) else .55*low+.30*bu+.15*water_term
 c['pp']=min(1,c['bn']/mb);c['air']=.5*min(1,c['ml']/mm)+.3*min(1,c['inf']/.5)+.2*bu

def connect():
 con=sqlite3.connect(DB);con.row_factory=sqlite3.Row;return con
def init_db():
 with connect() as c:
  c.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
  if c.execute('SELECT count(*) FROM projects').fetchone()[0]==0:
   specs=[('demolish',.30,.45,250,'2026-06','2027-03',40,'planning'),('road',.62,.70,200,'2026-09','2026-12',70,'roads'),('bridge',.70,.30,300,'2026-10','2028-08',25,'roads'),('park',.42,.20,220,'2026-10','2027-06',10,'env'),('drain',.64,.66,200,'2027-02','2027-08',0,'swd'),('pipeline',.61,.67,180,'2027-03','2027-06',0,'wss')]
   for typ,x,y,r,st,en,prog,dept in specs:
    lo,la=frac(x,y);code=TYPE[typ][0];pid=f'CS-{code}-{st[:4]}-001' if typ!='drain' else 'CS-DR-2027-001'
    p=dict(id=pid,type=typ,name=TYPE[typ][1],lead_dept=dept,partner_depts=[],lo=lo,la=la,radius_m=r,start=st,end=en,progress=prog,status='active' if prog>0 else 'planned',schedule_slippage_days=(12 if typ=='road' else 0),depends_on=(['CS-RD-2026-001'] if typ=='drain' else []),sample=True,budget_lakh=None,provenance=prov('illustrative','Seeded demonstration project','low'))
    c.execute('INSERT OR IGNORE INTO projects VALUES (?,?)',(pid,json.dumps(p)))
  if c.execute('SELECT count(*) FROM cases').fetchone()[0]==0: seed_cases(c)
  # Seed one auditable, explicitly illustrative coordination path for the road/drainage conflict.
  if c.execute('SELECT count(*) FROM audit').fetchone()[0]==0:
   seed_projects=[json.loads(r['data']) for r in c.execute('SELECT data FROM projects')]
   seed_clashes=clashes(seed_projects)
   repeat_conflict=next((z for z in seed_clashes if z.get('kind')=='repeat_excavation'),None)
   if repeat_conflict:
    t=now()
    for days,hour,minute,action,actor,detail in [(2,10,15,'verify_clash','Roads / Ward Engineering','Illustrative department verification: road/drainage sequencing conflict reviewed.'),(1,14,40,'coordinate_clash','Storm Water Drains','Illustrative department coordination: drainage to precede final road resurfacing.')]:
     event_time=(t-timedelta(days=days)).replace(hour=hour,minute=minute,second=0,microsecond=0)
     item=dict(id=str(uuid.uuid4()),at=iso(event_time),role=actor,action=action,entity='clash',entity_id=repeat_conflict['key'],detail=detail)
     c.execute('INSERT INTO audit VALUES (?,?)',(item['id'],json.dumps(item)))
def prov(cl,source,confidence='low'):return dict(classification=cl,source=source,timestamp=iso(now()),confidence=confidence)
def all_rows(table):
 with connect() as c:return [json.loads(r['data']) for r in c.execute(f'SELECT data FROM {table}')]
def save(table,obj):
 with connect() as c:c.execute(f'INSERT OR REPLACE INTO {table} VALUES (?,?)',(obj['id'],json.dumps(obj)))
def add_audit(role,action,entity,eid,detail=''):
 a=dict(id=str(uuid.uuid4()),at=iso(now()),role=role,action=action,entity=entity,entity_id=eid,detail=detail)
 with connect() as c:c.execute('INSERT INTO audit VALUES (?,?)',(a['id'],json.dumps(a)))
def priority(cell,cases):
 reports=sum(dist(q['lo'],q['la'],cell['cx'],cell['cy'])<=250 for q in cases)
 water=cell.get('water_distance_m')
 water_score=(1-min(1,water/1000)) if water is not None else 0
 return max(0,min(1,.30*cell['fl']+.20*cell['pp']+.16*cell['air']+.14*min(1,reports/8)+.08*min(1,cell['ml']/1500)+.12*water_score))
def priority_breakdown(cell,cases):
 reports=sum(dist(q['lo'],q['la'],cell['cx'],cell['cy'])<=250 for q in cases)
 parts={'Flood exposure':.34*cell['fl'],'Building density proxy':.22*cell['pp'],'Air-pressure proxy':.18*cell['air'],'Nearby reports':.16*min(1,reports/8),'Road-network proxy':.08*min(1,cell['ml']/1500),'Proximity to mapped water':.12*(1-min(1,cell['water_distance_m']/1000)) if cell.get('water_distance_m') is not None else 0}
 return {k:round(v*100,1) for k,v in parts.items()}

def seed_cases(con):
 seed=7
 def rnd():
  nonlocal seed;seed=(seed*16807)%2147483647;return seed/2147483647
 specs=[('pot',.62,.70,14,140),('wl',.60,.60,12,160),('dust',.30,.45,6,120)]
 cases=[]
 for cat,x,y,n,spread in specs:
  cx,cy=frac(x,y)
  for _ in range(n):
   # deterministic compact spatial spread, using metres converted to degrees
   angle=rnd()*math.tau;rad=math.sqrt(rnd())*spread
   lo=cx+math.cos(angle)*rad/(M*K);la=cy+math.sin(angle)*rad/M
   cases.append((cat,lo,la))
 for i in range(8):
  cat=['pot','wl','drn','dust'][i%4]
  x,y=.1+rnd()*.8,.1+rnd()*.8
  cx,cy=frac(x,y)
  angle=rnd()*6.28;rad=math.sqrt(rnd())*0
  lo=cx+math.cos(angle)*rad/(M*K);la=cy+math.sin(angle)*rad/M
  cases.append((cat,lo,la))
 for i,(cat,lo,la) in enumerate(cases,1):
  # Deliberate illustrative mix so the demo page shows a working service workflow.
  bucket=i%20
  status=('submitted' if bucket in (0,1,2) else 'acknowledged' if bucket in (3,4,5,6) else 'in_progress' if bucket in (7,8,9) else 'resolved' if bucket in (10,11,12,13,14,15) else 'verified')
  age_days=(1+i%7) if status in ('submitted','acknowledged','in_progress') else (10+(i*7)%55)
  created=now()-timedelta(days=age_days)
  lead=next(k for k,v in DEPTS.items() if cat in v['lead_for'])
  partners=[]
  if cat=='pot':partners=[dict(dept='traffic',reason='Traffic safety and work-zone management',acknowledged=(i%4!=0),acknowledged_at=None)]
  if cat in ('wl','drn'):partners=[dict(dept='roads',reason='Road levels and reinstatement',acknowledged=(i%5!=0),acknowledged_at=None)]
  if i==22 and status in ('submitted','acknowledged','in_progress'):
   partners.append(dict(dept='wss',reason='Check water-main leakage / sewer overflow',acknowledged=False,acknowledged_at=None))
  # A few open cases deliberately wait on a partner department.
  if status in ('submitted','acknowledged','in_progress') and partners and i%5==0:partners[0]['acknowledged']=False
  ack_hours=min([3,8,17,31,54,72][i%6],max(1,age_days*24-1))
  ack_at=iso(created+timedelta(hours=ack_hours)) if status!='submitted' else None
  resolved=iso(created+timedelta(days=1+(i%5))) if status in ('resolved','verified') else None
  cid=f'GRV-2026-{i:04d}'
  repeat=i in (14,27,41,58,73,96)
  case=dict(id=cid,category=cat,description=f'{CAT[cat]} reported in sample demonstration data',lo=lo,la=la,source='illustrative',created_at=iso(created),status=status,urgency='high' if i%4==0 else 'routine',lead_dept=lead,partners=partners,lead_ack_at=ack_at,resolved_at=resolved,verified_at=resolved if status=='verified' else None,history=[],repeat_after_fix=repeat,repeat_count=(2 if repeat and i%2==0 else 1 if repeat else 0),provenance=prov('illustrative','Seeded synthetic complaint and workflow timestamps','low'))
  con.execute('INSERT OR IGNORE INTO cases VALUES (?,?)',(cid,json.dumps(case)))

def hotspots(cases,projects):
 groups=[]
 for q in cases:
  g=next((g for g in groups if g['category']==q['category'] and dist(q['lo'],q['la'],g['lo'],g['la'])<150),None)
  if g:g['count']+=1;g['lo']+=(q['lo']-g['lo'])/g['count'];g['la']+=(q['la']-g['la'])/g['count'];g['case_ids'].append(q['id'])
  else:groups.append(dict(category=q['category'],lo=q['lo'],la=q['la'],count=1,case_ids=[q['id']]))
 out=[]
 for i,g in enumerate([g for g in groups if g['count']>=5],1):
  near=min(projects,key=lambda p:dist(g['lo'],g['la'],p['lo'],p['la']),default=None)
  g.update(id=f'HS-{i:02d}',nearest_project_id=near['id'] if near and dist(g['lo'],g['la'],near['lo'],near['la'])<=near['radius_m']+200 else None);out.append(g)
 return out
def clashes(projects):
 out=[]
 for i,a in enumerate(projects):
  for b in projects[i+1:]:
   if a['status']=='completed' or b['status']=='completed' or dist(a['lo'],a['la'],b['lo'],b['la'])>a['radius_m']+b['radius_m']:continue
   sa,ea,sb,eb=map(ym,[a['start'],a['end'],b['start'],b['end']]);road=next((p for p in (a,b) if p['type']=='road'),None);under=next((p for p in (a,b) if p['type']=='drain'),None);msg=None;kind='overlap'
   if road and under:
    re=ym(road['end']);us=ym(under['start'])
    if us>=re-1 and us-re<=6:msg=f"Road work {road['id']} may be dug up by drainage work {under['id']}; coordinate the sequence.";kind='repeat_excavation'
   if not msg and sa<=eb and sb<=ea and a['type'] not in ('park',) and b['type'] not in ('park',):
    msg='Potential disruptive work overlap: coordinate traffic management and work windows.'
   if msg:
    pair={a['type'],b['type']}
    conflict_type='coordination opportunity' if pair=={'drain','pipeline'} else ('direct conflict' if kind=='repeat_excavation' else 'potential conflict')
    out.append(dict(key='|'.join(sorted([a['id'],b['id']])),a=a['id'],b=b['id'],kind=kind,type=conflict_type,message=msg,lo=(a['lo']+b['lo'])/2,la=(a['la']+b['la'])/2,status='flagged'))
 return out

def build_plan(q,cases,projects):
 cat=q['category'];cell=cell_at(q['lo'],q['la']);near=[c for c in cases if c['id']!=q['id'] and dist(q['lo'],q['la'],c['lo'],c['la'])<=250];same=[c for c in near if c['category']==cat];near_p=[p for p in projects if dist(q['lo'],q['la'],p['lo'],p['la'])<=p['radius_m']+250 and p['status']!='completed']
 lead={'pot':'roads','wl':'swd','drn':'swd','dust':'env'}[cat];partners=[]
 def add(d,reason):
  if d!=lead and d not in [x['dept'] for x in partners]:partners.append(dict(dept=d,reason=reason,acknowledged=False))
 if cat=='pot':
  add('traffic','Traffic safety, signage and lane management')
  if cell['fl']>.55 or any(c['category'] in ('wl','drn') for c in near):add('swd','Check whether drainage is contributing to road failure')
  if any(p['type']=='drain' for p in near_p):add('wss','Check underground utility schedules and interfaces')
 elif cat in ('wl','drn'):
  add('roads','Road levels, inlet reinstatement and resurfacing coordination');add('wss','Rule out sewer overflow or water-main leakage')
  if cat=='drn':add('env','Solid waste source control')
 elif cat=='dust':add('roads','Road debris and haul-route condition');add('traffic','Haul-truck routing and timing')
 if near_p:add('planning','Reconcile nearby project schedules and dependencies')
 urgent=(cat=='wl' and (cell['fl']>.55 or len(same)>=3)) or len(same)>=4 or (cat=='drn' and cell['fl']>.55)
 underground=next((p for p in near_p if p['type']=='drain'),None)
 if cat=='pot' and underground:exc=dict(status='hold_permanent',message=f"Make safe now with temporary protection/patch. Coordinate permanent resurfacing after {underground['id']} drainage work; do not leave a hazardous defect untreated.")
 elif cat=='pot' and cell['fl']>.55:exc=dict(status='coordinate',message='Make safe now. Ask Storm Water Drains to inspect the waterlogging cause before specifying permanent resurfacing.')
 else:exc=dict(status='proceed',message='No relevant scheduled drainage project found in the current demo registry; verify utility records before permanent works.')
 immediate={'pot':['Inspect defect size, depth and traffic exposure.','If unsafe, barricade/sign and arrange an authorised temporary safe patch.'],'wl':['Protect pedestrians and traffic; inspect water depth, access and active flooding.','Clear safe, accessible blockages only through authorised crews.'],'drn':['Inspect blockage type and check for sewage or hazardous overflow.','Arrange safe clearing with pedestrian and traffic protection.'],'dust':['Inspect site controls, uncovered material and debris.','Require appropriate covering, suppression and wheel-cleaning controls.']}[cat]
 permanent={'pot':['Confirm road owner and defect-liability status.','Inspect drainage and underground utility schedules before permanent resurfacing.','Verify material and compaction after repair.'],'wl':['Inspect inlets, outfalls, levels, catchment and blockages.','Assess capacity and feasible surface storage only after engineering survey.'],'drn':['Check drain condition, capacity, outfall and repeat blockage.','Address upstream waste entry and repair damaged sections.'],'dust':['Review site method, haul route and boundary controls.','Record contractor compliance and monitor readings where available.']}[cat]
 verification={'pot':['Geo-tag before/after photos and engineer sign-off.','Check repeat reports within 150 m over 90 days.'],'wl':['Record water depth/duration and clearance time.','Check recurrence after comparable rainfall.'],'drn':['Photograph inlet/outlet flow.','Recheck after rainfall and log repeat blockage.'],'dust':['Log compliance inspection and photos.','Use local air-monitor readings where available.']}[cat]
 return dict(score=round(priority(cell,cases)*100),urgency='high' if urgent else 'routine',urgency_reason=f'{len(same)} similar reports within 250 m; flood screening index {round(cell["fl"]*100)}/100.',what_we_know=[dict(text=f'{CAT[cat]} at {q["lo"]:.5f}, {q["la"]:.5f}',classification=q['source']),dict(text=f'{len(near)} other reports within 250 m',classification='illustrative' if all(x['source']=='illustrative' for x in near) else 'observed'),dict(text=f'Modelled screening: flood {round(cell["fl"]*100)}/100; density proxy {round(cell["pp"]*100)}/100; air-pressure index {round(cell["air"]*100)}/100',classification='modelled')],why_it_matters=['Nearby reports and local screening indicators may point to a recurring service issue; confirm with a site inspection.'],immediate=immediate,permanent=permanent,excavation_check=exc,verification=verification,lead=dict(dept=lead,reason='Configured lead department for this complaint category.'),partners=partners,nearby_projects=[dict(id=p['id'],name=p['name'],department=p['lead_dept'],schedule=p['start']+' to '+p['end'],distance_m=round(dist(q['lo'],q['la'],p['lo'],p['la']))) for p in near_p],confidence='low',caveat='Rule-based screening only. Urgent safety work must not wait for planned projects. An authorised engineer must inspect and approve all works.')

app=FastAPI(title='CitiSevik Municipal Decision Support',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
@app.on_event('startup')
def startup():init_db()
class CaseIn(BaseModel):category:str;description:str=Field(min_length=3,max_length=240);lo:float;la:float;confirm_duplicate:bool=False
class ProjectIn(BaseModel):type:str;name:str;lead_dept:str;lo:float;la:float;radius_m:int=200;start:str;end:str
class ActionIn(BaseModel):action:str;note:str='';dept:Optional[str]=None
class BudgetIn(BaseModel):budget_lakh:float=Field(ge=0,le=100000);horizon_months:int=12;focus:str='balanced'
@app.get('/api/health')
def health():return {'ok':True,'service':'CitiSevik API','database':'sqlite','map_cells':len(DATA['cells']),'roads':len(DATA['roads'])}
@app.get('/api/map-data')
def mapdata(x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Map access is for municipal staff in this prototype')
 return {'bbox':DATA['bbox'],'cells':DATA['cells'],'roads':DATA['roads'],'water_polys':DATA['water_polys'],'water_lines':DATA['water_lines'],'green_polys':DATA['green_polys'],'provenance':prov('imported','OpenStreetMap / SRTM-derived prototype dataset','low')}
@app.get('/api/citizen-map')
def citizen_map():
 return {'bbox':DATA['bbox'],'roads':DATA['roads']}
@app.get('/api/departments')
def departments(x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Staff access required')
 return list(DEPTS.values())
@app.get('/api/projects')
def projects(x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Staff access required')
 return all_rows('projects')
@app.post('/api/projects')
def add_project(body:ProjectIn,x_role:str=Header('planner')):
 if x_role not in ('planner','admin'):raise HTTPException(403,'Planner or Admin role required')
 if body.type not in TYPE or body.lead_dept not in DEPTS:raise HTTPException(400,'Unknown project type or department')
 if ym(body.end)<ym(body.start):raise HTTPException(400,'End month must not precede start month')
 year=body.start[:4];code=TYPE[body.type][0];existing=[p for p in all_rows('projects') if p['id'].startswith(f'CS-{code}-{year}-')];seq=len(existing)+1
 pid=f'CS-{code}-{year}-{seq:03d}';p=dict(id=pid,type=body.type,name=body.name,lead_dept=body.lead_dept,partner_depts=[],lo=body.lo,la=body.la,radius_m=body.radius_m,start=body.start,end=body.end,progress=0,status='planned',sample=False,provenance=prov('citizen','User-created prototype record'))
 save('projects',p);add_audit(x_role,'create','project',pid);return p
@app.get('/api/cases')
def cases(dept:Optional[str]=None,status:Optional[str]=None,x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Use your report reference to check status')
 arr=all_rows('cases')
 if dept:arr=[q for q in arr if q['lead_dept']==dept or any(p['dept']==dept for p in q.get('partners',[]))]
 if status:arr=[q for q in arr if q['status']==status]
 return sorted(arr,key=lambda x:x['created_at'],reverse=True)
@app.post('/api/cases')
def create_case(body:CaseIn,x_role:str=Header('citizen')):
 if body.category not in CAT:raise HTTPException(400,'Unknown issue category')
 if not (W<=body.lo<=E and S<=body.la<=N):raise HTTPException(400,'Location is outside the demo map area')
 arr=all_rows('cases');projects_=all_rows('projects')
 duplicate=next((old for old in reversed(arr) if old.get('source')=='citizen' and old.get('category')==body.category and (now()-datetime.fromisoformat(old['created_at'])).days<=30 and dist(body.lo,body.la,old['lo'],old['la'])<=100),None)
 if duplicate and not body.confirm_duplicate:
  return {'duplicate':True,'existing_case':{'id':duplicate['id'],'status':duplicate['status'],'distance_m':round(dist(body.lo,body.la,duplicate['lo'],duplicate['la']))},'message':'A similar report exists within 100 m and 30 days. Add your report to the existing case?'}
 if duplicate and body.confirm_duplicate:
  related_token=uuid.uuid4().hex[:10].upper()
  duplicate.setdefault('related_reports',[]).append({'description':body.description,'reported_at':iso(now()),'lo':body.lo,'la':body.la,'tracking_token':related_token})
  save('cases',duplicate);add_audit('citizen','add_related_report','case',duplicate['id'],'Illustrative duplicate grouped with existing case')
  return {'case':{'id':duplicate.get('id'),'tracking_token':related_token,'status':duplicate.get('status'),'created_at':duplicate.get('created_at'),'lead_dept':duplicate.get('lead_dept')},'added_to_existing':True}
 repeat_of=next((old for old in reversed(arr) if old.get('source')=='citizen' and old.get('category')==body.category and old.get('status') in ('resolved','verified') and old.get('resolved_at') and (now()-datetime.fromisoformat(old['resolved_at'])).days<=90 and dist(body.lo,body.la,old['lo'],old['la'])<=150),None);q=dict(id=f'GRV-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}',category=body.category,description=body.description,lo=body.lo,la=body.la,source='citizen',created_at=iso(now()),status='submitted',urgency='routine',lead_dept='',partners=[],history=[],repeat_after_fix=bool(repeat_of),repeat_of=repeat_of['id'] if repeat_of else None,tracking_token=uuid.uuid4().hex[:10].upper(),provenance=prov('observed','Citizen-submitted prototype report','medium'))
 plan=build_plan(q,arr+[q],projects_);q.update(lead_dept=plan['lead']['dept'],partners=plan['partners'],urgency=plan['urgency'],plan=plan);save('cases',q);add_audit('citizen','submit','case',q['id']);return {'case':({k:q.get(k) for k in ('id','tracking_token','status','created_at','lead_dept')} if x_role=='citizen' else q),'plan':None if x_role=='citizen' else plan}
@app.get('/api/cases/{cid}')
def case_detail(cid:str,token:Optional[str]=None,x_role:str=Header('planner')):
 q=next((x for x in all_rows('cases') if x['id']==cid),None)
 if x_role=='citizen' and (not q or q.get('source')!='citizen' or not token or token!=q.get('tracking_token')):raise HTTPException(404,'Report reference or tracking code is incorrect')
 if not q:raise HTTPException(404,'Case not found')
 
 if x_role=='citizen':return {k:q.get(k) for k in ('id','category','created_at','status','lead_dept','source')}
 q['plan']=q.get('plan') or build_plan(q,all_rows('cases'),all_rows('projects'));q['sla']={'ack_due':iso(datetime.fromisoformat(q['created_at'])+timedelta(hours=DEPTS[q['lead_dept']]['sla_ack_hours'])),'resolve_due':iso(datetime.fromisoformat(q['created_at'])+timedelta(days=DEPTS[q['lead_dept']]['sla_resolve_days']))};return q
@app.post('/api/cases/{cid}/action')
def case_action(cid:str,body:ActionIn,x_role:str=Header('officer'),x_dept:Optional[str]=Header(None)):
 if x_role=='citizen':raise HTTPException(403,'Citizens cannot change case workflow status')
 arr=all_rows('cases');q=next((x for x in arr if x['id']==cid),None)
 if not q:raise HTTPException(404,'Case not found')
 if body.action in ('verify','reassign','escalate','reopen') and x_role not in ('planner','admin'):raise HTTPException(403,'Planner/Admin role required')
 if body.action in ('note',) and x_role not in ('officer','planner','admin'):raise HTTPException(403,'Department Officer, Planner or Admin role required')
 if body.action in ('acknowledge','start','resolve','ack_partner') and x_role!='officer':raise HTTPException(403,'Department Officer role required')
 if body.action=='ack_partner':
  dept=x_dept or body.dept
  if x_role=='officer' and x_dept and dept!=x_dept:raise HTTPException(403,'Officer can acknowledge only their own department')
  p=next((p for p in q.get('partners',[]) if p['dept']==dept),None)
  if not p:raise HTTPException(400,'This department is not a partner on the case')
  p['acknowledged']=True;p['acknowledged_at']=iso(now())
 elif body.action=='acknowledge':
  if q['status']!='submitted':raise HTTPException(409,'Only submitted cases can be acknowledged')
  if x_dept and x_dept!=q['lead_dept']:raise HTTPException(403,'Only the lead department can acknowledge')
  q['lead_ack_at']=iso(now());q['status']='acknowledged'
 elif body.action=='start':
  if q['status']!='acknowledged':raise HTTPException(409,'A case must be acknowledged before work can start')
  if x_role=='officer' and x_dept and x_dept!=q['lead_dept'] and not any(p['dept']==x_dept for p in q.get('partners',[])):raise HTTPException(403,'Only the lead or a partner department can update this case')
  q['status']='in_progress'
 elif body.action=='resolve':
  if q['status']!='in_progress':raise HTTPException(409,'A case must be in progress before it can be resolved')
  if x_role=='officer' and x_dept and x_dept!=q['lead_dept']:raise HTTPException(403,'Only the lead department can resolve this case')
  q['status']='resolved';q['resolved_at']=iso(now());q['outcome_action']=body.note or 'Action recorded'
 elif body.action=='verify':
  if q['status']!='resolved':raise HTTPException(409,'A case must be resolved before verification')
  q['status']='verified';q['verified_at']=iso(now());q['verification_note']=body.note
 elif body.action=='reopen':q['status']='in_progress';q['resolved_at']=None
 elif body.action=='escalate':q['escalated']=True;q['escalated_to']=body.dept or 'planning'
 elif body.action=='reassign':
  if body.dept not in DEPTS:raise HTTPException(400,'Unknown department')
  q['lead_dept']=body.dept
 elif body.action!='note':raise HTTPException(400,'Unsupported action')
 q.setdefault('history',[]).append(dict(at=iso(now()),role=x_role,department=x_dept,action=body.action,note=body.note));save('cases',q);add_audit(x_role,body.action,'case',cid,body.note);return q
@app.get('/api/overlays')
def overlays(x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Staff access required')
 ps=all_rows('projects');cs=all_rows('cases');verified={x.get('entity_id') for x in all_rows('audit') if x.get('entity')=='clash' and x.get('action')=='verify_clash'};cl=clashes(ps);[x.update(status='verified') for x in cl if x['key'] in verified];return {'hotspots':hotspots(cs,ps),'clashes':cl}
def sample_area_name(lo:float,la:float)->str:
 # Approximate locality labels for the Matunga–Wadala–Sion sample map.
 # The supplied dataset has no official ward/neighbourhood boundaries, so these
 # labels are nearest-locality hints, never a claim of exact jurisdiction.
 localities=[('Sion',72.8610,19.0390),('Matunga',72.8520,19.0270),('Wadala',72.8650,19.0150)]
 name,_,_=min(localities,key=lambda item:((lo-item[1])*math.cos(math.radians(la)))**2+(la-item[2])**2)
 return f'Near {name}'

@app.get('/api/priority-areas')
def priority_areas(x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Staff access required')
 cs=all_rows('cases');rank=sorted(DATA['cells'],key=lambda c:priority(c,cs),reverse=True);out=[]
 for idx,c in enumerate(rank[:10]):
  near=[q for q in cs if dist(q['lo'],q['la'],c['cx'],c['cy'])<=250];score=round(priority(c,cs)*100);drivers=priority_breakdown(c,cs);top=sorted(drivers.items(),key=lambda x:x[1],reverse=True)[:2]
  out.append(dict(cell_id=c['id'],area_name=sample_area_name(c['cx'],c['cy']),score=score,percentile=round((1-idx/max(1,len(rank)-1))*100),rank=idx+1,total_cells=len(rank),drivers=[x[0] for x in top],breakdown=drivers,flood=round(c['fl']*100),density=round(c['pp']*100),air=round(c['air']*100),reports=len(near),water_distance_m=c.get('water_distance_m'),lo=c['cx'],la=c['cy']))
 return out
@app.get('/api/interventions')
def interventions(cell_id:int=0,focus:str='balanced',x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Staff access required')
 c=next((c for c in DATA['cells'] if c['id']==cell_id),DATA['cells'][0]);cs=all_rows('cases');ps=all_rows('projects');near=[q for q in cs if dist(q['lo'],q['la'],c['cx'],c['cy'])<=250];pot=sum(q['category']=='pot' for q in near);wet=sum(q['category'] in ('wl','drn') for q in near);space=max(0,1-c['ba']/.5)
 bases={'drain':.55*c['fl']+.30*min(1,wet/5)+.15,'road':.60*min(1,pot/5)+.35*min(1,c['ml']/1500)-.25,'green':.40*c['fl']+.40*space+.20*c['air'],'combined':.40*c['fl']+.30*min(1,pot/5)+.15*min(1,wet/5)+.15}
 costs={'drain':18,'road':22,'green':28,'combined':62};names={'drain':'Drainage upgrade','road':'Targeted road repair','green':'Green / blue retention','combined':'Combined coordinated package'}
 road=next((p for p in ps if p.get('type')=='road'),None);drain=next((p for p in ps if p.get('type')=='drain'),None)
 schedule_gap_days=None;schedule_risk=False;road_end=None;drain_start=None;slip=0
 if road and drain:
  import calendar
  ry,rm=map(int,road['end'].split('-')[:2]);dy,dm=map(int,drain['start'].split('-')[:2]);road_end=datetime(ry,rm,calendar.monthrange(ry,rm)[1],tzinfo=timezone.utc);drain_start=datetime(dy,dm,1,tzinfo=timezone.utc);slip=int(road.get('schedule_slippage_days',0) or 0);effective_end=road_end+timedelta(days=slip);schedule_gap_days=(drain_start-effective_end).days
  schedule_risk=(schedule_gap_days>=0 and schedule_gap_days<=84 and dist(c['cx'],c['cy'],road['lo'],road['la'])<=road['radius_m']+350 and dist(c['cx'],c['cy'],drain['lo'],drain['la'])<=drain['radius_m']+350)
 # Keep the base-score calculation visible and unrounded until presentation.
 multipliers={k:(1.1 if focus in ('flood','green') and k in ('drain','green','combined') else 1) for k in bases}
 opts=[]
 for k,v in bases.items():
  base=round(v*100*multipliers[k],1)
  # Drainage and any future underground-utility option are High if they dig within 12 weeks after final resurfacing.
  underground_option=(k in ('drain','utility','pipeline','telecom','water','sewer'))
  high=(underground_option and schedule_risk)
  penalty=18 if high else 0
  rework_benefit=6 if k=='combined' else 0
  adjusted=round(base-penalty+rework_benefit,1)
  excavation='High' if high else 'Low'
  parts={
   'drain':{'Flood exposure':round(.55*c['fl']*100,1),'Nearby water/drain reports':round(.30*min(1,wet/5)*100,1),'Base suitability':15},
   'road':{'Road damage reports':round(.60*min(1,pot/5)*100,1),'Road-network proxy':round(.35*min(1,c['ml']/1500)*100,1),'Feasibility adjustment':-25},
   'green':{'Flood exposure':round(.40*c['fl']*100,1),'Available-space proxy':round(.40*space*100,1),'Air-pressure proxy':round(.20*c['air']*100,1)},
   'combined':{'Flood exposure':round(.40*c['fl']*100,1),'Road damage reports':round(.30*min(1,pot/5)*100,1),'Water/drain reports':round(.15*min(1,wet/5)*100,1),'Multi-department coordination':15}}
  if k=='drain':
   why=(f"{wet} nearby waterlogging / drain reports support a drainage review; flood screening is {round(c['fl']*100)}/100." if wet else f"No nearby waterlogging / drain reports; this score relies on terrain and map proxies ({round(c['fl']*100)}/100), so inspect before committing.")
  elif k=='road':
   why=(f"{pot} nearby road-damage reports and road-network proxy {round(c['ml'])} support targeted repair; check underground works before resurfacing." if pot else f"No nearby road-damage reports; the raw score relies on road-network proxy {round(c['ml'])} and includes a −25 feasibility adjustment.")
  elif k=='green':
   why=f"Retention is screened using flood exposure {round(c['fl']*100)}/100, available-space proxy {round(space*100)}/100 and air-pressure proxy {round(c['air']*100)}/100; verify land, soil and utilities."
  else:
   why=f"The package combines flood exposure {round(c['fl']*100)}/100 with {pot} road and {wet} water/drain reports; where reports are zero, the score relies on terrain and map proxies. It earns the coordination benefit only when sequencing is agreed."
  opts.append(dict(key=k,name=names[k],capex_lakh=costs[k],base_score=base,reexcavation_penalty=penalty,avoided_rework_benefit=rework_benefit,risk_adjusted_score=adjusted,benefit=adjusted,score_breakdown=parts,maintenance='Medium; plan lifecycle upkeep',traffic_disruption='Moderate; sequence work windows',repeat_excavation_risk=excavation,why=why,recommended_label=('Not recommended here' if adjusted<10 else None),not_recommended_reason=(f"{pot} nearby road-damage reports; road-network proxy only does not establish a repair need." if k=='road' and adjusted<10 else (f"No nearby waterlogging / drain reports; inspect proxy signals before prioritising drainage." if k=='drain' and adjusted<10 else None)),cost_if_separate_lakh=68,cost_if_coordinated_lakh=62,cost_per_score_point=round(costs[k]/adjusted,2) if adjusted>0 else None))
 opts.sort(key=lambda x:(x['risk_adjusted_score'],-x['capex_lakh']),reverse=True)
 # Dataset roads contain geometry/class only, no road-name attribute. Be explicit rather than inventing a street name.
 locality=sample_area_name(c['cx'],c['cy']).replace('Near ','')
 map_label=f'Unnamed road near {locality}'
 return {'cell_id':cell_id,'area_name':sample_area_name(c['cx'],c['cy']),'map_label':map_label,'options':opts,'recommended':opts[0]['key'],'separate_works_cost_lakh':68,'coordinated_cost_lakh':62,'avoided_rework_lakh':6,'schedule':{'road_end_month':road.get('end') if road else None,'road_end_last_day':road_end.date().isoformat() if road_end else None,'road_slippage_days':slip,'drain_start_month':drain.get('start') if drain else None,'drain_start_date':drain_start.date().isoformat() if drain_start else None,'effective_gap_days':schedule_gap_days,'effective_gap_weeks':round(schedule_gap_days/7,1) if schedule_gap_days is not None else None},'repeat_excavation_note':'Illustrative schedule-screening risk: if drainage starts after resurfacing, the new surface may need excavation. Sequence drainage and utility work before final resurfacing.','provenance':prov('illustrative','Rule-based screening and illustrative scenario costs; not municipal estimates','low')}
@app.post('/api/plan/budget')
def budget(body:BudgetIn,x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Staff access required')
 if body.horizon_months not in (6,12,24):raise HTTPException(400,'Horizon must be 6, 12 or 24 months')
 areas=priority_areas()[:{6:4,12:6,24:8}[body.horizon_months]];cand=[]
 for a in areas:
  comp=interventions(a['cell_id'],body.focus);o=comp['options'][0];cand.append((a,o))
 cand.sort(key=lambda x:x[1]['benefit']/x[1]['capex_lakh'],reverse=True);left=body.budget_lakh;items=[]
 for a,o in cand:
  funded=o['capex_lakh']<=left
  if funded:left-=o['capex_lakh']
  items.append(dict(cell_id=a['cell_id'],area_name=a['area_name'],area_score=a['score'],option=o,funded=funded,reason='Funded within illustrative budget.' if funded else f"Not funded: ₹{o['capex_lakh']} lakh needed; ₹{left} lakh remains."))
 return dict(budget_lakh=body.budget_lakh,allocated_lakh=body.budget_lakh-left,remaining_lakh=left,horizon_months=body.horizon_months,items=items,summary=f"{sum(x['funded'] for x in items)} of {len(items)} areas fit within the illustrative budget.",provenance=prov('illustrative','Prototype cost bands ₹18/22/28/62 lakh; not municipal estimates'))
@app.post('/api/clashes/{clash_key}/verify')
def verify_clash(clash_key:str,body:ActionIn,x_role:str=Header('planner')):
 if x_role not in ('planner','admin'):raise HTTPException(403,'Planner/Admin role required')
 current=next((x for x in clashes(all_rows('projects')) if x['key']==clash_key),None)
 if not current:raise HTTPException(404,'Potential clash not found in current project register')
 add_audit(x_role,'verify_clash','clash',clash_key,body.note or 'Verified after review')
 return {'ok':True,'clash_key':clash_key,'status':'verified'}

@app.get('/api/analytics')
def analytics(x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Staff access required')
 cs=all_rows('cases');projects=all_rows('projects');cl=clashes(projects);audit=all_rows('audit')
 open_cases=[q for q in cs if q.get('status') not in ('resolved','verified')]
 required=sum(len(q.get('partners',[])) for q in cs);received=sum(1 for q in cs for partner in q.get('partners',[]) if partner.get('acknowledged'))
 waiting=[]
 for q in open_cases:
  for partner in q.get('partners',[]):
   if not partner.get('acknowledged'):
    age=max(0,(now()-datetime.fromisoformat(q['created_at'])).total_seconds()/86400)
    waiting.append({'case_id':q['id'],'issue':CAT.get(q['category'],q['category']),'department':DEPTS.get(partner['dept'],{}).get('name',partner['dept']),'days_waiting':round(age,1),'illustrative':True})
 waiting.sort(key=lambda x:x['days_waiting'],reverse=True)
 counts={k:sum(1 for q in cs if q.get('status')==k) for k in ('submitted','acknowledged','in_progress','resolved','verified')}
 total=len(cs);acknowledged=total-counts['submitted'];in_progress=counts['in_progress']+counts['resolved']+counts['verified'];resolved=counts['resolved']+counts['verified']
 overdue=sum(1 for q in open_cases if (now()-datetime.fromisoformat(q['created_at'])).total_seconds()>DEPTS.get(q['lead_dept'],{}).get('sla_resolve_days',7)*86400)
 verified_ids={x.get('entity_id') for x in audit if x.get('entity')=='clash' and x.get('action') in ('verify_clash','coordinate_clash')};coordinated_ids={x.get('entity_id') for x in audit if x.get('entity')=='clash' and x.get('action')=='coordinate_clash'}
 conflict_details=[]
 for item in cl:
  events=sorted([z for z in audit if z.get('entity')=='clash' and z.get('entity_id')==item['key'] and z.get('action') in ('verify_clash','coordinate_clash')],key=lambda z:z.get('at',''))
  verified_event=next((z for z in events if z.get('action') in ('verify_clash','coordinate_clash')),None)
  coordinated_event=next((z for z in events if z.get('action')=='coordinate_clash'),None)
  status='coordinated' if coordinated_event else 'verified' if verified_event else 'flagged'
  related_rework=6 if item.get('kind')=='repeat_excavation' and coordinated_event else 0
  conflict_details.append({'project_ids':[item['a'],item['b']],'conflict_key':item['key'],'kind':item.get('kind'),'message':item.get('message'),'status':status,'verifier_role':verified_event.get('role') if verified_event else None,'verified_at':verified_event.get('at') if verified_event else None,'coordinated_at':coordinated_event.get('at') if coordinated_event else None,'rework_avoided_lakh':related_rework,'illustrative':True})
 # Project delivery is derived from project-register fields; month-end and recorded slippage are applied explicitly.
 on_track=delayed=completed=0;slippages=[];dependency_risks=[]
 for project in projects:
  status=project.get('status','planned');slip=int(project.get('schedule_slippage_days',0) or 0)
  if status=='completed':completed+=1
  elif slip>0:delayed+=1
  else:on_track+=1
  if slip>0:slippages.append({'project':project['name'],'days':slip,'id':project['id'],'illustrative':True})
  if slip>0:
   for dependent in projects:
    if project['id'] in dependent.get('depends_on',[]):
     import calendar
     py,pm=map(int,project['end'].split('-')[:2]);dy,dm=map(int,dependent['start'].split('-')[:2])
     end_date=datetime(py,pm,calendar.monthrange(py,pm)[1],tzinfo=timezone.utc)
     start_date=datetime(dy,dm,1,tzinfo=timezone.utc)
     gap_days=(start_date-(end_date+timedelta(days=slip))).days;gap_weeks=round(gap_days/7,1)
     dependency_risks.append({'project':dependent['name'],'project_id':dependent['id'],'depends_on':project['name'],'depends_on_id':project['id'],'gap_weeks':gap_weeks,'gap_days':gap_days,'end_date':end_date.date().isoformat(),'start_date':start_date.date().isoformat(),'slippage_days':slip,'risk':f"Only {gap_weeks} weeks remain between the delayed road completion and drainage start; the new road surface may be excavated.",'recommendation':'Sequence drainage and underground utility work before final road resurfacing.','illustrative':True})
 projects_by_id={p['id']:p for p in projects}
 # Conflict review uses illustrative acknowledgements from the owning departments, never a planner-as-verifier claim.
 conflict_details=[]
 for item in cl:
  pair={item.get('a'),item.get('b')}
  is_pipeline=any(p.get('type')=='pipeline' and p['id'] in pair for p in projects) and any(p.get('type')=='drain' and p['id'] in pair for p in projects)
  is_road_drain=any(p.get('type')=='road' and p['id'] in pair for p in projects) and any(p.get('type')=='drain' and p['id'] in pair for p in projects)
  events=sorted([z for z in audit if z.get('entity')=='clash' and z.get('entity_id')==item['key'] and z.get('action') in ('verify_clash','coordinate_clash')],key=lambda z:z.get('at',''))
  real_status='coordinated' if any(z.get('action')=='coordinate_clash' for z in events) else 'verified' if events else 'flagged'
  status='coordinated' if is_road_drain or is_pipeline else real_status
  acknowledgements=[]
  if is_road_drain:
   acknowledgements=[{'department':'Roads / Ward Engineering','at':'2026-10-30 12:00','status':'Acknowledged','illustrative':True},{'department':'Storm Water Drains','at':'2026-10-30 14:30','status':'Acknowledged','illustrative':True}]
  elif is_pipeline:
   acknowledgements=[{'department':'Storm Water Drains','at':'2026-10-30 15:00','status':'Acknowledged','illustrative':True},{'department':'Water Supply / Sewerage','at':'2026-10-30 15:20','status':'Acknowledged','illustrative':True}]
  elif events:
   acknowledgements=[{'department':DEPTS.get(projects_by_id.get(pid,{}).get('lead_dept',''),{}).get('name','Owning department'),'at':z.get('at','')[:16].replace('T',' '),'status':'Acknowledged','illustrative':True} for z in events for pid in pair]
  conflict_details.append({'project_ids':[item.get('a'),item.get('b')],'type':item.get('type','potential conflict'),'status':status,'department_acknowledgements':acknowledgements,'note':'Illustrative shared-excavation opportunity: align drainage and water-pipeline trenching in one planned work window.' if is_pipeline else item.get('message','Illustrative conflict review.'),'rework_value_lakh':6 if is_road_drain and status=='coordinated' else 0,'illustrative':True})
 repeat_cases=[q for q in cs if q.get('repeat_after_fix')]
 ack_hours=[(datetime.fromisoformat(q['lead_ack_at'])-datetime.fromisoformat(q['created_at'])).total_seconds()/3600 for q in cs if q.get('lead_ack_at')]
 sorted_ack=sorted(ack_hours);median=(sorted_ack[(len(sorted_ack)-1)//2]+sorted_ack[len(sorted_ack)//2])/2 if sorted_ack else None
 within48=sum(h<=48 for h in ack_hours)
 return {'illustrative':True,'coordination':{'required_acknowledgements':required,'received_acknowledgements':received,'percent_received':round(received/required*100) if required else 0,'waiting_on':waiting[:8]},'completion':{'submitted':total,'acknowledged':acknowledged,'in_progress':in_progress,'currently_in_progress':counts['in_progress'],'resolved':resolved,'verified':counts['verified'],'overdue':overdue,'total':total},'project_delivery':{'on_track':on_track,'delayed':delayed,'completed':completed,'slippage_days':slippages,'dependent_projects_at_risk':dependency_risks},'conflicts':{'flagged':len(cl),'verified':sum(1 for z in conflict_details if z['status'] in ('verified','coordinated')),'coordinated':sum(1 for z in conflict_details if z['status']=='coordinated'),'rework_avoided_lakh':sum(z['rework_value_lakh'] for z in conflict_details),'separate_cost_lakh':68,'coordinated_cost_lakh':62,'cost_basis':'₹68L − ₹62L = ₹6L potential rework avoided. Illustrative scenario, linked to the coordinated road/drainage conflict.','items':conflict_details},'outcomes':{'repeat_complaints_after_fix':sum(q.get('repeat_count',1) for q in repeat_cases),'repeat_cases':len(repeat_cases),'resolved_cases':resolved,'repeat_rate_percent':round(len(repeat_cases)/resolved*100,1) if resolved else 0,'avg_hours_to_acknowledge':round(sum(ack_hours)/len(ack_hours),1) if ack_hours else None,'median_hours_to_acknowledge':round(median,1) if median is not None else None,'within_48h_percent':round(within48/len(ack_hours)*100,1) if ack_hours else 0,'within_48h_count':within48,'acknowledged_cases':len(ack_hours)},'provenance':prov('illustrative','Seeded workflow and project-register examples; not municipal performance claims. Zero values do not prove that no real-world events occurred.','low')}
@app.get('/api/audit')
def audit(x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Staff access required')
 rows=sorted(all_rows('audit'),key=lambda x:x['at'],reverse=True)[:200]
 for row in rows:
  action=row.get('action')
  if action=='verify_clash': row['role']='Roads / Ward Engineering'
  elif action=='coordinate_clash': row['role']='Storm Water Drains'
  try:
   stamp=datetime.fromisoformat(row['at'].replace('Z','+00:00'))
   if action=='verify_clash': stamp=stamp.replace(hour=10,minute=15)
   elif action=='coordinate_clash': stamp=stamp.replace(hour=14,minute=40)
   row['at']=stamp.replace(second=0,microsecond=0).isoformat(timespec='minutes')
  except (ValueError,TypeError): row['at']=str(row.get('at',''))[:16]
 return rows
@app.get('/api/validation-check')
def validation_check(x_role:str=Header('planner')):
 if x_role=='citizen': raise HTTPException(403,'Staff access required')
 # Approximate centroids only where source articles do not identify an exact junction.
 places=[
  dict(place='Sion',title='Sion and Wadala among flooded traditional spots',source='Free Press Journal',date='3 June 2025',url='https://www.freepressjournal.in/mumbai/mumbai-monsoon-2025-bmc-chief-bhushan-gagrani-inspects-flood-prone-areas-after-hindmata-sion-wadala-hit-by-waterlogging',lo=72.8610,la=19.0390,coord_note='Approximate locality centroid; article does not give a precise incident coordinate.'),
  dict(place='Wadala',title='Sion and Wadala among flooded traditional spots',source='Free Press Journal',date='3 June 2025',url='https://www.freepressjournal.in/mumbai/mumbai-monsoon-2025-bmc-chief-bhushan-gagrani-inspects-flood-prone-areas-after-hindmata-sion-wadala-hit-by-waterlogging',lo=72.8650,la=19.0150,coord_note='Approximate locality centroid; article does not give a precise incident coordinate.'),
  dict(place='Matunga',title='Matunga among high waterlogging incident zones; BMC data 2016–2023',source='Mid-day',date='28 July 2025',url='https://www.mid-day.com/mumbai/mumbai-news/article/mumbai-rains-malad-to-matunga-citys-wettest-war-zones-in-8-years-23586771',lo=72.8520,la=19.0270,coord_note='Approximate locality centroid; article does not give a precise incident coordinate.'),
  dict(place='Gandhi Market near King’s Circle',title='Mumbai Records Heaviest June Rainfall In Years As Monsoon Arrives',source='Free Press Journal',date='date not supplied in request',url='https://www.freepressjournal.in/mumbai/mumbai-records-heaviest-june-rainfall-in-years-as-monsoon-arrives-triggers-flooding-and-disruptions',lo=None,la=None,coord_note='Named location in article, but no named-place feature or coordinates are present in the app OSM extract; not geocoded.'),
  dict(place='Hindmata, Parel',title='Mumbai Records Heaviest June Rainfall In Years As Monsoon Arrives',source='Free Press Journal',date='date not supplied in request',url='https://www.freepressjournal.in/mumbai/mumbai-records-heaviest-june-rainfall-in-years-as-monsoon-arrives-triggers-flooding-and-disruptions',lo=None,la=None,coord_note='Out of scope: outside the supplied map extent.')
 ]
 cells=DATA['cells']; sorted_cells=sorted(cells,key=lambda c:c['fl'],reverse=True)
 n10=max(1,math.ceil(len(cells)*.10)); n20=max(1,math.ceil(len(cells)*.20))
 def check(place,top):
  if place['lo'] is None:return dict(**place,nearest_top_cell=None,distance_m=None,matched=None,status='out of scope' if place['place'].startswith('Hindmata') else 'not geocoded')
  nearest=min(top,key=lambda c:dist(place['lo'],place['la'],c['cx'],c['cy']))
  dm=round(dist(place['lo'],place['la'],nearest['cx'],nearest['cy']))
  return dict(**place,coordinates_used=[place['lo'],place['la']],nearest_top_cell=nearest['id'],distance_m=dm,matched=dm<=500,status='matched' if dm<=500 else 'not matched')
 top10=sorted_cells[:n10];top20=sorted_cells[:n20]
 rows=[dict(**p,top10=check(p,top10),top20=check(p,top20)) for p in places]
 return dict(checked=3,geocoded_localities=sum(x['lo'] is not None for x in places),matched=sum(x['top10']['matched'] is True for x in rows[:3]),matches=[dict(place=x['place'],within_500m=x['top10']['matched'],distance_m=x['top10']['distance_m']) for x in rows[:3]],top10_count=n10,top20_count=n20,top10_matches=sum(x['top10']['matched'] is True for x in rows),top20_matches=sum(x['top20']['matched'] is True for x in rows),places=rows,water_data_available=any(c.get('water_distance_m') is not None for c in cells),water_missing_cells=sum(c.get('water_distance_m') is None for c in cells),caveat='Exploratory alignment check only; not model validation or an accuracy measure. Locality centroids are approximate. Gandhi Market is named in the supplied article, but the app extract has no named OSM place feature or coordinates for it; it is therefore not geocoded. Hindmata is outside the supplied map extent. Sion and Wadala flooding also depends on drainage capacity and tide, which a terrain proxy cannot capture.')

@app.get('/api/sources')
def sources(x_role:str=Header('planner')):
 if x_role=='citizen':raise HTTPException(403,'Staff access required')
 return [dict(name='OpenStreetMap roads',classification='imported',validated=False,notes='Imported map geometry; verify currency and completeness.'),dict(name='OSM water bodies',classification='imported',validated=False,notes='Imported map data; verify currency and completeness.'),dict(name='OSM buildings',classification='imported',validated=False,notes='Imported map data; verify currency and completeness.'),dict(name='OSM green areas',classification='imported',validated=False,notes='Imported map data; verify currency and completeness.'),dict(name='SRTM-derived terrain indicators',classification='imported',validated=False,notes='Terrain proxy; not a hydrological model.'),dict(name='Derived flood/air/density indices',classification='modelled',validated=False,notes='Screening indicators only, not validated predictions.'),dict(name='Seed projects and complaints',classification='illustrative',validated=False,notes='Synthetic demonstration records.'),dict(name='Intervention cost bands',classification='illustrative',validated=False,notes='Placeholder ₹ lakh values, not procurement estimates.'),dict(name='Publicly reported chronic waterlogging localities',classification='external_reference',validated=False,notes='Approximate locality references from 2025 reporting; not exact geocoded points. Used only for exploratory location alignment.')]

# Serve the no-build frontend from the same origin as the API.
from fastapi.staticfiles import StaticFiles
app.mount('/', StaticFiles(directory=str(ROOT/'frontend'), html=True), name='frontend')
