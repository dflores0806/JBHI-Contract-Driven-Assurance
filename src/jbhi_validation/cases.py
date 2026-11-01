from __future__ import annotations
import copy
import json
from pathlib import Path
from typing import Any
from .spec import contract_oracle, stroke_rule, lung_rule, lung_personalization
from .utils import canonical_json

T0="2026-01-15T10:00:00Z"
T1="2026-01-15T10:01:00Z"
T_OLD="2026-01-15T09:59:00Z"


def _base(case_id,twin,family,kind,source_basis,question):
    return {"case_id":case_id,"twin":twin,"family":family,"kind":kind,"source_basis":source_basis,"question":question,"steps":[],"oracle":{"assertions":[]}}


def _obs(cid,val,unit,source,event,at=T0):
    o={"event_id":event,"contract_id":cid,"value":val,"source":source}
    if unit is not None: o["unit"]=unit
    if at is not None: o["acquisition_time"]=at
    return o


def _add_contract(c, obs, expected=None):
    c["steps"]=[{"op":"reset","state":{}},{"op":"submit_observation","observation":obs}]
    if expected is None: expected=contract_oracle(c["twin"],obs["contract_id"],obs)
    c["oracle"]["assertions"]=[{"path":"steps.1.observation_status","op":"eq","value":expected["status"]}]
    c["oracle"]["review_label"]=expected["status"]
    c["oracle"]["review_allowed"]=["accepted","rejected","accepted_with_warning","missing","expired"]
    if expected.get("failure"):
        c["oracle"]["assertions"].append({"path":"steps.1.failures","op":"contains","value":expected["failure"]})
    return c


def _add_rule(c, rule_id, ctx, expected=None, hard=False):
    c["steps"]=[{"op":"reset","state":{}},{"op":"evaluate_rules","context":ctx}]
    if expected is None:
        expected=(stroke_rule if c["twin"]=="stroke" else lung_rule)(rule_id,ctx)
    c["target_rule_id"]=rule_id
    c["oracle"]["rule_state"]=expected
    c["oracle"]["review_label"]=expected
    c["oracle"]["review_allowed"]=["true","false","unknown"]
    c["oracle"]["assertions"]=[{"path":f"steps.1.rule_states.{rule_id}","op":"eq","value":expected}]
    if hard and expected=="true":
        c["oracle"]["assertions"].append({"path":"steps.1.output_policy","op":"eq","value":"blocked"})
    return c


