#!/usr/bin/env python3
"""Sensitivity of dependency-closure RTS to undeclared/omitted dependencies.

This intentionally corrupts the declared test->artifact dependency map while keeping
behavioral changes fixed. It is a limitation/sensitivity study, not a claim that an
execution-derived graph is automatically available in production.
"""
from __future__ import annotations
import json, runpy, copy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ns = runpy.run_path(str(ROOT/'scripts/22_release_evolution_study.py'))
CASES=ns['CASES']; DEP=ns['DEP']; BASE=ns['BASE']; CONTRACTS=ns['CONTRACTS']; M=ns['M']; GROUPS=ns['GROUPS']; outcome=ns['outcome']

# Recompute the changed test set for each candidate release.
release_sets=[]
for rel,idxs in GROUPS:
    cs=copy.deepcopy(CONTRACTS); rs={}; ps={}; arts=[]
    for i in idxs:
        _,art,f=M[i]; f(cs,rs,ps); arts.append(art)
    now={c['case_id']:outcome(c,cs,rs,ps) for c in CASES}
    changed={cid for cid in BASE if now[cid]!=BASE[cid]}
    release_sets.append((rel,arts,changed))

# Candidate dependency links whose omission is known to matter for at least one
# observed behavioral change in the seeded release study.
critical=[]
for rel,arts,changed in release_sets:
    for art in arts:
        affected={cid for cid in changed if art in DEP[cid]}
        if affected:
            critical.append((art, affected))
# unique by artifact
uniq={a:ids for a,ids in critical}
critical=list(uniq.items())

levels=[0,1,2,3]
results=[]
for k in levels:
    dep={cid:set(v) for cid,v in DEP.items()}
    omitted=[]
    for art,affected in critical[:k]:
        omitted.append({'artifact':art,'affected_cases':sorted(affected)})
        # simulate missing metadata edge by removing this artifact from all affected tests
        for cid in affected:
            dep[cid].discard(art)
    tp=fn=selected_total=changed_total=0
    per_release=[]
    for rel,arts,changed in release_sets:
        selected={cid for cid,d in dep.items() if d.intersection(arts)}
        captured=changed & selected
        misses=changed-selected
        tp += len(captured); fn += len(misses)
        selected_total += len(selected); changed_total += len(changed)
        per_release.append({'release':rel,'changed_n':len(changed),'selected_n':len(selected),
                            'captured_n':len(captured),'missed_n':len(misses),'missed_cases':sorted(misses)})
    recall=1.0 if changed_total==0 else tp/changed_total
    results.append({'omitted_dependency_links':k,'omitted':omitted,'changed_behavior_instances':changed_total,
                    'captured_instances':tp,'missed_instances':fn,'recall':round(recall,4),
                    'mean_selected_tests':round(selected_total/len(release_sets),1),'per_release':per_release})

summary={'study':'dependency_incompleteness_sensitivity','critical_dependency_candidates':len(critical),
         'levels':results,
         'interpretation':'Declared dependency closure is safe only under dependency completeness. Deliberately omitting dependency metadata creates false negatives; full regression remains the reference for detecting them.'}
out=ROOT/'data/runs/dependency_incompleteness_sensitivity.json'
out.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
