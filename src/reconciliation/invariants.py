"""Pure correctness checks for frozen expected and observed metadata IDs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


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
