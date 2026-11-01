"""Implementation-independent reference semantics.

CRITICAL: this module intentionally does not read target repository artifacts.
All expected outcomes used to create the locked oracle are declared here.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

TRUE, FALSE, UNKNOWN = "true", "false", "unknown"


def tri_and(*xs: str) -> str:
    if FALSE in xs:
        return FALSE
    if UNKNOWN in xs:
        return UNKNOWN
    return TRUE


def tri_or(*xs: str) -> str:
    if TRUE in xs:
        return TRUE
    if UNKNOWN in xs:
        return UNKNOWN
    return FALSE


def present(v: Any) -> bool:
    return v is not None and v != ""


def cmp_eq(v: Any, target: Any) -> str:
    if not present(v):
        return UNKNOWN
    return TRUE if v == target else FALSE


def cmp_neq(v: Any, target: Any) -> str:
    if not present(v):
        return UNKNOWN
    return TRUE if v != target else FALSE


def cmp_num(v: Any, op: str, target: float) -> str:
    if not present(v):
        return UNKNOWN
    try:
        if op == "lt": ok = v < target
        elif op == "lte": ok = v <= target
        elif op == "gt": ok = v > target
        elif op == "gte": ok = v >= target
        else: raise ValueError(op)
    except TypeError:
        return FALSE
    return TRUE if ok else FALSE


def cmp_in(v: Any, values: list[Any]) -> str:
    if not present(v):
        return UNKNOWN
    return TRUE if v in values else FALSE


# ---- Independent rule-state oracle ----
def stroke_rule(rule_id: str, c: dict[str, Any]) -> str:
    if rule_id == "ST-H001":
        return tri_and(cmp_eq(c.get("case_type"), "hemorrhagic"), cmp_in(c.get("learner_management"), ["ivt", "ivt_evt"]))
    if rule_id == "ST-S001": return cmp_eq(c.get("nihss"), 0)
    if rule_id == "ST-S002": return tri_and(cmp_num(c.get("nihss"), "gt", 0), cmp_num(c.get("nihss"), "lte", 4))
    if rule_id == "ST-S003": return tri_and(cmp_num(c.get("nihss"), "gt", 4), cmp_num(c.get("nihss"), "lte", 15))
    if rule_id == "ST-S004": return tri_and(cmp_num(c.get("nihss"), "gt", 15), cmp_num(c.get("nihss"), "lte", 20))
    if rule_id == "ST-S005": return cmp_num(c.get("nihss"), "gt", 20)
    if rule_id == "ST-S006": return tri_and(cmp_eq(c.get("expected_action_ct"), True), cmp_eq(c.get("action_ct"), False))
    if rule_id == "ST-S011":
        a,b=c.get("learner_diagnosis"),c.get("expected_diagnosis")
        if not present(a) or not present(b): return UNKNOWN
        return TRUE if a == b else FALSE
    if rule_id == "ST-S012":
        a,b,t=c.get("learner_diagnosis"),c.get("expected_diagnosis"),c.get("case_type")
        if not present(t) or not present(a): return UNKNOWN
        r1=cmp_eq(t,"ischemic")
        r2=cmp_in(a,["ais_lvo","ais_lacunar","ais_cardioembolic","posterior_bao","tia"])
        if not present(b): r3=UNKNOWN
        else: r3=TRUE if a != b else FALSE
        return tri_and(r1,r2,r3)
    if rule_id == "ST-S013":
        a,b,t=c.get("learner_diagnosis"),c.get("expected_diagnosis"),c.get("case_type")
        if not present(t) or not present(a): return UNKNOWN
        r1=cmp_eq(t,"hemorrhagic")
        r2=cmp_in(a,["ich","sah"])
        r3=UNKNOWN if not present(b) else (TRUE if a != b else FALSE)
        return tri_and(r1,r2,r3)
    raise KeyError(f"Independent stroke oracle does not define {rule_id}")


def lung_rule(rule_id: str, c: dict[str, Any]) -> str:
    if rule_id == "LU-H001": return tri_and(cmp_eq(c.get("learner_management"),"observe"), cmp_neq(c.get("expected_diagnosis"),"normal"))
    if rule_id == "LU-H002": return tri_and(cmp_eq(c.get("expected_diagnosis"),"embolism"), cmp_eq(c.get("learner_management"),"antibiotics_oxygen"))
    if rule_id == "LU-H003": return tri_and(cmp_eq(c.get("expected_diagnosis"),"ards"), cmp_eq(c.get("action_icu"),False))
    if rule_id == "LU-S001": return tri_or(cmp_num(c.get("fev1_fvc_ratio"),"lt",0.7),cmp_num(c.get("airway_resistance"),"gt",65),cmp_num(c.get("peak_expiratory_flow"),"lt",300))
    if rule_id == "LU-S002": return tri_or(cmp_num(c.get("fvc"),"lt",2.6),cmp_num(c.get("compliance"),"lt",35))
    if rule_id == "LU-S003": return tri_or(cmp_num(c.get("spo2"),"lt",90),cmp_num(c.get("pao2"),"lt",60))
    if rule_id == "LU-S004": return cmp_num(c.get("paco2"),"gt",50)
    if rule_id == "LU-S005": return tri_or(cmp_num(c.get("vq_ratio"),"lt",0.55),cmp_num(c.get("vq_ratio"),"gt",1.6))
    if rule_id == "LU-S006": return tri_and(cmp_eq(c.get("hypoxemia"),True),cmp_eq(c.get("restrictive"),True),cmp_num(c.get("compliance"),"lt",25))
    if rule_id == "LU-S007": return tri_and(cmp_eq(c.get("hypoxemia"),True),cmp_eq(c.get("vq_mismatch"),True))
    if rule_id == "LU-S008": return tri_and(cmp_eq(c.get("obstructive"),True),cmp_num(c.get("airway_resistance"),"gt",65))
    if rule_id == "LU-S009": return cmp_eq(c.get("restrictive"),True)
    if rule_id == "LU-S010": return cmp_num(c.get("peak_expiratory_flow"),"lt",300)
    if rule_id == "LU-S011": return cmp_num(c.get("vq_ratio"),"gt",1.6)
    if rule_id == "LU-S012": return cmp_num(c.get("vq_ratio"),"lt",0.55)
    if rule_id == "LU-S013": return tri_and(cmp_in(c.get("expected_diagnosis"),["asthma","copd"]),cmp_eq(c.get("action_oxygen"),False))
    raise KeyError(f"Independent lung oracle does not define {rule_id}")


# ---- Independent contract semantics for the stable subset used in the cross-implementation set ----
CONTRACTS = {
    "stroke": {
        "age_years": {"type":"integer","min":18,"unit":"years","sources":["case_database"],"time":True},
        "last_known_well_min": {"type":"integer","min":20,"unit":"min","sources":["case_database"],"time":True},
        "nihss": {"type":"integer","min":0,"unit":None,"sources":["case_database"],"time":True},
        "glucose": {"type":"integer","min":0,"unit":"mg/dL","sources":["case_database"],"time":True},
        "spo2": {"type":"integer","unit":"%","sources":["case_database"],"time":True},
        "perfusion_percent": {"type":"number","min":0,"max":100,"unit":"%","sources":["case_database"],"time":False},
        "core_fraction": {"type":"number","min":0,"max":1,"unit":None,"sources":["case_database"],"time":False},
        "decision_time_seconds": {"type":"integer","min":0,"max":180,"unit":"s","sources":["derived"],"time":True},
    },
    "lung": {
        "respiratory_rate": {"type":"integer","min":6,"max":40,"unit":"breaths/min","sources":["user_interaction","case_database"],"time":True},
        "fev1": {"type":"number","min":0.3,"max":5,"unit":"L","sources":["user_interaction","case_database"],"time":True},
        "fvc": {"type":"number","min":0.5,"max":6,"unit":"L","sources":["user_interaction","case_database"],"time":True},
        "spo2": {"type":"integer","min":70,"max":100,"unit":"%","sources":["user_interaction","case_database"],"time":True},
        "pao2": {"type":"integer","min":35,"max":120,"unit":"mmHg","sources":["user_interaction","case_database"],"time":True},
        "paco2": {"type":"integer","min":20,"max":80,"unit":"mmHg","sources":["user_interaction","case_database"],"time":True},
        "vq_ratio": {"type":"number","min":0.1,"max":3,"unit":None,"sources":["user_interaction","case_database"],"time":True},
        "baseline_spo2": {"type":"integer","min":70,"max":100,"unit":"%","sources":["user_interaction"],"time":True},
        "baseline_fev1": {"type":"number","min":0.3,"max":5,"unit":"L","sources":["user_interaction"],"time":True},
    }
}


def encoding_ok(value: Any, typ: str) -> bool:
    if typ == "integer": return isinstance(value, int) and not isinstance(value, bool)
    if typ == "number": return isinstance(value, (int,float)) and not isinstance(value, bool)
    return True


def contract_oracle(twin: str, contract_id: str, obs: dict[str, Any]) -> dict[str, Any]:
    s=CONTRACTS[twin][contract_id]
    if "value" not in obs or obs.get("value") in (None, ""):
        return {"status":"rejected","failure":"missing_value"}
    if not encoding_ok(obs.get("value"),s["type"]):
        return {"status":"rejected","failure":"invalid_encoding"}
    if s["unit"] is not None and obs.get("unit") != s["unit"]:
        return {"status":"rejected","failure":"missing_unit" if obs.get("unit") is None else "incompatible_unit"}
    v=obs.get("value")
    if "min" in s and v < s["min"]: return {"status":"rejected","failure":"below_min"}
    if "max" in s and v > s["max"]: return {"status":"rejected","failure":"above_max"}
    if obs.get("source") not in s["sources"]: return {"status":"rejected","failure":"disallowed_source"}
    if s["time"] and not obs.get("acquisition_time"): return {"status":"rejected","failure":"missing_acquisition_time"}
    return {"status":"accepted","failure":None}


def lung_personalization(kind: str, value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    if kind == "spo2_delta": return round(value-baseline,3)
    if kind == "fev1_percent": return None if baseline == 0 else round(((value-baseline)/baseline)*100,3)
    raise KeyError(kind)
