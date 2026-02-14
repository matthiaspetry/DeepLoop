# Testing Ralph ML Loop

This guide shows how to test the Ralph ML Loop MVP with a synthetic dataset.

## Quick Test

```bash
# Activate virtual environment
cd /root/.openclaw/workspace/ralph-ml-loop
source venv/bin/activate

# The dataset is already generated in /data

# Run the loop with a simple prompt
ralph-ml start --config test_config.json \
  "Create a neural network classifier for the synthetic dataset in /data. The dataset has 20 features and 10 classes. Target test accuracy: 85%."
```

## What Happens

1. **Phase 1**: OpenCode generates initial code (model, training, evaluation)
2. **Phase 2**: Training runs (synthetic dataset from `/data`)
3. **Phase 3**: Analysis reviews results and suggests improvements
4. **Loop continues** until:
   - Target accuracy (85%) is achieved
   - Max cycles (5) reached
   - No improvement for 2 consecutive cycles

## Monitor Progress

```bash
# Check status
ralph-ml status

# View cycle results
ls runs/
cat runs/cycle_0001/metrics.json
cat runs/cycle_0001/analysis.md

# Generate final report
ralph-ml report
```

## Expected Output

```
============================================================
🦕 Ralph ML Loop - synthetic-classifier
============================================================

Prompt: Create a neural network classifier...
Target: test_accuracy >= 0.85
Safeguards: max 5 cycles, 15min per cycle

────────────────────────────────────────────────────────────
🔄 CYCLE 1
────────────────────────────────────

📝 Phase 1: Code Generation...
   ✓ Code generation complete

🚀 Phase 2: Training & Validation...
   ✓ Training complete

🔍 Phase 3: Analysis...
   ✓ Analysis complete

📊 Cycle 1 Results:
   test_accuracy: 0.7623
   Target: 0.85
   Training time: 45.2s

💡 Analysis:
   Summary: Training achieved test_accuracy=0.7623. Target: 0.8500
   - Analyze and iterate (high)

────────────────────────────────────────────────────────────
🔄 CYCLE 2
────────────────────────────────────

...
```

## Dataset Details

The synthetic dataset is already generated in `/data`:

- **Train**: 7,000 samples
- **Val**: 1,000 samples
- **Test**: 2,000 samples
- **Features**: 20
- **Classes**: 10

Data is stored as NumPy arrays:
```
/data/train/features.npy
/data/train/labels.npy
/data/val/features.npy
/data/val/labels.npy
/data/test/features.npy
/data/test/labels.npy
```

## Troubleshooting

**OpenCode not found?**
```bash
# Check opencode path
ls /root/.opencode/bin/opencode
```

**Dataset not found?**
```bash
# Regenerate dataset
python scripts/generate_synthetic_data.py
```

**Training fails?**
```bash
# Check logs
cat runs/cycle_0001/training_stdout.txt
cat runs/cycle_0001/training_stderr.txt
```

## Next Steps

After successful test:
1. Try with real datasets (CIFAR-10, MNIST, etc.)
2. Experiment with different architectures
3. Adjust safeguards and targets
4. Analyze what improvements worked best
