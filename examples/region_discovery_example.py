#!/usr/bin/env python3
"""
Region Discovery Example

This example demonstrates how to use the BedrockRegionDiscovery class
to dynamically discover AWS Bedrock-enabled regions and use them with LLMManager.

Features demonstrated:
- Dynamic region discovery with caching
- Cache management and monitoring
- Using discovered regions with LLMManager
- Filtering regions by geography
- Error handling and fallback strategies
"""

from pathlib import Path

from bestehorn_llmmanager import (
    AWSRegions,
    BedrockRegionDiscovery,
    get_all_regions,
)
from bestehorn_llmmanager.bedrock.discovery.region_discovery import RegionDiscoveryError


def example_basic_discovery() -> None:
    """Basic region discovery example."""
    print("=" * 80)
    print("Example 1: Basic Region Discovery")
    print("=" * 80)

    # Create discovery instance with default settings
    discovery = BedrockRegionDiscovery()

    # Get Bedrock-enabled regions (uses cache if available)
    regions = discovery.get_bedrock_regions()

    print(f"\nFound {len(regions)} Bedrock-enabled regions:")
    for region in regions:
        print(f"  - {region}")

    print("\n")


def example_cache_management() -> None:
    """Cache management example."""
    print("=" * 80)
    print("Example 2: Cache Management")
    print("=" * 80)

    discovery = BedrockRegionDiscovery()

    # Get cache information
    cache_info = discovery.get_cache_info()

    print("\nCache Information:")
    print(f"  Cache file: {cache_info['cache_file']}")
    print(f"  Cache exists: {cache_info['cache_exists']}")
    print(f"  Cache TTL: {cache_info['cache_ttl_hours']} hours")

    if cache_info["cache_exists"]:
        print(f"  Cache age: {cache_info.get('cache_age_hours', 0):.1f} hours")
        print(f"  Cache valid: {cache_info.get('cache_valid', False)}")
        print(f"  Cached regions: {cache_info.get('cached_region_count', 0)}")

    # Force refresh to get fresh data
    print("\nForcing cache refresh...")
    fresh_regions = discovery.get_bedrock_regions(force_refresh=True)
    print(f"Fetched {len(fresh_regions)} regions from AWS")

    print("\n")


def example_custom_cache_config() -> None:
    """Custom cache configuration example."""
    print("=" * 80)
    print("Example 3: Custom Cache Configuration")
    print("=" * 80)

    # Create custom cache directory
    custom_cache_dir = Path.home() / ".aws" / "bedrock_cache"

    # Create discovery with custom settings
    discovery = BedrockRegionDiscovery(
        cache_dir=custom_cache_dir, cache_ttl_hours=48  # Cache for 48 hours
    )

    print(f"\nUsing custom cache directory: {custom_cache_dir}")
    print("Cache TTL: 48 hours")

    regions = discovery.get_bedrock_regions()
    print(f"Discovered {len(regions)} regions")

    print("\n")


def example_use_with_llm_manager() -> None:
    """Using discovered regions with LLMManager."""
    print("=" * 80)
    print("Example 4: Using Discovered Regions with LLMManager")
    print("=" * 80)

    # Discover regions
    discovery = BedrockRegionDiscovery()
    bedrock_regions = discovery.get_bedrock_regions()

    print(f"\nDiscovered {len(bedrock_regions)} Bedrock regions")
    print(f"First 5 regions: {bedrock_regions[:5]}")

    # Example of how to use with LLMManager (not executed in demo)
    print("\nExample usage with LLMManager:")
    print("  manager = LLMManager(")
    print("      models=['Claude 3 Haiku'],")
    print(f"      regions={bedrock_regions[:3]}")
    print("  )")
    print(f"\nThis would initialize LLMManager with regions: {bedrock_regions[:3]}")

    print("\n")


def example_geographic_filtering() -> None:
    """Filtering regions by geography."""
    print("=" * 80)
    print("Example 5: Geographic Region Filtering")
    print("=" * 80)

    # Get all Bedrock regions
    discovery = BedrockRegionDiscovery()
    all_regions = discovery.get_bedrock_regions()

    # Filter by geographic area
    us_regions = [r for r in all_regions if r.startswith("us-")]
    eu_regions = [r for r in all_regions if r.startswith("eu-")]
    ap_regions = [r for r in all_regions if r.startswith("ap-")]

    print(f"\nTotal Bedrock regions: {len(all_regions)}")
    print(f"\nUS regions ({len(us_regions)}):")
    for region in us_regions:
        print(f"  - {region}")

    print(f"\nEU regions ({len(eu_regions)}):")
    for region in eu_regions:
        print(f"  - {region}")

    print(f"\nAsia Pacific regions ({len(ap_regions)}):")
    for region in ap_regions:
        print(f"  - {region}")

    print("\n")


def example_static_regions() -> None:
    """Using static region utilities."""
    print("=" * 80)
    print("Example 6: Static Region Utilities")
    print("=" * 80)

    # Get static list of all AWS regions
    all_aws_regions = get_all_regions()

    print(f"\nStatic list of all AWS regions ({len(all_aws_regions)}):")
    for region in all_aws_regions[:5]:  # Show first 5
        print(f"  - {region}")
    print("  ...")

    # Use region constants
    print("\nUsing region constants:")
    print(f"  US East 1: {AWSRegions.US_EAST_1}")
    print(f"  US West 2: {AWSRegions.US_WEST_2}")
    print(f"  EU West 1: {AWSRegions.EU_WEST_1}")
    print(f"  AP Northeast 1: {AWSRegions.AP_NORTHEAST_1}")

    print("\n")


def example_error_handling() -> None:
    """Error handling and fallback strategies."""
    print("=" * 80)
    print("Example 7: Error Handling and Fallback")
    print("=" * 80)

    try:
        discovery = BedrockRegionDiscovery()
        regions = discovery.get_bedrock_regions()
        print(f"\nSuccessfully discovered {len(regions)} regions")

    except RegionDiscoveryError as e:
        print(f"\nFailed to discover regions: {e}")
        print("Falling back to static region list...")

        # Fallback to static list
        regions = get_all_regions()
        print(f"Using static region list: {len(regions)} regions")

    print("\n")


def example_monitoring_cache_state() -> None:
    """Monitoring cache state before fetching."""
    print("=" * 80)
    print("Example 8: Monitoring Cache State")
    print("=" * 80)

    discovery = BedrockRegionDiscovery()

    # Check cache before fetching
    cache_info = discovery.get_cache_info()

    if cache_info["cache_exists"] and cache_info.get("cache_valid", False):
        cache_age = cache_info.get("cache_age_hours", 0)
        print(f"\nUsing cached data (age: {cache_age:.1f} hours)")
        regions = discovery.get_bedrock_regions()
    else:
        print("\nCache is stale or doesn't exist. Fetching fresh data from AWS...")
        regions = discovery.get_bedrock_regions(force_refresh=True)

    print(f"Retrieved {len(regions)} regions")

    print("\n")


def main() -> None:
    """Run all examples."""
    print("\n")
    print("*" * 80)
    print("Bedrock Region Discovery Examples")
    print("*" * 80)
    print("\n")

    # Run examples
    example_basic_discovery()
    example_cache_management()
    example_custom_cache_config()
    example_use_with_llm_manager()
    example_geographic_filtering()
    example_static_regions()
    example_error_handling()
    example_monitoring_cache_state()

    print("*" * 80)
    print("All examples completed!")
    print("*" * 80)
    print("\n")


if __name__ == "__main__":
    main()
