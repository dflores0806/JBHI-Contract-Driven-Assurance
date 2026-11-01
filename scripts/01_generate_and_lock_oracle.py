#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from jbhi_validation.cases import generate_cases
from jbhi_validation.seal import write_jsonl, seal_oracle
from jbhi_validation.utils import load_yaml

study=load_yaml(ROOT/"config/study.yaml")
out=ROOT/"data/oracle/oracle_locked.jsonl"
cases=generate_cases()
write_jsonl(out,cases)
manifest=seal_oracle(out,study["study_id"])
print(f"Locked {len(cases)} cases: {out}")
print(f"SHA-256: {manifest['oracle_sha256']}")
print("Do not edit the oracle after this point. Any change invalidates the manifest hash.")
