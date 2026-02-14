"""Tests for Phase 3 analysis fallback behavior in orchestrator."""

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


class TestPhase3AnalysisFallback:
    """Test analysis phase fallback behavior when output files missing."""

    def test_fallback_when_all_outputs_missing(self, maximize_config, tmp_run_path):
        """Should create fallback analysis when no output files exist."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        metrics = MetricsResult(
            cycle=1,
            target=maximize_config.project.target_metric,
            result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            runtime=MetricsResult.Runtime(train_seconds=10.0),
        )

        def mock_run(*args, **kwargs):
            return (0, "analysis output", "", 5.0, False)

        orch._run_with_heartbeat = mock_run

        analysis = orch._phase3_analysis(cycle_dir, metrics, "Test prompt")

        assert analysis.summary is not None
        assert len(analysis.recommendations) >= 1
        assert analysis.decision.action in ["continue", "stop"]
        assert analysis.decision.rationale is not None

    def test_fallback_target_met(self, maximize_config, tmp_run_path):
        """Should recommend 'stop' when target is met."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        # Target is 0.9, achieved 0.92
        metrics = MetricsResult(
            cycle=1,
            target=maximize_config.project.target_metric,
            result=MetricsResult.ResultMetrics(test_accuracy=0.92),
            runtime=MetricsResult.Runtime(train_seconds=10.0),
        )

        def mock_run(*args, **kwargs):
            return (0, "analysis output", "", 5.0, False)

        orch._run_with_heartbeat = mock_run

        analysis = orch._phase3_analysis(cycle_dir, metrics, "Test prompt")

        assert analysis.decision.action == "stop"

    def test_read_recommendations_list_format(self, maximize_config, tmp_run_path):
        """Should parse recommendations.json as a list."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        # Create recommendations as a list
        recommendations_data = [
            {
                "action": "Increase learning rate",
                "confidence": "high",
                "rationale": "Training is stable",
            },
            {
                "action": "Add dropout",
                "confidence": "medium",
                "rationale": "Prevent overfitting",
            },
        ]
        (workspace / "recommendations.json").write_text(json.dumps(recommendations_data))

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        metrics = MetricsResult(
            cycle=1,
            target=maximize_config.project.target_metric,
            result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            runtime=MetricsResult.Runtime(train_seconds=10.0),
        )

        def mock_run(*args, **kwargs):
            return (0, "analysis output", "", 5.0, False)

        orch._run_with_heartbeat = mock_run

        analysis = orch._phase3_analysis(cycle_dir, metrics, "Test prompt")

        assert len(analysis.recommendations) == 2
        assert analysis.recommendations[0].action == "Increase learning rate"
        assert analysis.recommendations[0].confidence == "high"

    def test_read_recommendations_nested_format(self, maximize_config, tmp_run_path):
        """Should parse recommendations.json with nested structure."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        # Create recommendations with nested structure
        recommendations_data = {
            "recommendations": [
                {
                    "action": "Tune batch size",
                    "confidence": "high",
                    "rationale": "Better convergence",
                }
            ]
        }
        (workspace / "recommendations.json").write_text(json.dumps(recommendations_data))

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        metrics = MetricsResult(
            cycle=1,
            target=maximize_config.project.target_metric,
            result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            runtime=MetricsResult.Runtime(train_seconds=10.0),
        )

        def mock_run(*args, **kwargs):
            return (0, "analysis output", "", 5.0, False)

        orch._run_with_heartbeat = mock_run

        analysis = orch._phase3_analysis(cycle_dir, metrics, "Test prompt")

        assert len(analysis.recommendations) == 1
        assert analysis.recommendations[0].action == "Tune batch size"

    def test_read_decision_direct_format(self, maximize_config, tmp_run_path):
        """Should parse decision.json in direct format."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        decision_data = {
            "action": "stop",
            "rationale": "Target achieved",
        }
        (workspace / "decision.json").write_text(json.dumps(decision_data))

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        metrics = MetricsResult(
            cycle=1,
            target=maximize_config.project.target_metric,
            result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            runtime=MetricsResult.Runtime(train_seconds=10.0),
        )

        def mock_run(*args, **kwargs):
            return (0, "analysis output", "", 5.0, False)

        orch._run_with_heartbeat = mock_run

        analysis = orch._phase3_analysis(cycle_dir, metrics, "Test prompt")

        assert analysis.decision.action == "stop"
        assert analysis.decision.rationale == "Target achieved"

    def test_read_decision_nested_format(self, maximize_config, tmp_run_path):
        """Should parse decision.json with nested decision key."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        decision_data = {
            "decision": {
                "action": "continue",
                "rationale": "Need more training",
            }
        }
        (workspace / "decision.json").write_text(json.dumps(decision_data))

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        metrics = MetricsResult(
            cycle=1,
            target=maximize_config.project.target_metric,
            result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            runtime=MetricsResult.Runtime(train_seconds=10.0),
        )

        def mock_run(*args, **kwargs):
            return (0, "analysis output", "", 5.0, False)

        orch._run_with_heartbeat = mock_run

        analysis = orch._phase3_analysis(cycle_dir, metrics, "Test prompt")

        assert analysis.decision.action == "continue"
        assert analysis.decision.rationale == "Need more training"

    def test_read_analysis_md(self, maximize_config, tmp_run_path):
        """Should use analysis.md content as summary."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        analysis_content = "# Training Analysis\n\nThis was a great training run."
        (workspace / "analysis.md").write_text(analysis_content)

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        metrics = MetricsResult(
            cycle=1,
            target=maximize_config.project.target_metric,
            result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            runtime=MetricsResult.Runtime(train_seconds=10.0),
        )

        def mock_run(*args, **kwargs):
            return (0, "analysis output", "", 5.0, False)

        orch._run_with_heartbeat = mock_run

        analysis = orch._phase3_analysis(cycle_dir, metrics, "Test prompt")

        assert analysis.summary == analysis_content

    def test_malformed_recommendations_graceful(self, maximize_config, tmp_run_path):
        """Should handle malformed recommendations.json gracefully."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        # Invalid JSON
        (workspace / "recommendations.json").write_text("not valid json")

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        metrics = MetricsResult(
            cycle=1,
            target=maximize_config.project.target_metric,
            result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            runtime=MetricsResult.Runtime(train_seconds=10.0),
        )

        def mock_run(*args, **kwargs):
            return (0, "analysis output", "", 5.0, False)

        orch._run_with_heartbeat = mock_run

        # Should not crash
        analysis = orch._phase3_analysis(cycle_dir, metrics, "Test prompt")

        assert len(analysis.recommendations) >= 1
        assert analysis.decision.action in ["continue", "stop"]

    def test_malformed_decision_graceful(self, maximize_config, tmp_run_path):
        """Should handle malformed decision.json gracefully."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        workspace = tmp_run_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        # Invalid decision action
        (workspace / "decision.json").write_text(
            json.dumps({"action": "invalid_action", "rationale": "Test"})
        )

        cycle_dir = tmp_run_path / "cycles" / "cycle_0001"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        metrics = MetricsResult(
            cycle=1,
            target=maximize_config.project.target_metric,
            result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            runtime=MetricsResult.Runtime(train_seconds=10.0),
        )

        def mock_run(*args, **kwargs):
            return (0, "analysis output", "", 5.0, False)

        orch._run_with_heartbeat = mock_run

        # Should not crash, should use fallback
        analysis = orch._phase3_analysis(cycle_dir, metrics, "Test prompt")

        # Invalid action should fall back to valid one
        assert analysis.decision.action in ["continue", "stop"]
