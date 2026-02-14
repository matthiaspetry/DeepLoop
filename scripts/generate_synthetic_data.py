"""Generate a synthetic dataset for testing Ralph ML Loop."""

import json
import numpy as np
from pathlib import Path
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm


def generate_synthetic_dataset(
    output_dir: Path,
    n_samples: int = 10000,
    n_features: int = 20,
    n_classes: int = 10,
    test_size: float = 0.2,
    val_size: float = 0.1,
) -> None:
    """Generate a synthetic classification dataset.

    Args:
        output_dir: Directory to save the dataset
        n_samples: Number of samples to generate
        n_features: Number of features
        n_classes: Number of classes
        test_size: Fraction of data for test set
        val_size: Fraction of training data for validation set
    """
    output_dir = Path(output_dir)

    print(f"Generating synthetic dataset...")
    print(f"  Samples: {n_samples}")
    print(f"  Features: {n_features}")
    print(f"  Classes: {n_classes}")

    steps = tqdm(total=5, desc="Pipeline", unit="step")

    # Generate dataset
    steps.set_postfix_str("Generating data")
    X, y = make_classification(
        n_samples=n_samples,
        n_features=n_features,
        n_classes=n_classes,
        n_informative=n_features // 2,
        n_redundant=n_features // 4,
        n_clusters_per_class=1,
        random_state=42,
    )
    steps.update(1)

    # Split into train/val/test
    steps.set_postfix_str("Splitting data")
    # First split: train + val vs test
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    # Second split: train vs val
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val,
        y_train_val,
        test_size=val_size / (1 - test_size),
        random_state=42,
        stratify=y_train_val,
    )
    steps.update(1)

    # Standardize features
    steps.set_postfix_str("Scaling features")
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)
    steps.update(1)

    # Save splits
    steps.set_postfix_str("Saving splits")
    output_dir.mkdir(parents=True, exist_ok=True)

    splits = {
        "train": {"X": X_train, "y": y_train},
        "val": {"X": X_val, "y": y_val},
        "test": {"X": X_test, "y": y_test},
    }

    for split_name, data in tqdm(splits.items(), desc="Saving splits", unit="split"):
        split_dir = output_dir / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        # Save as numpy files
        np.save(split_dir / "features.npy", data["X"])
        np.save(split_dir / "labels.npy", data["y"])

        # Also save metadata
        metadata = {
            "n_samples": len(data["y"]),
            "n_features": data["X"].shape[1],
            "n_classes": len(np.unique(data["y"])),
            "shape": list(data["X"].shape),
        }
        (split_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    steps.update(1)

    # Save dataset metadata
    steps.set_postfix_str("Saving metadata")
    dataset_metadata = {
        "type": "synthetic_classification",
        "n_samples": n_samples,
        "n_features": n_features,
        "n_classes": n_classes,
        "splits": {
            "train": len(y_train),
            "val": len(y_val),
            "test": len(y_test),
        },
        "features": ["feature_" + str(i) for i in range(n_features)],
        "target": "class",
    }

    (output_dir / "dataset_metadata.json").write_text(
        json.dumps(dataset_metadata, indent=2)
    )
    steps.update(1)
    steps.close()

    print(f"\n✅ Dataset saved to: {output_dir}")
    print(f"\nSplits:")
    for name, count in dataset_metadata["splits"].items():
        print(f"  {name}: {count} samples")


if __name__ == "__main__":
    # Generate dataset in data directory
    data_dir = Path(__file__).resolve().parent.parent / "data"
    generate_synthetic_dataset(data_dir)
