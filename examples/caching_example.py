"""
Example demonstrating Bedrock prompt caching support in LLM Manager.

This example shows how to use Bedrock's prompt caching feature to optimize
costs and performance when making multiple requests with shared content.

Note: This is about Bedrock prompt caching (CacheConfig), not model catalog
caching (BedrockModelCatalog cache modes). For catalog caching examples,
see catalog_cache_modes.py.
"""

from bestehorn_llmmanager import LLMManager, create_user_message
from bestehorn_llmmanager.bedrock.models.cache_structures import CacheConfig, CacheStrategy


def main():
    """Demonstrate caching with sequential prompts analyzing the same images."""
    
    # Configure caching - OFF by default, must be explicitly enabled
    cache_config = CacheConfig(
        enabled=True,
        strategy=CacheStrategy.CONSERVATIVE,
        cache_point_threshold=1000  # Minimum tokens to cache
    )
    
    # Initialize manager with caching
    manager = LLMManager(
        models=["Claude 3 Haiku"],
        regions=["us-east-1"],
        cache_config=cache_config
    )
    
    # Simulated image data (in real usage, load actual images)
    image1_bytes = b"<simulated image 1 data>"  # ~450 tokens
    image2_bytes = b"<simulated image 2 data>"  # ~450 tokens
    
    # Shared context for all prompts
    shared_context = """You are an expert architectural analyst. 
    Please analyze the following images of Gothic architecture and provide detailed insights."""
    
    # Different analysis focus areas
    analysis_prompts = [
        "Focus on the Gothic architectural elements such as pointed arches and ribbed vaults.",
        "Examine the lighting and shadow composition in the images.",
        "Identify historical period indicators and architectural influences.",
        "Analyze the structural engineering aspects of the buildings.",
        "Compare and contrast the architectural styles shown in both images."
    ]
    
    print("Starting caching example with 5 sequential prompts...\n")
    
    for i, unique_prompt in enumerate(analysis_prompts):
        print(f"--- Request {i+1} ---")
        
        # Build message with automatic cache optimization
        message = create_user_message(cache_config=cache_config)
        message.add_text(shared_context, cacheable=True)
        message.add_image_bytes(image1_bytes, filename="gothic1.jpg", cacheable=True)
        message.add_image_bytes(image2_bytes, filename="gothic2.jpg", cacheable=True)
        message.add_cache_point()  # Explicit cache point (optional with auto-optimization)
        message.add_text(unique_prompt, cacheable=False)  # Unique content not cached
        
        # Make request
        response = manager.converse(messages=[message.build()])
        
        # Check cache performance
        cache_info = response.get_cached_tokens_info()
        if cache_info:
            if cache_info['cache_write']:
                print(f"Cache WRITE: {cache_info['cache_write_tokens']} tokens")
            if cache_info['cache_hit']:
                print(f"Cache HIT: {cache_info['cache_read_tokens']} tokens")
        
        # Get efficiency metrics
        efficiency = response.get_cache_efficiency()
        if efficiency:
            print(f"Cache efficiency: {efficiency['cache_effectiveness']}%")
            print(f"Tokens saved: {efficiency['cache_savings_tokens']}")
            print(f"Cost savings: {efficiency['cache_savings_cost']}")
        
        print(f"Response: {response.get_content()[:100]}...\n")
    
    print("\n=== Caching Summary ===")
    print("Expected results:")
    print("- Request 1: Cache WRITE ~1700 tokens (first time)")
    print("- Requests 2-5: Cache HIT ~1700 tokens each")
    print("- Total tokens saved: ~6800 (80% reduction)")
    print("- Approximate cost savings: $0.20")


def example_with_manual_cache_points():
    """Example showing manual cache point placement without MessageBuilder."""
    
    manager = LLMManager(
        models=["Claude 3 Haiku"],
        regions=["us-east-1"],
        cache_config=CacheConfig(enabled=True)
    )
    
    # Manually construct message with cache point
    messages = [{
        "role": "user",
        "content": [
            {"text": "Analyze these architectural images..."},
            {"image": {"format": "jpeg", "source": {"bytes": b"..."}}},
            {"image": {"format": "jpeg", "source": {"bytes": b"..."}}},
            {"cachePoint": {"type": "default"}},  # Manual cache point
            {"text": "What Gothic elements do you see?"}
        ]
    }]
    
    response = manager.converse(messages=messages)
    print(f"Cache info: {response.get_cached_tokens_info()}")


def example_with_error_handling():
    """Example showing graceful degradation when caching is not supported."""
    
    from bestehorn_llmmanager.bedrock.models.cache_structures import CacheErrorHandling
    
    cache_config = CacheConfig(
        enabled=True,
        strategy=CacheStrategy.CONSERVATIVE,
        error_handling=CacheErrorHandling.GRACEFUL_DEGRADATION,  # Default
        cache_availability_check=True,
        log_cache_failures=True
    )
    
    # Mix of models that may or may not support caching
    manager = LLMManager(
        models=["Claude 3 Haiku", "Llama 2"],  # Hypothetical mix
        regions=["us-east-1"],
        cache_config=cache_config
    )
    
    message = create_user_message(cache_config=cache_config)
    message.add_text("Long shared context...")
    message.add_cache_point()
    message.add_text("Specific question")
    
    response = manager.converse(messages=[message.build()])
    
    # Check for warnings about cache fallbacks
    if response.warnings:
        print("Warnings:", response.warnings)
        # Example: ['Caching disabled for Llama 2 in us-east-1']


if __name__ == "__main__":
    print("=== Bedrock Caching Example ===\n")
    
    # Note: This is a demonstration example. In production:
    # 1. Use actual image data instead of simulated bytes
    # 2. Ensure your AWS credentials have access to models with caching support
    # 3. Monitor cache metrics to optimize your caching strategy
    
    # Uncomment to run examples:
    # main()
    # example_with_manual_cache_points()
    # example_with_error_handling()
    
    print("Example complete. See code for implementation details.")
