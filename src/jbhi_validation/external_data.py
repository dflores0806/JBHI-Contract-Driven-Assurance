from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests


NHANES_SPX_G_URLS = [
    "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/SPX_G.xpt",
    "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/SPX_G.XPT",
]
NHANES_DEMO_G_URLS = [
    "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/DEMO_G.xpt",
    "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/DEMO_G.XPT",
]


def _decode(v: Any) -> Any:
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="replace").strip()
    if isinstance(v, str):
        return v.strip()
    return v


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_xport_file(path: Path) -> bool:
    """Return True only when *path* has a SAS XPORT library header.

    NHANES endpoints may return an HTML error/interstitial page with HTTP 200.
    Checking only the file size is therefore insufficient.
    """
    try:
        if not path.exists() or path.stat().st_size < 80:
            return False
        head = path.read_bytes()[:160]
    except OSError:
        return False
    upper = head.upper()
    return b"HEADER RECORD" in upper and b"LIBRARY HEADER RECORD" in upper


def _file_preview(path: Path, n: int = 120) -> str:
    try:
        b = path.read_bytes()[:n]
        return b.decode("utf-8", errors="replace").replace("\r", " ").replace("\n", " ")
    except OSError:
        return "<unreadable>"


def _download_nhanes_file(dest: Path, urls: list[str], label: str, force: bool = False, timeout: int = 120) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Reuse only a file that is actually SAS XPORT.  Older project versions
    # could leave an HTML page at this path; those files are replaced here.
    if dest.exists() and not force and _is_xport_file(dest):
        return {"path": str(dest), "sha256": sha256_file(dest), "downloaded": False, "validated_xport": True}

    if dest.exists() and not _is_xport_file(dest):
        # Keep a forensic copy rather than silently deleting the bad response.
        bad = dest.with_suffix(dest.suffix + ".invalid")
        try:
            if bad.exists():
                bad.unlink()
            dest.replace(bad)
        except OSError:
            pass

    errors = []
    for url in urls:
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            if tmp.exists():
                tmp.unlink()
            with requests.get(
                url, stream=True, timeout=timeout, allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (JBHI reproducibility study; NHANES public data)"},
            ) as r:
                r.raise_for_status()
                ctype = (r.headers.get("content-type") or "").lower()
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

            if tmp.stat().st_size < 10_000:
                raise RuntimeError(
                    f"downloaded file is unexpectedly small ({tmp.stat().st_size} bytes; content-type={ctype})"
                )
            if not _is_xport_file(tmp):
                preview = _file_preview(tmp)
                raise RuntimeError(
                    f"response is not a SAS XPORT file (content-type={ctype}; first bytes={preview!r})"
                )

            tmp.replace(dest)
            return {
                "path": str(dest), "sha256": sha256_file(dest), "downloaded": True,
                "url": url, "validated_xport": True,
            }
        except Exception as e:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            errors.append(f"{url}: {e}")

    raise RuntimeError(
        f"Could not download NHANES {label} automatically. Download it manually from the official CDC/NHANES 2011-2012 data page and place it at {dest}. Attempts:\n"
        + "\n".join(errors)
    )


def download_nhanes_spx_g(dest: Path, force: bool = False, timeout: int = 120) -> dict[str, Any]:
    """Download the official NHANES 2011-2012 spirometry XPT file."""
    return _download_nhanes_file(dest, NHANES_SPX_G_URLS, "SPX_G.XPT", force=force, timeout=timeout)


def download_nhanes_demo_g(dest: Path, force: bool = False, timeout: int = 120) -> dict[str, Any]:
    """Download NHANES 2011-2012 demographics so the external replay can be restricted to adults."""
    return _download_nhanes_file(dest, NHANES_DEMO_G_URLS, "DEMO_G.XPT", force=force, timeout=timeout)


def load_nhanes_spirometry(xpt_path: Path) -> pd.DataFrame:
    if not _is_xport_file(xpt_path):
        raise ValueError(
            f"{xpt_path} is not a valid SAS XPORT file. "
            "It is probably an HTML response left by an older downloader. "
            "Run: python scripts/10_download_nhanes.py --force"
        )
    df = pd.read_sas(xpt_path, format="xport")
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(_decode)
    return df


def load_nhanes_demographics(xpt_path: Path) -> pd.DataFrame:
    if not _is_xport_file(xpt_path):
        raise ValueError(
            f"{xpt_path} is not a valid SAS XPORT file. "
            "It is probably an HTML response left by an older downloader. "
            "Run: python scripts/10_download_nhanes.py --force"
        )
    df = pd.read_sas(xpt_path, format="xport")
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(_decode)
    return df


