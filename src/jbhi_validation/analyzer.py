from __future__ import annotations
import json, math
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, cohen_kappa_score, confusion_matrix
from .utils import nested_get


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def check_assertion(result: dict, a: dict) -> bool:
    got=nested_get(result,a["path"])
    op=a["op"]; val=a.get("value")
    if op=="eq": return got==val
    if op=="contains": return isinstance(got,(list,str)) and val in got
    if op=="approx": return got is not None and abs(float(got)-float(val))<=float(a.get("tol",1e-9))
    if op=="is_none_or_missing": return got is None
    raise KeyError(op)


def wilson(k:int,n:int,z=1.959963984540054)->tuple[float,float]:
    if n==0:return (float('nan'),float('nan'))
    p=k/n; den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0,center-half),min(1,center+half)


def analyze(oracle_path:Path, results_path:Path):
    cases={c["case_id"]:c for c in load_jsonl(oracle_path)}
    results={r["case_id"]:r for r in load_jsonl(results_path)}
    rec=[]; rule_true=[]; rule_pred=[]
    for cid,c in cases.items():
        r=results.get(cid)
        if r is None:
            rec.append({"case_id":cid,"twin":c["twin"],"family":c["family"],"kind":c["kind"],"pass":False,"reason":"missing_result"}); continue
        flags=[check_assertion(r,a) for a in c["oracle"]["assertions"]]
        rr={"case_id":cid,"twin":c["twin"],"family":c["family"],"kind":c["kind"],"pass":all(flags),"n_assertions":len(flags),"n_assertions_passed":sum(flags)}
        if "rule_state" in c["oracle"]:
            target=c["target_rule_id"]; pred=nested_get(r,f"steps.1.rule_states.{target}")
            rr.update({"target_rule_id":target,"oracle_rule_state":c["oracle"]["rule_state"],"system_rule_state":pred})
            rule_true.append(c["oracle"]["rule_state"]); rule_pred.append(pred)
        # Invariant checks over all traces produced by the case.
        traces=r.get("trace_history",[])
        rr["I2_release_coherence"] = all(t.get("release_id")==r.get("release_id") for t in traces) if traces else True
        rr["I3_output_binding"] = all(t.get("release_id") is not None and t.get("state_revision") is not None for t in traces) if traces else True
        # I1 proxy: any rejected observation must not report active_state_updated.
        obs_steps=[s for s in r.get("steps",[]) if s.get("op")=="submit_observation"]
        rr["I1_contract_before_reasoning"] = all(not(s.get("observation_status")=="rejected" and s.get("state_effect")=="active_state_updated") for s in obs_steps)
        rec.append(rr)
    df=pd.DataFrame(rec)
    metrics={}
    for key,sub in [("overall",df),*( (f"twin_{x}",df[df.twin==x]) for x in sorted(df.twin.unique()) )]:
        n=len(sub); k=int(sub["pass"].sum()); lo,hi=wilson(k,n)
        metrics[key]={"n":n,"passed":k,"agreement":k/n if n else None,"ci95_low":lo,"ci95_high":hi}
    family={}
    for (twin,fam),sub in df.groupby(["twin","family"]):
        n=len(sub); k=int(sub["pass"].sum()); lo,hi=wilson(k,n); family[f"{twin}:{fam}"]={"n":n,"passed":k,"agreement":k/n,"ci95_low":lo,"ci95_high":hi}
    metrics["by_family"]=family
    if rule_true:
        labels=["true","false","unknown"]
        metrics["rule_states"]={
            "n":len(rule_true),"macro_f1":float(f1_score(rule_true,rule_pred,labels=labels,average="macro",zero_division=0)),
            "kappa":float(cohen_kappa_score(rule_true,rule_pred,labels=labels)),
            "unknown_recall":float(sum(1 for a,b in zip(rule_true,rule_pred) if a=="unknown" and b=="unknown")/max(1,sum(1 for a in rule_true if a=="unknown"))),
            "labels":labels,"confusion_matrix":confusion_matrix(rule_true,rule_pred,labels=labels).tolist()
        }
    for inv in ["I1_contract_before_reasoning","I2_release_coherence","I3_output_binding"]:
        metrics[inv]={"n":len(df),"passed":int(df[inv].sum()),"rate":float(df[inv].mean())}
    return df,metrics
