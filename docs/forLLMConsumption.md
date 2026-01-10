# LLMManager - Complete API Reference for Coding Assistants

## Overview

The LLMManager package provides a comprehensive interface for managing AWS Bedrock LLM interactions with support for multiple models, regions, authentication methods, retry logic, parallel processing, and fluent message building with automatic format detection.

### Core Components

- **LLMManager**: Main class for single AWS Bedrock requests with retry logic
- **ParallelLLMManager**: Extended class for parallel processing of multiple requests
- **MessageBuilder**: Fluent interface for building multi-modal messages with automatic format detection
- **BedrockResponse**: Comprehensive response object with metadata and utilities
- **BedrockModelCatalog**: Unified model management system (replaces deprecated UnifiedModelManager)

## MessageBuilder - Fluent Message Construction

The MessageBuilder provides a fluent interface for constructing multi-modal messages with automatic format detection, validation, and AWS Bedrock Converse API compatibility.

### Core MessageBuilder Classes

#### ConverseMessageBuilder

Main class for building individual messages with fluent method chaining.

```python
from bestehorn_llmmanager import MessageBuilder, RolesEnum

# Create a message builder
builder = MessageBuilder(role=RolesEnum.USER)

# Or use the alias
from bestehorn_llmmanager.message_builder import ConverseMessageBuilder
builder = ConverseMessageBuilder(role=RolesEnum.USER)
```

#### Factory Functions

Convenient factory functions for creating message builders:

```python
from bestehorn_llmmanager import create_message, create_user_message, create_assistant_message, RolesEnum

# Main factory function
builder = create_message(role=RolesEnum.USER)

# Convenience factories
user_builder = create_user_message()
assistant_builder = create_assistant_message()
```

### MessageBuilder Methods

#### Text Content

```python
def add_text(self, text: str) -> 'ConverseMessageBuilder'
```

Add text content to the message. Text is automatically stripped of surrounding whitespace.

```python
# Basic text message
message = create_user_message()\
    .add_text("Hello, how are you?")\
    .build()

# Multiple text blocks
message = create_user_message()\
    .add_text("First paragraph")\
    .add_text("Second paragraph")\
    .build()
```

#### Image Content

**add_image_bytes() - Add image from raw bytes**
```python
def add_image_bytes(
    self,
    bytes: bytes,
    format: Optional[ImageFormatEnum] = None,
    filename: Optional[str] = None
) -> 'ConverseMessageBuilder'
```

**add_local_image() - Add image from local file**
```python
def add_local_image(
    self,
    path_to_local_file: str,
    format: Optional[ImageFormatEnum] = None,
    max_size_mb: float = 3.75
) -> 'ConverseMessageBuilder'
```

```python
from bestehorn_llmmanager import ImageFormatEnum

# Auto-detect format from bytes and filename
with open("photo.jpg", "rb") as f:
    image_data = f.read()

message = create_user_message()\
    .add_text("What's in this image?")\
    .add_image_bytes(bytes=image_data, filename="photo.jpg")\
    .build()

# Explicit format specification
message = create_user_message()\
    .add_text("Analyze this image")\
    .add_image_bytes(bytes=image_data, format=ImageFormatEnum.JPEG)\
    .build()

# Add from local file (automatic format detection)
message = create_user_message()\
    .add_text("What do you see here?")\
    .add_local_image("path/to/image.png")\
    .build()
```

#### Document Content

**add_document_bytes() - Add document from raw bytes**
```python
def add_document_bytes(
    self,
    bytes: bytes,
    format: Optional[DocumentFormatEnum] = None,
    filename: Optional[str] = None,
    name: Optional[str] = None
) -> 'ConverseMessageBuilder'
```

**add_local_document() - Add document from local file**
```python
def add_local_document(
    self,
    path_to_local_file: str,
    format: Optional[DocumentFormatEnum] = None,
    name: Optional[str] = None,
    max_size_mb: float = 4.5
) -> 'ConverseMessageBuilder'
```

```python
from bestehorn_llmmanager import DocumentFormatEnum

# Auto-detect format from bytes and filename
with open("report.pdf", "rb") as f:
    pdf_data = f.read()

message = create_user_message()\
    .add_text("Please summarize this report")\
    .add_document_bytes(bytes=pdf_data, filename="report.pdf", name="Monthly Report")\
    .build()

# Explicit format and custom name
message = create_user_message()\
    .add_text("Analyze this data")\
    .add_document_bytes(bytes=csv_data, format=DocumentFormatEnum.CSV, name="Sales Data")\
    .build()

# Add from local file
message = create_user_message()\
    .add_text("Review this document")\
    .add_local_document("path/to/document.docx", name="Project Proposal")\
    .build()
```

#### Video Content

**add_video_bytes() - Add video from raw bytes**
```python
def add_video_bytes(
    self,
    bytes: bytes,
    format: Optional[VideoFormatEnum] = None,
    filename: Optional[str] = None
) -> 'ConverseMessageBuilder'
```

**add_local_video() - Add video from local file**
```python
def add_local_video(
    self,
    path_to_local_file: str,
    format: Optional[VideoFormatEnum] = None,
    max_size_mb: float = 100.0
) -> 'ConverseMessageBuilder'
```

```python
from bestehorn_llmmanager import VideoFormatEnum

# Auto-detect format from bytes and filename
with open("demo.mp4", "rb") as f:
    video_data = f.read()

message = create_user_message()\
    .add_text("What happens in this video?")\
    .add_video_bytes(bytes=video_data, filename="demo.mp4")\
    .build()

# Add from local file with explicit format
message = create_user_message()\
    .add_text("Analyze this video content")\
    .add_local_video("path/to/video.mov", format=VideoFormatEnum.MOV)\
    .build()
```

#### Building Messages

```python
def build(self) -> Dict[str, Any]
```

Build and return the complete message dictionary compatible with LLMManager.converse().

```python
# Build a complete multi-modal message
message = create_user_message()\
    .add_text("Please analyze these files:")\
    .add_local_image("chart.png")\
    .add_local_document("data.xlsx")\
    .add_text("What insights can you provide?")\
    .build()

# Use with LLMManager
response = manager.converse(messages=[message])
```

### MessageBuilder Enums

#### RolesEnum

```python
from bestehorn_llmmanager import RolesEnum

class RolesEnum(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
```

#### ImageFormatEnum

```python
from bestehorn_llmmanager import ImageFormatEnum

class ImageFormatEnum(str, Enum):
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
```

#### DocumentFormatEnum

```python
from bestehorn_llmmanager import DocumentFormatEnum

class DocumentFormatEnum(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    DOC = "doc"
    DOCX = "docx"
    XLS = "xls"
    XLSX = "xlsx"
    HTML = "html"
    TXT = "txt"
    MD = "md"
```

#### VideoFormatEnum

```python
from bestehorn_llmmanager import VideoFormatEnum

class VideoFormatEnum(str, Enum):
    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"
    WEBM = "webm"
    MKV = "mkv"
```

### MessageBuilder Properties and Utilities

#### Properties

```python
# Get the role of the message
role = builder.role  # Returns RolesEnum

# Get current content block count
count = builder.content_block_count  # Returns int

# String representations
str_repr = str(builder)  # User-friendly string
repr_str = repr(builder)  # Detailed representation
```

#### Validation and Limits

The MessageBuilder automatically validates content and enforces limits:

- **Content block limit**: Maximum number of content blocks per message
- **Size limits**: 
  - Images: 3.75 MB default (configurable)
  - Documents: 4.5 MB default (configurable) 
  - Videos: 100 MB default (configurable)
- **Format validation**: Only supported formats accepted
- **Content validation**: Empty content rejected

### Automatic Format Detection

The MessageBuilder includes sophisticated file type detection:

```python
# Detection from filename extension
message = create_user_message()\
    .add_local_image("photo.jpg")  # Detects JPEG from extension
    
# Detection from content (magic bytes)
message = create_user_message()\
    .add_image_bytes(bytes=image_data)  # Detects format from content
    
# Combined detection (most reliable)
message = create_user_message()\
    .add_image_bytes(bytes=image_data, filename="photo.jpg")  # Uses both methods
```

#### Detection Methods

- **Extension-based**: Uses file extension for format detection
- **Content-based**: Analyzes file headers/magic bytes
- **Combined**: Uses both methods for highest confidence
- **Manual**: Explicitly specify format to skip detection

### MessageBuilder Usage Patterns

#### Simple Text Message

```python
from bestehorn_llmmanager import create_user_message

message = create_user_message()\
    .add_text("What is artificial intelligence?")\
    .build()

response = manager.converse(messages=[message])
```

