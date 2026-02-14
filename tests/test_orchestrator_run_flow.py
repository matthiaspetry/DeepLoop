"""Tests for orchestrator run flow and state management."""

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


class TestOrchestratorRunFlow:
    """Test main run() method behavior."""

    def test_executes_single_cycle(self, maximize_config, tmp_run_path, mock_run_methods):
        """Should execute one full cycle with mocked phases."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.paths.reports = str(tmp_run_path / "reports")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.max_cycles = 1

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # Mock the phase methods
        def mock_phase1(*args, **kwargs):
            pass

        def mock_phase2(*args, **kwargs):
            return MetricsResult(
                cycle=orch.state.current_cycle + 1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            )

        def mock_phase3(*args, **kwargs):
            return CycleAnalysis(
                summary="Test analysis",
                recommendations=[
                    Recommendation(action="test", confidence="high", rationale="test")
                ],
                decision=CycleAnalysis.Decision(action="continue", rationale="Test"),
            )

        orch._phase1_codegen = mock_phase1
        orch._phase2_training = mock_phase2
        orch._phase3_analysis = mock_phase3

        orch.run("Test prompt")

        assert orch.state.current_cycle == 1
        assert len(orch.state.history) == 1

    def test_stops_on_decision_stop(self, maximize_config, tmp_run_path, mock_run_methods):
        """Should stop when analysis decision is 'stop'."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.paths.reports = str(tmp_run_path / "reports")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.max_cycles = 10

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        def mock_phase1(*args, **kwargs):
            pass

        def mock_phase2(*args, **kwargs):
            return MetricsResult(
                cycle=orch.state.current_cycle + 1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.95),
            )

        def mock_phase3(*args, **kwargs):
            return CycleAnalysis(
                summary="Target met",
                recommendations=[],
                decision=CycleAnalysis.Decision(action="stop", rationale="Target achieved"),
            )

        orch._phase1_codegen = mock_phase1
        orch._phase2_training = mock_phase2
        orch._phase3_analysis = mock_phase3

        orch.run("Test prompt")

        # Should stop after first cycle
        assert orch.state.current_cycle == 1

    def test_respects_max_cycles(self, maximize_config, tmp_run_path, mock_run_methods):
        """Should stop when max_cycles reached."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.paths.reports = str(tmp_run_path / "reports")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.max_cycles = 3

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        def mock_phase1(*args, **kwargs):
            pass

        def mock_phase2(*args, **kwargs):
            return MetricsResult(
                cycle=orch.state.current_cycle + 1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            )

        def mock_phase3(*args, **kwargs):
            return CycleAnalysis(
                summary="Continue",
                recommendations=[],
                decision=CycleAnalysis.Decision(action="continue", rationale="Keep going"),
            )

        orch._phase1_codegen = mock_phase1
        orch._phase2_training = mock_phase2
        orch._phase3_analysis = mock_phase3

        orch.run("Test prompt")

        # Should stop at max_cycles
        assert orch.state.current_cycle == 3

    def test_saves_state_after_each_cycle(self, maximize_config, tmp_run_path, mock_run_methods):
        """Should persist state after each cycle."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.paths.reports = str(tmp_run_path / "reports")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.max_cycles = 2

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        def mock_phase1(*args, **kwargs):
            pass

        def mock_phase2(*args, **kwargs):
            return MetricsResult(
                cycle=orch.state.current_cycle + 1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            )

        def mock_phase3(*args, **kwargs):
            return CycleAnalysis(
                summary="Analysis",
                recommendations=[],
                decision=CycleAnalysis.Decision(action="continue", rationale="Test"),
            )

        orch._phase1_codegen = mock_phase1
        orch._phase2_training = mock_phase2
        orch._phase3_analysis = mock_phase3

        orch.run("Test prompt")

        # State file should exist and have 2 cycles
        assert state_path.exists()
        saved_state = json.loads(state_path.read_text())
        assert saved_state["current_cycle"] == 2
        assert len(saved_state["history"]) == 2

    def test_updates_best_metric(self, maximize_config, tmp_run_path, mock_run_methods):
        """Should track best metric across cycles."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.paths.reports = str(tmp_run_path / "reports")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.max_cycles = 3

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        accuracies = [0.80, 0.88, 0.85]  # Best is cycle 2

        def mock_phase1(*args, **kwargs):
            pass

        def mock_phase2(*args, **kwargs):
            cycle = orch.state.current_cycle + 1
            return MetricsResult(
                cycle=cycle,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=accuracies[cycle - 1]),
            )

        def mock_phase3(*args, **kwargs):
            return CycleAnalysis(
                summary="Analysis",
                recommendations=[],
                decision=CycleAnalysis.Decision(action="continue", rationale="Test"),
            )

        orch._phase1_codegen = mock_phase1
        orch._phase2_training = mock_phase2
        orch._phase3_analysis = mock_phase3

        orch.run("Test prompt")

        assert orch.state.best_metric == 0.88
        assert orch.state.best_cycle == 2

    def test_status_set_to_completed(self, maximize_config, tmp_run_path, mock_run_methods):
        """Should set status to 'completed' when done."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.paths.reports = str(tmp_run_path / "reports")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.max_cycles = 1

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        def mock_phase1(*args, **kwargs):
            pass

        def mock_phase2(*args, **kwargs):
            return MetricsResult(
                cycle=orch.state.current_cycle + 1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            )

        def mock_phase3(*args, **kwargs):
            return CycleAnalysis(
                summary="Analysis",
                recommendations=[],
                decision=CycleAnalysis.Decision(action="stop", rationale="Done"),
            )

        orch._phase1_codegen = mock_phase1
        orch._phase2_training = mock_phase2
        orch._phase3_analysis = mock_phase3

        orch.run("Test prompt")

        assert orch.state.status == "completed"

    def test_resumable_from_saved_state(self, maximize_config, tmp_run_path, mock_run_methods):
        """Should be able to resume from saved state."""
        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.paths.reports = str(tmp_run_path / "reports")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"

        # Create initial state with 2 completed cycles
        orch1 = Orchestrator(maximize_config, state_path=state_path)

        for i in range(1, 3):
            snapshot = CycleSnapshot(
                cycle_number=i,
                metrics=MetricsResult(
                    cycle=i,
                    target=maximize_config.project.target_metric,
                    result=MetricsResult.ResultMetrics(test_accuracy=0.8 + i * 0.02),
                ),
                timestamp="2024-01-01T00:00:00",
            )
            orch1.state.add_cycle(snapshot)
        orch1._save_state()

        # Resume with new orchestrator
        orch2 = Orchestrator(maximize_config, state_path=state_path)

        assert orch2.state.current_cycle == 2
        assert len(orch2.state.history) == 2


