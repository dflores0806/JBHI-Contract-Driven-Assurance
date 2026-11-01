#!/usr/bin/env python3
from __future__ import annotations
import copy, json, statistics, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from jbhi_validation.spec import (
    CONTRACTS, stroke_rule, lung_rule, lung_personalization,
    tri_and, tri_or, cmp_eq, cmp_num, cmp_in,
)

CASES=[json.loads(x) for x in (ROOT/'data/oracle/oracle_locked.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]

RULE_FIELDS={
    'ST-H001':{'case_type','learner_management'},'ST-S001':{'nihss'},'ST-S002':{'nihss'},
    'ST-S003':{'nihss'},'ST-S004':{'nihss'},'ST-S005':{'nihss'},'ST-S006':{'expected_action_ct','action_ct'},
    'ST-S011':{'learner_diagnosis','expected_diagnosis'},'ST-S012':{'learner_diagnosis','expected_diagnosis','case_type'},
    'ST-S013':{'learner_diagnosis','expected_diagnosis','case_type'},
    'LU-H001':{'learner_management','expected_diagnosis'},'LU-H002':{'expected_diagnosis','learner_management'},
    'LU-H003':{'expected_diagnosis','action_icu'},'LU-S001':{'fev1_fvc_ratio','airway_resistance','peak_expiratory_flow'},
    'LU-S002':{'fvc','compliance'},'LU-S003':{'spo2','pao2'},'LU-S004':{'paco2'},'LU-S005':{'vq_ratio'},
    'LU-S006':{'hypoxemia','restrictive','compliance'},'LU-S007':{'hypoxemia','vq_mismatch'},
    'LU-S008':{'obstructive','airway_resistance'},'LU-S009':{'restrictive'},'LU-S010':{'peak_expiratory_flow'},
    'LU-S011':{'vq_ratio'},'LU-S012':{'vq_ratio'},'LU-S013':{'expected_diagnosis','action_oxygen'},
}
DERIVED_FROM={'fev1_fvc_ratio':{'fev1','fvc'},'spo2_baseline_delta':{'spo2','baseline_spo2'},
              'fev1_baseline_percent_change':{'fev1','baseline_fev1'}}

def enc_ok(v,t):
    if t=='integer': return isinstance(v,int) and not isinstance(v,bool)
    if t=='number': return isinstance(v,(int,float)) and not isinstance(v,bool)
    return True

def outcome(case, contracts=None, rules=None, pers=None):
    contracts=contracts or CONTRACTS; rules=rules or {}; pers=pers or {}
    twin=case['twin']; kind=case['kind']
    if kind=='contract':
        obs=[s['observation'] for s in case['steps'] if s['op']=='submit_observation'][-1]
        sp=contracts[twin][obs['contract_id']]
        if 'value' not in obs or obs.get('value') in (None,''): return 'rejected:missing_value'
        v=obs.get('value')
        if not enc_ok(v,sp['type']): return 'rejected:invalid_encoding'
        if sp.get('unit') is not None and obs.get('unit')!=sp['unit']: return 'rejected:'+('missing_unit' if obs.get('unit') is None else 'incompatible_unit')
        if 'min' in sp and v<sp['min']: return 'rejected:below_min'
        if 'max' in sp and v>sp['max']: return 'rejected:above_max'
        if obs.get('source') not in sp['sources']: return 'rejected:disallowed_source'
        if sp['time'] and not obs.get('acquisition_time'): return 'rejected:missing_acquisition_time'
        return 'accepted'
    if kind=='rule':
        rid=case['target_rule_id']; ctx=[s.get('context',{}) for s in case['steps'] if s['op']=='evaluate_rules'][-1]
        if rid in rules: return rules[rid](ctx)
        return stroke_rule(rid,ctx) if twin=='stroke' else lung_rule(rid,ctx)
    if kind=='personalization':
        state=[s.get('state',{}) for s in case['steps'] if s['op']=='reset'][-1]
        paths=' '.join(a['path'] for a in case['oracle']['assertions'])
        if 'spo2_baseline_delta' in paths:
            fn=pers.get('spo2_delta',lambda v,b:lung_personalization('spo2_delta',v,b)); return fn(state.get('spo2'),state.get('baseline_spo2'))
        if 'fev1_baseline_percent_change' in paths:
            fn=pers.get('fev1_percent',lambda v,b:lung_personalization('fev1_percent',v,b)); return fn(state.get('fev1'),state.get('baseline_fev1'))
    if kind=='event_sequence': return tuple((a['path'],json.dumps(a.get('value'),sort_keys=True)) for a in case['oracle']['assertions'])
    raise KeyError(kind)

def deps(case):
    d=set(); twin=case['twin']; kind=case['kind']
    if kind=='contract':
        o=[s['observation'] for s in case['steps'] if s['op']=='submit_observation'][-1]; d.add(f'contract:{twin}:{o["contract_id"]}')
    elif kind=='event_sequence':
        for s in case['steps']:
            if s['op']=='submit_observation': d.add(f'contract:{twin}:{s["observation"]["contract_id"]}')
    elif kind=='rule':
        rid=case['target_rule_id']; d.add(f'rule:{twin}:{rid}')
        for fld in RULE_FIELDS[rid]:
            if fld in CONTRACTS.get(twin,{}): d.add(f'contract:{twin}:{fld}')
            if fld in DERIVED_FROM:
                for src in DERIVED_FROM[fld]:
                    if src in CONTRACTS.get(twin,{}): d.add(f'contract:{twin}:{src}')
    elif kind=='personalization':
        p=' '.join(a['path'] for a in case['oracle']['assertions'])
        if 'spo2_baseline_delta' in p: d|={'personalization:lung:spo2_delta','contract:lung:spo2','contract:lung:baseline_spo2'}
        if 'fev1_baseline_percent_change' in p: d|={'personalization:lung:fev1_percent','contract:lung:fev1','contract:lung:baseline_fev1'}
    return d

BASE={c['case_id']:outcome(c) for c in CASES}; DEP={c['case_id']:deps(c) for c in CASES}

# Eleven seeded, plausible artifact edits, grouped into five candidate releases.
M=[]
def contract(twin,cid,key,val,name):
    def f(cs,rs,ps): cs[twin][cid][key]=val
    M.append((name,f'contract:{twin}:{cid}',f))
def rule(twin,rid,fn,name):
    def f(cs,rs,ps): rs[rid]=fn
    M.append((name,f'rule:{twin}:{rid}',f))
def per(kind,fn,name):
    def f(cs,rs,ps): ps[kind]=fn
    M.append((name,f'personalization:lung:{kind}',f))

contract('lung','respiratory_rate','max',39,'RR maximum 40->39')
contract('lung','spo2','min',71,'SpO2 minimum 70->71')
contract('stroke','perfusion_percent','max',99,'Perfusion maximum 100->99')
contract('stroke','decision_time_seconds','max',179,'Decision-time maximum 180->179')
rule('lung','LU-S001',lambda c:tri_or(cmp_num(c.get('fev1_fvc_ratio'),'lt',0.50),cmp_num(c.get('airway_resistance'),'gt',65),cmp_num(c.get('peak_expiratory_flow'),'lt',300)),'LU-S001 ratio threshold 0.70->0.50')
rule('lung','LU-S003',lambda c:tri_or(cmp_num(c.get('spo2'),'lt',88),cmp_num(c.get('pao2'),'lt',60)),'LU-S003 SpO2 threshold 90->88')
rule('stroke','ST-S002',lambda c:tri_and(cmp_num(c.get('nihss'),'gt',0),cmp_num(c.get('nihss'),'lte',3)),'ST-S002 upper NIHSS 4->3')
rule('stroke','ST-S004',lambda c:tri_and(cmp_num(c.get('nihss'),'gt',15),cmp_num(c.get('nihss'),'lte',17)),'ST-S004 upper NIHSS 20->17')
rule('stroke','ST-H001',lambda c:tri_and(cmp_eq(c.get('case_type'),'hemorrhagic'),cmp_in(c.get('learner_management'),['ivt'])),'ST-H001 removes ivt_evt branch')
per('spo2_delta',lambda v,b:None if v is None or b is None else round(b-v,3),'SpO2 delta direction change')
per('fev1_percent',lambda v,b:None if v is None or b is None or v==0 else round(((v-b)/v)*100,3),'FEV1 denominator baseline->current')

GROUPS=[
 ('REL-A Lung admission update',[0,1,5]),
 ('REL-B Stroke boundary update',[2,3,6]),
 ('REL-C Stroke reasoning update',[7,8]),
 ('REL-D Lung interpretation/personalization',[4,9]),
 ('REL-E Lung FEV1 personalization',[10]),
]
results=[]
for rel,idxs in GROUPS:
    cs=copy.deepcopy(CONTRACTS); rs={}; ps={}; arts=[]; changes=[]
    for i in idxs:
        name,art,f=M[i]; f(cs,rs,ps); arts.append(art); changes.append(name)
    now={c['case_id']:outcome(c,cs,rs,ps) for c in CASES}
    changed=sorted([cid for cid in BASE if now[cid]!=BASE[cid]])
    selected=sorted([cid for cid,d in DEP.items() if d.intersection(arts)])
    missed=sorted(set(changed)-set(selected)); extra=sorted(set(selected)-set(changed))
    results.append({'release':rel,'seeded_changes':changes,'changed_artifacts':arts,'selected_n':len(selected),'full_suite_n':len(CASES),
                    'behavior_changes_n':len(changed),'behavior_changes':changed,'selected_cases':selected,'missed_changes':missed,
                    'conservative_extra_n':len(extra),'reduction_pct':round(100*(1-len(selected)/len(CASES)),1)})
summary={
 'study':'seeded_release_evolution_dependency_closure',
 'corpus_n':len(CASES),'candidate_releases':len(results),'seeded_artifact_changes':len(M),
 'total_observed_behavior_changes':sum(r['behavior_changes_n'] for r in results),
 'captured_behavior_changes':sum(r['behavior_changes_n']-len(r['missed_changes']) for r in results),
 'missed_behavior_changes':sum(len(r['missed_changes']) for r in results),
 'selected_tests_total':sum(r['selected_n'] for r in results),'full_regression_tests_total':len(CASES)*len(results),
 'mean_selected_tests':round(statistics.mean(r['selected_n'] for r in results),1),
 'median_selected_tests':statistics.median(r['selected_n'] for r in results),
 'mean_regression_reduction_pct':round(statistics.mean(r['reduction_pct'] for r in results),1),
 'results':results,
 'scope_note':'Seeded artifact changes over the frozen 80-case post-freeze corpus; demonstrates regression-scope mechanics, not empirical defect rates or clinical release history.'
}
out=ROOT/'data/runs/release_evolution_study.json'; out.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
if summary['missed_behavior_changes']!=0: raise SystemExit(1)
