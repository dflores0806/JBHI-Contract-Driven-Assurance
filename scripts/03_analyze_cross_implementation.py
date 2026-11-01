#!/usr/bin/env python3
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from jbhi_validation.analyzer import analyze
from jbhi_validation.reporting import make_all
results=ROOT/'data/runs/system_outputs.jsonl'
if not results.exists():
    raise SystemExit('No technical target outputs found. Run scripts/02_run_cross_implementation.py first.')
df,metrics=analyze(ROOT/'data/oracle/oracle_locked.jsonl',results)
make_all(df,metrics,ROOT)
print(json.dumps(metrics,indent=2))
print('\nGenerated audit assets are available under outputs/tables, outputs/figures and outputs/macros.')
