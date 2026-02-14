# Ralph ML Loop 🦕

Autonomous Deep Learning Improvement Cycle - A Ralph Loop for ML training.

Automatically iterates on deep learning models through cycles of code generation, training, analysis, and improvement until target metrics are met.

## Features

- 🔄 **Autonomous iteration** - AI agents continuously improve your models
- 🛡️ **Safety by default** - Hard caps on cycles, time, and resources
- 📊 **Full observability** - Metrics, logs, and decisions tracked per cycle
- 🧪 **Framework agnostic** - Works with PyTorch, TensorFlow, JAX, etc.
- 💾 **Resumable** - State can be saved and restored
- 🖥️ **CLI interface** - Easy to use command-line tool

## Quick Start

```bash
# Install
pip install -e .

# Initialize config
ralph-ml init

# Run the loop
ralph-ml start "Create an image classifier for CIFAR-10 dataset with 85% accuracy"

# Check status
ralph-ml status

# Generate report
ralph-ml report
```

## How It Works

Each cycle consists of three phases:

1. **Phase 1: Code Generation** - AI agent creates or modifies training code
2. **Phase 2: Training & Validation** - Execute training and collect metrics
3. **Phase 3: Analysis** - AI agent analyzes results and recommends improvements

The loop continues until:
- Target metric is achieved
- Max cycles reached
- No improvement for N cycles
- Manual stop

## Configuration

Edit `RALPH_ML_CONFIG.json` to configure:

- Project settings (name, framework, target metric)
- Data paths
- Safeguards (max cycles, time limits, etc.)
- Execution mode (local, container, cloud)
- Agent settings (model, thinking level)
- Paths and observability options

## Project Structure

```
ralph-ml-loop/
├── ralph_ml/           # Main package
│   ├── config.py       # Data models
│   ├── orchestrator.py # Main orchestrator
│   └── cli.py          # CLI interface
├── runs/               # Cycle outputs
│   ├── cycle_0001/
│   ├── cycle_0002/
│   └── ...
├── state/              # State files (resumable)
├── reports/            # Final reports
└── workspace/          # Generated code
```

## Safeguards

| Safeguard | Default | Purpose |
|-----------|---------|---------|
| Max cycles | 10 | Prevent infinite loops |
| No-improvement stop | 3 cycles | Stop when plateauing |
| Time limit per cycle | 30 min | Prevent runaway jobs |
| Token budget | 100k | Limit API usage |

## Example

```bash
# Start with a simple prompt
ralph-ml start "Train a neural network for MNIST digit classification with 98% accuracy"

# Monitor progress
ralph-ml status

# When complete, view results
cat runs/cycle_0004/analysis.md
```

## Requirements

- Python 3.10+
- OpenCode CLI (installed at `/root/.opencode/bin/opencode`)
- Dataset in `/data` directory

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black ralph_ml/
ruff check ralph_ml/
```

## License

MIT

---

Built with 🦕 Ralph Loop methodology - fail persistently until you succeed.
