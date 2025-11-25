"""
Fetchers module for retrieving data from AWS APIs.

This module provides fetchers for various AWS Bedrock data sources,
including CRIS (Cross-Region Inference) profile information.
"""

from .cris_api_fetcher import CRISAPIFetcher

__all__ = ["CRISAPIFetcher"]
