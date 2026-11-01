#!/usr/bin/env python3
from pathlib import Path
import json, sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'data/external/lung/processed/nhanes_high_quality_adult_baseline_all.csv'
if not p.exists(): raise SystemExit(f'Missing {p}')
df=pd.read_csv(p)
df['fev1_rejected']=(df.fev1_l<0.3)|(df.fev1_l>5.0)
df['fvc_rejected']=(df.fvc_l<0.5)|(df.fvc_l>6.0)
df['pef_rejected']=(df.pef_l_min<80)|(df.pef_l_min>750)
df['age_band']=pd.cut(df.age_years,[17,29,44,59,79],labels=['18-29','30-44','45-59','60-79'],include_lowest=True)
rows=[]
for band,g in df.groupby('age_band',observed=True):
    rows.append({'age_band':str(band),'n':int(len(g)),
                 'fev1_rejected_n':int(g.fev1_rejected.sum()),'fev1_rejected_pct':round(100*g.fev1_rejected.mean(),2),
                 'fvc_rejected_n':int(g.fvc_rejected.sum()),'fvc_rejected_pct':round(100*g.fvc_rejected.mean(),2),
                 'pef_rejected_n':int(g.pef_rejected.sum()),'pef_rejected_pct':round(100*g.pef_rejected.mean(),2)})
out={'study':'nhanes_context_stratification','eligible_n':int(len(df)),'age_bands':rows,
     'fev1_le_fvc_all':bool((df.fev1_l<=df.fvc_l).all()),
     'fev1_gt_fvc_n':int((df.fev1_l>df.fvc_l).sum()),
     'pef_gt_1000_n':int((df.pef_l_min>1000).sum()),
     'pef_max_l_min':float(df.pef_l_min.max()),
     'scope_note':'Descriptive secondary analysis; age is available in the prepared replay set. No causal or population-prevalence inference.'}
outp=ROOT/'data/external/runs/nhanes_context_analysis.json'; outp.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
