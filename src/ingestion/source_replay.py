"""Publish frozen replay events to the shared Spark landing directory.

The driver calls :meth:`ReplayFeeder.publish_initial` before starting the
stream. After a micro-batch has completed successfully, it calls
:meth:`ReplayFeeder.after_batch_completed` with that event's ``batch_id``.
Only then is the next event made visible to the file stream.

On restart, the files already present in the persistent landing directory are
left in place. The feeder finds the highest contiguous published batch and
waits for Spark to complete it before publishing the next one. B0 and B1 use
the same feeder; their checkpoint paths determine which existing files Spark
considers already processed.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence


DEFAULT_EVENT_SOURCE = Path("/workspace/data/replay/main/events")
_EVENT_NAME = re.compile(r"^event-(\d{3,})\.json$")
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_RECORDINGS_PER_EVENT = 10


@dataclass(frozen=True)
class ReplayEvent:
    """A validated frozen event file."""

    batch_id: int
    path: Path
    content: bytes


class ReplayFeeder:
    """Stage one event at a time in the landing directory used by Spark."""

    def __init__(
        self,
        landing_root: Path,
        run_id: str,
        event_source: Path = DEFAULT_EVENT_SOURCE,
    ) -> None:
        if not _RUN_ID.fullmatch(run_id):
            raise ValueError("RUN_ID contains characters unsafe for a directory name")

        self.landing_root = Path(landing_root)
        self.run_id = run_id
        self.event_source = Path(event_source)
        self.landing = self.landing_root / run_id
        # This sibling directory is on the same mounted filesystem as landing,
        # but is outside the directory Spark watches.
        self.staging = self.landing_root / ".staging" / run_id

    @classmethod
    def from_environment(cls) -> "ReplayFeeder":
        """Build the feeder using the lab-provided landing root and run ID."""
        try:
            landing_root = Path(os.environ["REPLAY_LANDING_ROOT"])
            run_id = os.environ["RUN_ID"]
        except KeyError as exc:
            raise ValueError(f"required environment variable is missing: {exc.args[0]}") from exc
        return cls(landing_root=landing_root, run_id=run_id)

    def publish_initial(self) -> ReplayEvent:
        """Publish event 0 for a new run, or preserve existing landing on restart."""
        source_events = self._source_events()
        existing = self._landing_events(source_events)
        if existing:
            # Do not stage k+1 yet: Spark must first recover/process the
            # already-published events. The completion callback does that.
            return existing[-1]
        if not source_events:
            raise ValueError(f"no event-*.json files found in {self.event_source}")
        return self._publish(source_events[0])

    def after_batch_completed(self, completed_batch_id: int) -> Optional[ReplayEvent]:
        """Publish the next event only after the latest staged batch completes.

        Call this only after all work for the event has succeeded (including
        its object PUT and Iceberg commit). On F2, an exception before this
        call leaves the event files intact for the replacement driver.
        """
        source_events = self._source_events()
        existing = self._landing_events(source_events)
        if not existing:
            raise RuntimeError("landing is empty; call publish_initial() first")

        latest_staged = existing[-1].batch_id
        if completed_batch_id != latest_staged:
            # Existing older events may be replayed after a driver restart.
            # They must not cause the feeder to publish ahead of the last
            # event that was already in landing.
            return None

        next_batch_id = latest_staged + 1
        if next_batch_id >= len(source_events):
            return None
        return self._publish(source_events[next_batch_id])

    def _source_events(self) -> List[ReplayEvent]:
        if not self.event_source.is_dir():
            raise FileNotFoundError(f"event source directory not found: {self.event_source}")

        indexed = []
        for path in self.event_source.iterdir():
            match = _EVENT_NAME.fullmatch(path.name)
            if match and path.is_file():
                indexed.append((int(match.group(1)), path))
        indexed.sort(key=lambda item: item[0])

        events = []
        for expected_id, (batch_id, path) in enumerate(indexed):
            if batch_id != expected_id:
                raise ValueError(
                    f"source event IDs must be contiguous from 0; expected "
                    f"{expected_id}, found {batch_id} ({path.name})"
                )
            content = path.read_bytes()
            self._validate_event(batch_id, content, path)
            events.append(ReplayEvent(batch_id=batch_id, path=path, content=content))
        return events

    def _landing_events(self, source_events: Sequence[ReplayEvent]) -> List[ReplayEvent]:
        if not self.landing.exists():
            return []
        if not self.landing.is_dir():
            raise NotADirectoryError(f"landing path is not a directory: {self.landing}")

        indexed = []
        for path in self.landing.iterdir():
            if path.name.startswith((".", "_")):
                continue
            if path.suffix == ".json":
                match = _EVENT_NAME.fullmatch(path.name)
                if not match or not path.is_file():
                    raise ValueError(f"unexpected visible JSON in landing: {path.name}")
                indexed.append((int(match.group(1)), path))
        indexed.sort(key=lambda item: item[0])

        existing = []
        for expected_id, (batch_id, path) in enumerate(indexed):
            if batch_id != expected_id:
                raise ValueError(
                    f"landing event IDs must be contiguous from 0; expected "
                    f"{expected_id}, found {batch_id} ({path.name})"
                )
            if batch_id >= len(source_events):
                raise ValueError(f"landing has event absent from source: {path.name}")
            content = path.read_bytes()
            if content != source_events[batch_id].content:
                raise ValueError(f"landing event differs from frozen source: {path.name}")
            existing.append(ReplayEvent(batch_id=batch_id, path=path, content=content))
        return existing

    @staticmethod
    def _validate_event(batch_id: int, content: bytes, path: Path) -> None:
        try:
            payload = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid JSON event: {path}") from exc

        if not isinstance(payload, dict) or payload.get("batch_id") != batch_id:
            raise ValueError(f"batch_id does not match event filename: {path.name}")
        recording_ids = payload.get("recording_ids")
        if (
            not isinstance(recording_ids, list)
            or len(recording_ids) != _RECORDINGS_PER_EVENT
            or any(not isinstance(value, str) or not value for value in recording_ids)
            or len(set(recording_ids)) != _RECORDINGS_PER_EVENT
        ):
            raise ValueError(
                f"event must contain {_RECORDINGS_PER_EVENT} unique recording_ids: {path.name}"
            )

    def _publish(self, event: ReplayEvent) -> ReplayEvent:
        self.landing_root.mkdir(parents=True, exist_ok=True)
        self.landing.mkdir(parents=True, exist_ok=True)
        self.staging.mkdir(parents=True, exist_ok=True)

        if os.stat(self.staging).st_dev != os.stat(self.landing).st_dev:
            raise OSError("staging and landing must be on the same filesystem for atomic replace")

        destination = self.landing / event.path.name
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite staged event: {destination}")

        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=".event-", suffix=".tmp", dir=str(self.staging)
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "wb") as stream:
                stream.write(event.content)
                stream.flush()
                os.fsync(stream.fileno())
            # Spark's worker needs read permission; the lab containers use a
            # shared read-only mount for the worker.
            temporary_path.chmod(0o644)
            os.replace(temporary_path, destination)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        return ReplayEvent(batch_id=event.batch_id, path=destination, content=event.content)
