"""High-value CLI behavior tests."""

import json
from pathlib import Path

from typer.testing import CliRunner

from ralph_ml.cli import app


runner = CliRunner()


def test_init_creates_default_config(tmp_path, monkeypatch):
    """init should create a default config when file does not exist."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    config_path = tmp_path / "RALPH_ML_CONFIG.json"
    assert config_path.exists()

    data = json.loads(config_path.read_text())
    assert data["project"]["name"] == "my-ml-project"
    assert data["project"]["target_metric"]["name"] == "test_accuracy"


def test_init_does_not_overwrite_existing_config(tmp_path, monkeypatch):
    """init should leave existing config untouched."""
    monkeypatch.chdir(tmp_path)

    config_path = tmp_path / "RALPH_ML_CONFIG.json"
    existing = {"project": {"name": "existing"}}
    config_path.write_text(json.dumps(existing))

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert "already exists" in result.output
    assert json.loads(config_path.read_text()) == existing


def test_start_rejects_config_and_no_config_together(tmp_path, monkeypatch):
    """start should fail fast when --config and --no-config are both used."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["start", "--config", "RALPH_ML_CONFIG.json", "--no-config", "build model"],
    )

    assert result.exit_code == 1
    assert "Use either --config or --no-config" in result.output


def test_start_rejects_missing_config(tmp_path, monkeypatch):
    """start should fail when explicit config path is missing."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["start", "--config", "missing.json", "build model"])

    assert result.exit_code == 1
    assert "Config file not found" in result.output


def test_start_no_config_creates_run_and_applies_overrides(tmp_path, monkeypatch):
    """start should create run directory and pass CLI overrides to orchestrator."""
    monkeypatch.chdir(tmp_path)

    captured: dict[str, object] = {}

    def fake_run(self, prompt):
        captured["prompt"] = prompt
        captured["config"] = self.config

    monkeypatch.setattr("ralph_ml.cli.Orchestrator.run", fake_run)

    result = runner.invoke(
        app,
        [
            "start",
            "--no-config",
            "--target",
            "0.95",
            "--max-cycles",
            "7",
            "--framework",
            "jax",
            "--data-root",
            "dataset",
            "train classifier",
        ],
    )

    assert result.exit_code == 0
    assert captured["prompt"] == "train classifier"

    config = captured["config"]
    assert config.project.target_metric.value == 0.95
    assert config.safeguards.max_cycles == 7
    assert config.project.framework == "jax"
    assert Path(config.data.root).is_absolute()
    assert Path(config.data.root).name == "dataset"

    runs_root = tmp_path / "runs"
    run_dirs = [p for p in runs_root.iterdir() if p.is_dir() and p.name.startswith("run_")]
    assert len(run_dirs) == 1

    run_dir = run_dirs[0]
    assert (run_dir / "workspace").exists()
    assert (run_dir / "cycles").exists()
    assert (run_dir / "state").exists()
    assert (run_dir / "reports").exists()

    resolved_config = run_dir / "resolved_config.json"
    assert resolved_config.exists()
    resolved_data = json.loads(resolved_config.read_text())
    assert resolved_data["project"]["framework"] == "jax"


def test_status_shows_latest_state_from_session_layout(tmp_path, monkeypatch):
    """status should discover and display latest session state file."""
    monkeypatch.chdir(tmp_path)

    runs = tmp_path / "runs"
    run1 = runs / "run_20250101_010101_000001"
    run2 = runs / "run_20250101_010102_000002"

    for run in (run1, run2):
        (run / "cycles" / "cycle_0001").mkdir(parents=True)
        (run / "state").mkdir(parents=True)

    latest_state = {
        "status": "running",
        "current_cycle": 3,
        "best_metric": 0.91,
        "best_cycle": 2,
    }
    (run2 / "state" / "ralph_state.json").write_text(json.dumps(latest_state))

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "run_20250101_010102_000002" in result.output
    assert "Current cycle: 3" in result.output
    assert "Best metric: 0.9100" in result.output


def test_report_uses_latest_session_and_writes_summary(tmp_path, monkeypatch):
    """report should auto-select latest session and generate markdown summary."""
    monkeypatch.chdir(tmp_path)

    runs = tmp_path / "runs"
    older = runs / "run_20250101_010101_000001"
    latest = runs / "run_20250101_010102_000002"

    for session in (older, latest):
        (session / "cycles").mkdir(parents=True)

    # Put a single cycle with artifacts in latest session only
    cycle_dir = latest / "cycles" / "cycle_0001"
    cycle_dir.mkdir(parents=True)
    (cycle_dir / "metrics.json").write_text(
        json.dumps(
            {
                "cycle": 1,
                "result": {"test_accuracy": 0.89},
                "runtime": {"train_seconds": 10.0},
            }
        )
    )
    (cycle_dir / "analysis.json").write_text(
        json.dumps(
            {
                "summary": "Good progress.",
                "decision": {"action": "continue"},
            }
        )
    )

    output_path = tmp_path / "reports" / "out.md"
    result = runner.invoke(app, ["report", "--run", str(runs), "--out", str(output_path)])

    assert result.exit_code == 0
    assert output_path.exists()

    report_text = output_path.read_text()
    assert "# Ralph ML Loop - Final Report" in report_text
    assert "Total cycles: 1" in report_text
    assert "### cycle_0001" in report_text
    assert "Good progress." in report_text
