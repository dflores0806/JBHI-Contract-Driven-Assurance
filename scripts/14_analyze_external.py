#!/usr/bin/env python3
from pathlib import Path
import sys, json
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from jbhi_validation.external_analyzer import analyze_lung

out=ROOT/'data/external/runs/external_outputs.jsonl'
if not out.exists():
    raise SystemExit('No NHANES target outputs found. Run scripts/13b_run_frozen_lung_external.py first.')
lung_df, metrics = analyze_lung(out)
run=ROOT/'data/external/runs'; run.mkdir(parents=True,exist_ok=True)
lung_df.to_csv(run/'lung_external_analysis.csv',index=False)
payload={'lung_external':metrics}
(run/'external_metrics.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
print(json.dumps(payload,indent=2))
