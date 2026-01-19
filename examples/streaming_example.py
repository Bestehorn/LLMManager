"""
Example demonstrating real streaming functionality in LLM Manager.

This example shows how to use the new converse_stream method that provides
real-time streaming responses using the AWS Bedrock converse_stream API.
"""

import logging

from bestehorn_llmmanager import LLMManager
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig


def basic_streaming_example():
    """Demonstrate basic streaming functionality."""
    print("=== Basic Streaming Example ===")
    
    # Use available models after refresh
    models = ["Claude 3.5 Sonnet v2", "Claude 3 Haiku", "Claude 3 Sonnet"]
    regions = ["us-east-1", "us-west-2", "eu-west-1"]
    
    # Initialize manager
    # The new BedrockModelCatalog handles data fetching automatically
    manager = LLMManager(
        models=models,
        regions=regions,
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
        # Use streaming API with real-time display
        print("Starting real-time streaming...")
        streaming_response = manager.converse_stream(messages=messages)
        
        print("\n📺 Real-time streaming output:")
        print("-" * 50)
        
        # Iterate through streaming response for real-time display
        try:
            for chunk in streaming_response:
                print(chunk, end='', flush=True)  # Real-time streaming display
        except Exception as stream_error:
            print(f"\n❌ Streaming interrupted: {stream_error}")
        
        print(f"\n{'-' * 50}")
        print(f"✅ Streaming completed!")
        
        # Now show model/region info after streaming completes
        print(f"🌊 Model: {streaming_response.model_used}")
        print(f"🌍 Region: {streaming_response.region_used}")
        
        # Show final metadata (available after streaming completes)
        print(f"📊 Final Status:")
        print(f"   Success: {streaming_response.success}")
        print(f"   Duration: {streaming_response.total_duration_ms:.1f}ms" if streaming_response.total_duration_ms else "   Duration: N/A")
        print(f"   API Latency: {streaming_response.api_latency_ms:.1f}ms" if streaming_response.api_latency_ms else "   API Latency: N/A")
        print(f"   Content Parts: {len(streaming_response.content_parts)}")
        print(f"   Stop Reason: {streaming_response.stop_reason}")
        
        # Show streaming token usage (available after completion)
        usage = streaming_response.get_usage()
        if usage:
            print(f"\n🎯 Token Usage:")
            print(f"   Input tokens: {streaming_response.get_input_tokens()}")
            print(f"   Output tokens: {streaming_response.get_output_tokens()}")
            print(f"   Total tokens: {streaming_response.get_total_tokens()}")
            
        if streaming_response.warnings:
            print(f"\n⚠️ Warnings: {streaming_response.warnings}")
            
    except Exception as e:
        print(f"❌ Streaming failed: {e}")


def streaming_with_iterator_example():
    """Demonstrate real-time streaming with iterator (actual implementation)."""
    print("\n=== Real-time Streaming Iterator Example ===")
    
    models = ["Claude 3.5 Sonnet v2", "Claude 3 Haiku"]
    regions = ["us-east-1", "us-west-2", "eu-west-1"]
    
    # Initialize manager
    # The new BedrockModelCatalog handles data fetching automatically
    manager = LLMManager(
        models=models,
        regions=regions,
        log_level=logging.WARNING
    )
    
    messages = [
        {
            "role": "user",
            "content": [{"text": "Explain how machine learning works in 2 paragraphs."}]
        }
    ]
    
    try:
        print("Real-time streaming iterator usage:")
        print(">>> streaming_response = manager.converse_stream(messages)")
        print(">>> for chunk in streaming_response:")
        print("...     print(chunk, end='', flush=True)")
        print()
        
        streaming_response = manager.converse_stream(messages=messages)
        
        print("📡 Live streaming output:")
        print("-" * 40)
        
        for chunk in streaming_response:
            print(chunk, end='', flush=True)  # Real-time display
            
        print("\n" + "-" * 40)
        print(f"✅ Iterator completed! Final status: {streaming_response.success}")
        
        # Show enhanced metrics with timing
        metrics = streaming_response.get_metrics()
        if metrics:
            print(f"⏱️  Enhanced Timing Metrics:")
            if "time_to_first_token_ms" in metrics:
                print(f"   Time to first token: {metrics['time_to_first_token_ms']:.1f}ms")
            if "time_to_last_token_ms" in metrics:
                print(f"   Time to last token: {metrics['time_to_last_token_ms']:.1f}ms")
            if "token_generation_duration_ms" in metrics:
                print(f"   Token generation duration: {metrics['token_generation_duration_ms']:.1f}ms")
        
    except Exception as e:
        print(f"❌ Iterator example failed: {e}")


def streaming_error_recovery_example():
    """Demonstrate streaming error recovery with detailed diagnostics."""
    print("\n=== Streaming Error Recovery Example ===")
    
    # Configure with specific retry settings for better recovery demonstration
    retry_config = RetryConfig(
        max_retries=4,
        retry_delay=0.5,
        max_retry_delay=8.0,
        backoff_multiplier=1.8
    )
    
    # Use multiple models and regions for comprehensive fallback testing
    models = ["Claude 3.5 Sonnet v2", "Claude 3 Haiku", "Claude 3 Sonnet", "Nova Pro"]
    regions = ["us-east-1", "us-west-2", "eu-west-1"]
    
    try:
        manager = LLMManager(
            models=models,
            regions=regions,
            retry_config=retry_config,
            log_level=logging.WARNING  # Reduce noise but capture important events
        )
    except Exception as e:
        print(f"❌ Failed to initialize LLM Manager: {e}")
        return
    
    # Create a challenging prompt that might trigger throttling or other issues
    messages = [
        {
            "role": "user", 
            "content": [{"text": "Write a comprehensive technical explanation of machine learning algorithms, including supervised learning, unsupervised learning, neural networks, deep learning architectures, optimization techniques, and practical applications. Include mathematical foundations and real-world examples. Make it detailed and thorough."}]
        }
    ]
    
    print("🔄 Starting streaming request with enhanced error recovery...")
    print(f"📊 Configuration: {len(models)} models × {len(regions)} regions = {len(models) * len(regions)} possible attempts")
    
    try:
        streaming_response = manager.converse_stream(messages=messages)
        
        print("📡 Live streaming output:")
        print("-" * 50)
        
        # Actually consume the stream to trigger API calls and recovery logic
        try:
            for chunk in streaming_response:
                print(chunk, end='', flush=True)  # Real-time streaming display
        except Exception as stream_error:
            print(f"\n❌ Streaming interrupted: {stream_error}")
        
        print(f"\n{'-' * 50}")
        
        # NOW we can check recovery info after the stream has been consumed
        recovery_info = streaming_response.get_recovery_info()
        mid_stream_exceptions = streaming_response.get_mid_stream_exceptions()
        
        print(f"\n📈 Results:")
        if streaming_response.success:
            print(f"✅ Streaming completed successfully!")
            print(f"🤖 Model used: {streaming_response.model_used}")
            print(f"🌍 Region used: {streaming_response.region_used}")
            print(f"📝 Content length: {len(streaming_response.get_full_content())} characters")
            print(f"📦 Content parts: {len(streaming_response.content_parts)}")
            print(f"⏱️  Duration: {streaming_response.total_duration_ms:.1f}ms" if streaming_response.total_duration_ms else "⏱️  Duration: N/A")
            print(f"🔚 Stop reason: {streaming_response.stop_reason}")
            
            # Show mid-stream recovery information
            if recovery_info.get("recovery_enabled", False):
                print(f"\n🔄 Mid-Stream Recovery Information:")
                print(f"   Total exceptions: {recovery_info.get('total_exceptions', 0)}")
                print(f"   Recovered exceptions: {recovery_info.get('recovered_exceptions', 0)}")
                print(f"   Target switches: {recovery_info.get('target_switches', 0)}")
                
                if mid_stream_exceptions:
                    print(f"   Mid-stream exceptions handled:")
                    for i, exc in enumerate(mid_stream_exceptions, 1):
                        status = "✅ recovered" if exc["recovered"] else "❌ failed"
                        print(f"     {i}. {exc['error_type']} at position {exc['position']} ({exc['model']}, {exc['region']}) - {status}")
                        if len(exc['error_message']) < 100:
                            print(f"        Error: {exc['error_message']}")
                else:
                    print(f"   No mid-stream exceptions occurred")
                
                if recovery_info.get("final_model") != models[0] or recovery_info.get("final_region") != regions[0]:
                    print(f"   🔄 Stream switched to: {recovery_info.get('final_model')} in {recovery_info.get('final_region')}")
            
            # Show token usage if available
            if streaming_response.get_total_tokens() > 0:
                print(f"\n🎯 Token usage: {streaming_response.get_input_tokens()} input + {streaming_response.get_output_tokens()} output = {streaming_response.get_total_tokens()} total")
            
            # Show enhanced timing metrics
            metrics = streaming_response.get_metrics()
            if metrics:
                print(f"\n⚡ Enhanced Timing Metrics:")
                if "time_to_first_token_ms" in metrics:
                    print(f"   Time to first token: {metrics['time_to_first_token_ms']:.1f}ms")
                if "token_generation_duration_ms" in metrics:
                    print(f"   Token generation time: {metrics['token_generation_duration_ms']:.1f}ms")
            
            if streaming_response.warnings:
                print(f"\n⚠️  Warnings: {streaming_response.warnings}")
                
        else:
            print("❌ Streaming failed despite retry attempts")
            print(f"🔍 Diagnosis:")
            
            # Show recovery information for failed requests too
            if recovery_info.get("recovery_enabled", False):
                print(f"   Recovery attempts made:")
                print(f"     Total exceptions: {recovery_info.get('total_exceptions', 0)}")
                print(f"     Recovered exceptions: {recovery_info.get('recovered_exceptions', 0)}")
                print(f"     Target switches: {recovery_info.get('target_switches', 0)}")
                
                if mid_stream_exceptions:
                    print(f"   Mid-stream exceptions:")
                    for i, exc in enumerate(mid_stream_exceptions, 1):
                        status = "recovered" if exc["recovered"] else "failed"
                        print(f"     {i}. {exc['error_type']} at pos {exc['position']} ({status})")
            
            # Show stream errors
            if streaming_response.stream_errors:
                print(f"   Stream errors ({len(streaming_response.stream_errors)}):")
                for i, error in enumerate(streaming_response.stream_errors, 1):
                    print(f"     {i}. {type(error).__name__}: {str(error)}")
            
            # Show partial content if any was received
            partial_content = streaming_response.get_full_content()
            if partial_content:
                print(f"   Partial content received: {len(partial_content)} characters")
                print(f"   Content parts: {len(streaming_response.content_parts)}")
            else:
                print(f"   No content received")
                
    except Exception as e:
        print(f"❌ Exception during streaming: {type(e).__name__}: {e}")
        
        # Try to extract more detailed error information
        if hasattr(e, 'response'):
            error_response = getattr(e, 'response', None)
            if error_response:
                error_code = error_response.get("Error", {}).get("Code", "Unknown")
                error_message = error_response.get("Error", {}).get("Message", str(e))
                print(f"   AWS Error Code: {error_code}")
                print(f"   AWS Error Message: {error_message}")


def compare_streaming_vs_regular():
    """Compare streaming vs regular response for the same prompt."""
    print("\n=== Streaming vs Regular Comparison ===")
    
    # Use correct model names
    models = ["Claude 3.5 Sonnet v2", "Claude 3 Haiku", "Nova Pro", "Nova Lite"]
    regions = ["us-east-1", "us-west-2", "eu-west-1"]
    
    manager = LLMManager(
        models=models,
        regions=regions,
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
        
        # Actually consume the stream to get the content
        for chunk in streaming_response:
            pass  # Just consume without printing for this comparison
        
        print(f"   ✓ Success: {streaming_response.success}")
        duration_str = f"{streaming_response.total_duration_ms:.1f}ms" if streaming_response.total_duration_ms is not None else "N/A"
        print(f"   ✓ Duration: {duration_str}")
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
