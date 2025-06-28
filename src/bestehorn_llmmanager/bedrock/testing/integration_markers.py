"""
Pytest markers for AWS Bedrock integration tests.

This module defines custom pytest markers used to categorize and control
execution of integration tests that require real AWS Bedrock API access.
"""

from typing import Final, List


class IntegrationTestMarkers:
    """
    Pytest markers for integration test categorization.

    These markers allow selective execution of integration tests based on
    cost, execution time, and AWS service requirements.
    """

    # Basic integration test marker
    AWS_INTEGRATION: Final[str] = "aws_integration"

    # Cost-based markers
    AWS_LOW_COST: Final[str] = "aws_low_cost"
    AWS_MEDIUM_COST: Final[str] = "aws_medium_cost"
    AWS_HIGH_COST: Final[str] = "aws_high_cost"

    # Speed-based markers
    AWS_FAST: Final[str] = "aws_fast"
    AWS_SLOW: Final[str] = "aws_slow"

    # Service-specific markers
    AWS_BEDROCK_RUNTIME: Final[str] = "aws_bedrock_runtime"
    AWS_BEDROCK_AGENT: Final[str] = "aws_bedrock_agent"
    AWS_BEDROCK_KNOWLEDGE_BASE: Final[str] = "aws_bedrock_knowledge_base"

    # Authentication markers
    AWS_PROFILE_AUTH: Final[str] = "aws_profile_auth"
    AWS_ROLE_AUTH: Final[str] = "aws_role_auth"
    AWS_CREDENTIALS_AUTH: Final[str] = "aws_credentials_auth"

    # Region-specific markers
    AWS_SINGLE_REGION: Final[str] = "aws_single_region"
    AWS_MULTI_REGION: Final[str] = "aws_multi_region"
    AWS_CROSS_REGION: Final[str] = "aws_cross_region"

    # Model-specific markers
    AWS_ANTHROPIC_MODELS: Final[str] = "aws_anthropic_models"
    AWS_AMAZON_MODELS: Final[str] = "aws_amazon_models"
    AWS_META_MODELS: Final[str] = "aws_meta_models"
    AWS_COHERE_MODELS: Final[str] = "aws_cohere_models"

    # Feature-specific markers
    AWS_STREAMING: Final[str] = "aws_streaming"
    AWS_RETRY_LOGIC: Final[str] = "aws_retry_logic"
    AWS_PARALLEL_EXECUTION: Final[str] = "aws_parallel_execution"
    AWS_CRIS_MODELS: Final[str] = "aws_cris_models"


class MarkerDescriptions:
    """
    Human-readable descriptions for integration test markers.

    These descriptions are used in pytest configuration and documentation
    to explain the purpose and usage of each marker.
    """

    DESCRIPTIONS = {
        IntegrationTestMarkers.AWS_INTEGRATION: "Tests requiring real AWS Bedrock API access",
        IntegrationTestMarkers.AWS_LOW_COST: "Low-cost tests (< $0.01 estimated)",
        IntegrationTestMarkers.AWS_MEDIUM_COST: "Medium-cost tests ($0.01 - $0.10 estimated)",
        IntegrationTestMarkers.AWS_HIGH_COST: "High-cost tests (> $0.10 estimated)",
        IntegrationTestMarkers.AWS_FAST: "Fast integration tests (< 30 seconds)",
        IntegrationTestMarkers.AWS_SLOW: "Slow integration tests (> 30 seconds)",
        IntegrationTestMarkers.AWS_BEDROCK_RUNTIME: "Tests using Bedrock Runtime API",
        IntegrationTestMarkers.AWS_BEDROCK_AGENT: "Tests using Bedrock Agent API",
        IntegrationTestMarkers.AWS_BEDROCK_KNOWLEDGE_BASE: "Tests using Bedrock Knowledge Base API",
        IntegrationTestMarkers.AWS_PROFILE_AUTH: "Tests requiring AWS CLI profile authentication",
        IntegrationTestMarkers.AWS_ROLE_AUTH: "Tests requiring IAM role authentication",
        IntegrationTestMarkers.AWS_CREDENTIALS_AUTH: "Tests requiring direct AWS credentials",
        IntegrationTestMarkers.AWS_SINGLE_REGION: "Tests operating in a single AWS region",
        IntegrationTestMarkers.AWS_MULTI_REGION: "Tests operating across multiple AWS regions",
        IntegrationTestMarkers.AWS_CROSS_REGION: "Tests using cross-region inference",
        IntegrationTestMarkers.AWS_ANTHROPIC_MODELS: "Tests using Anthropic models",
        IntegrationTestMarkers.AWS_AMAZON_MODELS: "Tests using Amazon models",
        IntegrationTestMarkers.AWS_META_MODELS: "Tests using Meta models",
        IntegrationTestMarkers.AWS_COHERE_MODELS: "Tests using Cohere models",
        IntegrationTestMarkers.AWS_STREAMING: "Tests using streaming responses",
        IntegrationTestMarkers.AWS_RETRY_LOGIC: "Tests validating retry mechanisms",
        IntegrationTestMarkers.AWS_PARALLEL_EXECUTION: "Tests using parallel request execution",
        IntegrationTestMarkers.AWS_CRIS_MODELS: "Tests using Cross-Region Inference Service models",
    }


