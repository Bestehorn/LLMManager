# MessageBuilder Documentation

## Overview

The MessageBuilder system provides a fluent interface for constructing AWS Bedrock Converse API messages with automatic format detection, validation, and multi-modal support. It simplifies the creation of complex messages containing text, images, documents, and videos.

## Table of Contents

- [Quick Start](#quick-start)
- [Factory Functions](#factory-functions)
- [Core Features](#core-features)
- [Content Types](#content-types)
- [Auto-Detection](#auto-detection)
- [Path-Based Methods](#path-based-methods)
- [Validation and Limits](#validation-and-limits)
- [Error Handling](#error-handling)
- [Integration with LLMManager](#integration-with-llmmanager)
- [Examples](#examples)
- [API Reference](#api-reference)

## Quick Start

```python
from bedrock.models.message_builder_factory import create_user_message

# Simple text message
message = create_user_message() \
    .add_text("Hello, how can you help me today?") \
    .build()

# Multi-modal message with auto-detection
message = create_user_message() \
    .add_text("Please analyze this image and document:") \
    .add_local_image(path_to_local_file="photo.jpg") \
    .add_local_document(path_to_local_file="report.pdf") \
    .build()
```

## Factory Functions

### `create_message(role: RolesEnum)`
Creates a message builder with the specified role.

### `create_user_message()`
Convenience function for creating user messages. Equivalent to `create_message(RolesEnum.USER)`.

### `create_assistant_message()`
Convenience function for creating assistant messages. Equivalent to `create_message(RolesEnum.ASSISTANT)`.

## Core Features

### 🏗️ Fluent Interface
Chain methods together for intuitive message construction:

```python
message = create_user_message() \
    .add_text("Please analyze this content:") \
    .add_image_bytes(image_data, filename="photo.jpg") \
    .add_document_bytes(pdf_data, filename="report.pdf") \
    .build()
```

### 🔍 Automatic Format Detection
The system automatically detects file formats using:
- **Magic bytes analysis**: Analyzes file content signatures
- **File extension mapping**: Uses filename extensions as hints
- **Combined detection**: Merges both methods for high confidence

### 🛡️ Built-in Validation
- Content size limits and warnings
- Format compatibility checking
- Maximum content blocks per message
- Comprehensive error reporting

### 🎯 Multi-Modal Support
Support for multiple content types in a single message:
- Text content
- Images (JPEG, PNG, GIF, WebP)
- Documents (PDF, DOC/DOCX, XLS/XLSX, CSV, HTML, TXT, MD)
- Videos (MP4, MOV, AVI, WebM, MKV)

## Content Types

### Text Content
```python
builder.add_text("Your text content here")
```

### Image Content
```python
# Using bytes with auto-detection
builder.add_image_bytes(
    bytes=image_data,
    filename="photo.jpg"  # Optional, helps with detection
)

# Using bytes with explicit format
from bedrock.models.message_builder_enums import ImageFormatEnum
builder.add_image_bytes(
    bytes=image_data,
    format=ImageFormatEnum.JPEG
)

# Using local file path (recommended)
builder.add_local_image(
    path_to_local_file="path/to/image.jpg",
    max_size_mb=3.75  # Optional size limit
)
```

### Document Content
```python
# Using bytes
builder.add_document_bytes(
    bytes=doc_data,
    filename="report.pdf",
    name="Financial Report"  # Optional display name
)

# Using local file path (recommended)
builder.add_local_document(
    path_to_local_file="path/to/document.pdf",
    name="Financial Report",  # Optional display name
    max_size_mb=4.5  # Optional size limit
)
```

### Video Content
```python
# Using bytes
builder.add_video_bytes(
    bytes=video_data,
    filename="demo.mp4"
)

# Using local file path (recommended)
builder.add_local_video(
    path_to_local_file="path/to/video.mp4",
    max_size_mb=100.0  # Optional size limit
)
```

## Auto-Detection

The MessageBuilder uses a sophisticated detection system that combines multiple strategies:

### Detection Methods
1. **Extension-based**: Fast detection using file extensions
2. **Content-based**: Accurate detection using magic bytes
3. **Combined**: Merges both methods for optimal results

### Magic Bytes Supported
- **Images**: JPEG signatures, PNG signature, GIF signatures, WebP RIFF format
- **Documents**: PDF signature, ZIP-based Office formats, legacy Office formats, HTML tags
- **Videos**: MP4/MOV containers, AVI RIFF format, WebM/MKV EBML format

### Confidence Levels
- **High (0.95)**: Both methods agree or strong content signature
- **Medium (0.75)**: Single method or partial agreement
- **Low (0.50)**: Fallback detection

## Path-Based Methods

New convenience methods for working with local files:

### Benefits
- **Simplified API**: No need to manually read files
- **Automatic detection**: Format detection from both content and filename
- **Size validation**: Built-in file size checking
- **Error handling**: Comprehensive file access error reporting

### Comparison

**Traditional bytes approach**:
```python
def read_image_bytes(image_path: str) -> bytes:
    with open(image_path, "rb") as f:
        return f.read()

image_bytes = read_image_bytes("photo.jpg")
message = create_user_message() \
    .add_image_bytes(bytes=image_bytes, filename="photo.jpg") \
    .build()
```

**Path-based approach**:
```python
message = create_user_message() \
    .add_local_image(path_to_local_file="photo.jpg") \
    .build()
```

## Validation and Limits

### Content Size Limits
- **Images**: 3.75 MB (3,750,000 bytes)
- **Documents**: 4.5 MB (4,500,000 bytes)  
- **Videos**: 100 MB (100,000,000 bytes)

### Other Limits
- **Content blocks per message**: 100
- **Magic bytes read size**: 64 bytes
- **ZIP header read size**: 1024 bytes (for Office formats)

### Warning Thresholds
- Size warnings at 80% of limits
- Content block warnings at 80% of limit

## Error Handling

### Exception Types
- `RequestValidationError`: Validation failures, size limits, format issues
- `FileNotFoundError`: File access issues with path-based methods
- `ValueError`: Invalid parameters or configurations

### Common Error Scenarios
```python
try:
    message = create_user_message() \
        .add_local_image("nonexistent.jpg") \
        .build()
except FileNotFoundError as e:
    print(f"File not found: {e}")
except RequestValidationError as e:
    print(f"Validation error: {e}")
```

## Integration with LLMManager

MessageBuilder creates messages compatible with LLMManager:

```python
from LLMManager import LLMManager
from bedrock.models.message_builder_factory import create_user_message

# Create LLMManager instance
manager = LLMManager(models=["Claude 3.5 Sonnet v2"], regions=["us-east-1"])

# Build message
message = create_user_message() \
    .add_text("Analyze this image:") \
    .add_local_image("photo.jpg") \
    .build()

# Send to LLM
response = manager.converse(messages=[message])
```

## Examples

### Basic Text Message
```python
message = create_user_message() \
    .add_text("Hello! Please introduce yourself.") \
    .build()
```

### Image Analysis
```python
message = create_user_message() \
    .add_text("Please analyze this image in detail:") \
    .add_local_image(
        path_to_local_file="images/photo.jpg",
        max_size_mb=5.0
    ) \
    .build()
```

### Multi-Image Comparison
```python
message = create_user_message() \
    .add_text("Compare these two images:") \
    .add_local_image("image1.jpg") \
    .add_local_image("image2.jpg") \
    .build()
```

### Document Analysis
```python
message = create_user_message() \
    .add_text("Summarize this document:") \
    .add_local_document(
        path_to_local_file="report.pdf",
        name="Financial Report",
        max_size_mb=5.0
    ) \
    .build()
```

### Video Analysis
```python
message = create_user_message() \
    .add_text("Describe what happens in this video:") \
    .add_local_video(
        path_to_local_file="demo.mp4",
        max_size_mb=150.0
    ) \
    .build()
```

### Mixed Content Types
```python
# Using both path-based and bytes-based methods
with open("document.pdf", "rb") as f:
    doc_bytes = f.read()

message = create_user_message() \
    .add_text("Analyze both the image and document:") \
    .add_local_image("photo.jpg") \
    .add_document_bytes(doc_bytes, filename="document.pdf") \
    .build()
```

### Complex Multi-Modal Message
```python
message = create_user_message() \
    .add_text("You are a professional analyst. Here's reference material:") \
    .add_local_document("guidelines.pdf", name="Analysis Guidelines") \
    .add_text("Now analyze this content:") \
    .add_local_image("chart.png") \
    .add_local_video("presentation.mp4") \
    .add_text("Provide comprehensive analysis using the guidelines.") \
    .build()
```

## API Reference

### ConverseMessageBuilder

#### Constructor
```python
ConverseMessageBuilder(role: RolesEnum)
```

#### Text Methods
```python
add_text(text: str) -> ConverseMessageBuilder
```

#### Image Methods
```python
add_image_bytes(
    bytes: bytes,
    format: Optional[ImageFormatEnum] = None,
    filename: Optional[str] = None
) -> ConverseMessageBuilder

add_local_image(
    path_to_local_file: str,
    format: Optional[ImageFormatEnum] = None,
    max_size_mb: float = 3.75
) -> ConverseMessageBuilder
```

#### Document Methods
```python
add_document_bytes(
    bytes: bytes,
    format: Optional[DocumentFormatEnum] = None,
    filename: Optional[str] = None,
    name: Optional[str] = None
) -> ConverseMessageBuilder

add_local_document(
    path_to_local_file: str,
    format: Optional[DocumentFormatEnum] = None,
    name: Optional[str] = None,
    max_size_mb: float = 4.5
) -> ConverseMessageBuilder
```

#### Video Methods
```python
add_video_bytes(
    bytes: bytes,
    format: Optional[VideoFormatEnum] = None,
    filename: Optional[str] = None
) -> ConverseMessageBuilder

add_local_video(
    path_to_local_file: str,
    format: Optional[VideoFormatEnum] = None,
    max_size_mb: float = 100.0
) -> ConverseMessageBuilder
```

#### Build Method
```python
build() -> Dict[str, Any]
```

#### Properties
```python
role: RolesEnum
content_block_count: int
```

### Enums

#### RolesEnum
- `USER`: User message role
- `ASSISTANT`: Assistant message role

#### ImageFormatEnum
- `JPEG`: JPEG image format
- `PNG`: PNG image format
- `GIF`: GIF image format
- `WEBP`: WebP image format

#### DocumentFormatEnum
- `PDF`: PDF document format
- `CSV`: CSV document format
- `DOC`: Microsoft Word 97-2003 format
- `DOCX`: Microsoft Word 2007+ format
- `XLS`: Microsoft Excel 97-2003 format
- `XLSX`: Microsoft Excel 2007+ format
- `HTML`: HTML document format
- `TXT`: Plain text format
- `MD`: Markdown format

#### VideoFormatEnum
- `MP4`: MP4 video format
- `MOV`: QuickTime video format
- `AVI`: AVI video format
- `WEBM`: WebM video format
- `MKV`: Matroska video format

#### DetectionMethodEnum
- `EXTENSION`: Detection by file extension
- `CONTENT`: Detection by content analysis
- `COMBINED`: Combined detection method
- `MANUAL`: Manual format specification

### DetectionResult

Represents the result of file type detection:

```python
@dataclass(frozen=True)
class DetectionResult:
    detected_format: str
    confidence: float
    detection_method: DetectionMethodEnum
    filename: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[dict] = None
    
    @property
    def is_successful(self) -> bool
    
    @property
    def is_high_confidence(self) -> bool
```

## Best Practices

### 1. Use Path-Based Methods
Prefer `add_local_*` methods over `add_*_bytes` for local files:

```python
# ✅ Recommended
message = create_user_message() \
    .add_local_image("photo.jpg") \
    .build()

# ❌ Less convenient
with open("photo.jpg", "rb") as f:
    image_bytes = f.read()
message = create_user_message() \
    .add_image_bytes(image_bytes, filename="photo.jpg") \
    .build()
```

### 2. Provide Filenames for Better Detection
When using bytes methods, provide filenames to improve detection:

```python
# ✅ Better detection
builder.add_image_bytes(image_data, filename="photo.jpg")

# ❌ Content-only detection
builder.add_image_bytes(image_data)
```

### 3. Handle Errors Appropriately
Always handle potential errors:

```python
try:
    message = create_user_message() \
        .add_local_image("photo.jpg") \
        .build()
except FileNotFoundError:
    print("Image file not found")
except RequestValidationError as e:
    print(f"Validation error: {e}")
```

### 4. Use Meaningful Names for Documents
Provide descriptive names for documents:

```python
builder.add_local_document(
    "report.pdf",
    name="Q4 Financial Report"  # Helps LLM understand context
)
```

### 5. Monitor Content Size
Be aware of size limits and consider compression for large files:

```python
# Check file size before adding
file_size_mb = Path("video.mp4").stat().st_size / (1024 * 1024)
if file_size_mb > 50:
    print("Consider compressing the video")

builder.add_local_video("video.mp4", max_size_mb=100.0)
```

## Troubleshooting

### Common Issues

1. **File Not Found**: Ensure file paths are correct and files exist
2. **Size Limits**: Check file sizes against documented limits
3. **Format Detection**: Provide filenames or explicit formats for better detection
4. **Memory Usage**: Large files are loaded into memory - consider file sizes

### Debug Logging

Enable debug logging to see detection details:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show format detection processes, confidence levels, and method decisions.

---

The MessageBuilder system provides a powerful, flexible, and user-friendly way to construct complex multi-modal messages for AWS Bedrock applications. Its fluent interface, automatic detection, and comprehensive validation make it easy to build sophisticated AI applications.