#### Multi-Modal Message

```python
# Complex multi-modal message with automatic format detection
message = create_user_message()\
    .add_text("Please analyze this data visualization and the underlying data:")\
    .add_local_image("charts/sales_chart.png")\
    .add_local_document("data/sales_data.xlsx")\
    .add_text("What trends do you notice and what recommendations do you have?")\
    .build()

response = manager.converse(messages=[message])
```

#### Conversation with Assistant Response

```python
from bestehorn_llmmanager import create_assistant_message

# User message
user_message = create_user_message()\
    .add_text("What's in this image?")\
    .add_local_image("photo.jpg")\
    .build()

# Simulate assistant response (or get from actual response)
assistant_message = create_assistant_message()\
    .add_text("I can see a beautiful sunset over mountains with vibrant orange and pink colors in the sky.")\
    .build()

# Continue conversation
follow_up = create_user_message()\
    .add_text("What time of day do you think this was taken?")\
    .build()

messages = [user_message, assistant_message, follow_up]
response = manager.converse(messages=messages)
```

#### Batch Message Creation

```python
# Create multiple messages efficiently
image_files = ["image1.jpg", "image2.png", "image3.gif"]

messages = []
for i, image_file in enumerate(image_files):
    message = create_user_message()\
        .add_text(f"Analyze image {i+1}:")\
        .add_local_image(image_file)\
        .build()
    messages.append(message)

# Process with parallel manager
from bestehorn_llmmanager import ParallelLLMManager
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

parallel_manager = ParallelLLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])

requests = [
    BedrockConverseRequest(request_id=f"img-{i}", messages=[msg])
    for i, msg in enumerate(messages)
]

parallel_response = parallel_manager.converse_parallel(requests=requests)
```

#### Error Handling with MessageBuilder

```python
from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import RequestValidationError

try:
    message = create_user_message()\
        .add_text("Analyze this large image")\
        .add_local_image("huge_image.jpg", max_size_mb=10.0)\
        .build()
        
except FileNotFoundError as e:
    print(f"Image file not found: {e}")
    
except RequestValidationError as e:
    print(f"Validation error: {e}")
    
except Exception as e:
    print(f"Unexpected error: {e}")
```

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
    cache_config: Optional[CacheConfig] = None,           # Optional: Prompt caching configuration
    unified_model_manager: Optional[UnifiedModelManager] = None,  # Optional: Pre-configured model manager
    force_download: bool = False,                         # Optional: Force download fresh model data
    strict_cache_mode: bool = False,                      # Optional: Fail on stale cache (default: permissive)
    ignore_cache_age: bool = False,                       # Optional: Bypass cache age validation
    default_inference_config: Optional[Dict[str, Any]] = None,    # Optional: Default inference parameters
    timeout: int = 300,                                   # Optional: Request timeout in seconds
    log_level: Union[int, str] = logging.WARNING         # Optional: Logging level (default: WARNING)
)
```

**Model Profile Cache Parameters:**
- `force_download`: If True, always download fresh model profile data, bypassing cache
- `strict_cache_mode`: If True, fail when expired cache cannot be refreshed. If False (default), use stale cache with warning
- `ignore_cache_age`: If True, bypass cache age validation entirely. If False (default), respect max_cache_age_hours

**Note**: `cache_config` is for Bedrock prompt caching, while `strict_cache_mode` and `ignore_cache_age` control model profile data caching.

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
    timeout: int = 300,                                   # Optional: Request timeout in seconds
    log_level: Union[int, str] = logging.WARNING         # Optional: Logging level (default: WARNING)
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

**retry_failed_requests() - Retry failed requests from previous execution**
```python
def retry_failed_requests(
    self,
    previous_response: ParallelResponse,                  # Required: Previous ParallelResponse with failures
    filter_func: Optional[Callable[[str, BedrockResponse], bool]] = None,  # Optional: Filter function
    target_regions_per_request: Optional[int] = None,     # Optional: Target regions for retry
    response_validation_config: Optional[ResponseValidationConfig] = None  # Optional: Response validation
) -> ParallelResponse
```

The `retry_failed_requests()` method enables selective retry of failed requests from a previous parallel execution. Key features:

- **Selective retry**: Optional filter function to choose which failures to retry
- **Automatic merging**: Combines retry results with previous successful results
- **Fresh attempts**: Resets retry count and failure history for clean retry
- **Flexible filtering**: Filter by error type, timeout, or custom criteria

**Single Request Methods**
```python
def converse_with_request(self, request: BedrockConverseRequest) -> BedrockResponse  # Execute single request
def get_underlying_llm_manager(self) -> LLMManager       # Get underlying LLMManager instance
```

## Data Structures

### Message Structure

Messages follow the AWS Bedrock Converse API format. The MessageBuilder automatically creates these structures:

```python
# Basic text message (created by MessageBuilder)
message = {
    "role": "user",  # or "assistant"
    "content": [
        {"text": "Hello, how are you?"}
    ]
}

# Multimodal message with image (created by MessageBuilder)
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

# Message with document (created by MessageBuilder)
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

### Basic Single Request with MessageBuilder

```python
from bestehorn_llmmanager import LLMManager, create_user_message
import logging

# Initialize manager with default WARNING log level (minimal output)
manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2"]
)

# Or initialize with custom log level
manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2"],
    log_level=logging.INFO  # More detailed logging
)

# Log levels can be set using:
# - logging constants: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL
# - strings: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" 
# - integers: 10 (DEBUG), 20 (INFO), 30 (WARNING), 40 (ERROR), 50 (CRITICAL)

# Create message using MessageBuilder
message = create_user_message()\
    .add_text("Hello, how are you?")\
    .build()

response = manager.converse(messages=[message])

if response.success:
    print(f"Response: {response.get_content()}")
    print(f"Model used: {response.model_used}")
    print(f"Region used: {response.region_used}")
    print(f"Duration: {response.total_duration_ms}ms")
else:
    print(f"Request failed: {response.get_last_error()}")
```

### Multi-Modal Request with MessageBuilder

```python
from bestehorn_llmmanager import create_user_message

# Create complex multi-modal message
message = create_user_message()\
    .add_text("Please analyze this image and document:")\
    .add_local_image("chart.png")\
    .add_local_document("data.pdf")\
    .add_text("What insights can you provide?")\
    .build()

response = manager.converse(messages=[message])
```

### Parallel Processing with MessageBuilder

```python
from bestehorn_llmmanager import ParallelLLMManager, create_user_message
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

# Initialize parallel manager
parallel_manager = ParallelLLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2", "eu-west-1"]
)

# Create messages using MessageBuilder
message1 = create_user_message().add_text("What is AI?").build()
message2 = create_user_message().add_text("Explain machine learning").build()

# Create requests
requests = [
    BedrockConverseRequest(request_id="req-1", messages=[message1]),
    BedrockConverseRequest(request_id="req-2", messages=[message2])
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

### Parallel Processing with Automatic Retry

```python
from bestehorn_llmmanager import ParallelLLMManager, create_user_message
from bestehorn_llmmanager.bedrock.models.parallel_structures import (
    BedrockConverseRequest, ParallelProcessingConfig
)
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig

# Configure automatic retry behavior
retry_config = RetryConfig(
    max_retries=3,
    retry_delay=1.0,
    backoff_multiplier=2.0
)

# Configure parallel processing with automatic retry
parallel_config = ParallelProcessingConfig(
    max_concurrent_requests=10,
    enable_automatic_retry=True,  # Enable automatic retry
    max_retries_per_request=3      # Max retries per request
)

# Initialize manager with retry configuration
parallel_manager = ParallelLLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2", "eu-west-1"],
    retry_config=retry_config,
    parallel_config=parallel_config
)

# Create and execute requests
# Failed requests will automatically retry with exponential backoff
parallel_response = parallel_manager.converse_parallel(requests=requests)

# Check results after automatic retry
print(f"Final success rate: {parallel_response.get_success_rate():.1%}")
print(f"Successful: {len(parallel_response.successful_request_ids)}")
print(f"Failed: {len(parallel_response.failed_request_ids)}")
print(f"Timed out: {len(parallel_response.timed_out_request_ids)}")
```

### Manual Retry of Failed Requests

```python
# Execute initial parallel request
initial_response = parallel_manager.converse_parallel(requests=requests)

# Check if any requests failed
if initial_response.failed_request_ids or initial_response.timed_out_request_ids:
    print(f"Initial execution: {len(initial_response.failed_request_ids)} failed")
    
    # Retry all failed requests
    retry_response = parallel_manager.retry_failed_requests(
        previous_response=initial_response
    )
    
    print(f"After retry: {retry_response.get_success_rate():.1%} success rate")
    print(f"Total duration: {retry_response.total_duration_ms}ms")
