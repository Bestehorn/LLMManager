# LLMManager - Complete API Reference for Coding Assistants

## Overview

The LLMManager package provides a comprehensive interface for managing AWS Bedrock LLM interactions with support for multiple models, regions, authentication methods, retry logic, parallel processing, and fluent message building with automatic format detection.

### Core Components

- **LLMManager**: Main class for single AWS Bedrock requests with retry logic
- **ParallelLLMManager**: Extended class for parallel processing of multiple requests
- **MessageBuilder**: Fluent interface for building multi-modal messages with automatic format detection
- **BedrockResponse**: Comprehensive response object with metadata and utilities
- **UnifiedModelManager**: Manages model availability and access information

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
    unified_model_manager: Optional[UnifiedModelManager] = None,  # Optional: Pre-configured model manager
    default_inference_config: Optional[Dict[str, Any]] = None,    # Optional: Default inference parameters
    timeout: int = 300,                                   # Optional: Request timeout in seconds
    log_level: Union[int, str] = logging.WARNING         # Optional: Logging level (default: WARNING)
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
