# Contract-Driven Assurance and Runtime Verification of Health Digital Twins

[![Manuscript](https://img.shields.io/badge/manuscript-IEEE%20JBHI-00629B)](https://www.embs.org/jbhi/)
![Reproducibility](https://img.shields.io/badge/reproducibility-PASS-brightgreen)
![Tests](https://img.shields.io/badge/tests-5%20passed-brightgreen)
![Python](https://img.shields.io/badge/Python-%E2%89%A53.10-blue)
![Node.js](https://img.shields.io/badge/Node.js-%E2%89%A518-green)
![Data](https://img.shields.io/badge/data-NHANES%202011--2012-informational)

Reproducibility package accompanying the manuscript **"Contract-Driven Assurance and Runtime Verification of Health Digital Twins"**, prepared for the *IEEE Journal of Biomedical and Health Informatics (JBHI)*.

This repository contains the frozen artifacts, scripts, locked scenarios and oracles, compact result files, and external-data processing pipeline used to reproduce the main post-freeze engineering-assurance experiments reported in the manuscript. The evaluation covers StrokeTwinMentor and LungTwinMentor, together with an external biomedical-data stress replay using public NHANES spirometry data.

The repository is intended to support **technical reproducibility and auditability**. The reported experiments evaluate engineering conformance, cross-implementation consistency, trace-invariant checks, deterministic personalization properties, controlled release-change behavior, and contract behavior under external replay. They do not constitute clinical validation, diagnostic-accuracy evaluation, patient-safety validation, regulatory validation, or author-independent validation.

## What this repository reproduces

- **Cross-implementation consistency:** 80 locked scenarios, 40 for StrokeTwinMentor and 40 for LungTwinMentor, covering nominal, boundary, missing-evidence, conflicting-evidence, and explicit-unknown cases.
- **I1-I3 negative controls:** 30 deliberately corrupted execution records, 10 per invariant, used to verify that the trace checker flags the specified violations.
- **Personalization metamorphic testing:** 500 generated Lung states and 2,500 deterministic assertions covering formula consistency, source immutability, non-interference, baseline dependence, and missing-baseline suppression.
- **Seeded release-change study:** five controlled candidate releases containing 11 contract, rule, or personalization changes, with dependency-closure regression selection evaluated against the full 80-case reference corpus.
- **Dependency-completeness sensitivity:** controlled omission of behavior-relevant dependency links to expose the assumption that the declared dependency graph is complete.
- **NHANES external replay:** all 3,945 eligible adult baseline spirometry records and all 276 eligible paired pre/post FEV1 records from NHANES 2011-2012.

The manuscript also reports an internal development-conformance corpus of 505 contract mutation/order cases plus 49 clean controls and 198 rule-state cases. The original development harness for those internal campaigns was not part of the validation archive used to prepare this public package, so those two internal corpora are **not recreated here**. The public repository reproduces the post-freeze experiments listed above.

## Frozen target snapshots

The target artifacts are bundled directly in `targets/`, so the 80-case technical validation does not depend on cloning external repositories during execution.

| Target | Public source repository | Frozen commit |
|---|---|---|
| StrokeTwinMentor | https://github.com/francisco-diaz-barrancas/StrokeTwinMentor | `f5d1a040a3270310cdc2ebc8dd78765917859677` |
| LungTwinMentor | https://github.com/francisco-diaz-barrancas/LungTwinMentor | `8b9e284fe4fd98ef5304b56316d393e62918709b` |

The preflight step also verifies the exact runtime and embedded-artifact snapshots:

| Target | `methodology_runtime.js` SHA-256 | `artifacts_embed.js` SHA-256 |
|---|---|---|
| Stroke | `2b8d32bc159e9aca33c71dd55c5b25cdc70877afab1b93908ff55c876c8594c2` | `f609fcef44f946fa0030cd94d930615b248b288a433e4cbd6c6c6238425556b9` |
| Lung | `2b8d32bc159e9aca33c71dd55c5b25cdc70877afab1b93908ff55c876c8594c2` | `82deabd9d0f9d20d88373c25f97596fa56238e59903f039f1d0c7e84a1a8cf08` |

Artifact-internal identifiers such as `stroke-methodology-v1` and `lung-methodology-v1` are preserved because they are part of the frozen executable snapshots. They are implementation release identifiers and should not be interpreted as manuscript-version labels.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer
- Python dependencies listed in `requirements.txt`
- Internet access for automatic NHANES download, unless the official XPT files are supplied manually

## Quick start

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python -m pytest -q
python scripts/90_run_validation.py
```

The end-to-end command runs the preflight checks, cross-implementation evaluation, I1-I3 negative controls, personalization metamorphic checks, seeded release study, dependency-completeness sensitivity analysis, and NHANES replay pipeline.

Individual stages can also be executed through the provided `Makefile`:

```bash
make test
make preflight
make technical
make nhanes
make all
```

## Expected results

The clean package was executed end-to-end before archiving. The expected key results are:

| Experiment | Expected result |
|---|---:|
| Unit tests | `5 passed` |
| Cross-implementation consistency | `80/80` exact agreement |
| Rule-state subset | `23 true / 1 false / 13 unknown` |
| I1-I3 negative controls | `30/30` detected |
| Personalization metamorphic checks | `2,500/2,500` passed |
| Seeded release study | `11/11` observed changes retained |
| Selected tests per seeded release | `17, 10, 6, 4, 1` |
| Dependency recall with 0/1/2/3 omitted relevant links | `100% / 90.9% / 81.8% / 72.7%` |
| NHANES eligible baseline records | `3,945` |
| FEV1 admitted | `3,855/3,945 (97.7%)` |
| FVC admitted | `3,804/3,945 (96.4%)` |
| PEF admitted | `3,844/3,945 (97.4%)` |
| NHANES eligible paired FEV1 records | `276` |
| Numeric paired outputs | `274` |
| Numeric outputs within 0.001 percentage points | `274/274` |
| LU-S001 | `593 true / 3,352 unknown` |

The locked 80-case oracle has SHA-256:

```text
acc0ffca5d1939de97672792e51f3bc187c716361b439b9a2393dce22e91fda5
```

Compact machine-readable results and hashes are recorded in `RESULTS_MANIFEST.json` and `SUBMISSION_RELEASE_MANIFEST.json`.

## NHANES external biomedical-data replay

The LungTwinMentor external replay uses the public, de-identified **NHANES 2011-2012** datasets from the U.S. National Center for Health Statistics:

| File | Description | SHA-256 used in the submitted analysis |
|---|---|---|
| `SPX_G.XPT` | Spirometry — Pre and Post-Bronchodilator | `58177b07ad94a2c005b0c9494cddb82fc94ec8f5c6c13a91b83da035f20770d9` |
| `DEMO_G.XPT` | Demographic Variables and Sample Weights | `eaf0525d1952626885af3e935415a1f66ad62c18698080e7354789c125af252d` |

`scripts/10_download_nhanes.py` retrieves the official files from CDC/NCHS. The raw XPT files are not redistributed in this repository.

Baseline eligibility requires age ≥18 years, A/B baseline FEV1 quality, A/B baseline FVC quality, and available FEV1, FVC, and PEF. All eligible records are used; no sampling is applied. The paired FEV1 analysis additionally requires usable post-bronchodilator FEV1/FVC quality.

Unit conversions are performed as follows: FEV1/FVC values from mL to L and PEF from mL/s to L/min.

The frozen Lung prototype exercises these interface-derived bounds:

| Variable | Unit | Declared bound | Basis |
|---|---|---:|---|
| FEV1 | L | 0.3-5.0 | HTML range control |
| FVC | L | 0.5-6.0 | HTML range control |
| PEF | L/min | 80-750 | HTML range control |

The replay is a **specification stress test**, not a diagnostic or clinical-performance study. A rejected measurement indicates incompatibility with the declared prototype contract; it must not be interpreted as evidence of pathology.

## Repository structure

```text
.
├── config/                  # Study configuration and frozen target paths
├── data/
│   ├── oracle/              # Locked cross-implementation oracle and inventory
│   ├── runs/                # Compact technical results
│   └── external/            # Processed NHANES data and compact replay results
├── frozen_targets/lung/     # Minimal frozen Lung runtime used for full NHANES replay
├── node/                    # JavaScript runtime bridge
├── outputs/                 # Regenerable figures, tables, and macros
├── scripts/                 # Reproducible study steps and one-command pipeline
├── src/jbhi_validation/     # Python reference specification and analysis code
├── targets/                 # Frozen Stroke/Lung artifact snapshots
├── tests/                   # Unit tests
├── Makefile
├── requirements.txt
├── pyproject.toml
├── RESULTS_MANIFEST.json
├── SUBMISSION_RELEASE_MANIFEST.json
└── README.md
```

Large deterministic intermediates, including the full generated NHANES case JSONL and execution-output JSONL, are intentionally excluded. They are regenerated by the documented pipeline.

## Main result files

```text
data/oracle/oracle_locked.jsonl
data/oracle/oracle_manifest.json
data/runs/metrics.json
data/runs/invariant_negative_controls.json
data/runs/personalization_metamorphic.json
data/runs/release_evolution_study.json
data/runs/dependency_incompleteness_sensitivity.json
data/external/runs/external_metrics.json
data/external/runs/nhanes_context_analysis.json
outputs/figures/nhanes_rejection_by_age.pdf
```

## Scope and interpretation

The package supports claims about implementation conformance to a locked specification, cross-implementation agreement, detection of deliberately injected I1-I3 trace violations, deterministic properties of two implemented personalization mechanisms, dependency-closure behavior under controlled release changes, sensitivity to missing declared dependencies, and contract behavior on independently collected NHANES spirometry measurements.

It does **not** establish clinical correctness of the contracts or rules, diagnostic accuracy, prospective clinical effectiveness, patient safety, regulatory validation, superiority over FHIR/openEHR/CQL/PROV or a complete standards-based engineering stack, author-independent validation, production defect rates, developer-effort savings, or distributed/physical IoMT scalability.

The Python specification and JavaScript runtime are separate implementations, but the same research team authored the domain specification and the reported synthetic scenarios/oracles. The 80-case result should therefore be interpreted as a **cross-implementation consistency check**, not independent validation of the specification.

## Ethics and data use

NHANES data are public and de-identified. This repository performs secondary computational analysis and contains no direct identifiers.

No participant-level ECGTwinMentor data are included or re-analysed. The manuscript uses the previously published ECGTwinMentor evaluation only as contextual information for the retrospective mapping.

## Authors and contact

| Author | Affiliation |
|---|---|
| **Daniel Flores-Martin** | COMPUTAEX, Extremadura Supercomputing Center, Cáceres, Spain |
| **Francisco Díaz-Barrancas** | Universidad de Valladolid, Valladolid, Spain |
| **Pedro J. Pardo** | Universidad de Extremadura, Badajoz, Spain |
| **Javier Berrocal** | Universidad de Extremadura, Badajoz, Spain |
| **Juan M. Murillo** | Universidad de Extremadura, Badajoz, Spain |

**Corresponding author:** Daniel Flores-Martin  
**Email:** daniel.flores@computaex.es

For questions about the manuscript, reproducibility package, or execution of the validation pipeline, please contact the corresponding author.
