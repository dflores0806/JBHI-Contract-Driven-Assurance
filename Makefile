PYTHON ?= python3

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

preflight:
	PYTHONPATH=src $(PYTHON) scripts/00_preflight.py

technical:
	PYTHONPATH=src $(PYTHON) scripts/01_generate_and_lock_oracle.py
	PYTHONPATH=src $(PYTHON) scripts/02_run_cross_implementation.py
	PYTHONPATH=src $(PYTHON) scripts/03_analyze_cross_implementation.py
	PYTHONPATH=src $(PYTHON) scripts/04_invariant_negative_controls.py
	node scripts/21_personalization_metamorphic.js
	PYTHONPATH=src $(PYTHON) scripts/22_release_evolution_study.py
	PYTHONPATH=src $(PYTHON) scripts/25_dependency_incompleteness_sensitivity.py

nhanes:
	PYTHONPATH=src $(PYTHON) scripts/10_download_nhanes.py
	PYTHONPATH=src $(PYTHON) scripts/11_prepare_lung_external.py
	node --version
	PYTHONPATH=src $(PYTHON) scripts/13b_run_frozen_lung_external.py
	PYTHONPATH=src $(PYTHON) scripts/14_analyze_external.py
	PYTHONPATH=src $(PYTHON) scripts/23_nhanes_context_analysis.py
	PYTHONPATH=src $(PYTHON) scripts/24_generate_clinical_result_figure.py

all:
	PYTHONPATH=src $(PYTHON) scripts/90_run_validation.py
