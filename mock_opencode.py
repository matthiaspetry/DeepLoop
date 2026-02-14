#!/usr/bin/env python3
"""Mock OpenCode for testing Ralph ML Loop - Simplified version."""

import json
import sys
from pathlib import Path

# Read prompt from stdin
if sys.stdin.isatty():
    print("Error: This script reads from stdin", file=sys.stderr)
    sys.exit(1)

prompt = sys.stdin.read()

# Extract cycle number from context
cycle_number = 1
if "first cycle" in prompt.lower() or "Cycle 1" in prompt:
    cycle_number = 1
elif "Previous cycle (1)" in prompt or "previous cycle (1)" in prompt:
    cycle_number = 2
elif "Previous cycle (2)" in prompt or "previous cycle (2)" in prompt:
    cycle_number = 3
elif "Previous cycle (3)" in prompt or "previous cycle (3)" in prompt:
    cycle_number = 4
elif "Previous cycle (4)" in prompt or "previous cycle (4)" in prompt:
    cycle_number = 5
elif "Previous cycle (5)" in prompt or "previous cycle (5)" in prompt:
    cycle_number = 6

print(f"Detected cycle {cycle_number}", file=sys.stderr)

# Base accuracies for testing
base_accuracies = {1: 0.75, 2: 0.82, 3: 0.88, 4: 0.93, 5: 0.96, 6: 0.98}
target_accuracy = base_accuracies.get(cycle_number, 0.95)

# Model architecture improves with cycles
if cycle_number == 1:
    hidden_dim = 32
    layers = 1
    use_bn = False
    use_dropout = False
elif cycle_number == 2:
    hidden_dim = 64
    layers = 2
    use_bn = False
    use_dropout = False
elif cycle_number == 3:
    hidden_dim = 128
    layers = 2
    use_bn = True
    use_dropout = True
elif cycle_number >= 4:
    hidden_dim = 256
    layers = 3
    use_bn = True
    use_dropout = True
else:
    hidden_dim = 128
    layers = 2
    use_bn = True
    use_dropout = True

workspace = Path("/root/.openclaw/workspace/ralph-ml-loop/workspace")

# Create model.py
model_code = """import torch
import torch.nn as nn

class SimpleClassifier(nn.Module):
    def __init__(self, input_dim=20, hidden_dim={}, num_classes=10):
        super().__init__()
        layers_list = []
        layers_list.append(nn.Linear(input_dim, hidden_dim))""".format(hidden_dim)

if use_bn:
    model_code += """
        layers_list.append(nn.BatchNorm1d(hidden_dim))"""

model_code += """
        layers_list.append(nn.ReLU())"""

for i in range(layers - 1):
    model_code += """
        layers_list.append(nn.Linear(hidden_dim, hidden_dim))"""
    if use_bn:
        model_code += """
        layers_list.append(nn.BatchNorm1d(hidden_dim))"""
    model_code += """
        layers_list.append(nn.ReLU())"""
    if use_dropout:
        model_code += """
        layers_list.append(nn.Dropout(0.3))"""

model_code += """
        layers_list.append(nn.Linear(hidden_dim, num_classes))
        self.network = nn.Sequential(*layers_list)

    def forward(self, x):
        return self.network(x)
"""

(workspace / "model.py").write_text(model_code)

# Create data.py
data_code = """import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

class SyntheticDataset(Dataset):
    def __init__(self, data_dir, split="train"):
        features = np.load(f"{data_dir}/{split}/features.npy")
        labels = np.load(f"{data_dir}/{split}/labels.npy")
        self.X = torch.FloatTensor(features)
        self.y = torch.LongTensor(labels)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def get_dataloaders(data_dir, batch_size=32):
    train_dataset = SyntheticDataset(data_dir, "train")
    val_dataset = SyntheticDataset(data_dir, "val")
    test_dataset = SyntheticDataset(data_dir, "test")

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)

    return train_loader, val_loader, test_loader
"""

(workspace / "data.py").write_text(data_code)

# Create train.py
train_code = """import json
import torch
import torch.nn as nn
import torch.optim as optim
from model import SimpleClassifier
from data import get_dataloaders

def train():
    torch.manual_seed(42)

    train_loader, val_loader, test_loader = get_dataloaders("/root/.openclaw/workspace/ralph-ml-loop/data")

    model = SimpleClassifier()
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    num_epochs = 10

    print("Starting training...")
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        # Validation
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                outputs = model(X_batch)
                _, predicted = torch.max(outputs.data, 1)
                total += y_batch.size(0)
                correct += (predicted == y_batch).sum().item()

        val_accuracy = correct / total
        print(f"Epoch {epoch+1}/{num_epochs}, Loss: {train_loss/len(train_loader):.4f}, Val Acc: {val_accuracy:.4f}")

    # Test
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            outputs = model(X_batch)
            _, predicted = torch.max(outputs.data, 1)
            total += y_batch.size(0)
            correct += (predicted == y_batch).sum().item()

    test_accuracy = """ + str(target_accuracy) + """
    print(f"Test Accuracy: {test_accuracy:.4f}")

    # Save metrics
    metrics = {
        "cycle": """ + str(cycle_number) + """,
        "target": {"name": "test_accuracy", "value": 0.96},
        "result": {
            "test_accuracy": test_accuracy,
            "val_accuracy": val_accuracy,
            "train_loss": train_loss/len(train_loader)
        },
        "runtime": {
            "train_seconds": 30.0,
            "eval_seconds": 5.0
        }
    }

    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print("Training complete!")
    print(f"Metrics saved: test_accuracy={test_accuracy:.4f}")

if __name__ == "__main__":
    train()
"""

(workspace / "train.py").write_text(train_code)

# Create eval.py
eval_code = """import torch
from model import SimpleClassifier
from data import get_dataloaders

def eval():
    train_loader, val_loader, test_loader = get_dataloaders("/root/.openclaw/workspace/ralph-ml-loop/data")

    model = SimpleClassifier()
    # Load checkpoint if exists
    try:
        model.load_state_dict(torch.load("model.pth"))
    except:
        pass

    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            outputs = model(X_batch)
            _, predicted = torch.max(outputs.data, 1)
            total += y_batch.size(0)
            correct += (predicted == y_batch).sum().item()

    test_accuracy = correct / total
    print(f"Evaluation Accuracy: {test_accuracy:.4f}")

if __name__ == "__main__":
    eval()
"""

(workspace / "eval.py").write_text(eval_code)

# Create config.json
config = {
    "model": "SimpleClassifier",
    "input_dim": 20,
    "hidden_dim": hidden_dim,
    "num_classes": 10,
    "epochs": 10,
    "batch_size": 32,
    "learning_rate": 0.001,
    "data_dir": "/root/.openclaw/workspace/ralph-ml-loop/data"
}
(workspace / "config.json").write_text(json.dumps(config, indent=2))

# Create requirements.txt
(workspace / "requirements.txt").write_text("torch>=2.0.0\nnumpy>=1.24.0\n")

print("Mock OpenCode complete!")
