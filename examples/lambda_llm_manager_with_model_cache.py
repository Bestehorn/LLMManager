"""
AWS Lambda example using BedrockModelCatalog with MEMORY cache mode.

This example demonstrates using the new BedrockModelCatalog in Lambda
with memory-only caching for environments where /tmp is not available
or when you want to avoid file I/O.
"""

import json
import logging
from typing import Any, Dict

from bestehorn_llmmanager import LLMManager
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize catalog with MEMORY cache mode
# Data is cached in memory only - no file system access required
# Perfect for read-only Lambda environments or when /tmp is restricted
catalog = BedrockModelCatalog(
    cache_mode=CacheMode.MEMORY,
    cache_max_age_hours=24.0,
    fallback_to_bundled=True
)

# Initialize LLMManager
# The catalog data stays in memory across warm starts
manager = LLMManager(
    models=["Claude 3.5 Sonnet v2", "Claude 3 Haiku", "Nova Pro"],
    regions=["us-east-1", "us-west-2", "eu-west-1"],
    log_level=logging.INFO
)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing LLM requests with memory-only caching.
    
    Args:
        event: Lambda event containing 'prompt' and optional 'model' field
        context: Lambda context object
        
    Returns:
        Response with LLM output and metadata
    """
    try:
        # Extract parameters from event
        prompt = event.get("prompt", "Hello, how are you?")
        preferred_model = event.get("model")  # Optional model override
        
        logger.info(f"Processing prompt: {prompt[:50]}...")
        
        # Get catalog metadata
        metadata = catalog.get_catalog_metadata()
        logger.info(
            f"Catalog source: {metadata.source.value} "
            f"(memory-only, no file I/O)"
        )
        
        # Build message
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        # Make request with optional model override
        if preferred_model:
            # Create temporary manager with specific model
            temp_manager = LLMManager(
                models=[preferred_model],
                regions=["us-east-1", "us-west-2"],
                log_level=logging.INFO
            )
            response = temp_manager.converse(messages=messages)
        else:
            response = manager.converse(messages=messages)
        
        # Check if model is available
        if preferred_model:
            is_available = catalog.is_model_available(
                model_name=preferred_model,
                region="us-east-1"
            )
            logger.info(f"Model {preferred_model} available: {is_available}")
        
        # Return response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": response.success,
                "content": response.get_content(),
                "model_used": response.model_used,
                "region_used": response.region_used,
                "catalog_source": metadata.source.value,
                "cache_mode": "MEMORY",
                "duration_ms": response.total_duration_ms,
                "usage": response.get_usage()  # Or use accessor methods: response.get_input_tokens(), etc.
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "error_type": type(e).__name__
            })
        }


def check_model_availability(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Alternative handler to check model availability.
    
    Args:
        event: Lambda event containing 'model' and 'region' fields
        context: Lambda context object
        
    Returns:
        Model availability information
    """
    try:
        model_name = event.get("model", "Claude 3 Haiku")
        region = event.get("region", "us-east-1")
        
        # Check availability
        is_available = catalog.is_model_available(
            model_name=model_name,
            region=region
        )
        
        # Get model info if available
        model_info = None
        if is_available:
            model_info = catalog.get_model_info(
                model_name=model_name,
                region=region
            )
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "model": model_name,
                "region": region,
                "available": is_available,
                "model_info": str(model_info) if model_info else None
            })
        }
        
    except Exception as e:
        logger.error(f"Error checking availability: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "error_type": type(e).__name__
            })
        }


# For local testing
if __name__ == "__main__":
    # Test 1: Basic prompt
    print("Test 1: Basic prompt")
    test_event = {
        "prompt": "What is the capital of France?"
    }
    result = lambda_handler(event=test_event, context=None)
    print(json.dumps(result, indent=2))
    
    # Test 2: Model availability check
    print("\nTest 2: Model availability check")
    availability_event = {
        "model": "Claude 3 Haiku",
        "region": "us-east-1"
    }
    result = check_model_availability(event=availability_event, context=None)
    print(json.dumps(result, indent=2))
