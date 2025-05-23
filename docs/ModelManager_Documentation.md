# Amazon Bedrock Model Manager Documentation

## Overview

The `ModelManager` class is a production-ready Python component designed to download, parse, and manage Amazon Bedrock foundational model information from AWS documentation. It provides a comprehensive solution for maintaining up-to-date model catalogs with structured data output.

## Features

- **Automated Documentation Retrieval**: Downloads the latest model information from AWS Bedrock documentation
- **Robust HTML Parsing**: Uses BeautifulSoup to extract structured data from HTML tables
- **JSON Serialization**: Outputs clean, timestamped JSON with consistent field naming
- **Error Handling**: Comprehensive error handling with proper logging
- **Caching**: Intelligent caching to avoid unnecessary downloads
- **Extensible Architecture**: Modular design with clear abstractions for easy modification
- **Production Quality**: Type hints, logging, error handling, and maintainable code structure

## Installation and Dependencies

### Required Dependencies

```python
# Core dependencies
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import logging
import json

# Third-party dependencies
import requests  # For HTTP downloads
from bs4 import BeautifulSoup  # For HTML parsing
```

### Installation

```bash
# Install required packages
pip install requests beautifulsoup4 lxml
```

## Basic Usage

### Simple Example

```python
from src.bedrock.ModelManager import ModelManager

# Initialize with default settings
manager = ModelManager()

# Download and parse latest model data
catalog = manager.refresh_model_data()

# Display results
print(f"Found {catalog.model_count} models")
print(f"Data retrieved at: {catalog.retrieval_timestamp}")
```

### Custom Configuration

```python
from pathlib import Path
from src.bedrock.ModelManager import ModelManager

# Custom configuration
manager = ModelManager(
    html_output_path=Path("custom/bedrock_models.html"),
    json_output_path=Path("output/models.json"),
    documentation_url="https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html",
    download_timeout=60
)

catalog = manager.refresh_model_data()
```

## Class Reference

### ModelManager

#### Constructor

```python
ModelManager(
    html_output_path: Optional[Path] = None,
    json_output_path: Optional[Path] = None,
    documentation_url: Optional[str] = None,
    download_timeout: int = 30
)
```

**Parameters:**
- `html_output_path`: Path where downloaded HTML will be saved (default: `docs/FoundationalModels.htm`)
- `json_output_path`: Path where parsed JSON will be saved (default: `docs/FoundationalModels.json`)
- `documentation_url`: Custom documentation URL (default: AWS Bedrock models page)
- `download_timeout`: Request timeout in seconds (default: 30)

#### Methods

##### refresh_model_data()

```python
def refresh_model_data(self, force_download: bool = True) -> ModelCatalog
```

Downloads and parses the latest model documentation.

**Parameters:**
- `force_download`: If True, always download fresh data. If False, use existing HTML if recent.

**Returns:**
- `ModelCatalog`: Complete catalog of parsed model information

**Raises:**
- `ModelManagerError`: If any step in the process fails

##### get_models_by_provider()

```python
def get_models_by_provider(self, provider: str) -> Dict[str, BedrockModelInfo]
```

Get all models from a specific provider.

**Parameters:**
- `provider`: Provider name (e.g., 'Amazon', 'Anthropic', 'Meta')

**Returns:**
- Dictionary of model names to model information

##### get_models_by_region()

```python
def get_models_by_region(self, region: str) -> Dict[str, BedrockModelInfo]
```

Get all models available in a specific AWS region.

**Parameters:**
- `region`: AWS region identifier (e.g., 'us-east-1')

**Returns:**
- Dictionary of model names to model information

##### get_streaming_models()

```python
def get_streaming_models(self) -> Dict[str, BedrockModelInfo]
```

Get all models that support streaming responses.

**Returns:**
- Dictionary of model names to model information for streaming-enabled models

## JSON Output Format

### Structure Overview

The ModelManager outputs JSON with the following top-level structure:

```json
{
  "retrieval_timestamp": "2025-05-23T16:41:55+02:00",
  "models": {
    "model_name_1": { /* model details */ },
    "model_name_2": { /* model details */ },
    ...
  }
}
```

### Field Definitions

#### Top Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `retrieval_timestamp` | string (ISO 8601) | Timestamp when data was retrieved from AWS |
| `models` | object | Dictionary containing all model information |

#### Model Object Fields

Each model in the `models` dictionary contains:

| Field | Type | Description |
|-------|------|-------------|
| `provider` | string | Model provider (e.g., "Amazon", "Anthropic", "Meta") |
| `model_id` | string | Unique model identifier for API calls |
| `regions_supported` | array[string] | List of AWS regions where model is available |
| `input_modalities` | array[string] | Supported input types (e.g., ["Text", "Image"]) |
| `output_modalities` | array[string] | Supported output types (e.g., ["Text", "Chat"]) |
| `streaming_supported` | boolean | Whether model supports streaming responses |
| `inference_parameters_link` | string\|null | URL to inference parameters documentation |
| `hyperparameters_link` | string\|null | URL to hyperparameters documentation |

### Complete Example

