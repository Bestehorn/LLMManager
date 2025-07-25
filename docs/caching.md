# Amazon Bedrock Caching Support in LLM Manager

## Table of Contents
1. [Overview](#overview)
2. [How Bedrock Caching Works](#how-bedrock-caching-works)
3. [LLM Manager Caching Architecture](#llm-manager-caching-architecture)
4. [Usage Without MessageBuilder](#usage-without-messagebuilder)
5. [Usage With MessageBuilder](#usage-with-messagebuilder)
6. [Caching Strategies](#caching-strategies)
7. [Performance Benefits](#performance-benefits)
8. [Best Practices](#best-practices)
9. [Example: Sequential Prompts with Shared Content](#example-sequential-prompts-with-shared-content)

## Overview

The LLM Manager provides intelligent caching capabilities built on top of Amazon Bedrock's native prompt caching feature. While Bedrock provides the basic caching mechanism through `cachePoint` content blocks, LLM Manager adds:

- **Automatic cache point optimization** based on configurable strategies
- **Seamless MessageBuilder integration** for easy cache management
- **Performance analytics** to track cache efficiency
- **Cost optimization** through intelligent cache placement

### Key Benefits
- **Cost Reduction**: 80-90% reduction in token costs for cached content
- **Latency Improvement**: 2-5x faster response times for cached portions
- **Developer Experience**: Simple, intuitive API with automatic optimization

## How Bedrock Caching Works

Amazon Bedrock's Converse API supports caching through special `cachePoint` content blocks:

```json
{
  "messages": [{
    "role": "user",
    "content": [
      {"text": "Analyze these images..."},
      {"image": {"format": "jpeg", "source": {"bytes": "..."}}},
      {"cachePoint": {"type": "default"}},
      {"text": "What specific details do you see?"}
    ]
  }]
}
```

### Caching Behavior
1. **First Request**: Content before cache point is processed and written to cache
2. **Subsequent Requests**: Cached content is read instantly, only new content is processed
3. **Token Tracking**: Response includes `cacheReadInputTokensCount` and `cacheWriteInputTokensCount`

## LLM Manager Caching Architecture

### Core Components

#### 1. CacheConfig
Configuration class for cache behavior:

```python
@dataclass
class CacheConfig:
    enabled: bool = True
    strategy: CacheStrategy = CacheStrategy.CONSERVATIVE
    auto_cache_system_messages: bool = True
    cache_point_threshold: int = 100  # minimum tokens to cache
    max_cache_ttl: Optional[int] = None
```

#### 2. CacheStrategy Enum
Defines intelligent cache placement strategies:

```python
class CacheStrategy(Enum):
    CONSERVATIVE = "conservative"  # Cache only obvious repeated content
    AGGRESSIVE = "aggressive"      # Maximize caching opportunities
    CUSTOM = "custom"             # User-defined rules
```

#### 3. CachePointManager
Handles automatic cache point insertion and optimization:

```python
class CachePointManager:
    def inject_cache_points(self, messages: List[Dict], config: CacheConfig) -> List[Dict]
    def optimize_cache_placement(self, conversation_history: List[Dict]) -> List[int]
    def validate_cache_configuration(self, request: Dict) -> List[str]
```

## Usage Without MessageBuilder

### Basic Manual Caching

```python
from bestehorn_llmmanager import LLMManager
from bestehorn_llmmanager.bedrock.models.cache_structures import CacheConfig, CacheStrategy

# Enable caching (OFF by default)
cache_config = CacheConfig(
    enabled=True,
    strategy=CacheStrategy.CONSERVATIVE
)

# Initialize manager with caching
manager = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"],
    cache_config=cache_config
)

# Manually construct messages with cache points
messages = [
    {
        "role": "user",
        "content": [
            {"text": "Analyze the following images for architectural details:"},
            {"image": {"format": "jpeg", "source": {"bytes": image1_bytes}}},
            {"image": {"format": "jpeg", "source": {"bytes": image2_bytes}}},
            {"cachePoint": {"type": "default"}},  # Manual cache point
            {"text": "Focus specifically on the Gothic elements"}
        ]
    }
]

response = manager.converse(messages=messages)

# Check cache performance
cache_info = response.get_cached_tokens_info()
if cache_info:
    print(f"Cache hit: {cache_info['cache_read_tokens']} tokens")
    print(f"Cache efficiency: {response.get_cache_efficiency()}")
```

### Automatic Cache Point Injection

With caching enabled, LLM Manager automatically optimizes cache placement:

```python
# Messages without explicit cache points
messages = [
    {
        "role": "user",
        "content": [
            {"text": "Long shared context..."},  # 800 tokens
            {"image": {"format": "jpeg", "source": {"bytes": img1}}},  # 450 tokens
            {"image": {"format": "jpeg", "source": {"bytes": img2}}},  # 450 tokens
            {"text": "Unique question"}  # 100 tokens
        ]
    }
]

# CachePointManager automatically inserts cache point after shared content
# Result: 1700 tokens cached, 100 tokens processed per request
```

## Usage With MessageBuilder

### Enhanced MessageBuilder API

#### 1. Explicit Cache Point Control

```python
from bestehorn_llmmanager import create_user_message

# Manual cache point placement
message = create_user_message()
    .add_text("Analyze these architectural images...")
    .add_image_bytes(image1_bytes, filename="building1.jpg")
    .add_image_bytes(image2_bytes, filename="building2.jpg")
    .add_cache_point()  # Explicit cache point
    .add_text("Focus on the Gothic architectural elements")
    .build()

response = manager.converse(messages=[message])
```

#### 2. Automatic Cache Optimization

```python
# Initialize MessageBuilder with cache config
cache_config = CacheConfig(
    enabled=True,
    strategy=CacheStrategy.CONSERVATIVE
)

message = create_user_message(cache_config=cache_config)
    .add_text("Analyze these images...")  # Automatically marked cacheable
    .add_image_bytes(image1_bytes)       # Automatically marked cacheable
    .add_image_bytes(image2_bytes)       # Automatically marked cacheable
    .add_text("What specific details stand out?")  # Unique content
    .build()  # Cache points auto-inserted during build
```

#### 3. Content Marking Approach

```python
# Fine-grained control over cacheability
message = create_user_message()
    .add_text("System context...", cacheable=True)
    .add_image_bytes(shared_image, cacheable=True)
    .add_text("User-specific question", cacheable=False)
    .add_cache_point()  # Optional explicit control
    .add_text("Additional unique content")
    .build()
```

### MessageBuilder Enhancements

New methods added to `ConverseMessageBuilder`:

```python
def add_cache_point(self, cache_type: str = "default") -> "ConverseMessageBuilder":
    """Add an explicit cache point at the current position."""

def add_text(self, text: str, cacheable: Optional[bool] = None) -> "ConverseMessageBuilder":
    """Add text with optional cacheability marking."""

def add_image_bytes(self, bytes: bytes, format: Optional[ImageFormatEnum] = None, 
                   filename: Optional[str] = None, cacheable: Optional[bool] = None) -> "ConverseMessageBuilder":
    """Add image with optional cacheability marking."""
```

## Caching Strategies

### 1. CONSERVATIVE Strategy (Recommended Default)

**Philosophy**: Only cache content that's clearly beneficial and safe

**Behavior**:
- Caches content blocks totaling > 1000 tokens
- Single cache point after all shared content
- Minimal overhead, predictable behavior

**Example**:
```
[shared_text + images] → CACHE_POINT → [unique_content]
```

**Best For**: Most use cases, especially sequential prompts with clear shared/unique boundaries

### 2. AGGRESSIVE Strategy

**Philosophy**: Maximize caching opportunities for best performance

**Behavior**:
- Multiple cache points for granular control
- Caches smaller content blocks (> 500 tokens)
- Better recovery from partial content changes

**Example**:
```
[text] → CACHE_POINT → [image1] → CACHE_POINT → [image2] → CACHE_POINT → [unique]
```

**Best For**: High-volume applications where maximum efficiency is critical

### 3. CUSTOM Strategy

**Philosophy**: User-defined rules for specific patterns

**Configuration**:
```python
cache_config = CacheConfig(
    strategy=CacheStrategy.CUSTOM,
    custom_rules={
        "cache_text_blocks_over": 500,
        "cache_all_images": True,
        "cache_repeated_content": True,
        "min_cache_benefit": 0.7  # Only cache if >70% benefit
    }
)
```

**Best For**: Specialized use cases with unique content patterns

## Performance Benefits

### Token Usage Comparison

For 10 sequential prompts with 1700 shared tokens and 100 unique tokens each:

| Metric | Without Caching | With Caching | Improvement |
|--------|----------------|--------------|-------------|
| Total Input Tokens | 18,000 | 2,700 | 85% reduction |
| Cache Write Tokens | 0 | 1,700 | One-time cost |
| Cache Read Tokens | 0 | 15,300 | 9x reuse |
| Estimated Cost | $0.54 | $0.08 | 85% savings |
| Average Latency | 3.2s | 0.8s | 4x faster |

### Cache Efficiency Metrics

```python
response.get_cache_efficiency()
# Returns:
{
    'cache_hit_ratio': 0.89,  # 89% of tokens from cache
    'cache_savings_tokens': 15300,
    'cache_savings_cost': '$0.46',
    'latency_reduction_ms': 2400
}
```

## Best Practices

### 1. Content Organization
- Place shared content first in messages
- Group related cacheable content together
- Keep unique content at the end

### 2. Cache Point Placement
- After system prompts and instructions
- After shared context and examples
- Before user-specific questions

### 3. Strategy Selection
- Start with CONSERVATIVE for most use cases
- Use AGGRESSIVE for high-volume, predictable patterns
- Implement CUSTOM for specialized requirements

### 4. Monitoring
- Track cache hit ratios
- Monitor cost savings
- Analyze latency improvements
- Adjust strategy based on metrics

## Example: Sequential Prompts with Shared Content

### Scenario
10 prompts analyzing the same images with different focus areas:
- Shared: 800 tokens of text + 900 tokens of images (2 images)
- Unique: 100-200 tokens per prompt

### Implementation

```python
from bestehorn_llmmanager import LLMManager, create_user_message
from bestehorn_llmmanager.bedrock.models.cache_structures import CacheConfig, CacheStrategy

# Configure caching
cache_config = CacheConfig(
    enabled=True,
    strategy=CacheStrategy.CONSERVATIVE,
    cache_point_threshold=1000  # Your shared content is ~1700 tokens
)

# Initialize manager
manager = LLMManager(
    models=["Claude 3 Haiku"],
    regions=["us-east-1"],
    cache_config=cache_config
)

# Shared content
shared_text = "Analyze the following architectural images..."
shared_images = [image1_bytes, image2_bytes]

# Unique prompts
unique_prompts = [
    "Focus on the Gothic architectural elements",
    "Examine the lighting and shadow composition",
    "Identify historical period indicators",
    # ... 7 more prompts
]

# Process prompts efficiently
responses = []
for i, unique_content in enumerate(unique_prompts):
    # Build message with automatic cache optimization
    message = create_user_message(cache_config=cache_config)
        .add_text(shared_text)
        .add_image_bytes(shared_images[0], filename="architecture1.jpg")
        .add_image_bytes(shared_images[1], filename="architecture2.jpg")
        .add_cache_point()  # Optional - auto-inserted if not specified
        .add_text(unique_content)
        .build()
    
    response = manager.converse(messages=[message])
    
    # Monitor cache performance
    if i == 0:
        print(f"First request - Cache write: {response.get_cached_tokens_info()}")
    else:
        cache_info = response.get_cached_tokens_info()
        print(f"Request {i+1} - Cache hit: {cache_info['cache_read_tokens']} tokens")
    
    responses.append(response)

# Analyze overall efficiency
total_cache_savings = sum(r.get_cache_efficiency()['cache_savings_tokens'] for r in responses[1:])
print(f"Total tokens saved: {total_cache_savings}")
print(f"Efficiency: {(total_cache_savings / (len(responses) * 1700)) * 100:.1f}%")
```

### Expected Results

1. **First Request**: Cache MISS → writes 1700 tokens
2. **Requests 2-10**: Cache HIT → reads 1700 tokens each
3. **Total Savings**: 15,300 tokens (85% reduction)
4. **Performance**: 4x faster average response time

## Error Handling

### Graceful Degradation (Default)

LLM Manager automatically handles cases where caching is not supported for specific model/region combinations:

```python
class CacheErrorHandling(Enum):
    GRACEFUL_DEGRADATION = "graceful"  # Default: silently disable caching
    WARN_AND_CONTINUE = "warn"         # Log warning but continue
    FAIL_FAST = "fail"                 # Fail immediately (for testing)
```

### Cache Availability Tracking

The system tracks which model/region combinations support caching:

```python
# Configuration with error handling
cache_config = CacheConfig(
    enabled=True,
    strategy=CacheStrategy.CONSERVATIVE,
    error_handling=CacheErrorHandling.GRACEFUL_DEGRADATION,
    cache_availability_check=True,  # Pre-check support
    blacklist_duration_minutes=60   # Remember unsupported combos
)
```

### Error Scenarios

1. **Model doesn't support caching**: Automatically retries without cache points
2. **Region limitation**: Falls back to non-cached request
3. **Temporary failures**: Blacklists combination temporarily

Example with mixed models:
```python
manager = LLMManager(
    models=["Claude 3 Haiku", "Llama 2"],  # Mix of cache/non-cache models
    regions=["us-east-1", "eu-west-1"],
    cache_config=cache_config
)

response = manager.converse(messages=[...])

# Check warnings for cache fallbacks
if response.warnings:
    print(response.warnings)
    # Output: ['Caching disabled for Llama 2 in us-east-1']
```

## Future Enhancements

While not covered in this initial implementation, planned enhancements include:

1. **Parallel Processing Support**: Cache sharing across parallel requests
2. **Region-Aware Caching**: Advanced optimization across regions
3. **Cache Warming**: Pre-populate cache for known patterns
4. **Cache Analytics Dashboard**: Detailed performance tracking
5. **Cache Invalidation API**: Manual cache management

## Conclusion

LLM Manager's caching support transforms Bedrock's basic caching mechanism into an intelligent, automated system that dramatically reduces costs and latency. Whether using manual message construction or the enhanced MessageBuilder, developers can easily implement efficient caching strategies tailored to their specific use cases.

The combination of automatic optimization, flexible strategies, and comprehensive analytics makes it simple to achieve 80-90% cost reduction and 2-5x performance improvements for repetitive prompt patterns.
