# LLMManager - Complete API Reference for Coding Assistants

## Overview

The LLMManager package provides a comprehensive interface for managing AWS Bedrock LLM interactions with support for multiple models, regions, authentication methods, retry logic, and parallel processing.

### Core Components

- **LLMManager**: Main class for single AWS Bedrock requests with retry logic
- **ParallelLLMManager**: Extended class for parallel processing of multiple requests
- **BedrockResponse**: Comprehensive response object with metadata and utilities
- **UnifiedModelManager**: Manages model availability and access information

## Main Classes

### LLMManager

Primary interface for single AWS Bedrock requests with automatic retry logic and region failover.

#### Constructor
```python
LLMManager(
    models: List[str],                                    # Required: List of model names/IDs
    regions: List[str],                                   # Required: List of AWS regions
    auth_config: Optional[AuthConfig] = None,             # Optional: Authentication configuration
    retry_config: Optional[RetryConfig] = None,           # Optional: Retry behavior configuration
    unified_model_manager: Optional[UnifiedModelManager] = None,  # Optional: Pre-configured model manager
    default_inference_config: Optional[Dict[str, Any]] = None,    # Optional: Default inference parameters
    timeout: int = 300                                    # Optional: Request timeout in seconds
)
```

#### Core Methods

**converse() - Primary method for conversation requests**
```python
def converse(
    self,
    messages: List[Dict[str, Any]],                       # Required: List of message objects
    system: Optional[List[Dict[str, str]]] = None,        # Optional: System message objects
    inference_config: Optional[Dict[str, Any]] = None,    # Optional: Inference parameters
    additional_model_request_fields: Optional[Dict[str, Any]] = None,  # Optional: Model-specific fields
    additional_model_response_field_paths: Optional[List[str]] = None, # Optional: Extra response fields
    guardrail_config: Optional[Dict[str, Any]] = None,    # Optional: Guardrail configuration
    tool_config: Optional[Dict[str, Any]] = None,         # Optional: Tool use configuration
    request_metadata: Optional[Dict[str, Any]] = None,    # Optional: Request metadata
    prompt_variables: Optional[Dict[str, Any]] = None,    # Optional: Prompt template variables
    response_validation_config: Optional[ResponseValidationConfig] = None  # Optional: Response validation
) -> BedrockResponse
```

**converse_stream() - Streaming conversation requests**
```python
def converse_stream(
    self,
    messages: List[Dict[str, Any]],                       # Same parameters as converse()
    # ... other parameters identical to converse()
) -> StreamingResponse
```

**Utility Methods**
```python
def get_available_models(self) -> List[str]              # Get configured models
def get_available_regions(self) -> List[str]             # Get configured regions
def get_model_access_info(self, model_name: str, region: str) -> Optional[Dict[str, Any]]  # Get model access info
def validate_configuration(self) -> Dict[str, Any]       # Validate current configuration
def refresh_model_data(self) -> None                     # Refresh model data from AWS
def get_retry_stats(self) -> Dict[str, Any]              # Get retry statistics
```

### ParallelLLMManager

Extended class for parallel processing of multiple requests across regions.

#### Constructor
```python
ParallelLLMManager(
    models: List[str],                                    # Required: List of model names/IDs
    regions: List[str],                                   # Required: List of AWS regions
    auth_config: Optional[AuthConfig] = None,             # Optional: Authentication configuration
    retry_config: Optional[RetryConfig] = None,           # Optional: Retry behavior configuration
    parallel_config: Optional[ParallelProcessingConfig] = None,  # Optional: Parallel processing config
    default_inference_config: Optional[Dict] = None,     # Optional: Default inference parameters
    timeout: int = 300                                    # Optional: Request timeout in seconds
)
```

#### Core Methods

**converse_parallel() - Primary method for parallel processing**
```python
def converse_parallel(
    self,
    requests: List[BedrockConverseRequest],               # Required: List of request objects
    target_regions_per_request: int = 2,                  # Optional: Target regions per request
    response_validation_config: Optional[ResponseValidationConfig] = None  # Optional: Response validation
) -> ParallelResponse
```

**Single Request Methods**
```python
def converse_with_request(self, request: BedrockConverseRequest) -> BedrockResponse  # Execute single request
def get_underlying_llm_manager(self) -> LLMManager       # Get underlying LLMManager instance
```

