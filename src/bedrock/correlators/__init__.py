"""
Correlators package for Bedrock model management.
Contains modules for correlating and merging data from different sources.
"""

from .model_cris_correlator import ModelCRISCorrelator, ModelCRISCorrelationError

__all__ = [
    "ModelCRISCorrelator",
    "ModelCRISCorrelationError",
]
