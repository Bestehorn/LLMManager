# Bestehorn LLMManager

[![PyPI version](https://badge.fury.io/py/bestehorn-llmmanager.svg)](https://badge.fury.io/py/bestehorn-llmmanager)
[![Python Versions](https://img.shields.io/pypi/pyversions/bestehorn-llmmanager.svg)](https://pypi.org/project/bestehorn-llmmanager/)
[![Build Status](https://github.com/Bestehorn/LLMManager/actions/workflows/ci.yml/badge.svg)](https://github.com/Bestehorn/LLMManager/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Bestehorn/LLMManager/graph/badge.svg?token=YOUR_CODECOV_TOKEN)](https://codecov.io/gh/Bestehorn/LLMManager)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**A comprehensive Python library that simplifies and enhances AWS Bedrock Converse API interactions with intelligent message building, automatic file format detection, multi-modal support, and advanced reliability features.**

## 🚀 Key Advantages Over Native AWS Bedrock Converse API

This library was built to simplify the [standard AWS Bedrock Converse API](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html). 
While some of these simplifications come at a loss of flexibility, for most use cases, the code becomes cleaner, less prone to errors and easier to understand when it is based on the abstractions provided in this package: 

### 🎯 **Fluent MessageBuilder with Automatic Format Detection**
- **Native API**: Manual message dictionary construction with complex nested structures resulting in complex JSON
- **LLMManager**: Intuitive fluent interface with automatic file type detection and validation that hides the intricacies of building message JSON for Bedrock's converse API.

### 🔄 **Intelligent Multi-Region Failover**
- **Native API**: Single region, manual error handling required, i.e., you have to handle different types of errors in your code and implement retry logic.
- **LLMManager**: Automatic failover across multiple AWS regions with configurable retry strategies, e.g., if you request fails in one AWS region, it is moved to another region.

### ⚡ **Built-in Parallel Processing**
- **Native API**: Sequential processing only
- **LLMManager**: Concurrent execution across multiple models and regions; this is particularly important for any kind of batch processing or when throttling becomes an issue.

### 🛡️ **Enhanced Error Handling & Reliability**
- **Native API**: Basic error responses, no automatic retries
- **LLMManager**: Comprehensive error handling, exponential backoff, and feature fallback

### 📊 **Rich Response Management**
- **Native API**: Raw response dictionaries, i.e., you have to parse and understand the JSON structure from Bedrock.
- **LLMManager**: Structured response objects with metadata, utilities, and validation that provide data access through typed functions.

## ✨ Features

### 🏗️ **Fluent MessageBuilder**
- **Intuitive API**: Chain methods to build complex multi-modal messages
- **Automatic Format Detection**: Intelligent file type detection from content and filenames
- **Multi-Modal Support**: Seamlessly combine text, images, documents, and videos
- **Built-in Validation**: Automatic content validation and size limit enforcement
- **Type Safety**: Comprehensive enums for formats, roles, and content types

### 🔄 **Advanced Reliability**
- **Multi-Model Support**: Work with multiple LLM models simultaneously with automatic fallback
- **Multi-Region Failover**: Automatic failover across AWS regions with intelligent routing
- **Intelligent Retry Logic**: Exponential backoff with configurable retry strategies
- **Feature Fallback**: Graceful degradation when advanced features aren't supported

### ⚡ **Performance & Scalability**
- **Parallel Processing**: Execute multiple requests concurrently across regions
- **Load Balancing**: Intelligent distribution across available resources
- **Connection Pooling**: Efficient resource management for high-throughput scenarios
- **Streaming Support**: Real-time response streaming for long-form content

### 🛡️ **Security & Authentication**
- **Flexible Authentication**: Support for AWS profiles, credentials, IAM roles, and auto-detection
- **Response Validation**: Optional content validation with custom validation functions
- **Guardrail Integration**: Full support for AWS Bedrock guardrails
- **Secure File Handling**: Safe processing of uploaded files with size and format validation

### 📊 **Comprehensive Monitoring**
- **Rich Response Objects**: Detailed response metadata with performance metrics
- **Execution Statistics**: Request timing, token usage, and success rates
- **Error Tracking**: Comprehensive error logging with retry attempt details
- **Validation Reporting**: Detailed validation results and failure analysis

## Installation

### From PyPI (Recommended)

```bash
pip install bestehorn-llmmanager
```

### From Source (Development)

For development or integration into other projects:

```bash
git clone https://github.com/Bestehorn/LLMManager.git
cd LLMManager
pip install -e .
```

### With Development Dependencies

```bash
pip install -e .[dev]
```

## 🚀 Quick Start

### MessageBuilder vs. Native API Comparison

**❌ With Native AWS Bedrock Converse API:**
```python
import boto3
import base64

# Complex manual message construction
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

# Manual dictionary construction - error-prone and verbose
with open("document.pdf", "rb") as f:
    doc_bytes = f.read()

messages = [
    {
        "role": "user",
        "content": [
            {"text": "Analyze this document:"},
            {
                "document": {
                    "name": "document.pdf",
                    "format": "pdf",  # Must specify format manually
                    "source": {"bytes": doc_bytes}
                }
            }
        ]
    }
]

# Basic API call with no error handling or retry logic
try:
    response = bedrock.converse(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",  # Must specify exact model ID
        messages=messages
    )
    content = response['output']['message']['content'][0]['text']
except Exception as e:
    print(f"Error: {e}")  # Limited error information
```

**✅ With LLMManager and MessageBuilder:**
```python
from bestehorn_llmmanager import LLMManager, create_user_message

# Simple initialization with friendly model names and multi-region support
manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],  # Friendly names, automatic fallback
    regions=["us-east-1", "us-west-2"]  # Multi-region with automatic failover
)

# Fluent message building with automatic format detection
message = create_user_message()\
    .add_text("Analyze this document:")\
    .add_local_document("document.pdf")\
    .build()  # Automatically detects PDF format from file extension

# Enhanced API call with comprehensive error handling
response = manager.converse(messages=[message])

if response.success:
    print(response.get_content())
    print(f"Used model: {response.model_used} in region: {response.region_used}")
    print(f"Duration: {response.total_duration_ms}ms")
else:
    print(f"Request failed after {len(response.attempts)} attempts")
    print(f"Last error: {response.get_last_error()}")
```

### 🏗️ MessageBuilder: Intelligent Multi-Modal Message Construction

The MessageBuilder provides a fluent, type-safe interface for building complex messages with automatic format detection:

#### Basic Text Messages
```python
from bestehorn_llmmanager import create_user_message, create_assistant_message

# Simple text message
message = create_user_message().add_text("Hello, how are you?").build()

# Multi-paragraph text
message = create_user_message()\
    .add_text("First paragraph of my question.")\
    .add_text("Second paragraph with more details.")\
    .build()
```

#### Multi-Modal Messages with Automatic Format Detection
```python
# Combine text, images, and documents in one fluent chain
message = create_user_message()\
    .add_text("Please analyze this data visualization and the underlying data:")\
    .add_local_image("charts/sales_chart.png")  # Auto-detects PNG format\
    .add_local_document("data/sales_data.xlsx")  # Auto-detects Excel format\
    .add_text("What trends do you notice and what recommendations do you have?")\
    .build()

# The MessageBuilder automatically:
# - Detects file formats from extensions and content
# - Validates file sizes and formats
# - Handles file reading and encoding
# - Creates proper AWS Bedrock message structure
```

#### File Format Detection Capabilities
```python
from bestehorn_llmmanager import ImageFormatEnum, DocumentFormatEnum, VideoFormatEnum

# Automatic detection from file extensions
message = create_user_message()\
    .add_local_image("photo.jpg")     # Detects JPEG\
    .add_local_image("diagram.png")   # Detects PNG\
    .add_local_document("report.pdf") # Detects PDF\
    .add_local_document("data.csv")   # Detects CSV\
    .build()

# Manual format specification when needed
message = create_user_message()\
    .add_image_bytes(image_data, format=ImageFormatEnum.WEBP)\
    .add_document_bytes(doc_data, format=DocumentFormatEnum.DOCX, name="Proposal")\
    .build()

# Supported formats:
# Images: JPEG, PNG, GIF, WEBP
# Documents: PDF, CSV, DOC, DOCX, XLS, XLSX, HTML, TXT, MD  
# Videos: MP4, MOV, AVI, WEBM, MKV
```

### ⚡ Parallel Processing with MessageBuilder

**❌ Native API Limitation:** Sequential processing only
```python
# With native API, you must process requests one by one
results = []
for question in questions:
    response = bedrock.converse(modelId="...", messages=[{"role": "user", "content": [{"text": question}]}])
    results.append(response)  # Slow, sequential processing
```

**✅ LLMManager Advantage:** Concurrent multi-region processing
```python
from bestehorn_llmmanager import ParallelLLMManager, create_user_message
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

# Initialize parallel manager with multiple regions for high availability
parallel_manager = ParallelLLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2", "eu-west-1"]
)

# Create multiple requests using MessageBuilder
questions = ["What is AI?", "Explain machine learning", "How does neural network training work?"]

requests = []
for i, question in enumerate(questions):
    message = create_user_message().add_text(question).build()
    requests.append(BedrockConverseRequest(
        request_id=f"question-{i}",
        messages=[message]
    ))

# Execute all requests in parallel across multiple regions
parallel_response = parallel_manager.converse_parallel(
    requests=requests,
    target_regions_per_request=2  # Use 2 regions per request for redundancy
)

# Get comprehensive results
print(f"Success rate: {parallel_response.get_success_rate():.1%}")
print(f"Total duration: {parallel_response.total_duration_ms}ms")
print(f"Average per request: {parallel_response.parallel_execution_stats.average_request_duration_ms:.1f}ms")

# Access individual results
for request_id, response in parallel_response.get_successful_responses().items():
    print(f"{request_id}: {response.get_content()}")
    print(f"  Model: {response.model_used}, Region: {response.region_used}")
```

### 🔄 Advanced MessageBuilder Patterns

#### Conversation Context Management
```python
from bestehorn_llmmanager import create_user_message, create_assistant_message

# Build a multi-turn conversation with context
conversation = []

# Initial user message with image
user_msg1 = create_user_message()\
    .add_text("What's in this image?")\
    .add_local_image("photo.jpg")\
    .build()
conversation.append(user_msg1)

# Simulate assistant response (or use actual response)
assistant_msg1 = create_assistant_message()\
    .add_text("I can see a beautiful landscape with mountains and a lake.")\
    .build()
conversation.append(assistant_msg1)

# Follow-up question maintaining context
user_msg2 = create_user_message()\
    .add_text("What time of day do you think this photo was taken? Please be specific about the lighting conditions.")\
    .build()
conversation.append(user_msg2)

# Process the entire conversation
response = manager.converse(messages=conversation)
```

#### Batch Document Processing
```python
import os
from pathlib import Path

# Process multiple documents with detailed analysis
documents_dir = Path("documents")
document_files = list(documents_dir.glob("*.pdf"))

# Create parallel requests for document analysis
requests = []
for doc_file in document_files:
    message = create_user_message()\
        .add_text(f"Please provide a comprehensive analysis of this document, including:")\
        .add_text("1. Main topics and themes")\
        .add_text("2. Key findings or conclusions")\
        .add_text("3. Important data or statistics mentioned")\
        .add_text("4. Any recommendations or action items")\
        .add_local_document(str(doc_file), name=doc_file.stem)\
        .build()
    
    requests.append(BedrockConverseRequest(
        request_id=f"doc-analysis-{doc_file.stem}",
        messages=[message]
    ))

# Process all documents in parallel
parallel_response = parallel_manager.converse_parallel(requests=requests)

# Generate summary report
for request_id, response in parallel_response.get_successful_responses().items():
    doc_name = request_id.replace("doc-analysis-", "")
    print(f"\n=== Analysis of {doc_name} ===")
    print(response.get_content())
    print(f"Processing time: {response.total_duration_ms}ms")
```

#### Error Handling and Validation
```python
from bestehorn_llmmanager.bedrock.exceptions import RequestValidationError, LLMManagerError

try:
    # Build message with potential validation issues
    message = create_user_message()\
        .add_text("Analyze this large file:")\
        .add_local_document("very_large_file.pdf", max_size_mb=10.0)  # Increased limit\
        .build()
    
    response = manager.converse(messages=[message])
    
    if response.success:
        print(f"Analysis complete: {response.get_content()[:200]}...")
        
        # Check for warnings (non-fatal issues)
        warnings = response.get_warnings()
        if warnings:
            print(f"Warnings: {warnings}")
            
    else:
        # Detailed error analysis
        print(f"Request failed after {len(response.attempts)} attempts")
        print(f"Models tried: {[attempt.model_used for attempt in response.attempts]}")
        print(f"Regions tried: {[attempt.region_used for attempt in response.attempts]}")
        print(f"Final error: {response.get_last_error()}")

except RequestValidationError as e:
    print(f"Message validation failed: {e}")
    if hasattr(e, 'validation_errors'):
        for error in e.validation_errors:
            print(f"  - {error}")
            
except FileNotFoundError as e:
    print(f"File not found: {e}")
    
except LLMManagerError as e:
    print(f"LLM Manager error: {e}")
```

### With Authentication Configuration

```python
from bestehorn_llmmanager import LLMManager
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    AuthConfig, AuthenticationType
)

# Configure authentication
auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="my-aws-profile"
)

manager = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"],
    auth_config=auth_config
)
```

## Requirements

- Python 3.8+
- AWS credentials configured (AWS CLI, environment variables, or IAM roles)
- Internet access for initial model data download

### Dependencies

- `boto3>=1.28.0` - AWS SDK
- `beautifulsoup4>=4.12.0` - HTML parsing
- `requests>=2.31.0` - HTTP requests

## Configuration

### AWS Credentials

The library supports multiple authentication methods:

1. **AWS Profiles**: Use named profiles from `~/.aws/credentials`
2. **Environment Variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
3. **IAM Roles**: For EC2 instances or Lambda functions
4. **Default Credential Chain**: Standard AWS credential resolution

### Model Data

The library automatically downloads and caches AWS Bedrock model information on first use. This requires internet connectivity initially but uses cached data for subsequent runs.

## 🔧 Advanced Usage

### 🔄 Custom Retry Configuration

**❌ Native API Limitation:** No automatic retry logic
```python
# With native API, you must implement your own retry logic
import time
import random

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt + random.uniform(0, 1))
```

**✅ LLMManager Advantage:** Built-in intelligent retry with multiple strategies
```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    RetryConfig, RetryStrategy
)

# Configure sophisticated retry behavior
retry_config = RetryConfig(
    max_retries=5,                              # Maximum retry attempts
    retry_delay=1.0,                            # Initial delay (seconds)
    backoff_multiplier=2.0,                     # Exponential backoff
    max_retry_delay=60.0,                       # Maximum delay cap
    retry_strategy=RetryStrategy.REGION_FIRST,  # Try different regions first
    enable_feature_fallback=True                # Disable features if incompatible
)

manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    regions=["us-east-1", "us-west-2", "eu-west-1"],
    retry_config=retry_config
)

# The manager automatically handles:
# - Exponential backoff between retries
# - Region failover for high availability  
# - Model fallback if primary model fails
# - Feature degradation for compatibility issues
# - Detailed retry statistics and logging
```

### 🛡️ Response Validation

**❌ Native API Limitation:** No response validation capabilities
```python
# With native API, manual validation is required
response = bedrock.converse(...)
content = response['output']['message']['content'][0]['text']

# Manual validation logic
if "inappropriate" in content.lower():
    # Handle inappropriate content manually
    pass
```

**✅ LLMManager Advantage:** Comprehensive response validation system
```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    ResponseValidationConfig, ValidationResult
)

def custom_content_validator(response):
    """Custom validation function for response content."""
    content = response.get_content()
    
    # Check for empty responses
    if not content or len(content.strip()) < 10:
        return ValidationResult(
            success=False,
            error_message="Response too short or empty"
        )
    
    # Check for potentially harmful content
    harmful_keywords = ["violence", "illegal", "inappropriate"]
    if any(keyword in content.lower() for keyword in harmful_keywords):
        return ValidationResult(
            success=False,
            error_message="Response contains potentially harmful content",
            error_details={"flagged_content": content[:100]}
        )
    
    # Check for factual consistency (example)
    if "I don't know" in content and len(content) < 50:
        return ValidationResult(
            success=False,
            error_message="Response appears incomplete"
        )
    
    return ValidationResult(success=True)

# Configure validation
validation_config = ResponseValidationConfig(
    response_validation_function=custom_content_validator,
    response_validation_retries=3,               # Retry validation failures
    response_validation_delay=0.5                # Delay between validation retries
)

message = create_user_message().add_text("Tell me about AI safety").build()
response = manager.converse(
    messages=[message],
    response_validation_config=validation_config
)

# Check validation results
if response.had_validation_failures():
    print("Validation issues detected:")
    for error in response.get_validation_errors():
        print(f"  - {error['error_message']}")
```

### 📊 Rich Response Analysis

**❌ Native API Limitation:** Basic response dictionaries only
```python
# Native API provides minimal response information
response = bedrock.converse(...)
content = response['output']['message']['content'][0]['text']
usage = response.get('usage', {})
# Limited metadata available
```

**✅ LLMManager Advantage:** Comprehensive response objects with detailed metadata
```python
message = create_user_message().add_text("Explain quantum computing").build()
response = manager.converse(messages=[message])

# Rich response information
print(f"Success: {response.success}")
print(f"Content: {response.get_content()}")

# Performance metrics
print(f"Total duration: {response.total_duration_ms}ms")
print(f"Model used: {response.model_used}")
print(f"Region used: {response.region_used}")

# Token usage analysis
usage = response.get_usage()
if usage:
    print(f"Input tokens: {usage.get('inputTokens', 'N/A')}")
    print(f"Output tokens: {usage.get('outputTokens', 'N/A')}")
    print(f"Total tokens: {usage.get('totalTokens', 'N/A')}")

# Detailed execution metrics
metrics = response.get_metrics()
print(f"Request preparation time: {metrics.get('request_prep_ms', 'N/A')}ms")
print(f"Network latency: {metrics.get('network_latency_ms', 'N/A')}ms")

# Retry and error information
print(f"Total attempts: {len(response.attempts)}")
for i, attempt in enumerate(response.attempts):
    print(f"  Attempt {i+1}: {attempt.model_used} in {attempt.region_used}")
    if attempt.error:
        print(f"    Error: {attempt.error}")

# Stop reason analysis
stop_reason = response.get_stop_reason()
print(f"Stop reason: {stop_reason}")  # max_tokens, end_turn, tool_use, etc.

# Warnings and issues
warnings = response.get_warnings()
if warnings:
    print(f"Warnings: {warnings}")
```

### 🧪 Streaming Responses

**❌ Native API:** Basic streaming support
```python
# Native API streaming is limited
response = bedrock.converse_stream(...)
for chunk in response['stream']:
    if 'contentBlockDelta' in chunk:
        print(chunk['contentBlockDelta'].get('text', ''), end='')
```

**✅ LLMManager Advantage:** Enhanced streaming with MessageBuilder
```python
# Create streaming request with MessageBuilder
message = create_user_message()\
    .add_text("Write a detailed explanation of machine learning algorithms.")\
    .add_text("Include examples and use cases for each algorithm.")\
    .build()

# Stream response with enhanced error handling
try:
    stream_response = manager.converse_stream(messages=[message])
    
    print("Streaming response:")
    full_content = ""
    
    for chunk in stream_response:
        if chunk.get("contentBlockDelta"):
            delta = chunk["contentBlockDelta"]
            if "text" in delta:
                text_chunk = delta["text"]
                print(text_chunk, end="", flush=True)
                full_content += text_chunk
        
        # Handle tool use in streaming
        elif chunk.get("contentBlockStart"):
            block_start = chunk["contentBlockStart"]
            if "toolUse" in block_start:
                print(f"\n[Tool use started: {block_start['toolUse']['name']}]")
    
    print(f"\n\nStream completed. Total characters: {len(full_content)}")
    
except Exception as e:
    print(f"Streaming error: {e}")
    # Automatic fallback to non-streaming if needed
    fallback_response = manager.converse(messages=[messages])
    print(f"Fallback response: {fallback_response.get_content()}")
```

### 🔧 Tool Use Integration

**Native API:** Complex tool configuration
```python
# Manual tool definition with native API
tools = [
    {
        "toolSpec": {
            "name": "calculator",
            "description": "Perform mathematical calculations",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"}
                    },
                    "required": ["expression"]
                }
            }
        }
    }
]

tool_config = {"tools": tools}
```

**✅ LLMManager Enhancement:** Simplified tool integration with MessageBuilder
```python
# Define tools with enhanced configuration
def calculator_function(expression: str) -> str:
    """Safe calculator function."""
    try:
        # Simple expression evaluation (in practice, use a safe evaluator)
        result = eval(expression.replace('^', '**'))
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# Tool configuration
tool_config = {
    "tools": [
        {
            "toolSpec": {
                "name": "calculator",
                "description": "Perform basic mathematical calculations",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            }
        }
    ]
}

# Create message with tool request
message = create_user_message()\
    .add_text("Please calculate 25 * 37 + 15 and explain the result.")\
    .build()

response = manager.converse(
    messages=[message],
    tool_config=tool_config
)

# Handle tool use in response
if response.success:
    # Check for tool use in the response
    response_data = response.response_data
    content = response_data.get("output", {}).get("message", {}).get("content", [])
    
    for block in content:
        if "toolUse" in block:
            tool_use = block["toolUse"]
            tool_name = tool_use["name"]
            tool_input = tool_use["input"]
            tool_id = tool_use["toolUseId"]
            
            print(f"Tool called: {tool_name}")
            print(f"Input: {tool_input}")
            
            # Execute the tool function
            if tool_name == "calculator":
                result = calculator_function(tool_input["expression"])
                
                # Create tool result message
                tool_result_message = create_user_message()\
                    .add_tool_result(
                        tool_use_id=tool_id,
                        content=result,
                        status="success"
                    )\
                    .build()
                
                # Continue conversation with tool result
                final_response = manager.converse(messages=[
                    message,
                    response_data["output"]["message"],
                    tool_result_message
                ])
                
                print(f"Final response: {final_response.get_content()}")
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd bestehorn-llmmanager

# Install in editable mode with development dependencies
pip install -e .[dev]

# Run tests
pytest

# Run tests with coverage
pytest --cov=bestehorn_llmmanager
```

### Project Structure

```
bestehorn-llmmanager/
├── src/
│   └── bestehorn_llmmanager/
│       ├── __init__.py
│       ├── llm_manager.py
│       ├── parallel_llm_manager.py
│       └── bedrock/
├── test/
├── docs/
├── pyproject.toml
└── README.md
```

### Running Tests

```bash
# Unit tests only
pytest test/bestehorn_llmmanager/

# Integration tests (requires AWS credentials)
pytest test/integration/ -m integration

# All tests
pytest
```

## 📚 API Reference

### 🏗️ MessageBuilder API

The MessageBuilder provides a fluent interface for constructing multi-modal messages with automatic format detection.

#### Factory Functions
```python
from bestehorn_llmmanager import (
    create_user_message, create_assistant_message, 
    create_message, MessageBuilder, RolesEnum
)

# Convenience factories
create_user_message() -> ConverseMessageBuilder
create_assistant_message() -> ConverseMessageBuilder
create_message(role: RolesEnum) -> ConverseMessageBuilder

# Direct instantiation
MessageBuilder(role: RolesEnum) -> ConverseMessageBuilder
```

#### Core Methods

**Text Content**
```python
def add_text(self, text: str) -> 'ConverseMessageBuilder'
```
Add text content to the message. Text is automatically stripped of whitespace.

**Image Content**
```python
def add_image_bytes(
    self, bytes: bytes, 
    format: Optional[ImageFormatEnum] = None,
    filename: Optional[str] = None
) -> 'ConverseMessageBuilder'

def add_local_image(
    self, path_to_local_file: str,
    format: Optional[ImageFormatEnum] = None,
    max_size_mb: float = 3.75
) -> 'ConverseMessageBuilder'
```

**Document Content**
```python
def add_document_bytes(
    self, bytes: bytes,
    format: Optional[DocumentFormatEnum] = None,
    filename: Optional[str] = None,
    name: Optional[str] = None
) -> 'ConverseMessageBuilder'

def add_local_document(
    self, path_to_local_file: str,
    format: Optional[DocumentFormatEnum] = None,
    name: Optional[str] = None,
    max_size_mb: float = 4.5
) -> 'ConverseMessageBuilder'
```

**Video Content**
```python
def add_video_bytes(
    self, bytes: bytes,
    format: Optional[VideoFormatEnum] = None,
    filename: Optional[str] = None
) -> 'ConverseMessageBuilder'

def add_local_video(
    self, path_to_local_file: str,
    format: Optional[VideoFormatEnum] = None,
    max_size_mb: float = 100.0
) -> 'ConverseMessageBuilder'
```

**Build Message**
```python
def build(self) -> Dict[str, Any]
```
Build and return the AWS Bedrock-compatible message dictionary.

#### Supported Formats

**Images**: JPEG, PNG, GIF, WEBP  
**Documents**: PDF, CSV, DOC, DOCX, XLS, XLSX, HTML, TXT, MD  
**Videos**: MP4, MOV, AVI, WEBM, MKV

### 🔧 LLMManager

Primary interface for single AWS Bedrock requests with enhanced reliability.

#### Constructor
```python
LLMManager(
    models: List[str],                                    # Model names/IDs
    regions: List[str],                                   # AWS regions
    auth_config: Optional[AuthConfig] = None,             # Authentication config
    retry_config: Optional[RetryConfig] = None,           # Retry configuration
    default_inference_config: Optional[Dict] = None,     # Default inference params
    timeout: int = 300,                                   # Request timeout (seconds)
    log_level: Union[int, str] = logging.WARNING         # Logging level
)
```

#### Core Methods
```python
def converse(
    self, messages: List[Dict[str, Any]],
    system: Optional[List[Dict[str, str]]] = None,
    inference_config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> BedrockResponse

def converse_stream(
    self, messages: List[Dict[str, Any]],
    **kwargs
) -> StreamingResponse

def validate_configuration(self) -> Dict[str, Any]
def refresh_model_data(self) -> None
def get_available_models(self) -> List[str]
def get_available_regions(self) -> List[str]
```

### ⚡ ParallelLLMManager

Interface for concurrent multi-region processing.

#### Constructor
```python
ParallelLLMManager(
    models: List[str],                                    # Model names/IDs
    regions: List[str],                                   # AWS regions
    parallel_config: Optional[ParallelProcessingConfig] = None,
    **kwargs                                              # Same as LLMManager
)
```

#### Core Methods
```python
def converse_parallel(
    self, requests: List[BedrockConverseRequest],
    target_regions_per_request: int = 2,
    response_validation_config: Optional[ResponseValidationConfig] = None
) -> ParallelResponse

def get_parallel_config(self) -> ParallelProcessingConfig
```

### 📊 Response Objects

#### BedrockResponse
```python
# Status and content
response.success: bool
response.get_content() -> str
response.get_usage() -> Dict[str, Any]
response.get_stop_reason() -> str

# Execution details
response.model_used: str
response.region_used: str
response.total_duration_ms: float
response.attempts: List[RequestAttempt]

# Error handling
response.get_last_error() -> Exception
response.get_all_errors() -> List[Exception]
response.get_warnings() -> List[str]

# Validation (if used)
response.had_validation_failures() -> bool
response.get_validation_errors() -> List[Dict]

# Serialization
response.to_dict() -> Dict[str, Any]
response.to_json(indent: int = None) -> str
```

#### ParallelResponse
```python
# Overall results
parallel_response.success: bool
parallel_response.get_success_rate() -> float
parallel_response.total_duration_ms: float

# Individual responses
parallel_response.request_responses: Dict[str, BedrockResponse]
parallel_response.get_successful_responses() -> Dict[str, BedrockResponse]
parallel_response.failed_requests: List[str]

# Statistics
parallel_response.parallel_execution_stats.total_requests: int
parallel_response.parallel_execution_stats.successful_requests: int
parallel_response.parallel_execution_stats.average_request_duration_ms: float
```

### 🔧 Configuration Classes

#### AuthConfig
```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    AuthConfig, AuthenticationType
)

AuthConfig(
    auth_type: AuthenticationType,                # PROFILE, CREDENTIALS, IAM_ROLE, AUTO
    profile_name: Optional[str] = None,           # AWS profile name
    access_key_id: Optional[str] = None,          # AWS access key
    secret_access_key: Optional[str] = None,      # AWS secret key
    session_token: Optional[str] = None,          # AWS session token
    region: Optional[str] = None                  # Default region
)
```

#### RetryConfig
```python
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    RetryConfig, RetryStrategy
)

RetryConfig(
    max_retries: int = 3,                         # Maximum retry attempts
    retry_delay: float = 1.0,                     # Initial delay (seconds)
    backoff_multiplier: float = 2.0,              # Exponential backoff multiplier
    max_retry_delay: float = 60.0,                # Maximum delay cap
    retry_strategy: RetryStrategy = RetryStrategy.REGION_FIRST,
    enable_feature_fallback: bool = True          # Disable features on errors
)
```

### 🎯 Enums

#### MessageBuilder Enums
```python
from bestehorn_llmmanager import (
    RolesEnum, ImageFormatEnum, 
    DocumentFormatEnum, VideoFormatEnum
)

class RolesEnum(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class ImageFormatEnum(str, Enum):
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"

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

class VideoFormatEnum(str, Enum):
    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"
    WEBM = "webm"
    MKV = "mkv"
```

## 🎯 Complete Example: Multi-Modal Document Analysis

Here's a comprehensive example showcasing the library's key features:

```python
from bestehorn_llmmanager import (
    LLMManager, ParallelLLMManager, create_user_message,
    AuthConfig, AuthenticationType, RetryConfig, RetryStrategy
)
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import ResponseValidationConfig, ValidationResult

# Configure authentication and retry behavior
auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="bedrock-profile"
)

retry_config = RetryConfig(
    max_retries=5,
    retry_strategy=RetryStrategy.REGION_FIRST,
    enable_feature_fallback=True
)

# Custom response validation
def validate_analysis_quality(response):
    content = response.get_content()
    if len(content) < 100:
        return ValidationResult(
            success=False,
            error_message="Analysis too brief"
        )
    return ValidationResult(success=True)

validation_config = ResponseValidationConfig(
    response_validation_function=validate_analysis_quality,
    response_validation_retries=2
)

# Initialize managers
single_manager = LLMManager(
    models=["Claude 3 Sonnet", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2", "eu-west-1"],
    auth_config=auth_config,
    retry_config=retry_config
)

parallel_manager = ParallelLLMManager(
    models=["Claude 3 Sonnet", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2", "eu-west-1"],
    auth_config=auth_config,
    retry_config=retry_config
)

# Single request with multi-modal content
message = create_user_message()\
    .add_text("Please analyze this comprehensive business report:")\
    .add_local_document("reports/quarterly_report.pdf")\
    .add_text("Focus on these key areas:")\
    .add_text("1. Financial performance trends")\
    .add_text("2. Market position analysis")\
    .add_text("3. Strategic recommendations")\
    .add_local_image("charts/performance_chart.png")\
    .add_text("How does the visual data support the written analysis?")\
    .build()

# Execute single request with validation
response = single_manager.converse(
    messages=[message],
    response_validation_config=validation_config
)

if response.success:
    print(f"Analysis completed in {response.total_duration_ms}ms")
    print(f"Using {response.model_used} in {response.region_used}")
    print(f"Content: {response.get_content()[:500]}...")
    
    # Check token usage
    usage = response.get_usage()
    if usage:
        print(f"Tokens used: {usage.get('totalTokens', 'N/A')}")
else:
    print(f"Analysis failed: {response.get_last_error()}")

# Parallel processing for multiple documents
documents = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
requests = []

for i, doc in enumerate(documents):
    message = create_user_message()\
        .add_text(f"Provide a executive summary of this document:")\
        .add_local_document(doc)\
        .build()
    
    requests.append(BedrockConverseRequest(
        request_id=f"summary-{i}",
        messages=[message]
    ))

# Execute in parallel with high availability
parallel_response = parallel_manager.converse_parallel(
    requests=requests,
    target_regions_per_request=2,
    response_validation_config=validation_config
)

print(f"Parallel execution results:")
print(f"Success rate: {parallel_response.get_success_rate():.1%}")
print(f"Total time: {parallel_response.total_duration_ms}ms")
print(f"Average per request: {parallel_response.parallel_execution_stats.average_request_duration_ms:.1f}ms")

# Process results
for request_id, response in parallel_response.get_successful_responses().items():
    print(f"\n{request_id}: {response.get_content()[:200]}...")
```

This comprehensive example demonstrates:
- **Multi-modal message construction** with text, documents, and images
- **Automatic format detection** for uploaded files
- **Multi-region failover** with intelligent retry logic
- **Response validation** with custom validation functions
- **Parallel processing** across multiple models and regions
- **Detailed performance monitoring** and error handling
- **Flexible authentication** configuration

## Error Handling

The library provides comprehensive error handling with specific exception types:

- `LLMManagerError`: Base exception for all library errors
- `ConfigurationError`: Configuration-related errors
- `AuthenticationError`: AWS authentication failures
- `RequestValidationError`: Request validation failures
- `RetryExhaustedError`: All retry attempts failed
- `ParallelProcessingError`: Parallel execution errors

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Support

For issues and questions:
- Check the documentation in the `docs/` directory
- Review existing issues on GitHub
- Create a new issue with detailed information about your problem
