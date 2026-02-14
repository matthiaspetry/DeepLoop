"""Orchestrator for Ralph ML Loop."""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from ralph_ml.config import (
    CycleAnalysis,
    CycleSnapshot,
    MetricsResult,
    RalphMLConfig,
    RalphState,
    Recommendation,
)


class Orchestrator:
    """Main orchestrator for Ralph ML Loop."""

    def __init__(self, config: RalphMLConfig, state_path: Optional[Path] = None):
        """Initialize orchestrator.

        Args:
            config: Configuration for the loop
            state_path: Path to save/load state (for resumability)
        """
        self.config = config
        self.state_path = state_path or config.get_paths()["state"] / "ralph_state.json"
        self.state = self._load_state()

        # Determine OpenCode path (mock or real)
        if config.agents.code_model == "mock_opencode":
            self.opencode_path = "/root/.openclaw/workspace/ralph-ml-loop/mock_opencode.py"
        else:
            self.opencode_path = "/root/.opencode/bin/opencode"

    def _load_state(self) -> RalphState:
        """Load state from file if exists, otherwise create new."""
        if self.state_path.exists():
            try:
                with open(self.state_path) as f:
                    data = json.load(f)
                return RalphState.model_validate(data)
            except Exception:
                pass
        return RalphState(config=self.config)

    def _save_state(self) -> None:
        """Save state to file."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w") as f:
            f.write(self.state.model_dump_json(indent=2))

    def _get_cycle_dir(self, cycle_num: int) -> Path:
        """Get directory for a cycle."""
        cycle_dir = self.config.get_paths()["runs"] / f"cycle_{cycle_num:04d}"
        cycle_dir.mkdir(parents=True, exist_ok=True)
        return cycle_dir

    def run(self, prompt: str) -> None:
        """Run the Ralph ML Loop.

        Args:
            prompt: User prompt describing what model to build
        """
        print(f"\n{'='*60}")
        print(f"🦕 Ralph ML Loop - {self.config.project.name}")
        print(f"{'='*60}\n")
        print(f"Prompt: {prompt}")
        print(f"Target: {self.config.project.target_metric.name} >= {self.config.project.target_metric.value}")
        print(f"Safeguards: max {self.config.safeguards.max_cycles} cycles, {self.config.safeguards.time_limit_per_cycle_minutes}min per cycle\n")
        sys.stdout.flush()

        self.state.status = "running"
        self.state.start_time = datetime.now().isoformat()

        try:
            while True:
                # Check safeguards
                if self._should_stop():
                    break

                # Run next cycle
                cycle_num = self.state.current_cycle + 1
                print(f"\n{'─'*60}")
                print(f"🔄 CYCLE {cycle_num}")
                print(f"{'─'*60}\n")
                sys.stdout.flush()

                cycle_dir = self._get_cycle_dir(cycle_num)

                # Phase 1: Code Generation
                print("📝 Phase 1: Code Generation...")
                sys.stdout.flush()
                self._phase1_codegen(cycle_dir, prompt)

                # Phase 2: Training & Validation
                print("\n🚀 Phase 2: Training & Validation...")
                sys.stdout.flush()
                metrics = self._phase2_training(cycle_dir)

                # Phase 3: Analysis
                print("\n🔍 Phase 3: Analysis...")
                sys.stdout.flush()
                analysis = self._phase3_analysis(cycle_dir, metrics, prompt)

                # Create snapshot
                snapshot = CycleSnapshot(
                    cycle_number=cycle_num,
                    metrics=metrics,
                    analysis=analysis,
                    timestamp=datetime.now().isoformat(),
                )
                self.state.add_cycle(snapshot)
                self._save_state()

                # Print results
                self._print_cycle_results(snapshot)

                # Check decision
                if analysis.decision.action == "stop":
                    print(f"\n✅ Stopping: {analysis.decision.rationale}")
                    break

                # Check max cycles
                if cycle_num >= self.config.safeguards.max_cycles:
                    print(f"\n⚠️  Max cycles ({self.config.safeguards.max_cycles}) reached")
                    break

        finally:
            self.state.status = "completed"
            self.state.last_update = datetime.now().isoformat()
            self._save_state()
            self._print_final_summary()

    def _should_stop(self) -> bool:
        """Check if we should stop before starting a cycle."""
        # Check no-improvement stop
        if len(self.state.history) >= self.config.safeguards.no_improvement_stop_cycles:
            recent_cycles = self.state.history[-self.config.safeguards.no_improvement_stop_cycles :]
            values = [
                m.metrics.result.model_dump().get(m.metrics.target.name, 0)
                for m in recent_cycles
            ]
            if all(
                v == values[0]
                for v in values
            ):  # No change in recent cycles
                print(f"\n⚠️  No improvement for {self.config.safeguards.no_improvement_stop_cycles} cycles")
                return True

        return False

    def _phase1_codegen(self, cycle_dir: Path, prompt: str) -> None:
        """Phase 1: Code generation using OpenCode.

        Args:
            cycle_dir: Directory for this cycle
            prompt: Original user prompt
        """
        context = self._build_codegen_context(cycle_dir, prompt)

        opencode_prompt = f"""Create or modify a training codebase for this task.

