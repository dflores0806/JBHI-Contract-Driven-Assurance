from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from jbhi_validation.spec import stroke_rule,lung_rule,TRUE,FALSE,UNKNOWN

def test_three_valued_logic():
    assert stroke_rule('ST-H001',{'case_type':'hemorrhagic','learner_management':'ivt'})==TRUE
    assert stroke_rule('ST-H001',{'learner_management':'ivt'})==UNKNOWN
    assert lung_rule('LU-S003',{})==UNKNOWN
    assert lung_rule('LU-S003',{'spo2':88,'pao2':80})==TRUE