## Data Structures

### Message Structure

Messages follow the AWS Bedrock Converse API format:

```python
# Basic text message
message = {
    "role": "user",  # or "assistant"
    "content": [
        {"text": "Hello, how are you?"}
    ]
}

# Multimodal message with image
message = {
    "role": "user",
    "content": [
        {"text": "What's in this image?"},
        {
            "image": {
                "format": "jpeg",  # or "png", "gif", "webp"
                "source": {
                    "bytes": image_bytes  # or use s3Location
                }
            }
        }
    ]
}

# Message with document
message = {
    "role": "user",
    "content": [
        {"text": "Analyze this document"},
        {
            "document": {
                "name": "document.pdf",
                "format": "pdf",  # or "csv", "doc", "docx", "xls", "xlsx", "html", "txt", "md"
                "source": {
                    "bytes": document_bytes
                }
            }
        }
    ]
}

# Message with tool use
message = {
    "role": "assistant",
    "content": [
        {
            "toolUse": {
                "toolUseId": "unique-id",
                "name": "function_name",
                "input": {"param1": "value1"}
            }
        }
    ]
}

# Message with tool result
message = {
    "role": "user",
    "content": [
        {
            "toolResult": {
                "toolUseId": "unique-id",
                "content": [{"text": "Function result"}],
                "status": "success"  # or "error"
            }
        }
    ]
}
```

### BedrockConverseRequest

Request structure for parallel processing:

```python
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

request = BedrockConverseRequest(
    request_id="unique-request-id",                       # Optional: Auto-generated if not provided
    messages=[...],                                       # Required: List of message objects
    system=None,                                          # Optional: System messages
    inference_config=None,                                # Optional: Inference configuration
    additional_model_request_fields=None,                 # Optional: Model-specific fields
    additional_model_response_field_paths=None,           # Optional: Extra response fields
    guardrail_config=None,                                # Optional: Guardrail configuration
    tool_config=None,                                     # Optional: Tool configuration
    request_metadata=None,                                # Optional: Request metadata
    prompt_variables=None                                 # Optional: Prompt variables
)
```

### BedrockResponse

Comprehensive response object with utilities:

```python
# Access response content
response = manager.converse(messages=[...])

# Basic response information
success = response.success                                # Boolean: Request success status
content = response.get_content()                          # String: Main text content
usage = response.get_usage()                             # Dict: Token usage information
metrics = response.get_metrics()                         # Dict: Performance metrics
stop_reason = response.get_stop_reason()                 # String: Why generation stopped

# Execution details
model_used = response.model_used                         # String: Model ID that succeeded
region_used = response.region_used                       # String: Region that succeeded
attempts = response.attempts                             # List[RequestAttempt]: All attempts made
total_duration_ms = response.total_duration_ms           # Float: Total execution time
warnings = response.get_warnings()                       # List[str]: Warning messages

# Error handling
if not response.success:
    last_error = response.get_last_error()               # Exception: Last error encountered
    all_errors = response.get_all_errors()               # List[Exception]: All errors

# Response validation (if used)
had_validation_failures = response.had_validation_failures()  # Boolean: Any validation failures
validation_errors = response.get_validation_errors()     # List[Dict]: Validation error details

# Serialization
response_dict = response.to_dict()                       # Dict: Dictionary representation
response_json = response.to_json(indent=2)               # String: JSON representation
```

### ParallelResponse

Response object for parallel processing:

```python
parallel_response = parallel_manager.converse_parallel(requests=[...])

# Overall results
success = parallel_response.success                      # Boolean: Overall success
success_rate = parallel_response.get_success_rate()     # Float: Success rate (0.0-1.0)
total_duration_ms = parallel_response.total_duration_ms  # Float: Total execution time

# Individual responses
responses = parallel_response.request_responses          # Dict[str, BedrockResponse]: All responses
successful_responses = parallel_response.get_successful_responses()  # Dict[str, BedrockResponse]
failed_requests = parallel_response.failed_requests      # List[str]: Failed request IDs

# Execution statistics
stats = parallel_response.parallel_execution_stats
total_requests = stats.total_requests                    # Int: Total requests processed
successful_requests = stats.successful_requests          # Int: Successful requests
avg_duration = stats.average_request_duration_ms         # Float: Average request duration
region_distribution = stats.region_distribution          # Dict[str, int]: Requests per region
```

