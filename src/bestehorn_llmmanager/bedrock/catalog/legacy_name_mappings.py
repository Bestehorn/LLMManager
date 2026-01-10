"""
Legacy model name mappings for backward compatibility.

This module provides mappings from UnifiedModelManager friendly names to
BedrockModelCatalog API-based names. These mappings ensure backward compatibility
for existing code and tests that use the old naming conventions.

The mappings are organized by provider and include all known legacy names from
UnifiedModelManager that are still available in BedrockModelCatalog.
"""

from typing import Dict, Optional

# Legacy name mappings from UnifiedModelManager to BedrockModelCatalog
# Format: {legacy_name: catalog_name}
LEGACY_NAME_MAPPINGS: Dict[str, str] = {
    # Anthropic Claude models
    "Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "Claude 3 Opus": "anthropic.claude-3-opus-20240229-v1:0",
    "Claude 3.5 Sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "Claude 3.5 Sonnet v2": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "Claude Instant": "anthropic.claude-instant-v1",
    "Claude 2": "anthropic.claude-v2",
    "Claude 2.1": "anthropic.claude-v2:1",
    # Amazon Titan models
    "Titan Text G1 - Lite": "amazon.titan-text-lite-v1",
    "Titan Text G1 - Express": "amazon.titan-text-express-v1",
    "Titan Text G1 - Premier": "amazon.titan-text-premier-v1:0",
    "Titan Embeddings G1 - Text": "amazon.titan-embed-text-v1",
    "Titan Embeddings G1 - Text v2": "amazon.titan-embed-text-v2:0",
    "Titan Image Generator G1": "amazon.titan-image-generator-v1",
    "Titan Image Generator G1 v2": "amazon.titan-image-generator-v2:0",
    "Titan Multimodal Embeddings G1": "amazon.titan-embed-image-v1",
    # Meta Llama models
    "Llama 2 13B Chat": "meta.llama2-13b-chat-v1",
    "Llama 2 70B Chat": "meta.llama2-70b-chat-v1",
    "Llama 3 8B Instruct": "meta.llama3-8b-instruct-v1:0",
    "Llama 3 70B Instruct": "meta.llama3-70b-instruct-v1:0",
    "Llama 3.1 8B Instruct": "meta.llama3-1-8b-instruct-v1:0",
    "Llama 3.1 70B Instruct": "meta.llama3-1-70b-instruct-v1:0",
    "Llama 3.1 405B Instruct": "meta.llama3-1-405b-instruct-v1:0",
    "Llama 3.2 1B Instruct": "meta.llama3-2-1b-instruct-v1:0",
    "Llama 3.2 3B Instruct": "meta.llama3-2-3b-instruct-v1:0",
    "Llama 3.2 11B Vision Instruct": "meta.llama3-2-11b-instruct-v1:0",
    "Llama 3.2 90B Vision Instruct": "meta.llama3-2-90b-instruct-v1:0",
    # Cohere models
    "Cohere Command": "cohere.command-text-v14",
    "Cohere Command Light": "cohere.command-light-text-v14",
    "Cohere Command R": "cohere.command-r-v1:0",
    "Cohere Command R+": "cohere.command-r-plus-v1:0",
    "Cohere Embed English": "cohere.embed-english-v3",
    "Cohere Embed Multilingual": "cohere.embed-multilingual-v3",
    # AI21 Labs models
    "AI21 Jamba Instruct": "ai21.jamba-instruct-v1:0",
    "AI21 Jamba 1.5 Mini": "ai21.jamba-1-5-mini-v1:0",
    "AI21 Jamba 1.5 Large": "ai21.jamba-1-5-large-v1:0",
    "AI21 Jurassic-2 Mid": "ai21.j2-mid-v1",
    "AI21 Jurassic-2 Ultra": "ai21.j2-ultra-v1",
    # Mistral AI models
    "Mistral 7B Instruct": "mistral.mistral-7b-instruct-v0:2",
    "Mistral 8x7B Instruct": "mistral.mixtral-8x7b-instruct-v0:1",
    "Mistral Large": "mistral.mistral-large-2402-v1:0",
    "Mistral Large 2": "mistral.mistral-large-2407-v1:0",
    "Mistral Small": "mistral.mistral-small-2402-v1:0",
    # Stability AI models
    "Stable Diffusion XL": "stability.stable-diffusion-xl-v1",
    "Stable Image Core": "stability.stable-image-core-v1:0",
    "Stable Image Ultra": "stability.stable-image-ultra-v1:0",
    # APAC regional prefixed models (common in integration tests)
    "APAC Anthropic Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "APAC Anthropic Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "APAC Anthropic Claude 3 Opus": "anthropic.claude-3-opus-20240229-v1:0",
    "APAC Anthropic Claude 3.5 Sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "APAC Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "APAC Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "APAC Claude 3 Opus": "anthropic.claude-3-opus-20240229-v1:0",
    "APAC Claude 3.5 Sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    # EU regional prefixed models
    "EU Anthropic Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "EU Anthropic Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "EU Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "EU Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    # US regional prefixed models
    "US Anthropic Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "US Anthropic Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "US Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "US Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
}


# Deprecated models that are no longer available in BedrockModelCatalog
# These models existed in UnifiedModelManager but have been removed from AWS Bedrock
# Format: {legacy_name: deprecation_reason}
DEPRECATED_MODELS: Dict[str, str] = {
    "Claude v1": "Replaced by Claude 2 and Claude 3 models",
    "Claude v1.3": "Replaced by Claude 2 and Claude 3 models",
    "Titan Text G1": "Replaced by Titan Text G1 - Lite, Express, and Premier variants",
}


def get_legacy_mapping(legacy_name: str) -> Optional[str]:
    """
    Get the catalog name for a legacy model name.

    Args:
        legacy_name: Legacy model name from UnifiedModelManager

    Returns:
        Catalog model name if mapping exists, None otherwise
    """
    return LEGACY_NAME_MAPPINGS.get(legacy_name)


def is_deprecated_model(legacy_name: str) -> bool:
    """
    Check if a legacy model name refers to a deprecated model.

    Args:
        legacy_name: Legacy model name from UnifiedModelManager

    Returns:
        True if the model is deprecated
    """
    return legacy_name in DEPRECATED_MODELS


def get_deprecation_reason(legacy_name: str) -> Optional[str]:
    """
    Get the deprecation reason for a legacy model.

    Args:
        legacy_name: Legacy model name from UnifiedModelManager

    Returns:
        Deprecation reason if model is deprecated, None otherwise
    """
    return DEPRECATED_MODELS.get(legacy_name)


def get_all_legacy_names() -> list[str]:
    """
    Get all known legacy model names.

    Returns:
        List of all legacy model names
    """
    return list(LEGACY_NAME_MAPPINGS.keys())


def get_all_deprecated_names() -> list[str]:
    """
    Get all deprecated model names.

    Returns:
        List of all deprecated model names
    """
    return list(DEPRECATED_MODELS.keys())
