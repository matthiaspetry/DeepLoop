#!/usr/bin/env python3
"""Mock OpenCode for testing Ralph ML Loop - Supports both synthetic and MNIST."""

import json
import sys
from pathlib import Path

# Read prompt from stdin
if sys.stdin.isatty():
    print("Error: This script reads from stdin", file=sys.stderr)
    sys.exit(1)

prompt = sys.stdin.read()

# Detect if MNIST or synthetic dataset
is_mnist = "mnist" in prompt.lower() or "MNIST" in prompt
is_first_cycle = "first cycle" in prompt.lower() or "Cycle 1" in prompt

# Extract cycle number from context
cycle_number = 1
if is_first_cycle:
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

print(f"Detected cycle {cycle_number}, is_mnist={is_mnist}", file=sys.stderr)

# Base accuracies for testing
if is_mnist:
    # MNIST gets higher baseline accuracy
    base_accuracies = {1: 0.94, 2: 0.96, 3: 0.97, 4: 0.973, 5: 0.975, 6: 0.977}
else:
    base_accuracies = {1: 0.75, 2: 0.82, 3: 0.88, 4: 0.93, 5: 0.96, 6: 0.98}

target_accuracy = base_accuracies.get(cycle_number, 0.95)

workspace = Path("/root/.openclaw/workspace/ralph-ml-loop/workspace")

if is_mnist:
    # MNIST - CNN architecture
    print(f"Generating MNIST CNN code for cycle {cycle_number}", file=sys.stderr)

    # Architecture improves with cycles
    if cycle_number == 1:
        filters = 16
        hidden_units = 64
        use_bn = False
        use_dropout = False
    elif cycle_number == 2:
        filters = 32
        hidden_units = 128
        use_bn = True
        use_dropout = False
    elif cycle_number == 3:
        filters = 64
        hidden_units = 256
        use_bn = True
        use_dropout = True
    elif cycle_number >= 4:
        filters = 128
        hidden_units = 512
        use_bn = True
        use_dropout = True
    else:
        filters = 64
        hidden_units = 256
        use_bn = True
        use_dropout = True

    # Create model.py (CNN for MNIST)
    bn_conv = "        self.bn1 = nn.BatchNorm2d({})".format(filters) if use_bn else ""
    bn_fc = "        self.bn2 = nn.BatchNorm1d({})".format(hidden_units) if use_bn else ""
    dropout_line = "        self.dropout = nn.Dropout(0.3)" if use_dropout else ""

    model_code = """import torch
import torch.nn as nn
import torch.nn.functional as F

class MNISTCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, {}, 3, 1, 1)""".format(filters) + """
        self.pool = nn.MaxPool2d(2, 2)
""" + bn_conv + """
        self.conv2 = nn.Conv2d({}, {}, 3, 1, 1)
""".format(filters, filters * 2) + bn_conv.replace("bn1", "bn2") + """
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear({}*7*7, {})
        self.fc2 = nn.Linear({}, 10)
""".format(filters * 2, hidden_units, hidden_units) + dropout_line + """

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.view(-1, {}*7*7)
        x = F.relu(self.fc1(x))
        x = self.dropout(x) if hasattr(self, 'dropout') else x
        x = self.fc2(x)
        return x
""".format(filters * 2)

    (workspace / "model.py").write_text(model_code)

    # Create data.py (MNIST loader)
    data_code = """import torch
from torch.utils.data import Dataset, DataLoader
import torchvision
import torchvision.transforms as transforms

def get_mnist_dataloaders(data_dir, batch_size=64):
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])

    # Load MNIST
    train_dataset = torchvision.datasets.MNIST(
        root=data_dir,
        train=True,
        download=False,
        transform=transform
    )

    test_dataset = torchvision.datasets.MNIST(
        root=data_dir,
        train=False,
        download=False,
        transform=transform
    )

    # Split training into train/val (80/20)
    train_size = int(0.8 * len(train_dataset))
    val_size = len(train_dataset) - train_size

    train_subset, val_subset = torch.utils.data.random_split(
        train_dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )

    train_loader = DataLoader(train_subset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_subset, batch_size=batch_size)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)

    return train_loader, val_loader, test_loader
"""

    (workspace / "data.py").write_text(data_code)

    # Create train.py
    train_code = """import json
import torch
import torch.nn as nn
import torch.optim as optim
from model import MNISTCNN
from data import get_mnist_dataloaders
import time

def train():
    torch.manual_seed(42)

    train_loader, val_loader, test_loader = get_mnist_dataloaders("/root/.openclaw/workspace/ralph-ml-loop/data", batch_size=64)

    model = MNISTCNN()
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    num_epochs = 5

    print("Starting MNIST training...")
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0
        correct = 0
        total = 0

        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

            _, predicted = torch.max(outputs.data, 1)
            total += y_batch.size(0)
            correct += (predicted == y_batch).sum().item()

        train_accuracy = correct / total

        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                outputs = model(X_batch)
                _, predicted = torch.max(outputs.data, 1)
                val_total += y_batch.size(0)
                val_correct += (predicted == y_batch).sum().item()

        val_accuracy = val_correct / val_total
        print(f"Epoch {epoch+1}/{num_epochs}, Loss: {train_loss/len(train_loader):.4f}, Train Acc: {train_accuracy:.4f}, Val Acc: {val_accuracy:.4f}")

    # Test
    model.eval()
    test_correct = 0
    test_total = 0
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            outputs = model(X_batch)
            _, predicted = torch.max(outputs.data, 1)
            test_total += y_batch.size(0)
            test_correct += (predicted == y_batch).sum().item()

    test_accuracy = test_correct / test_total
    print(f"Test Accuracy: {test_accuracy:.4f}")

    metrics = {
        "cycle": """ + str(cycle_number) + """,
        "target": {"name": "test_accuracy", "value": 0.97},
        "result": {
            "test_accuracy": """ + str(target_accuracy) + """,
            "val_accuracy": val_accuracy,
            "train_accuracy": train_accuracy,
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

if __name__ == "__main__":
    train()
"""

    (workspace / "train.py").write_text(train_code)

    # Create eval.py
    eval_code = """import torch
from model import MNISTCNN
from data import get_mnist_dataloaders

def eval():
    train_loader, val_loader, test_loader = get_mnist_dataloaders("/root/.openclaw/workspace/ralph-ml-loop/data", batch_size=64)

    model = MNISTCNN()

    model.eval()
    test_correct = 0
    test_total = 0
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            outputs = model(X_batch)
            _, predicted = torch.max(outputs.data, 1)
            test_total += y_batch.size(0)
            test_correct += (predicted == y_batch).sum().item()

    test_accuracy = test_correct / test_total
    print(f"Evaluation Accuracy: {test_accuracy:.4f}")

if __name__ == "__main__":
    eval()
"""

    (workspace / "eval.py").write_text(eval_code)

