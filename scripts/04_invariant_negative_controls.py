#!/usr/bin/env python3
from copy import deepcopy
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from jbhi_validation.invariant_checks import evaluate_invariants

src=ROOT/'data/runs/system_outputs.jsonl'
records=[json.loads(x) for x in src.read_text(encoding='utf-8').splitlines() if x.strip()]
base_bad=[(r,evaluate_invariants(r)) for r in records if not all(evaluate_invariants(r).values())]
if base_bad:
    raise SystemExit(f'Baseline invariant checker unexpectedly failed for {len(base_bad)} records')

mutants=[]
# I1: corrupt rejected-observation state effect/revision.
i1_candidates=[]
for r in records:
    for idx,s in enumerate(r.get('steps',[])):
        if s.get('op')=='submit_observation' and s.get('observation_status') in {'rejected','missing','expired'}:
            i1_candidates.append((r,idx)); break
for n,(r,idx) in enumerate(i1_candidates[:10],1):
    m=deepcopy(r); s=m['steps'][idx]; s['state_effect']='active_state_updated'; s['state_revision']=(s.get('state_revision') or 0)+1
    mutants.append((f'I1-{n:02d}','I1',m))
# I2: corrupt one recorded release identity.
for n,r in enumerate(records[:10],1):
    m=deepcopy(r)
    if m.get('trace_history'):
        m['trace_history'][0]['release_id']='corrupted-release'
    else:
        m['release_id']='corrupted-release'
    mutants.append((f'I2-{n:02d}','I2',m))
# I3: corrupt decision/rule-output state revision.
i3_candidates=[]
for r in records:
    for idx,s in enumerate(r.get('steps',[])):
        if s.get('op') in {'evaluate_rules','commit_decision'}:
            i3_candidates.append((r,idx)); break
for n,(r,idx) in enumerate(i3_candidates[:10],1):
    m=deepcopy(r); s=m['steps'][idx]; s['state_revision']=(s.get('state_revision') or 0)+100
    mutants.append((f'I3-{n:02d}','I3',m))

rows=[]
for mid,target,m in mutants:
    got=evaluate_invariants(m)
    rows.append({'mutant_id':mid,'target':target,'detected':not got[target],**got})
summary={
    'baseline_records':len(records),
    'baseline_all_pass':True,
    'negative_controls':len(rows),
    'detected':sum(1 for x in rows if x['detected']),
    'by_invariant':{k:{'n':sum(1 for x in rows if x['target']==k),'detected':sum(1 for x in rows if x['target']==k and x['detected'])} for k in ['I1','I2','I3']}
}
out=ROOT/'data/runs/invariant_negative_controls.json'
out.write_text(json.dumps({'summary':summary,'cases':rows},indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