## Configuration Classes

### AuthConfig

Authentication configuration:

```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import AuthConfig, AuthenticationType

# AWS Profile authentication
auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="my-aws-profile"
)

# Direct credentials authentication
auth_config = AuthConfig(
    auth_type=AuthenticationType.CREDENTIALS,
    access_key_id="AKIA...",
    secret_access_key="...",
    session_token="..."  # Optional for temporary credentials
)

# IAM Role authentication
auth_config = AuthConfig(
    auth_type=AuthenticationType.IAM_ROLE,
    region="us-east-1"
)

# Auto-detection (default)
auth_config = AuthConfig(
    auth_type=AuthenticationType.AUTO
)
```

### RetryConfig

Retry behavior configuration:

```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig, RetryStrategy

retry_config = RetryConfig(
    max_retries=3,                                       # Maximum retry attempts
    retry_delay=1.0,                                     # Initial delay between retries (seconds)
    backoff_multiplier=2.0,                              # Exponential backoff multiplier
    max_retry_delay=60.0,                                # Maximum delay between retries
    retry_strategy=RetryStrategy.REGION_FIRST,           # or RetryStrategy.MODEL_FIRST
    enable_feature_fallback=True,                        # Disable features on compatibility errors
    retryable_errors=()                                  # Additional error types to retry
)
```

### ParallelProcessingConfig

Parallel processing configuration:

```python
from bestehorn_llmmanager.bedrock.models.parallel_structures import (
    ParallelProcessingConfig, FailureHandlingStrategy, LoadBalancingStrategy
)

parallel_config = ParallelProcessingConfig(
    max_concurrent_requests=10,                          # Maximum concurrent requests
    request_timeout_seconds=120,                         # Individual request timeout
    failure_handling_strategy=FailureHandlingStrategy.CONTINUE_ON_FAILURE,  # Failure handling
    failure_threshold=0.5,                               # Failure rate threshold (0.0-1.0)
    load_balancing_strategy=LoadBalancingStrategy.ROUND_ROBIN,  # Load balancing strategy
    enable_request_prioritization=False                  # Request prioritization
)

# Failure handling strategies:
# - CONTINUE_ON_FAILURE: Continue processing all requests regardless of failures
# - STOP_ON_FIRST_FAILURE: Stop processing on first failure
# - STOP_ON_THRESHOLD: Stop when failure rate exceeds threshold

# Load balancing strategies:
# - ROUND_ROBIN: Distribute requests evenly across regions
# - LEAST_LOADED: Send requests to least loaded regions
# - RANDOM: Random distribution
```

### ResponseValidationConfig

Response validation configuration:

```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import ResponseValidationConfig, ValidationResult

def my_validation_function(response: BedrockResponse) -> ValidationResult:
    """Custom validation function example."""
    content = response.get_content()
    if content and "error" in content.lower():
        return ValidationResult(
            success=False,
            error_message="Response contains error keyword",
            error_details={"content": content}
        )
    return ValidationResult(success=True)

validation_config = ResponseValidationConfig(
    response_validation_function=my_validation_function,
    response_validation_retries=3,                       # Number of validation retries
    response_validation_delay=0.0                        # Delay between validation retries
)
```

### Inference Configuration

Inference parameters for model behavior:

```python
inference_config = {
    "maxTokens": 4096,                                   # Maximum tokens to generate
    "temperature": 0.7,                                  # Randomness (0.0-1.0)
    "topP": 0.9,                                         # Nucleus sampling (0.0-1.0)
    "stopSequences": ["Human:", "Assistant:"]            # Stop sequences
}
```

## Common Usage Patterns

### Basic Single Request

```python
from bestehorn_llmmanager import LLMManager

# Initialize manager
manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2"]
)

# Send request
messages = [
    {"role": "user", "content": [{"text": "Hello, how are you?"}]}
]

response = manager.converse(messages=messages)

if response.success:
    print(f"Response: {response.get_content()}")
    print(f"Model used: {response.model_used}")
    print(f"Region used: {response.region_used}")
    print(f"Duration: {response.total_duration_ms}ms")
else:
    print(f"Request failed: {response.get_last_error()}")
```

