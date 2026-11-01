#!/usr/bin/env python3
"""Run the reproducible experiments included in this supplementary package."""
from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
steps=[
    (sys.executable,'00_preflight.py'),
    (sys.executable,'01_generate_and_lock_oracle.py'),
    (sys.executable,'02_run_cross_implementation.py'),
    (sys.executable,'03_analyze_cross_implementation.py'),
    (sys.executable,'04_invariant_negative_controls.py'),
    ('node','21_personalization_metamorphic.js'),
    (sys.executable,'22_release_evolution_study.py'),
    (sys.executable,'25_dependency_incompleteness_sensitivity.py'),
    (sys.executable,'10_download_nhanes.py'),
    (sys.executable,'11_prepare_lung_external.py'),
    (sys.executable,'13b_run_frozen_lung_external.py'),
    (sys.executable,'14_analyze_external.py'),
    (sys.executable,'23_nhanes_context_analysis.py'),
    (sys.executable,'24_generate_clinical_result_figure.py'),
]
for exe,name in steps:
    print('\n'+'='*72); print('RUNNING', name); print('='*72)
    subprocess.run([exe,str(ROOT/'scripts'/name)],check=True,cwd=ROOT)
print('\nDONE. See data/runs/, data/external/runs/, and outputs/.')
