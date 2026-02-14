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
- **Modularity:** Clean separation of concerns for maintainability.

---

## High-Level Architecture

```
                        ┌─────────────────────────────────────┐
                        │      User config + target           │
                        └──────────────────┬──────────────────┘
                                           │
                                           ▼
                        ┌─────────────────────────────────────┐
                        │           Orchestrator               │
                        │  (State machine + safeguard enforcement)│
                        └──────────────────┬──────────────────┘
                                           │
                     ┌──────────────────────┼──────────────────────┐
                     │                      │                      │
                     ▼                      ▼                      ▼
         ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
         │     Phase 1         │  │     Phase 2         │  │     Phase 3         │
         │  Code Generation    │  │  Train + Validate   │  │  Analysis + Recs    │
         │     (Agent)         │─▶│     (Executor)      │─▶│      (Agent)        │
         └──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘
                    │                        │                        │
                    │                        │                        │
                    └────────────────────────┼────────────────────────┘
                                             │
                                             ▼
                                   ┌─────────────────────┐
                                   │   Decision Engine   │
                                   │  ─────────────────   │
                                   │  • Target met?      │
                                   │  • Safeguards ok?   │
                                   │  • Continue?        │
                                   └──────────┬──────────┘
                                              │
                           ┌──────────────────┴──────────────────┐
                           │                                     │
                      Continue                                 Stop
                           │                                     │
                           ▼                                     ▼
               ┌─────────────────────┐               ┌─────────────────────┐
               │   Next Cycle (N+1)  │               │  Final Report +     │
               └─────────────────────┘               │  Best Artifacts     │
                                                    └─────────────────────┘

                   ┌──────────────────────────────────────────┐
                   │      Shared Context + Memory             │
                   │      ──────────────────────             │
                   │  • Cycle history (all artifacts)        │
                   │  • Metrics timeline                     │
                   │  • What worked / didn't work           │
                   │  • Best checkpoints + configs          │
                   └──────────────────────────────────────────┘
                                ▲
                                │ shared by all phases
                                │

                   ┌──────────────────────────────────────────┐
                   │      Monitoring Dashboard                │
                   │      ──────────────────────              │
                   │  • Live cycle status                    │
                   │  • Real-time metrics                     │
                   │  • Phase progress                        │
                   │  • Resource usage                       │
                   └──────────────────────────────────────────┘
```

---

## Module Architecture

The codebase is organized into focused modules with clear responsibilities:

```
ralph_ml/
├── orchestrator.py          # Thin coordinator - state machine & cycle management
├── stopping.py              # Stop policy logic (pure functions)
├── runtime/
│   └── process_runner.py    # Subprocess execution with heartbeats & live logs
├── phases/
│   ├── training.py          # Metrics parsing (nested/flat/final_epoch/history)
│   └── analysis.py          # Analysis loading with graceful fallbacks
├── artifacts.py             # Artifact capture & best model index
└── config.py                # Data models & configuration
```

### Module Responsibilities

**Orchestrator** (`orchestrator.py`)
- State machine management (cycle transitions)
- Delegates to specialized modules
- Persists state & artifacts
- Thin coordinator (~600 lines vs 1000+ originally)

**Stop Policy** (`stopping.py`)
- Pure functions for plateau detection
- Supports maximize/minimize metrics
- Configurable delta thresholds

**Process Runner** (`runtime/process_runner.py`)
- Subprocess execution with timeout
- Heartbeat progress reporting
- Live log streaming for training

**Phase Handlers** (`phases/`)
- `training.py`: Metrics parsing from multiple JSON formats
- `analysis.py`: Loading analysis outputs with fallback defaults

**Artifacts** (`artifacts.py`)
- Architecture log (SHA256 fingerprints)
- Source snapshots for reproducibility
- Model artifact collection
- Best model index generation

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

**Metrics Format Support:**
- Nested result: `{"result": {"test_accuracy": ...}}`
- Top-level: `{"test_accuracy": ...}`
- Final epoch: `{"final_epoch": {"test_accuracy": ...}}`
- History array: `{"history": [{"train_loss": ...}, ...]}`

### Phase 3 — Analysis + Improvement (Agent)

**Purpose:** Interpret metrics and logs to propose the next best experiment.

**Typical outputs:**
- `analysis.md`
- `recommendations.json` (ranked actions)
- `decision.json` (continue/stop + rationale)
- Optional: `ablation_plan.json`

**Fallback Behavior:**
- If files missing, generates sensible defaults
- Supports both list and nested JSON formats
- Handles malformed files gracefully

### Decision Engine

Stops when any stop condition triggers, otherwise schedules next cycle with an updated plan.

---

## Core Components

### 1) Orchestrator