def stroke_cases():
    out=[]; i=1
    def cid():
        nonlocal i; x=f"ST-IND-{i:03d}"; i+=1; return x
    # 16 nominal: 8 admission + 8 rule semantics
    for contract,val,unit in [
        ("age_years",65,"years"),("last_known_well_min",90,"min"),("nihss",8,None),("glucose",105,"mg/dL"),
        ("spo2",96,"%"),("perfusion_percent",45.0,"%"),("core_fraction",0.25,None),("decision_time_seconds",75,"s")]:
        c=_base(cid(),"stroke","nominal","contract","METHODOLOGY","Should the observation be admitted by the declared contract?")
        out.append(_add_contract(c,_obs(contract,val,unit,"derived" if contract=="decision_time_seconds" else "case_database",c["case_id"])))
    for rid,ctx,hard in [
        ("ST-S001",{"nihss":0},False),("ST-S002",{"nihss":4},False),("ST-S003",{"nihss":10},False),("ST-S004",{"nihss":18},False),
        ("ST-S005",{"nihss":24},False),("ST-H001",{"case_type":"hemorrhagic","learner_management":"ivt"},True),
        ("ST-S011",{"learner_diagnosis":"ais_lvo","expected_diagnosis":"ais_lvo"},False),
        ("ST-S012",{"case_type":"ischemic","learner_diagnosis":"ais_lacunar","expected_diagnosis":"ais_lvo"},False)]:
        src="AHA_ICH_2022" if rid=="ST-H001" else "IMPLEMENTATION_DECLARATION"
        out.append(_add_rule(_base(cid(),"stroke","nominal","rule",src,"What is the three-valued state of the target rule?"),rid,ctx,hard=hard))
    # 8 boundary
    for contract,val,unit,source in [
        ("decision_time_seconds",0,"s","derived"),("decision_time_seconds",180,"s","derived"),("decision_time_seconds",-1,"s","derived"),("decision_time_seconds",181,"s","derived"),
        ("perfusion_percent",0.0,"%","case_database"),("perfusion_percent",100.0,"%","case_database"),("core_fraction",0.0,None,"case_database"),("core_fraction",1.0,None,"case_database")]:
        c=_base(cid(),"stroke","boundary","contract","METHODOLOGY","Does the boundary value satisfy the independent contract specification?")
        out.append(_add_contract(c,_obs(contract,val,unit,source,c["case_id"])))
    # 6 missing evidence
    c=_base(cid(),"stroke","missing_evidence","contract","METHODOLOGY","Is acquisition time mandatory for this observation?"); out.append(_add_contract(c,_obs("age_years",65,"years","case_database",c["case_id"],None)))
    c=_base(cid(),"stroke","missing_evidence","contract","METHODOLOGY","Is the mandatory value rejected when absent?"); o=_obs("nihss",8,None,"case_database",c["case_id"]); o.pop("value"); out.append(_add_contract(c,o))
    c=_base(cid(),"stroke","missing_evidence","contract","METHODOLOGY","Is a required unit rejected when absent?"); o=_obs("glucose",100,None,"case_database",c["case_id"]); out.append(_add_contract(c,o))
    for rid,ctx in [("ST-S011",{"learner_diagnosis":"ais_lvo"}),("ST-S006",{"action_ct":False}),("ST-H001",{"learner_management":"ivt"})]:
        out.append(_add_rule(_base(cid(),"stroke","missing_evidence","rule","IMPLEMENTATION_DECLARATION","How is incomplete evidence represented?"),rid,ctx,hard=(rid=="ST-H001")))
    # 6 conflicting evidence / event-history behavior
    c=_base(cid(),"stroke","conflicting_evidence","event_sequence","METHODOLOGY","Does a duplicate event leave the active state unchanged?")
    o=_obs("nihss",10,None,"case_database","dup-stroke",T0); c["steps"]=[{"op":"reset","state":{}},{"op":"submit_observation","observation":o},{"op":"submit_observation","observation":o}]; c["oracle"]["assertions"]=[{"path":"steps.2.state_effect","op":"eq","value":"duplicate_ignored"},{"path":"steps.2.warnings","op":"contains","value":"duplicate_ignored"}]; c["oracle"]["review_label"]="duplicate_ignored"; c["oracle"]["review_allowed"]=["duplicate_ignored","active_state_updated"]; out.append(c)
    c=_base(cid(),"stroke","conflicting_evidence","event_sequence","METHODOLOGY","Does an older event fail to replace the newer active value?")
    n=_obs("nihss",12,None,"case_database","new-stroke",T1); old=_obs("nihss",4,None,"case_database","old-stroke",T_OLD); c["steps"]=[{"op":"reset","state":{}},{"op":"submit_observation","observation":n},{"op":"submit_observation","observation":old},{"op":"snapshot"}]; c["oracle"]["assertions"]=[{"path":"steps.2.state_effect","op":"eq","value":"history_only"},{"path":"steps.3.nihss","op":"eq","value":12}]; c["oracle"]["review_label"]="history_only"; c["oracle"]["review_allowed"]=["history_only","active_state_updated"]; out.append(c)
    for rid,ctx,hard in [
        ("ST-H001",{"case_type":"hemorrhagic","learner_management":"ivt_evt"},True),
        ("ST-H001",{"case_type":"ischemic","learner_management":"ivt"},False),
        ("ST-S012",{"case_type":"ischemic","learner_diagnosis":"ais_lacunar","expected_diagnosis":"ais_lvo"},False),
        ("ST-S013",{"case_type":"hemorrhagic","learner_diagnosis":"sah","expected_diagnosis":"ich"},False)]:
        out.append(_add_rule(_base(cid(),"stroke","conflicting_evidence","rule","IMPLEMENTATION_DECLARATION","Resolve deliberately discordant evidence deterministically."),rid,ctx,hard=hard))
    # 4 explicit unknown
    for rid,ctx in [("ST-S002",{}),("ST-S011",{"learner_diagnosis":"ais_lvo"}),("ST-S012",{"case_type":"ischemic"}),("ST-H001",{"learner_management":"ivt"})]:
        out.append(_add_rule(_base(cid(),"stroke","explicit_unknown","rule","IMPLEMENTATION_DECLARATION","Must missing evidence remain unknown rather than be collapsed to false?"),rid,ctx,expected="unknown",hard=(rid=="ST-H001")))
    assert len(out)==40, len(out)
    return out