```json
{
  "retrieval_timestamp": "2025-05-23T16:41:55+02:00",
  "models": {
    "Nova Canvas": {
      "provider": "Amazon",
      "model_id": "amazon.nova-canvas-v1:0",
      "regions_supported": [
        "us-east-1",
        "ap-northeast-1",
        "eu-west-1"
      ],
      "input_modalities": [
        "Text",
        "Image"
      ],
      "output_modalities": [
        "Image"
      ],
      "streaming_supported": false,
      "inference_parameters_link": "https://docs.aws.amazon.com/nova/latest/userguide/image-gen-req-resp-structure.html",
      "hyperparameters_link": "https://docs.aws.amazon.com/nova/latest/userguide/customize-fine-tune-hyperparameters.html"
    },
    "Claude 3.5 Sonnet": {
      "provider": "Anthropic",
      "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
      "regions_supported": [
        "us-east-1",
        "us-west-2",
        "eu-central-1"
      ],
      "input_modalities": [
        "Text",
        "Image"
      ],
      "output_modalities": [
        "Text",
        "Chat"
      ],
      "streaming_supported": true,
      "inference_parameters_link": "https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-claude.html",
      "hyperparameters_link": null
    }
  }
}
```

### Boolean Value Mapping

The parser automatically converts AWS documentation values to proper booleans:

| Documentation Value | JSON Boolean |
|-------------------|--------------|
| "Yes" | `true` |
| "No" | `false` |
| "N/A" | `false` |

### Region Name Normalization

Region names are normalized to remove cross-region inference indicators:
- `"us-east-1*"` becomes `"us-east-1"`
- Duplicate regions are automatically removed

## Error Handling

### Exception Hierarchy

```python
ModelManagerError
├── NetworkError (from downloader)
├── FileSystemError (from downloader)
└── ParsingError (from parser)
```

### Example Error Handling

```python
from src.bedrock.ModelManager import ModelManager, ModelManagerError

try:
    manager = ModelManager()
    catalog = manager.refresh_model_data()
except ModelManagerError as e:
    print(f"Failed to refresh model data: {e}")
    # Handle error appropriately
```

## Logging

The ModelManager uses Python's built-in logging module with appropriate log levels:

- **INFO**: Major operations (download start/complete, parsing complete)
- **WARNING**: Data inconsistencies or parsing issues for individual rows
- **ERROR**: Failed operations that stop execution

### Configuring Logging

```python
import logging

# Configure logging to see ModelManager operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now ModelManager operations will be logged
manager = ModelManager()
catalog = manager.refresh_model_data()
```

## Advanced Usage

### Custom Parsing Logic

For advanced users who need custom parsing behavior:

```python
from src.bedrock.parsers.bedrock_parser import BedrockHTMLParser
from src.bedrock.downloaders.html_downloader import HTMLDocumentationDownloader
from pathlib import Path

# Use components independently
downloader = HTMLDocumentationDownloader(timeout=60)
parser = BedrockHTMLParser()

# Download
downloader.download(
    url="https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html",
    output_path=Path("custom.html")
)

# Parse
models = parser.parse(file_path=Path("custom.html"))
```

### Extending the Parser

To add custom parsing logic, extend the `BedrockHTMLParser`:

```python
from src.bedrock.parsers.bedrock_parser import BedrockHTMLParser

class CustomBedrockParser(BedrockHTMLParser):
    def _extract_custom_field(self, cells, column):
        # Custom parsing logic
        pass
```

## Performance Considerations

### Caching Strategy

- HTML files are cached and reused if less than 1 hour old
- Use `force_download=False` to leverage caching
- JSON output is generated fresh each time but can be cached externally

### Memory Usage

- Large HTML files (2-5MB) are processed entirely in memory
- JSON output is typically much smaller (50-500KB)
- Memory usage scales with number of models (~1-2KB per model)

### Network Efficiency

- Single HTTP request per refresh operation
- Respects AWS documentation server limits
- Configurable timeout and retry behavior

## Production Deployment

### Recommended Configuration

```python
# Production-ready configuration
manager = ModelManager(
    html_output_path=Path("/app/cache/bedrock_models.html"),  
    json_output_path=Path("/app/data/models.json"),
    download_timeout=120  # Longer timeout for production
)

# Schedule regular updates (e.g., daily via cron)
try:
    catalog = manager.refresh_model_data(force_download=False)
    logger.info(f"Successfully updated {catalog.model_count} models")
except ModelManagerError as e:
    logger.error(f"Model update failed: {e}")
    # Alert monitoring system
```

### Security Considerations

- Validates SSL certificates by default
- No execution of downloaded content
- Safe parsing using BeautifulSoup
- No sensitive data stored in output

## Troubleshooting

### Common Issues

1. **Network Errors**: Check internet connectivity and AWS documentation availability
2. **Parsing Errors**: AWS may have changed their HTML structure
3. **File Errors**: Ensure write permissions for output directories
4. **SSL Errors**: Check system SSL certificate configuration

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed parsing information
manager = ModelManager()  
catalog = manager.refresh_model_data()
```

## Version History

- **v1.0.0**: Initial production release with complete functionality