**Responsibilities:**
- Own the state machine (cycle/phase transitions)
- Enforce safeguards (delegates to `stopping.py`)
- Persist artifacts & context
- Select "best so far" checkpoint/config
- Emit structured events for the dashboard

**Key design choice:**
- Treat all phases as pure steps with explicit inputs/outputs (makes retries safe)
- Delegate to focused modules rather than monolithic implementation

### 2) Stop Policy (`stopping.py`)

Pure functions for determining when to stop:

- **Plateau detection:** Stop after N cycles with no significant improvement
- **Direction support:** Works for both maximize (accuracy) and minimize (loss) metrics
- **Configurable thresholds:** Minimum delta to count as improvement

### 3) Process Runner (`runtime/process_runner.py`)

Subprocess execution with enhanced monitoring:

- **Heartbeat mode:** Periodic progress updates for long-running tasks
- **Live log mode:** Stream stdout/stderr in real-time for training
- **Timeout handling:** Kill processes that exceed time limits
- **Universal:** Works with any subprocess, not just ML training

### 4) Phase Handlers (`phases/`)

**Training Phase** (`phases/training.py`):
- Parse metrics from multiple JSON formats
- Extract target metric from result/final_epoch/history
- Fallback to parsing from stdout if metrics.json missing

**Analysis Phase** (`phases/analysis.py`):
- Load analysis.md, recommendations.json, decision.json
- Build fallback analysis when files missing
- Merge loaded data with sensible defaults

### 5) Artifact Manager (`artifacts.py`)

Capture and preserve cycle artifacts:

- **Architecture log:** SHA256 fingerprints of source files
- **Source snapshot:** Copy of model.py, train.py, etc. for reproducibility
- **Model artifact:** Find and copy best_model.pt from various locations
- **Best model index:** JSON pointer to best cycle across all runs

### 6) Context & Memory Store

A simple, auditable structure is best:

- **Cycle snapshots:** code + config + metrics + analysis
- **Aggregated metrics:** rolling timeline for quick comparisons
- **Experience log:** "this change helped/hurt" records

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
    architecture_log.json   # File fingerprints
    source_snapshot/        # Preserved source files
    artifacts/              # Model files
  cycle_0002/
    ...
reports/
  final_report.md
  leaderboard.json     # best checkpoints/configs across cycles
state/
  ralph_state.json     # orchestrator state (resumable)
best_model_index.json  # Pointer to best cycle
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

## CLI Contract

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

## Testing

The project includes a comprehensive test suite:

```
tests/
├── conftest.py                      # Shared fixtures
├── test_orchestrator_stop_policy.py # Stop/plateau detection
├── test_orchestrator_phase2_metrics.py # Metrics parsing
├── test_orchestrator_phase3_analysis.py # Analysis fallback
├── test_orchestrator_artifacts.py   # Artifact capture
└── test_orchestrator_run_flow.py    # End-to-end flow
```

**Test characteristics:**
- 56 tests covering all major functionality
- Deterministic (< 1s execution)
- Uses mocked subprocesses (no real training)
- Isolated with `tmp_path` fixtures

---

## Roadmap

### MVP ✅ Completed
- [x] Orchestrator state machine
- [x] Local executor (subprocess)
- [x] Basic metrics contract + per-cycle folders
- [x] Simple stop conditions
- [x] CLI status output
- [x] Comprehensive test suite

### v1.0
- [x] Resumable runs (state file) ✅
- [x] Better comparison + leaderboard ✅
- [ ] Diff-based code snapshots (git integration)
- [ ] Dashboard (TUI via `rich`)

### v2.0
- [ ] Multi-task templates (NLP/CV/RL)
- [ ] Parallel experiments (branching cycles)
- [ ] MLFlow/W&B integration
- [ ] Knowledge base: pattern library of successful interventions

---

## Implementation Notes

- **Keep the orchestrator "boring":** Deterministic, testable, minimal magic. Now ~600 lines down from 1000+.
- **Treat agents as untrusted:** Validate outputs, lint, run unit checks.
- **Make every artifact addressable** by `(cycle_id, run_id)` for traceability.
- **Prefer patches over full rewrites** after cycle 1 to reduce churn.
- **Refactor safely:** Extract modules incrementally with comprehensive tests.

### Recent Refactoring (2024)

The orchestrator was refactored from a monolithic 1000+ line file into focused modules:

1. **Stop policy** extracted to `stopping.py` (48 lines)
2. **Process runner** extracted to `runtime/process_runner.py` (167 lines)
3. **Training phase** extracted to `phases/training.py` (151 lines)
4. **Analysis phase** extracted to `phases/analysis.py` (175 lines)
5. **Artifacts** extracted to `artifacts.py` (207 lines)

**Results:**
- 40% reduction in orchestrator complexity
- Each module has a single responsibility
- All 56 tests pass with zero behavior changes
- Future changes are easier and safer