else:
    # Synthetic - MLP architecture
    print(f"Generating synthetic MLP code for cycle {cycle_number}", file=sys.stderr)

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

    # Create model.py with progressive improvements
    layers_list = [
        "        layers_list.append(nn.Linear(input_dim, hidden_dim))",
    ]
    if use_bn:
        layers_list.append("        layers_list.append(nn.BatchNorm1d(hidden_dim))")
    layers_list.append("        layers_list.append(nn.ReLU())")
    if use_dropout:
        layers_list.append("        layers_list.append(nn.Dropout(0.3))")

    for i in range(layers - 1):
        layers_list.append("        layers_list.append(nn.Linear(hidden_dim, hidden_dim))")
        if use_bn:
            layers_list.append("        layers_list.append(nn.BatchNorm1d(hidden_dim))")
        layers_list.append("        layers_list.append(nn.ReLU())")
        if use_dropout:
            layers_list.append("        layers_list.append(nn.Dropout(0.3))")

    layers_list.append("        layers_list.append(nn.Linear(hidden_dim, num_classes))")
    layers_list.append("        self.network = nn.Sequential(*layers_list)")

    model_code = """import torch
import torch.nn as nn

class SimpleClassifier(nn.Module):
    def __init__(self, input_dim=20, hidden_dim={}, num_classes=10):
        super().__init__()
        layers_list = []
{}
        for i in range({}):
            {}
        {}

    def forward(self, x):
        return self.network(x)
""".format(hidden_dim, "\n".join(layers_list), layers - 1,
             "\n        for i in range({}):".format(layers - 1) +
             "\n            layers_list.append(nn.Linear(hidden_dim, hidden_dim))" +
             ("\n        layers_list.append(nn.BatchNorm1d(hidden_dim))" if use_bn else "") +
             "\n        layers_list.append(nn.ReLU())" +
             ("\n        layers_list.append(nn.Dropout(0.3))" if use_dropout else ""))

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

    # Create train.py (synthetic)
    train_code = """import json
import torch
import torch.nn as nn
import torch.optim as optim
from model import SimpleClassifier
from data import get_dataloaders

def train():
    torch.manual_seed(42)

    train_loader, val_loader, test_loader = get_dataloaders("/root/.openclaw/workspace/ralph-ml-loop/data", batch_size=32)

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

if __name__ == "__main__":
    train()
"""

    (workspace / "train.py").write_text(train_code)

    # Create eval.py (synthetic)
    eval_code = """import torch
from model import SimpleClassifier
from data import get_dataloaders

def eval():
    train_loader, val_loader, test_loader = get_dataloaders("/root/.openclaw/workspace/ralph-ml-loop/data", batch_size=32)

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

# Common files for both cases
config_code = {
    "dataset": "mnist" if is_mnist else "synthetic",
    "cycles": cycle_number
}
(workspace / "config.json").write_text(json.dumps(config_code, indent=2))

requirements_code = """torch>=2.0.0
numpy>=1.24.0
"""
if is_mnist:
    requirements_code += "torchvision>=0.15.0\n"
else:
    requirements_code += "scikit-learn>=1.3.0\n"

(workspace / "requirements.txt").write_text(requirements_code)

print("Mock OpenCode complete!")
