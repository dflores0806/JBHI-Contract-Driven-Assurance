import pandas as pd
import pytest
from jbhi_validation.external_data import prepare_nhanes_frames, lung_external_cases


def test_nhanes_adult_quality_filter_and_units():
    spx=pd.DataFrame({
        'SEQN':[1,2,3,4], 'SPXNFEV1':[3000,1800,2500,2200], 'SPXNFVC':[4000,3000,3200,3000],
        'SPXNPEF':[5000,3500,4200,4000], 'SPXNQFVC':['A','A','C','B'], 'SPXNQFV1':['B','A','A','B'],
        'SPDBRONC':[2,1,2,2], 'SPXBFEV1':[3300,2100,2600,2400], 'SPXBQFVC':['A','B','A','C'], 'SPXBQFV1':['A','B','A','A']})
    demo=pd.DataFrame({'SEQN':[1,2,3,4],'RIDAGEYR':[45,16,60,50]})
    base,paired=prepare_nhanes_frames(spx,demographics=demo,adult_min_age=18)
    assert set(base.SEQN.astype(int))=={1,4}
    r=base.set_index('SEQN').loc[1]
    assert r.fev1_l==pytest.approx(3.0) and r.fvc_l==pytest.approx(4.0)
    assert r.pef_l_min==pytest.approx(300.0) and r.fev1_fvc_ratio==pytest.approx(0.75)
    assert set(paired.SEQN.astype(int))=={1}
    assert paired.iloc[0].fev1_percent_change==pytest.approx(10.0)


def test_lung_external_case_payload_uses_real_values():
    base=pd.DataFrame([{'SEQN':10,'fev1_l':2.4,'fvc_l':4.0,'pef_l_min':280.0,'fev1_fvc_ratio':0.6,
        'nhanes_bronchodilator_eligible':True,'ratio_band':'lt_0_70','age_years':55}])
    paired=pd.DataFrame([{'SEQN':11,'baseline_fev1_l':2.0,'post_fev1_l':2.4,'fev1_percent_change':20.0,'age_years':61}])
    cases=lung_external_cases(base,paired)
    assert len(cases)==2 and cases[0]['steps'][1]['observation']['value']==pytest.approx(2.4)
    assert cases[1]['reference']['fev1_percent_change']==pytest.approx(20.0)


def test_xport_guard_rejects_html(tmp_path):
    from jbhi_validation.external_data import _is_xport_file, load_nhanes_spirometry
    p=tmp_path/'SPX_G.XPT'; p.write_text('<html>not xport</html>'*1000,encoding='utf-8')
    assert _is_xport_file(p) is False
    with pytest.raises(ValueError,match='not a valid SAS XPORT file'):
        load_nhanes_spirometry(p)
