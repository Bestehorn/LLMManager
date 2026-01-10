# Inference Profile Support - Troubleshooting Guide

## Overview

This guide helps you troubleshoot common issues related to AWS Bedrock inference profile support in LLMManager. Inference profiles (also called CRIS profiles) are required for certain newer models like Claude Sonnet 4.5.

## Table of Contents

1. [Common Errors](#common-errors)
2. [Checking Access Methods](#checking-access-methods)
3. [Missing Profile Information](#missing-profile-information)
4. [Access Method Statistics](#access-method-statistics)
5. [Logging and Debugging](#logging-and-debugging)
6. [Performance Issues](#performance-issues)
7. [Parallel Processing Issues](#parallel-processing-issues)

## Common Errors

### Error: "Model requires inference profile but none available"

**Symptom:**
```
WARNING: Model 'anthropic.claude-sonnet-4-20250514-v1:0' requires inference profile 
in 'us-east-1' but no profile information available in catalog
```

**Cause:**
The model requires an inference profile for access, but the catalog doesn't have profile information for that model/region combination.

**Solutions:**

1. **Refresh catalog data:**
```python
from bestehorn_llmmanager import LLMManager

manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"]
)

# Force refresh of model data
manager.refresh_model_data()

# Try request again
response = manager.converse(messages=[message])
```

2. **Use fallback models:**
```python
# Add fallback models that support direct access
manager = LLMManager(
    models=["Claude Sonnet 4.5", "Claude 3 Haiku"],  # Haiku as fallback
    regions=["us-east-1", "us-west-2"]
)

response = manager.converse(messages=[message])
```

3. **Try different regions:**
```python
# Some regions may have better profile coverage
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1", "us-west-2", "eu-west-1"]  # Multiple regions
)

response = manager.converse(messages=[message])
```

### Error: "ValidationException: with on-demand throughput isn't supported"

**Symptom:**
```
ValidationException: Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0 
with on-demand throughput isn't supported. Retry your request with the ID or ARN 
of an inference profile that contains this model.
```

**Cause:**
This error should be automatically handled by the system. If you're seeing this error, the automatic profile retry may not be working.

**Solutions:**

1. **Check LLMManager version:**
```python
import bestehorn_llmmanager
print(f"Version: {bestehorn_llmmanager.__version__}")
# Should be >= 0.4.0 for automatic profile support
```

2. **Enable INFO logging to see retry flow:**
```python
import logging

manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"],
    log_level=logging.INFO  # See profile retry attempts
)

response = manager.converse(messages=[message])
```

3. **Check response warnings:**
```python
response = manager.converse(messages=[message])

if not response.success:
    print(f"Error: {response.get_last_error()}")
    
warnings = response.get_warnings()
for warning in warnings:
    print(f"Warning: {warning}")
```

### Error: "All retry attempts exhausted"

**Symptom:**
```
RetryExhaustedError: All retry attempts exhausted. Models tried: ['Claude Sonnet 4.5']. 
All models require inference profiles.
```

**Cause:**
All configured models require inference profiles, but none of the profiles are working.

**Solutions:**

1. **Check IAM permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream",
    "bedrock:ListInferenceProfiles"
  ],
  "Resource": "*"
}
```

2. **Verify model availability in region:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

catalog = BedrockModelCatalog()

# Check if model is available
is_available = catalog.is_model_available(
    model_name="Claude Sonnet 4.5",
    region="us-east-1"
)
print(f"Available: {is_available}")

# Get detailed model info
model_info = catalog.get_model_info(
    model_name="Claude Sonnet 4.5",
    region="us-east-1"
)

if model_info:
    print(f"Model ID: {model_info.model_id}")
    print(f"Profile ID: {model_info.inference_profile_id}")
    print(f"Access method: {model_info.access_method.value}")
```

3. **Add fallback models:**
```python
manager = LLMManager(
    models=[
        "Claude Sonnet 4.5",
        "Claude 3.5 Sonnet",  # Fallback 1
        "Claude 3 Haiku"      # Fallback 2
    ],
    regions=["us-east-1", "us-west-2"]
)
```

## Checking Access Methods

### Check Which Access Method Was Used

```python
from bestehorn_llmmanager import LLMManager, create_user_message

manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"]
)

message = create_user_message().add_text("Hello").build()
response = manager.converse(messages=[message])

if response.success:
    # Check access method
    print(f"Access method: {response.access_method_used}")
    # Output: "direct", "regional_cris", or "global_cris"
    
    # Check if profile was used
    print(f"Profile used: {response.inference_profile_used}")
    # Output: True or False
    
    # Get profile ID if used
    if response.inference_profile_used:
        print(f"Profile ID: {response.inference_profile_id}")
        # Output: Profile ARN or ID
    
    # Model and region information
    print(f"Model: {response.model_used}")
    print(f"Region: {response.region_used}")
```

### Check Access Method for Multiple Requests

```python
# Track access methods across multiple requests
access_methods = []

for i in range(10):
    message = create_user_message().add_text(f"Request {i}").build()
    response = manager.converse(messages=[message])
    
    if response.success:
        access_methods.append(response.access_method_used)
        print(f"Request {i}: {response.access_method_used}")

# Analyze distribution
from collections import Counter
distribution = Counter(access_methods)
print(f"\nAccess method distribution:")
for method, count in distribution.items():
    print(f"  {method}: {count}")
```

### Check Access Method in Parallel Processing

```python
from bestehorn_llmmanager import ParallelLLMManager
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

parallel_manager = ParallelLLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1", "us-west-2"]
)

requests = [
    BedrockConverseRequest(request_id=f"req-{i}", messages=[message])
    for i in range(5)
]

parallel_response = parallel_manager.converse_parallel(requests=requests)

# Check access method for each request
for request_id, response in parallel_response.request_responses.items():
    if response.success:
        print(f"{request_id}: {response.access_method_used}")

# Check aggregated statistics
stats = parallel_response.parallel_execution_stats
print(f"\nAccess method distribution:")
print(f"  Direct: {stats.access_method_distribution.get('direct', 0)}")
print(f"  Regional CRIS: {stats.access_method_distribution.get('regional_cris', 0)}")
print(f"  Global CRIS: {stats.access_method_distribution.get('global_cris', 0)}")
```

## Missing Profile Information

### Diagnose Missing Profile Information

```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

catalog = BedrockModelCatalog()

# Check model availability
model_name = "Claude Sonnet 4.5"
region = "us-east-1"

is_available = catalog.is_model_available(model_name, region)
print(f"Model available: {is_available}")

if is_available:
    model_info = catalog.get_model_info(model_name, region)
    
    print(f"\nModel Information:")
    print(f"  Model ID: {model_info.model_id}")
    print(f"  Inference Profile: {model_info.inference_profile_id}")
    print(f"  Access Method: {model_info.access_method.value}")
    print(f"  Has Direct Access: {model_info.has_direct_access}")
    print(f"  Has Regional CRIS: {model_info.has_regional_cris}")
    print(f"  Has Global CRIS: {model_info.has_global_cris}")
else:
    print(f"Model '{model_name}' not available in region '{region}'")
    
    # List available models in region
    available_models = catalog.list_models(region=region)
    print(f"\nAvailable models in {region}:")
    for model in available_models[:10]:  # Show first 10
        print(f"  - {model.model_name}")
```

### Refresh Catalog Data

```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode

# Force refresh from AWS API
catalog = BedrockModelCatalog(
    force_refresh=True,  # Bypass cache
    cache_mode=CacheMode.FILE
)

# Check if model is now available
model_info = catalog.get_model_info("Claude Sonnet 4.5", "us-east-1")
if model_info:
    print(f"Profile ID: {model_info.inference_profile_id}")
else:
    print("Model still not available")
```

### Check Catalog Metadata

```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

catalog = BedrockModelCatalog()

# Get catalog metadata
metadata = catalog.get_catalog_metadata()

print(f"Catalog Information:")
print(f"  Source: {metadata.source.value}")  # API, CACHE, or BUNDLED
print(f"  Retrieved: {metadata.retrieval_timestamp}")
print(f"  Regions queried: {len(metadata.api_regions_queried)}")

if metadata.source == "bundled":
    print(f"  Bundled version: {metadata.bundled_data_version}")
    print("\nUsing bundled data. Consider refreshing for latest models:")
    print("  catalog = BedrockModelCatalog(force_refresh=True)")
elif metadata.source == "cache":
    print(f"  Cache file: {metadata.cache_file_path}")
```

## Access Method Statistics

### Get Global Access Method Statistics

```python
from bestehorn_llmmanager.bedrock.tracking import AccessMethodTracker

# Get singleton tracker instance
tracker = AccessMethodTracker.get_instance()

# Get comprehensive statistics
stats = tracker.get_statistics()

print("Access Method Tracker Statistics:")
print(f"  Total tracked combinations: {stats['total_tracked']}")
print(f"  Profile-required models: {stats['profile_required_count']}")
print(f"  Direct-access models: {stats['direct_access_count']}")

# Access method distribution
print(f"\nAccess Method Distribution:")
for method, count in stats.get('access_method_distribution', {}).items():
    print(f"  {method}: {count}")

# Recently learned preferences
print(f"\nRecently Learned Preferences:")
for combo, pref in list(stats.get('preferences', {}).items())[:5]:
    model_id, region = combo
    print(f"  {model_id} in {region}: {pref.get_preferred_method()}")
```

### Check Specific Model/Region Preference

```python
from bestehorn_llmmanager.bedrock.tracking import AccessMethodTracker

tracker = AccessMethodTracker.get_instance()

# Check if model requires profile
model_id = "anthropic.claude-sonnet-4-20250514-v1:0"
region = "us-east-1"

requires_profile = tracker.requires_profile(model_id, region)
print(f"Requires profile: {requires_profile}")

# Get learned preference
preference = tracker.get_preference(model_id, region)
if preference:
    print(f"Preferred method: {preference.get_preferred_method()}")
    print(f"Learned from error: {preference.learned_from_error}")
    print(f"Last updated: {preference.last_updated}")
else:
    print("No preference learned yet")
```

### Monitor Access Method Learning

```python
from bestehorn_llmmanager import LLMManager, create_user_message
from bestehorn_llmmanager.bedrock.tracking import AccessMethodTracker

manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"]
)

tracker = AccessMethodTracker.get_instance()

# Before requests
stats_before = tracker.get_statistics()
print(f"Before: {stats_before['total_tracked']} tracked combinations")

# Execute requests
for i in range(5):
    message = create_user_message().add_text(f"Request {i}").build()
    response = manager.converse(messages=[message])
    print(f"Request {i}: {response.access_method_used}")

# After requests
stats_after = tracker.get_statistics()
print(f"\nAfter: {stats_after['total_tracked']} tracked combinations")
print(f"New preferences learned: {stats_after['total_tracked'] - stats_before['total_tracked']}")
```

## Logging and Debugging

### Enable Detailed Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create manager with DEBUG logging
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"],
    log_level=logging.DEBUG
)

# Execute request - will show detailed profile retry flow
message = create_user_message().add_text("Hello").build()
response = manager.converse(messages=[message])
```

### Log Levels and What They Show

**WARNING (Default):**
- Profile requirement detection
- Missing profile information
- Profile unavailability

```python
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"],
    log_level=logging.WARNING  # Default
)
```

**INFO:**
- Profile selection
- Profile retry success
- Access method switches
- All WARNING messages

```python
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"],
    log_level=logging.INFO
)
```

**DEBUG:**
- Access method learning
- Preference updates
- Detailed retry flow
- All INFO and WARNING messages

```python
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"],
    log_level=logging.DEBUG
)
```

### Capture Logs Programmatically

```python
import logging
from io import StringIO

# Create string buffer for logs
log_buffer = StringIO()
handler = logging.StreamHandler(log_buffer)
handler.setLevel(logging.INFO)

# Add handler to logger
logger = logging.getLogger('bestehorn_llmmanager')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Execute request
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"]
)

