"""
Basic usage examples for BedrockModelCatalog.

This example demonstrates the fundamental operations of the new
BedrockModelCatalog system, including initialization, querying,
and model availability checks.
"""

import logging
from pathlib import Path

from bestehorn_llmmanager.bedrock.catalog import (
    BedrockModelCatalog,
    CacheMode,
    CatalogSource
)


# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def example_1_basic_initialization():
    """Example 1: Basic catalog initialization with default settings."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Initialization")
    print("=" * 60)
    
    # Initialize with defaults (FILE cache mode, default directory)
    catalog = BedrockModelCatalog()
    
    # Get metadata about the catalog
    metadata = catalog.get_catalog_metadata()
    
    print(f"Catalog initialized successfully!")
    print(f"  Source: {metadata.source.value}")
    print(f"  Retrieval timestamp: {metadata.retrieval_timestamp}")
    print(f"  Regions queried: {len(metadata.api_regions_queried)}")
    
    if metadata.source == CatalogSource.BUNDLED:
        print(f"  Bundled data version: {metadata.bundled_data_version}")
    elif metadata.source == CatalogSource.CACHE:
        print(f"  Cache file: {metadata.cache_file_path}")


def example_2_check_model_availability():
    """Example 2: Check if specific models are available in regions."""
    print("\n" + "=" * 60)
    print("Example 2: Check Model Availability")
    print("=" * 60)
    
    catalog = BedrockModelCatalog()
    
    # Check various models in different regions
    test_cases = [
        ("Claude 3.5 Sonnet v2", "us-east-1"),
        ("Claude 3 Haiku", "us-west-2"),
        ("Nova Pro", "eu-west-1"),
        ("Llama 3.1 70B", "us-east-1"),
    ]
    
    for model_name, region in test_cases:
        is_available = catalog.is_model_available(
            model_name=model_name,
            region=region
        )
        status = "✓ Available" if is_available else "✗ Not available"
        print(f"{status}: {model_name} in {region}")


def example_3_get_model_info():
    """Example 3: Get detailed information about a model."""
    print("\n" + "=" * 60)
    print("Example 3: Get Model Information")
    print("=" * 60)
    
    catalog = BedrockModelCatalog()
    
    # Get info for Claude 3 Haiku in us-east-1
    model_name = "Claude 3 Haiku"
    region = "us-east-1"
    
    model_info = catalog.get_model_info(
        model_name=model_name,
        region=region
    )
    
    if model_info:
        print(f"Model: {model_name}")
        print(f"Region: {region}")
        print(f"  Model ID: {model_info.model_id}")
        print(f"  Inference Profile ID: {model_info.inference_profile_id}")
        print(f"  Access Method: {model_info.access_method.value if model_info.access_method else 'N/A'}")
        print(f"  Supports Streaming: {model_info.supports_streaming}")
    else:
        print(f"Model {model_name} not found in {region}")


def example_4_list_models():
    """Example 4: List available models with filtering."""
    print("\n" + "=" * 60)
    print("Example 4: List Models")
    print("=" * 60)
    
    catalog = BedrockModelCatalog()
    
    # List all models
    print("\n4a. All models:")
    all_models = catalog.list_models()
    print(f"  Total models: {len(all_models)}")
    
    # Show first 5 models
    for model in all_models[:5]:
        print(f"  - {model.model_name} ({model.provider})")
    print(f"  ... and {len(all_models) - 5} more")
    
    # List models in specific region
    print("\n4b. Models in us-east-1:")
    us_east_models = catalog.list_models(region="us-east-1")
    print(f"  Models available: {len(us_east_models)}")
    
    # List models by provider
    print("\n4c. Anthropic models:")
    anthropic_models = catalog.list_models(provider="Anthropic")
    print(f"  Anthropic models: {len(anthropic_models)}")
    for model in anthropic_models[:3]:
        print(f"  - {model.model_name}")
    
    # List streaming-capable models
    print("\n4d. Streaming-capable models:")
    streaming_models = catalog.list_models(streaming_only=True)
    print(f"  Streaming models: {len(streaming_models)}")
    
    # Combined filters
    print("\n4e. Anthropic streaming models in us-west-2:")
    filtered_models = catalog.list_models(
        region="us-west-2",
        provider="Anthropic",
        streaming_only=True
    )
    print(f"  Filtered models: {len(filtered_models)}")
    for model in filtered_models:
        print(f"  - {model.model_name}")


def example_5_catalog_metadata():
    """Example 5: Inspect catalog metadata."""
    print("\n" + "=" * 60)
    print("Example 5: Catalog Metadata")
    print("=" * 60)
    
    catalog = BedrockModelCatalog()
    metadata = catalog.get_catalog_metadata()
    
    print(f"Catalog Information:")
    print(f"  Source: {metadata.source.value}")
    print(f"  Retrieved: {metadata.retrieval_timestamp}")
    print(f"  Regions queried: {', '.join(metadata.api_regions_queried)}")
    
    if metadata.bundled_data_version:
        print(f"  Bundled data version: {metadata.bundled_data_version}")
    
    if metadata.cache_file_path:
        print(f"  Cache file: {metadata.cache_file_path}")
    
    # Determine data freshness
    from datetime import datetime, timezone
    
    age = datetime.now(timezone.utc) - metadata.retrieval_timestamp
    age_hours = age.total_seconds() / 3600
    
    print(f"  Data age: {age_hours:.1f} hours")
    
    if metadata.source == CatalogSource.API:
        print("  ✓ Using fresh API data")
    elif metadata.source == CatalogSource.CACHE:
        print("  ✓ Using cached data (fast)")
    elif metadata.source == CatalogSource.BUNDLED:
        print("  ⚠ Using bundled fallback data (may be stale)")


def example_6_force_refresh():
    """Example 6: Force refresh from API."""
    print("\n" + "=" * 60)
    print("Example 6: Force Refresh")
    print("=" * 60)
    
    # Initialize with force_refresh=True to bypass cache
    print("Forcing refresh from AWS APIs...")
    catalog = BedrockModelCatalog(force_refresh=True)
    
    metadata = catalog.get_catalog_metadata()
    print(f"Catalog refreshed!")
    print(f"  Source: {metadata.source.value}")
    print(f"  Retrieved: {metadata.retrieval_timestamp}")
    
    if metadata.source == CatalogSource.API:
        print("  ✓ Successfully fetched fresh data from AWS")
    else:
        print(f"  ⚠ Fell back to {metadata.source.value}")


def example_7_custom_configuration():
    """Example 7: Custom catalog configuration."""
    print("\n" + "=" * 60)
    print("Example 7: Custom Configuration")
    print("=" * 60)
    
    # Initialize with custom settings
    catalog = BedrockModelCatalog(
        cache_mode=CacheMode.FILE,
        cache_directory=Path("./my_custom_cache"),
        cache_max_age_hours=12.0,  # Refresh after 12 hours
        timeout=20,  # API timeout in seconds
        max_workers=8,  # Parallel workers for API calls
        fallback_to_bundled=True
    )
    
    metadata = catalog.get_catalog_metadata()
    print(f"Custom catalog initialized:")
    print(f"  Cache directory: ./my_custom_cache")
    print(f"  Max cache age: 12 hours")
    print(f"  API timeout: 20 seconds")
    print(f"  Parallel workers: 8")
    print(f"  Source: {metadata.source.value}")


def example_8_error_handling():
    """Example 8: Error handling and fallback behavior."""
    print("\n" + "=" * 60)
    print("Example 8: Error Handling")
    print("=" * 60)
    
    try:
        # Initialize catalog (will try API, cache, then bundled)
        catalog = BedrockModelCatalog(
            fallback_to_bundled=True,
            timeout=5  # Short timeout for demo
        )
        
        metadata = catalog.get_catalog_metadata()
        print(f"Catalog initialized successfully")
        print(f"  Source: {metadata.source.value}")
        
        # Try to get info for a model that might not exist
        model_info = catalog.get_model_info(
            model_name="NonExistentModel",
            region="us-east-1"
        )
        
        if model_info:
            print(f"  Found model: {model_info.model_id}")
        else:
            print(f"  Model not found (expected)")
            
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        print("This is expected if AWS credentials are not configured")


def main():
    """Run all examples."""
    print("=" * 60)
    print("BedrockModelCatalog Basic Usage Examples")
    print("=" * 60)
    print("\nNote: These examples require AWS credentials to fetch fresh data.")
    print("Without credentials, the catalog will use bundled fallback data.")
    
    try:
        example_1_basic_initialization()
        example_2_check_model_availability()
        example_3_get_model_info()
        example_4_list_models()
        example_5_catalog_metadata()
        example_6_force_refresh()
        example_7_custom_configuration()
        example_8_error_handling()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("This is expected if AWS credentials are not configured.")


if __name__ == "__main__":
    main()
