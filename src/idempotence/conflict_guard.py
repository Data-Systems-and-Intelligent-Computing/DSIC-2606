"""Shared explicit errors for idempotent sink guards."""


class IdempotenceConflictError(RuntimeError):
    """An existing object or metadata row disagrees with the frozen manifest."""


class DuplicateRecordingError(ValueError):
    """One replay event or metadata source contains a recording ID more than once."""


def require_unique_recording_ids(records):
    seen = set()
    duplicates = set()
    for record in records:
        recording_id = str(record.get("recording_id", "")).strip()
        if not recording_id:
            raise ValueError("recording_id must be non-empty")
        if recording_id in seen:
            duplicates.add(recording_id)
        seen.add(recording_id)
    if duplicates:
        raise DuplicateRecordingError(
            "duplicate recording_id in one source batch: " + ", ".join(sorted(duplicates))
        )
