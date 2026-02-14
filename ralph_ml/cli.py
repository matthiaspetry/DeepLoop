"""CLI interface for Ralph ML Loop."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ralph_ml.config import RalphMLConfig
from ralph_ml.orchestrator import Orchestrator

app = typer.Typer(
    name="ralph-ml",
    help="Ralph ML Loop - Autonomous Deep Learning Improvement Cycle",
    add_completion=False,
)
console = Console()


@app.command()
def init(
    config: str = typer.Option(
        "RALPH_ML_CONFIG.json",
        "--config",
        "-c",
        help="Path to config file",
    ),
) -> None:
    """Initialize a new Ralph ML Loop project.

    Creates a default config file if it doesn't exist.
    """
    config_path = Path(config)

    if config_path.exists():
        console.print(f"⚠️  Config file already exists: {config_path}")
        return

    # Create default config
    default_config = RalphMLConfig(
        project={
            "name": "my-ml-project",
            "framework": "pytorch",
            "target_metric": {"name": "test_accuracy", "value": 0.85},
        }
    )

    config_path.write_text(default_config.model_dump_json(indent=2))

    console.print(f"✅ Created config file: {config_path}")
    console.print("\nEdit the config file, then run:")
    console.print(f"  ralph-ml start --config {config}")


@app.command()
def start(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (optional)",
    ),
    no_config: bool = typer.Option(
        False,
        "--no-config",
        help="Ignore RALPH_ML_CONFIG.json and use built-in defaults",
    ),
    prompt: str = typer.Argument(..., help="Prompt describing the model to build"),
    target: Optional[float] = typer.Option(
        None,
        "--target",
        help="Override target metric value",
    ),
    max_cycles: Optional[int] = typer.Option(
        None,
        "--max-cycles",
        help="Override max optimization cycles",
    ),
    data_root: Optional[str] = typer.Option(
        None,
        "--data-root",
        help="Override dataset root path",
    ),
    framework: Optional[str] = typer.Option(
        None,
        "--framework",
        help="Override framework (pytorch/tensorflow/jax)",
    ),
) -> None:
    """Start the Ralph ML Loop.

    Example:
        ralph-ml start "Create an image classifier for CIFAR-10 dataset with 85% accuracy"
    """
    default_config_path = Path("RALPH_ML_CONFIG.json")
    config_path: Optional[Path] = None

    if no_config and config is not None:
        console.print("❌ Use either --config or --no-config, not both.")
        sys.exit(1)

    if no_config:
        config_path = None
    elif config is not None:
        config_path = Path(config)
        if not config_path.exists():
            console.print(f"❌ Config file not found: {config_path}")
            sys.exit(1)
    elif default_config_path.exists():
        config_path = default_config_path

    if config_path is not None:
        with open(config_path) as f:
            config_data = json.load(f)
        ralph_config = RalphMLConfig.model_validate(config_data)
        console.print(f"📄 Using config: {config_path}")
    else:
        ralph_config = RalphMLConfig(
            project={
                "name": "quickstart-ml-project",
                "framework": "pytorch",
                "target_metric": {"name": "test_accuracy", "value": 0.90},
            }
        )
        console.print("⚙️  No config file found. Using built-in defaults.")

    # Optional CLI overrides
    if target is not None:
        ralph_config.project.target_metric.value = target
    if max_cycles is not None:
        ralph_config.safeguards.max_cycles = max_cycles
    if data_root is not None:
        ralph_config.data.root = data_root
    if framework is not None:
        ralph_config.project.framework = framework

    # Resolve data root to absolute path before relocating run workspace.
    # This prevents generated training code from looking for ./data inside
    # runs/<run_id>/workspace instead of the project-level dataset directory.
    ralph_config.data.root = str(Path(ralph_config.data.root).expanduser().resolve())

    # Create an isolated run directory for each start invocation
    base_runs_dir = Path(ralph_config.paths.runs)
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")
    run_root = base_runs_dir / run_id

    ralph_config.paths.workspace = str(run_root / "workspace")
    ralph_config.paths.runs = str(run_root / "cycles")
    ralph_config.paths.reports = str(run_root / "reports")
    ralph_config.paths.state = str(run_root / "state")

    # Create directories
    ralph_config.create_directories()
    console.print(f"📁 Run directory: {run_root}")

    # Persist resolved run config for reproducibility
    resolved_config_path = run_root / "resolved_config.json"
    resolved_config_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_config_path.write_text(ralph_config.model_dump_json(indent=2))

    # Run orchestrator
    orchestrator = Orchestrator(ralph_config)
    orchestrator.run(prompt)


@app.command()
def resume(
    state: str = typer.Option(
        "./state/ralph_state.json",
        "--state",
        "-s",
        help="Path to state file",
    ),
) -> None:
    """Resume a previous Ralph ML Loop run.

    Use this to continue from a saved state.
    """
    state_path = Path(state)

    if not state_path.exists():
        console.print(f"❌ State file not found: {state_path}")
        sys.exit(1)

    # Load state
    with open(state_path) as f:
        state_data = json.load(f)

    # Reconstruct config from state
    ralph_config = RalphMLConfig.model_validate(state_data["config"])

    # Create orchestrator with existing state
    orchestrator = Orchestrator(ralph_config, state_path=state_path)

    console.print(f"🔄 Resuming from cycle {orchestrator.state.current_cycle}")
    if orchestrator.state.best_metric is None:
        console.print("Best metric so far: N/A")
    else:
        console.print(f"Best metric so far: {orchestrator.state.best_metric:.4f}")

    # Continue from where we left off
    # Note: This is a simplified version - in a real implementation,
    # you'd need to track the original prompt or extract it from somewhere
    console.print("\n⚠️  Resume functionality requires the original prompt.")
    console.print("Please use 'start' with the same prompt to continue manually.")


@app.command()
def status() -> None:
    """Show status of recent runs."""
    runs_dir = Path("./runs")

    console.print("\n📊 Ralph ML Loop Status\n")

    # Show runs
    if runs_dir.exists():
        run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()])

        if run_dirs:
            table = Table(title="Cycle Runs")
            table.add_column("Cycle", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Path", style="dim")

            for run_dir in run_dirs[:10]:  # Show last 10
                name = run_dir.name

                # Legacy layout: runs/cycle_0001
                if (run_dir / "metrics.json").exists() or run_dir.name.startswith("cycle_"):
                    has_metrics = (run_dir / "metrics.json").exists()
                    status = "✅ Complete" if has_metrics else "⏳ Incomplete"
                    table.add_row(name, status, str(run_dir))
                    continue

                # Session layout: runs/run_YYYY.../cycles/cycle_0001
                cycles_dir = run_dir / "cycles"
                if cycles_dir.exists():
                    cycle_dirs = sorted([d for d in cycles_dir.iterdir() if d.is_dir()])
                    completed = sum(1 for d in cycle_dirs if (d / "metrics.json").exists())
                    status = f"🧪 Session ({completed}/{len(cycle_dirs)} cycles)"
                    table.add_row(name, status, str(run_dir))
                    continue

                table.add_row(name, "❓ Unknown", str(run_dir))

            console.print(table)
        else:
            console.print("No runs found.")
    else:
        console.print("No runs directory found.")

    # Show latest state (session layout first, then legacy)
    state_file: Optional[Path] = None
    if runs_dir.exists():
        session_states = sorted(runs_dir.glob("run_*/state/ralph_state.json"))
        if session_states:
            state_file = session_states[-1]

    if state_file is None:
        legacy_state_file = Path("./state/ralph_state.json")
        if legacy_state_file.exists():
            state_file = legacy_state_file

    if state_file and state_file.exists():
        with open(state_file) as f:
            state_data = json.load(f)

        console.print(f"\n📁 State: {state_file}")
        console.print(f"   Status: {state_data.get('status', 'unknown')}")
        console.print(f"   Current cycle: {state_data.get('current_cycle', 0)}")
        best_metric = state_data.get("best_metric")
        if isinstance(best_metric, (int, float)):
            console.print(f"   Best metric: {best_metric:.4f}")
        else:
            console.print("   Best metric: N/A")
        console.print(f"   Best cycle: {state_data.get('best_cycle', 0)}")


@app.command()
def report(
    run: str = typer.Option(
        "./runs",
        "--run",
        "-r",
        help="Path to runs directory",
    ),
    output: str = typer.Option(
        "./reports/final_report.md",
        "--out",
        "-o",
        help="Output report file",
    ),
) -> None:
    """Generate a final report from runs.

    Creates a summary report of all cycles and results.
    """
    runs_path = Path(run)
    output_path = Path(output)

    if not runs_path.exists():
        console.print(f"❌ Runs directory not found: {runs_path}")
        sys.exit(1)

    # Resolve cycle directories from either:
    # 1) ./runs (auto-pick latest session),
    # 2) session root (runs/run_...)
    # 3) explicit cycles dir
    # 4) legacy runs dir containing cycle_*
    resolved_cycles_path = runs_path

    if runs_path.name.startswith("run_") and (runs_path / "cycles").exists():
        resolved_cycles_path = runs_path / "cycles"
    elif (runs_path / "cycles").exists() and (runs_path / "state").exists():
        resolved_cycles_path = runs_path / "cycles"
    else:
        session_dirs = sorted([d for d in runs_path.glob("run_*") if d.is_dir()])
        if session_dirs:
            latest_session = session_dirs[-1]
            latest_cycles = latest_session / "cycles"
            if latest_cycles.exists():
                resolved_cycles_path = latest_cycles
                console.print(f"ℹ️  Using latest session: {latest_session.name}")

    cycle_dirs = sorted(
        [d for d in resolved_cycles_path.iterdir() if d.is_dir() and d.name.startswith("cycle_")]
    )

    # Fallback for older layout where all subdirs under runs_path are cycles
    if not cycle_dirs and resolved_cycles_path == runs_path:
        cycle_dirs = sorted([d for d in runs_path.iterdir() if d.is_dir()])

    if not cycle_dirs:
        console.print(f"❌ No cycles found in: {resolved_cycles_path}")
        sys.exit(1)

    # Generate report
    lines = [
        "# Ralph ML Loop - Final Report",
        "",
        f"Total cycles: {len(cycle_dirs)}",
        "",
        "## Cycle Results",
        "",
    ]

    for cycle_dir in cycle_dirs:
        cycle_name = cycle_dir.name
        metrics_file = cycle_dir / "metrics.json"
        analysis_file = cycle_dir / "analysis.json"

        lines.append(f"### {cycle_name}")

        if metrics_file.exists():
            with open(metrics_file) as f:
                metrics = json.load(f)
                lines.append(f"Cycle: {metrics.get('cycle', 'N/A')}")
                lines.append(f"Result: {json.dumps(metrics.get('result', {}), indent=2)}")
                lines.append(f"Runtime: {metrics.get('runtime', {})}")

        if analysis_file.exists():
            with open(analysis_file) as f:
                analysis = json.load(f)
                lines.append(f"\nSummary: {analysis.get('summary', 'N/A')}")
                lines.append(f"Decision: {analysis.get('decision', {}).get('action', 'N/A')}")

        lines.append("")

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))

    console.print(f"✅ Report generated: {output_path}")


if __name__ == "__main__":
    app()
