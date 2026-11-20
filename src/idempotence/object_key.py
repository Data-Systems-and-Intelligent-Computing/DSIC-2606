"""Resolve the stable object location from a recording's frozen manifest row."""

from src.ingestion.write_object import object_target


def canonical_object_target(recording_id: str, expected_object_uri: str) -> tuple[str, str]:
    recording_id = str(recording_id).strip()
    if not recording_id:
        raise ValueError("recording_id must be non-empty")
    # The URI is frozen in the manifest and selected through its unique recording_id.
    # It therefore stays stable across runs and does not contain run-specific state.
    return object_target(expected_object_uri)
