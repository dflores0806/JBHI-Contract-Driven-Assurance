from __future__ import annotations
from typing import Any

NON_ADMITTED = {"rejected", "missing", "expired"}

def check_i1(result: dict[str, Any]) -> bool:
    """Rejected/unresolved observations must not modify active state or revision."""
    last_revision = None
    for step in result.get("steps", []):
        rev = step.get("state_revision")
        if step.get("op") == "reset":
            last_revision = rev
            continue
        if step.get("op") == "submit_observation":
            status = step.get("observation_status")
            if status in NON_ADMITTED:
                if step.get("state_effect") == "active_state_updated":
                    return False
                if last_revision is not None and rev is not None and rev != last_revision:
                    return False
            if rev is not None:
                last_revision = rev
        elif rev is not None:
            last_revision = rev
    return True

def check_i2(result: dict[str, Any]) -> bool:
    """Every executed/recorded artifact trace must resolve to the active release."""
    active = result.get("release_id")
    if not active:
        return False
    for step in result.get("steps", []):
        sid = step.get("release_id")
        if sid is not None and sid != active:
            return False
        tr = step.get("trace")
        if isinstance(tr, dict) and tr.get("release_id") is not None and tr.get("release_id") != active:
            return False
    for tr in result.get("trace_history", []):
        if tr.get("release_id") != active:
            return False
    return True

def check_i3(result: dict[str, Any]) -> bool:
    """Decision/rule outputs must bind to the active release and current state revision."""
    active = result.get("release_id")
    current_revision = None
    checked = 0
    for step in result.get("steps", []):
        op = step.get("op")
        if op in {"reset", "submit_observation", "commit_decision"} and step.get("state_revision") is not None:
            current_revision = step.get("state_revision")
        if op in {"evaluate_rules", "commit_decision"}:
            checked += 1
            if step.get("release_id") != active:
                return False
            if step.get("state_revision") is None:
                return False
            if current_revision is not None and step.get("state_revision") != current_revision:
                return False
            tr = step.get("trace")
            if op == "commit_decision" and isinstance(tr, dict):
                if tr.get("release_id") != active or tr.get("state_revision") != step.get("state_revision"):
                    return False
    return True if checked >= 0 else False

def evaluate_invariants(result: dict[str, Any]) -> dict[str, bool]:
    return {"I1": check_i1(result), "I2": check_i2(result), "I3": check_i3(result)}