```

### Selective Retry with Filter Function

```python
from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse

# Define filter function to retry only throttled requests
def retry_throttled_only(request_id: str, response: BedrockResponse) -> bool:
    """Retry only requests that were throttled."""
    warnings = response.get_warnings()
    return any("throttl" in w.lower() for w in warnings)

# Execute initial request
initial_response = parallel_manager.converse_parallel(requests=requests)

# Retry only throttled requests
retry_response = parallel_manager.retry_failed_requests(
    previous_response=initial_response,
    filter_func=retry_throttled_only
)

# Define filter function to retry only timeouts
def retry_timeouts_only(request_id: str, response: BedrockResponse) -> bool:
    """Retry only requests that timed out."""
    warnings = response.get_warnings()
    return any("timed out" in w.lower() for w in warnings)

# Retry only timed out requests
retry_response = parallel_manager.retry_failed_requests(
    previous_response=initial_response,
    filter_func=retry_timeouts_only
)

# Complex filter: retry based on request ID pattern
def retry_critical_requests(request_id: str, response: BedrockResponse) -> bool:
    """Retry only critical requests (based on ID pattern)."""
    return request_id.startswith("critical-")

retry_response = parallel_manager.retry_failed_requests(
    previous_response=initial_response,
    filter_func=retry_critical_requests
)
```

### Multi-Stage Retry Strategy

```python
# Stage 1: Initial execution
print("Stage 1: Initial execution")
response = parallel_manager.converse_parallel(requests=requests)
print(f"Success rate: {response.get_success_rate():.1%}")

# Stage 2: Retry timeouts with more regions
if response.timed_out_request_ids:
    print("\nStage 2: Retrying timeouts with more regions")
    
    def retry_timeouts(req_id: str, resp: BedrockResponse) -> bool:
        return any("timed out" in w.lower() for w in resp.get_warnings())
    
    response = parallel_manager.retry_failed_requests(
        previous_response=response,
        filter_func=retry_timeouts,
        target_regions_per_request=3  # Use more regions for retry
    )
    print(f"Success rate: {response.get_success_rate():.1%}")

# Stage 3: Retry throttled requests with delay
if response.failed_request_ids:
    print("\nStage 3: Retrying throttled requests")
    import time
    time.sleep(2)  # Wait before retrying throttled requests
    
    def retry_throttled(req_id: str, resp: BedrockResponse) -> bool:
        return any("throttl" in w.lower() for w in resp.get_warnings())
    
    response = parallel_manager.retry_failed_requests(
        previous_response=response,
        filter_func=retry_throttled
    )
    print(f"Final success rate: {response.get_success_rate():.1%}")

# Final results
print(f"\nFinal Results:")
print(f"  Successful: {len(response.successful_request_ids)}")
print(f"  Failed: {len(response.failed_request_ids)}")
print(f"  Total duration: {response.total_duration_ms}ms")
```

### Accessing Retry History

```python
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

# After execution, check retry history for each request
for request_id, request in response.original_requests.items():
    if request.failure_history:
        print(f"\nRequest {request_id} retry history:")
        print(f"  Total retry attempts: {request.retry_count}")
        
        for i, failure in enumerate(request.failure_history, 1):
            print(f"  Attempt {failure.attempt_number}:")
            print(f"    Timestamp: {failure.timestamp}")
            print(f"    Error type: {failure.exception_type}")
            print(f"    Error message: {failure.error_message}")
            if failure.region:
                print(f"    Failed region: {failure.region}")
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

# Create message with MessageBuilder
message = create_user_message()\
    .add_text("What's the weather in New York?")\
    .build()

