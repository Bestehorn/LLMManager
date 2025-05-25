# CRISManager Documentation

## Overview

The `CRISManager` class provides comprehensive management of Amazon Bedrock Cross-Region Inference (CRIS) model information. It orchestrates the download, parsing, and serialization of CRIS documentation from AWS, enabling developers to programmatically access and query cross-region inference capabilities.

## Table of Contents

- [Architecture](#architecture)
- [Installation and Setup](#installation-and-setup)
- [Basic Usage](#basic-usage)
- [API Reference](#api-reference)
- [Configuration Options](#configuration-options)
- [Error Handling](#error-handling)
- [Caching and Performance](#caching-and-performance)
- [Extension and Customization](#extension-and-customization)
- [Best Practices](#best-practices)
- [Examples](#examples)

## Architecture

The CRISManager follows a modular, layered architecture:

### Core Components

1. **CRISManager**: Main orchestrator class
2. **CRISHTMLParser**: Parses AWS HTML documentation
3. **HTMLDocumentationDownloader**: Downloads HTML content
4. **JSONModelSerializer**: Handles JSON serialization/deserialization
5. **Data Structures**: Type-safe models for CRIS information

### Data Flow

```
AWS Documentation URL
         ↓
HTMLDocumentationDownloader
         ↓
Local HTML File
         ↓
CRISHTMLParser
         ↓
CRISModelInfo Objects
         ↓
CRISCatalog
         ↓
JSONModelSerializer
         ↓
JSON Output File
```

### Design Patterns

- **Dependency Injection**: Components are injected for testability
- **Strategy Pattern**: Different parsers can be plugged in
- **Template Method**: Consistent workflow across managers
- **Immutable Data**: Thread-safe data structures using `@dataclass(frozen=True)`

## Installation and Setup

### Prerequisites

- Python 3.9+
- Required dependencies: `beautifulsoup4`, `requests`, `typing-extensions`

### Installation

```bash
# Install from source
git clone <repository>
cd LLMManager
pip install -r requirements.txt

# Add to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/LLMManager/src"
```

### Basic Setup

```python
from pathlib import Path
from src.bedrock.CRISManager import CRISManager

# Basic setup with defaults
manager = CRISManager()

# Custom configuration
manager = CRISManager(
    html_output_path=Path("custom/cris.htm"),
    json_output_path=Path("custom/cris.json"),
    download_timeout=60
)
```

## Basic Usage

### Quick Start

```python
from src.bedrock.CRISManager import CRISManager, CRISManagerError

# Initialize manager
cris_manager = CRISManager()

try:
    # Download and parse latest CRIS data
    catalog = cris_manager.refresh_cris_data()
    print(f"Found {catalog.model_count} CRIS models")
    
    # Query models by source region
    us_west_models = cris_manager.get_models_by_source_region("us-west-2")
    
    # Get inference profile for specific model
    profile_id = cris_manager.get_inference_profile_for_model("Nova Lite")
    
except CRISManagerError as e:
    print(f"Error: {e}")
```

### Caching Workflow

```python
# Try to load cached data first
catalog = cris_manager.load_cached_data()

if not catalog:
    # Download fresh data if cache miss
    catalog = cris_manager.refresh_cris_data()
```

## API Reference

### CRISManager Class

#### Constructor

```python
def __init__(
    self,
    html_output_path: Optional[Path] = None,
    json_output_path: Optional[Path] = None,
    documentation_url: Optional[str] = None,
    download_timeout: int = 30
) -> None
```

**Parameters:**
- `html_output_path`: Custom path for HTML output (default: `docs/CRIS.htm`)
- `json_output_path`: Custom path for JSON output (default: `docs/CRIS.json`)
- `documentation_url`: Custom documentation URL (default: AWS CRIS docs)
- `download_timeout`: Request timeout in seconds (default: 30)

#### Core Methods

##### refresh_cris_data()

```python
def refresh_cris_data(self, force_download: bool = True) -> CRISCatalog
```

Downloads and parses the latest CRIS documentation.

**Parameters:**
- `force_download`: If True, always download fresh data. If False, use existing HTML if recent.

**Returns:** `CRISCatalog` containing all parsed CRIS model information

**Raises:** `CRISManagerError` if any step fails

##### load_cached_data()

```python
def load_cached_data(self) -> Optional[CRISCatalog]
```

Loads previously cached CRIS data from JSON file.

**Returns:** `CRISCatalog` if cached data exists and is valid, `None` otherwise

#### Query Methods

##### get_models_by_source_region()

```python
def get_models_by_source_region(self, source_region: str) -> Dict[str, CRISModelInfo]
```

Get all CRIS models callable from a specific source region.

**Parameters:**
- `source_region`: Source region identifier (e.g., 'us-east-1')

**Returns:** Dictionary of model names to CRIS model info

##### get_models_by_destination_region()

```python
def get_models_by_destination_region(self, destination_region: str) -> Dict[str, CRISModelInfo]
```

Get all CRIS models that can route to a specific destination region.

**Parameters:**
- `destination_region`: Destination region identifier (e.g., 'us-west-2')

**Returns:** Dictionary of model names to CRIS model info

##### get_inference_profile_for_model()

```python
def get_inference_profile_for_model(self, model_name: str) -> Optional[str]
```

Get the inference profile ID for a specific CRIS model.

**Parameters:**
- `model_name`: The name of the model to look up

**Returns:** Inference profile ID if model exists, `None` otherwise

##### get_destinations_for_source_and_model()

```python
def get_destinations_for_source_and_model(
    self, 
    model_name: str, 
    source_region: str
) -> List[str]
```

Get destination regions available for a specific model from a specific source region.

**Parameters:**
- `model_name`: The name of the CRIS model
- `source_region`: The source region to query from

**Returns:** List of destination regions

#### Utility Methods

##### get_model_count()

```python
def get_model_count(self) -> int
```

Get the total number of CRIS models in the catalog.

##### get_model_names()

```python
def get_model_names(self) -> List[str]
```

Get all CRIS model names in the catalog.

##### has_model()

```python
def has_model(self, model_name: str) -> bool
```

Check if a CRIS model exists in the catalog.

##### get_all_source_regions() / get_all_destination_regions()

```python
def get_all_source_regions(self) -> List[str]
def get_all_destination_regions(self) -> List[str]
```

Get all unique source/destination regions across all models.

### Data Structures

#### CRISModelInfo

Immutable data class representing a single CRIS model.

```python
@dataclass(frozen=True)
class CRISModelInfo:
    model_name: str
    inference_profile_id: str
    region_mappings: Dict[str, List[str]]
```

**Key Methods:**
- `get_source_regions()`: Get all source regions for this model
- `get_destination_regions()`: Get all unique destination regions
- `can_route_from_source(source_region)`: Check if callable from source
- `can_route_to_destination(destination_region)`: Check if routes to destination

#### CRISCatalog

Immutable data class representing the complete CRIS catalog.

```python
@dataclass(frozen=True)
class CRISCatalog:
    retrieval_timestamp: datetime
    cris_models: Dict[str, CRISModelInfo]
```

## Configuration Options

### File Paths

```python
# Default paths
DEFAULT_HTML_OUTPUT = "docs/CRIS.htm"
DEFAULT_JSON_OUTPUT = "docs/CRIS.json"

# Custom paths
manager = CRISManager(
    html_output_path=Path("/custom/path/cris.htm"),
    json_output_path=Path("/custom/path/cris.json")
)
```

### Network Configuration

```python
# Custom timeout and URL
manager = CRISManager(
    documentation_url="https://custom.docs.url",
    download_timeout=120  # 2 minutes
)
```

### Logging Configuration

```python
import logging

# Configure logging levels
logging.getLogger('bedrock.CRISManager').setLevel(logging.INFO)
logging.getLogger('bedrock.parsers.cris_parser').setLevel(logging.DEBUG)
```

## Error Handling

### Exception Hierarchy

```
CRISManagerError (base)
├── NetworkError (from downloader)
├── FileSystemError (from downloader)
└── ParsingError (from parser)
```

### Error Handling Patterns

```python
from src.bedrock.CRISManager import CRISManager, CRISManagerError
from src.bedrock.downloaders.base_downloader import NetworkError
from src.bedrock.parsers.base_parser import ParsingError

try:
    catalog = cris_manager.refresh_cris_data()
except NetworkError as e:
    print(f"Network issue: {e}")
    # Try cached data as fallback
    catalog = cris_manager.load_cached_data()
except ParsingError as e:
    print(f"Parsing failed: {e}")
    # Log for debugging
    logger.error(f"Parser error details: {e}")
except CRISManagerError as e:
    print(f"General CRIS error: {e}")
```

### Validation Errors

```python
# Model validation occurs during construction
try:
    model = CRISModelInfo(
        model_name="Invalid@Name",  # Invalid characters
        inference_profile_id="invalid-format",  # Wrong format
        region_mappings={}  # Empty mappings
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

## Caching and Performance

### Cache Management

```python
# Check if HTML file is recent (default: 1 hour)
if not manager._is_html_file_recent(max_age_hours=2):
    # Download fresh data
    catalog = manager.refresh_cris_data(force_download=True)
else:
    # Use existing HTML
    catalog = manager.refresh_cris_data(force_download=False)
```

### Performance Considerations

1. **Caching Strategy**: Always try to load cached data first
2. **Download Optimization**: Use appropriate timeouts and retry logic
3. **Memory Usage**: Immutable data structures are memory-efficient
4. **Parsing Performance**: BeautifulSoup with html.parser is fast and reliable

### Performance Monitoring

```python
import time

start_time = time.time()
catalog = cris_manager.refresh_cris_data()
duration = time.time() - start_time

print(f"Processed {catalog.model_count} models in {duration:.2f} seconds")
```

## Extension and Customization

### Custom Parsers

```python
from src.bedrock.parsers.cris_parser import BaseCRISParser

class CustomCRISParser(BaseCRISParser):
    def parse(self, file_path: Path) -> Dict[str, CRISModelInfo]:
        # Custom parsing logic
        pass

# Use custom parser
manager._parser = CustomCRISParser()
```

### Custom Serializers

```python
class YAMLSerializer:
    def serialize_dict_to_file(self, data: Dict, output_path: Path) -> None:
        # YAML serialization logic
        pass

# Replace serializer
manager._serializer = YAMLSerializer()
```

### Adding New Fields

```python
# Extend constants
class ExtendedCRISJSONFields(CRISJSONFields):
    COST_INFO: Final[str] = "cost_info"
    LATENCY_INFO: Final[str] = "latency_info"

# Extend data structures
@dataclass(frozen=True)
class ExtendedCRISModelInfo(CRISModelInfo):
    cost_per_request: Optional[float] = None
    avg_latency_ms: Optional[int] = None
```

## Best Practices

### Development Best Practices

1. **Use Type Hints**: Leverage strict typing for better IDE support
2. **Named Parameters**: Always use named parameters for clarity
3. **Error Handling**: Handle specific exceptions appropriately
4. **Logging**: Use appropriate log levels for debugging
5. **Testing**: Write comprehensive unit tests for extensions

### Production Best Practices

1. **Caching**: Implement proper cache invalidation strategies
2. **Monitoring**: Monitor download success rates and parsing errors
3. **Resilience**: Implement retry logic and fallback mechanisms
4. **Resource Management**: Ensure proper cleanup of file handles
5. **Security**: Validate URLs and sanitize file paths

### Code Quality

```python
# Good: Named parameters and error handling
try:
    models = manager.get_models_by_source_region(source_region="us-east-1")
    for model_name, model_info in models.items():
        profile = manager.get_inference_profile_for_model(model_name=model_name)
        destinations = model_info.get_destinations_for_source(source_region="us-east-1")
        print(f"Model {model_name}: {profile} -> {destinations}")
except CRISManagerError as e:
    logger.error(f"Failed to query models: {e}")

# Bad: Positional parameters and poor error handling
try:
    models = manager.get_models_by_source_region("us-east-1")
    # No error handling
except Exception:
    pass  # Silent failure
```

## Examples

### Multi-Region Setup Script

```python
#!/usr/bin/env python3
"""
Multi-region CRIS setup script.
Configures cross-region inference for optimal performance.
"""

from src.bedrock.CRISManager import CRISManager
import json

def setup_multi_region_inference():
    manager = CRISManager()
    
    try:
        # Load latest CRIS data
        catalog = manager.refresh_cris_data()
        
        # Define target regions
        primary_region = "us-east-1"
        backup_regions = ["us-west-2", "us-east-2"]
        
        # Find models available from primary region
        primary_models = manager.get_models_by_source_region(primary_region)
        
        config = {
            "primary_region": primary_region,
            "models": {}
        }
        
        for model_name, model_info in primary_models.items():
            available_destinations = model_info.get_destinations_for_source(primary_region)
            fallback_regions = [r for r in backup_regions if r in available_destinations]
            
            config["models"][model_name] = {
                "inference_profile_id": model_info.inference_profile_id,
                "primary_region": primary_region,
                "fallback_regions": fallback_regions
            }
        
        # Save configuration
        with open("multi_region_config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Configured {len(config['models'])} models for multi-region inference")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")

if __name__ == "__main__":
    setup_multi_region_inference()
```

### Cost Optimization Tool

```python
"""
CRIS cost optimization tool.
Analyzes region routing for cost efficiency.
"""

def analyze_cost_efficiency():
    manager = CRISManager()
    catalog = manager.refresh_cris_data()
    
    # Cost analysis by region (mock data for example)
    region_costs = {
        "us-east-1": 1.0,    # Base cost
        "us-west-2": 1.1,    # 10% higher
        "us-east-2": 0.95,   # 5% lower
    }
    
    recommendations = []
    
    for model_name in manager.get_model_names():
        model_info = catalog.cris_models[model_name]
        
        # Analyze each source region
        for source_region in model_info.get_source_regions():
            destinations = model_info.get_destinations_for_source(source_region)
            
            # Find lowest cost destination
            cost_analysis = [
                (dest, region_costs.get(dest, 1.0)) 
                for dest in destinations 
                if dest in region_costs
            ]
            
            if cost_analysis:
                optimal_dest = min(cost_analysis, key=lambda x: x[1])
                
                recommendations.append({
                    "model": model_name,
                    "source": source_region,
                    "optimal_destination": optimal_dest[0],
                    "cost_factor": optimal_dest[1],
                    "inference_profile": model_info.inference_profile_id
                })
    
    # Display recommendations
    print("💰 Cost Optimization Recommendations:")
    for rec in recommendations[:5]:  # Show top 5
        print(f"   {rec['model']}: {rec['source']} → {rec['optimal_destination']} "
              f"(cost factor: {rec['cost_factor']})")

if __name__ == "__main__":
    analyze_cost_efficiency()
```

### Health Check Script

```python
"""
CRIS health check script.
Validates CRIS configuration and connectivity.
"""

def health_check():
    manager = CRISManager()
    
    checks = {
        "cache_available": False,
        "download_successful": False,
        "parsing_successful": False,
        "model_count": 0,
        "regions_available": 0
    }
    
    # Check 1: Cache availability
    cached_catalog = manager.load_cached_data()
    checks["cache_available"] = cached_catalog is not None
    
    # Check 2: Fresh download and parsing
    try:
        fresh_catalog = manager.refresh_cris_data(force_download=True)
        checks["download_successful"] = True
        checks["parsing_successful"] = True
        checks["model_count"] = fresh_catalog.model_count
        checks["regions_available"] = len(fresh_catalog.get_all_source_regions())
    except Exception as e:
        print(f"❌ Download/parsing failed: {e}")
    
    # Report health status
    print("🏥 CRIS Health Check Results:")
    print(f"   Cache Available: {'✅' if checks['cache_available'] else '❌'}")
    print(f"   Download Success: {'✅' if checks['download_successful'] else '❌'}")
    print(f"   Parsing Success: {'✅' if checks['parsing_successful'] else '❌'}")
    print(f"   Models Available: {checks['model_count']}")
    print(f"   Regions Available: {checks['regions_available']}")
    
    # Overall health
    overall_health = all([
        checks["download_successful"],
        checks["parsing_successful"],
        checks["model_count"] > 0
    ])
    
    print(f"   Overall Health: {'✅ HEALTHY' if overall_health else '❌ UNHEALTHY'}")
    
    return overall_health

if __name__ == "__main__":
    health_check()
```

## Troubleshooting

### Common Issues

1. **Network Timeouts**
   - Increase `download_timeout` parameter
   - Check firewall and proxy settings
   - Verify internet connectivity

2. **Parsing Failures**
   - Check if AWS documentation format changed
   - Verify HTML file is not corrupted
   - Enable debug logging for detailed error info

3. **Cache Issues**
   - Ensure write permissions for output directories
   - Check disk space availability
   - Verify JSON file is not corrupted

4. **Permission Errors**
   - Ensure read/write permissions for output paths
   - Check directory existence and creation permissions

### Debug Configuration

```python
import logging

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cris_debug.log'),
        logging.StreamHandler()
    ]
)

# Enable specific component debugging
logging.getLogger('bedrock.parsers.cris_parser').setLevel(logging.DEBUG)
logging.getLogger('bedrock.downloaders').setLevel(logging.DEBUG)
```

---

**Note**: This documentation covers the core functionality of CRISManager. For the latest updates and additional features, please refer to the source code and inline documentation.
