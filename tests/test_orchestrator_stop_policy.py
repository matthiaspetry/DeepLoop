"""Tests for orchestrator stop policy logic (_should_stop)."""

import pytest

from ralph_ml.config import (
    CycleAnalysis,
    CycleSnapshot,
    MetricsResult,
    Recommendation,
    TargetMetric,
)


class TestShouldStopMaximize:
    """Test stop logic for maximize metrics (e.g., accuracy)."""

    def test_no_stop_with_few_cycles(self, maximize_config, tmp_run_path):
        """Should not stop when history has fewer than no_improvement_stop_cycles."""
        from ralph_ml.orchestrator import Orchestrator

        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.no_improvement_stop_cycles = 3

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # Add 2 cycles - less than stop threshold
        for i in range(1, 3):
            snapshot = CycleSnapshot(
                cycle_number=i,
                metrics=MetricsResult(
                    cycle=i,
                    target=maximize_config.project.target_metric,
                    result=MetricsResult.ResultMetrics(test_accuracy=0.8),
                ),
                timestamp="2024-01-01T00:00:00",
            )
            orch.state.add_cycle(snapshot)

        assert not orch._should_stop()

    def test_stop_when_all_deltas_below_threshold(self, maximize_config, tmp_run_path):
        """Should stop when no improvement for N consecutive cycles."""
        from ralph_ml.orchestrator import Orchestrator

        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.no_improvement_stop_cycles = 3
        maximize_config.safeguards.min_improvement_delta = 0.01

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # Add 3 cycles with minimal improvement (all deltas < 0.01)
        accuracies = [0.80, 0.805, 0.809]
        for i, acc in enumerate(accuracies, 1):
            snapshot = CycleSnapshot(
                cycle_number=i,
                metrics=MetricsResult(
                    cycle=i,
                    target=maximize_config.project.target_metric,
                    result=MetricsResult.ResultMetrics(test_accuracy=acc),
                ),
                timestamp="2024-01-01T00:00:00",
            )
            orch.state.add_cycle(snapshot)

        assert orch._should_stop()

    def test_no_stop_when_one_delta_meets_threshold(self, maximize_config, tmp_run_path):
        """Should not stop when at least one cycle shows significant improvement."""
        from ralph_ml.orchestrator import Orchestrator

        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.no_improvement_stop_cycles = 3
        maximize_config.safeguards.min_improvement_delta = 0.01

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # Cycle 1 -> 2: delta = 0.02 (> 0.01), Cycle 2 -> 3: delta = 0.005
        accuracies = [0.80, 0.82, 0.825]
        for i, acc in enumerate(accuracies, 1):
            snapshot = CycleSnapshot(
                cycle_number=i,
                metrics=MetricsResult(
                    cycle=i,
                    target=maximize_config.project.target_metric,
                    result=MetricsResult.ResultMetrics(test_accuracy=acc),
                ),
                timestamp="2024-01-01T00:00:00",
            )
            orch.state.add_cycle(snapshot)

        assert not orch._should_stop()

    def test_stop_when_values_identical(self, maximize_config, tmp_run_path):
        """Should stop when all values are exactly the same."""
        from ralph_ml.orchestrator import Orchestrator

        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.no_improvement_stop_cycles = 3

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # All same accuracy
        for i in range(1, 4):
            snapshot = CycleSnapshot(
                cycle_number=i,
                metrics=MetricsResult(
                    cycle=i,
                    target=maximize_config.project.target_metric,
                    result=MetricsResult.ResultMetrics(test_accuracy=0.85),
                ),
                timestamp="2024-01-01T00:00:00",
            )
            orch.state.add_cycle(snapshot)

        assert orch._should_stop()


class TestShouldStopMinimize:
    """Test stop logic for minimize metrics (e.g., loss)."""

    def test_stop_when_loss_not_decreasing(self, minimize_config, tmp_run_path):
        """Should stop when loss doesn't decrease significantly."""
        from ralph_ml.orchestrator import Orchestrator

        minimize_config.paths.workspace = str(tmp_run_path / "workspace")
        minimize_config.paths.runs = str(tmp_run_path / "cycles")
        minimize_config.paths.state = str(tmp_run_path / "state")
        minimize_config.data.root = str(tmp_run_path / "data")
        minimize_config.safeguards.no_improvement_stop_cycles = 3
        minimize_config.safeguards.min_improvement_delta = 0.05

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(minimize_config, state_path=state_path)

        # Losses: 0.5 -> 0.48 -> 0.46 (deltas 0.02, 0.02 both < 0.05)
        losses = [0.5, 0.48, 0.46]
        for i, loss in enumerate(losses, 1):
            snapshot = CycleSnapshot(
                cycle_number=i,
                metrics=MetricsResult(
                    cycle=i,
                    target=minimize_config.project.target_metric,
                    result=MetricsResult.ResultMetrics(val_loss=loss),
                ),
                timestamp="2024-01-01T00:00:00",
            )
            orch.state.add_cycle(snapshot)

        assert orch._should_stop()

    def test_no_stop_when_loss_decreasing(self, minimize_config, tmp_run_path):
        """Should not stop when loss is decreasing significantly."""
        from ralph_ml.orchestrator import Orchestrator

        minimize_config.paths.workspace = str(tmp_run_path / "workspace")
        minimize_config.paths.runs = str(tmp_run_path / "cycles")
        minimize_config.paths.state = str(tmp_run_path / "state")
        minimize_config.data.root = str(tmp_run_path / "data")
        minimize_config.safeguards.no_improvement_stop_cycles = 3
        minimize_config.safeguards.min_improvement_delta = 0.05

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(minimize_config, state_path=state_path)

        # Losses: 0.5 -> 0.44 -> 0.39 (delta 0.06 > 0.05)
        losses = [0.5, 0.44, 0.39]
        for i, loss in enumerate(losses, 1):
            snapshot = CycleSnapshot(
                cycle_number=i,
                metrics=MetricsResult(
                    cycle=i,
                    target=minimize_config.project.target_metric,
                    result=MetricsResult.ResultMetrics(val_loss=loss),
                ),
                timestamp="2024-01-01T00:00:00",
            )
            orch.state.add_cycle(snapshot)

        assert not orch._should_stop()


class TestShouldStopEdgeCases:
    """Test edge cases in stop logic."""

    def test_empty_history(self, maximize_config, tmp_run_path):
        """Should not stop with empty history."""
        from ralph_ml.orchestrator import Orchestrator

        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        assert not orch._should_stop()

    def test_none_values_in_metrics(self, maximize_config, tmp_run_path):
        """Should handle None values gracefully."""
        from ralph_ml.orchestrator import Orchestrator

        maximize_config.paths.workspace = str(tmp_run_path / "workspace")
        maximize_config.paths.runs = str(tmp_run_path / "cycles")
        maximize_config.paths.state = str(tmp_run_path / "state")
        maximize_config.data.root = str(tmp_run_path / "data")
        maximize_config.safeguards.no_improvement_stop_cycles = 3

        state_path = tmp_run_path / "state" / "ralph_state.json"
        orch = Orchestrator(maximize_config, state_path=state_path)

        # Add cycles with None metrics
        for i in range(1, 4):
            snapshot = CycleSnapshot(
                cycle_number=i,
                metrics=MetricsResult(
                    cycle=i,
                    target=maximize_config.project.target_metric,
                    result=MetricsResult.ResultMetrics(test_accuracy=None),
                ),
                timestamp="2024-01-01T00:00:00",
            )
            orch.state.add_cycle(snapshot)

        # Should not crash, might stop or not depending on implementation
        result = orch._should_stop()
        assert isinstance(result, bool)