### Parallel Processing

```python
from bestehorn_llmmanager import ParallelLLMManager
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

# Initialize parallel manager
parallel_manager = ParallelLLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2", "eu-west-1"]
)

# Create multiple requests
requests = [
    BedrockConverseRequest(
        request_id="req-1",
        messages=[{"role": "user", "content": [{"text": "What is AI?"}]}]
    ),
    BedrockConverseRequest(
        request_id="req-2", 
        messages=[{"role": "user", "content": [{"text": "Explain machine learning"}]}]
    )
]

# Execute in parallel
parallel_response = parallel_manager.converse_parallel(
    requests=requests,
    target_regions_per_request=2
)

print(f"Success rate: {parallel_response.get_success_rate():.1%}")
print(f"Total duration: {parallel_response.total_duration_ms}ms")

# Access individual responses
for request_id, response in parallel_response.request_responses.items():
    if response.success:
        print(f"Request {request_id}: {response.get_content()}")
    else:
        print(f"Request {request_id} failed: {response.get_last_error()}")
```

### Multimodal Request with Image

```python
import base64

# Load image
with open("image.jpg", "rb") as f:
    image_bytes = f.read()

# Create multimodal message
messages = [
    {
        "role": "user",
        "content": [
            {"text": "What's in this image?"},
            {
                "image": {
                    "format": "jpeg",
                    "source": {"bytes": image_bytes}
                }
            }
        ]
    }
]

response = manager.converse(messages=messages)
```

### Tool Use Configuration

```python
# Define tools
tool_config = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_weather",
                "description": "Get weather information for a location",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The location to get weather for"
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        }
    ]
}

# Send request with tool configuration
messages = [
    {"role": "user", "content": [{"text": "What's the weather in New York?"}]}
]

response = manager.converse(
    messages=messages,
    tool_config=tool_config
)

# Handle tool use in response
if response.success:
    content = response.response_data.get("output", {}).get("message", {}).get("content", [])
    for block in content:
        if "toolUse" in block:
            tool_use = block["toolUse"]
            print(f"Tool called: {tool_use['name']}")
            print(f"Input: {tool_use['input']}")
```

### Authentication with AWS Profile

```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import AuthConfig, AuthenticationType

auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="my-bedrock-profile"
)

manager = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"],
    auth_config=auth_config
)
```

### Custom Retry Configuration

```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig, RetryStrategy

retry_config = RetryConfig(
    max_retries=5,
    retry_delay=2.0,
    backoff_multiplier=1.5,
    retry_strategy=RetryStrategy.MODEL_FIRST,
    enable_feature_fallback=True
)

manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2"],
    retry_config=retry_config
)
```

### Response Validation

```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import ResponseValidationConfig, ValidationResult

def validate_response(response: BedrockResponse) -> ValidationResult:
    """Validate that response doesn't contain harmful content."""
    content = response.get_content()
    if not content:
        return ValidationResult(
            success=False,
            error_message="Empty response content"
        )
    
    harmful_keywords = ["violence", "illegal", "harmful"]
    if any(keyword in content.lower() for keyword in harmful_keywords):
        return ValidationResult(
            success=False,
            error_message="Response contains potentially harmful content",
            error_details={"content": content}
        )
    
    return ValidationResult(success=True)

validation_config = ResponseValidationConfig(
    response_validation_function=validate_response,
    response_validation_retries=3
)

response = manager.converse(
    messages=messages,
    response_validation_config=validation_config
)
```

## Error Handling

### Exception Hierarchy

```python
from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    LLMManagerError,           # Base exception
    ConfigurationError,        # Configuration problems
    RequestValidationError,    # Request validation failures
    AuthenticationError,       # Authentication failures
    RetryExhaustedError       # All retries failed
)

from bestehorn_llmmanager.bedrock.exceptions.parallel_exceptions import (
    ParallelProcessingError,   # Base parallel processing exception
    ParallelExecutionError,    # Execution failures
    ParallelConfigurationError # Parallel configuration problems
)
```

### Error Handling Pattern

