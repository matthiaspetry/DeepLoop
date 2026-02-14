"""Training phase utilities for Ralph ML Loop."""

import json
import re
from pathlib import Path
from typing import Any

from ralph_ml.config import MetricsResult, TargetMetric


def parse_metrics_from_file(
    metrics_path: Path, target_metric: TargetMetric
) -> MetricsResult | None:
    """Parse metrics from a metrics.json file.

    Supports multiple formats:
    - Nested result: {"result": {"test_accuracy": ...}}
    - Top-level: {"test_accuracy": ...}
    - final_epoch: {"final_epoch": {"test_accuracy": ...}}
    - history: {"history": [{"train_loss": ...}, ...]}

    Args:
        metrics_path: Path to metrics.json file
        target_metric: Target metric configuration

    Returns:
        MetricsResult or None if parsing fails
    """
    if not metrics_path.exists():
        return None

    try:
        with open(metrics_path) as f:
            metrics_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

    # Support both formats:
    # 1) {"result": {"test_accuracy": ...}}
    # 2) {"test_accuracy": ..., "val_accuracy": ..., ...}
    raw_result = metrics_data.get("result")
    result_source = raw_result if isinstance(raw_result, dict) else metrics_data

    # Extract test_accuracy with fallbacks
    test_accuracy = result_source.get("test_accuracy")
    if test_accuracy is None:
        test_accuracy = result_source.get("best_test_accuracy")

    # Extract from final_epoch if needed
    final_epoch = metrics_data.get("final_epoch")
    if test_accuracy is None and isinstance(final_epoch, dict):
        test_accuracy = final_epoch.get("test_accuracy")

    # Extract losses
    train_loss = result_source.get("train_loss")
    val_loss = result_source.get("val_loss")
    if isinstance(final_epoch, dict):
        if train_loss is None:
            train_loss = final_epoch.get("train_loss")
        if val_loss is None:
            val_loss = final_epoch.get("val_loss")

    # Fallback to history for losses
    history = metrics_data.get("history")
    if isinstance(history, list) and history:
        last_entry = history[-1] if isinstance(history[-1], dict) else {}
        if train_loss is None:
            train_loss = last_entry.get("train_loss")
        if val_loss is None:
            val_loss = last_entry.get("val_loss")

    # Extract val_accuracy
    val_accuracy = result_source.get("val_accuracy")
    if val_accuracy is None:
        val_accuracy = result_source.get("best_val_accuracy")
    if val_accuracy is None and isinstance(final_epoch, dict):
        val_accuracy = final_epoch.get("val_accuracy")

    # Extract target metric
    target_name = target_metric.name
    target_value = result_source.get(target_name)
    if target_value is None and isinstance(final_epoch, dict):
        target_value = final_epoch.get(target_name)
    if target_value is None and isinstance(history, list) and history:
        last_entry = history[-1] if isinstance(history[-1], dict) else {}
        target_value = last_entry.get(target_name)

    # Build result payload
    result_payload: dict[str, Any] = {
        "test_accuracy": test_accuracy,
        "val_accuracy": val_accuracy,
        "train_loss": train_loss,
        "val_loss": val_loss,
    }
    if isinstance(target_value, (int, float)):
        result_payload[target_name] = float(target_value)

    return MetricsResult(
        cycle=0,  # Will be set by caller
        target=target_metric,
        result=MetricsResult.ResultMetrics(**result_payload),
    )


def parse_metrics_from_output(output: str, target_metric: TargetMetric) -> MetricsResult:
    """Parse metrics from training output text.

    Args:
        output: Training stdout/stderr text
        target_metric: Target metric configuration

    Returns:
        MetricsResult with parsed values
    """
    metrics = MetricsResult(
        cycle=0,
        target=target_metric,
    )

    # Try to find target metric in output
    target_name_lower = target_metric.name.lower()
    for line in output.split("\n"):
        if target_name_lower in line.lower():
            try:
                numbers = re.findall(r"[0-9]+(?:\.[0-9]+)?", line)
                if numbers:
                    setattr(
                        metrics.result,
                        target_metric.name,
                        float(numbers[-1]),
                    )
            except Exception:
                pass

        # Also look for common metrics
        if "test_accuracy" in line.lower() or "test accuracy" in line.lower():
            try:
                match = re.search(r"[0-9.]+", line)
                if match:
                    metrics.result.test_accuracy = float(match.group())
            except Exception:
                pass
        elif "val_accuracy" in line.lower() or "val accuracy" in line.lower():
            try:
                match = re.search(r"[0-9.]+", line)
                if match:
                    metrics.result.val_accuracy = float(match.group())
            except Exception:
                pass

    return metrics
