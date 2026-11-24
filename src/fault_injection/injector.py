"""Publish deterministic F1/F2/F3 markers and wait for supervisor SIGKILL."""
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


class DriverKillInjector:
    """Inject at one frozen side-effect/checkpoint boundary in attempt one."""

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
        if self.plan.fault_point != "F1" or not self.plan.enabled:
            return False
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
        return self._publish_and_wait(
            batch_id=batch_id, record_index=record_index, recording_id=recording_id,
            object_uri=object_uri, object_key=object_key,
            metadata_rows_committed=metadata_rows_committed,
            stage="after_object_put_before_metadata_commit",
        )

    def after_metadata_commit(self, *, batch_id: int, record_index: int,
                              recording_id: str, object_uri: str, object_key: str,
                              metadata_rows_committed: int) -> bool:
        """F2: stop after the last row in a target batch commits, before callback return."""
        if self.plan.fault_point != "F2" or not self.plan.enabled:
            return False
        if (batch_id, record_index) != (self.plan.batch_id, self.plan.record_index):
            return False
        if record_index != 10 or metadata_rows_committed != 10:
            raise RuntimeError("F2 requires all ten target-batch metadata rows committed")
        return self._publish_and_wait(
            batch_id=batch_id, record_index=record_index, recording_id=recording_id,
            object_uri=object_uri, object_key=object_key,
            metadata_rows_committed=metadata_rows_committed,
            stage="after_metadata_commit_before_checkpoint_commit",
        )

    def after_checkpoint_commit(self, *, batch_id: int, record_index: int,
                                recording_id: str, object_uri: str, object_key: str,
                                metadata_rows_committed: int,
                                checkpoint_commit_confirmed: bool) -> bool:
        """F3: stop after Spark has durably recorded the target batch commit."""
        if self.plan.fault_point != "F3" or not self.plan.enabled:
            return False
        if (batch_id, record_index) != (self.plan.batch_id, self.plan.record_index):
            return False
        if not checkpoint_commit_confirmed:
            raise RuntimeError("F3 target reached without a confirmed Spark checkpoint commit")
        if record_index != 10 or metadata_rows_committed != 10:
            raise RuntimeError("F3 requires the complete ten-record target batch")
        return self._publish_and_wait(
            batch_id=batch_id, record_index=record_index, recording_id=recording_id,
            object_uri=object_uri, object_key=object_key,
            metadata_rows_committed=metadata_rows_committed,
            stage="after_spark_checkpoint_commit_before_next_event_publication",
        )

    def _publish_and_wait(self, *, batch_id: int, record_index: int,
                          recording_id: str, object_uri: str, object_key: str,
                          metadata_rows_committed: int, stage: str) -> bool:
        if self.triggered:
            raise RuntimeError(f"{self.plan.fault_point} injector was already triggered")
        self.signal_dir.mkdir(parents=True, exist_ok=True)
        marker = self.signal_dir / f"{self.run_id}.kill"
        temporary = self.signal_dir / f".{self.run_id}.kill.tmp"
        if marker.exists() or temporary.exists():
            raise FileExistsError(f"stale fault marker exists for run {self.run_id}")
        target_template = self.plan.target
        if not target_template:
            raise ValueError(f"{self.plan.fault_point} plan has no target")
        target = target_template.format(run_id=self.run_id)
        event = {
            "target": target, "fault_point": self.plan.fault_point,
            "batch_id": batch_id, "run_id": self.run_id,
            "treatment": self.treatment, "record_index": record_index,
            "stage": stage, "method": self.plan.method,
            "recording_id": recording_id, "object_uri": object_uri,
            "object_key": object_key,
            "metadata_rows_committed": metadata_rows_committed,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        LOGGER.info(
            "FAULT_BOUNDARY_REACHED fault_point=%s batch_id=%d record_index=%d "
            "stage=%s object_key=%s metadata_rows_committed=%d target=%s",
            self.plan.fault_point, batch_id, record_index, stage, object_key,
            metadata_rows_committed, target,
        )
        # kill_on_marker.sh reads target from the first key=value line.
        marker_text = "\n".join(f"{key}={value}" for key, value in event.items()) + "\n"
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(marker_text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, marker)
        self.triggered = True
        LOGGER.info("FAULT_MARKER_WRITTEN path=%s marker=%s", marker,
                    json.dumps(event, sort_keys=True, separators=(",", ":")))
        self.wait_for_kill()
        raise RuntimeError(f"{self.plan.fault_point} wait returned without supervisor SIGKILL")


# Preserve imports used by the F1 snapshot-era code and existing local checks.
F1DriverKillInjector = DriverKillInjector
