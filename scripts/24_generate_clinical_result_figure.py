#!/usr/bin/env python3
"""Generate the manuscript's age-stratified NHANES contract-rejection figure."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
src=ROOT/'data/external/lung/processed/nhanes_high_quality_adult_baseline_all.csv'
outdir=ROOT/'outputs/figures'; outdir.mkdir(parents=True,exist_ok=True)
df=pd.read_csv(src)
df['fev1_rejected']=(df['fev1_l']<0.3)|(df['fev1_l']>5.0)
df['fvc_rejected']=(df['fvc_l']<0.5)|(df['fvc_l']>6.0)
df['pef_rejected']=(df['pef_l_min']<80)|(df['pef_l_min']>750)
df['age_band']=pd.cut(df['age_years'],bins=[17,29,44,59,79],labels=['18-29','30-44','45-59','60-79'],include_lowest=True)
rates=df.groupby('age_band',observed=True)[['fev1_rejected','fvc_rejected','pef_rejected']].mean().mul(100)
fig,ax=plt.subplots(figsize=(5.25,2.75))
x=np.arange(len(rates.index)); width=.24
ax.bar(x-width,rates['fev1_rejected'],width,label='FEV1')
ax.bar(x,rates['fvc_rejected'],width,label='FVC')
ax.bar(x+width,rates['pef_rejected'],width,label='PEF')
ax.set_ylabel('Rejected by declared bound (%)'); ax.set_xlabel('Age group (years)')
ax.set_xticks(x); ax.set_xticklabels(rates.index.astype(str)); ax.set_ylim(0,7)
ax.legend(frameon=False,ncol=3,loc='upper right'); ax.grid(axis='y',alpha=.25)
for spine in ['top','right']: ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(outdir/'nhanes_rejection_by_age.pdf',bbox_inches='tight')
fig.savefig(outdir/'nhanes_rejection_by_age.png',dpi=220,bbox_inches='tight')
print(rates.round(2).to_string())
