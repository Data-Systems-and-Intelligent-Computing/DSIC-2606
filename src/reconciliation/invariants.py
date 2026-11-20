"""Pure correctness checks for frozen expected and observed metadata IDs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def normalize_object_uri(value: object) -> str | None:
    """Normalize s3/s3a object URIs while preserving bucket and key exactly."""
    text = _clean(value)
    if not text:
        return None
    parsed = urlsplit(text)
    if parsed.scheme.lower() not in {"s3", "s3a"} or not parsed.netloc:
        return None
    if parsed.query or parsed.fragment:
        return None
    # Remove only the URI separator; preserve any leading slash that belongs
    # to the actual S3 key so keys are never silently collapsed.
    key = parsed.path[1:] if parsed.path.startswith("/") else parsed.path
    if not key or "\\x00" in key:
        return None
    return f"s3://{parsed.netloc}/{key}"


def reconcile_i1_i2(expected_ids: Iterable[object], actual_ids: Iterable[object]) -> dict:
    """Evaluate I1 completeness and I2 uniqueness for metadata recording IDs."""
    expected_values = [_clean(value) for value in expected_ids]
    if any(not value for value in expected_values):
        raise ValueError("expected metadata contains an empty recording_id")
    expected_counts = Counter(expected_values)
    duplicate_expected = sorted(rid for rid, count in expected_counts.items() if count > 1)
    if duplicate_expected:
        raise ValueError(f"expected metadata has duplicate recording_id values: {duplicate_expected[:5]}")
    expected = set(expected_values)
    if not expected:
        raise ValueError("expected metadata must contain at least one recording_id")

    actual_values = [_clean(value) for value in actual_ids]
    invalid_actual_rows = sum(not value for value in actual_values)
    actual_counts = Counter(value for value in actual_values if value)
    missing = sorted(expected.difference(actual_counts))
    duplicate_ids = {
        rid: count for rid, count in sorted(actual_counts.items()) if count > 1
    }
    duplicate_recording_count = len(duplicate_ids)
    excess_duplicate_rows = sum(count - 1 for count in duplicate_ids.values())
    expected_count = len(expected)

    i1 = {
        "passed": not missing,
        "expected_recording_count": expected_count,
        "missing_count": len(missing),
        "missing_rate": len(missing) / expected_count,
        "missing_ids": missing,
    }
    i2 = {
        "passed": duplicate_recording_count == 0 and invalid_actual_rows == 0,
        "duplicate_recording_count": duplicate_recording_count,
        "excess_duplicate_rows": excess_duplicate_rows,
        "duplicate_rate": duplicate_recording_count / expected_count,
        "duplicate_ids_and_row_counts": duplicate_ids,
        "invalid_recording_id_rows": invalid_actual_rows,
    }
    return {
        "expected_recording_count": expected_count,
        "actual_metadata_row_count": len(actual_values),
        "actual_distinct_nonempty_recording_ids": len(actual_counts),
        "I1_completeness": i1,
        "I2_uniqueness": i2,
        "all_pass": i1["passed"] and i2["passed"],
    }


def _row_uri(row: Mapping[str, object]) -> str | None:
    return normalize_object_uri(row.get("object_uri"))


def reconcile_i3_i5(
    expected_rows: Iterable[Mapping[str, object]],
    actual_rows: Iterable[Mapping[str, object]],
    actual_objects: Iterable[Mapping[str, object]],
) -> dict:
    """Evaluate I3 referential, I4 orphan objects, and I5 dangling metadata.

    I3 compares each known recording's stored URI with the frozen expected URI.
    I4 compares listed object URIs against URIs referenced by metadata rows.
    I5 compares metadata URIs against the complete listed object URI set.
    """
    expected_by_id: dict[str, str] = {}
    for row in expected_rows:
        recording_id = _clean(row.get("recording_id"))
        uri = normalize_object_uri(row.get("object_uri"))
        if not recording_id or uri is None:
            raise ValueError("expected metadata rows need non-empty recording_id and valid object_uri")
        if recording_id in expected_by_id:
            raise ValueError(f"expected metadata has duplicate recording_id: {recording_id}")
        expected_by_id[recording_id] = uri
    if not expected_by_id:
        raise ValueError("expected metadata must contain at least one row")

    rows = list(actual_rows)
    objects = list(actual_objects)
    violations_i3 = []
    referenced_uris: set[str] = set()
    object_uris: set[str] = set()

    for row in rows:
        recording_id = _clean(row.get("recording_id"))
        actual_uri = normalize_object_uri(row.get("object_uri"))
        expected_uri = expected_by_id.get(recording_id)
        if expected_uri is not None and actual_uri != expected_uri:
            violations_i3.append({
                "recording_id": recording_id,
                "expected_object_uri": expected_uri,
                "actual_object_uri": actual_uri,
            })
        if actual_uri is not None:
            referenced_uris.add(actual_uri)
    for obj in objects:
        uri = normalize_object_uri(obj.get("uri"))
        if uri is not None:
            object_uris.add(uri)

    orphan_objects = sorted(object_uris - referenced_uris)
    # Compute against a stable set after collecting all listed objects.
    actual_uri_set = object_uris
    dangling = [
        {"recording_id": _clean(row.get("recording_id")), "object_uri": _clean(row.get("object_uri")) or None}
        for row in rows
        if (uri := _row_uri(row)) is None or uri not in actual_uri_set
    ]

    i3 = {"passed": not violations_i3, "violation_count": len(violations_i3), "violations": violations_i3}
    i4 = {"passed": not orphan_objects, "orphan_object_count": len(orphan_objects), "orphan_object_uris": orphan_objects}
    i5 = {"passed": not dangling, "dangling_metadata_count": len(dangling), "dangling_metadata": dangling}
    return {
        "actual_metadata_row_count": len(rows),
        "actual_object_count": len(objects),
        "actual_distinct_object_uri_count": len(object_uris),
        "I3_referential": i3,
        "I4_no_orphan": i4,
        "I5_no_dangling": i5,
        "all_pass": i3["passed"] and i4["passed"] and i5["passed"],
    }
