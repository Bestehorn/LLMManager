"""
Lambda-specific usage patterns for BedrockModelCatalog.

This example demonstrates best practices for using BedrockModelCatalog
in AWS Lambda, including cold start optimization, warm start reuse,
and error handling strategies.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from bestehorn_llmmanager import LLMManager
from bestehorn_llmmanager.bedrock.catalog import (
    BedrockModelCatalog,
    CacheMode,
    CatalogSource
)


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ============================================================================
# Pattern 1: Global Initialization (Recommended for Lambda)
# ============================================================================
# Initialize catalog and manager at module level for warm start reuse
# This is the recommended pattern for Lambda functions

CATALOG = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("/tmp/bedrock_cache"),
    cache_max_age_hours=24.0,
    fallback_to_bundled=True,
    timeout=10  # Shorter timeout for Lambda
)

MANAGER = LLMManager(
    models=["Claude 3.5 Sonnet v2", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"],
    log_level=logging.INFO
)


def lambda_handler_pattern_1(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Pattern 1: Global initialization (recommended).
    
    Benefits:
    - Fast warm starts (catalog already loaded)
    - Efficient resource usage
    - Simple code
    
    Use when:
    - Standard Lambda deployment
    - /tmp directory available
    - Want optimal performance
    """
    try:
        prompt = event.get("prompt", "Hello!")
        
        # Catalog and manager are already initialized
        # On warm starts, this is instant
        logger.info("Using pre-initialized catalog and manager")
        
        # Get catalog metadata
        metadata = CATALOG.get_catalog_metadata()
        logger.info(f"Catalog source: {metadata.source.value}")
        
        # Make request
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        response = MANAGER.converse(messages=messages)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "pattern": "global_initialization",
                "success": response.success,
                "content": response.get_content(),
                "model_used": response.model_used,
                "catalog_source": metadata.source.value
            })
        }
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


# ============================================================================
# Pattern 2: Lazy Initialization
# ============================================================================
# Initialize on first use, cache for subsequent calls

_lazy_catalog = None
_lazy_manager = None


def get_catalog_lazy():
    """Get or create catalog (lazy initialization)."""
    global _lazy_catalog
    if _lazy_catalog is None:
        logger.info("Lazy initializing catalog")
        _lazy_catalog = BedrockModelCatalog(
            cache_mode=CacheMode.FILE,
            cache_directory=Path("/tmp/bedrock_cache"),
            fallback_to_bundled=True
        )
    return _lazy_catalog


def get_manager_lazy():
    """Get or create manager (lazy initialization)."""
    global _lazy_manager
    if _lazy_manager is None:
        logger.info("Lazy initializing manager")
        _lazy_manager = LLMManager(
            models=["Claude 3 Haiku"],
            regions=["us-east-1"],
            log_level=logging.INFO
        )
    return _lazy_manager


def lambda_handler_pattern_2(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Pattern 2: Lazy initialization.
    
    Benefits:
    - Only initialize when needed
    - Reduces cold start time if not used
    - Still benefits from warm starts
    
    Use when:
    - Lambda has multiple code paths
    - Not all paths need the catalog
    - Want to optimize cold start for non-LLM paths
    """
    try:
        operation = event.get("operation", "converse")
        
        if operation == "converse":
            # Only initialize when needed
            catalog = get_catalog_lazy()
            manager = get_manager_lazy()
            
            prompt = event.get("prompt", "Hello!")
            messages = [{"role": "user", "content": [{"text": prompt}]}]
            response = manager.converse(messages=messages)
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "pattern": "lazy_initialization",
                    "success": response.success,
                    "content": response.get_content()
                })
            }
        else:
            # Other operations don't need catalog
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "pattern": "lazy_initialization",
                    "message": "Operation completed without catalog"
                })
            }
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


# ============================================================================
# Pattern 3: Memory-Only Cache (Read-Only Environments)
# ============================================================================

MEMORY_CATALOG = BedrockModelCatalog(
    cache_mode=CacheMode.MEMORY,
    fallback_to_bundled=True
)

MEMORY_MANAGER = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"],
    log_level=logging.INFO
)


def lambda_handler_pattern_3(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Pattern 3: Memory-only cache.
    
    Benefits:
    - Works in read-only environments
    - No file system access needed
    - Still benefits from warm starts
    
    Use when:
    - /tmp is not available or restricted
    - Read-only file system
    - Security policies prevent file writes
    """
    try:
        prompt = event.get("prompt", "Hello!")
        
        metadata = MEMORY_CATALOG.get_catalog_metadata()
        logger.info(f"Using memory cache, source: {metadata.source.value}")
        
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        response = MEMORY_MANAGER.converse(messages=messages)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "pattern": "memory_cache",
                "success": response.success,
                "content": response.get_content(),
                "catalog_source": metadata.source.value
            })
        }
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


# ============================================================================
# Pattern 4: No Cache (Always Fresh)
# ============================================================================