User Request: {prompt}

Context from previous cycles:
{context}

Requirements:
1. Create a complete, runnable training setup
2. Include: model.py, train.py, eval.py, data.py, config.json
3. Use data from: {self.config.data.root}
4. Target: {self.config.project.target_metric.name} >= {self.config.project.target_metric.value}
5. Framework: {self.config.project.framework}
6. Make it deterministic where possible (seeds)
7. Output metrics to metrics.json after training

Write the code files directly."""

        # Use a simpler approach - write prompt to file and use input
        import os

        # Create a temporary script to run opencode
        script_content = f'''#!/bin/bash
cd {self.config.get_paths()["workspace"]}
echo "{opencode_prompt}" | {self.opencode_path} run
'''

        script_path = cycle_dir / "run_opencode.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        print(f"   Running OpenCode code generation...")
        print(f"   Prompt: Create training codebase for {prompt[:50]}...")

        # Run the script
        result = subprocess.run(
            ["bash", str(script_path)],
            capture_output=True,
            text=True,
            cwd=self.config.get_paths()["workspace"],
            timeout=self.config.safeguards.time_limit_per_cycle_minutes * 60,
        )

        # Save output
        (cycle_dir / "phase1_opencode_output.txt").write_text(result.stdout)
        if result.stderr:
            (cycle_dir / "phase1_opencode_errors.txt").write_text(result.stderr)

        print(f"   ✓ Code generation complete")
        print(f"   Output: {result.stdout[:200] if result.stdout else 'No output'}")

    def _phase2_training(self, cycle_dir: Path) -> MetricsResult:
        """Phase 2: Training execution.

        Args:
            cycle_dir: Directory for this cycle

        Returns:
            Metrics result
        """
        # Run training
        train_cmd = self.config.execution.train_cmd.split()
        workspace = self.config.get_paths()["workspace"]

        start_time = time.time()

        result = subprocess.run(
            train_cmd,
            capture_output=True,
            text=True,
            cwd=workspace,
            timeout=self.config.safeguards.time_limit_per_cycle_minutes * 60,
        )

        train_seconds = time.time() - start_time

        # Save logs
        (cycle_dir / "training_stdout.txt").write_text(result.stdout)
        if result.stderr:
            (cycle_dir / "training_stderr.txt").write_text(result.stderr)

        # Load metrics if available
        metrics_path = workspace / "metrics.json"
        if metrics_path.exists():
            with open(metrics_path) as f:
                metrics_data = json.load(f)

            metrics = MetricsResult(
                cycle=self.state.current_cycle + 1,
                target=self.config.project.target_metric,
                result=MetricsResult.ResultMetrics(**metrics_data.get("result", {})),
                runtime=MetricsResult.Runtime(train_seconds=train_seconds),
            )
        else:
            # Parse from output if no metrics.json
            metrics = self._parse_metrics_from_output(result.stdout)
            metrics.cycle = self.state.current_cycle + 1
            metrics.runtime.train_seconds = train_seconds

        # Save metrics to cycle dir
        (cycle_dir / "metrics.json").write_text(metrics.model_dump_json(indent=2))

        return metrics

    def _phase3_analysis(
        self, cycle_dir: Path, metrics: MetricsResult, prompt: str
    ) -> CycleAnalysis:
        """Phase 3: Analysis using OpenCode.

        Args:
            cycle_dir: Directory for this cycle
            metrics: Metrics from training
            prompt: Original user prompt

        Returns:
            Cycle analysis
        """
        # Load context
        context = self._build_analysis_context(metrics)

        analysis_prompt = f"""Analyze the training results and recommend improvements.

Original Request: {prompt}
Target: {metrics.target.name} >= {metrics.target.value}
Achieved: {metrics.result.model_dump().get(metrics.target.name, 'N/A')}

Context:
{context}

Tasks:
1. Analyze what went well and what didn't
2. Identify specific improvements (architecture, hyperparameters, data, etc.)
3. Rank recommendations by confidence (high/medium/low)
4. Decide if we should continue or stop

