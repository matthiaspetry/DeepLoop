"""Analysis phase utilities for Ralph ML Loop."""

import json
from pathlib import Path
from typing import Any

from ralph_ml.config import CycleAnalysis, MetricsResult, Recommendation, TargetMetric


def load_analysis_from_workspace(
    workspace: Path,
    metrics: MetricsResult,
    target_metric: TargetMetric,
) -> tuple[str | None, list[Recommendation] | None, dict[str, Any] | None]:
    """Load analysis outputs from workspace files.

    Args:
        workspace: Path to workspace directory
        metrics: Metrics from training
        target_metric: Target metric configuration

    Returns:
        Tuple of (summary, recommendations, decision_data) or None for missing files
    """
    analysis_md_path = workspace / "analysis.md"
    recommendations_path = workspace / "recommendations.json"
    decision_path = workspace / "decision.json"

    # Load summary
    summary = None
    if analysis_md_path.exists():
        analysis_md = analysis_md_path.read_text().strip()
        if analysis_md:
            summary = analysis_md

    # Load recommendations
    recommendations = None
    if recommendations_path.exists():
        try:
            with open(recommendations_path) as f:
                recommendations_data = json.load(f)

            if isinstance(recommendations_data, dict):
                raw_recommendations = recommendations_data.get("recommendations", [])
            elif isinstance(recommendations_data, list):
                raw_recommendations = recommendations_data
            else:
                raw_recommendations = []

            recommendations = []
            for item in raw_recommendations:
                if isinstance(item, dict):
                    recommendations.append(
                        Recommendation(
                            action=str(item.get("action", "Analyze and iterate")),
                            confidence=str(item.get("confidence", "medium")),
                            rationale=str(item.get("rationale", "No rationale provided")),
                        )
                    )
        except Exception:
            recommendations = None

    # Load decision
    decision_data = None
    if decision_path.exists():
        try:
            with open(decision_path) as f:
                decision_data = json.load(f)

            # Handle nested format {"decision": {...}}
            if (
                isinstance(decision_data, dict)
                and "decision" in decision_data
                and isinstance(decision_data["decision"], dict)
            ):
                decision_data = decision_data["decision"]
        except Exception:
            decision_data = None

    return summary, recommendations, decision_data


def build_fallback_analysis(
    metrics: MetricsResult,
    target_metric: TargetMetric,
) -> CycleAnalysis:
    """Build fallback analysis when files are missing.

    Args:
        metrics: Metrics from training
        target_metric: Target metric configuration

    Returns:
        CycleAnalysis with default values
    """
    result_dict = metrics.result.model_dump()
    target_value = result_dict.get(metrics.target.name, None)
    target_met = isinstance(target_value, (int, float)) and metrics.target.target_is_met(
        float(target_value)
    )
    target_display = f"{target_value:.4f}" if isinstance(target_value, (int, float)) else "N/A"

    summary = (
        f"Training achieved {metrics.target.name}={target_display}. "
        f"Target: {target_metric.comparator_symbol()} {target_metric.value:.4f}"
    )

    recommendations = [
        Recommendation(
            action="Analyze and iterate" if not target_met else "Finalize model",
            confidence="high",
            rationale="Target not yet met" if not target_met else "Target achieved",
        )
    ]

    decision_action = "stop" if target_met else "continue"
    decision_rationale = (
        "Target met for optimization direction"
        if target_met
        else "Continue improving toward optimization objective"
    )

    return CycleAnalysis(
        summary=summary,
        recommendations=recommendations,
        decision=CycleAnalysis.Decision(
            action=decision_action,
            rationale=decision_rationale,
        ),
    )


def merge_analysis_with_fallback(
    fallback: CycleAnalysis,
    summary: str | None,
    recommendations: list[Recommendation] | None,
    decision_data: dict[str, Any] | None,
) -> CycleAnalysis:
    """Merge loaded analysis data with fallback defaults.

    Args:
        fallback: Fallback analysis with defaults
        summary: Loaded summary or None
        recommendations: Loaded recommendations or None
        decision_data: Loaded decision data or None

    Returns:
        Merged CycleAnalysis
    """
    # Use loaded summary if available
    final_summary = summary if summary is not None else fallback.summary

    # Use loaded recommendations if available
    final_recommendations = (
        recommendations if recommendations is not None else fallback.recommendations
    )

    # Parse decision data
    decision_action = fallback.decision.action
    decision_rationale = fallback.decision.rationale

    if decision_data is not None and isinstance(decision_data, dict):
        parsed_action = str(decision_data.get("action", decision_action)).lower()
        if parsed_action in {"continue", "stop"}:
            decision_action = parsed_action
        decision_rationale = str(decision_data.get("rationale", decision_rationale))

    return CycleAnalysis(
        summary=final_summary,
        recommendations=final_recommendations,
        decision=CycleAnalysis.Decision(
            action=decision_action,
            rationale=decision_rationale,
        ),
    )
