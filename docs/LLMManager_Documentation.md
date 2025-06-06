# LLMManager Documentation

## Overview

The `LLMManager` class is the primary interface for interacting with AWS Bedrock Large Language Models (LLMs). It provides a unified, production-ready API that abstracts the complexity of multi-model, multi-region LLM interactions with automatic failover, retry logic, authentication handling, and comprehensive response management.

## Table of Contents

- [Architecture](#architecture)
- [Installation and Setup](#installation-and-setup)
- [Basic Usage](#basic-usage)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Response Objects](#response-objects)
- [Advanced Features](#advanced-features)
- [Integration Examples](#integration-examples)
- [Performance Considerations](#performance-considerations)
- [Best Practices](#best-practices)

## Architecture

The LLMManager orchestrates several components to provide a seamless LLM experience:

### Core Components

```
LLMManager
├── UnifiedModelManager    # Model registry and access information
├── AuthManager           # Authentication handling
├── RetryManager          # Retry logic and failover
└── MessageBuilder        # Message construction utilities
```

### Data Flow

```
User Request → LLMManager → Request Validation → Auth → Retry Logic → AWS Bedrock → Response Processing → User
                    ↓
              [UnifiedModelManager] → Model/Region Selection
                    ↓
              [RetryManager] → Failover Logic
                    ↓
              [AuthManager] → Credential Management
```

### Key Features

- **Multi-Model Support**: Works with multiple LLM models simultaneously
- **Multi-Region Failover**: Automatic failover across AWS regions
- **Authentication Management**: Supports profiles, IAM roles, and credentials
- **Retry Logic**: Intelligent retry with exponential backoff
- **Response Validation**: Optional response validation with retry
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **Type Safety**: Full type hints for better IDE support and error prevention

## Installation and Setup

### Prerequisites

- Python 3.9 or higher
- AWS credentials configured
- Required dependencies installed

### Basic Setup

```python
from src.LLMManager import LLMManager

# Minimal setup - uses default authentication
manager = LLMManager(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1"]
)
```

### Advanced Setup

```python
from src.LLMManager import LLMManager
from src.bedrock.models.llm_manager_structures import (
    AuthConfig, RetryConfig, AuthenticationType, RetryStrategy
)

# Advanced configuration
auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="my-aws-profile",
    region_override="us-east-1"
)

retry_config = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF
)

manager = LLMManager(
    models=["Claude 3.5 Sonnet", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2", "eu-west-1"],
    auth_config=auth_config,
    retry_config=retry_config,
    default_inference_config={
        "maxTokens": 1000,
        "temperature": 0.7
    },
    timeout=60
)
```

## Basic Usage

### Simple Text Conversation

```python
from src.bedrock.models.message_builder_factory import create_user_message

# Create a simple message
message = create_user_message() \
    .add_text("What is the capital of France?") \
    .build()

# Send the request
response = manager.converse(messages=[message])

# Get the response content
answer = response.get_content()
print(f"Answer: {answer}")
print(f"Model used: {response.model_used}")
print(f"Region used: {response.region_used}")
```

### Multi-Turn Conversation

```python
# Build conversation history
messages = [
    create_user_message().add_text("Hello, I'm learning about Python.").build(),
    {
        "role": "assistant",
        "content": [{"text": "Hello! I'd be happy to help you learn Python. What specific topic would you like to explore?"}]
    },
    create_user_message().add_text("Can you explain list comprehensions?").build()
]

response = manager.converse(messages=messages)
print(response.get_content())
```

### Multi-Modal Messages

```python
# Text + Image
message = create_user_message() \
    .add_text("Please analyze this chart and explain the trends:") \
    .add_local_image("data/sales_chart.png") \
    .build()

response = manager.converse(messages=[message])
print(response.get_content())

# Text + Document
message = create_user_message() \
    .add_text("Summarize the key points from this report:") \
    .add_local_document("reports/quarterly_report.pdf") \
    .build()

response = manager.converse(messages=[message])
```

## API Reference

### LLMManager Class

#### Constructor

```python
def __init__(
    self,
    models: List[str],
    regions: List[str],
    auth_config: Optional[AuthConfig] = None,
    retry_config: Optional[RetryConfig] = None,
    unified_model_manager: Optional[UnifiedModelManager] = None,
    default_inference_config: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> None
```

**Parameters:**

- `models`: List of model names to use (e.g., `["Claude 3.5 Sonnet", "Claude 3 Haiku"]`)
- `regions`: List of AWS regions to try (e.g., `["us-east-1", "us-west-2"]`)
- `auth_config`: Authentication configuration (optional, auto-detects if None)
- `retry_config`: Retry behavior configuration (optional, uses defaults if None)
- `unified_model_manager`: Pre-configured model manager (optional)
- `default_inference_config`: Default inference parameters (optional)
- `timeout`: Request timeout in seconds (default: 30)

#### Core Methods

##### converse()

```python
def converse(
    self,
    messages: List[Dict[str, Any]],
    system: Optional[List[Dict[str, str]]] = None,
    inference_config: Optional[Dict[str, Any]] = None,
    additional_model_request_fields: Optional[Dict[str, Any]] = None,
    additional_model_response_field_paths: Optional[List[str]] = None,
    guardrail_config: Optional[Dict[str, Any]] = None,
    tool_config: Optional[Dict[str, Any]] = None,
    request_metadata: Optional[Dict[str, Any]] = None,
    prompt_variables: Optional[Dict[str, Any]] = None,
    response_validation_config: Optional[ResponseValidationConfig] = None
) -> BedrockResponse
```

**Parameters:**

- `messages`: List of message objects for the conversation
- `system`: System message objects (optional)
- `inference_config`: Inference parameters (optional, merges with defaults)
- `additional_model_request_fields`: Model-specific request parameters (optional)
- `additional_model_response_field_paths`: Additional response fields to return (optional)
- `guardrail_config`: Guardrail configuration (optional)
- `tool_config`: Tool use configuration (optional)
- `request_metadata`: Request metadata (optional)
- `prompt_variables`: Variables for prompt templates (optional)
- `response_validation_config`: Response validation configuration (optional)

**Returns:** `BedrockResponse` object with the conversation result

**Raises:**
- `RequestValidationError`: If request validation fails
- `RetryExhaustedError`: If all retry attempts fail
- `AuthenticationError`: If authentication fails

##### converse_stream()

```python
def converse_stream(
    self,
    messages: List[Dict[str, Any]],
    system: Optional[List[Dict[str, str]]] = None,
    inference_config: Optional[Dict[str, Any]] = None,
    additional_model_request_fields: Optional[Dict[str, Any]] = None,
    additional_model_response_field_paths: Optional[List[str]] = None,
    guardrail_config: Optional[Dict[str, Any]] = None,
    tool_config: Optional[Dict[str, Any]] = None,
    request_metadata: Optional[Dict[str, Any]] = None,
    prompt_variables: Optional[Dict[str, Any]] = None
) -> StreamingResponse
```

Streaming version of `converse()` that returns a `StreamingResponse` object for real-time response processing.

##### converse_with_request()

```python
def converse_with_request(
    self, 
    request: BedrockConverseRequest,
    response_validation_config: Optional[ResponseValidationConfig] = None
) -> BedrockResponse
```

Convenience method for using `BedrockConverseRequest` objects (useful for parallel processing).

#### Utility Methods

##### get_available_models()

```python
def get_available_models(self) -> List[str]
```

Returns the list of currently configured models.

##### get_available_regions()

```python
def get_available_regions(self) -> List[str]
```

Returns the list of currently configured regions.

##### get_model_access_info()

```python
def get_model_access_info(self, model_name: str, region: str) -> Optional[Dict[str, Any]]
```

Returns access information for a specific model in a region.

##### validate_configuration()

```python
def validate_configuration(self) -> Dict[str, Any]
```

Validates the current configuration and returns status information.

##### refresh_model_data()

```python
def refresh_model_data(self) -> None
```

Refreshes the unified model data from AWS sources.

## Configuration

### Authentication Configuration

```python
from src.bedrock.models.llm_manager_structures import AuthConfig, AuthenticationType

# AWS Profile
auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="my-profile"
)

# Environment Variables
auth_config = AuthConfig(
    auth_type=AuthenticationType.ENVIRONMENT
)

# Direct Credentials
auth_config = AuthConfig(
    auth_type=AuthenticationType.CREDENTIALS,
    access_key="your-access-key",
    secret_key="your-secret-key",
    session_token="your-session-token"  # Optional
)

# IAM Role
auth_config = AuthConfig(
    auth_type=AuthenticationType.IAM_ROLE,
    role_arn="arn:aws:iam::123456789012:role/BedrockRole"
)
```

### Retry Configuration

```python
from src.bedrock.models.llm_manager_structures import RetryConfig, RetryStrategy

retry_config = RetryConfig(
    max_attempts=5,              # Maximum retry attempts
    base_delay=1.0,              # Base delay in seconds
    max_delay=30.0,              # Maximum delay in seconds
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,  # Retry strategy
    retryable_exceptions=[       # Custom retryable exceptions
        "ThrottlingException",
        "InternalServerException"
    ]
)
```

### Inference Configuration

```python
# Default inference parameters applied to all requests
default_inference_config = {
    "maxTokens": 1000,
    "temperature": 0.7,
    "topP": 0.9,
    "stopSequences": ["###", "---"]
}

manager = LLMManager(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1"],
    default_inference_config=default_inference_config
)

# Override for specific requests
response = manager.converse(
    messages=[message],
    inference_config={
        "maxTokens": 2000,  # Override default
        "temperature": 0.1  # Override default
    }
)
```

## Error Handling

### Exception Hierarchy

```python
LLMManagerError (base)
├── ConfigurationError
├── RequestValidationError
├── AuthenticationError
└── RetryExhaustedError
```

### Error Handling Patterns

```python
from src.bedrock.exceptions.llm_manager_exceptions import (
    LLMManagerError, ConfigurationError, RequestValidationError,
    AuthenticationError, RetryExhaustedError
)

try:
    response = manager.converse(messages=[message])
    print(response.get_content())
    
except RequestValidationError as e:
    print(f"Request validation failed: {e}")
    print(f"Validation errors: {e.validation_errors}")
    
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Handle authentication issues
    
except RetryExhaustedError as e:
    print(f"All retry attempts failed: {e}")
    # Handle complete failure
    
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    # Handle configuration issues
    
except LLMManagerError as e:
    print(f"General LLM error: {e}")
    # Handle other LLM-related errors
```

### Graceful Degradation

```python
def robust_conversation(manager, message):
    """Example of robust conversation handling."""
    try:
        response = manager.converse(messages=[message])
        return response.get_content()
        
    except RetryExhaustedError as e:
        # Log the error but continue
        logger.error(f"LLM request failed: {e}")
        return "I'm sorry, I'm temporarily unavailable. Please try again later."
        
    except RequestValidationError as e:
        # Handle validation errors
        logger.warning(f"Request validation failed: {e}")
        return "I couldn't process your request. Please check your input and try again."
```

## Response Objects

### BedrockResponse

The primary response object containing comprehensive information about the LLM interaction.

```python
class BedrockResponse:
    success: bool
    response_data: Optional[Dict[str, Any]]
    model_used: Optional[str]
    region_used: Optional[str]
    access_method_used: Optional[str]
    attempts: List[RequestAttempt]
    total_duration_ms: float
    api_latency_ms: Optional[float]
    warnings: List[str]
    features_disabled: List[str]
```

#### Key Methods

```python
# Content extraction
content = response.get_content()                    # Main response text
usage = response.get_usage()                        # Token usage information
metrics = response.get_metrics()                    # Performance metrics

# Response metadata
stop_reason = response.get_stop_reason()            # Why the response stopped
additional_fields = response.get_additional_model_response_fields()

# Success/failure information
success = response.was_successful()                 # Whether request succeeded
warnings = response.get_warnings()                  # Any warnings
errors = response.get_all_errors()                  # All errors encountered

# Attempt information
attempt_count = response.get_attempt_count()        # Number of attempts made
successful_attempt = response.get_successful_attempt()  # Successful attempt details

# Validation information (if response validation was used)
had_validation_failures = response.had_validation_failures()
validation_errors = response.get_validation_errors()
validation_metrics = response.get_validation_metrics()

# Serialization
response_dict = response.to_dict()                  # Convert to dictionary
response_json = response.to_json(indent=2)          # Convert to JSON string
```

### StreamingResponse

For streaming responses, the `StreamingResponse` object provides methods to handle real-time content:

```python
streaming_response = manager.converse_stream(messages=[message])

# Get content as it arrives
for chunk in streaming_response:
    print(chunk, end="", flush=True)

# Get full content after streaming is complete
full_content = streaming_response.get_full_content()

# Get individual content parts
content_parts = streaming_response.get_content_parts()

# Handle streaming errors
stream_errors = streaming_response.get_stream_errors()
```

## Advanced Features

### Response Validation with Retry

```python
from src.bedrock.models.llm_manager_structures import ResponseValidationConfig

def validate_response_length(response):
    """Custom validation function."""
    content = response.get_content()
    return content and len(content) > 50

validation_config = ResponseValidationConfig(
    max_validation_attempts=3,
    validation_function=validate_response_length,
    validation_retry_delay=2.0
)

response = manager.converse(
    messages=[message],
    response_validation_config=validation_config
)

# Check if validation was successful
if response.had_validation_failures():
    print(f"Validation failed {response.get_validation_attempt_count()} times")
    print(f"Validation errors: {response.get_validation_errors()}")
```

### Tool Use Configuration

```python
# Define tools
tools = [
    {
        "toolSpec": {
            "name": "get_weather",
            "description": "Get current weather information",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    },
                    "required": ["location"]
                }
            }
        }
    }
]

tool_config = {
    "tools": tools,
    "toolChoice": {"auto": {}}
}

response = manager.converse(
    messages=[message],
    tool_config=tool_config
)
```

### Guardrail Configuration

```python
guardrail_config = {
    "guardrailIdentifier": "your-guardrail-id",
    "guardrailVersion": "1",
    "trace": "enabled"
}

response = manager.converse(
    messages=[message],
    guardrail_config=guardrail_config
)
```

### System Messages

```python
system_messages = [
    {
        "text": "You are a helpful assistant specializing in Python programming. "
                "Always provide code examples and explain your reasoning."
    }
]

response = manager.converse(
    messages=[message],
    system=system_messages
)
```

## Integration Examples

### Flask Web Application

```python
from flask import Flask, request, jsonify
from src.LLMManager import LLMManager
from src.bedrock.models.message_builder_factory import create_user_message

app = Flask(__name__)

# Initialize LLM Manager once
manager = LLMManager(
    models=["Claude 3.5 Sonnet", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"]
)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        # Create message
        message = create_user_message().add_text(user_message).build()
        
        # Get response
        response = manager.converse(messages=[message])
        
        return jsonify({
            'success': True,
            'response': response.get_content(),
            'model_used': response.model_used,
            'usage': response.get_usage()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
```

### Batch Processing

```python
def process_batch(manager, questions):
    """Process a batch of questions."""
    results = []
    
    for i, question in enumerate(questions):
        try:
            message = create_user_message().add_text(question).build()
            response = manager.converse(messages=[message])
            
            results.append({
                'index': i,
                'question': question,
                'answer': response.get_content(),
                'model_used': response.model_used,
                'tokens_used': response.get_usage()
            })
            
        except Exception as e:
            results.append({
                'index': i,
                'question': question,
                'error': str(e)
            })
    
    return results

# Usage
questions = [
    "What is machine learning?",
    "Explain neural networks",
    "How does backpropagation work?"
]

batch_results = process_batch(manager, questions)
```

### Conversation Memory

```python
class ConversationMemory:
    """Simple conversation memory implementation."""
    
    def __init__(self, manager, max_history=10):
        self.manager = manager
        self.messages = []
        self.max_history = max_history
    
    def add_user_message(self, text):
        """Add user message to conversation."""
        message = create_user_message().add_text(text).build()
        self.messages.append(message)
        self._trim_history()
    
    def add_assistant_message(self, text):
        """Add assistant message to conversation."""
        message = {
            "role": "assistant",
            "content": [{"text": text}]
        }
        self.messages.append(message)
        self._trim_history()
    
    def get_response(self, user_input):
        """Get response maintaining conversation context."""
        self.add_user_message(user_input)
        
        response = self.manager.converse(messages=self.messages)
        assistant_response = response.get_content()
        
        self.add_assistant_message(assistant_response)
        return assistant_response
    
    def _trim_history(self):
        """Keep only recent messages."""
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

# Usage
conversation = ConversationMemory(manager)
response1 = conversation.get_response("Hello, I'm learning Python")
response2 = conversation.get_response("Can you give me an example?")
```

## Performance Considerations

### Response Caching

```python
from functools import lru_cache
import hashlib

class CachedLLMManager:
    """LLM Manager with response caching."""
    
    def __init__(self, manager):
        self.manager = manager
        self.cache = {}
    
    def _get_cache_key(self, messages, **kwargs):
        """Generate cache key for request."""
        content = str(messages) + str(sorted(kwargs.items()))
        return hashlib.md5(content.encode()).hexdigest()
    
    def converse(self, messages, **kwargs):
        """Converse with caching."""
        cache_key = self._get_cache_key(messages, **kwargs)
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        response = self.manager.converse(messages=messages, **kwargs)
        self.cache[cache_key] = response
        return response

# Usage
cached_manager = CachedLLMManager(manager)
```

### Connection Pooling

```python
# LLMManager automatically handles connection pooling through boto3
# No additional configuration needed for basic connection pooling

# For advanced connection management:
from src.bedrock.models.llm_manager_structures import AuthConfig

auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="my-profile",
    # Connection pooling is handled automatically by boto3
)
```

### Memory Management

```python
# For long-running applications, consider periodic cleanup
import gc

def cleanup_resources():
    """Cleanup resources periodically."""
    gc.collect()

# Use with threading.Timer for periodic cleanup
import threading

def periodic_cleanup():
    cleanup_resources()
    timer = threading.Timer(300, periodic_cleanup)  # Every 5 minutes
    timer.start()

periodic_cleanup()
```

## Best Practices

### 1. Error Handling

```python
# ✅ Good: Specific error handling
try:
    response = manager.converse(messages=[message])
except RequestValidationError as e:
    # Handle validation errors specifically
    logger.warning(f"Request validation failed: {e}")
except RetryExhaustedError as e:
    # Handle retry exhaustion
    logger.error(f"All retries failed: {e}")

# ❌ Bad: Generic error handling
try:
    response = manager.converse(messages=[message])
except Exception as e:
    print(f"Error: {e}")
```

### 2. Configuration Management

```python
# ✅ Good: Environment-based configuration
import os

def create_manager():
    return LLMManager(
        models=os.getenv("LLM_MODELS", "Claude 3.5 Sonnet").split(","),
        regions=os.getenv("LLM_REGIONS", "us-east-1").split(","),
        timeout=int(os.getenv("LLM_TIMEOUT", "30"))
    )

# ❌ Bad: Hardcoded configuration
manager = LLMManager(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1"]
)
```

### 3. Resource Management

```python
# ✅ Good: Reuse manager instance
class ChatService:
    def __init__(self):
        self.manager = LLMManager(models=["Claude 3.5 Sonnet"], regions=["us-east-1"])
    
    def chat(self, message):
        return self.manager.converse(messages=[message])

# ❌ Bad: Create new manager for each request
def chat(message):
    manager = LLMManager(models=["Claude 3.5 Sonnet"], regions=["us-east-1"])
    return manager.converse(messages=[message])
```

### 4. Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# ✅ Good: Proper logging
try:
    response = manager.converse(messages=[message])
    logger.info(f"Successfully got response from {response.model_used}")
except Exception as e:
    logger.error(f"Failed to get response: {e}", exc_info=True)
```

### 5. Testing

```python
# ✅ Good: Testable code with dependency injection
def process_user_input(user_input, llm_manager=None):
    if llm_manager is None:
        llm_manager = LLMManager(models=["Claude 3.5 Sonnet"], regions=["us-east-1"])
    
    message = create_user_message().add_text(user_input).build()
    return llm_manager.converse(messages=[message])

# Test with mock
def test_process_user_input():
    mock_manager = Mock()
    mock_manager.converse.return_value = Mock(get_content=lambda: "test response")
    
    result = process_user_input("test input", mock_manager)
    assert result.get_content() == "test response"
```

---

This comprehensive documentation provides everything needed to effectively use the LLMManager class in production applications. For additional examples and advanced use cases, refer to the other documentation files and the notebooks directory.
