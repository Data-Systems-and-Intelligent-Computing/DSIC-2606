"""Load and validate the frozen fault-injection plan for an experiment run."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import yaml

@dataclass(frozen=True)
class FaultPlan:
    fault_point: str
    enabled: bool
    batch_id: int | None = None
    record_index: int | None = None
    stage: str | None = None
    target: str | None = None
    method: str | None = None
    rationale: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

def load_fault_plan(path: Path, expected_fault_point: str) -> FaultPlan:
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict) or not isinstance(document.get("fault_plan"), dict):
        raise ValueError(f"fault plan must contain a fault_plan mapping: {path}")
    raw = document["fault_plan"]
    point, enabled = raw.get("fault_point"), raw.get("enabled")
    if point != expected_fault_point:
        raise ValueError(f"fault plan is for {point!r}, expected {expected_fault_point!r}")
    if not isinstance(enabled, bool):
        raise ValueError("fault_plan.enabled must be boolean")
    if point == "F0":
        if enabled:
            raise ValueError("F0 must not inject a failure")
        return FaultPlan(fault_point="F0", enabled=False)
    stages = {
        "F1": "after_object_put_before_metadata_commit",
        "F2": "after_metadata_commit_before_checkpoint_commit",
        "F3": "after_spark_checkpoint_commit_before_next_event_publication",
    }
    if point not in stages:
        raise ValueError(f"unsupported fault point: {point!r}")
    if not enabled:
        raise ValueError(f"{point} plan must be enabled")
    try:
        batch_id, record_index = int(raw["batch_id"]), int(raw["record_index"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{point} requires integer batch_id and record_index") from exc
    if batch_id < 0:
        raise ValueError(f"{point} batch_id must be non-negative")
    if not 1 <= record_index <= 10:
        raise ValueError(f"{point} record_index must be between 1 and 10")
    if point in {"F2", "F3"} and record_index != 10:
        raise ValueError(f"{point} targets the end of the ten-record micro-batch (record_index=10)")
    if raw.get("stage") != stages[point]:
        raise ValueError(f"{point} stage must be {stages[point]}")
    if raw.get("target") != "drv-{run_id}-a1":
        raise ValueError(f"{point} target must be drv-{run_id}-a1")
    if raw.get("method") != "sigkill_on_marker":
        raise ValueError(f"{point} method must be sigkill_on_marker")
    rationale = raw.get("rationale")
    if not isinstance(rationale, str) or len(rationale.strip()) < 20:
        raise ValueError(f"{point} rationale must explain the frozen position")
    return FaultPlan(
        fault_point=point, enabled=True, batch_id=batch_id,
        record_index=record_index, stage=str(raw["stage"]),
        target=str(raw["target"]), method=str(raw["method"]),
        rationale=rationale.strip(),
    )
