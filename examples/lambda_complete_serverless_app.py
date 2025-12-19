"""
AWS Lambda example using BedrockModelCatalog with NONE cache mode.

This example demonstrates using the new BedrockModelCatalog in Lambda
with no caching - always fetching fresh data from AWS APIs with bundled
data fallback. Useful for environments with strict security requirements
or when you always want the latest model information.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from bestehorn_llmmanager import LLMManager, create_user_message
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize catalog with NONE cache mode
# No caching - always tries API first, falls back to bundled data
# Ensures latest model availability but may have higher latency
catalog = BedrockModelCatalog(
    cache_mode=CacheMode.NONE,
    fallback_to_bundled=True,
    timeout=10,  # Shorter timeout for Lambda
    max_workers=5  # Limit parallel workers for Lambda
)

# Initialize LLMManager
manager = LLMManager(
    models=["Claude 3.5 Sonnet v2", "Claude 3 Haiku", "Nova Pro"],
    regions=["us-east-1", "us-west-2"],
    log_level=logging.INFO
)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for processing LLM requests with no caching.
    
    Supports multiple operations:
    - 'converse': Standard conversation
    - 'stream': Streaming conversation
    - 'list_models': List available models
    - 'check_availability': Check model availability
    
    Args:
        event: Lambda event with 'operation' and operation-specific fields
        context: Lambda context object
        
    Returns:
        Response based on operation
    """
    try:
        operation = event.get("operation", "converse")
        
        if operation == "converse":
            return handle_converse(event=event, context=context)
        elif operation == "stream":
            return handle_stream(event=event, context=context)
        elif operation == "list_models":
            return handle_list_models(event=event, context=context)
        elif operation == "check_availability":
            return handle_check_availability(event=event, context=context)
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Unknown operation: {operation}",
                    "supported_operations": [
                        "converse",
                        "stream",
                        "list_models",
                        "check_availability"
                    ]
                })
            }
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "error_type": type(e).__name__
            })
        }


def handle_converse(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle standard conversation request."""
    try:
        prompt = event.get("prompt", "Hello!")
        system_prompt = event.get("system_prompt")
        
        logger.info(f"Converse: {prompt[:50]}...")
        
        # Get catalog metadata
        metadata = catalog.get_catalog_metadata()
        logger.info(
            f"Catalog source: {metadata.source.value} "
            f"(no caching, fresh data)"
        )
        
        # Build message
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        # Add system prompt if provided
        system = None
        if system_prompt:
            system = [{"text": system_prompt}]
        
        # Make request
        response = manager.converse(messages=messages, system=system)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "operation": "converse",
                "success": response.success,
                "content": response.get_content(),
                "model_used": response.model_used,
                "region_used": response.region_used,
                "catalog_source": metadata.source.value,
                "cache_mode": "NONE",
                "duration_ms": response.total_duration_ms,
                "usage": response.get_usage()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in handle_converse: {e}", exc_info=True)
        raise


def handle_stream(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle streaming conversation request.
    
    Note: Lambda doesn't support true streaming responses by default.
    This collects the full stream and returns it.
    For true streaming, use Lambda Function URLs with response streaming.
    """
    try:
        prompt = event.get("prompt", "Hello!")
        
        logger.info(f"Stream: {prompt[:50]}...")
        
        # Build message
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        # Make streaming request
        streaming_response = manager.converse_stream(messages=messages)
        
        # Collect stream (Lambda doesn't support true streaming by default)
        chunks: List[str] = []
        for chunk in streaming_response:
            chunks.append(chunk)
        
        full_content = "".join(chunks)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "operation": "stream",
                "success": streaming_response.success,
                "content": full_content,
                "chunks_count": len(chunks),
                "model_used": streaming_response.model_used,
                "region_used": streaming_response.region_used,
                "cache_mode": "NONE",
                "duration_ms": streaming_response.total_duration_ms,
                "usage": streaming_response.get_usage()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in handle_stream: {e}", exc_info=True)
        raise


def handle_list_models(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle list models request."""
    try:
        region = event.get("region")
        provider = event.get("provider")
        streaming_only = event.get("streaming_only", False)
        
        logger.info(
            f"List models: region={region}, provider={provider}, "
            f"streaming_only={streaming_only}"
        )
        
        # List models with filters
        models = catalog.list_models(
            region=region,
            provider=provider,
            streaming_only=streaming_only
        )
        
        # Convert to serializable format
        models_data = [
            {
                "model_id": model.model_id,
                "model_name": model.model_name,
                "provider": model.provider,
                "regions": model.regions,
                "supports_streaming": model.supports_streaming
            }
            for model in models
        ]
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "operation": "list_models",
                "count": len(models_data),
                "models": models_data,
                "filters": {
                    "region": region,
                    "provider": provider,
                    "streaming_only": streaming_only
                }
            })
        }
        
    except Exception as e:
        logger.error(f"Error in handle_list_models: {e}", exc_info=True)
        raise


def handle_check_availability(
    event: Dict[str, Any],
    context: Any
) -> Dict[str, Any]:
    """Handle model availability check request."""
    try:
        model_name = event.get("model", "Claude 3 Haiku")
        region = event.get("region", "us-east-1")
        
        logger.info(f"Check availability: {model_name} in {region}")
        
        # Check availability
        is_available = catalog.is_model_available(
            model_name=model_name,
            region=region
        )
        
        # Get model info if available
        model_info = None
        if is_available:
            info = catalog.get_model_info(
                model_name=model_name,
                region=region
            )
            if info:
                model_info = {
                    "model_id": info.model_id,
                    "inference_profile_id": info.inference_profile_id,
                    "access_method": info.access_method.value if info.access_method else None,
                    "supports_streaming": info.supports_streaming
                }
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "operation": "check_availability",
                "model": model_name,
                "region": region,
                "available": is_available,
                "model_info": model_info
            })
        }
        
    except Exception as e:
        logger.error(f"Error in handle_check_availability: {e}", exc_info=True)
        raise


# For local testing
if __name__ == "__main__":
    print("=" * 60)
    print("Complete Serverless App Example (NONE cache mode)")
    print("=" * 60)
    
    # Test 1: Converse
    print("\nTest 1: Converse operation")
    print("-" * 60)
    converse_event = {
        "operation": "converse",
        "prompt": "What is machine learning?",
        "system_prompt": "You are a helpful AI assistant."
    }
    result = lambda_handler(event=converse_event, context=None)
    print(json.dumps(result, indent=2))
    
    # Test 2: List models
    print("\nTest 2: List models operation")
    print("-" * 60)
    list_event = {
        "operation": "list_models",
        "region": "us-east-1",
        "streaming_only": False
    }
    result = lambda_handler(event=list_event, context=None)
    print(json.dumps(result, indent=2))
    
    # Test 3: Check availability
    print("\nTest 3: Check availability operation")
    print("-" * 60)
    check_event = {
        "operation": "check_availability",
        "model": "Claude 3 Haiku",
        "region": "us-east-1"
    }
    result = lambda_handler(event=check_event, context=None)
    print(json.dumps(result, indent=2))
    
    print("\n" + "=" * 60)
    print("Tests completed!")