def lambda_handler_pattern_4(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Pattern 4: No cache (always fresh).
    
    Benefits:
    - Always uses latest model data
    - No stale cache issues
    - Bundled fallback for reliability
    
    Use when:
    - Security requires always-fresh data
    - Model availability changes frequently
    - Can tolerate higher latency
    
    Trade-offs:
    - Higher cold start time
    - More API calls
    - Higher latency
    """
    try:
        # Initialize fresh each time (or use global with NONE mode)
        catalog = BedrockModelCatalog(
            cache_mode=CacheMode.NONE,
            fallback_to_bundled=True,
            timeout=10
        )
        
        manager = LLMManager(
            models=["Claude 3 Haiku"],
            regions=["us-east-1"],
            log_level=logging.INFO
        )
        
        prompt = event.get("prompt", "Hello!")
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        response = manager.converse(messages=messages)
        
        metadata = catalog.get_catalog_metadata()
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "pattern": "no_cache",
                "success": response.success,
                "content": response.get_content(),
                "catalog_source": metadata.source.value,
                "always_fresh": True
            })
        }
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


# ============================================================================
# Pattern 5: Error Handling and Fallback
# ============================================================================

def lambda_handler_pattern_5(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Pattern 5: Comprehensive error handling.
    
    Benefits:
    - Graceful degradation
    - Detailed error reporting
    - Fallback strategies
    
    Use when:
    - Production environment
    - Need high reliability
    - Want detailed diagnostics
    """
    try:
        # Try to initialize catalog with multiple fallback strategies
        catalog = None
        catalog_source = None
        
        try:
            # Try FILE cache first
            catalog = BedrockModelCatalog(
                cache_mode=CacheMode.FILE,
                cache_directory=Path("/tmp/bedrock_cache"),
                fallback_to_bundled=True,
                timeout=5
            )
            metadata = catalog.get_catalog_metadata()
            catalog_source = metadata.source.value
            logger.info(f"Catalog initialized: {catalog_source}")
            
        except Exception as catalog_error:
            logger.warning(f"FILE cache failed: {catalog_error}")
            
            try:
                # Fallback to MEMORY cache
                catalog = BedrockModelCatalog(
                    cache_mode=CacheMode.MEMORY,
                    fallback_to_bundled=True
                )
                metadata = catalog.get_catalog_metadata()
                catalog_source = metadata.source.value
                logger.info(f"Fallback to MEMORY: {catalog_source}")
                
            except Exception as memory_error:
                logger.error(f"MEMORY cache failed: {memory_error}")
                raise
        
        # Initialize manager
        manager = LLMManager(
            models=["Claude 3 Haiku"],
            regions=["us-east-1"],
            log_level=logging.INFO
        )
        
        # Make request
        prompt = event.get("prompt", "Hello!")
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        response = manager.converse(messages=messages)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "pattern": "error_handling",
                "success": response.success,
                "content": response.get_content(),
                "catalog_source": catalog_source,
                "fallback_used": catalog_source == CatalogSource.BUNDLED.value
            })
        }
        
    except Exception as e:
        logger.error(f"All fallbacks failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "error_type": type(e).__name__,
                "message": "All initialization strategies failed"
            })
        }


# ============================================================================
# Pattern 6: Model Availability Check
# ============================================================================

def lambda_handler_pattern_6(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Pattern 6: Model availability check before use.
    
    Benefits:
    - Validate models before making requests
    - Better error messages
    - Avoid wasted API calls
    
    Use when:
    - User-specified models
    - Dynamic model selection
    - Want to validate before processing
    """
    try:
        model_name = event.get("model", "Claude 3 Haiku")
        region = event.get("region", "us-east-1")
        prompt = event.get("prompt", "Hello!")
        
        # Check if model is available
        is_available = CATALOG.is_model_available(
            model_name=model_name,
            region=region
        )
        
        if not is_available:
            # Return helpful error
            available_models = CATALOG.list_models(region=region)
            model_names = [m.model_name for m in available_models[:5]]
            
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Model '{model_name}' not available in {region}",
                    "available_models": model_names,
                    "suggestion": "Use one of the available models"
                })
            }
        
        # Model is available, proceed with request
        manager = LLMManager(
            models=[model_name],
            regions=[region],
            log_level=logging.INFO
        )
        
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        response = manager.converse(messages=messages)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "pattern": "availability_check",
                "success": response.success,
                "content": response.get_content(),
                "model_validated": True
            })
        }
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


# ============================================================================
# Main (for local testing)
# ============================================================================

def main():
    """Test all patterns locally."""
    print("=" * 60)
    print("Lambda Usage Patterns for BedrockModelCatalog")
    print("=" * 60)
    
    test_event = {"prompt": "What is machine learning?"}
    
    patterns = [
        ("Pattern 1: Global Initialization", lambda_handler_pattern_1),
        ("Pattern 2: Lazy Initialization", lambda_handler_pattern_2),
        ("Pattern 3: Memory-Only Cache", lambda_handler_pattern_3),
        ("Pattern 4: No Cache", lambda_handler_pattern_4),
        ("Pattern 5: Error Handling", lambda_handler_pattern_5),
        ("Pattern 6: Availability Check", lambda_handler_pattern_6),
    ]
    
    for name, handler in patterns:
        print(f"\n{name}")
        print("-" * 60)
        try:
            result = handler(event=test_event, context=None)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("Pattern Recommendations:")
    print("=" * 60)
    print("• Standard Lambda: Use Pattern 1 (Global Initialization)")
    print("• Read-only env: Use Pattern 3 (Memory-Only Cache)")
    print("• Security-critical: Use Pattern 4 (No Cache)")
    print("• High reliability: Use Pattern 5 (Error Handling)")
    print("• User models: Use Pattern 6 (Availability Check)")


if __name__ == "__main__":
    main()
