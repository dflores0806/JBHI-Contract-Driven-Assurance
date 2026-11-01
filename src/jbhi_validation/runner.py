from __future__ import annotations
import json, subprocess
from pathlib import Path
from .utils import ROOT, canonical_json


def run_case(repo: Path, case: dict, node_bin="node") -> dict:
    bridge=ROOT/"node/runtime_bridge.js"
    p=subprocess.run([node_bin,str(bridge),str(repo)],input=canonical_json(case),text=True,capture_output=True)
    if p.returncode!=0:
        raise RuntimeError(f"Node bridge failed for {case['case_id']}:\n{p.stderr}")
    return json.loads(p.stdout)


def run_all(cases: list[dict], repos: dict[str,Path], out_path: Path, node_bin="node") -> None:
    out_path.parent.mkdir(parents=True,exist_ok=True)
    with open(out_path,"w",encoding="utf-8") as f:
        for c in cases:
            r=run_case(repos[c["twin"]],c,node_bin=node_bin)
            f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