message = create_user_message().add_text("Hello").build()
response = manager.converse(messages=[message])

# Get captured logs
logs = log_buffer.getvalue()
print("Captured logs:")
print(logs)

# Analyze logs
if "inference profile" in logs.lower():
    print("\nProfile was used in this request")
if "profile requirement" in logs.lower():
    print("Profile requirement was detected")
```

## Performance Issues

### Slow First Request

**Symptom:**
First request takes longer than expected.

**Cause:**
Profile requirement detection adds one retry attempt on first request.

**Solution:**
This is expected behavior. Subsequent requests will be faster due to learned preferences.

```python
import time
from bestehorn_llmmanager import LLMManager, create_user_message

manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"]
)

message = create_user_message().add_text("Hello").build()

# First request (may include profile detection)
start = time.time()
response1 = manager.converse(messages=[message])
duration1 = time.time() - start
print(f"First request: {duration1:.2f}s")

# Second request (uses learned preference)
start = time.time()
response2 = manager.converse(messages=[message])
duration2 = time.time() - start
print(f"Second request: {duration2:.2f}s")

print(f"Speedup: {duration1/duration2:.1f}x")
```

### Multiple Profile Retries

**Symptom:**
Seeing multiple profile retry attempts.

**Cause:**
Multiple models or regions requiring profiles.

**Solution:**
This is expected when trying multiple model/region combinations. Check retry statistics:

```python
response = manager.converse(messages=[message])

