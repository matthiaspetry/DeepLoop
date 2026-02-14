"""Orchestrator for Ralph ML Loop."""

import json
import os
import selectors
import shutil
import subprocess
import sys
import time
from hashlib import sha256
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ralph_ml.config import (
    CycleAnalysis,
    CycleSnapshot,
    MetricsResult,
    RalphMLConfig,
    RalphState,
    Recommendation,
)
from ralph_ml.stopping import should_stop
from ralph_ml.runtime.process_runner import run_with_heartbeat, run_training_with_live_logs
from ralph_ml.phases.training import parse_metrics_from_file, parse_metrics_from_output


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
            self.opencode_path = str(Path(__file__).resolve().parent.parent / "mock_opencode.py")
        else:
            opencode_from_env = os.getenv("OPENCODE_PATH")
            opencode_from_path = shutil.which("opencode")
            default_linux_path = "/root/.opencode/bin/opencode"

            if opencode_from_env:
                self.opencode_path = opencode_from_env
            elif opencode_from_path:
                self.opencode_path = opencode_from_path
            else:
                self.opencode_path = default_linux_path

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

    def _run_with_heartbeat(
        self,
        command: list[str],
        cwd: Path,
        timeout_seconds: int,
        phase_label: str,
        heartbeat_seconds: int = 10,
        input_text: Optional[str] = None,
    ) -> tuple[int, str, str, float, bool]:
        """Run subprocess and print periodic progress until completion."""
        return run_with_heartbeat(
            command, cwd, timeout_seconds, phase_label, heartbeat_seconds, input_text
        )

    def _run_training_with_live_logs(
        self,
        command: list[str],
        cwd: Path,
        timeout_seconds: int,
        heartbeat_seconds: int = 10,
    ) -> tuple[int, str, str, float, bool]:
        """Run training and stream stdout/stderr lines live."""
        return run_training_with_live_logs(command, cwd, timeout_seconds, heartbeat_seconds)

    def run(self, prompt: str) -> None:
        """Run the Ralph ML Loop.

        Args:
            prompt: User prompt describing what model to build
        """
        print(f"\n{'=' * 60}")
        print(f"🦕 Ralph ML Loop - {self.config.project.name}")
        print(f"{'=' * 60}\n")
        print(f"Prompt: {prompt}")
        print(
            f"Target: {self.config.project.target_metric.name} {self.config.project.target_metric.comparator_symbol()} {self.config.project.target_metric.value}"
        )
        print(
            f"Safeguards: max {self.config.safeguards.max_cycles} cycles, {self.config.safeguards.time_limit_per_cycle_minutes}min per cycle\n"
        )
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
                print(f"\n{'─' * 60}")
                print(f"🔄 CYCLE {cycle_num}")
                print(f"{'─' * 60}\n")
                sys.stdout.flush()

                cycle_dir = self._get_cycle_dir(cycle_num)

                # Phase 1: Code Generation
                print("📝 Phase 1: Code Generation...")
                sys.stdout.flush()
                self._phase1_codegen(cycle_dir, prompt)

                source_snapshot_dir = self._capture_source_snapshot(cycle_dir)
                architecture_log = self._capture_architecture_log(cycle_dir)

                # Phase 2: Training & Validation
                print("\n🚀 Phase 2: Training & Validation...")
                sys.stdout.flush()
                metrics = self._phase2_training(cycle_dir)

                best_model_artifact = self._capture_model_artifact(cycle_dir)

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
                    architecture_log=architecture_log,
                    best_model_artifact=best_model_artifact,
                    source_snapshot_dir=source_snapshot_dir,
                )
                self.state.add_cycle(snapshot)
                self._save_state()
                self._write_best_model_index()

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
            self._write_best_model_index()
            self._print_final_summary()

    def _should_stop(self) -> bool:
        """Check if we should stop before starting a cycle."""
        return should_stop(self.state, self.config)

    def _phase1_codegen(self, cycle_dir: Path, prompt: str) -> None:
        """Phase 1: Code generation using OpenCode.

        Args:
            cycle_dir: Directory for this cycle
            prompt: Original user prompt
        """
        context = self._build_codegen_context(cycle_dir, prompt)

        cycle_num = self.state.current_cycle + 1

        opencode_prompt = f"""Create or modify a training codebase for this task.

User Request: {prompt}
Cycle: {cycle_num}

Context from previous cycles:
{context}

Requirements:
1. Create a complete, runnable training setup
2. Include: model.py, train.py, eval.py, data.py, config.json
3. Use data from: {self.config.data.root}
4. Target: {self.config.project.target_metric.name} {self.config.project.target_metric.comparator_symbol()} {self.config.project.target_metric.value}
5. Framework: {self.config.project.framework}
6. Make it deterministic where possible (seeds)
7. Output metrics to metrics.json after training
8. If files already exist, update them in place and keep working parts
9. Do not rewrite from scratch unless files are missing or broken
10. Training observability is required:
    - show live progress with tqdm in train.py
    - print a clear epoch summary line (epoch, train_loss, val_loss, val_acc, test_acc) every epoch
    - ensure logs flush so progress is visible in real time in non-interactive terminals
11. Do not execute training/evaluation commands in this phase.
    - Do not run python train.py, python eval.py, pytest, or any long-running experiments.
    - Only create/update source files in this phase.

Write the code files directly."""

        workspace_path = self.config.get_paths()["workspace"].resolve()
        (cycle_dir / "phase1_prompt.txt").write_text(opencode_prompt)

        print(f"   Running OpenCode code generation...")
        print(f"   Prompt: Create training codebase for {prompt[:50]}...")
        print(f"   Workspace: {workspace_path}")
        print(f"   OpenCode: {self.opencode_path}")
        print(
            "   Logs: "
            f"{cycle_dir / 'phase1_opencode_output.txt'} and {cycle_dir / 'phase1_opencode_errors.txt'}"
        )

        returncode, stdout, stderr, elapsed, timed_out = self._run_with_heartbeat(
            command=[self.opencode_path, "run"],
            cwd=workspace_path,
            timeout_seconds=self.config.safeguards.time_limit_per_cycle_minutes * 60,
            phase_label="Phase 1 code generation",
            input_text=opencode_prompt,
        )

        # Save output
        (cycle_dir / "phase1_opencode_output.txt").write_text(stdout)
        if stderr:
            (cycle_dir / "phase1_opencode_errors.txt").write_text(stderr)

        if timed_out:
            print("   ! Code generation timed out")
        elif returncode != 0:
            print(f"   ! Code generation failed (exit {returncode})")
            if stderr:
                print(f"   Error: {stderr[:300]}")
        else:
            print(f"   ✓ Code generation complete ({elapsed:.1f}s)")
            print(f"   Output: {stdout[:200] if stdout else 'No output'}")

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
        self._ensure_workspace_data_access(workspace)

        # Remove stale metrics produced outside Phase 2
        stale_metrics = workspace / "metrics.json"
        if stale_metrics.exists():
            stale_metrics.unlink()
            print(f"   Removed stale metrics before training: {stale_metrics}")

        print(f"   Command: {' '.join(train_cmd)}")
        print(f"   Workspace: {workspace.resolve()}")
        print(
            f"   Logs: {cycle_dir / 'training_stdout.txt'} and {cycle_dir / 'training_stderr.txt'}"
        )

        returncode, train_stdout, train_stderr, train_seconds, timed_out = (
            self._run_training_with_live_logs(
                command=train_cmd,
                cwd=workspace,
                timeout_seconds=self.config.safeguards.time_limit_per_cycle_minutes * 60,
            )
        )

        # Save logs
        (cycle_dir / "training_stdout.txt").write_text(train_stdout)
        if train_stderr:
            (cycle_dir / "training_stderr.txt").write_text(train_stderr)

        if timed_out:
            print("   ! Training timed out")
        elif returncode != 0:
            print(f"   ! Training exited with code {returncode}")
            if train_stderr:
                print(f"   Error: {train_stderr[:300]}")
        else:
            print(f"   ✓ Training finished ({train_seconds:.1f}s)")

        # Load metrics if available
        metrics_path = workspace / "metrics.json"
        metrics = parse_metrics_from_file(metrics_path, self.config.project.target_metric)

        if metrics is not None:
            metrics.cycle = self.state.current_cycle + 1
            metrics.runtime.train_seconds = train_seconds

            parsed_target = metrics.result.model_dump().get(self.config.project.target_metric.name)
            print(
                f"   Parsed metrics from {metrics_path}: {self.config.project.target_metric.name}={parsed_target}"
            )
        else:
            # Parse from output if no metrics.json
            metrics = parse_metrics_from_output(train_stdout, self.config.project.target_metric)
            metrics.cycle = self.state.current_cycle + 1
            metrics.runtime.train_seconds = train_seconds

        # Save metrics to cycle dir
        (cycle_dir / "metrics.json").write_text(metrics.model_dump_json(indent=2))

        return metrics

    def _ensure_workspace_data_access(self, workspace: Path) -> None:
        """Ensure workspace-local ./data resolves to configured dataset root."""
        data_root = Path(self.config.data.root).expanduser()
        if not data_root.is_absolute():
            data_root = data_root.resolve()

        if not data_root.exists() or not data_root.is_dir():
            return

        workspace_data = workspace / "data"
        if workspace_data.exists() or workspace_data.is_symlink():
            return

        try:
            workspace_data.symlink_to(data_root, target_is_directory=True)
            print(f"   Linked workspace data: {workspace_data} -> {data_root}")
        except OSError:
            # Fallback for environments where symlinks are restricted.
            shutil.copytree(data_root, workspace_data)
            print(f"   Copied dataset into workspace: {workspace_data}")

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
Target: {metrics.target.name} {metrics.target.comparator_symbol()} {metrics.target.value}
Achieved: {metrics.result.model_dump().get(metrics.target.name, "N/A")}

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

        workspace_path = self.config.get_paths()["workspace"].resolve()
        (cycle_dir / "phase3_prompt.txt").write_text(analysis_prompt)

        print(f"   Running OpenCode analysis...")
        print(f"   Workspace: {workspace_path}")
        print(f"   OpenCode: {self.opencode_path}")
        print(
            "   Logs: "
            f"{cycle_dir / 'phase3_opencode_output.txt'} and {cycle_dir / 'phase3_opencode_errors.txt'}"
        )

        returncode, stdout, stderr, elapsed, timed_out = self._run_with_heartbeat(
            command=[self.opencode_path, "run"],
            cwd=workspace_path,
            timeout_seconds=self.config.safeguards.time_limit_per_cycle_minutes * 60,
            phase_label="Phase 3 analysis",
            input_text=analysis_prompt,
        )

        # Save output
        (cycle_dir / "phase3_opencode_output.txt").write_text(stdout)
        if stderr:
            (cycle_dir / "phase3_opencode_errors.txt").write_text(stderr)

        if timed_out:
            print("   ! Analysis timed out")
        elif returncode != 0:
            print(f"   ! Analysis exited with code {returncode}")
            if stderr:
                print(f"   Error: {stderr[:300]}")
        else:
            print(f"   ✓ Analysis completed ({elapsed:.1f}s)")

        # Build analysis from files generated by analysis phase, with safe fallbacks
        result_dict = metrics.result.model_dump()
        target_value = result_dict.get(metrics.target.name, None)
        target_met = isinstance(target_value, (int, float)) and metrics.target.target_is_met(
            float(target_value)
        )
        target_display = f"{target_value:.4f}" if isinstance(target_value, (int, float)) else "N/A"

        workspace = self.config.get_paths()["workspace"]
        analysis_md_path = workspace / "analysis.md"
        recommendations_path = workspace / "recommendations.json"
        decision_path = workspace / "decision.json"

        summary = (
            f"Training achieved {metrics.target.name}={target_display}. "
            f"Target: {self.config.project.target_metric.comparator_symbol()} {self.config.project.target_metric.value:.4f}"
        )
        if analysis_md_path.exists():
            analysis_md = analysis_md_path.read_text().strip()
            if analysis_md:
                summary = analysis_md

        recommendations: list[Recommendation] = []
        if recommendations_path.exists():
            try:
                with open(recommendations_path) as f:
                    recommendations_data = json.load(f)

                if isinstance(recommendations_data, dict):
                    raw_recommendations = recommendations_data.get("recommendations", [])
                elif isinstance(recommendations_data, list):
                    raw_recommendations = recommendations_data
                else:
                    raw_recommendations = []

                for item in raw_recommendations:
                    if isinstance(item, dict):
                        recommendations.append(
                            Recommendation(
                                action=str(item.get("action", "Analyze and iterate")),
                                confidence=str(item.get("confidence", "medium")),
                                rationale=str(item.get("rationale", "No rationale provided")),
                            )
                        )
            except Exception:
                recommendations = []

        if not recommendations:
            recommendations = [
                Recommendation(
                    action="Analyze and iterate" if not target_met else "Finalize model",
                    confidence="high",
                    rationale="Target not yet met" if not target_met else "Target achieved",
                )
            ]

        decision_action = "stop" if target_met else "continue"
        decision_rationale = (
            "Target met for optimization direction"
            if target_met
            else "Continue improving toward optimization objective"
        )

        if decision_path.exists():
            try:
                with open(decision_path) as f:
                    decision_data = json.load(f)

                if (
                    isinstance(decision_data, dict)
                    and "decision" in decision_data
                    and isinstance(decision_data["decision"], dict)
                ):
                    decision_data = decision_data["decision"]

                if isinstance(decision_data, dict):
                    parsed_action = str(decision_data.get("action", decision_action)).lower()
                    if parsed_action in {"continue", "stop"}:
                        decision_action = parsed_action
                    decision_rationale = str(decision_data.get("rationale", decision_rationale))
            except Exception:
                pass

        analysis = CycleAnalysis(
            summary=summary,
            recommendations=recommendations,
            decision=CycleAnalysis.Decision(
                action=decision_action,
                rationale=decision_rationale,
            ),
        )

        # Save analysis
        (cycle_dir / "analysis.json").write_text(analysis.model_dump_json(indent=2))
        (cycle_dir / "analysis.md").write_text(analysis.summary)

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
- Recommendations: {[{"action": r.action, "confidence": r.confidence, "rationale": r.rationale} for r in prev_analysis.recommendations]}
{f"- Architecture changes: {prev_snapshot.architecture_log.get('changed_files', [])}" if prev_snapshot.architecture_log else ""}

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
            history_lines.append(
                f"Cycle {snapshot.cycle_number}: {snapshot.metrics.target.name}={value}"
            )

        history_str = "\n".join(history_lines)

        return f"""
Metrics history:
{history_str}

Current cycle metrics:
{metrics.result.model_dump()}

Objective: {self.config.project.target_metric.get_direction()} {self.config.project.target_metric.name}
Best achieved: {self.state.best_metric} (Cycle {self.state.best_cycle})
"""

    def _print_cycle_results(self, snapshot: CycleSnapshot) -> None:
        """Print results of a cycle."""
        target_name = snapshot.metrics.target.name
        target_value = snapshot.metrics.result.model_dump().get(target_name, "N/A")

        print(f"\n📊 Cycle {snapshot.cycle_number} Results:")
        print(f"   {target_name}: {target_value}")
        print(
            f"   Target: {snapshot.metrics.target.comparator_symbol()} {snapshot.metrics.target.value}"
        )
        print(f"   Training time: {snapshot.metrics.runtime.train_seconds:.1f}s")

        if isinstance(target_value, (int, float)):
            met = snapshot.metrics.target.target_is_met(float(target_value))
            print(f"   Target met: {'yes' if met else 'no'}")

        if snapshot.architecture_log:
            print(f"   Architecture changes: {snapshot.architecture_log.get('changed_files', [])}")

        if snapshot.best_model_artifact:
            print(f"   Model artifact: {snapshot.best_model_artifact}")

        if snapshot.analysis:
            print(f"\n💡 Analysis:")
            print(f"   {snapshot.analysis.summary}")
            for rec in snapshot.analysis.recommendations[:2]:  # Show top 2
                print(f"   - {rec.action} ({rec.confidence})")

    def _print_final_summary(self) -> None:
        """Print final summary."""
        print(f"\n{'=' * 60}")
        print(f"🏁 Ralph ML Loop Complete")
        print(f"{'=' * 60}\n")

        print(f"Total cycles: {self.state.current_cycle}")
        if self.state.best_metric is None:
            print("Best metric: N/A")
        else:
            print(f"Best metric: {self.state.best_metric:.4f} (Cycle {self.state.best_cycle})")
        print(
            f"Target: {self.config.project.target_metric.name} {self.config.project.target_metric.comparator_symbol()} {self.config.project.target_metric.value}"
        )

        if self.state.best_cycle > 0 and len(self.state.history) >= self.state.best_cycle:
            best_snapshot = self.state.history[self.state.best_cycle - 1]
            if best_snapshot.best_model_artifact:
                print(f"Best model artifact: {best_snapshot.best_model_artifact}")
            if best_snapshot.architecture_log:
                arch_path = best_snapshot.architecture_log.get("log_path")
                if arch_path:
                    print(f"Best architecture log: {arch_path}")
            if best_snapshot.source_snapshot_dir:
                print(f"Best source snapshot: {best_snapshot.source_snapshot_dir}")

        if self.state.history:
            print(f"\n📈 Metrics Timeline:")
            for snapshot in self.state.history:
                target_name = snapshot.metrics.target.name
                value = snapshot.metrics.result.model_dump().get(target_name, "N/A")
                print(f"   Cycle {snapshot.cycle_number}: {target_name}={value}")

        print(f"\n📁 Artifacts: {self.config.get_paths()['runs']}")
        print(f"📊 State: {self.state_path}")

    def _capture_architecture_log(self, cycle_dir: Path) -> dict[str, Any]:
        """Capture architecture-relevant file fingerprints for this cycle."""
        workspace = self.config.get_paths()["workspace"]
        tracked_files = ["model.py", "train.py", "eval.py", "data.py", "config.json"]

        previous_hashes: dict[str, str] = {}
        if self.state.history:
            prev_arch = self.state.history[-1].architecture_log or {}
            prev_files = prev_arch.get("files", {}) if isinstance(prev_arch, dict) else {}
            for file_name, info in prev_files.items():
                if isinstance(info, dict) and isinstance(info.get("sha256"), str):
                    previous_hashes[file_name] = info["sha256"]

        files_payload: dict[str, Any] = {}
        changed_files: list[str] = []

        for rel_path in tracked_files:
            full_path = workspace / rel_path
            if not full_path.exists():
                files_payload[rel_path] = {"exists": False}
                continue

            content = full_path.read_text(errors="ignore")
            digest = sha256(content.encode("utf-8")).hexdigest()
            line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

            previous_digest = previous_hashes.get(rel_path)
            changed = previous_digest is None or previous_digest != digest
            if changed:
                changed_files.append(rel_path)

            files_payload[rel_path] = {
                "exists": True,
                "sha256": digest,
                "line_count": line_count,
                "bytes": full_path.stat().st_size,
                "changed_since_prev_cycle": changed,
            }

        arch_log = {
            "cycle": self.state.current_cycle + 1,
            "timestamp": datetime.now().isoformat(),
            "objective": {
                "name": self.config.project.target_metric.name,
                "target_value": self.config.project.target_metric.value,
                "direction": self.config.project.target_metric.get_direction(),
            },
            "changed_files": changed_files,
            "files": files_payload,
        }

        arch_log_path = cycle_dir / "architecture_log.json"
        arch_log["log_path"] = str(arch_log_path)
        arch_log_path.write_text(json.dumps(arch_log, indent=2))

        print(
            f"   Architecture log captured: {arch_log_path} (changed files: {changed_files or ['none']})"
        )
        return arch_log

    def _capture_source_snapshot(self, cycle_dir: Path) -> str:
        """Copy cycle source files so any cycle can be fully restored later."""
        workspace = self.config.get_paths()["workspace"]
        tracked_files = ["model.py", "train.py", "eval.py", "data.py", "config.json"]
        snapshot_dir = cycle_dir / "source_snapshot"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        for rel_path in tracked_files:
            source_path = workspace / rel_path
            if not source_path.exists() or not source_path.is_file():
                continue

            target_path = snapshot_dir / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            copied.append(rel_path)

        manifest = {
            "cycle": self.state.current_cycle + 1,
            "timestamp": datetime.now().isoformat(),
            "files": copied,
        }
        (snapshot_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(f"   Source snapshot saved: {snapshot_dir} (files: {copied or ['none']})")
        return str(snapshot_dir)

    def _capture_model_artifact(self, cycle_dir: Path) -> Optional[str]:
        """Copy best model artifact for this cycle into cycle artifacts directory."""
        workspace = self.config.get_paths()["workspace"]
        candidates = [
            workspace / "best_model.pt",
            workspace / "artifacts" / "best_model.pt",
            workspace / "outputs" / "best_model.pt",
            workspace / "model.pth",
            workspace / "checkpoint.pt",
        ]

        artifact_source = next((p for p in candidates if p.exists() and p.is_file()), None)
        if artifact_source is None:
            return None

        artifact_dir = cycle_dir / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        target_path = artifact_dir / artifact_source.name
        shutil.copy2(artifact_source, target_path)
        return str(target_path)

    def _write_best_model_index(self) -> None:
        """Write a single JSON pointer for the current best model."""
        index_path = self.state_path.parent.parent / "best_model_index.json"

        target = self.config.project.target_metric
        payload: dict[str, Any] = {
            "updated_at": datetime.now().isoformat(),
            "objective": {
                "name": target.name,
                "direction": target.get_direction(),
                "target_value": target.value,
                "comparator": target.comparator_symbol(),
            },
            "best_cycle": self.state.best_cycle,
            "best_metric": self.state.best_metric,
            "target_met": False,
            "best_model_artifact": None,
            "best_architecture_log": None,
            "best_source_snapshot": None,
        }

        if self.state.best_cycle > 0 and len(self.state.history) >= self.state.best_cycle:
            best_snapshot = self.state.history[self.state.best_cycle - 1]
            metric_value = best_snapshot.metrics.result.model_dump().get(target.name)
            if isinstance(metric_value, (int, float)):
                payload["best_metric"] = float(metric_value)
                payload["target_met"] = target.target_is_met(float(metric_value))

            if best_snapshot.best_model_artifact:
                payload["best_model_artifact"] = best_snapshot.best_model_artifact

            if best_snapshot.architecture_log and isinstance(best_snapshot.architecture_log, dict):
                payload["best_architecture_log"] = best_snapshot.architecture_log.get("log_path")

            if best_snapshot.source_snapshot_dir:
                payload["best_source_snapshot"] = best_snapshot.source_snapshot_dir

        index_path.write_text(json.dumps(payload, indent=2))
