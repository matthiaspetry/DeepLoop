"""Pytest fixtures for Ralph ML Loop tests."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from ralph_ml.config import (
    CycleAnalysis,
    CycleSnapshot,
    MetricsResult,
    RalphMLConfig,
    RalphState,
    Recommendation,
    TargetMetric,
)
from ralph_ml.orchestrator import Orchestrator


@pytest.fixture
def base_config():
    """Return a minimal valid RalphMLConfig."""
    return RalphMLConfig(
        project={
            "name": "test-project",
            "framework": "pytorch",
            "target_metric": {"name": "test_accuracy", "value": 0.9},
        },
        safeguards={
            "max_cycles": 5,
            "no_improvement_stop_cycles": 3,
            "min_improvement_delta": 0.01,
        },
        agents={"code_model": "mock_opencode", "analysis_model": "mock_opencode"},
    )


@pytest.fixture
def maximize_config(base_config):
    """Return config with maximize target metric."""
    base_config.project.target_metric = TargetMetric(
        name="test_accuracy", value=0.9, direction="maximize"
    )
    return base_config


@pytest.fixture
def minimize_config(base_config):
    """Return config with minimize target metric."""
    base_config.project.target_metric = TargetMetric(
        name="val_loss", value=0.1, direction="minimize"
    )
    return base_config


@pytest.fixture
def tmp_run_path(tmp_path):
    """Return a temporary run path with standard subdirectories."""
    run_path = tmp_path / "test_run"
    (run_path / "cycles").mkdir(parents=True)
    (run_path / "workspace").mkdir(parents=True)
    (run_path / "state").mkdir(parents=True)
    (run_path / "reports").mkdir(parents=True)
    (run_path / "data").mkdir(parents=True)
    return run_path


@pytest.fixture
def orchestrator_with_paths(base_config, tmp_run_path):
    """Return orchestrator configured to use temp paths."""
    base_config.paths.workspace = str(tmp_run_path / "workspace")
    base_config.paths.runs = str(tmp_run_path / "cycles")
    base_config.paths.state = str(tmp_run_path / "state")
    base_config.paths.reports = str(tmp_run_path / "reports")
    base_config.data.root = str(tmp_run_path / "data")

    state_path = tmp_run_path / "state" / "ralph_state.json"
    return Orchestrator(base_config, state_path=state_path)


@pytest.fixture
def sample_metrics():
    """Return sample metrics result."""
    return MetricsResult(
        cycle=1,
        target=TargetMetric(name="test_accuracy", value=0.9),
        result=MetricsResult.ResultMetrics(
            test_accuracy=0.85,
            val_accuracy=0.87,
            train_loss=0.5,
            val_loss=0.45,
        ),
        runtime=MetricsResult.Runtime(train_seconds=10.0),
    )


@pytest.fixture
def sample_analysis():
    """Return sample cycle analysis."""
    return CycleAnalysis(
        summary="Test analysis summary",
        recommendations=[
            Recommendation(
                action="Increase learning rate",
                confidence="high",
                rationale="Test rationale",
            )
        ],
        decision=CycleAnalysis.Decision(
            action="continue",
            rationale="Target not met",
        ),
    )


@pytest.fixture
def sample_snapshot(sample_metrics, sample_analysis):
    """Return sample cycle snapshot."""
    return CycleSnapshot(
        cycle_number=1,
        metrics=sample_metrics,
        analysis=sample_analysis,
        timestamp=datetime.now().isoformat(),
    )


@pytest.fixture
def orchestrator_with_history(maximize_config, tmp_run_path, sample_snapshot):
    """Return orchestrator with populated history."""
    maximize_config.paths.workspace = str(tmp_run_path / "workspace")
    maximize_config.paths.runs = str(tmp_run_path / "cycles")
    maximize_config.paths.state = str(tmp_run_path / "state")
    maximize_config.paths.reports = str(tmp_run_path / "reports")
    maximize_config.data.root = str(tmp_run_path / "data")

    state_path = tmp_run_path / "state" / "ralph_state.json"
    orchestrator = Orchestrator(maximize_config, state_path=state_path)
    orchestrator.state.add_cycle(sample_snapshot)
    return orchestrator


@pytest.fixture
def mock_run_methods(monkeypatch):
    """Mock orchestrator methods that run subprocesses."""

    def mock_run_with_heartbeat(*args, **kwargs):
        return (0, "mock output", "", 1.0, False)

    def mock_training_with_logs(*args, **kwargs):
        return (0, "mock output", "", 10.0, False)

    monkeypatch.setattr(Orchestrator, "_run_with_heartbeat", mock_run_with_heartbeat)
    monkeypatch.setattr(Orchestrator, "_run_training_with_live_logs", mock_training_with_logs)


@pytest.fixture
def create_metrics_json():
    """Factory fixture to create metrics.json files."""

    def _create(path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

    return _create


@pytest.fixture
def create_workspace_files(tmp_path):
    """Factory fixture to create workspace source files."""

    def _create(workspace: Path, files: dict[str, str]):
        workspace.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            (workspace / filename).write_text(content)

    return _create
