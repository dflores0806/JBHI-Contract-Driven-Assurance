from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from jbhi_validation.cases import generate_cases

def test_case_count_and_mix():
    cs=generate_cases(); assert len(cs)==80; assert len({c['case_id'] for c in cs})==80
    for twin in ['stroke','lung']:
        sub=[c for c in cs if c['twin']==twin]; assert len(sub)==40
        mix={f:sum(c['family']==f for c in sub) for f in ['nominal','boundary','missing_evidence','conflicting_evidence','explicit_unknown']}
        assert mix=={'nominal':16,'boundary':8,'missing_evidence':6,'conflicting_evidence':6,'explicit_unknown':4}