response = manager.converse(
    messages=[message],
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

message = create_user_message().add_text("Tell me about safety").build()
response = manager.converse(
    messages=[message],
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
    message = create_user_message().add_text("Hello").build()
    response = manager.converse(messages=[message])
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

## CRIS (Cross-Region Inference Service) Management

### Version 0.3.0 Enhancements

#### AWS Bedrock API-Based CRIS Fetching

Starting in v0.3.0, the system uses AWS Bedrock API for CRIS data retrieval instead of HTML parsing:

**New Components:**
- **BedrockRegionDiscovery**: Dynamic discovery of Bedrock-enabled regions using `boto3.Session().get_available_regions('bedrock')`
- **CRISAPIFetcher**: Parallel API calls across regions using ThreadPoolExecutor
- **AuthManager.get_bedrock_control_client()**: Creates Bedrock control plane clients for API operations

**Benefits:**
- More reliable than HTML parsing (no breakage when AWS changes documentation)
- Faster through parallel execution (10-20 regions simultaneously)
- Future-proof with automatic region discovery
- Automatic fallback to HTML parsing if API fails

**Usage:**
```python
from bestehorn_llmmanager.bedrock import CRISManager

# Default: Use AWS Bedrock API (recommended)
manager = CRISManager()
catalog = manager.refresh_cris_data()
print(f"Found {catalog.model_count} CRIS models")

# Explicit API usage
manager = CRISManager(use_api=True)
catalog = manager.refresh_cris_data()

# Force HTML fallback (legacy)
manager = CRISManager(use_api=False)
catalog = manager.refresh_cris_data()
```

**Region Caching:**
- Bedrock-enabled regions are cached for 24 hours in `docs/bedrock_regions.json`
- Cache reduces API calls and improves performance
- Use `force_refresh=True` to bypass cache

**Required IAM Permissions:**
```json
{
  "Effect": "Allow",
  "Action": ["bedrock:ListInferenceProfiles"],
  "Resource": "*"
}
```

#### CRIS-Only Model Detection

v0.3.0 includes automatic detection of models that only support CRIS access:

**Known CRIS-Only Models (Pattern-Based Detection):**
- Claude Haiku 4.5 (`anthropic.claude-haiku-4-5-*`)
- Claude Sonnet 4.5 (`anthropic.claude-sonnet-4-5-*`)
- Claude Opus 4.5 (`anthropic.claude-opus-4-5-*`)

These models are incorrectly listed in AWS documentation without CRIS markers (`*`), but actually require inference profiles for all access. The system now automatically detects these patterns and forces CRIS-only access.

**What This Fixes:**
```python
# BEFORE v0.3.0: Would fail with ValidationException
# "Invocation of model ID anthropic.claude-haiku-4-5-20251001-v1:0 
#  with on-demand throughput isn't supported."

# AFTER v0.3.0: Automatically uses correct inference profile
message = create_user_message().add_text("Hello").build()
manager = LLMManager(
    models=["Claude Haiku 4.5"],  # System detects this is CRIS-only
    regions=["us-east-1"]
)
response = manager.converse(messages=[message])
# Uses inference profile: global.anthropic.claude-haiku-4-5-20251001-v1:0 ✓
```

**Technical Details:**
- Pattern matching in `ModelCorrelationConfig.CRIS_ONLY_MODEL_PATTERNS`
- Automatic CRIS-only access forced for matching models
- Regions without CRIS profiles are automatically skipped
- Detailed logging at INFO level for troubleshooting

## Inference Profile Support (Automatic)

### Overview

Starting in v0.4.0, LLMManager includes automatic inference profile support for AWS Bedrock models that require profile-based access. This feature is completely transparent - the system automatically detects when models require inference profiles, selects appropriate profiles, and learns access method preferences over time.

**Key Features:**
- **Automatic Detection**: Detects profile requirements from AWS ValidationException errors
- **Intelligent Selection**: Automatically selects optimal inference profiles
- **Learning System**: Learns and remembers successful access methods
- **Zero Configuration**: No code changes required - works automatically
- **Backward Compatible**: Models with direct access continue working unchanged

### What Are Inference Profiles?

Inference profiles (also called Cross-Region Inference or CRIS profiles) are AWS Bedrock resources that provide access to foundation models, potentially across multiple regions. Some newer models (like Claude Sonnet 4.5) require profile-based access instead of direct model ID invocation.

**Access Methods:**
- **Direct Access**: Using model ID directly (e.g., `anthropic.claude-3-haiku-20240307-v1:0`)
- **Regional CRIS**: Using regional inference profile ARN
- **Global CRIS**: Using global inference profile ID

### Automatic Profile Detection

The system automatically detects when a model requires inference profile access:

```python
from bestehorn_llmmanager import LLMManager, create_user_message

# No special configuration needed!
manager = LLMManager(
    models=["Claude Sonnet 4.5"],  # Requires inference profile
    regions=["us-east-1", "us-west-2"]
)

message = create_user_message().add_text("Hello!").build()

# System automatically:
# 1. Detects profile requirement from AWS error
# 2. Selects appropriate inference profile
# 3. Retries with profile immediately
# 4. Learns preference for future requests
response = manager.converse(messages=[message])

if response.success:
    print(f"Response: {response.get_content()}")
    print(f"Access method used: {response.access_method_used}")
    print(f"Profile used: {response.inference_profile_used}")
```

### Access Method Selection

The system uses intelligent preference ordering when multiple access methods are available:

**Preference Order:**
1. **Direct Access** - Fastest, lowest latency (preferred when available)
2. **Regional CRIS** - Region-specific inference profile
3. **Global CRIS** - Cross-region inference profile

**Automatic Learning:**
Once the system successfully uses a specific access method, it remembers this preference for future requests to the same model/region combination.

```python
# First request: System tries direct access, detects profile requirement, retries with profile
response1 = manager.converse(messages=[message])
# Access method: regional_cris (learned)

# Second request: System uses learned preference immediately
response2 = manager.converse(messages=[message])
# Access method: regional_cris (from learned preference)
```

### Checking Access Method Used

Response objects include metadata about which access method was used:

```python
response = manager.converse(messages=[message])

if response.success:
    # Check access method
    print(f"Access method: {response.access_method_used}")
    # Output: "direct", "regional_cris", or "global_cris"
    
    # Check if inference profile was used
    if response.inference_profile_used:
        print(f"Profile ID: {response.inference_profile_id}")
        # Output: Profile ARN or ID
    
    # Model and region information
    print(f"Model: {response.model_used}")
    print(f"Region: {response.region_used}")
```

### Response Metadata Fields

**BedrockResponse Fields:**
- `access_method_used` (str): Access method used ("direct", "regional_cris", "global_cris")
- `inference_profile_used` (bool): Whether an inference profile was used
- `inference_profile_id` (str): Profile ARN/ID if profile was used

**ParallelResponse Aggregation:**
```python
from bestehorn_llmmanager import ParallelLLMManager
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

parallel_manager = ParallelLLMManager(
    models=["Claude Sonnet 4.5", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"]
)

requests = [
    BedrockConverseRequest(request_id=f"req-{i}", messages=[message])
    for i in range(10)
]

parallel_response = parallel_manager.converse_parallel(requests=requests)

# Access method statistics
stats = parallel_response.parallel_execution_stats
print(f"Direct access: {stats.access_method_distribution.get('direct', 0)}")
print(f"Regional CRIS: {stats.access_method_distribution.get('regional_cris', 0)}")
print(f"Global CRIS: {stats.access_method_distribution.get('global_cris', 0)}")
```

### Access Method Statistics

Monitor access method usage across your application:

```python
from bestehorn_llmmanager.bedrock.tracking import AccessMethodTracker

# Get singleton tracker instance
tracker = AccessMethodTracker.get_instance()

# Get statistics
stats = tracker.get_statistics()

print(f"Total tracked combinations: {stats['total_tracked']}")
print(f"Profile-required models: {stats['profile_required_count']}")
print(f"Direct-access models: {stats['direct_access_count']}")

# Check if specific model requires profile
requires_profile = tracker.requires_profile(
    model_id="anthropic.claude-sonnet-4-20250514-v1:0",
    region="us-east-1"
)
print(f"Requires profile: {requires_profile}")
```

### Parallel Processing Support

Inference profile support works seamlessly with parallel processing:

```python
from bestehorn_llmmanager import ParallelLLMManager, create_user_message
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

parallel_manager = ParallelLLMManager(
    models=["Claude Sonnet 4.5"],  # Requires profiles
    regions=["us-east-1", "us-west-2", "eu-west-1"]
)

# Create multiple requests
messages = [
    create_user_message().add_text(f"Question {i}").build()
    for i in range(5)
]

requests = [
    BedrockConverseRequest(request_id=f"req-{i}", messages=[msg])
    for i, msg in enumerate(messages)
]

# Execute in parallel - profiles handled automatically for each request
parallel_response = parallel_manager.converse_parallel(requests=requests)

# Check results
for request_id, response in parallel_response.request_responses.items():
    if response.success:
        print(f"{request_id}: {response.access_method_used}")
```

### Graceful Degradation

When profile information is unavailable, the system gracefully falls back:

```python
# If a model requires a profile but none is available:
# 1. System logs warning about missing profile
# 2. Continues to next model/region combination
# 3. Eventually succeeds with available model/region

manager = LLMManager(
    models=["Claude Sonnet 4.5", "Claude 3 Haiku"],  # Fallback to Haiku if needed
    regions=["us-east-1", "us-west-2"]
)

response = manager.converse(messages=[message])

# Check warnings for profile-related issues
warnings = response.get_warnings()
for warning in warnings:
    print(f"Warning: {warning}")
```

### Logging

Profile support includes comprehensive logging at appropriate levels:

**WARNING Level** (Default):
- Profile requirement detection
- Missing profile information
- Profile unavailability

**INFO Level**:
- Profile selection
- Profile retry success
- Access method switches

**DEBUG Level**:
- Access method learning
- Preference updates
- Detailed retry flow

```python
import logging

# Enable INFO logging to see profile usage
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"],
    log_level=logging.INFO
)

# Logs will show:
# INFO: Model 'anthropic.claude-sonnet-4-20250514-v1:0' requires inference profile in region 'us-east-1'. Retrying with profile...
# INFO: Using inference profile 'arn:aws:bedrock:us-east-1::inference-profile/...' for model 'Claude Sonnet 4.5' in 'us-east-1'
# INFO: Request succeeded using inference profile for model 'Claude Sonnet 4.5' in 'us-east-1'
```

### Backward Compatibility

**No Breaking Changes:**
- All existing code continues to work without modifications
- Models supporting direct access use it by default
- Profile support is additive only
- No API changes required

```python
# Existing code works unchanged
manager = LLMManager(
    models=["Claude 3 Haiku"],  # Supports direct access
    regions=["us-east-1"]
)

message = create_user_message().add_text("Hello").build()
response = manager.converse(messages=[message])

# Uses direct access (no profile needed)
print(f"Access method: {response.access_method_used}")  # "direct"
```

### Common Scenarios

#### Scenario 1: New Model Requiring Profile

```python
# First time using Claude Sonnet 4.5
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"]
)

message = create_user_message().add_text("Hello").build()
response = manager.converse(messages=[message])

# System automatically:
# 1. Tries direct access (fails with ValidationException)
# 2. Detects profile requirement
# 3. Selects inference profile
# 4. Retries with profile (succeeds)
# 5. Records preference for future use

print(f"Success: {response.success}")
print(f"Access method: {response.access_method_used}")  # "regional_cris"
```

#### Scenario 2: Mixed Access Methods

```python
# Using models with different access requirements
manager = LLMManager(
    models=["Claude Sonnet 4.5", "Claude 3 Haiku"],  # Mixed requirements
    regions=["us-east-1", "us-west-2"]
)

message = create_user_message().add_text("Hello").build()
response = manager.converse(messages=[message])

# System uses appropriate access method for each model
# Claude Sonnet 4.5: Uses inference profile
# Claude 3 Haiku: Uses direct access
```

#### Scenario 3: Monitoring Access Methods

```python
from bestehorn_llmmanager.bedrock.tracking import AccessMethodTracker

# Execute multiple requests
for i in range(10):
    message = create_user_message().add_text(f"Request {i}").build()
    response = manager.converse(messages=[message])
    print(f"Request {i}: {response.access_method_used}")

# Check learned preferences
tracker = AccessMethodTracker.get_instance()
stats = tracker.get_statistics()

print(f"\nAccess Method Statistics:")
print(f"Total tracked: {stats['total_tracked']}")
print(f"Profile required: {stats['profile_required_count']}")
print(f"Direct access: {stats['direct_access_count']}")
```

### Troubleshooting

**Issue: Model requires profile but none available**

```python
# Error message will indicate:
# "Model 'anthropic.claude-sonnet-4-20250514-v1:0' requires inference profile 
#  in 'us-east-1' but no profile information available in catalog"

# Solution: Refresh catalog data
manager.refresh_model_data()

# Or use fallback model
manager = LLMManager(
    models=["Claude Sonnet 4.5", "Claude 3 Haiku"],  # Fallback to Haiku
    regions=["us-east-1"]
)
```

**Issue: Want to see which access method is being used**

```python
# Enable INFO logging
import logging

manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"],
    log_level=logging.INFO
)

# Check response metadata
response = manager.converse(messages=[message])
print(f"Access method: {response.access_method_used}")
print(f"Profile used: {response.inference_profile_used}")
if response.inference_profile_used:
    print(f"Profile ID: {response.inference_profile_id}")
```

**Issue: Want to monitor access method distribution**

```python
from bestehorn_llmmanager.bedrock.tracking import AccessMethodTracker

tracker = AccessMethodTracker.get_instance()
stats = tracker.get_statistics()

print(f"Access method distribution:")
for method, count in stats.get('access_method_distribution', {}).items():
    print(f"  {method}: {count}")
```

### Performance Impact

**Minimal Overhead:**
- Profile detection only occurs on ValidationException (rare)
- Access method lookup is O(1) dictionary lookup
- Learning system uses thread-safe in-memory cache
- No additional API calls (profile info from catalog)

**Typical Performance:**
- First request with profile requirement: +1 retry (immediate)
- Subsequent requests: No overhead (uses learned preference)
- Parallel processing: No performance degradation

### Summary

Inference profile support in LLMManager is:
- **Automatic**: No configuration or code changes required
- **Intelligent**: Learns and optimizes access methods over time
- **Transparent**: Works seamlessly with existing code
- **Reliable**: Graceful fallback when profiles unavailable
- **Observable**: Comprehensive logging and statistics
- **Performant**: Minimal overhead, fast learning

The system handles all complexity of inference profiles automatically, allowing you to focus on building your application without worrying about AWS Bedrock access method details.

## Model and Region Management

### Enhanced Provider Support

LLMManager now supports comprehensive provider prefix normalization for all AWS Bedrock providers, enabling seamless correlation between CRIS data and foundational model data. This enhancement ensures that models from all providers load correctly, including:

**Supported Providers:**
- **Anthropic** - Claude models (e.g., Claude 3 Haiku, Claude 3.5 Sonnet)
- **Meta** - Llama models (e.g., Llama 3.1, Llama 3.2, Llama 3.3)
- **Amazon** - Titan and Nova models
- **Mistral AI** - Mistral and Pixtral models
- **TwelveLabs** - Marengo models (e.g., Marengo Embed v2.7)
- **Cohere** - Command and Embed models
- **Writer** - Palmyra models
- **DeepSeek** - DeepSeek models
- **Stability AI** - Stable Diffusion models
- **AI21 Labs** - Jurassic models

The system automatically handles provider prefix normalization (e.g., `anthropic.claude-3-5-haiku-20241022-v1:0` → `claude-3-5-haiku-20241022-v1:0`) to ensure proper model correlation across different AWS Bedrock naming conventions.

### CRIS Model Correlation

The Cross-Region Inference Service (CRIS) correlation system has been enhanced to:

1. **Global Variant Prioritization**: Automatically prioritizes Global CRIS variants over regional variants for better routing and availability
2. **Comprehensive Provider Coverage**: Supports all AWS Bedrock providers through enhanced prefix normalization
3. **Synthetic Model Creation**: Automatically creates synthetic base models for CRIS-only models (like Claude Haiku 4.5) to ensure proper loading
4. **Expected Behavior Logging**: CRIS-only region messages are logged at INFO level rather than WARNING level, as this is expected behavior for models with limited CRIS coverage

**CRIS-Only Regions:**
Some models may only be available through CRIS in certain regions. These are automatically detected and handled:
- Regions marked with `*` in model data indicate CRIS-only availability
- The system automatically uses inference profiles for CRIS-only regions
- INFO level logging confirms expected CRIS-only behavior (not errors)

### Model Names

The LLMManager supports flexible model name resolution (NEW in v3.1.0), allowing you to use friendly, memorable names instead of exact API identifiers. **For complete documentation, see the [Model Name Resolution Guide](MODEL_NAME_RESOLUTION_GUIDE.md).**

**Friendly Names (Recommended):**
- `"Claude 3 Haiku"` - Fast, efficient model
- `"Claude 3 Sonnet"` - Balanced performance
- `"Claude 3 Opus"` - Most capable model
- `"Claude 3.5 Sonnet"` - Enhanced version
- `"Claude 3.5 Haiku"` - Enhanced efficient model
- `"Claude 4.5 Haiku"` - Latest efficient model
- `"Nova Micro"` - Amazon's multimodal model
- `"Nova Lite"` - Amazon's lightweight model
- `"Nova Pro"` - Amazon's professional model
- `"Llama 3 8B Instruct"` - Meta's instruction-tuned model
- `"Llama 3.1 8B Instruct"` - Meta's enhanced model
- `"Marengo Embed v2.7"` - TwelveLabs embedding model

**Name Resolution Features:**
- **Case Insensitive**: `"claude 3 haiku"` = `"Claude 3 Haiku"`
- **Flexible Spacing**: `"Claude3Haiku"` = `"Claude 3 Haiku"`
- **Flexible Punctuation**: `"Claude-3-Haiku"` = `"Claude 3 Haiku"`
- **Version Formats**: `"Claude 3.5 Sonnet"` = `"Claude 3 5 Sonnet"`
- **Word Order**: `"Claude 3 Haiku"` = `"Claude Haiku 3"`
- **Provider Prefixes**: `"Anthropic Claude 3 Haiku"` = `"Claude 3 Haiku"`
- **Automatic Aliases**: System generates multiple aliases for each model
- **Legacy Support**: All UnifiedModelManager names work automatically

**API Names (Also Supported):**
- `"anthropic.claude-3-haiku-20240307-v1:0"` - Full model ID
- `"Claude Haiku 4 5 20251001"` - API model name

**Legacy Names (Backward Compatible):**
All UnifiedModelManager names are automatically supported for backward compatibility. No code changes required when migrating from UnifiedModelManager to BedrockModelCatalog.

**Examples:**
```python
from bestehorn_llmmanager import LLMManager

# All of these work and refer to the same model:
manager = LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])
manager = LLMManager(models=["Claude Haiku 3"], regions=["us-east-1"])
manager = LLMManager(models=["claude-3-haiku"], regions=["us-east-1"])
manager = LLMManager(models=["CLAUDE 3 HAIKU"], regions=["us-east-1"])
manager = LLMManager(models=["Claude3Haiku"], regions=["us-east-1"])

# Version number flexibility:
manager = LLMManager(models=["Claude 3.5 Sonnet"], regions=["us-east-1"])
manager = LLMManager(models=["Claude 3 5 Sonnet"], regions=["us-east-1"])
manager = LLMManager(models=["Claude Sonnet 3.5"], regions=["us-east-1"])

# Legacy UnifiedModelManager names still work:
manager = LLMManager(models=["Titan Text G1 - Lite"], regions=["us-east-1"])
```

**Error Handling:**
If a model name cannot be resolved, you'll receive a helpful error message with suggestions:

```python
from bestehorn_llmmanager.bedrock.exceptions import ConfigurationError

try:
    manager = LLMManager(models=["Claude 3 Hiku"], regions=["us-east-1"])  # Typo
except ConfigurationError as e:
    print(e)
    # "Model 'Claude 3 Hiku' not found. Did you mean: Claude 3 Haiku, 
    #  Claude 3.5 Haiku, Claude 3 Sonnet?"
```

**For More Information:**
- Complete name resolution documentation: [Model Name Resolution Guide](MODEL_NAME_RESOLUTION_GUIDE.md)
- Migration scenarios and examples
- Troubleshooting guide
- Legacy name mappings table

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

## BedrockModelCatalog - Unified Model Management

The `BedrockModelCatalog` is the new unified system for managing AWS Bedrock model availability data. It replaces the deprecated `ModelManager`, `CRISManager`, and `UnifiedModelManager` classes.

### Overview

**Key Features:**
- API-only data retrieval (no HTML parsing)
- Single unified class for all model management
- Flexible cache modes (FILE, MEMORY, NONE)
- Lambda-friendly design
- Bundled fallback data for offline scenarios
- Automatic failover and error handling
- **User-friendly model name resolution** (NEW in v3.1.0)

**Deprecation Notice:**
The following classes are deprecated and will be removed in version 4.0.0:
- `ModelManager` - Use `BedrockModelCatalog` instead
- `CRISManager` - Use `BedrockModelCatalog` instead
- `UnifiedModelManager` - Use `BedrockModelCatalog` instead

### Model Name Resolution (NEW in v3.1.0)

The `BedrockModelCatalog` now includes a powerful model name resolution system that allows you to reference models using friendly, memorable names instead of API-specific identifiers.

**For complete documentation, see the [Model Name Resolution Guide](MODEL_NAME_RESOLUTION_GUIDE.md).**

#### Why Name Resolution?

AWS Bedrock API returns model names like `"Claude Haiku 4 5 20251001"` which are difficult to remember and use. The name resolution system automatically generates user-friendly aliases like `"Claude 3 Haiku"`, `"Claude Haiku 4.5"`, and maintains backward compatibility with legacy `UnifiedModelManager` names.

#### Key Features

- **User-Friendly Names**: Use memorable names like `"Claude 3 Haiku"` instead of `"Claude Haiku 4 5 20251001"`
- **Flexible Matching**: Case-insensitive, handles spacing/punctuation variations
- **Version Flexibility**: `"Claude 3.5 Sonnet"` = `"Claude 3 5 Sonnet"` = `"Claude Sonnet 3.5"`
- **Backward Compatible**: All `UnifiedModelManager` legacy names work automatically
- **Helpful Errors**: Suggestions provided when names don't resolve
- **Automatic Aliases**: System generates multiple aliases for each model

#### Supported Name Formats

The catalog accepts multiple name formats for the same model:

**API Names (Exact):**
- `"Claude Haiku 4 5 20251001"` - Exact API name
- `"anthropic.claude-3-haiku-20240307-v1:0"` - Full model ID

**Friendly Aliases (Generated):**
- `"Claude 3 Haiku"` - Simple, memorable name
- `"Claude Haiku 3"` - Alternative word order
- `"Claude 3.5 Sonnet"` - Version with decimal notation
- `"Claude Sonnet 3.5"` - Alternative word order

**Legacy Names (Backward Compatible):**
- All `UnifiedModelManager` names are supported
- Automatic mapping to new catalog names
- Clear error messages for deprecated models

**Flexible Matching:**
- Case insensitive: `"claude 3 haiku"` = `"Claude 3 Haiku"`
- Spacing variations: `"Claude3Haiku"` = `"Claude 3 Haiku"`
- Punctuation variations: `"Claude-3-Haiku"` = `"Claude 3 Haiku"`
- Version formats: `"4.5"` = `"4 5"` = `"45"`
- Word order: `"Claude 3 Haiku"` = `"Claude Haiku 3"`
- Provider prefixes: `"Anthropic Claude 3 Haiku"` = `"Claude 3 Haiku"`

#### Quick Examples

```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

catalog = BedrockModelCatalog()

# All of these resolve to the same model:
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
model_info = catalog.get_model_info("Claude Haiku 3", "us-east-1")
model_info = catalog.get_model_info("claude-3-haiku", "us-east-1")
model_info = catalog.get_model_info("CLAUDE 3 HAIKU", "us-east-1")
model_info = catalog.get_model_info("Claude3Haiku", "us-east-1")

# Version number flexibility:
model_info = catalog.get_model_info("Claude 3.5 Sonnet", "us-east-1")
model_info = catalog.get_model_info("Claude Sonnet 3.5", "us-east-1")
model_info = catalog.get_model_info("Claude 3 5 Sonnet", "us-east-1")

# Legacy UnifiedModelManager names still work:
model_info = catalog.get_model_info("Titan Text G1 - Lite", "us-east-1")
model_info = catalog.get_model_info("Llama 3 8B Instruct", "us-east-1")
```

#### Error Messages with Suggestions

When a model name cannot be resolved, the catalog provides helpful suggestions:

```python
from bestehorn_llmmanager.bedrock.exceptions import ConfigurationError

try:
    model_info = catalog.get_model_info("Claude 3 Hiku", "us-east-1")  # Typo
except ConfigurationError as e:
    # Error message includes suggestions:
    # "Model 'Claude 3 Hiku' not found in region 'us-east-1'. 
    #  Did you mean: Claude 3 Haiku, Claude 3.5 Haiku, Claude 3 Sonnet?"
    print(e)
```

#### Name Resolution with LLMManager

The `LLMManager` automatically uses the name resolution system:

```python
from bestehorn_llmmanager import LLMManager, create_user_message

# Use friendly names - no need to know exact API names!
manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3.5 Sonnet"],  # Friendly names
    regions=["us-east-1", "us-west-2"]
)

message = create_user_message().add_text("Hello!").build()
response = manager.converse(messages=[message])

# The system automatically resolves to the correct model IDs
print(f"Used model: {response.model_used}")
```

#### Common Model Name Aliases

**Claude Models:**
- `"Claude 3 Haiku"`, `"Claude Haiku 3"`, `"claude-3-haiku"`
- `"Claude 3 Sonnet"`, `"Claude Sonnet 3"`, `"claude-3-sonnet"`
- `"Claude 3 Opus"`, `"Claude Opus 3"`, `"claude-3-opus"`
- `"Claude 3.5 Sonnet"`, `"Claude Sonnet 3.5"`, `"claude-3-5-sonnet"`
- `"Claude 3.5 Haiku"`, `"Claude Haiku 3.5"`, `"claude-3-5-haiku"`
- `"Claude 4.5 Haiku"`, `"Claude Haiku 4.5"`, `"claude-4-5-haiku"`

**Amazon Models:**
- `"Nova Micro"`, `"Amazon Nova Micro"`
- `"Nova Lite"`, `"Amazon Nova Lite"`
- `"Nova Pro"`, `"Amazon Nova Pro"`
- `"Titan Text G1 - Lite"`, `"Titan Text Lite"`

**Meta Models:**
- `"Llama 3 8B Instruct"`, `"Llama 3 8B"`
- `"Llama 3.1 8B Instruct"`, `"Llama 3.1 8B"`
- `"Llama 3.2 1B Instruct"`, `"Llama 3.2 1B"`

**Provider-Prefixed Models:**
- `"APAC Claude 3 Haiku"` → resolves to `"Claude 3 Haiku"`
- `"EU Anthropic Claude 3 Sonnet"` → resolves to `"Claude 3 Sonnet"`

#### Name Resolution Behavior

The resolution system follows this priority order:

1. **Exact Match**: Check for exact API name match
2. **Alias Match**: Check generated friendly aliases
3. **Legacy Match**: Check UnifiedModelManager legacy mappings
4. **Normalized Match**: Check with normalization (case, spacing, punctuation)
5. **Fuzzy Match**: Find similar names (if not in strict mode)

#### Migration from UnifiedModelManager

**No code changes required!** All legacy names work automatically:

```python
# OLD CODE (UnifiedModelManager) - Still works!
manager = LLMManager(
    models=["Claude 3 Haiku"],  # Legacy name
    regions=["us-east-1"]
)

# NEW CODE (BedrockModelCatalog) - Also works!
manager = LLMManager(
    models=["Claude 3 Haiku"],  # Same name, automatic resolution
    regions=["us-east-1"]
)

# No code changes needed for migration!
```

#### For More Information

For comprehensive documentation including:
- Complete list of supported name formats
- Detailed migration scenarios
- Troubleshooting guide
- Legacy name mappings table
- Testing examples
- Best practices

See the **[Model Name Resolution Guide](MODEL_NAME_RESOLUTION_GUIDE.md)**.

### Basic Usage

```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

# Initialize with defaults
catalog = BedrockModelCatalog()

# Check if a model is available in a region
is_available = catalog.is_model_available(
    model_name="Claude 3 Haiku",
    region="us-east-1"
)

# Get detailed model information
model_info = catalog.get_model_info(
    model_name="Claude 3 Haiku",
    region="us-east-1"
)

if model_info:
    print(f"Model ID: {model_info.model_id}")
    print(f"Inference Profile: {model_info.inference_profile_id}")
    print(f"Access Method: {model_info.access_method.value}")
    print(f"Supports Streaming: {model_info.supports_streaming}")

# List all available models
all_models = catalog.list_models()

# Filter models by criteria
anthropic_models = catalog.list_models(
    region="us-east-1",
    provider="Anthropic",
    streaming_only=True
)
```

### Cache Modes

The catalog supports three cache modes to fit different deployment scenarios:

#### CacheMode.FILE (Default)

File-based caching with persistent storage.

```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode
from pathlib import Path

catalog = BedrockModelCatalog(
    cache_mode=CacheMode.FILE,
    cache_directory=Path("/tmp/bedrock_cache"),
    cache_max_age_hours=24.0
)
```

**Best for:** Production environments, Lambda with /tmp access  
**Pros:** Fast warm starts, persistent across process restarts  
**Cons:** Requires file system write access  
**Performance:** < 100ms warm start

#### CacheMode.MEMORY

In-memory caching for process lifetime.

```python
catalog = BedrockModelCatalog(cache_mode=CacheMode.MEMORY)
```

**Best for:** Read-only environments, Lambda without /tmp  
**Pros:** No file I/O, works in restricted environments  
**Cons:** Cache lost on process restart  
**Performance:** Fast during warm starts, slower on cold starts

#### CacheMode.NONE

No caching, always fetch fresh data.

```python
catalog = BedrockModelCatalog(
    cache_mode=CacheMode.NONE,
    fallback_to_bundled=True
)
```

**Best for:** Security-critical environments, always need latest data  
**Pros:** Always fresh data, no stale cache issues  
**Cons:** Higher latency, more API calls  
**Performance:** 2-5 seconds per initialization

### Initialization Parameters

```python
def __init__(
    self,
    cache_mode: CacheMode = CacheMode.FILE,
    cache_directory: Optional[Path] = None,
    cache_max_age_hours: float = 24.0,
    force_refresh: bool = False,
    timeout: int = 30,
    max_workers: int = 10,
    fallback_to_bundled: bool = True,
) -> None
```

**Parameters:**
- `cache_mode`: Caching strategy (FILE, MEMORY, NONE). Default: FILE
- `cache_directory`: Directory for cache file. Default: platform-specific cache directory
- `cache_max_age_hours`: Maximum cache age before refresh. Default: 24.0
- `force_refresh`: Force API refresh even if cache is valid. Default: False
- `timeout`: API call timeout in seconds. Default: 30
- `max_workers`: Parallel workers for multi-region API calls. Default: 10
- `fallback_to_bundled`: Use bundled data if API fails. Default: True

### Query Methods

#### get_model_info()

Get detailed information about a model in a specific region.

```python
def get_model_info(
    self,
    model_name: str,
    region: str
) -> Optional[ModelAccessInfo]
```

**Returns:** `ModelAccessInfo` object or `None` if model not available

**Example:**
```python
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
if model_info:
    print(f"Model ID: {model_info.model_id}")
    print(f"Inference Profile: {model_info.inference_profile_id}")
    print(f"Access Method: {model_info.access_method.value}")
    print(f"Supports Streaming: {model_info.supports_streaming}")
    print(f"Regions: {model_info.regions}")
```

#### is_model_available()

Check if a model is available in a specific region.

```python
def is_model_available(
    self,
    model_name: str,
    region: str
) -> bool
```

**Returns:** `True` if model is available, `False` otherwise

**Example:**
```python
if catalog.is_model_available("Claude 3 Haiku", "us-east-1"):
    print("Model is available")
else:
    print("Model is not available")
```

#### list_models()

List models with optional filtering.

```python
def list_models(
    self,
    region: Optional[str] = None,
    provider: Optional[str] = None,
    streaming_only: bool = False
) -> List[ModelInfo]
```

**Parameters:**
- `region`: Filter by AWS region (optional)
- `provider`: Filter by provider name (optional)
- `streaming_only`: Only return streaming-capable models (optional)

**Returns:** List of `ModelInfo` objects

**Example:**
```python
# List all models
all_models = catalog.list_models()

# List models in specific region
us_east_models = catalog.list_models(region="us-east-1")

# List models by provider
anthropic_models = catalog.list_models(provider="Anthropic")

# List streaming-capable models
streaming_models = catalog.list_models(streaming_only=True)

# Combined filters
filtered = catalog.list_models(
    region="us-west-2",
    provider="Anthropic",
    streaming_only=True
)
```

#### get_catalog_metadata()

Get metadata about the catalog source and freshness.

```python
def get_catalog_metadata(self) -> CatalogMetadata
```

**Returns:** `CatalogMetadata` object with source, timestamp, and version information

**Example:**
```python
metadata = catalog.get_catalog_metadata()
print(f"Source: {metadata.source.value}")  # API, CACHE, or BUNDLED
print(f"Retrieved: {metadata.retrieval_timestamp}")
print(f"Regions queried: {metadata.api_regions_queried}")

if metadata.source == CatalogSource.BUNDLED:
    print(f"Bundled version: {metadata.bundled_data_version}")
elif metadata.source == CatalogSource.CACHE:
    print(f"Cache file: {metadata.cache_file_path}")
```

### Data Structures

#### CatalogMetadata

```python
@dataclass
class CatalogMetadata:
    source: CatalogSource  # API, CACHE, or BUNDLED
    retrieval_timestamp: datetime
    api_regions_queried: List[str]
    bundled_data_version: Optional[str]
    cache_file_path: Optional[Path]
```

#### CatalogSource

```python
class CatalogSource(Enum):
    API = "api"          # Fresh data from AWS APIs
    CACHE = "cache"      # Loaded from cache file
    BUNDLED = "bundled"  # Loaded from bundled package data
```

#### CacheMode

```python
class CacheMode(Enum):
    FILE = "file"      # Cache to file system
    MEMORY = "memory"  # Cache in memory only
    NONE = "none"      # No caching
```

### Bundled Fallback Data

The package includes pre-generated model data for offline scenarios:

**Features:**
- Automatic fallback if API calls fail
- Works without AWS credentials or internet access
- Updated with each package release
- Includes generation timestamp and version

**Example:**
```python
# Catalog will try: Cache → API → Bundled Data
catalog = BedrockModelCatalog(fallback_to_bundled=True)

metadata = catalog.get_catalog_metadata()
if metadata.source == CatalogSource.BUNDLED:
    print(f"Using bundled data (version: {metadata.bundled_data_version})")
    print("Consider refreshing for latest model availability")
```

### Lambda Deployment

#### Lambda with /tmp Access (Recommended)

```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode
from pathlib import Path

def lambda_handler(event, context):
    catalog = BedrockModelCatalog(
        cache_mode=CacheMode.FILE,
        cache_directory=Path("/tmp/bedrock_cache")
    )
    
    model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
    return {"available": model_info is not None}
```

#### Lambda Read-Only Environment

```python
def lambda_handler(event, context):
    catalog = BedrockModelCatalog(cache_mode=CacheMode.MEMORY)
    is_available = catalog.is_model_available("Claude 3 Haiku", "us-east-1")
    return {"available": is_available}
```

### Integration with LLMManager

The `LLMManager` automatically uses `BedrockModelCatalog` internally. You can configure catalog behavior through LLMManager parameters:

```python
from bestehorn_llmmanager import LLMManager
from bestehorn_llmmanager.bedrock.catalog import CacheMode
from pathlib import Path

manager = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"],
    catalog_cache_mode=CacheMode.FILE,
    catalog_cache_directory=Path("/tmp/my_cache")
)
```

**LLMManager Catalog Parameters:**
- `catalog_cache_mode`: Cache mode for the catalog (default: FILE)
- `catalog_cache_directory`: Cache directory path (default: platform-specific)

### Error Handling

The catalog uses a fallback strategy for reliability:

1. **Try Cache:** Load from cache if valid
2. **Try API:** Fetch from AWS APIs if cache invalid/missing
3. **Try Bundled:** Use bundled data if API fails
4. **Raise Error:** Only if all sources fail

**Exceptions:**
- `CatalogUnavailableError`: Raised when catalog cannot be obtained from any source
- `APIFetchError`: Raised when API fetching fails
- `CacheError`: Raised when cache operations fail
- `BundledDataError`: Raised when bundled data is missing or corrupt

**Example:**
```python
from bestehorn_llmmanager.bedrock.exceptions import CatalogUnavailableError

try:
    catalog = BedrockModelCatalog(
        fallback_to_bundled=False  # Disable bundled fallback
    )
except CatalogUnavailableError as e:
    print(f"Catalog unavailable: {e}")
    # Handle error (e.g., use default models)
```

### Performance Characteristics

- **Cold start (no cache):** 2-5 seconds (parallel API calls)
- **Warm start (valid cache):** < 100ms (file load)
- **Memory usage:** ~5-10 MB for full catalog
- **Cache file size:** ~500 KB - 1 MB

### Migration from Old Managers

**Old Code:**
```python
from bestehorn_llmmanager.bedrock import UnifiedModelManager

manager = UnifiedModelManager()
model_info = manager.get_model_info("Claude 3 Haiku", "us-east-1")
```

**New Code:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

catalog = BedrockModelCatalog()
model_info = catalog.get_model_info("Claude 3 Haiku", "us-east-1")
```

See the [Migration Guide](MIGRATION_GUIDE.md) for detailed migration instructions.

## Best Practices

### 1. MessageBuilder Usage
- Use the fluent interface for building complex messages
- Leverage automatic format detection for convenience
- Use explicit format specification when format is known
- Handle file size limits appropriately
- Chain multiple content types for rich interactions

### 2. Model Selection
- Use multiple models for redundancy
- Order models by preference (first = preferred)
- Consider cost vs. capability trade-offs

### 3. Region Selection
- Use multiple regions for reliability
- Consider latency and data locality
- Include at least 2-3 regions for fault tolerance

### 4. Error Handling
- Always check `response.success` before accessing content
- Handle specific exception types appropriately
- Use try-catch blocks around MessageBuilder operations
- Log errors and warnings for debugging

### 5. Performance Optimization
- Use parallel processing for multiple requests
- Configure appropriate timeouts
- Monitor retry statistics and adjust configuration
- Use MessageBuilder for efficient message construction

### 6. Security
- Use IAM roles or profiles instead of hardcoded credentials
- Implement response validation for sensitive applications
- Consider guardrails for content filtering
- Validate file uploads before processing

### 7. Resource Management
- Refresh model data periodically
- Monitor token usage and costs
- Use appropriate inference configurations
- Handle large files efficiently with size limits

## Constants and Enums

### Important Constants

```python
# From message_builder_constants.py
from bestehorn_llmmanager.message_builder_constants import (
    MessageBuilderConfig,     # Configuration defaults
    MessageBuilderLogMessages, # Log message templates
    MessageBuilderErrorMessages, # Error message templates
    SupportedFormats         # Supported file formats
)

# Content limits
MAX_IMAGES_PER_REQUEST = 20
MAX_DOCUMENTS_PER_REQUEST = 5
MAX_VIDEOS_PER_REQUEST = 1
MAX_IMAGE_SIZE_BYTES = 3_750_000  # 3.75 MB
MAX_DOCUMENT_SIZE_BYTES = 4_500_000  # 4.5 MB
MAX_VIDEO_SIZE_BYTES = 100_000_000  # 100 MB

# Default configuration values
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_TIMEOUT = 300
MAX_CONTENT_BLOCKS_PER_MESSAGE = 20
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

# MessageBuilder roles
class RolesEnum(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

# Supported image formats
class ImageFormatEnum(str, Enum):
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"

# Supported document formats
class DocumentFormatEnum(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    DOC = "doc"
    DOCX = "docx"
    XLS = "xls"
    XLSX = "xlsx"
    HTML = "html"
    TXT = "txt"
    MD = "md"

# Supported video formats
class VideoFormatEnum(str, Enum):
    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"
    WEBM = "webm"
    MKV = "mkv"

# File type detection methods
class DetectionMethodEnum(str, Enum):
    EXTENSION = "extension"
    CONTENT = "content"
    COMBINED = "combined"
    MANUAL = "manual"

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

## Advanced MessageBuilder Features

### File Type Detection

The MessageBuilder includes sophisticated file type detection capabilities:

```python
from bestehorn_llmmanager.util.file_type_detector import FileTypeDetector, DetectionResult

# Manual file type detection (advanced usage)
detector = FileTypeDetector()

# Detect image format from bytes
with open("image.jpg", "rb") as f:
    image_data = f.read()

result = detector.detect_image_format(content=image_data, filename="image.jpg")
if result.is_successful:
    print(f"Detected format: {result.detected_format}")
    print(f"Confidence: {result.confidence}")
    print(f"Method: {result.detection_method.value}")
else:
    print(f"Detection failed: {result.error_message}")
```

### Custom Validation

```python
# Advanced MessageBuilder with custom validation
def validate_message_content(builder):
    """Custom validation for message content."""
    if builder.content_block_count > 10:
        raise ValueError("Too many content blocks")
    return True

try:
    message = create_user_message()
    message.add_text("Primary content")
    
    # Add multiple content blocks with validation
    for i in range(5):
        message.add_text(f"Additional content {i}")
    
    validate_message_content(message)
    
    built_message = message.build()
    response = manager.converse(messages=[built_message])
    
except ValueError as e:
    print(f"Validation error: {e}")
```

### Streaming with MessageBuilder

```python
# Use MessageBuilder with streaming responses
message = create_user_message()\
    .add_text("Write a long story about adventure")\
    .build()

stream_response = manager.converse_stream(messages=[message])

# Handle streaming response
for chunk in stream_response:
    if chunk.get("contentBlockDelta"):
        delta = chunk["contentBlockDelta"]
        if "text" in delta:
            print(delta["text"], end="", flush=True)
```

## Summary

This comprehensive documentation covers all aspects of the LLMManager package, with special emphasis on the MessageBuilder functionality. The MessageBuilder provides:

1. **Fluent Interface**: Method chaining for intuitive message construction
2. **Automatic Format Detection**: Intelligent file type detection from content and filenames
3. **Multi-Modal Support**: Support for text, images, documents, and videos
4. **Validation**: Built-in content validation and size limit enforcement
5. **AWS Bedrock Compatibility**: Direct compatibility with AWS Bedrock Converse API
6. **Error Handling**: Comprehensive error handling and validation
7. **Flexibility**: Support for both convenience methods and advanced configuration

The MessageBuilder eliminates the need to manually construct complex message dictionaries and provides a type-safe, validated approach to building multi-modal messages for AWS Bedrock interactions.

**Key MessageBuilder Features:**
- Fluent method chaining: `.add_text().add_image().add_document().build()`
- Automatic format detection from file content and extensions
- Built-in size limits and validation
- Support for local files and raw bytes
- Compatible with all LLMManager methods
- Comprehensive error handling
- Full type safety with enums for formats and roles

Use the MessageBuilder for all message construction needs to ensure proper formatting, validation, and compatibility with the AWS Bedrock Converse API.

## CI/CD Integration and Workflow Synchronization

### GitHub CI Workflow Integration

This project uses GitHub Actions for continuous integration. The primary CI configuration is located at `.github/workflows/ci.yml` and includes the following jobs:

1. **lint**: Code quality checks (black, isort, flake8, mypy)
2. **test**: Unit tests with coverage across Python versions 3.8-3.12  
3. **build**: Package building and validation
4. **security**: CodeQL security analysis

### Cline Workflow Synchronization

**IMPORTANT FOR LLM ASSISTANTS**: The project includes a Cline Workflow at `.clinerules/workflows/pre-commit-checks.md` that must be kept synchronized with the GitHub CI workflow. When working with this project, LLM assistants should:

#### 1. Monitor CI Workflow Changes

Always check if the GitHub CI workflow (`.github/workflows/ci.yml`) has been modified when:
- Making changes to the project structure
- Updating dependencies or tooling
- Modifying linting/testing configurations
- Any changes that might affect the CI pipeline

#### 2. Update Cline Workflow When CI Changes

When the CI workflow is updated, automatically update the Cline Workflow (`.clinerules/workflows/pre-commit-checks.md`) to match:

**Key synchronization points:**
- **Lint job commands**: Ensure the pre-commit workflow uses identical commands as the CI lint job
- **Dependencies**: Match the exact versions and installation commands
- **File exclusions**: Keep the same exclusion patterns for `_version.py` files
- **Command flags**: Use identical flags and options for all tools (black, isort, flake8, mypy)
- **Directory paths**: Maintain consistent `src/` and `test/` directory references

**Example mapping:**
```yaml
# CI workflow lint job step:
- name: Check code formatting with Black
  run: black --check --extend-exclude="src/bestehorn_llmmanager/_version.py" src/ test/

# Should map to Cline workflow step:
### Step 2: Code Formatting Check (Black)
```bash
black --check --extend-exclude="src/bestehorn_llmmanager/_version.py" src/ test/
```
```

#### 3. Synchronization Checklist

When updating the Cline Workflow after CI changes, verify:

- [ ] All lint job commands are reflected in the pre-commit workflow
- [ ] Installation commands match (pip install statements)
- [ ] File exclusion patterns are identical
- [ ] Command flags and options are the same
- [ ] Directory paths are consistent
- [ ] New tools or checks are added to the workflow
- [ ] Removed tools or checks are removed from the workflow
- [ ] Step descriptions and expected results are updated

#### 4. Configuration File Dependencies

The Cline Workflow depends on these configuration files:
- `pyproject.toml` - Contains tool configurations for black, isort, pytest, mypy
- `.github/workflows/ci.yml` - Source of truth for CI pipeline commands

When these files change, review and update the Cline Workflow documentation accordingly.

#### 5. Automatic Synchronization Process

**For LLM Assistants working on this project:**

1. **Before making changes**: Always read `.github/workflows/ci.yml` to understand current CI setup
2. **After CI modifications**: Immediately update `.clinerules/workflows/pre-commit-checks.md` to match
3. **Verification**: Test that the Cline Workflow commands produce the same results as CI
4. **Documentation**: Update any step descriptions or troubleshooting sections as needed

This synchronization ensures that developers can run the same checks locally through Cline that will be executed in the CI pipeline, preventing CI failures and improving development workflow efficiency.