# Check retry statistics
stats = manager.get_retry_stats()
print(f"Total attempts: {stats['total_attempts']}")
print(f"Successful attempts: {stats['successful_attempts']}")
print(f"Failed attempts: {stats['failed_attempts']}")

# Check which models/regions were tried
for attempt in response.attempts:
    print(f"Attempt {attempt.attempt_number}:")
    print(f"  Model: {attempt.model_id}")
    print(f"  Region: {attempt.region}")
    print(f"  Success: {attempt.success}")
```

## Parallel Processing Issues

### Inconsistent Access Methods in Parallel

**Symptom:**
Different requests using different access methods in parallel execution.

**Cause:**
This is expected behavior - each request independently determines optimal access method.

**Solution:**
This is normal. Monitor distribution:

```python
from bestehorn_llmmanager import ParallelLLMManager
from bestehorn_llmmanager.bedrock.models.parallel_structures import BedrockConverseRequest

parallel_manager = ParallelLLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1", "us-west-2"]
)

requests = [
    BedrockConverseRequest(request_id=f"req-{i}", messages=[message])
    for i in range(10)
]

parallel_response = parallel_manager.converse_parallel(requests=requests)

# Check access method distribution
stats = parallel_response.parallel_execution_stats
print("Access method distribution:")
for method, count in stats.access_method_distribution.items():
    print(f"  {method}: {count}")
