# UnifiedModelManager Documentation

## Overview

The `UnifiedModelManager` class serves as the centralized model registry for the LLMManager system, combining information from both direct AWS Bedrock model access and Cross-Region Inference System (CRIS) data sources. It provides a unified view of model availability, access methods, and regional capabilities, enabling intelligent model selection and routing decisions.

## Table of Contents

- [Architecture](#architecture)
- [Installation and Setup](#installation-and-setup)
- [Basic Usage](#basic-usage)
- [API Reference](#api-reference)
- [Data Sources](#data-sources)
- [Model Access Methods](#model-access-methods)
- [Correlation Engine](#correlation-engine)
- [Caching and Performance](#caching-and-performance)
- [Advanced Features](#advanced-features)
- [Integration Examples](#integration-examples)
- [Best Practices](#best-practices)

## Architecture

The UnifiedModelManager acts as the central intelligence hub for model information:

### Core Components

```
UnifiedModelManager
├── ModelManager          # Direct Bedrock model catalog
├── CRISManager          # Cross-region inference data
├── CorrelationEngine    # Model matching and correlation
├── CacheManager         # Data caching and persistence
└── AccessRecommendation # Optimal access method selection
```

### Data Flow

```
AWS Sources → Data Acquisition → Correlation → Unified Catalog → Access Recommendations
     ↓              ↓              ↓              ↓                    ↓
[Bedrock API] → [Downloaders] → [Matching    → [Unified     → [Intelligent
[CRIS Docs ]    [Parsers   ]    Algorithm]     Models]        Routing]
```

### Key Features

- **Unified Data Model**: Single interface for all model information
- **Intelligent Correlation**: Advanced matching between different data sources  
- **Access Method Optimization**: Recommends optimal access methods per region
- **Real-time Availability**: Up-to-date model availability information
- **Performance Caching**: Intelligent caching for optimal performance
- **Extensible Architecture**: Support for additional data sources

## Installation and Setup

### Prerequisites

- Python 3.9 or higher
- ModelManager and CRISManager dependencies
- AWS credentials configured

### Basic Setup

```python
from src.bedrock.UnifiedModelManager import UnifiedModelManager

# Initialize with default settings
unified_manager = UnifiedModelManager()

# Load or refresh model data
try:
    # Try to load cached data first
    if not unified_manager.load_cached_data():
        print("No cached data found, refreshing...")
        unified_manager.refresh_unified_data()
except Exception as e:
    print(f"Failed to initialize model data: {e}")
```

### Advanced Configuration

```python
from src.bedrock.UnifiedModelManager import UnifiedModelManager
from src.bedrock.ModelManager import ModelManager
from src.bedrock.CRISManager import CRISManager
from pathlib import Path

# Custom component configuration
model_manager = ModelManager(
    html_output_path=Path("custom/bedrock_models.html"),
    json_output_path=Path("custom/bedrock_models.json")
)

cris_manager = CRISManager(
    html_output_path=Path("custom/cris_models.html"),
    json_output_path=Path("custom/cris_models.json")
)

# Initialize with custom components
unified_manager = UnifiedModelManager(
    model_manager=model_manager,
    cris_manager=cris_manager,
    json_output_path=Path("custom/unified_models.json"),
    enable_fuzzy_matching=True
)

# Refresh with custom settings
unified_manager.refresh_unified_data(force_download=True)
```

## Basic Usage

### Model Access Information

```python
# Get access information for a specific model in a region
access_info = unified_manager.get_model_access_info(
    model_name="Claude 3.5 Sonnet",
    region="us-east-1"
)

if access_info:
    print(f"Model ID: {access_info.model_id}")
    print(f"Access Method: {access_info.access_method}")
    print(f"Region: {access_info.region}")
    print(f"Inference Profile: {access_info.inference_profile_id}")
else:
    print("Model not available in specified region")
```

### Access Recommendations

```python
# Get recommended access method for optimal performance
recommendation = unified_manager.get_recommended_access(
    model_name="Claude 3.5 Sonnet",
    region="us-west-2"
)

if recommendation:
    print(f"Recommended Access: {recommendation.access_method}")
    print(f"Model ID: {recommendation.model_id}")
    print(f"Confidence: {recommendation.confidence:.2%}")
    print(f"Reason: {recommendation.recommendation_reason}")
```

### Model Availability Queries

```python
# Check if a model is available in a specific region
is_available = unified_manager.is_model_available_in_region(
    model_name="Claude 3 Haiku",
    region="eu-west-1"
)
print(f"Claude 3 Haiku available in eu-west-1: {is_available}")

# Get all models available in a region
models_in_region = unified_manager.get_models_by_region("us-east-1")
print(f"Models in us-east-1: {len(models_in_region)}")

for model_name, model_info in models_in_region.items():
    print(f"  {model_name}: {model_info.provider}")
```

### Provider and Category Queries

```python
# Get models by provider
anthropic_models = unified_manager.get_models_by_provider("Anthropic")
print(f"Anthropic models: {list(anthropic_models.keys())}")

# Get streaming-capable models
streaming_models = unified_manager.get_streaming_models()
print(f"Streaming models: {len(streaming_models)}")

# Get models with direct access only
direct_models = unified_manager.get_direct_access_models_by_region("us-east-1")
print(f"Direct access models in us-east-1: {len(direct_models)}")

# Get models available only through CRIS
cris_only_models = unified_manager.get_cris_only_models_by_region("eu-central-1")
print(f"CRIS-only models in eu-central-1: {len(cris_only_models)}")
```

## API Reference

### UnifiedModelManager Class

#### Constructor

```python
def __init__(
    self,
    model_manager: Optional[ModelManager] = None,
    cris_manager: Optional[CRISManager] = None,
    json_output_path: Optional[Path] = None,
    enable_fuzzy_matching: bool = True
) -> None
```

**Parameters:**

- `model_manager`: Pre-configured ModelManager instance (optional)
- `cris_manager`: Pre-configured CRISManager instance (optional)
- `json_output_path`: Path for unified model data JSON (optional)
- `enable_fuzzy_matching`: Enable fuzzy model name matching (default: True)

#### Core Methods

##### refresh_unified_data()

```python
def refresh_unified_data(self, force_download: Optional[bool] = None) -> UnifiedModelCatalog
```

Refresh unified model data from all sources.

**Parameters:**
- `force_download`: Force fresh download from sources (optional)

**Returns:** `UnifiedModelCatalog` with refreshed data

##### load_cached_data()

```python
def load_cached_data(self) -> Optional[UnifiedModelCatalog]
```

Load previously cached unified model data.

**Returns:** `UnifiedModelCatalog` if cached data exists, `None` otherwise

##### get_model_access_info()

```python
def get_model_access_info(self, model_name: str, region: str) -> Optional[ModelAccessInfo]
```

Get access information for a specific model in a region.

**Parameters:**
- `model_name`: Name of the model to query
- `region`: AWS region identifier

**Returns:** `ModelAccessInfo` if available, `None` otherwise

##### get_recommended_access()

```python
def get_recommended_access(self, model_name: str, region: str) -> Optional[AccessRecommendation]
```

Get recommended access method for optimal performance.

**Parameters:**
- `model_name`: Name of the model
- `region`: Target AWS region

**Returns:** `AccessRecommendation` with optimization details

#### Query Methods

##### is_model_available_in_region()

```python
def is_model_available_in_region(self, model_name: str, region: str) -> bool
```

Check if a model is available in a specific region.

##### get_models_by_region()

```python
def get_models_by_region(self, region: str) -> Dict[str, UnifiedModelInfo]
```

Get all models available in a specific region.

##### get_models_by_provider()

```python
def get_models_by_provider(self, provider: str) -> Dict[str, UnifiedModelInfo]
```

Get all models from a specific provider.

##### get_direct_access_models_by_region()

```python
def get_direct_access_models_by_region(self, region: str) -> Dict[str, UnifiedModelInfo]
```

Get models with direct access in a region.

##### get_cris_only_models_by_region()

```python
def get_cris_only_models_by_region(self, region: str) -> Dict[str, UnifiedModelInfo]
```

Get models available only through CRIS in a region.

##### get_streaming_models()

```python
def get_streaming_models(self) -> Dict[str, UnifiedModelInfo]
```

Get all models that support streaming responses.

#### Utility Methods

##### get_all_supported_regions()

```python
def get_all_supported_regions(self) -> List[str]
```

Get all regions supported by any model.

##### get_model_names()

```python
def get_model_names(self) -> List[str]
```

Get all available model names.

##### get_model_count()

```python
def get_model_count(self) -> int
```

Get total number of unified models.

##### has_model()

```python
def has_model(self, model_name: str) -> bool
```

Check if a model exists in the unified catalog.

##### get_correlation_stats()

```python
def get_correlation_stats(self) -> Dict[str, int]
```

Get statistics about model correlation process.

## Data Sources

### ModelManager Integration

The UnifiedModelManager integrates with ModelManager to access direct Bedrock model information:

```python
# ModelManager provides:
# - Direct model availability per region
# - Model capabilities (streaming, modalities)
# - Provider information
# - Model IDs for API calls

model_info = unified_manager.get_models_by_provider("Amazon")
for model_name, info in model_info.items():
    print(f"{model_name}:")
    print(f"  Direct regions: {info.get_direct_access_regions()}")
    print(f"  Streaming: {info.streaming_supported}")
    print(f"  Modalities: {info.input_modalities}")
```

### CRISManager Integration

Integration with CRISManager provides cross-region inference capabilities:

```python
# CRISManager provides:
# - Cross-region inference profiles
# - Regional routing information
# - Multi-regional model variants
# - Optimal region selection

# Get models with CRIS access
cris_models = unified_manager.get_cris_only_models_by_region("ap-southeast-1")
for model_name, info in cris_models.items():
    profiles = info.get_inference_profiles()
    print(f"{model_name}: {len(profiles)} inference profiles")
```

### Data Correlation Process

The correlation engine matches models from different sources:

```python
# View correlation statistics
stats = unified_manager.get_correlation_stats()
print(f"Correlation Statistics:")
print(f"  Direct models: {stats['direct_models']}")
print(f"  CRIS models: {stats['cris_models']}")
print(f"  Unified models: {stats['unified_models']}")
print(f"  Exact matches: {stats['exact_matches']}")
print(f"  Fuzzy matches: {stats['fuzzy_matches']}")
print(f"  Unmatched: {stats['unmatched_models']}")
```

## Model Access Methods

### ModelAccessMethod Enum

```python
from src.bedrock.models.access_method import ModelAccessMethod

# Available access methods
DIRECT = ModelAccessMethod.DIRECT              # Direct regional access
CROSS_REGION = ModelAccessMethod.CROSS_REGION  # CRIS inference profiles
```

### ModelAccessInfo Structure

```python
from src.bedrock.models.access_method import ModelAccessInfo

# Access information structure
access_info = ModelAccessInfo(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region="us-east-1",
    access_method=ModelAccessMethod.DIRECT,
    inference_profile_id=None  # Only for CROSS_REGION access
)
```

### Access Method Selection

```python
def demonstrate_access_methods():
    """Demonstrate different access methods."""
    
    model_name = "Claude 3.5 Sonnet"
    
    # Check different regions
    regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
    
    for region in regions:
        access_info = unified_manager.get_model_access_info(model_name, region)
        
        if access_info:
            print(f"{region}: {access_info.access_method.value}")
            if access_info.access_method == ModelAccessMethod.CROSS_REGION:
                print(f"  Inference Profile: {access_info.inference_profile_id}")
        else:
            print(f"{region}: Not available")

demonstrate_access_methods()
```

## Correlation Engine

### Fuzzy Matching Configuration

```python
# Enable/disable fuzzy matching
unified_manager.set_fuzzy_matching_enabled(True)

# Check current setting
is_enabled = unified_manager.is_fuzzy_matching_enabled()
print(f"Fuzzy matching enabled: {is_enabled}")
```

### Correlation Algorithm

The correlation engine uses multiple strategies to match models:

1. **Exact Name Matching**: Direct string comparison
2. **Normalized Matching**: Case-insensitive, whitespace-normalized
3. **Fuzzy Matching**: Similarity-based matching for variations
4. **Provider Context**: Provider-aware matching

```python
# Examples of model name variations that get correlated:
# ModelManager: "Claude 3.5 Sonnet"
# CRISManager: "Claude 3.5 Sonnet" (exact match)
# 
# ModelManager: "Nova Pro"  
# CRISManager: "Nova Pro" (exact match)
#
# Fuzzy matching handles minor variations:
# "Claude-3.5-Sonnet" → "Claude 3.5 Sonnet"
# "Llama3.1 405B" → "Llama 3.1 405B"
```

### Custom Correlation Rules

```python
class CustomCorrelationEngine:
    """Example of custom correlation logic."""
    
    def __init__(self):
        self.custom_mappings = {
            "claude-3.5-sonnet": "Claude 3.5 Sonnet",
            "llama3-405b": "Llama 3.1 405B",
            # Add custom mappings
        }
    
    def correlate_model_names(self, direct_name, cris_name):
        """Custom correlation logic."""
        # Normalize names
        direct_normalized = self.normalize_name(direct_name)
        cris_normalized = self.normalize_name(cris_name)
        
        # Check custom mappings
        if direct_normalized in self.custom_mappings:
            direct_normalized = self.custom_mappings[direct_normalized]
        
        return direct_normalized == cris_normalized
    
    def normalize_name(self, name):
        """Normalize model name for comparison."""
        return name.lower().replace("-", " ").replace("_", " ").strip()
```

## Caching and Performance

### Cache Management

```python
# Check if cached data is available
cached_catalog = unified_manager.load_cached_data()
if cached_catalog:
    print(f"Loaded {cached_catalog.model_count} models from cache")
    print(f"Cache timestamp: {cached_catalog.retrieval_timestamp}")
else:
    print("No cached data available")

# Force refresh from sources
fresh_catalog = unified_manager.refresh_unified_data(force_download=True)
print(f"Refreshed {fresh_catalog.model_count} models from sources")
```

### Performance Optimization

```python
import time

def benchmark_queries():
    """Benchmark query performance."""
    
    # Warm up cache
    unified_manager.get_model_names()
    
    # Benchmark region queries
    start_time = time.time()
    for _ in range(100):
        models = unified_manager.get_models_by_region("us-east-1")
    region_query_time = (time.time() - start_time) / 100
    
    # Benchmark access info queries
    start_time = time.time()
    for _ in range(100):
        access_info = unified_manager.get_model_access_info("Claude 3.5 Sonnet", "us-east-1")
    access_query_time = (time.time() - start_time) / 100
    
    print(f"Region query time: {region_query_time*1000:.2f}ms")
    print(f"Access info query time: {access_query_time*1000:.2f}ms")

benchmark_queries()
```

### Memory Management

```python
def optimize_memory_usage():
    """Optimize memory usage for long-running applications."""
    
    # Periodic cache refresh (e.g., every hour)
    import threading
    import time
    
    def refresh_cache_periodically():
        while True:
            time.sleep(3600)  # 1 hour
            try:
                unified_manager.refresh_unified_data(force_download=False)
                print("Cache refreshed successfully")
            except Exception as e:
                print(f"Cache refresh failed: {e}")
    
    # Start background refresh thread
    refresh_thread = threading.Thread(target=refresh_cache_periodically, daemon=True)
    refresh_thread.start()
```

## Advanced Features

### Access Recommendations

```python
from src.bedrock.models.access_method import AccessRecommendation

def get_optimal_access_methods():
    """Get optimal access methods for different scenarios."""
    
    scenarios = [
        ("Claude 3.5 Sonnet", "us-east-1", "low-latency"),
        ("Claude 3.5 Sonnet", "ap-southeast-1", "availability"),
        ("Nova Pro", "eu-central-1", "cost-optimization")
    ]
    
    for model_name, region, optimization_goal in scenarios:
        recommendation = unified_manager.get_recommended_access(model_name, region)
        
        if recommendation:
            print(f"\n{model_name} in {region} (goal: {optimization_goal}):")
            print(f"  Recommended: {recommendation.access_method.value}")
            print(f"  Model ID: {recommendation.model_id}")
            print(f"  Confidence: {recommendation.confidence:.2%}")
            print(f"  Reason: {recommendation.recommendation_reason}")
        else:
            print(f"\n{model_name} not available in {region}")

get_optimal_access_methods()
```

### Multi-Source Validation

```python
def validate_data_consistency():
    """Validate consistency between data sources."""
    
    inconsistencies = []
    
    # Get all unified models
    unified_models = unified_manager.get_model_names()
    
    for model_name in unified_models:
        # Check each region
        for region in unified_manager.get_all_supported_regions():
            access_info = unified_manager.get_model_access_info(model_name, region)
            
            if access_info:
                # Validate access method consistency
                if access_info.access_method == ModelAccessMethod.DIRECT:
                    # Should have valid model_id
                    if not access_info.model_id:
                        inconsistencies.append(f"Direct access {model_name} in {region} missing model_id")
                
                elif access_info.access_method == ModelAccessMethod.CROSS_REGION:
                    # Should have inference_profile_id
                    if not access_info.inference_profile_id:
                        inconsistencies.append(f"CRIS access {model_name} in {region} missing inference_profile_id")
    
    if inconsistencies:
        print("Data inconsistencies found:")
        for issue in inconsistencies[:10]:  # Show first 10
            print(f"  - {issue}")
    else:
        print("Data validation passed - no inconsistencies found")

validate_data_consistency()
```

### Model Capability Analysis

```python
def analyze_model_capabilities():
    """Analyze model capabilities across regions."""
    
    capabilities = {
        'streaming_by_region': {},
        'multimodal_by_region': {},
        'provider_distribution': {},
        'access_method_distribution': {}
    }
    
    all_regions = unified_manager.get_all_supported_regions()
    
    for region in all_regions:
        models = unified_manager.get_models_by_region(region)
        
        streaming_count = sum(1 for m in models.values() if m.streaming_supported)
        multimodal_count = sum(1 for m in models.values() 
                             if len(m.input_modalities) > 1 or 'Image' in m.input_modalities)
        
        capabilities['streaming_by_region'][region] = streaming_count
        capabilities['multimodal_by_region'][region] = multimodal_count
        
        # Provider distribution
        for model_info in models.values():
            provider = model_info.provider
            if provider not in capabilities['provider_distribution']:
                capabilities['provider_distribution'][provider] = 0
            capabilities['provider_distribution'][provider] += 1
        
        # Access method distribution
        for model_name in models.keys():
            access_info = unified_manager.get_model_access_info(model_name, region)
            if access_info:
                method = access_info.access_method.value
                if method not in capabilities['access_method_distribution']:
                    capabilities['access_method_distribution'][method] = 0
                capabilities['access_method_distribution'][method] += 1
    
    # Print analysis
    print("Model Capability Analysis:")
    print(f"\nStreaming Support by Region:")
    for region, count in capabilities['streaming_by_region'].items():
        print(f"  {region}: {count} models")
    
    print(f"\nMultimodal Support by Region:")
    for region, count in capabilities['multimodal_by_region'].items():
        print(f"  {region}: {count} models")
    
    print(f"\nProvider Distribution:")
    for provider, count in capabilities['provider_distribution'].items():
        print(f"  {provider}: {count} model-region combinations")
    
    print(f"\nAccess Method Distribution:")
    for method, count in capabilities['access_method_distribution'].items():
        print(f"  {method}: {count} combinations")

analyze_model_capabilities()
```

## Integration Examples

### LLMManager Integration

```python
# UnifiedModelManager is automatically used by LLMManager
from src.LLMManager import LLMManager

# LLMManager uses UnifiedModelManager internally
manager = LLMManager(
    models=["Claude 3.5 Sonnet", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"]
)

# Access the underlying UnifiedModelManager
unified_manager = manager._unified_model_manager

# Query model information
for model in manager.get_available_models():
    for region in manager.get_available_regions():
        access_info = unified_manager.get_model_access_info(model, region)
        if access_info:
            print(f"{model} in {region}: {access_info.access_method.value}")
```

### Custom Model Selector

```python
class IntelligentModelSelector:
    """Select optimal models based on requirements."""
    
    def __init__(self, unified_manager):
        self.unified_manager = unified_manager
    
    def select_models_for_requirements(self, requirements):
        """Select models based on specific requirements."""
        selected_models = {}
        
        target_region = requirements.get('region', 'us-east-1')
        need_streaming = requirements.get('streaming', False)
        need_multimodal = requirements.get('multimodal', False)
        preferred_providers = requirements.get('providers', [])
        
        # Get available models in target region
        available_models = self.unified_manager.get_models_by_region(target_region)
        
        for model_name, model_info in available_models.items():
            # Check streaming requirement
            if need_streaming and not model_info.streaming_supported:
                continue
            
            # Check multimodal requirement
            if need_multimodal and 'Image' not in model_info.input_modalities:
                continue
            
            # Check provider preference
            if preferred_providers and model_info.provider not in preferred_providers:
                continue
            
            # Get access information
            access_info = self.unified_manager.get_model_access_info(model_name, target_region)
            if access_info:
                selected_models[model_name] = {
                    'model_info': model_info,
                    'access_info': access_info,
                    'recommendation': self.unified_manager.get_recommended_access(model_name, target_region)
                }
        
        return selected_models
    
    def rank_models_by_suitability(self, models_dict, criteria):
        """Rank models by suitability score."""
        scored_models = []
        
        for model_name, info in models_dict.items():
            score = 0
            model_info = info['model_info']
            access_info = info['access_info']
            recommendation = info['recommendation']
            
            # Score based on access method (direct is better)
            if access_info.access_method == ModelAccessMethod.DIRECT:
                score += 10
            
            # Score based on recommendation confidence
            if recommendation:
                score += recommendation.confidence * 10
            
            # Score based on streaming support
            if criteria.get('streaming') and model_info.streaming_supported:
                score += 5
            
            # Score based on provider preference
            preferred_providers = criteria.get('providers', [])
            if not preferred_providers or model_info.provider in preferred_providers:
                score += 3
            
            scored_models.append((model_name, score, info))
        
        # Sort by score (descending)
        scored_models.sort(key=lambda x: x[1], reverse=True)
        return scored_models

# Usage example
selector = IntelligentModelSelector(unified_manager)

requirements = {
    'region': 'us-east-1',
    'streaming': True,
    'multimodal': True,
    'providers': ['Anthropic', 'Amazon']
}

selected = selector.select_models_for_requirements(requirements)
ranked = selector.rank_models_by_suitability(selected, requirements)

print("Recommended Models (ranked by suitability):")
for model_name, score, info in ranked[:3]:  # Top 3
    print(f"\n{model_name} (score: {score:.1f})")
    print(f"  Provider: {info['model_info'].provider}")
    print(f"  Access: {info['access_info'].access_method.value}")
    print(f"  Streaming: {info['model_info'].streaming_supported}")
```

### Health Monitoring

```python
import time
from datetime import datetime, timedelta

class UnifiedModelManagerHealthMonitor:
    """Monitor health and performance of UnifiedModelManager."""
    
    def __init__(self, unified_manager):
        self.unified_manager = unified_manager
        self.health_metrics = {
            'last_refresh': None,
            'refresh_duration': None,
            'model_count': 0,
            'region_count': 0,
            'correlation_success_rate': 0.0,
            'cache_hit_rate': 0.0,
            'errors': []
        }
    
    def check_health(self):
        """Perform comprehensive health check."""
        print("🏥 UnifiedModelManager Health Check")
        print("=" * 40)
        
        # Check 1: Data availability
        try:
            model_count = self.unified_manager.get_model_count()
            region_count = len(self.unified_manager.get_all_supported_regions())
            
            print(f"✅ Data Availability:")
            print(f"   Models: {model_count}")
            print(f"   Regions: {region_count}")
            
            self.health_metrics['model_count'] = model_count
            self.health_metrics['region_count'] = region_count
            
        except Exception as e:
            print(f"❌ Data Availability: {e}")
            self.health_metrics['errors'].append(f"Data availability: {e}")
        
        # Check 2: Correlation statistics
        try:
            stats = self.unified_manager.get_correlation_stats()
            total_models = stats.get('direct_models', 0) + stats.get('cris_models', 0)
            unified_models = stats.get('unified_models', 0)
            success_rate = (unified_models / total_models * 100) if total_models > 0 else 0
            
            print(f"✅ Correlation Engine:")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Unified Models: {unified_models}")
            print(f"   Exact Matches: {stats.get('exact_matches', 0)}")
            print(f"   Fuzzy Matches: {stats.get('fuzzy_matches', 0)}")
            
            self.health_metrics['correlation_success_rate'] = success_rate
            
        except Exception as e:
            print(f"❌ Correlation Engine: {e}")
            self.health_metrics['errors'].append(f"Correlation: {e}")
        
        # Check 3: Performance benchmarks
        try:
            self._benchmark_performance()
        except Exception as e:
            print(f"❌ Performance Benchmark: {e}")
            self.health_metrics['errors'].append(f"Performance: {e}")
        
        # Check 4: Cache status
        try:
            self._check_cache_status()
        except Exception as e:
            print(f"❌ Cache Status: {e}")
            self.health_metrics['errors'].append(f"Cache: {e}")
        
        # Overall health assessment
        error_count = len(self.health_metrics['errors'])
        if error_count == 0:
            print(f"\n🟢 Overall Health: HEALTHY")
        elif error_count <= 2:
            print(f"\n🟡 Overall Health: WARNING ({error_count} issues)")
        else:
            print(f"\n🔴 Overall Health: CRITICAL ({error_count} issues)")
        
        return self.health_metrics
    
    def _benchmark_performance(self):
        """Benchmark query performance."""
        # Test region query performance
        start_time = time.time()
        for _ in range(50):
            models = self.unified_manager.get_models_by_region("us-east-1")
        region_query_time = (time.time() - start_time) / 50 * 1000
        
        # Test access info query performance
        start_time = time.time()
        for _ in range(50):
            access_info = self.unified_manager.get_model_access_info("Claude 3.5 Sonnet", "us-east-1")
        access_query_time = (time.time() - start_time) / 50 * 1000
        
        print(f"✅ Performance Benchmarks:")
        print(f"   Region Query: {region_query_time:.2f}ms avg")
        print(f"   Access Query: {access_query_time:.2f}ms avg")
        
        # Store metrics
        self.health_metrics['region_query_time_ms'] = region_query_time
        self.health_metrics['access_query_time_ms'] = access_query_time
    
    def _check_cache_status(self):
        """Check cache status and freshness."""
        try:
            cached_catalog = self.unified_manager.load_cached_data()
            if cached_catalog:
                cache_age = datetime.now() - cached_catalog.retrieval_timestamp
                cache_age_hours = cache_age.total_seconds() / 3600
                
                print(f"✅ Cache Status:")
                print(f"   Cache Available: Yes")
                print(f"   Cache Age: {cache_age_hours:.1f} hours")
                print(f"   Models Cached: {cached_catalog.model_count}")
                
                # Warn if cache is old
                if cache_age_hours > 24:
                    print(f"   ⚠️  Cache is over 24 hours old")
                    self.health_metrics['errors'].append("Cache is stale")
                
            else:
                print(f"❌ Cache Status: No cache available")
                self.health_metrics['errors'].append("No cache available")
                
        except Exception as e:
            print(f"❌ Cache Status: Error checking cache - {e}")
            self.health_metrics['errors'].append(f"Cache error: {e}")

# Usage
health_monitor = UnifiedModelManagerHealthMonitor(unified_manager)
health_status = health_monitor.check_health()
```

## Best Practices

### 1. Initialization and Setup

```python
# ✅ Good: Robust initialization with error handling
def initialize_unified_manager():
    """Initialize UnifiedModelManager with proper error handling."""
    try:
        unified_manager = UnifiedModelManager()
        
        # Try to load cached data first
        if not unified_manager.load_cached_data():
            print("No cached data found, refreshing from sources...")
            unified_manager.refresh_unified_data()
        else:
            print("Loaded model data from cache")
        
        # Validate data integrity
        model_count = unified_manager.get_model_count()
        if model_count == 0:
            raise Exception("No models loaded - data may be corrupted")
        
        print(f"Successfully initialized with {model_count} models")
        return unified_manager
        
    except Exception as e:
        print(f"Failed to initialize UnifiedModelManager: {e}")
        raise

# ❌ Bad: No error handling
def bad_initialization():
    unified_manager = UnifiedModelManager()
    unified_manager.refresh_unified_data()  # May fail silently
    return unified_manager
```

### 2. Query Optimization

```python
# ✅ Good: Efficient batch queries
def get_model_capabilities_efficiently(unified_manager, models, region):
    """Efficiently query multiple model capabilities."""
    
    # Get all models in region once
    region_models = unified_manager.get_models_by_region(region)
    
    results = {}
    for model_name in models:
        if model_name in region_models:
            model_info = region_models[model_name]
            access_info = unified_manager.get_model_access_info(model_name, region)
            
            results[model_name] = {
                'available': True,
                'streaming': model_info.streaming_supported,
                'access_method': access_info.access_method.value if access_info else None,
                'provider': model_info.provider
            }
        else:
            results[model_name] = {'available': False}
    
    return results

# ❌ Bad: Inefficient individual queries
def get_model_capabilities_inefficiently(unified_manager, models, region):
    results = {}
    for model_name in models:
        # Inefficient: queries region models for each model
        is_available = unified_manager.is_model_available_in_region(model_name, region)
        results[model_name] = {'available': is_available}
    return results
```

### 3. Caching Strategy

```python
# ✅ Good: Intelligent cache management
class ManagedUnifiedModelManager:
    """Wrapper with intelligent cache management."""
    
    def __init__(self, cache_ttl_hours=6):
        self.unified_manager = UnifiedModelManager()
        self.cache_ttl_hours = cache_ttl_hours
        self.last_refresh = None
    
    def get_model_access_info(self, model_name, region):
        """Get model access info with cache freshness check."""
        self._ensure_fresh_cache()
        return self.unified_manager.get_model_access_info(model_name, region)
    
    def _ensure_fresh_cache(self):
        """Ensure cache is fresh, refresh if needed."""
        needs_refresh = False
        
        # Check if we need to refresh
        if self.last_refresh is None:
            needs_refresh = True
        else:
            age = datetime.now() - self.last_refresh
            if age.total_seconds() / 3600 > self.cache_ttl_hours:
                needs_refresh = True
        
        if needs_refresh:
            try:
                self.unified_manager.refresh_unified_data(force_download=False)
                self.last_refresh = datetime.now()
                print("Cache refreshed successfully")
            except Exception as e:
                print(f"Cache refresh failed: {e}")
                # Continue with existing cache

# ❌ Bad: No cache management
def bad_cache_usage():
    unified_manager = UnifiedModelManager()
    # Never refreshes cache, may become stale
    return unified_manager.get_model_access_info("Claude 3.5 Sonnet", "us-east-1")
```

### 4. Error Handling and Resilience

```python
# ✅ Good: Comprehensive error handling
def robust_model_selection(unified_manager, preferred_models, region):
    """Robustly select available model from preferred list."""
    
    for model_name in preferred_models:
        try:
            # Check availability
            if not unified_manager.is_model_available_in_region(model_name, region):
                continue
            
            # Get access information
            access_info = unified_manager.get_model_access_info(model_name, region)
            if not access_info:
                continue
            
            # Verify access method is supported
            if access_info.access_method in [ModelAccessMethod.DIRECT, ModelAccessMethod.CROSS_REGION]:
                return {
                    'model_name': model_name,
                    'access_info': access_info,
                    'success': True
                }
        
        except Exception as e:
            print(f"Error checking {model_name}: {e}")
            continue
    
    return {'success': False, 'error': 'No available models found'}

# ❌ Bad: Poor error handling
def fragile_model_selection(unified_manager, preferred_models, region):
    # May crash on first error
    for model_name in preferred_models:
        access_info = unified_manager.get_model_access_info(model_name, region)
        if access_info:
            return access_info
    return None
```

### 5. Performance Monitoring

```python
# ✅ Good: Performance monitoring and optimization
import time
from functools import wraps

def monitor_performance(func):
    """Decorator to monitor UnifiedModelManager operation performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            
            if duration > 100:  # Log slow operations
                print(f"Slow operation: {func.__name__} took {duration:.2f}ms")
            
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            print(f"Failed operation: {func.__name__} failed after {duration:.2f}ms: {e}")
            raise
    return wrapper

class MonitoredUnifiedModelManager:
    """UnifiedModelManager with performance monitoring."""
    
    def __init__(self):
        self.unified_manager = UnifiedModelManager()
    
    @monitor_performance
    def get_model_access_info(self, model_name, region):
        return self.unified_manager.get_model_access_info(model_name, region)
    
    @monitor_performance
    def get_models_by_region(self, region):
        return self.unified_manager.get_models_by_region(region)

# ❌ Bad: No performance visibility
# Using UnifiedModelManager without any monitoring or performance awareness
```

### 6. Testing and Validation

```python
# ✅ Good: Comprehensive validation
def validate_unified_manager(unified_manager):
    """Validate UnifiedModelManager functionality."""
    
    validation_results = {
        'passed': [],
        'failed': [],
        'warnings': []
    }
    
    try:
        # Test 1: Basic data availability
        model_count = unified_manager.get_model_count()
        if model_count > 0:
            validation_results['passed'].append(f"Data available: {model_count} models")
        else:
            validation_results['failed'].append("No models available")
        
        # Test 2: Region coverage
        regions = unified_manager.get_all_supported_regions()
        if len(regions) >= 3:  # Expect at least 3 regions
            validation_results['passed'].append(f"Region coverage: {len(regions)} regions")
        else:
            validation_results['warnings'].append(f"Limited region coverage: {len(regions)} regions")
        
        # Test 3: Access method functionality
        test_models = ["Claude 3.5 Sonnet", "Claude 3 Haiku"]
        for model_name in test_models:
            access_info = unified_manager.get_model_access_info(model_name, "us-east-1")
            if access_info:
                validation_results['passed'].append(f"Access info available for {model_name}")
            else:
                validation_results['warnings'].append(f"No access info for {model_name}")
        
        # Test 4: Correlation statistics
        stats = unified_manager.get_correlation_stats()
        success_rate = stats.get('unified_models', 0) / max(1, stats.get('direct_models', 0) + stats.get('cris_models', 0))
        if success_rate > 0.8:
            validation_results['passed'].append(f"High correlation success rate: {success_rate:.2%}")
        else:
            validation_results['warnings'].append(f"Low correlation success rate: {success_rate:.2%}")
        
    except Exception as e:
        validation_results['failed'].append(f"Validation error: {e}")
    
    # Report results
    print("Validation Results:")
    for result in validation_results['passed']:
        print(f"  ✅ {result}")
    for result in validation_results['warnings']:
        print(f"  ⚠️  {result}")
    for result in validation_results['failed']:
        print(f"  ❌ {result}")
    
    return validation_results

# Usage
validation_results = validate_unified_manager(unified_manager)
is_healthy = len(validation_results['failed']) == 0
```

---

This comprehensive documentation provides everything needed to effectively use the UnifiedModelManager as the central model registry for LLM applications. The unified approach to model management enables intelligent routing, optimal access method selection, and robust application architecture while maintaining high performance and reliability.
