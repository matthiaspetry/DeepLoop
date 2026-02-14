"""Download and prepare MNIST dataset for testing."""

import torch
import torchvision
import torchvision.transforms as transforms
from pathlib import Path

def download_mnist(data_dir: Path = None):
    """Download MNIST dataset.

    Args:
        data_dir: Directory to save dataset (default: ./data)
    """
    if data_dir is None:
        data_dir = Path("./data")
    else:
        data_dir = Path(data_dir)

    data_dir.mkdir(parents=True, exist_ok=True)

    print("Downloading MNIST dataset...")

    # Transform to normalize images to [0, 1]
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])

    # Download training data
    train_dataset = torchvision.datasets.MNIST(
        root=str(data_dir),
        train=True,
        download=True,
        transform=transform
    )

    # Download test data
    test_dataset = torchvision.datasets.MNIST(
        root=str(data_dir),
        train=False,
        download=True,
        transform=transform
    )

    print(f"✅ MNIST downloaded successfully!")
    print(f"   Training samples: {len(train_dataset)}")
    print(f"   Test samples: {len(test_dataset)}")
    print(f"   Data directory: {data_dir}")

    # Split training into train/val (80/20 split)
    train_size = int(0.8 * len(train_dataset))
    val_size = len(train_dataset) - train_size

    train_subset, val_subset = torch.utils.data.random_split(
        train_dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )

    print(f"   Train split: {train_size} samples")
    print(f"   Val split: {val_size} samples")

    return data_dir


if __name__ == "__main__":
    download_mnist("/root/.openclaw/workspace/ralph-ml-loop/data")
