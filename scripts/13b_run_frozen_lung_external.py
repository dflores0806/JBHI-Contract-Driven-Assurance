#!/usr/bin/env python3
"""Replay prepared NHANES Lung cases against the frozen target runtime/artifacts shipped with this package."""
from pathlib import Path
import subprocess, json, hashlib, datetime as dt, sys
ROOT=Path(__file__).resolve().parents[1]
repo=ROOT/'frozen_targets/lung'
cases=ROOT/'data/external/lung/processed/lung_external_cases.jsonl'
out=ROOT/'data/external/runs/external_outputs.jsonl'
runner=ROOT/'scripts/run_lung_frozen_batch.js'
if not cases.exists():
    raise SystemExit('Prepared NHANES cases missing; run scripts/10_download_nhanes.py and 11_prepare_lung_external.py first.')
for p in [repo/'artifacts/artifacts_embed.js',repo/'artifacts/methodology_runtime.js',runner]:
    if not p.exists(): raise SystemExit(f'Missing frozen target asset: {p}')
out.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['node',str(runner),str(repo),str(cases),str(out)],check=True)
def sha(p):
    h=hashlib.sha256();
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
manifest={
  'study_id':'JBHI-CONTRACT-DRIVEN-ASSURANCE',
  'executed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
  'n_cases':sum(1 for line in cases.open(encoding='utf-8') if line.strip()),
  'case_file_sha256':sha(cases),
  'output_sha256':sha(out),
  'frozen_target':{
    'artifacts_embed_sha256':sha(repo/'artifacts/artifacts_embed.js'),
    'runtime_sha256':sha(repo/'artifacts/methodology_runtime.js'),
  },
  'semantic_crosscheck':'frozen_targets/lung/SEMANTIC_CROSSCHECK.json',
}
(ROOT/'data/external/runs/external_run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest,indent=2))