def prepare_nhanes_frames(df: pd.DataFrame, demographics: pd.DataFrame | None = None, adult_min_age: int = 18) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = ["SEQN", "SPXNFVC", "SPXNFEV1", "SPXNPEF", "SPXNQFVC", "SPXNQFV1", "SPDBRONC"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"NHANES file is missing expected columns: {missing}")

    merged = df.copy()
    if demographics is not None:
        demo_required = ["SEQN", "RIDAGEYR"]
        demo_missing = [c for c in demo_required if c not in demographics.columns]
        if demo_missing:
            raise KeyError(f"NHANES demographics file is missing expected columns: {demo_missing}")
        demo = demographics[demo_required].copy()
        merged = merged.merge(demo, on="SEQN", how="left", validate="many_to_one")
        merged = merged[pd.to_numeric(merged["RIDAGEYR"], errors="coerce") >= adult_min_age].copy()
        merged["age_years"] = pd.to_numeric(merged["RIDAGEYR"], errors="coerce").astype(int)

    base = merged.copy()
    base["SPXNQFVC"] = base["SPXNQFVC"].map(_decode)
    base["SPXNQFV1"] = base["SPXNQFV1"].map(_decode)
    q = base["SPXNQFVC"].isin(["A", "B"]) & base["SPXNQFV1"].isin(["A", "B"])
    q &= base["SPXNFEV1"].notna() & base["SPXNFVC"].notna() & base["SPXNPEF"].notna()
    q &= base["SPXNFVC"] > 0
    base_cols = ["SEQN", "SPXNFEV1", "SPXNFVC", "SPXNPEF", "SPXNQFVC", "SPXNQFV1", "SPDBRONC"]
    if "age_years" in base.columns:
        base_cols.append("age_years")
    base = base.loc[q, base_cols].copy()
    base["fev1_l"] = base["SPXNFEV1"].astype(float) / 1000.0
    base["fvc_l"] = base["SPXNFVC"].astype(float) / 1000.0
    base["pef_l_min"] = base["SPXNPEF"].astype(float) * 0.06
    base["fev1_fvc_ratio"] = base["SPXNFEV1"].astype(float) / base["SPXNFVC"].astype(float)
    base["nhanes_bronchodilator_eligible"] = base["SPDBRONC"].eq(1)
    base["ratio_band"] = pd.cut(
        base["fev1_fvc_ratio"], bins=[-np.inf, 0.70, 0.80, np.inf],
        labels=["lt_0_70", "0_70_to_0_80", "ge_0_80"], right=False,
    ).astype(str)

    post_required = ["SPXBFEV1", "SPXBQFV1", "SPXBQFVC"]
    if not all(c in df.columns for c in post_required):
        paired = pd.DataFrame(columns=list(base.columns) + ["post_fev1_l", "fev1_percent_change"])
        return base.reset_index(drop=True), paired

    p = merged.copy()
    p["SPXNQFVC"] = p["SPXNQFVC"].map(_decode)
    p["SPXNQFV1"] = p["SPXNQFV1"].map(_decode)
    p["SPXBQFVC"] = p["SPXBQFVC"].map(_decode)
    p["SPXBQFV1"] = p["SPXBQFV1"].map(_decode)
    pq = (
        p["SPXNQFVC"].isin(["A", "B"]) & p["SPXNQFV1"].isin(["A", "B"]) &
        p["SPXBQFVC"].isin(["A", "B"]) & p["SPXBQFV1"].isin(["A", "B"]) &
        p["SPXNFEV1"].notna() & p["SPXBFEV1"].notna() & (p["SPXNFEV1"] > 0)
    )
    pair_cols = ["SEQN", "SPXNFEV1", "SPXBFEV1", "SPXNQFV1", "SPXBQFV1"]
    if "age_years" in p.columns:
        pair_cols.append("age_years")
    paired = p.loc[pq, pair_cols].copy()
    paired["baseline_fev1_l"] = paired["SPXNFEV1"].astype(float) / 1000.0
    paired["post_fev1_l"] = paired["SPXBFEV1"].astype(float) / 1000.0
    paired["fev1_percent_change"] = ((paired["post_fev1_l"] - paired["baseline_fev1_l"]) / paired["baseline_fev1_l"]) * 100.0
    return base.reset_index(drop=True), paired.reset_index(drop=True)


