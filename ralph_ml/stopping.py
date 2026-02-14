"""Stop policy logic for Ralph ML Loop."""

from typing import Optional

from ralph_ml.config import RalphMLConfig, RalphState


def should_stop(state: RalphState, config: RalphMLConfig) -> bool:
    """Check if we should stop before starting a cycle.

    Args:
        state: Current orchestrator state
        config: Configuration for the loop

    Returns:
        True if stop condition met, False otherwise
    """
    # Check no-improvement stop
    if len(state.history) >= config.safeguards.no_improvement_stop_cycles:
        recent_cycles = state.history[-config.safeguards.no_improvement_stop_cycles :]
        values = []
        for snapshot in recent_cycles:
            value = snapshot.metrics.result.model_dump().get(snapshot.metrics.target.name)
            if isinstance(value, (int, float)):
                values.append(float(value))

        if len(values) == len(recent_cycles):
            direction = config.project.target_metric.get_direction()
            min_delta = config.safeguards.min_improvement_delta
            deltas = []
            for idx in range(1, len(values)):
                if direction == "minimize":
                    deltas.append(values[idx - 1] - values[idx])
                else:
                    deltas.append(values[idx] - values[idx - 1])

            if deltas and all(delta < min_delta for delta in deltas):
                print(
                    f"\n⚠️  No significant improvement (delta < {min_delta}) for "
                    f"{config.safeguards.no_improvement_stop_cycles} cycles"
                )
                return True

        elif values and all(v == values[0] for v in values):
            print(f"\n⚠️  No improvement for {config.safeguards.no_improvement_stop_cycles} cycles")
            return True

    return False
