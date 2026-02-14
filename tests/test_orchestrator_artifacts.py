"""Tests for orchestrator artifact capture methods."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from ralph_ml.config import (
    CycleAnalysis,
    CycleSnapshot,
    MetricsResult,
    Recommendation,
    TargetMetric,
)
from ralph_ml.orchestrator import Orchestrator


class TestCaptureArchitectureLog:
    """Test _capture_architecture_log method."""

    def test_captures_file_hashes(self, maximize_config, tmp_run_path, create_workspace_files):
        """Should capture SHA256 hashes for tracked files."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        create_workspace_files(
            workspace,
            {
                "model.py": "import torch\nclass Model(torch.nn.Module): pass",
                "train.py": "# Training code",
                "eval.py": "# Eval code",
                "data.py": "# Data loading",
                "config.json": '{"lr": 0.001}',
            },
        )

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        arch_log = orch._capture_architecture_log(cycle_dir)

        assert "files" in arch_log
        assert "model.py" in arch_log["files"]
        assert arch_log["files"]["model.py"]["exists"] is True
        assert "sha256" in arch_log["files"]["model.py"]
        assert "line_count" in arch_log["files"]["model.py"]
        assert "bytes" in arch_log["files"]["model.py"]

    def test_detects_changed_files(self, maximize_config, tmp_run_path, create_workspace_files):
        """Should detect which files changed since previous cycle."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"

        # First cycle
        create_workspace_files(workspace, {"model.py": "version 1"})
        cycle1_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle1_dir.mkdir(parents=True, exist_ok=True)
        arch_log1 = orch._capture_architecture_log(cycle1_dir)

        # Add to history
        snapshot = CycleSnapshot(
            cycle_number=1,
            metrics=MetricsResult(
                cycle=1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(),
            ),
            timestamp="2024-01-01T00:00:00",
            architecture_log=arch_log1,
        )
        orch.state.add_cycle(snapshot)

        # Second cycle with changed file
        create_workspace_files(workspace, {"model.py": "version 2"})
        cycle2_dir = tmp_run_path / "cycles" / "cycle_0002"
        cycle2_dir.mkdir(parents=True, exist_ok=True)
        arch_log2 = orch._capture_architecture_log(cycle2_dir)

        assert "model.py" in arch_log2["changed_files"]
        assert arch_log2["files"]["model.py"]["changed_since_prev_cycle"] is True

    def test_detects_unchanged_files(self, maximize_config, tmp_run_path, create_workspace_files):
        """Should detect unchanged files correctly."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"

        # First cycle
        create_workspace_files(workspace, {"model.py": "unchanged content"})
        cycle1_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle1_dir.mkdir(parents=True, exist_ok=True)
        arch_log1 = orch._capture_architecture_log(cycle1_dir)

        # Add to history
        snapshot = CycleSnapshot(
            cycle_number=1,
            metrics=MetricsResult(
                cycle=1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(),
            ),
            timestamp="2024-01-01T00:00:00",
            architecture_log=arch_log1,
        )
        orch.state.add_cycle(snapshot)

        # Second cycle with same content
        create_workspace_files(workspace, {"model.py": "unchanged content"})
        cycle2_dir = tmp_run_path / "cycles" / "cycle_0002"
        cycle2_dir.mkdir(parents=True, exist_ok=True)
        arch_log2 = orch._capture_architecture_log(cycle2_dir)

        assert "model.py" not in arch_log2["changed_files"]
        assert arch_log2["files"]["model.py"]["changed_since_prev_cycle"] is False

    def test_missing_files_marked(self, maximize_config, tmp_run_path):
        """Should mark missing files with exists=False."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # Create workspace but only some files
        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "model.py").write_text("# model")

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        arch_log = orch._capture_architecture_log(cycle_dir)

        assert arch_log["files"]["model.py"]["exists"] is True
        assert arch_log["files"]["train.py"]["exists"] is False

    def test_log_file_created(self, maximize_config, tmp_run_path, create_workspace_files):
        """Should create architecture_log.json in cycle directory."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        create_workspace_files(workspace, {"model.py": "# model"})

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        arch_log = orch._capture_architecture_log(cycle_dir)

        log_path = cycle_dir / "architecture_log.json"
        assert log_path.exists()

        saved_data = json.loads(log_path.read_text())
        assert saved_data["cycle"] == 1
        assert "objective" in saved_data
        assert saved_data["objective"]["name"] == "test_accuracy"


