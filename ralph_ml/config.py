"""Configuration and data models for Ralph ML Loop."""

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class TargetMetric(BaseModel):
    """Target metric definition."""

    name: str = Field(..., description="Metric name (e.g., test_accuracy)")
    value: float = Field(..., description="Target value to achieve")


class ProjectConfig(BaseModel):
    """Project configuration."""

    name: str = Field(..., description="Project name")
    framework: str = Field(default="pytorch", description="ML framework")
    task: Optional[str] = Field(None, description="Task type (e.g., image-classification)")
    target_metric: TargetMetric = Field(..., description="Target metric")


class DataConfig(BaseModel):
    """Data configuration."""

    root: str = Field(default="./data", description="Root directory for data")
    train_split: str = Field(default="train", description="Training split name")
    val_split: str = Field(default="val", description="Validation split name")
    test_split: str = Field(default="test", description="Test split name")


class SafeguardsConfig(BaseModel):
    """Safeguards configuration."""

    max_cycles: int = Field(default=10, description="Maximum number of cycles")
    no_improvement_stop_cycles: int = Field(
        default=3, description="Stop after N cycles without improvement"
    )
    min_improvement_delta: float = Field(
        default=0.002, description="Minimum improvement delta to count as progress"
    )
    time_limit_per_cycle_minutes: int = Field(
        default=30, description="Time limit per cycle"
    )
    token_budget_per_cycle: int = Field(
        default=100000, description="Token budget per cycle"
    )


class ExecutionConfig(BaseModel):
    """Execution configuration."""

    mode: str = Field(default="local", description="Execution mode (local/container/cloud)")
    python: str = Field(default="python", description="Python interpreter")
    train_cmd: str = Field(default="python train.py --config config.json", description="Training command")
    eval_cmd: str = Field(default="python eval.py --config config.json", description="Evaluation command")
    env_capture: bool = Field(default=True, description="Capture environment info")


class AgentsConfig(BaseModel):
    """Agents configuration."""

    code_model: str = Field(default="opencode", description="Code generation model")
    analysis_model: str = Field(default="opencode", description="Analysis model")
    thinking: str = Field(default="medium", description="Thinking level (low/medium/high)")


class PathsConfig(BaseModel):
    """Paths configuration."""

    workspace: str = Field(default="./workspace", description="Workspace directory")
    runs: str = Field(default="./runs", description="Runs directory")
    reports: str = Field(default="./reports", description="Reports directory")
    state: str = Field(default="./state", description="State directory")


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    logger: str = Field(default="tensorboard", description="Logger type (tensorboard/wandb/mlflow)")
    save_stdout: bool = Field(default=True, description="Save stdout to file")
    emit_events_jsonl: bool = Field(default=True, description="Emit events to JSONL")


class RalphMLConfig(BaseModel):
    """Main configuration for Ralph ML Loop."""

    project: ProjectConfig = Field(..., description="Project configuration")
    data: DataConfig = Field(default_factory=DataConfig, description="Data configuration")
    safeguards: SafeguardsConfig = Field(default_factory=SafeguardsConfig, description="Safeguards")
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig, description="Execution settings")
    agents: AgentsConfig = Field(default_factory=AgentsConfig, description="Agent settings")
    paths: PathsConfig = Field(default_factory=PathsConfig, description="Path settings")
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig, description="Observability settings")

    def get_paths(self) -> dict[str, Path]:
        """Get all paths as Path objects."""
        return {
            "workspace": Path(self.paths.workspace),
            "runs": Path(self.paths.runs),
            "reports": Path(self.paths.reports),
            "state": Path(self.paths.state),
            "data": Path(self.data.root),
        }

    def create_directories(self) -> None:
        """Create all required directories."""
        paths = self.get_paths()
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)


class MetricsResult(BaseModel):
    """Metrics result from a cycle."""

    cycle: int = Field(..., description="Cycle number")
    target: TargetMetric = Field(..., description="Target metric")

    class ResultMetrics(BaseModel):
        """Result metrics."""

        test_accuracy: Optional[float] = None
        val_accuracy: Optional[float] = None
        train_loss: Optional[float] = None
        val_loss: Optional[float] = None

    result: ResultMetrics = Field(default_factory=ResultMetrics, description="Result metrics")

    class Runtime(BaseModel):
        """Runtime metrics."""

        train_seconds: float = 0.0
        eval_seconds: float = 0.0

    runtime: Runtime = Field(default_factory=Runtime, description="Runtime metrics")

    class Resources(BaseModel):
        """Resource metrics."""

        gpu: Optional[str] = None
        vram_gb: Optional[float] = None
        peak_mem_gb: Optional[float] = None

    resources: Resources = Field(default_factory=Resources, description="Resource metrics")


class Recommendation(BaseModel):
    """A single recommendation."""

    action: str = Field(..., description="Action to take")
    confidence: str = Field(..., description="Confidence level (high/medium/low)")
    rationale: str = Field(..., description="Rationale for this recommendation")


class CycleAnalysis(BaseModel):
    """Analysis result from a cycle."""

    summary: str = Field(..., description="Summary of analysis")
    recommendations: list[Recommendation] = Field(default_factory=list, description="Recommendations")

    class Decision(BaseModel):
        """Decision to continue or stop."""

        action: str = Field(..., description="Action (continue/stop)")
        rationale: str = Field(..., description="Rationale for decision")

    decision: Decision = Field(..., description="Decision")


class CycleSnapshot(BaseModel):
    """Snapshot of a cycle."""

    cycle_number: int
    metrics: MetricsResult
    analysis: Optional[CycleAnalysis] = None
    timestamp: str
    git_commit: Optional[str] = None


class RalphState(BaseModel):
    """Orchestrator state (resumable)."""

    config: RalphMLConfig
    current_cycle: int = Field(default=0, description="Current cycle number")
    best_metric: float = Field(0.0, description="Best metric achieved so far")
    best_cycle: int = Field(0, description="Cycle number with best metric")
    history: list[CycleSnapshot] = Field(default_factory=list, description="Cycle history")
    status: str = Field(default="idle", description="Current status")
    start_time: Optional[str] = None
    last_update: Optional[str] = None

    def add_cycle(self, snapshot: CycleSnapshot) -> None:
        """Add a cycle to history."""
        self.history.append(snapshot)
        self.current_cycle = snapshot.cycle_number

        # Update best metric
        target_name = snapshot.metrics.target.name
        if target_name in snapshot.metrics.result.model_dump():
            current_value = snapshot.metrics.result.model_dump()[target_name]
            if isinstance(current_value, (int, float)) and current_value > self.best_metric:
                self.best_metric = current_value
                self.best_cycle = snapshot.cycle_number

    def has_improved(self, previous_metric: float, min_delta: float) -> bool:
        """Check if there's improvement."""
        return self.best_metric - previous_metric >= min_delta