Output format:
analysis.md with summary
recommendations.json with list of recommendations
decision.json with action (continue/stop) and rationale"""

        # Use script approach for OpenCode
        script_content = f'''#!/bin/bash
cd {self.config.get_paths()["workspace"]}
echo "{analysis_prompt}" | {self.opencode_path} run
'''

        script_path = cycle_dir / "run_opencode_analysis.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        print(f"   Running OpenCode analysis...")

        result = subprocess.run(
            ["bash", str(script_path)],
            capture_output=True,
            text=True,
            cwd=self.config.get_paths()["workspace"],
            timeout=self.config.safeguards.time_limit_per_cycle_minutes * 60,
        )

        # Save output
        (cycle_dir / "phase3_opencode_output.txt").write_text(result.stdout)

        # Create default analysis
        result_dict = metrics.result.model_dump()
        target_value = result_dict.get(metrics.target.name, None)
        target_met = isinstance(target_value, (int, float)) and target_value >= self.config.project.target_metric.value

        analysis = CycleAnalysis(
            summary=f"Training achieved {metrics.target.name}={target_value:.4f}. Target: {self.config.project.target_metric.value:.4f}",
            recommendations=[
                Recommendation(
                    action="Analyze and iterate" if not target_met else "Finalize model",
                    confidence="high" if not target_met else "high",
                    rationale="Target not yet met" if not target_met else "Target achieved",
                )
            ],
            decision=CycleAnalysis.Decision(
                action="stop" if target_met else "continue",
                rationale="Target met" if target_met else "Continue improving",
            ),
        )

        # Save analysis
        (cycle_dir / "analysis.json").write_text(analysis.model_dump_json(indent=2))
        (cycle_dir / "analysis.md").write_text(analysis.summary)

        print(f"   ✓ Analysis complete")

        return analysis

    def _build_codegen_context(self, cycle_dir: Path, prompt: str) -> str:
        """Build context for code generation phase."""
        if self.state.current_cycle == 0:
            return "This is the first cycle - create initial codebase."

        # Get previous analysis
        prev_snapshot = self.state.history[-1]
        prev_analysis = prev_snapshot.analysis

        context = f"""
Previous cycle ({prev_snapshot.cycle_number}) results:
- Metrics: {prev_snapshot.metrics.result.model_dump()}
- Analysis: {prev_analysis.summary}
- Recommendations: {[r.action for r in prev_analysis.recommendations]}

Apply the recommendations from the previous cycle.
"""
        return context

    def _build_analysis_context(self, metrics: MetricsResult) -> str:
        """Build context for analysis phase."""
        if not self.state.history:
            return "First cycle - baseline analysis."

        # Build metrics history
        history_lines = []
        for snapshot in self.state.history:
            value = snapshot.metrics.result.model_dump().get(snapshot.metrics.target.name, "N/A")
            history_lines.append(f"Cycle {snapshot.cycle_number}: {snapshot.metrics.target.name}={value}")

        history_str = "\n".join(history_lines)

        return f"""
Metrics history:
{history_str}

Current cycle metrics:
{metrics.result.model_dump()}

Best achieved: {self.state.best_metric} (Cycle {self.state.best_cycle})
"""

    def _parse_metrics_from_output(self, output: str) -> MetricsResult:
        """Parse metrics from training output."""
        # Simple parsing - in real implementation would be more robust
        metrics = MetricsResult(
            cycle=0,
            target=self.config.project.target_metric,
        )

        # Try to find accuracy in output
        for line in output.split("\n"):
            if "test_accuracy" in line.lower() or "test accuracy" in line.lower():
                try:
                    # Extract number
                    import re
                    match = re.search(r"[0-9.]+", line)
                    if match:
                        metrics.result.test_accuracy = float(match.group())
                except Exception:
                    pass
            elif "val_accuracy" in line.lower() or "val accuracy" in line.lower():
                try:
                    import re
                    match = re.search(r"[0-9.]+", line)
                    if match:
                        metrics.result.val_accuracy = float(match.group())
                except Exception:
                    pass

        return metrics

    def _print_cycle_results(self, snapshot: CycleSnapshot) -> None:
        """Print results of a cycle."""
        target_name = snapshot.metrics.target.name
        target_value = snapshot.metrics.result.model_dump().get(target_name, "N/A")

        print(f"\n📊 Cycle {snapshot.cycle_number} Results:")
        print(f"   {target_name}: {target_value}")
        print(f"   Target: {snapshot.metrics.target.value}")
        print(f"   Training time: {snapshot.metrics.runtime.train_seconds:.1f}s")

        if snapshot.analysis:
            print(f"\n💡 Analysis:")
            print(f"   {snapshot.analysis.summary}")
            for rec in snapshot.analysis.recommendations[:2]:  # Show top 2
                print(f"   - {rec.action} ({rec.confidence})")

    def _print_final_summary(self) -> None:
        """Print final summary."""
        print(f"\n{'='*60}")
        print(f"🏁 Ralph ML Loop Complete")
        print(f"{'='*60}\n")

        print(f"Total cycles: {self.state.current_cycle}")
        print(f"Best metric: {self.state.best_metric:.4f} (Cycle {self.state.best_cycle})")
        print(f"Target: {self.config.project.target_metric.name} >= {self.config.project.target_metric.value}")

        if self.state.history:
            print(f"\n📈 Metrics Timeline:")
            for snapshot in self.state.history:
                target_name = snapshot.metrics.target.name
                value = snapshot.metrics.result.model_dump().get(target_name, "N/A")
                print(f"   Cycle {snapshot.cycle_number}: {target_name}={value}")

        print(f"\n📁 Artifacts: {self.config.get_paths()['runs']}")
        print(f"📊 State: {self.state_path}")
