# LLMManager by Markus Bestehorn

[![PyPI version](https://img.shields.io/pypi/v/bestehorn-llmmanager.svg)](https://pypi.org/project/bestehorn-llmmanager/)
[![Python Versions](https://img.shields.io/pypi/pyversions/bestehorn-llmmanager.svg)](https://pypi.org/project/bestehorn-llmmanager/)
[![Build Status](https://github.com/Bestehorn/LLMManager/actions/workflows/ci.yml/badge.svg)](https://github.com/Bestehorn/LLMManager/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Bestehorn/LLMManager/graph/badge.svg?token=YOUR_CODECOV_TOKEN)](https://codecov.io/gh/Bestehorn/LLMManager)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**A comprehensive Python library that simplifies and enhances AWS Bedrock Converse API interactions with intelligent message building, automatic file format detection, multi-modal support, streaming capabilities, caching, and advanced reliability features.**

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- AWS credentials configured (AWS CLI, environment variables, or IAM roles)

### Installation & Basic Usage

```python
# Install the package
pip install bestehorn-llmmanager

# Simple example - get started in 5 lines
from bestehorn_llmmanager import LLMManager, create_user_message

manager = LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])
message = create_user_message().add_text("Explain quantum computing").build()
response = manager.converse(messages=[message])
print(response.get_content())
```

## 🎯 Key Simplifications Over Native AWS Bedrock Converse API

This library was built to simplify the [standard AWS Bedrock Converse API](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html). 
While some of these simplifications come at a loss of flexibility, for most use cases, the code becomes cleaner, less prone to errors and easier to understand when it is based on the abstractions provided in this package: 

### 🏗️ **Fluent MessageBuilder with Automatic Format Detection**
- **Native API**: Manual message dictionary construction with complex nested structures resulting in complex JSON
- **LLMManager**: Intuitive fluent interface with automatic file type detection and validation that hides the intricacies of building message JSON for Bedrock's converse API.

### 🔄 **Intelligent Multi-Region Failover**
- **Native API**: Single region, manual error handling required, i.e., you have to handle different types of errors in your code and implement retry logic.
- **LLMManager**: Automatic failover across multiple AWS regions with configurable retry strategies, e.g., if you request fails in one AWS region, it is moved to another region.

### ⚡ **Built-in Parallel Processing**
- **Native API**: Sequential processing only
- **LLMManager**: Concurrent execution across multiple models and regions; this is particularly important for any kind of batch processing to reduce inference time.

### 🛡️ **Enhanced Error Handling & Reliability**
- **Native API**: Basic error responses, no automatic retries
- **LLMManager**: Comprehensive error handling, exponential backoff, and feature fallback

### 📊 **Rich Response Management**
- **Native API**: Raw response dictionaries, i.e., you have to parse and understand the JSON structure from Bedrock.
- **LLMManager**: Structured response objects with metadata, utilities, and validation that provide data access through typed functions.

### 🌊 **Real-Time Streaming Support**
- **Native API**: Basic streaming with manual chunk handling
- **LLMManager**: Enhanced streaming with automatic retry, recovery, and real-time display utilities

### 💾 **Intelligent Caching**
- **Native API**: Manual cache point management required
- **LLMManager**: Automatic cache optimization with configurable strategies for cost reduction

I have implemented this set of functions over time while working on projects and demos using Amazon Bedrock.
One of the key use cases that started the implementation of this project has been: I have a prompt and I do not care where the prompt gets executed, I just want to make sure I get a response and I do not want to handle any temporal issues such as malformed responses from LLMs or throttling.
It helped me to avoid common mistakes and sources for errors when using the [standard AWS Bedrock Converse API](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html).

⚠️**Important**: The code in this repository comes with no guarentees or liabilities. It is not intended for production use, but rather as an inspiration for implementing your own logic for the Bedrock converse API in production environments.

Quick note on the package name: As there are other packages (public & private) that are named "LLMManager", I have chosen to prefix the name of this package with my last name as I am sure there are no other packages with this name.
If this is an issue, feel free to contact me and propose another name.

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

### 🌊 **Streaming Capabilities**
- **Real-Time Output**: See responses as they're generated with `converse_stream()`
- **Automatic Recovery**: Stream interruption detection and intelligent retry
- **Rich Metadata**: Streaming performance metrics and token usage tracking
- **Display Utilities**: Built-in utilities for streaming visualization

### 💾 **Caching Support**
- **Automatic Optimization**: Intelligent cache point placement based on content patterns
- **Cost Reduction**: Up to 90% reduction in token costs for repetitive prompts
- **Simple Configuration**: Enable with `CacheConfig(enabled=True)`
- **Flexible Strategies**: Conservative, Aggressive, or Custom caching approaches
- **MessageBuilder Integration**: Seamless cache control with `add_cache_point()`

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

## 🚀 Quick Start Examples

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

In this example above, you have to load the document and then construct the JSON for the message to get it passed to Bedrock's converse API in a single region.
Once the response returns, you have to spcifically know where the answer is (which is simple for this straightforward example) and for complex usage scenarios, you will need complex logic to access the right response.
Furthermore, you have to specifically know the model ID of the model which you want to access.
If you want to access the model directly (as above), you will have to find the right model in the [AWS documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html).
For cross-region inference (CRIS), this becomes even more complex as you have to choose the right inference/model ID for the CRIS profile you want to use, e.g., different CRIS profiles for the model in the US or EU from the [AWS documentation page](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html#inference-profiles-support-system).
If the request to Bedrock fails, you get a relatively generic Exception object which you have to handle and there is no automated retry with this approach or other ways to handle errors gracefully.
The code below covers all of this and more using the LLM Manager:

**✅ With LLMManager and MessageBuilder:**
```python
from bestehorn_llmmanager import LLMManager, create_user_message

# Simple initialization with friendly model names and multi-region support
manager = LLMManager(
    models=["Claude 3 Haiku", "Claude 3 Sonnet"],  # Friendly names, automatic fallback
    regions=["us-east-1", "us-west-2", "eu-west-1"]  # Multi-region with automatic failover
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

First an foremost, you simply select the models you want to use with the models parameter and the LLM Manager will use either CRIS or direct access (with preference to CRIS).
You do not have to read documentation pages or find model IDs to use model as the LLM Manager has a built-in parsing mechanism for these documentation pages to load the model IDs and inference profiles automatically.
The list of regions gives flexibility and the default converse API does not give the option to execute prompts in various regions. 
The loading of the PDF document happens simply by pointing to the local file, the detection of the content will also happen automatically.
As a response from Bedrock, you always get a BedrockResponse object which allows you to easily determine if the request was sucessful or not.
The access to the response's text does not require knowing the JSON structure and reduces parsing of JSON. 

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

### 🌊 Streaming Responses

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
    fallback_response = manager.converse(messages=[message])
    print(f"Fallback response: {fallback_response.get_content()}")
```

### 💾 Caching for Cost Optimization

**❌ Native API:** Manual cache point management
```python
# With native API, manual cache point construction required
messages = [{
    "role": "user",
    "content": [
        {"text": "Analyze these images..."},
        {"image": {"format": "jpeg", "source": {"bytes": image_bytes}}},
        {"cachePoint": {"type": "default"}},  # Manual placement
        {"text": "What do you see?"}
    ]
}]
```

**✅ LLMManager Advantage:** Automatic cache optimization
```python
from bestehorn_llmmanager.bedrock.models.cache_structures import CacheConfig, CacheStrategy

# Enable caching for dramatic cost reduction
cache_config = CacheConfig(
    enabled=True,
    strategy=CacheStrategy.CONSERVATIVE  # Automatic optimization
)

manager = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"],
    cache_config=cache_config
)

# Build message with automatic cache optimization
message = create_user_message()\
    .add_text("Analyze these architectural images...")  # Cached after first use\
    .add_local_image("building1.jpg")                  # Cached\
    .add_local_image("building2.jpg")                  # Cached\
    .add_cache_point()  # Optional explicit control\
    .add_text("Focus on the Gothic elements")          # Unique per request\
    .build()

# First request: writes to cache
response1 = manager.converse(messages=[message])

# Subsequent requests: reads from cache (90% cost reduction!)
for i in range(9):
    unique_message = create_user_message()\
        .add_text("Analyze these architectural images...")\
        .add_local_image("building1.jpg")\
        .add_local_image("building2.jpg")\
        .add_cache_point()\
        .add_text(f"Focus on aspect {i+2}")  # Different question each time\
        .build()
    
    response = manager.converse(messages=[unique_message])
    print(f"Cache efficiency: {response.get_cache_efficiency()}")
```

### ⚡ Parallel Processing with MessageBuilder

**❌ Native API:** Sequential processing only
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

**❌ Native API:** No automatic retry logic
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

**✅ LLMManager Simplification:** Built-in intelligent retry with multiple strategies
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

**❌ Native API:** No response validation capabilities
```python
# With native API, manual validation is required
response = bedrock.converse(...)
content = response['output']['message']['content'][0]['text']

# Manual validation logic
if "inappropriate" in content.lower():
    # Handle inappropriate content manually
    pass
```

LLMs are inherently probabilistic in their responses, i.e., even with exactly the same prompt between to calls, responses from LLMs will differ.
When you need a specific format, e.g., you want a formatted JSON response for down-stream processing, then even if the prompt explicitly specifies the exact format of the JSON response, there is still a chance you get a malformed response.
In such cases, it is often advisable to just execute another request to obtain a compliant response from Bedrock.
With the default converse API, you have to handle this in your application code.
The LLM Manager gives you a way to handle this more elegantly by poiting to a validation function and having the LLM Manager retry if the validation function determines the response does not conform to the expected format.

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

In the example above, the validation config contains a custom-validation function that checks the content of the message for various errors: length of the response, illegal keywowrds and completeness.
This function is then passed as a parameter and used before the call from the LLM Manager converse() function returns.
In case of errors, the LLM Manager will try to get a valid response before returning.
If you need a JSON