```python
try:
    response = manager.converse(messages=messages)
    if response.success:
        print(response.get_content())
    else:
        print(f"Request failed: {response.get_last_error()}")
        
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    
except RequestValidationError as e:
    print(f"Request validation failed: {e}")
    print(f"Validation errors: {e.validation_errors}")
    
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    
except RetryExhaustedError as e:
    print(f"All retries failed: {e}")
    
except LLMManagerError as e:
    print(f"LLM Manager error: {e}")
```

## Model and Region Management

### Model Names

Common model names supported:
- `"Claude 3 Haiku"` - Fast, efficient model
- `"Claude 3 Sonnet"` - Balanced performance
- `"Claude 3 Opus"` - Most capable model
- `"Claude 3.5 Sonnet"` - Enhanced version
- `"Nova Micro"` - Amazon's multimodal model
- `"Nova Lite"` - Amazon's lightweight model
- `"Nova Pro"` - Amazon's professional model

### AWS Regions

Common regions with Bedrock support:
- `"us-east-1"` - US East (N. Virginia)
- `"us-west-2"` - US West (Oregon)
- `"eu-west-1"` - Europe (Ireland)
- `"eu-central-1"` - Europe (Frankfurt)
- `"ap-southeast-1"` - Asia Pacific (Singapore)
- `"ap-northeast-1"` - Asia Pacific (Tokyo)

### Model Access Information

```python
# Check model availability
access_info = manager.get_model_access_info("Claude 3 Haiku", "us-east-1")
if access_info:
    print(f"Model ID: {access_info['model_id']}")
    print(f"Access method: {access_info['access_method']}")
    print(f"Region: {access_info['region']}")
else:
    print("Model not available in this region")

# Validate configuration
validation_result = manager.validate_configuration()
if validation_result["valid"]:
    print(f"Configuration valid with {validation_result['model_region_combinations']} model/region combinations")
else:
    print(f"Configuration errors: {validation_result['errors']}")
```

## Best Practices

### 1. Model Selection
- Use multiple models for redundancy
- Order models by preference (first = preferred)
- Consider cost vs. capability trade-offs

### 2. Region Selection
- Use multiple regions for reliability
- Consider latency and data locality
- Include at least 2-3 regions for fault tolerance

### 3. Error Handling
- Always check `response.success` before accessing content
- Handle specific exception types appropriately
- Log errors and warnings for debugging

### 4. Performance Optimization
- Use parallel processing for multiple requests
- Configure appropriate timeouts
- Monitor retry statistics and adjust configuration

### 5. Security
- Use IAM roles or profiles instead of hardcoded credentials
- Implement response validation for sensitive applications
- Consider guardrails for content filtering

### 6. Resource Management
- Refresh model data periodically
- Monitor token usage and costs
- Use appropriate inference configurations

## Constants and Enums

### Important Constants

```python
# From llm_manager_constants.py
from bestehorn_llmmanager.bedrock.models.llm_manager_constants import (
    ConverseAPIFields,        # API field names
    LLMManagerConfig,         # Configuration defaults
    ContentLimits,            # Content size limits
    RetryableErrorTypes       # Error type classifications
)

# Content limits
MAX_IMAGES_PER_REQUEST = 20
MAX_DOCUMENTS_PER_REQUEST = 5
MAX_VIDEOS_PER_REQUEST = 1
MAX_IMAGE_SIZE_BYTES = 3_750_000  # 3.75 MB
MAX_DOCUMENT_SIZE_BYTES = 4_500_000  # 4.5 MB

# Default configuration values
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_TIMEOUT = 300
```

### Enums

```python
# Authentication types
class AuthenticationType(Enum):
    PROFILE = "profile"
    CREDENTIALS = "credentials"
    IAM_ROLE = "iam_role"
    AUTO = "auto"

# Retry strategies
class RetryStrategy(Enum):
    REGION_FIRST = "region_first"
    MODEL_FIRST = "model_first"

# Failure handling strategies
class FailureHandlingStrategy(Enum):
    CONTINUE_ON_FAILURE = "continue_on_failure"
    STOP_ON_FIRST_FAILURE = "stop_on_first_failure"
    STOP_ON_THRESHOLD = "stop_on_threshold"

# Load balancing strategies
class LoadBalancingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
```

This documentation provides comprehensive coverage of the LLMManager package for coding assistants. It includes all necessary classes, methods, data structures, configuration options, and usage patterns needed to effectively use the library.