class TestCaptureSourceSnapshot:
    """Test _capture_source_snapshot method."""

    def test_copies_tracked_files(self, maximize_config, tmp_run_path, create_workspace_files):
        """Should copy tracked files to snapshot directory."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        files = {
            "model.py": "class Model: pass",
            "train.py": "def train(): pass",
            "eval.py": "def eval(): pass",
            "data.py": "def load(): pass",
            "config.json": '{"lr": 0.001}',
        }
        create_workspace_files(workspace, files)

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        snapshot_dir = orch._capture_source_snapshot(cycle_dir)

        snapshot_path = Path(snapshot_dir)
        assert snapshot_path.exists()
        assert (snapshot_path / "model.py").exists()
        assert (snapshot_path / "train.py").read_text() == "def train(): pass"

    def test_creates_manifest(self, maximize_config, tmp_run_path, create_workspace_files):
        """Should create manifest.json with file list."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        create_workspace_files(workspace, {"model.py": "# model", "train.py": "# train"})

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        orch._capture_source_snapshot(cycle_dir)

        manifest_path = cycle_dir / "source_snapshot" / "manifest.json"
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text())
        assert manifest["cycle"] == 1
        assert "model.py" in manifest["files"]
        assert "train.py" in manifest["files"]

    def test_skips_missing_files(self, maximize_config, tmp_run_path, create_workspace_files):
        """Should skip files that don't exist in workspace."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        create_workspace_files(workspace, {"model.py": "# model"})  # Only one file

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        snapshot_dir = orch._capture_source_snapshot(cycle_dir)

        manifest = json.loads((Path(snapshot_dir) / "manifest.json").read_text())
        assert "model.py" in manifest["files"]
        assert "train.py" not in manifest["files"]


class TestCaptureModelArtifact:
    """Test _capture_model_artifact method."""

    def test_copies_first_existing_candidate(self, maximize_config, tmp_run_path):
        """Should copy first existing model file candidate."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        # Create model file
        (workspace / "best_model.pt").write_bytes(b"fake model data")

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = orch._capture_model_artifact(cycle_dir)

        assert artifact_path is not None
        assert "best_model.pt" in artifact_path
        assert (cycle_dir / "artifacts" / "best_model.pt").exists()

    def test_checks_all_candidates(self, maximize_config, tmp_run_path):
        """Should check all candidate paths until finding one."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        # Create model in subdirectory (not first candidate)
        artifacts_dir = workspace / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "best_model.pt").write_bytes(b"fake model data")

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = orch._capture_model_artifact(cycle_dir)

        assert artifact_path is not None
        assert (cycle_dir / "artifacts" / "best_model.pt").exists()

    def test_returns_none_when_no_artifact(self, maximize_config, tmp_run_path):
        """Should return None when no model file exists."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        # No model files

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = orch._capture_model_artifact(cycle_dir)

        assert artifact_path is None


class TestWriteBestModelIndex:
    """Test _write_best_model_index method."""

    def test_writes_correct_fields(self, maximize_config, tmp_run_path):
        """Should write best_model_index.json with correct fields."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.paths.reports = str(tmp_run_path / "reports")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.project.target_metric.value = 0.9

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # Add a cycle with good metrics
        snapshot = CycleSnapshot(
            cycle_number=1,
            metrics=MetricsResult(
                cycle=1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.88),
            ),
            timestamp="2024-01-01T00:00:00",
        )
        orch.state.add_cycle(snapshot)

        orch._write_best_model_index()

        index_path = tmp_run_path / "state" / ".." / "best_model_index.json"
        index_path = index_path.resolve()
        assert index_path.exists()

        data = json.loads(index_path.read_text())
        assert data["best_cycle"] == 1
        assert data["best_metric"] == 0.88
        assert data["objective"]["name"] == "test_accuracy"
        assert data["objective"]["target_value"] == 0.9
        assert data["objective"]["direction"] == "maximize"
        assert data["objective"]["comparator"] == ">="

    def test_target_met_flag(self, maximize_config, tmp_run_path):
        """Should set target_met flag when target achieved."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.paths.reports = str(tmp_run_path / "reports")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.project.target_metric.value = 0.9

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # Add a cycle with metrics exceeding target
        snapshot = CycleSnapshot(
            cycle_number=1,
            metrics=MetricsResult(
                cycle=1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.92),
            ),
            timestamp="2024-01-01T00:00:00",
        )
        orch.state.add_cycle(snapshot)

        orch._write_best_model_index()

        index_path = (tmp_run_path / "state" / ".." / "best_model_index.json").resolve()
        data = json.loads(index_path.read_text())

        assert data["target_met"] is True

    def test_includes_artifact_paths(self, maximize_config, tmp_run_path):
        """Should include artifact paths when available."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.paths.reports = str(tmp_run_path / "reports")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # Add a cycle with artifact
        snapshot = CycleSnapshot(
            cycle_number=1,
            metrics=MetricsResult(
                cycle=1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.88),
            ),
            timestamp="2024-01-01T00:00:00",
            best_model_artifact="/path/to/model.pt",
            architecture_log={"log_path": "/path/to/arch.json"},
            source_snapshot_dir="/path/to/source",
        )
        orch.state.add_cycle(snapshot)

        orch._write_best_model_index()

        index_path = (tmp_run_path / "state" / ".." / "best_model_index.json").resolve()
        data = json.loads(index_path.read_text())

        assert data["best_model_artifact"] == "/path/to/model.pt"
        assert data["best_architecture_log"] == "/path/to/arch.json"
        assert data["best_source_snapshot"] == "/path/to/source"
