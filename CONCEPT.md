# Ralph ML Loop
## Autonomous Deep Learning Improvement Cycle (Spec)

A Ralph ML Loop is an orchestrated, safeguard‑driven system that repeatedly:
1) generates or modifies training code, 2) runs training + evaluation, 3) analyzes results,
and 4) applies targeted improvements until a stopping condition is met.

---

## Design Goals

- **Reliable iteration:** Repeatable cycles with clear inputs/outputs.
- **Safety by default:** Hard caps on cycles, time, and token/compute spend.
- **Reproducibility:** Configs + artifacts versioned per cycle.
- **Observability:** Metrics, logs, and decisions visible in real time.
- **Portability:** Framework‑agnostic core (PyTorch/TensorFlow/JAX via adapters).

---

## High-Level Architecture

```mermaid
graph TB
    U[User config + target] --> O[Orchestrator]

    subgraph Cycle["Cycle N"]
        CG[Phase 1: Code generation (agent)] --> TR[Phase 2: Train + validate (executor)]
        TR --> AN[Phase 3: Analysis + recommendations (agent)]
        AN --> DE[Decision engine]
    end

    O --> CG
    DE -->|continue| CG
    DE -->|stop| FR[Final report + best artifacts]

    subgraph Shared["Shared context + memory"]
        H[Cycle history]
        M[Metrics timeline]
        K[What worked / didn't]
        B[Best checkpoints + configs]
    end

    TR --> Shared
    AN --> Shared
    O --> Shared
    Shared --> CG

    O --> MON[Monitoring dashboard]
    TR --> MON
    AN --> MON
    DE --> MON
```

---

## Lifecycle (What Happens Each Cycle)

### Inputs (Per Cycle)

- Project target (e.g., `test_accuracy >= 0.92`)
- Current best checkpoint + config
- Previous cycle analysis + recommendations
- Codebase state (git commit or snapshot)
- Safeguard budgets remaining (cycles/time/tokens/compute)

### Phase 1 — Code Generation (Agent)

**Purpose:** Produce a runnable training package (or patch) consistent with the target.

**Typical outputs:**
- `model.py`, `train.py`, `data.py`, `eval.py`
- `config.json` (or TOML/YAML)
- `requirements.txt` / `pyproject.toml`
- A diff or snapshot of changes

**Hard requirements:**
- Deterministic seeds (when possible)
- Single command entrypoint
- Machine-readable metrics output (`metrics.json`)

### Phase 2 — Training + Validation (Executor)

**Purpose:** Run training with the produced code/config and record artifacts.

**Typical outputs:**
- `checkpoints/` (latest + best)
- `logs/` (tensorboard/wandb/mlflow, stdout, system stats)
- `metrics.json` (train/val/test + runtime/cost)
- `env.json` (pip freeze, git hash, hardware info)

### Phase 3 — Analysis + Improvement (Agent)

**Purpose:** Interpret metrics and logs to propose the next best experiment.

**Typical outputs:**
- `analysis.md`
- `recommendations.json` (ranked actions)
- `decision.json` (continue/stop + rationale)
- Optional: `ablation_plan.json`

### Decision Engine

Stops when any stop condition triggers, otherwise schedules next cycle with an updated plan.

---

## Core Components

### 1) Orchestrator

**Responsibilities:**
- Own the state machine (cycle/phase transitions)
- Enforce safeguards
- Persist artifacts & context
- Select "best so far" checkpoint/config
- Emit structured events for the dashboard

**Key design choice:**
- Treat all phases as pure steps with explicit inputs/outputs (makes retries safe).

### 2) Context & Memory Store

A simple, auditable structure is best:

- **Cycle snapshots:** code + config + metrics + analysis
- **Aggregated metrics:** rolling timeline for quick comparisons
- **Experience log:** "this change helped/hurt" records

### 3) Training Executor

Pluggable runner:

- **Local:** Python subprocess
- **Containerized:** Docker
- **Cluster:** Kubernetes/Slurm
- **Cloud:** Managed jobs

**Must support:**
- Timeouts
- Log streaming
- Artifact collection
- Deterministic working directory per run

### 4) Agents

Two roles (can be the same model, but separate prompts/tools):

- **Code agent:** Writes patches and ensures runnable training.
- **Analysis agent:** Reads outputs and proposes next steps.

### 5) Monitoring Dashboard

**Minimum viable:**
- CLI table + live logs + phase status
- Metrics chart across cycles
- Resource usage + budgets remaining

---

## Data Model (Artifacts Per Cycle)

