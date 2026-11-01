from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def analyze_lung(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    for r in load_jsonl(path):
        if r.get("external_source") != "NHANES_2011_2012_SPX_G":
            continue
        ref = r.get("reference", {})
        if r.get("external_kind") == "baseline_spirometry":
            obs = [s for s in r.get("steps", []) if s.get("op") == "submit_observation"]
            status = {s.get("trace",{}).get("event",{}).get("contract_id", s.get("contract_id")): s.get("observation_status") for s in obs}
            # Runtime bridge does not repeat contract_id at top level; infer by position if needed.
            ids = ["fev1", "fvc", "peak_expiratory_flow"]
            for i, cid in enumerate(ids):
                if i < len(obs): status[cid] = obs[i].get("observation_status")
            evals = [s for s in r.get("steps", []) if s.get("op") == "evaluate_rules"]
            rule_state = evals[0].get("rule_states", {}).get("LU-S001") if evals else None
            rows.append({
                "case_id": r["case_id"], "kind":"baseline_spirometry", "source_record_id":r.get("source_record_id"),
                "fev1_l":ref.get("fev1_l"), "fvc_l":ref.get("fvc_l"), "pef_l_min":ref.get("pef_l_min"),
                "fev1_fvc_ratio":ref.get("fev1_fvc_ratio"), "ratio_band":ref.get("ratio_band"),
                "nhanes_bronchodilator_eligible":ref.get("nhanes_bronchodilator_eligible"),
                "fev1_status":status.get("fev1"), "fvc_status":status.get("fvc"), "pef_status":status.get("peak_expiratory_flow"),
                "obstructive_rule_state":rule_state,
            })
        else:
            snaps = [s for s in r.get("steps", []) if s.get("op") == "snapshot"]
            got = snaps[-1].get("fev1_baseline_percent_change") if snaps else None
            exp = ref.get("fev1_percent_change")
            err = None if got is None or exp is None else float(got) - float(exp)
            obs = [s for s in r.get("steps", []) if s.get("op") == "submit_observation"]
            rows.append({
                "case_id":r["case_id"], "kind":"pre_post_bronchodilator_personalization", "source_record_id":r.get("source_record_id"),
                "baseline_fev1_l":ref.get("baseline_fev1_l"), "post_fev1_l":ref.get("post_fev1_l"),
                "expected_percent_change":exp, "runtime_percent_change":got, "error":err,
                "baseline_status":obs[0].get("observation_status") if len(obs)>0 else None,
                "post_status":obs[1].get("observation_status") if len(obs)>1 else None,
            })
    df = pd.DataFrame(rows)
    metrics: dict[str, Any] = {"available": not df.empty}
    if df.empty:
        return df, metrics
    b = df[df.kind == "baseline_spirometry"].copy()
    p = df[df.kind == "pre_post_bronchodilator_personalization"].copy()
    if len(b):
        for cid, col in [("fev1","fev1_status"),("fvc","fvc_status"),("peak_expiratory_flow","pef_status")]:
            metrics[f"contract_{cid}"] = {
                "n": int(len(b)),
                "accepted": int(b[col].isin(["accepted","accepted_with_warning"]).sum()),
                "coverage": float(b[col].isin(["accepted","accepted_with_warning"]).mean()),
                "status_counts": b[col].value_counts(dropna=False).to_dict(),
            }
        metrics["obstructive_rule_state_counts"] = b["obstructive_rule_state"].value_counts(dropna=False).to_dict()
        elig = b.dropna(subset=["nhanes_bronchodilator_eligible","obstructive_rule_state"])
        if len(elig):
            # Exploratory: runtime true vs NHANES selection criterion. Unknown is retained, not forced to false.
            metrics["exploratory_bronchodilator_selection"] = {
                "n": int(len(elig)),
                "nhanes_eligible": int(elig.nhanes_bronchodilator_eligible.astype(bool).sum()),
                "runtime_true": int((elig.obstructive_rule_state == "true").sum()),
                "runtime_unknown": int((elig.obstructive_rule_state == "unknown").sum()),
            }
    if len(p):
        ok = p["runtime_percent_change"].notna() & p["expected_percent_change"].notna()
        abs_err = (p.loc[ok,"runtime_percent_change"].astype(float)-p.loc[ok,"expected_percent_change"].astype(float)).abs()
        metrics["personalization"] = {
            "n": int(len(p)), "numeric_outputs": int(ok.sum()),
            "within_0_001_pp": int((abs_err <= 0.0011).sum()) if len(abs_err) else 0,
            "max_abs_error_pp": float(abs_err.max()) if len(abs_err) else None,
            "mean_abs_error_pp": float(abs_err.mean()) if len(abs_err) else None,
        }
    return df, metrics
