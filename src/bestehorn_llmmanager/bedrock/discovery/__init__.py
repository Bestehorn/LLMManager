"""
Discovery module for AWS Bedrock regions and services.

This module provides dynamic discovery capabilities for AWS Bedrock services,
including region discovery and service availability checking.
"""

from .region_discovery import BedrockRegionDiscovery

__all__ = ["BedrockRegionDiscovery"]
