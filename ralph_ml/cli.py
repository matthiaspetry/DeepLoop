"""CLI interface for Ralph ML Loop."""

import json
import sys
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
    config: str = typer.Option(
        "RALPH_ML_CONFIG.json",
        "--config",
        "-c",
        help="Path to config file",
    ),
    prompt: str = typer.Argument(..., help="Prompt describing the model to build"),
) -> None:
    """Start the Ralph ML Loop.

    Example:
        ralph-ml start "Create an image classifier for CIFAR-10 dataset with 85% accuracy"
    """
    config_path = Path(config)

    if not config_path.exists():
        console.print(f"❌ Config file not found: {config_path}")
        console.print("Run 'ralph-ml init' to create a default config.")
        sys.exit(1)

    # Load config
    with open(config_path) as f:
        config_data = json.load(f)

    ralph_config = RalphMLConfig.model_validate(config_data)

    # Create directories
    ralph_config.create_directories()

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
    console.print(f"Best metric so far: {orchestrator.state.best_metric:.4f}")

    # Continue from where we left off
    # Note: This is a simplified version - in a real implementation,
    # you'd need to track the original prompt or extract it from somewhere
    console.print("\n⚠️  Resume functionality requires the original prompt.")
    console.print("Please use 'start' with the same prompt to continue manually.")


@app.command()
def status() -> None:
    """Show status of recent runs."""
    # Look for state files
    state_dir = Path("./state")
    runs_dir = Path("./runs")

    if not state_dir.exists():
        console.print("❌ No state directory found.")
        return

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
                cycle_name = run_dir.name
                has_metrics = (run_dir / "metrics.json").exists()
                status = "✅ Complete" if has_metrics else "⏳ Incomplete"

                table.add_row(cycle_name, status, str(run_dir))

            console.print(table)
        else:
            console.print("No runs found.")
    else:
        console.print("No runs directory found.")

    # Show state
    state_file = state_dir / "ralph_state.json"
    if state_file.exists():
        with open(state_file) as f:
            state_data = json.load(f)

        console.print(f"\n📁 State: {state_file}")
        console.print(f"   Status: {state_data.get('status', 'unknown')}")
        console.print(f"   Current cycle: {state_data.get('current_cycle', 0)}")
        console.print(f"   Best metric: {state_data.get('best_metric', 0):.4f}")
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

    # Collect all cycle data
    cycle_dirs = sorted([d for d in runs_path.iterdir() if d.is_dir()])

    if not cycle_dirs:
        console.print("❌ No cycles found in runs directory.")
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
