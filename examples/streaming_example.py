"""
Example demonstrating real streaming functionality in LLM Manager.

This example shows how to use the new converse_stream method that provides
real-time streaming responses using the AWS Bedrock converse_stream API.
"""

import asyncio
import logging
from typing import Iterator

from bestehorn_llmmanager import LLMManager
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import AuthConfig, RetryConfig
from bestehorn_llmmanager.bedrock.streaming.stream_processor import StreamProcessor


def basic_streaming_example():
    """Demonstrate basic streaming functionality."""
    print("=== Basic Streaming Example ===")
    
    # Initialize LLM Manager
    manager = LLMManager(
        models=["Claude 3 Haiku"],
        regions=["us-east-1"],
        log_level=logging.INFO
    )
    
    # Prepare messages
    messages = [
        {
            "role": "user",
            "content": [{"text": "Write a short story about a robot learning to paint. Make it about 3 paragraphs."}]
        }
    ]
    
    try:
        # Use streaming API
        print("Starting streaming request...")
        streaming_response = manager.converse_stream(messages=messages)
        
        print(f"Streaming completed!")
        print(f"Success: {streaming_response.success}")
        print(f"Model used: {streaming_response.model_used}")
        print(f"Region used: {streaming_response.region_used}")
        print(f"Total duration: {streaming_response.total_duration_ms:.1f}ms")
        print(f"API latency: {streaming_response.api_latency_ms}ms" if streaming_response.api_latency_ms else "API latency: N/A")
        print(f"Content parts received: {len(streaming_response.content_parts)}")
        print(f"Stop reason: {streaming_response.stop_reason}")
        
        # Get full content
        full_content = streaming_response.get_full_content()
        print(f"\nGenerated content ({len(full_content)} characters):")
        print("-" * 50)
        print(full_content)
        print("-" * 50)
        
        # Show streaming metadata
        if streaming_response.usage_info:
            usage = streaming_response.usage_info
            print(f"\nToken usage:")
            print(f"  Input tokens: {usage.get('input_tokens', 0)}")
            print(f"  Output tokens: {usage.get('output_tokens', 0)}")
            print(f"  Total tokens: {usage.get('total_tokens', 0)}")
            
        if streaming_response.warnings:
            print(f"\nWarnings: {streaming_response.warnings}")
            
    except Exception as e:
        print(f"Streaming failed: {e}")
        # Additional error details if available
        if hasattr(e, '__dict__'):
            error_attrs = [attr for attr in dir(e) if not attr.startswith('_') and hasattr(e, attr)]
            if error_attrs:
                print(f"Error details: {[f'{attr}={getattr(e, attr, None)}' for attr in error_attrs[:3]]}")


def streaming_with_iterator_example():
    """Demonstrate real-time streaming with iterator (conceptual example)."""
    print("\n=== Real-time Streaming Iterator Concept ===")
    
    # Note: This is a conceptual example showing how you could implement
    # real-time streaming iteration. The actual implementation would require
    # modifications to expose the iterator from the StreamProcessor.
    
    print("This would allow real-time processing of streaming chunks:")
    print("for chunk in manager.converse_stream_iterator(messages):")
    print("    print(chunk, end='', flush=True)  # Print as it arrives")
    print("\nTo implement this, you could modify StreamProcessor.create_streaming_iterator")
    print("to be exposed through the LLM Manager interface.")


def streaming_error_recovery_example():
    """Demonstrate streaming error recovery."""
    print("\n=== Streaming Error Recovery Example ===")
    
    # Configure with specific retry settings
    retry_config = RetryConfig(
        max_retries=3,
        retry_delay=1.0,
        max_retry_delay=10.0,
        backoff_multiplier=2.0  # Exponential backoff multiplier
    )
    
    manager = LLMManager(
        models=["Claude 3 Haiku", "Claude 3 Sonnet"],  # Multiple models for fallback
        regions=["us-east-1", "us-west-2"],  # Multiple regions for fallback
        retry_config=retry_config,
        log_level=logging.INFO
    )
    
    # Long prompt that might be more prone to interruption
    messages = [
        {
            "role": "user", 
            "content": [{"text": "Write a detailed technical explanation of how neural networks work, including the mathematical foundations, backpropagation algorithm, and common architectures. Make it comprehensive and detailed."}]
        }
    ]
    
    try:
        print("Starting streaming request with error recovery...")
        streaming_response = manager.converse_stream(messages=messages)
        
        if streaming_response.success:
            print(f"✓ Streaming completed successfully!")
            print(f"Model: {streaming_response.model_used}")
            print(f"Region: {streaming_response.region_used}")
            print(f"Content length: {len(streaming_response.get_full_content())} characters")
            
            if streaming_response.warnings:
                print(f"⚠ Warnings encountered: {streaming_response.warnings}")
                
        else:
            print("✗ Streaming failed despite retry attempts")
            if streaming_response.stream_errors:
                print(f"Errors: {[str(e) for e in streaming_response.stream_errors]}")
                
    except Exception as e:
        print(f"Streaming failed with exception: {e}")


def compare_streaming_vs_regular():
    """Compare streaming vs regular response for the same prompt."""
    print("\n=== Streaming vs Regular Comparison ===")
    
    manager = LLMManager(
        models=["Claude 3 Haiku"],
        regions=["us-east-1"],
        log_level=logging.WARNING  # Reduce noise for comparison
    )
    
    messages = [
        {
            "role": "user",
            "content": [{"text": "Explain the concept of machine learning in 2 paragraphs."}]
        }
    ]
    
    print("1. Regular converse() call:")
    try:
        regular_response = manager.converse(messages=messages)
        print(f"   ✓ Success: {regular_response.success}")
        print(f"   ✓ Duration: {regular_response.total_duration_ms:.1f}ms")
        print(f"   ✓ Content length: {len(regular_response.get_content() or '')}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    print("\n2. Streaming converse_stream() call:")
    try:
        streaming_response = manager.converse_stream(messages=messages)
        print(f"   ✓ Success: {streaming_response.success}")
        print(f"   ✓ Duration: {streaming_response.total_duration_ms:.1f}ms")
        print(f"   ✓ Content length: {len(streaming_response.get_full_content())}")
        print(f"   ✓ Content parts: {len(streaming_response.content_parts)}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")


if __name__ == "__main__":
    print("LLM Manager Real Streaming Examples")
    print("=" * 40)
    print("Note: These examples require valid AWS credentials and access to Bedrock models.")
    print()
    
    # Run examples
    basic_streaming_example()
    streaming_with_iterator_example()
    streaming_error_recovery_example()
    compare_streaming_vs_regular()
    
    print("\n" + "=" * 40)
    print("Examples completed!")
