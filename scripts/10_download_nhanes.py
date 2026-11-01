#!/usr/bin/env python3
from pathlib import Path
import sys, argparse, json
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from jbhi_validation.external_data import download_nhanes_spx_g, download_nhanes_demo_g

ap=argparse.ArgumentParser(description='Download official NHANES 2011-2012 spirometry and demographics files.')
ap.add_argument('--force',action='store_true')
args=ap.parse_args()
raw=ROOT/'data/external/lung/raw'
spx=raw/'SPX_G.XPT'; demo=raw/'DEMO_G.XPT'
try:
    info={
        'spirometry':download_nhanes_spx_g(spx,force=args.force),
        'demographics':download_nhanes_demo_g(demo,force=args.force),
    }
except Exception as e:
    print(e)
    print('\nManual fallback: download SPX_G.xpt and DEMO_G.xpt from the official NHANES 2011-2012 pages and save them as:')
    print(spx); print(demo)
    raise SystemExit(2)
print(json.dumps(info,indent=2))
