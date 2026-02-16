"""
CLI wrapper for Ralph ML Orchestrator.

This script is called by the Go CLI and invokes the Orchestrator.run() method.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import ralph_ml
sys.path.insert(0, str(Path(__file__).parent.parent))

from ralph_ml.config import RalphMLConfig
from ralph_ml.orchestrator import Orchestrator


def main():
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python orchestrator_cli.py <prompt> [--config <path>]", file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1]
    config_path = None

    # Parse config flag
    for i in range(2, len(sys.argv)):
        if sys.argv[i] == "--config" and i + 1 < len(sys.argv):
            config_path = sys.argv[i + 1]
            break

    # Load config
    if config_path:
        with open(config_path) as f:
            config_data = json.load(f)
        config = RalphMLConfig.model_validate(config_data)
    else:
        # Create default config
        config = RalphMLConfig(
            project={
                "name": "quickstart-ml-project",
                "framework": "pytorch",
                "target_metric": {"name": "test_accuracy", "value": 0.90},
            }
        )

    # Run orchestrator
    orchestrator = Orchestrator(config)
    orchestrator.run(prompt)


if __name__ == "__main__":
    main()
