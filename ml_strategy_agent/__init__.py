"""
ml_strategy_agent/__init__.py
------------------------------
Package entry point — exposes the primary public interface.
"""

from ml_strategy_agent.agent   import MLStrategyAgent
from ml_strategy_agent.schemas import (
    DataAgentOutput,
    DatasetMetadata,
    TargetDistribution,
    PreprocessingSummary,
    MLStrategy,
)

__all__ = [
    "MLStrategyAgent",
    "DataAgentOutput",
    "DatasetMetadata",
    "TargetDistribution",
    "PreprocessingSummary",
    "MLStrategy",
]
