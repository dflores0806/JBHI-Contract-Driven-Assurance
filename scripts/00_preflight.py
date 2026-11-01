#!/usr/bin/env python3
from pathlib import Path
import sys, json
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from jbhi_validation.utils import load_yaml, dump_json
from jbhi_validation.preflight import inspect_target
study=load_yaml(ROOT/'config/study.yaml')
srcfile=ROOT/'config/sources.yaml'
if not srcfile.exists(): raise SystemExit('Missing config/sources.yaml.')
sources=load_yaml(srcfile)
if 'targets' not in sources: raise SystemExit('sources.yaml must contain a top-level targets: mapping.')
reports=[]
for name in ['stroke','lung']:
    reports.append(inspect_target(name,sources['targets'][name],study['expected_targets'][name]))
print(json.dumps(reports,indent=2))
dump_json(ROOT/'data/runs/preflight.json',reports)
failed=[(r['target'],k) for r in reports for k,v in r['checks'].items() if not v]
if failed:
    print('\nREFUSING PAPER VALIDATION: target snapshot does not match configured manuscript expectations:')
    for x in failed: print(' -',x)
    print('If the manuscript release identifiers/counts changed, update config/study.yaml deliberately and document the change.')
    raise SystemExit(2)
print('\nPreflight PASS: target snapshots match the configured manuscript release.')
