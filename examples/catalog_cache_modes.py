"""
Cache modes demonstration for BedrockModelCatalog.

This example demonstrates the three cache modes (FILE, MEMORY, NONE)
and their use cases, performance characteristics, and trade-offs.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any

from bestehorn_llmmanager.bedrock.catalog import (
    BedrockModelCatalog,
    CacheMode,
    CatalogSource
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def measure_initialization_time(
    cache_mode: CacheMode,
    **kwargs
) -> Dict[str, Any]:
    """
    Measure catalog initialization time for a given cache mode.
    
    Args:
        cache_mode: Cache mode to test
        **kwargs: Additional arguments for BedrockModelCatalog
        
    Returns:
        Dictionary with timing and metadata
    """
    start_time = time.time()
    
    catalog = BedrockModelCatalog(cache_mode=cache_mode, **kwargs)
    metadata = catalog.get_catalog_metadata()
    
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    
    return {
        "cache_mode": cache_mode.value,
        "duration_ms": duration_ms,
        "source": metadata.source.value,
        "timestamp": metadata.retrieval_timestamp
    }


def example_1_file_cache_mode():
    """
    Example 1: FILE cache mode.
    
    Best for: Production environments, Lambda with /tmp access
    Pros: Fast warm starts, persistent across process restarts
    Cons: Requires file system access
    """
    print("\n" + "=" * 60)
    print("Example 1: FILE Cache Mode")
    print("=" * 60)
    
    print("\nUse case: Production environments with file system access")
    print("Benefits: Fast warm starts, persistent cache")
    
    # First initialization (cold start)
    print("\n1a. Cold start (no cache):")
    result1 = measure_initialization_time(
        cache_mode=CacheMode.FILE,
        cache_directory=Path("./demo_cache"),
        force_refresh=True  # Force API call
    )
    print(f"  Duration: {result1['duration_ms']:.1f}ms")
    print(f"  Source: {result1['source']}")
    
    # Second initialization (warm start)
    print("\n1b. Warm start (with cache):")
    result2 = measure_initialization_time(
        cache_mode=CacheMode.FILE,
        cache_directory=Path("./demo_cache")
    )
    print(f"  Duration: {result2['duration_ms']:.1f}ms")
    print(f"  Source: {result2['source']}")
    print(f"  Speedup: {result1['duration_ms'] / result2['duration_ms']:.1f}x faster")
    
    # Show cache file location
    catalog = BedrockModelCatalog(
        cache_mode=CacheMode.FILE,
        cache_directory=Path("./demo_cache")
    )
    metadata = catalog.get_catalog_metadata()
    if metadata.cache_file_path:
        print(f"\n  Cache file: {metadata.cache_file_path}")
        print(f"  Cache exists: {metadata.cache_file_path.exists()}")


def example_2_memory_cache_mode():
    """
    Example 2: MEMORY cache mode.
    
    Best for: Read-only environments, Lambda without /tmp
    Pros: No file I/O, works in read-only environments
    Cons: Cache lost on process restart
    """
    print("\n" + "=" * 60)
    print("Example 2: MEMORY Cache Mode")
    print("=" * 60)
    
    print("\nUse case: Read-only environments, restricted file systems")
    print("Benefits: No file I/O, works anywhere")
    print("Trade-off: Cache lost on process restart")
    
    # First initialization
    print("\n2a. First initialization:")
    result1 = measure_initialization_time(cache_mode=CacheMode.MEMORY)
    print(f"  Duration: {result1['duration_ms']:.1f}ms")
    print(f"  Source: {result1['source']}")
    
    # Simulate warm start (same process)
    print("\n2b. Same process (memory cache active):")
    result2 = measure_initialization_time(cache_mode=CacheMode.MEMORY)
    print(f"  Duration: {result2['duration_ms']:.1f}ms")
    print(f"  Source: {result2['source']}")
    
    if result2['source'] == CatalogSource.CACHE.value:
        print(f"  ✓ Using in-memory cache")
    
    print("\n  Note: Cache is stored in memory only")
    print("  On process restart, cache is lost and data is re-fetched")


def example_3_none_cache_mode():
    """
    Example 3: NONE cache mode.
    
    Best for: Security-critical environments, always-fresh data
    Pros: Always fresh data, no stale cache issues
    Cons: Higher latency, more API calls
    """
    print("\n" + "=" * 60)
    print("Example 3: NONE Cache Mode")
    print("=" * 60)
    
    print("\nUse case: Security-critical, always need latest data")
    print("Benefits: Always fresh, no stale cache")
    print("Trade-off: Higher latency, more API calls")
    
    # First call
    print("\n3a. First call:")
    result1 = measure_initialization_time(cache_mode=CacheMode.NONE)
    print(f"  Duration: {result1['duration_ms']:.1f}ms")
    print(f"  Source: {result1['source']}")
    
    # Second call (still fetches fresh)
    print("\n3b. Second call (still fetches fresh):")
    result2 = measure_initialization_time(cache_mode=CacheMode.NONE)
    print(f"  Duration: {result2['duration_ms']:.1f}ms")
    print(f"  Source: {result2['source']}")
    
    print("\n  Note: Each initialization fetches fresh data")
    print("  Falls back to bundled data if API fails")


def example_4_lambda_scenarios():
    """Example 4: Lambda deployment scenarios."""
    print("\n" + "=" * 60)
    print("Example 4: Lambda Deployment Scenarios")
    print("=" * 60)
    
    print("\n4a. Lambda with /tmp access (recommended):")
    print("  cache_mode=CacheMode.FILE")
    print("  cache_directory=Path('/tmp/bedrock_cache')")
    print("  Benefits:")
    print("    - Fast warm starts")
    print("    - Cache persists across invocations")
    print("    - Optimal performance")
    
    print("\n4b. Lambda read-only environment:")
    print("  cache_mode=CacheMode.MEMORY")
    print("  Benefits:")
    print("    - No file system access needed")
    print("    - Works in restricted environments")
    print("    - Cache active during warm starts")
    
    print("\n4c. Lambda with strict security requirements:")
    print("  cache_mode=CacheMode.NONE")
    print("  fallback_to_bundled=True")
    print("  Benefits:")
    print("    - Always fresh data")
    print("    - Bundled fallback for reliability")
    print("    - No cache management needed")


def example_5_performance_comparison():
    """Example 5: Performance comparison across cache modes."""
    print("\n" + "=" * 60)
    print("Example 5: Performance Comparison")
    print("=" * 60)
    
    print("\nComparing initialization times across cache modes...")
    print("(Times may vary based on network and AWS API latency)")
    
    results = []
    
    # Test FILE mode
    print("\nTesting FILE mode...")
    file_result = measure_initialization_time(
        cache_mode=CacheMode.FILE,
        cache_directory=Path("./perf_test_cache")
    )
    results.append(file_result)
    
    # Test MEMORY mode
    print("Testing MEMORY mode...")
    memory_result = measure_initialization_time(cache_mode=CacheMode.MEMORY)
    results.append(memory_result)
    
    # Test NONE mode
    print("Testing NONE mode...")
    none_result = measure_initialization_time(cache_mode=CacheMode.NONE)
    results.append(none_result)
    
    # Display results
    print("\n" + "-" * 60)
    print(f"{'Cache Mode':<15} {'Duration (ms)':<15} {'Source':<15}")
    print("-" * 60)
    for result in results:
        print(
            f"{result['cache_mode']:<15} "
            f"{result['duration_ms']:<15.1f} "
            f"{result['source']:<15}"
        )
    print("-" * 60)
    
    # Find fastest
    fastest = min(results, key=lambda x: x['duration_ms'])
    print(f"\nFastest: {fastest['cache_mode']} ({fastest['duration_ms']:.1f}ms)")


def example_6_cache_configuration():
    """Example 6: Advanced cache configuration."""
    print("\n" + "=" * 60)
    print("Example 6: Advanced Cache Configuration")
    print("=" * 60)
    
    print("\n6a. Custom cache directory:")
    catalog1 = BedrockModelCatalog(
        cache_mode=CacheMode.FILE,
        cache_directory=Path("./my_app_cache")
    )
    print(f"  Cache directory: ./my_app_cache")
    
    print("\n6b. Custom cache age:")
    catalog2 = BedrockModelCatalog(
        cache_mode=CacheMode.FILE,
        cache_max_age_hours=6.0  # Refresh every 6 hours
    )
    print(f"  Max cache age: 6 hours")
    
    print("\n6c. Disable bundled fallback:")
    try:
        catalog3 = BedrockModelCatalog(
            cache_mode=CacheMode.NONE,
            fallback_to_bundled=False  # Fail if API unavailable
        )
        print(f"  Bundled fallback: disabled")
    except Exception as e:
        print(f"  Failed (expected if no API access): {type(e).__name__}")
    
    print("\n6d. Custom API timeout:")
    catalog4 = BedrockModelCatalog(
        cache_mode=CacheMode.FILE,
        timeout=10  # 10 second timeout
    )
    print(f"  API timeout: 10 seconds")


def example_7_cache_invalidation():
    """Example 7: Cache invalidation strategies."""
    print("\n" + "=" * 60)
    print("Example 7: Cache Invalidation")
    print("=" * 60)
    
    print("\n7a. Time-based invalidation:")
    print("  Set cache_max_age_hours to control freshness")
    catalog1 = BedrockModelCatalog(
        cache_mode=CacheMode.FILE,
        cache_max_age_hours=24.0  # Default: 24 hours
    )
    metadata1 = catalog1.get_catalog_metadata()
    print(f"  Cache age: {metadata1.retrieval_timestamp}")
    
    print("\n7b. Force refresh:")
    print("  Use force_refresh=True to bypass cache")
    catalog2 = BedrockModelCatalog(
        cache_mode=CacheMode.FILE,
        force_refresh=True  # Always fetch fresh
    )
    metadata2 = catalog2.get_catalog_metadata()
    print(f"  Source: {metadata2.source.value}")
    
    print("\n7c. Manual cache deletion:")
    print("  Delete cache file to force refresh")
    cache_dir = Path("./demo_cache")
    cache_file = cache_dir / "bedrock_catalog.json"
    if cache_file.exists():
        print(f"  Cache file exists: {cache_file}")
        print(f"  To invalidate: delete {cache_file}")


def main():
    """Run all cache mode examples."""
    print("=" * 60)
    print("BedrockModelCatalog Cache Modes Demonstration")
    print("=" * 60)
    print("\nThis example demonstrates the three cache modes:")
    print("  - FILE: Persistent file-based caching")
    print("  - MEMORY: In-memory caching (process lifetime)")
    print("  - NONE: No caching (always fresh)")
    
    try:
        example_1_file_cache_mode()
        example_2_memory_cache_mode()
        example_3_none_cache_mode()
        example_4_lambda_scenarios()
        example_5_performance_comparison()
        example_6_cache_configuration()
        example_7_cache_invalidation()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
        print("\nRecommendations:")
        print("  - Production: Use FILE mode with /tmp in Lambda")
        print("  - Read-only: Use MEMORY mode")
        print("  - Security-critical: Use NONE mode with bundled fallback")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("This is expected if AWS credentials are not configured.")


if __name__ == "__main__":
    main()