def deterministic_stratified_sample(df: pd.DataFrame, n: int, seed: int, strata_col: str) -> pd.DataFrame:
    if n <= 0 or len(df) <= n:
        return df.sort_values([strata_col, "SEQN"]).reset_index(drop=True)
    groups = list(df.groupby(strata_col, dropna=False))
    if not groups:
        return df.sample(n=n, random_state=seed).sort_values("SEQN").reset_index(drop=True)
    per = n // len(groups)
    pieces = []
    chosen = set()
    for i, (_, g) in enumerate(groups):
        take = min(per, len(g))
        if take:
            s = g.sample(n=take, random_state=seed + i)
            pieces.append(s)
            chosen.update(s.index.tolist())
    current = sum(len(x) for x in pieces)
    if current < n:
        remain = df.loc[~df.index.isin(chosen)]
        extra = remain.sample(n=min(n-current, len(remain)), random_state=seed + 1000)
        pieces.append(extra)
    out = pd.concat(pieces, ignore_index=False)
    return out.sort_values([strata_col, "SEQN"]).reset_index(drop=True)


def deterministic_sample(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    if n <= 0 or len(df) <= n:
        return df.sort_values("SEQN").reset_index(drop=True)
    return df.sample(n=n, random_state=seed).sort_values("SEQN").reset_index(drop=True)


def lung_external_cases(base_sample: pd.DataFrame, paired_sample: pd.DataFrame) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    t0 = "2026-01-15T10:00:00Z"
    for _, r in base_sample.iterrows():
        seq = int(r.SEQN)
        cases.append({
            "case_id": f"NHANES-B-{seq}",
            "twin": "lung",
            "external_source": "NHANES_2011_2012_SPX_G",
            "external_kind": "baseline_spirometry",
            "source_record_id": str(seq),
            "reference": {
                "fev1_l": float(r.fev1_l),
                "fvc_l": float(r.fvc_l),
                "pef_l_min": float(r.pef_l_min),
                "fev1_fvc_ratio": float(r.fev1_fvc_ratio),
                "nhanes_bronchodilator_eligible": bool(r.nhanes_bronchodilator_eligible),
                "ratio_band": str(r.ratio_band),
                "age_years": int(r.age_years) if "age_years" in r.index and pd.notna(r.age_years) else None,
            },
            "steps": [
                {"op":"reset","state":{}},
                {"op":"submit_observation","observation":{"event_id":f"{seq}-fev1","contract_id":"fev1","value":round(float(r.fev1_l),6),"unit":"L","source":"case_database","acquisition_time":t0}},
                {"op":"submit_observation","observation":{"event_id":f"{seq}-fvc","contract_id":"fvc","value":round(float(r.fvc_l),6),"unit":"L","source":"case_database","acquisition_time":t0}},
                {"op":"submit_observation","observation":{"event_id":f"{seq}-pef","contract_id":"peak_expiratory_flow","value":int(round(float(r.pef_l_min))),"unit":"L/min","source":"case_database","acquisition_time":t0}},
                {"op":"evaluate_rules","context":{"fev1_fvc_ratio":round(float(r.fev1_fvc_ratio),8),"peak_expiratory_flow":round(float(r.pef_l_min),6)}},
            ],
        })
    for _, r in paired_sample.iterrows():
        seq = int(r.SEQN)
        expected = float(r.fev1_percent_change)
        cases.append({
            "case_id": f"NHANES-P-{seq}",
            "twin": "lung",
            "external_source": "NHANES_2011_2012_SPX_G",
            "external_kind": "pre_post_bronchodilator_personalization",
            "source_record_id": str(seq),
            "reference": {
                "baseline_fev1_l": float(r.baseline_fev1_l),
                "post_fev1_l": float(r.post_fev1_l),
                "fev1_percent_change": expected,
                "age_years": int(r.age_years) if "age_years" in r.index and pd.notna(r.age_years) else None,
            },
            "steps": [
                {"op":"reset","state":{}},
                {"op":"submit_observation","observation":{"event_id":f"{seq}-basefev1","contract_id":"baseline_fev1","value":round(float(r.baseline_fev1_l),6),"unit":"L","source":"user_interaction","acquisition_time":t0}},
                {"op":"submit_observation","observation":{"event_id":f"{seq}-postfev1","contract_id":"fev1","value":round(float(r.post_fev1_l),6),"unit":"L","source":"user_interaction","acquisition_time":"2026-01-15T10:10:00Z"}},
                {"op":"snapshot"},
            ],
        })
    return cases
