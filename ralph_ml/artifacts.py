"""Artifact management for Ralph ML Loop."""

import json
import shutil
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional

from ralph_ml.config import CycleSnapshot, RalphState, TargetMetric


def capture_architecture_log(
    workspace: Path,
    cycle_dir: Path,
    state: RalphState,
    target_metric: TargetMetric,
) -> dict[str, Any]:
    """Capture architecture-relevant file fingerprints for this cycle.

    Args:
        workspace: Path to workspace directory
        cycle_dir: Directory for this cycle
        state: Current orchestrator state
        target_metric: Target metric configuration

    Returns:
        Architecture log dictionary
    """
    tracked_files = ["model.py", "train.py", "eval.py", "data.py", "config.json"]

    previous_hashes: dict[str, str] = {}
    if state.history:
        prev_arch = state.history[-1].architecture_log or {}
        prev_files = prev_arch.get("files", {}) if isinstance(prev_arch, dict) else {}
        for file_name, info in prev_files.items():
            if isinstance(info, dict) and isinstance(info.get("sha256"), str):
                previous_hashes[file_name] = info["sha256"]

    files_payload: dict[str, Any] = {}
    changed_files: list[str] = []

    for rel_path in tracked_files:
        full_path = workspace / rel_path
        if not full_path.exists():
            files_payload[rel_path] = {"exists": False}
            continue

        content = full_path.read_text(errors="ignore")
        digest = sha256(content.encode("utf-8")).hexdigest()
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

        previous_digest = previous_hashes.get(rel_path)
        changed = previous_digest is None or previous_digest != digest
        if changed:
            changed_files.append(rel_path)

        files_payload[rel_path] = {
            "exists": True,
            "sha256": digest,
            "line_count": line_count,
            "bytes": full_path.stat().st_size,
            "changed_since_prev_cycle": changed,
        }

    arch_log = {
        "cycle": state.current_cycle + 1,
        "timestamp": datetime.now().isoformat(),
        "objective": {
            "name": target_metric.name,
            "target_value": target_metric.value,
            "direction": target_metric.get_direction(),
        },
        "changed_files": changed_files,
        "files": files_payload,
    }

    arch_log_path = cycle_dir / "architecture_log.json"
    arch_log["log_path"] = str(arch_log_path)
    arch_log_path.write_text(json.dumps(arch_log, indent=2))

    print(
        f"   Architecture log captured: {arch_log_path} (changed files: {changed_files or ['none']})"
    )
    return arch_log


def capture_source_snapshot(
    workspace: Path,
    cycle_dir: Path,
    cycle_number: int,
) -> str:
    """Copy cycle source files so any cycle can be fully restored later.

    Args:
        workspace: Path to workspace directory
        cycle_dir: Directory for this cycle
        cycle_number: Current cycle number

    Returns:
        Path to snapshot directory as string
    """
    tracked_files = ["model.py", "train.py", "eval.py", "data.py", "config.json"]
    snapshot_dir = cycle_dir / "source_snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for rel_path in tracked_files:
        source_path = workspace / rel_path
        if not source_path.exists() or not source_path.is_file():
            continue

        target_path = snapshot_dir / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied.append(rel_path)

    manifest = {
        "cycle": cycle_number,
        "timestamp": datetime.now().isoformat(),
        "files": copied,
    }
    (snapshot_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"   Source snapshot saved: {snapshot_dir} (files: {copied or ['none']})")
    return str(snapshot_dir)


def capture_model_artifact(
    workspace: Path,
    cycle_dir: Path,
) -> Optional[str]:
    """Copy best model artifact for this cycle into cycle artifacts directory.

    Args:
        workspace: Path to workspace directory
        cycle_dir: Directory for this cycle

    Returns:
        Path to copied artifact or None if no artifact found
    """
    candidates = [
        workspace / "best_model.pt",
        workspace / "artifacts" / "best_model.pt",
        workspace / "outputs" / "best_model.pt",
        workspace / "model.pth",
        workspace / "checkpoint.pt",
    ]

    artifact_source = next((p for p in candidates if p.exists() and p.is_file()), None)
    if artifact_source is None:
        return None

    artifact_dir = cycle_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    target_path = artifact_dir / artifact_source.name
    shutil.copy2(artifact_source, target_path)
    return str(target_path)


def write_best_model_index(
    state_path: Path,
    state: RalphState,
    target_metric: TargetMetric,
) -> None:
    """Write a single JSON pointer for the current best model.

    Args:
        state_path: Path to state file
        state: Current orchestrator state
        target_metric: Target metric configuration
    """
    index_path = state_path.parent.parent / "best_model_index.json"

    target = target_metric
    payload: dict[str, Any] = {
        "updated_at": datetime.now().isoformat(),
        "objective": {
            "name": target.name,
            "direction": target.get_direction(),
            "target_value": target.value,
            "comparator": target.comparator_symbol(),
        },
        "best_cycle": state.best_cycle,
        "best_metric": state.best_metric,
        "target_met": False,
        "best_model_artifact": None,
        "best_architecture_log": None,
        "best_source_snapshot": None,
    }

    if state.best_cycle > 0 and len(state.history) >= state.best_cycle:
        best_snapshot = state.history[state.best_cycle - 1]
        metric_value = best_snapshot.metrics.result.model_dump().get(target.name)
        if isinstance(metric_value, (int, float)):
            payload["best_metric"] = float(metric_value)
            payload["target_met"] = target.target_is_met(float(metric_value))

        if best_snapshot.best_model_artifact:
            payload["best_model_artifact"] = best_snapshot.best_model_artifact

        if best_snapshot.architecture_log and isinstance(best_snapshot.architecture_log, dict):
            payload["best_architecture_log"] = best_snapshot.architecture_log.get("log_path")

        if best_snapshot.source_snapshot_dir:
            payload["best_source_snapshot"] = best_snapshot.source_snapshot_dir

    index_path.write_text(json.dumps(payload, indent=2))