### Recommended Directory Layout

```
runs/
  cycle_0001/
    code_snapshot/      # optional (or git commit)
    config.json
    logs/
    checkpoints/
    metrics.json
    analysis.md
    recommendations.json
    decision.json
  cycle_0002/
    ...
reports/
  final_report.md
  leaderboard.json     # best checkpoints/configs across cycles
state/
  ralph_state.json     # orchestrator state (resumable)
```

### `metrics.json` (Minimal Contract)

```json
{
  "cycle": 1,
  "target": {
    "name": "test_accuracy",
    "value": 0.92
  },
  "result": {
    "test_accuracy": 0.784,
    "val_accuracy": 0.792,
    "train_loss": 1.23
  },
  "runtime": {
    "train_seconds": 812,
    "eval_seconds": 44
  },
  "resources": {
    "gpu": "A10",
    "vram_gb": 24,
    "peak_mem_gb": 11.2
  }
}
```

---

## Safeguards (Non-Negotiable)

| Safeguard | What it prevents | Typical default |
|-----------|------------------|------------------|
| **Max cycles** | Infinite loops | 10 |
| **No-improvement stop** | Plateauing waste | 3 cycles |
| **Time limit per cycle** | Runaway jobs | 30 min |
| **Budget per cycle** | Overspending tokens/compute | Configurable |
| **Minimum validation gate** | Training garbage configs | Configurable |
| **Manual stop/pause** | Human override | Always on |

**No-Improvement rule (example):**
Stop if the target metric fails to improve by at least `min_delta` for `N` consecutive cycles.

---

## Decision Logic (Example)

A simple, explicit policy is easier to debug:

1. **Stop immediately if:**
   - Target met
   - Max cycles reached
   - Budgets exceeded

2. **Else stop if:**
   - Plateau rule triggered (no improvement for `N`)

3. **Else continue if:**
   - Recommendations include at least one "high confidence" change
   - Validation gate is satisfied

---

## Configuration File

### `RALPH_ML_CONFIG.json` (Recommended)

```json
{
  "project": {
    "name": "cifar10-classifier",
    "framework": "pytorch",
    "task": "image-classification",
    "target_metric": {
      "name": "test_accuracy",
      "value": 0.92
    }
  },
  "data": {
    "root": "./data",
    "train_split": "train",
    "val_split": "val",
    "test_split": "test"
  },
  "safeguards": {
    "max_cycles": 10,
    "no_improvement_stop_cycles": 3,
    "min_improvement_delta": 0.002,
    "time_limit_per_cycle_minutes": 30,
    "token_budget_per_cycle": 100000
  },
  "execution": {
    "mode": "local",
    "python": "python",
    "train_cmd": "python train.py --config config.json",
    "eval_cmd": "python eval.py --config config.json",
    "env_capture": true
  },
  "agents": {
    "code_model": "opencode",
    "analysis_model": "opencode",
    "thinking": "medium"
  },
  "paths": {
    "workspace": "./workspace",
    "runs": "./runs",
    "reports": "./reports",
    "state": "./state"
  },
  "observability": {
    "logger": "tensorboard",
    "save_stdout": true,
    "emit_events_jsonl": true
  }
}
```

---

## CLI Contract (Suggested)

```
ralph-ml init --config <file>
ralph-ml start --config <file>
ralph-ml resume --state ./state/ralph_state.json
ralph-ml status
ralph-ml report --run ./runs --out ./reports/final_report.md
```

**Exit codes:**
- `0`: target met / clean stop
- `2`: stopped by safeguards
- `3`: stopped due to plateau
- `4`: unrecoverable error

---

## Roadmap

### MVP
- Orchestrator state machine
- Local executor (subprocess)
- Basic metrics contract + per-cycle folders
- Simple stop conditions
- CLI status output

### v1.0
- Resumable runs (state file)
- Better comparison + leaderboard
- Diff-based code snapshots (git integration)
- Dashboard (TUI via `rich`)

### v2.0
- Multi-task templates (NLP/CV/RL)
- Parallel experiments (branching cycles)
- MLFlow/W&B integration
- Knowledge base: pattern library of successful interventions

---

## Implementation Notes (Practical)

- **Keep the orchestrator "boring":** Deterministic, testable, minimal magic.
- **Treat agents as untrusted:** Validate outputs, lint, run unit checks.
- **Make every artifact addressable** by `(cycle_id, run_id)` for traceability.
- **Prefer patches over full rewrites** after cycle 1 to reduce churn.
