#!/usr/bin/env python3
from pathlib import Path
import sys, json, subprocess, platform, datetime as dt
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from jbhi_validation.utils import load_yaml, sha256_file, dump_json, git_commit, resolve_repo_path
from jbhi_validation.runner import run_all
from jbhi_validation.analyzer import load_jsonl
from jbhi_validation.preflight import inspect_target

study=load_yaml(ROOT/'config/study.yaml')
manifest=json.loads((ROOT/'data/oracle/oracle_manifest.json').read_text(encoding='utf-8'))
oracle=ROOT/'data/oracle/oracle_locked.jsonl'
if sha256_file(oracle)!=manifest['oracle_sha256']:
    raise SystemExit('Oracle hash mismatch. Regenerate/seal and document the change before execution.')
sources=load_yaml(ROOT/'config/sources.yaml')
# Refuse execution if the target folders do not match this package's declared snapshot.
preflight=[]
for name in ['stroke','lung']:
    r=inspect_target(name,sources['targets'][name],study['expected_targets'][name]); preflight.append(r)
failed=[(r['target'],k) for r in preflight for k,v in r['checks'].items() if not v]
if failed:
    raise SystemExit('Cross-implementation execution refused: target snapshot failed preflight: '+str(failed))
repos={k:resolve_repo_path(v['repo_path']) for k,v in sources['targets'].items()}
cases=load_jsonl(oracle)
out=ROOT/'data/runs/system_outputs.jsonl'
run_all(cases,repos,out)
try:
    node_version=subprocess.run(['node','--version'],capture_output=True,text=True,check=True).stdout.strip()
except Exception:
    node_version='unknown'
run_manifest={
    'study_id':study['study_id'], 'executed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
    'oracle_sha256':manifest['oracle_sha256'], 'system_outputs_sha256':sha256_file(out),
    'python_version':sys.version, 'node_version':node_version, 'platform':platform.platform(), 'targets':{}
}
for name,repo in repos.items():
    source_meta_path=repo/'SOURCE.json'
    source_meta=json.loads(source_meta_path.read_text(encoding='utf-8')) if source_meta_path.exists() else {}
    run_manifest['targets'][name]={
        'repo_path':sources['targets'][name]['repo_path'],
        'source_commit':source_meta.get('commit'),
        'git_commit':git_commit(repo),
        'release_sha256':sha256_file(repo/'artifacts/release.json'),
        'contracts_sha256':sha256_file(repo/'artifacts/contracts.json'),
        'rules_sha256':sha256_file(repo/'artifacts/rules.json'),
        'runtime_sha256':sha256_file(repo/'artifacts/methodology_runtime.js'),
        'embed_sha256':sha256_file(repo/'artifacts/artifacts_embed.js'),
    }
dump_json(ROOT/'data/runs/run_manifest.json',run_manifest)
print(f'Executed {len(cases)} locked cross-implementation cases.')
print(f'Results: {out}')
