"""Deterministic F1 marker publication and wait-for-supervisor hook."""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Callable
from src.fault_injection.fault_plan import FaultPlan

LOGGER = logging.getLogger("dsic.fault_injection")

class F1DriverKillInjector:
    def __init__(self, plan: FaultPlan, run_id: str, treatment: str, signal_dir: Path,
                 wait_for_kill: Callable[[], None] | None = None):
        self.plan = plan
        self.run_id = run_id
        self.treatment = treatment
        self.signal_dir = Path(signal_dir)
        self.wait_for_kill = wait_for_kill or self._wait_forever
        self.triggered = False

    @staticmethod
    def _wait_forever() -> None:
        threading.Event().wait()

    def after_object_put(self, *, batch_id: int, record_index: int,
                         recording_id: str, object_uri: str, object_key: str,
                         metadata_rows_committed: int, put_confirmed: bool) -> bool:
        """Publish one atomic signal and block only at the frozen successful-PUT boundary."""
        if not self.plan.enabled:
            return False
        if self.triggered:
            raise RuntimeError("F1 injector was already triggered")
        if (batch_id, record_index) != (self.plan.batch_id, self.plan.record_index):
            return False
        if not put_confirmed:
            raise RuntimeError("F1 target reached without a newly confirmed object PUT")
        expected_prior = record_index - 1
        if metadata_rows_committed != expected_prior:
            raise RuntimeError(
                f"F1 expected {expected_prior} prior metadata commits in batch, "
                f"found {metadata_rows_committed}"
            )
        self.signal_dir.mkdir(parents=True, exist_ok=True)
        marker = self.signal_dir / f"{self.run_id}.kill"
        temporary = self.signal_dir / f".{self.run_id}.kill.tmp"
        if marker.exists() or temporary.exists():
            raise FileExistsError(f"stale F1 marker exists for run {self.run_id}")
        target = self.plan.target.format(run_id=self.run_id)
        event = {
            "run_id": self.run_id, "treatment": self.treatment,
            "target": target, "fault_point": "F1", "batch_id": batch_id,
            "record_index": record_index, "stage": self.plan.stage,
            "method": self.plan.method, "recording_id": recording_id,
            "object_uri": object_uri, "object_key": object_key,
            "metadata_rows_committed": metadata_rows_committed,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        LOGGER.info(
            "FAULT_BOUNDARY_REACHED batch_id=%d record_index=%d stage=%s "
            "object_key=%s metadata_rows_committed=%d target=%s",
            batch_id, record_index, self.plan.stage, object_key,
            metadata_rows_committed, target,
        )
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(event, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, marker)
        self.triggered = True
        LOGGER.info("FAULT_MARKER_WRITTEN path=%s marker=%s", marker,
                    json.dumps(event, sort_keys=True, separators=(",", ":")))
        self.wait_for_kill()
        raise RuntimeError("F1 wait returned without supervisor SIGKILL")
