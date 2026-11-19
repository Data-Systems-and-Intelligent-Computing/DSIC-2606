"""Verify effective B0/B1 logs differ only at checkpoint_location."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


_PREFIX = "EFFECTIVE_CONFIG "


def read_effective_config(path: Path) -> dict:
    matches = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        marker = line.find(_PREFIX)
        if marker >= 0:
            matches.append(line[marker + len(_PREFIX):].strip())
    if len(matches) != 1:
        raise ValueError(f"{path}: expected exactly one EFFECTIVE_CONFIG line, found {len(matches)}")
    value = json.loads(matches[0])
    if not isinstance(value, dict):
        raise ValueError(f"{path}: effective config is not a JSON object")
    return value


def changed_keys(left: dict, right: dict) -> list[str]:
    return sorted(key for key in set(left) | set(right) if left.get(key) != right.get(key))


def verify_configs(b0_path: Path, b1_path: Path) -> list[str]:
    b0 = read_effective_config(b0_path)
    b1 = read_effective_config(b1_path)
    changed = changed_keys(b0, b1)
    if changed != ["checkpoint_location"]:
        raise ValueError(f"effective configs must differ only by checkpoint_location; found {changed}")
    if not b0.get("checkpoint_location", "").startswith("/checkpoints/ephemeral/"):
        raise ValueError("B0 checkpoint must use /checkpoints/ephemeral")
    if not b1.get("checkpoint_location", "").startswith("/checkpoints/persistent/"):
        raise ValueError("B1 checkpoint must use /checkpoints/persistent")
    if b0.get("idempotence_enabled") is not False or b1.get("idempotence_enabled") is not False:
        raise ValueError("B0 and B1 must both have idempotence disabled")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("b0_log", type=Path)
    parser.add_argument("b1_log", type=Path)
    args = parser.parse_args()
    try:
        changed = verify_configs(args.b0_log, args.b1_log)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print("B0/B1 effective configuration: COCOK")
    print("Kunci berbeda: " + ", ".join(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
