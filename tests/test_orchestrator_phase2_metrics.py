"""Tests for Phase 2 metrics parsing in orchestrator."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from ralph_ml.config import CycleSnapshot, MetricsResult, TargetMetric
from ralph_ml.orchestrator import Orchestrator


class TestPhase2MetricsParsing:
    """Test metrics.json parsing with various formats."""

    def test_parse_metrics_with_nested_result(self, maximize_config, tmp_run_path):
        """Parse metrics.json with nested 'result' key."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # Get the workspace path that orchestrator will use
        workspace = orch.config.get_paths()["workspace"]
        workspace.mkdir(parents=True, exist_ok=True)

        # Create cycle directory
        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        # Mock the training execution - writes metrics.json AFTER stale removal
        def mock_training(*args, **kwargs):
            metrics_data = {
                "cycle": 1,
                "target": {"name": "test_accuracy", "value": 0.9},
                "result": {
                    "test_accuracy": 0.87,
                    "val_accuracy": 0.88,
                    "train_loss": 0.3,
                    "val_loss": 0.35,
                },
                "runtime": {"train_seconds": 15.0},
            }
            (workspace / "metrics.json").write_text(json.dumps(metrics_data))
            return (0, "training output", "", 15.0, False)

        orch._run_training_with_live_logs = mock_training

        metrics = orch._phase2_training(cycle_dir)

        assert metrics.result.test_accuracy == 0.87
        assert metrics.result.val_accuracy == 0.88
        assert metrics.result.train_loss == 0.3
        assert metrics.result.val_loss == 0.35
        assert metrics.runtime.train_seconds == 15.0

    def test_parse_metrics_top_level(self, maximize_config, tmp_run_path):
        """Parse metrics.json with top-level metrics (no result nesting)."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = orch.config.get_paths()["workspace"]
        workspace.mkdir(parents=True, exist_ok=True)

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        def mock_training(*args, **kwargs):
            metrics_data = {
                "test_accuracy": 0.91,
                "val_accuracy": 0.90,
                "train_loss": 0.25,
                "val_loss": 0.28,
            }
            (workspace / "metrics.json").write_text(json.dumps(metrics_data))
            return (0, "training output", "", 20.0, False)

        orch._run_training_with_live_logs = mock_training

        metrics = orch._phase2_training(cycle_dir)

        assert metrics.result.test_accuracy == 0.91

    def test_parse_metrics_from_final_epoch(self, maximize_config, tmp_run_path):
        """Parse metrics from final_epoch key when result is missing."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = orch.config.get_paths()["workspace"]
        workspace.mkdir(parents=True, exist_ok=True)

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        def mock_training(*args, **kwargs):
            metrics_data = {
                "final_epoch": {
                    "test_accuracy": 0.92,
                    "val_accuracy": 0.91,
                    "train_loss": 0.22,
                    "val_loss": 0.25,
                },
            }
            (workspace / "metrics.json").write_text(json.dumps(metrics_data))
            return (0, "training output", "", 25.0, False)

        orch._run_training_with_live_logs = mock_training

        metrics = orch._phase2_training(cycle_dir)

        assert metrics.result.test_accuracy == 0.92

    def test_parse_metrics_from_history(self, maximize_config, tmp_run_path):
        """Parse metrics from history array when other sources missing."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = orch.config.get_paths()["workspace"]
        workspace.mkdir(parents=True, exist_ok=True)

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        def mock_training(*args, **kwargs):
            metrics_data = {
                "history": [
                    {"epoch": 1, "train_loss": 0.8, "val_loss": 0.7},
                    {"epoch": 2, "train_loss": 0.5, "val_loss": 0.45},
                    {"epoch": 3, "train_loss": 0.3, "val_loss": 0.35},
                ],
            }
            (workspace / "metrics.json").write_text(json.dumps(metrics_data))
            return (0, "training output", "", 30.0, False)

        orch._run_training_with_live_logs = mock_training

        metrics = orch._phase2_training(cycle_dir)

        assert metrics.result.train_loss == 0.3
        assert metrics.result.val_loss == 0.35

    def test_stale_metrics_removed_before_training(self, maximize_config, tmp_run_path):
        """Stale metrics.json from previous run should be removed."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = orch.config.get_paths()["workspace"]
        workspace.mkdir(parents=True, exist_ok=True)

        # Create stale metrics
        stale_metrics = {"test_accuracy": 0.99, "from": "previous_run"}
        (workspace / "metrics.json").write_text(json.dumps(stale_metrics))

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        # Mock training that creates new metrics
        def mock_training(*args, **kwargs):
            new_metrics = {
                "test_accuracy": 0.85,
                "val_accuracy": 0.87,
            }
            (workspace / "metrics.json").write_text(json.dumps(new_metrics))
            return (0, "training output", "", 10.0, False)

        orch._run_training_with_live_logs = mock_training

        metrics = orch._phase2_training(cycle_dir)

        # Should have new metrics, not stale
        assert metrics.result.test_accuracy == 0.85

    def test_best_test_accuracy_fallback(self, maximize_config, tmp_run_path):
        """Use 'best_test_accuracy' key when 'test_accuracy' not present."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = orch.config.get_paths()["workspace"]
        workspace.mkdir(parents=True, exist_ok=True)

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        def mock_training(*args, **kwargs):
            metrics_data = {
                "result": {
                    "best_test_accuracy": 0.93,
                    "best_val_accuracy": 0.92,
                },
            }
            (workspace / "metrics.json").write_text(json.dumps(metrics_data))
            return (0, "training output", "", 20.0, False)

        orch._run_training_with_live_logs = mock_training

        metrics = orch._phase2_training(cycle_dir)

        assert metrics.result.test_accuracy == 0.93

    def test_fallback_to_output_parsing(self, maximize_config, tmp_run_path):
        """When metrics.json missing, parse from training output."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = orch.config.get_paths()["workspace"]
        workspace.mkdir(parents=True, exist_ok=True)

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        # Mock training output with test_accuracy in it
        output = """
        Epoch 1/10: loss=0.5, accuracy=0.7
        Epoch 2/10: loss=0.3, accuracy=0.85
        Final test_accuracy: 0.88
        """

        def mock_training(*args, **kwargs):
            return (0, output, "", 20.0, False)

        orch._run_training_with_live_logs = mock_training

        metrics = orch._phase2_training(cycle_dir)

        # Should parse from output since metrics.json doesn't exist
        assert metrics.result.test_accuracy == 0.88

    def test_target_metric_name_preserved(self, maximize_config, tmp_run_path):
        """Ensure target metric name from config is preserved in metrics."""
        maximize_config.project.target_metric.name = "custom_metric"
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = orch.config.get_paths()["workspace"]
        workspace.mkdir(parents=True, exist_ok=True)

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        def mock_training(*args, **kwargs):
            metrics_data = {
                "result": {
                    "custom_metric": 0.89,
                },
            }
            (workspace / "metrics.json").write_text(json.dumps(metrics_data))
            return (0, "training output", "", 15.0, False)

        orch._run_training_with_live_logs = mock_training

        metrics = orch._phase2_training(cycle_dir)

        assert metrics.target.name == "custom_metric"
        # ResultMetrics has extra='allow' so custom_metric should be accessible via model_dump
        result_dict = metrics.result.model_dump()
        assert result_dict.get("custom_metric") == 0.89