```

### Parallel Requests Slower Than Expected

**Symptom:**
Parallel processing not showing expected speedup.

**Cause:**
Profile detection may add overhead to parallel requests.

**Solution:**
1. Warm up the access method tracker:

```python
# Execute a few requests to learn preferences
for i in range(3):
    message = create_user_message().add_text("Warmup").build()
    manager.converse(messages=[message])

# Now execute parallel requests
parallel_response = parallel_manager.converse_parallel(requests=requests)
```

2. Check parallel configuration:

```python
from bestehorn_llmmanager.bedrock.models.parallel_structures import ParallelProcessingConfig

parallel_config = ParallelProcessingConfig(
    max_concurrent_requests=10,  # Increase for more parallelism
    request_timeout_seconds=120
)

parallel_manager = ParallelLLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1", "us-west-2"],
    parallel_config=parallel_config
)
```

## Best Practices

### 1. Use Multiple Regions

```python
# Good: Multiple regions for redundancy
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1", "us-west-2", "eu-west-1"]
)
```

### 2. Include Fallback Models

```python
# Good: Fallback models with different access requirements
manager = LLMManager(
    models=["Claude Sonnet 4.5", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"]
)
```

### 3. Enable Appropriate Logging

```python
import logging

# Development: Use INFO or DEBUG
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"],
    log_level=logging.INFO
)

# Production: Use WARNING (default)
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"],
    log_level=logging.WARNING
)
```

### 4. Monitor Access Method Statistics

```python
from bestehorn_llmmanager.bedrock.tracking import AccessMethodTracker

# Periodically check statistics
tracker = AccessMethodTracker.get_instance()
stats = tracker.get_statistics()

# Alert if too many profile requirements
if stats['profile_required_count'] > stats['direct_access_count']:
    print("Warning: Most models require profiles")
```

### 5. Refresh Catalog Periodically

```python
# Refresh catalog daily or when new models are released
manager.refresh_model_data()
```

## Getting Help

If you're still experiencing issues:

1. **Check version:**
```python
import bestehorn_llmmanager
print(f"Version: {bestehorn_llmmanager.__version__}")
```

2. **Enable DEBUG logging:**
```python
import logging
manager = LLMManager(
    models=["Claude Sonnet 4.5"],
    regions=["us-east-1"],
    log_level=logging.DEBUG
)
```

3. **Collect diagnostics:**
```python
# Response information
print(f"Success: {response.success}")
print(f"Access method: {response.access_method_used}")
print(f"Model used: {response.model_used}")
print(f"Region used: {response.region_used}")
print(f"Warnings: {response.get_warnings()}")

# Tracker statistics
tracker = AccessMethodTracker.get_instance()
stats = tracker.get_statistics()
print(f"Tracker stats: {stats}")

# Catalog metadata
catalog = BedrockModelCatalog()
metadata = catalog.get_catalog_metadata()
print(f"Catalog source: {metadata.source.value}")
```

4. **Check GitHub issues:** [bestehorn-llmmanager issues](https://github.com/yourusername/bestehorn-llmmanager/issues)

5. **Report issue with:**
   - LLMManager version
   - Python version
   - Model and region configuration
   - Complete error message
   - DEBUG logs
   - Diagnostic information
