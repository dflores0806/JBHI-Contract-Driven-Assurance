from __future__ import annotations
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path | str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_json(path: Path | str, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit(repo: Path) -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return p.stdout.strip()
    except Exception:
        return None


def ensure_repo_layout(repo: Path) -> None:
    needed = [
        repo / "artifacts" / "artifacts_embed.js",
        repo / "artifacts" / "methodology_runtime.js",
        repo / "artifacts" / "release.json",
        repo / "artifacts" / "contracts.json",
        repo / "artifacts" / "rules.json",
        repo / "artifacts" / "personalization.json",
    ]
    missing = [str(p) for p in needed if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing target files:\n" + "\n".join(missing))


def nested_get(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            i = int(part)
            cur = cur[i] if 0 <= i < len(cur) else None
        else:
            return None
    return cur


def resolve_repo_path(value: str) -> Path:
    p=Path(value).expanduser()
    if not p.is_absolute():
        p=ROOT/p
    return p.resolve()