class TestStateManagement:
    """Test RalphState methods."""

    def test_add_cycle_updates_current_cycle(self, maximize_config):
        """add_cycle should update current_cycle."""
        from ralph_ml.config import RalphState

        state = RalphState(config=maximize_config)

        snapshot = CycleSnapshot(
            cycle_number=1,
            metrics=MetricsResult(
                cycle=1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            ),
            timestamp="2024-01-01T00:00:00",
        )
        state.add_cycle(snapshot)

        assert state.current_cycle == 1

        snapshot2 = CycleSnapshot(
            cycle_number=2,
            metrics=MetricsResult(
                cycle=2,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.88),
            ),
            timestamp="2024-01-01T00:00:00",
        )
        state.add_cycle(snapshot2)

        assert state.current_cycle == 2

    def test_add_cycle_updates_best_metric_maximize(self, maximize_config):
        """add_cycle should track best metric for maximize direction."""
        from ralph_ml.config import RalphState

        state = RalphState(config=maximize_config)

        # First cycle: 0.85
        snapshot1 = CycleSnapshot(
            cycle_number=1,
            metrics=MetricsResult(
                cycle=1,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.85),
            ),
            timestamp="2024-01-01T00:00:00",
        )
        state.add_cycle(snapshot1)

        assert state.best_metric == 0.85
        assert state.best_cycle == 1

        # Second cycle: 0.88 (better)
        snapshot2 = CycleSnapshot(
            cycle_number=2,
            metrics=MetricsResult(
                cycle=2,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.88),
            ),
            timestamp="2024-01-01T00:00:00",
        )
        state.add_cycle(snapshot2)

        assert state.best_metric == 0.88
        assert state.best_cycle == 2

        # Third cycle: 0.86 (worse, should not update best)
        snapshot3 = CycleSnapshot(
            cycle_number=3,
            metrics=MetricsResult(
                cycle=3,
                target=maximize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(test_accuracy=0.86),
            ),
            timestamp="2024-01-01T00:00:00",
        )
        state.add_cycle(snapshot3)

        assert state.best_metric == 0.88
        assert state.best_cycle == 2

    def test_add_cycle_updates_best_metric_minimize(self, minimize_config):
        """add_cycle should track best metric for minimize direction."""
        from ralph_ml.config import RalphState

        state = RalphState(config=minimize_config)

        # First cycle: loss 0.5
        snapshot1 = CycleSnapshot(
            cycle_number=1,
            metrics=MetricsResult(
                cycle=1,
                target=minimize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(val_loss=0.5),
            ),
            timestamp="2024-01-01T00:00:00",
        )
        state.add_cycle(snapshot1)

        assert state.best_metric == 0.5
        assert state.best_cycle == 1

        # Second cycle: loss 0.3 (better for minimize)
        snapshot2 = CycleSnapshot(
            cycle_number=2,
            metrics=MetricsResult(
                cycle=2,
                target=minimize_config.project.target_metric,
                result=MetricsResult.ResultMetrics(val_loss=0.3),
            ),
            timestamp="2024-01-01T00:00:00",
        )
        state.add_cycle(snapshot2)

        assert state.best_metric == 0.3
        assert state.best_cycle == 2
