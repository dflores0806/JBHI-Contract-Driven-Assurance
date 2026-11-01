from __future__ import annotations
import datetime as dt
from pathlib import Path
from .utils import canonical_json, dump_json, sha256_file


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:
        for r in rows:
            f.write(canonical_json(r)+"\n")


def seal_oracle(path: Path, study_id: str, generator_version: str="1.0.0") -> dict:
    manifest={
        "study_id":study_id,
        "oracle_file":path.name,
        "oracle_sha256":sha256_file(path),
        "case_count":sum(1 for _ in open(path,"r",encoding="utf-8")),
        "generator_version":generator_version,
        "sealed_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "statement":"Oracle frozen before target execution; editing invalidates this manifest hash."
    }
    dump_json(path.with_name("oracle_manifest.json"),manifest)
    return manifest
