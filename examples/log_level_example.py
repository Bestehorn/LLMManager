"""
Example demonstrating log level configuration in LLMManager.

This example shows how to control the amount of logging output from LLMManager
by setting different log levels at initialization time.
"""

import logging
from bestehorn_llmmanager import LLMManager, ParallelLLMManager, create_user_message

def demo_log_levels():
    """Demonstrate different log level configurations."""
    
    print("=" * 60)
    print("LLMManager Log Level Configuration Example")
    print("=" * 60)
    
    # Example 1: Default log level (WARNING) - minimal output
    print("\n1. Default log level (WARNING) - Minimal output:")
    print("-" * 50)
    manager_default = LLMManager(
        models=["Claude 3 Haiku"],
        regions=["us-east-1"]
    )
    print("✓ Manager created with default WARNING level")
    print("  Only warnings and errors will be shown")
    
    # Example 2: INFO level - moderate output
    print("\n2. INFO log level - Moderate output:")
    print("-" * 50)
    manager_info = LLMManager(
        models=["Claude 3 Haiku"],
        regions=["us-east-1"],
        log_level=logging.INFO
    )
    print("✓ Manager created with INFO level")
    print("  Info messages, warnings, and errors will be shown")
    
    # Example 3: ERROR level - minimal output
    print("\n3. ERROR log level - Very minimal output:")
    print("-" * 50)
    manager_error = LLMManager(
        models=["Claude 3 Haiku"],
        regions=["us-east-1"],
        log_level="ERROR"  # Can use string
    )
    print("✓ Manager created with ERROR level")
    print("  Only errors will be shown")
    
    # Example 4: DEBUG level - verbose output
    print("\n4. DEBUG log level - Verbose output:")
    print("-" * 50)
    manager_debug = LLMManager(
        models=["Claude 3 Haiku"],
        regions=["us-east-1"],
        log_level=logging.DEBUG
    )
    print("✓ Manager created with DEBUG level")
    print("  All messages including debug info will be shown")
    
    # Example 5: ParallelLLMManager with log level
    print("\n5. ParallelLLMManager with custom log level:")
    print("-" * 50)
    parallel_manager = ParallelLLMManager(
        models=["Claude 3 Haiku"],
        regions=["us-east-1", "us-west-2"],
        log_level=logging.WARNING  # Default level
    )
    print("✓ ParallelLLMManager created with WARNING level")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary of Log Levels:")
    print("=" * 60)
    print("• DEBUG (10)    - Most verbose, shows everything")
    print("• INFO (20)     - Informational messages + warnings/errors")
    print("• WARNING (30)  - Default level, warnings + errors only")
    print("• ERROR (40)    - Only error messages")
    print("• CRITICAL (50) - Only critical error messages")
    print("\nLog levels can be set using:")
    print("• Logging constants: logging.DEBUG, logging.INFO, etc.")
    print("• Strings: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'")
    print("• Integers: 10, 20, 30, 40, 50")
    
    # Example usage (would require AWS credentials)
    print("\n" + "=" * 60)
    print("Example Usage (requires AWS credentials):")
    print("=" * 60)
    print("""
# Create a message
message = create_user_message().add_text("Hello!").build()

# Make a request (will only show warnings/errors with default level)
try:
    response = manager_default.converse(messages=[message])
    print(f"Success: {response.success}")
except Exception as e:
    print(f"Note: {e}")
""")

if __name__ == "__main__":
    demo_log_levels()
