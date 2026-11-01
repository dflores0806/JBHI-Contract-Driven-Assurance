from __future__ import annotations
import json
from pathlib import Path
from .utils import ensure_repo_layout, git_commit, load_yaml, sha256_file, resolve_repo_path


def inspect_target(name: str, cfg: dict, expected: dict) -> dict:
    repo=resolve_repo_path(cfg["repo_path"])
    ensure_repo_layout(repo)
    release=json.loads((repo/"artifacts/release.json").read_text(encoding="utf-8"))
    contracts=json.loads((repo/"artifacts/contracts.json").read_text(encoding="utf-8"))["contracts"]
    rules=json.loads((repo/"artifacts/rules.json").read_text(encoding="utf-8"))["rules"]
    actual_commit=git_commit(repo)
    report={
        "target":name,"repo_path":str(cfg["repo_path"]),"release_id":release.get("release_id"),
        "contract_count":len(contracts),"rule_count":len(rules),"git_commit":actual_commit,
        "runtime_sha256":sha256_file(repo/"artifacts/methodology_runtime.js"),
        "embed_sha256":sha256_file(repo/"artifacts/artifacts_embed.js"),
    }
    report["checks"]={
        "release_id": report["release_id"]==expected["expected_release_id"],
        "contract_count": report["contract_count"]==expected["expected_contract_count"],
        "rule_count": report["rule_count"]==expected["expected_rule_count"],
        "git_commit": True if not cfg.get("expected_git_commit") else actual_commit==cfg.get("expected_git_commit"),
        "runtime_sha256": True if not expected.get("expected_runtime_sha256") else report["runtime_sha256"]==expected.get("expected_runtime_sha256"),
        "embed_sha256": True if not expected.get("expected_embed_sha256") else report["embed_sha256"]==expected.get("expected_embed_sha256"),
    }
    return report