def lung_cases():
    out=[]; i=1
    def cid():
        nonlocal i; x=f"LU-IND-{i:03d}"; i+=1; return x
    # 16 nominal: 6 contract + 8 rules + 2 personalization
    for contract,val,unit in [("respiratory_rate",16,"breaths/min"),("fev1",3.0,"L"),("fvc",4.0,"L"),("spo2",96,"%"),("pao2",90,"mmHg"),("paco2",40,"mmHg")]:
        c=_base(cid(),"lung","nominal","contract","METHODOLOGY","Should the observation be admitted by the declared contract?")
        out.append(_add_contract(c,_obs(contract,val,unit,"case_database",c["case_id"])))
    for rid,ctx,hard in [
        ("LU-S001",{"fev1_fvc_ratio":0.60,"airway_resistance":40,"peak_expiratory_flow":450},False),
        ("LU-S002",{"fvc":2.4,"compliance":50},False),("LU-S003",{"spo2":88,"pao2":80},False),("LU-S004",{"paco2":55},False),
        ("LU-S005",{"vq_ratio":1.8},False),("LU-H001",{"learner_management":"observe","expected_diagnosis":"copd"},True),
        ("LU-H002",{"expected_diagnosis":"embolism","learner_management":"antibiotics_oxygen"},True),
        ("LU-H003",{"expected_diagnosis":"ards","action_icu":False},True)]:
        src="ERS_ATS_2022" if rid.startswith("LU-S") else "IMPLEMENTATION_DECLARATION"
        out.append(_add_rule(_base(cid(),"lung","nominal","rule",src,"What is the three-valued state of the target rule?"),rid,ctx,hard=hard))
    for kind,state,field,expected in [
        ("spo2_delta",{"spo2":90,"baseline_spo2":95},"spo2_baseline_delta",lung_personalization("spo2_delta",90,95)),
        ("fev1_percent",{"fev1":2.0,"baseline_fev1":2.5},"fev1_baseline_percent_change",lung_personalization("fev1_percent",2.0,2.5))]:
        c=_base(cid(),"lung","nominal","personalization","METHODOLOGY","Does personalization alter only its declared derived output?")
        c["steps"]=[{"op":"reset","state":state},{"op":"snapshot"}]; c["oracle"]["assertions"]=[{"path":f"steps.1.{field}","op":"approx","value":expected,"tol":1e-9}]; c["oracle"]["review_label"]=str(expected); c["oracle"]["review_allowed"]=[str(expected),"missing"]; out.append(c)
    # 8 boundary
    for contract,val,unit in [("respiratory_rate",6,"breaths/min"),("respiratory_rate",40,"breaths/min"),("respiratory_rate",5,"breaths/min"),("respiratory_rate",41,"breaths/min"),("spo2",70,"%"),("spo2",100,"%"),("spo2",69,"%"),("spo2",101,"%")]:
        c=_base(cid(),"lung","boundary","contract","METHODOLOGY","Does the boundary value satisfy the independent contract specification?")
        out.append(_add_contract(c,_obs(contract,val,unit,"case_database",c["case_id"])))
    # 6 missing evidence
    c=_base(cid(),"lung","missing_evidence","contract","METHODOLOGY","Is acquisition time mandatory for this observation?"); out.append(_add_contract(c,_obs("respiratory_rate",16,"breaths/min","case_database",c["case_id"],None)))
    c=_base(cid(),"lung","missing_evidence","contract","METHODOLOGY","Is a required unit rejected when absent?"); out.append(_add_contract(c,_obs("pao2",80,None,"case_database",c["case_id"])))
    c=_base(cid(),"lung","missing_evidence","contract","METHODOLOGY","Is the mandatory value rejected when absent?"); o=_obs("fev1",2.0,"L","case_database",c["case_id"]); o.pop("value"); out.append(_add_contract(c,o))
    out.append(_add_rule(_base(cid(),"lung","missing_evidence","rule","IMPLEMENTATION_DECLARATION","How is incomplete evidence represented?"),"LU-S003",{}))
    out.append(_add_rule(_base(cid(),"lung","missing_evidence","rule","IMPLEMENTATION_DECLARATION","How is incomplete hard-rule evidence represented?"),"LU-H003",{"expected_diagnosis":"ards"},hard=True))
    c=_base(cid(),"lung","missing_evidence","personalization","METHODOLOGY","Is personalization omitted when the required baseline is missing?"); c["steps"]=[{"op":"reset","state":{"spo2":90}},{"op":"snapshot"}]; c["oracle"]["assertions"]=[{"path":"steps.1.spo2_baseline_delta","op":"is_none_or_missing","value":True}]; c["oracle"]["review_label"]="missing"; c["oracle"]["review_allowed"]=["missing","numeric_value"]; out.append(c)
    # 6 conflicting evidence
    c=_base(cid(),"lung","conflicting_evidence","event_sequence","METHODOLOGY","Does a duplicate event leave the active state unchanged?"); o=_obs("spo2",92,"%","case_database","dup-lung",T0); c["steps"]=[{"op":"reset","state":{}},{"op":"submit_observation","observation":o},{"op":"submit_observation","observation":o}]; c["oracle"]["assertions"]=[{"path":"steps.2.state_effect","op":"eq","value":"duplicate_ignored"},{"path":"steps.2.warnings","op":"contains","value":"duplicate_ignored"}]; c["oracle"]["review_label"]="duplicate_ignored"; c["oracle"]["review_allowed"]=["duplicate_ignored","active_state_updated"]; out.append(c)
    c=_base(cid(),"lung","conflicting_evidence","event_sequence","METHODOLOGY","Does an older event fail to replace the newer active value?"); n=_obs("spo2",94,"%","case_database","new-lung",T1); old=_obs("spo2",82,"%","case_database","old-lung",T_OLD); c["steps"]=[{"op":"reset","state":{}},{"op":"submit_observation","observation":n},{"op":"submit_observation","observation":old},{"op":"snapshot"}]; c["oracle"]["assertions"]=[{"path":"steps.2.state_effect","op":"eq","value":"history_only"},{"path":"steps.3.spo2","op":"eq","value":94}]; c["oracle"]["review_label"]="history_only"; c["oracle"]["review_allowed"]=["history_only","active_state_updated"]; out.append(c)
    for rid,ctx,hard in [
        ("LU-H001",{"expected_diagnosis":"copd","learner_management":"observe"},True),
        ("LU-H002",{"expected_diagnosis":"embolism","learner_management":"antibiotics_oxygen"},True),
        ("LU-H003",{"expected_diagnosis":"ards","action_icu":False},True),
        ("LU-S007",{"hypoxemia":True,"vq_mismatch":True},False)]:
        out.append(_add_rule(_base(cid(),"lung","conflicting_evidence","rule","IMPLEMENTATION_DECLARATION","Resolve deliberately discordant evidence deterministically."),rid,ctx,hard=hard))
    # 4 explicit unknown
    for rid,ctx in [("LU-S001",{}),("LU-S002",{}),("LU-S005",{}),("LU-S013",{"expected_diagnosis":"asthma"})]:
        out.append(_add_rule(_base(cid(),"lung","explicit_unknown","rule","IMPLEMENTATION_DECLARATION","Must missing evidence remain unknown rather than be collapsed to false?"),rid,ctx,expected="unknown"))
    assert len(out)==40, len(out)
    return out


def generate_cases():
    cases=stroke_cases()+lung_cases()
    ids=[c["case_id"] for c in cases]
    assert len(ids)==80 and len(set(ids))==80
    return cases
