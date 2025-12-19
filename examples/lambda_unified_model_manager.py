"""
AWS Lambda example using BedrockModelCatalog with FILE cache mode.

This example demonstrates using the new BedrockModelCatalog in Lambda
with file-based caching to /tmp for warm start optimization.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from bestehorn_llmmanager import LLMManager
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize catalog with FILE cache mode for Lambda /tmp directory
# This enables warm start optimization - subsequent invocations reuse cached data
catalog = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("/tmp/bedrock_cache"),
    cache_max_age_hours=24.0,
    fallback_to_bundled=True
)

# Initialize LLMManager with the catalog
# The catalog is shared across warm starts for better performance
manager = LLMManager(
    models=["Claude 3.5 Sonnet v2", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"],
    log_level=logging.INFO
)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing LLM requests.
    
    Args:
        event: Lambda event containing 'prompt' field
        context: Lambda context object
        
    Returns:
        Response with LLM output and metadata
    """
    try:
        # Extract prompt from event
        prompt = event.get("prompt", "Hello, how are you?")
        
        logger.info(f"Processing prompt: {prompt[:50]}...")
        
        # Get catalog metadata to show cache status
        metadata = catalog.get_catalog_metadata()
        logger.info(
            f"Catalog source: {metadata.source.value}, "
            f"timestamp: {metadata.retrieval_timestamp}"
        )
        
        # Build message
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        # Make request
        response = manager.converse(messages=messages)
        
        # Return response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": response.success,
                "content": response.get_content(),
                "model_used": response.model_used,
                "region_used": response.region_used,
                "catalog_source": metadata.source.value,
                "duration_ms": response.total_duration_ms
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


# For local testing
if __name__ == "__main__":
    # Simulate Lambda event
    test_event = {
        "prompt": "Explain machine learning in one sentence."
    }
    
    # Call handler
    result = lambda_handler(event=test_event, context=None)
    
    # Print result
    print(json.dumps(result, indent=2))
