#!/usr/bin/env python3
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from jbhi_validation.utils import load_yaml, dump_json
from jbhi_validation.external_data import (
    load_nhanes_spirometry, load_nhanes_demographics, prepare_nhanes_frames,
    deterministic_stratified_sample, deterministic_sample, lung_external_cases, sha256_file
)

cfg=load_yaml(ROOT/'config/study.yaml')['external_validation']['lung_nhanes']
raw=ROOT/'data/external/lung/raw'
spx=raw/'SPX_G.XPT'; demo=raw/'DEMO_G.XPT'
missing=[str(p) for p in (spx,demo) if not p.exists()]
if missing:
    raise SystemExit('Required NHANES files not found: '+', '.join(missing)+'. Run scripts/10_download_nhanes.py or place them manually in data/external/lung/raw/.')
df=load_nhanes_spirometry(spx); demographics=load_nhanes_demographics(demo)
adult_min_age=int(cfg.get('adult_min_age',18))
base,paired=prepare_nhanes_frames(df,demographics=demographics,adult_min_age=adult_min_age)
base_s=deterministic_stratified_sample(base,int(cfg['baseline_sample_n']),int(cfg['seed']),'ratio_band')
paired_s=deterministic_sample(paired,int(cfg['paired_sample_n']),int(cfg['seed'])+1)
outdir=ROOT/'data/external/lung/processed'; outdir.mkdir(parents=True,exist_ok=True)
base.to_csv(outdir/'nhanes_high_quality_adult_baseline_all.csv',index=False)
paired.to_csv(outdir/'nhanes_high_quality_adult_pre_post_all.csv',index=False)
cases=lung_external_cases(base_s,paired_s)
casefile=outdir/'lung_external_cases.jsonl'
with casefile.open('w',encoding='utf-8') as f:
    for c in cases: f.write(json.dumps(c,ensure_ascii=False,sort_keys=True)+'\n')
manifest={
    'source_files':{'SPX_G.XPT':'data/external/lung/raw/SPX_G.XPT','DEMO_G.XPT':'data/external/lung/raw/DEMO_G.XPT'},
    'source_sha256':{'SPX_G.XPT':sha256_file(spx),'DEMO_G.XPT':sha256_file(demo)},
    'adult_min_age':adult_min_age,
    'high_quality_adult_baseline_n':len(base),'high_quality_adult_pre_post_n':len(paired),
    'baseline_sample_n':len(base_s),'paired_sample_n':len(paired_s),
    'seed':cfg['seed'],
    'quality_filter':'Adults >=18 years; baseline FEV1 and FVC quality A/B; paired analysis also requires post-bronchodilator FEV1/FVC quality A/B',
    'case_file':'data/external/lung/processed/lung_external_cases.jsonl','case_file_sha256':sha256_file(casefile)
}
dump_json(outdir/'manifest.json',manifest)
print(json.dumps(manifest,indent=2))