def get_marker_description(marker_name: str) -> str:
    """
    Get human-readable description for a marker.

    Args:
        marker_name: Name of the pytest marker

    Returns:
        Description string for the marker
    """
    return MarkerDescriptions.DESCRIPTIONS.get(marker_name, f"Custom marker: {marker_name}")


def get_all_integration_markers() -> List[str]:
    """
    Get all integration test marker names.

    Returns:
        List of all available integration test markers
    """
    return [
        IntegrationTestMarkers.AWS_INTEGRATION,
        IntegrationTestMarkers.AWS_LOW_COST,
        IntegrationTestMarkers.AWS_MEDIUM_COST,
        IntegrationTestMarkers.AWS_HIGH_COST,
        IntegrationTestMarkers.AWS_FAST,
        IntegrationTestMarkers.AWS_SLOW,
        IntegrationTestMarkers.AWS_BEDROCK_RUNTIME,
        IntegrationTestMarkers.AWS_BEDROCK_AGENT,
        IntegrationTestMarkers.AWS_BEDROCK_KNOWLEDGE_BASE,
        IntegrationTestMarkers.AWS_PROFILE_AUTH,
        IntegrationTestMarkers.AWS_ROLE_AUTH,
        IntegrationTestMarkers.AWS_CREDENTIALS_AUTH,
        IntegrationTestMarkers.AWS_SINGLE_REGION,
        IntegrationTestMarkers.AWS_MULTI_REGION,
        IntegrationTestMarkers.AWS_CROSS_REGION,
        IntegrationTestMarkers.AWS_ANTHROPIC_MODELS,
        IntegrationTestMarkers.AWS_AMAZON_MODELS,
        IntegrationTestMarkers.AWS_META_MODELS,
        IntegrationTestMarkers.AWS_COHERE_MODELS,
        IntegrationTestMarkers.AWS_STREAMING,
        IntegrationTestMarkers.AWS_RETRY_LOGIC,
        IntegrationTestMarkers.AWS_PARALLEL_EXECUTION,
        IntegrationTestMarkers.AWS_CRIS_MODELS,
    ]


def get_cost_markers() -> List[str]:
    """
    Get cost-related markers.

    Returns:
        List of cost-related marker names
    """
    return [
        IntegrationTestMarkers.AWS_LOW_COST,
        IntegrationTestMarkers.AWS_MEDIUM_COST,
        IntegrationTestMarkers.AWS_HIGH_COST,
    ]


def get_speed_markers() -> List[str]:
    """
    Get speed-related markers.

    Returns:
        List of speed-related marker names
    """
    return [
        IntegrationTestMarkers.AWS_FAST,
        IntegrationTestMarkers.AWS_SLOW,
    ]


def get_service_markers() -> List[str]:
    """
    Get AWS service-related markers.

    Returns:
        List of AWS service-related marker names
    """
    return [
        IntegrationTestMarkers.AWS_BEDROCK_RUNTIME,
        IntegrationTestMarkers.AWS_BEDROCK_AGENT,
        IntegrationTestMarkers.AWS_BEDROCK_KNOWLEDGE_BASE,
    ]


def get_auth_markers() -> List[str]:
    """
    Get authentication-related markers.

    Returns:
        List of authentication-related marker names
    """
    return [
        IntegrationTestMarkers.AWS_PROFILE_AUTH,
        IntegrationTestMarkers.AWS_ROLE_AUTH,
        IntegrationTestMarkers.AWS_CREDENTIALS_AUTH,
    ]


def get_model_markers() -> List[str]:
    """
    Get model provider-related markers.

    Returns:
        List of model provider-related marker names
    """
    return [
        IntegrationTestMarkers.AWS_ANTHROPIC_MODELS,
        IntegrationTestMarkers.AWS_AMAZON_MODELS,
        IntegrationTestMarkers.AWS_META_MODELS,
        IntegrationTestMarkers.AWS_COHERE_MODELS,
    ]
