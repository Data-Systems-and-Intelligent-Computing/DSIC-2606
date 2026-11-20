"""Pure correctness checks for frozen expected and observed metadata IDs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
import re
from urllib.parse import urlsplit


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def _identity(value: object) -> str:
    """Keep non-empty identifiers exact; whitespace is not silently normalized."""
    return "" if value is None else str(value)


def normalize_object_uri(value: object) -> str | None:
    """Normalize s3/s3a object URIs while preserving bucket and key exactly."""
    text = _identity(value)
    if not text or text != text.strip():
        return None
    parsed = urlsplit(text)
    if parsed.scheme.lower() not in {"s3", "s3a"} or not parsed.netloc:
        return None
    if parsed.query or parsed.fragment:
        return None
    # Remove only the URI separator; preserve any leading slash that belongs
    # to the actual S3 key so keys are never silently collapsed.
    key = parsed.path[1:] if parsed.path.startswith("/") else parsed.path
    if not key or "\x00" in key:
        return None
    return f"s3://{parsed.netloc}/{key}"


def reconcile_i1_i2(expected_ids: Iterable[object], actual_ids: Iterable[object]) -> dict:
    """Evaluate I1 completeness and I2 uniqueness for metadata recording IDs."""
    expected_values = [_identity(value) for value in expected_ids]
    if any(not value.strip() for value in expected_values):
        raise ValueError("expected metadata contains an empty recording_id")
    expected_counts = Counter(expected_values)
    duplicate_expected = sorted(rid for rid, count in expected_counts.items() if count > 1)
    if duplicate_expected:
        raise ValueError(f"expected metadata has duplicate recording_id values: {duplicate_expected[:5]}")
    expected = set(expected_values)
    if not expected:
        raise ValueError("expected metadata must contain at least one recording_id")

    actual_values = [_identity(value) for value in actual_ids]
    invalid_actual_rows = sum(not value.strip() for value in actual_values)
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


def _same_instant(left: object, right: object) -> bool:
    """Compare ISO timestamps as UTC instants; reject timestamps without zones."""
    try:
        parsed = []
        for value in (left, right):
            text = _clean(value)
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            timestamp = datetime.fromisoformat(text)
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                return False
            parsed.append(timestamp.astimezone(timezone.utc))
        return parsed[0] == parsed[1]
    except (TypeError, ValueError):
        return False


def _metadata_field_matches(field: str, expected: object, actual: object) -> bool:
    if field == "file_size_bytes":
        try:
            return int(expected) == int(actual)
        except (TypeError, ValueError):
            return False
    if field == "sha256":
        return _clean(expected).lower() == _clean(actual).lower()
    return _identity(expected) == _identity(actual)


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
    expected_by_id: dict[str, Mapping[str, object]] = {}
    for row in expected_rows:
        recording_id = _identity(row.get("recording_id"))
        uri = normalize_object_uri(row.get("object_uri"))
        if not recording_id.strip() or uri is None:
            raise ValueError("expected metadata rows need non-empty recording_id and valid object_uri")
        if recording_id in expected_by_id:
            raise ValueError(f"expected metadata has duplicate recording_id: {recording_id}")
        expected_by_id[recording_id] = row
    if not expected_by_id:
        raise ValueError("expected metadata must contain at least one row")

    rows = list(actual_rows)
    objects = list(actual_objects)
    violations_i3 = []
    field_mismatches_i3 = []
    referenced_uris: set[str] = set()
    object_uris: set[str] = set()

    for row in rows:
        recording_id = _identity(row.get("recording_id"))
        actual_uri = normalize_object_uri(row.get("object_uri"))
        expected_row = expected_by_id.get(recording_id)
        expected_uri = normalize_object_uri(expected_row.get("object_uri")) if expected_row else None
        if expected_row is not None and actual_uri != expected_uri:
            violations_i3.append({
                "recording_id": recording_id,
                "expected_object_uri": expected_uri,
                "actual_object_uri": actual_uri,
            })
        if expected_row is not None:
            for field in ("device_id", "file_size_bytes", "sha256"):
                if field not in expected_row:
                    continue
                expected_value = expected_row.get(field)
                actual_value = row.get(field)
                equal = _metadata_field_matches(field, expected_value, actual_value)
                if not equal:
                    field_mismatches_i3.append({
                        "recording_id": recording_id,
                        "field": field,
                        "expected": expected_value,
                        "actual": actual_value,
                    })
            if "start_time" in expected_row and not _same_instant(expected_row.get("start_time"), row.get("start_time")):
                field_mismatches_i3.append({
                    "recording_id": recording_id,
                    "field": "start_time",
                    "expected": expected_row.get("start_time"),
                    "actual": row.get("start_time"),
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

    i3 = {
        "passed": not violations_i3 and not field_mismatches_i3,
        "violation_count": len(violations_i3) + len(field_mismatches_i3),
        "violations": violations_i3,
        "metadata_field_mismatch_count": len(field_mismatches_i3),
        "metadata_field_mismatches": field_mismatches_i3,
    }
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


def reconcile_i6_i7(
    expected_rows: Iterable[Mapping[str, object]],
    actual_rows: Iterable[Mapping[str, object]],
    actual_hashes: Mapping[str, Mapping[str, object]],
) -> dict:
    """Evaluate I6 byte integrity and I7 metadata IDs outside ground truth."""
    expected_by_id: dict[str, Mapping[str, object]] = {}
    for row in expected_rows:
        recording_id = _identity(row.get("recording_id"))
        uri = normalize_object_uri(row.get("object_uri"))
        if not recording_id.strip() or uri is None:
            raise ValueError("expected metadata rows need non-empty recording_id and valid object_uri")
        if recording_id in expected_by_id:
            raise ValueError(f"expected metadata has duplicate recording_id: {recording_id}")
        expected_by_id[recording_id] = row
    if not expected_by_id:
        raise ValueError("expected metadata must contain at least one row")

    mismatches = []
    hashed_byte_count = 0
    hashed_object_count = 0
    for recording_id, row in sorted(expected_by_id.items()):
        uri = normalize_object_uri(row.get("object_uri"))
        observed = actual_hashes.get(uri)
        if observed is None:
            # Missing object is reported by I5; it cannot be byte-checked.
            continue
        try:
            expected_size = int(row["file_size_bytes"])
            observed_size = int(observed["size"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid expected/observed object size for {recording_id}") from exc
        expected_sha = _clean(row.get("sha256")).lower()
        observed_sha = _clean(observed.get("sha256")).lower()
        if expected_size < 0 or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise ValueError(f"invalid expected size or SHA-256 for {recording_id}")
        hashed_object_count += 1
        hashed_byte_count += observed_size
        if expected_size != observed_size or expected_sha != observed_sha:
            mismatches.append({
                "recording_id": recording_id,
                "object_uri": uri,
                "expected_size_bytes": expected_size,
                "actual_size_bytes": observed_size,
                "expected_sha256": expected_sha,
                "actual_sha256": observed_sha,
            })

    expected_ids = set(expected_by_id)
    actual_counts = Counter(_identity(row.get("recording_id")) for row in actual_rows)
    extras = sorted(recording_id for recording_id, count in actual_counts.items() if recording_id.strip() and recording_id not in expected_ids)
    i6 = {
        "passed": not mismatches,
        "checksum_mismatch_count": len(mismatches),
        "checksum_mismatches": mismatches,
        "hashed_object_count": hashed_object_count,
        "hashed_byte_count": hashed_byte_count,
    }
    i7 = {
        "passed": not extras,
        "extra_recording_id_count": len(extras),
        "extra_recording_ids": extras,
        "extra_metadata_row_count": sum(actual_counts[rid] for rid in extras),
    }
    return {
        "I6_byte_integrity": i6,
        "I7_no_extras": i7,
        "all_pass": i6["passed"] and i7["passed"],
    }
