# Examples Directory

This directory contains examples demonstrating various features of the bestehorn-llmmanager package.

## Basic Examples

### `log_level_example.py`
Demonstrates how to configure logging levels for LLMManager to control the amount of output.

**Key concepts:**
- Setting log levels (DEBUG, INFO, WARNING, ERROR)
- Controlling verbosity of manager operations

### `streaming_example.py`
Demonstrates real-time streaming responses using the `converse_stream()` method.

**Key concepts:**
- Streaming API usage
- Real-time token generation
- Error recovery during streaming
- Performance comparison with regular responses

### `caching_example.py`
Demonstrates Bedrock's prompt caching feature for optimizing costs and performance.

**Key concepts:**
- Prompt caching with CacheConfig
- Cache points and strategies
- Cost optimization for repeated content

**Note:** This is about Bedrock prompt caching, not model catalog caching. For catalog caching, see the catalog examples below.

## Model Catalog Examples

The new BedrockModelCatalog system provides flexible model data management with multiple cache modes.

### `catalog_basic_usage.py`
Introduction to BedrockModelCatalog with fundamental operations.

**Key concepts:**
- Basic initialization
- Checking model availability
- Getting model information
- Listing and filtering models
- Inspecting catalog metadata

**Best for:** Getting started with the catalog system

### `catalog_cache_modes.py`
Comprehensive demonstration of the three cache modes (FILE, MEMORY, NONE).

**Key concepts:**
- FILE mode: Persistent file-based caching
- MEMORY mode: In-memory caching (process lifetime)
- NONE mode: No caching (always fresh)
- Performance comparison
- Cache configuration and invalidation

**Best for:** Understanding cache modes and choosing the right one

### `catalog_lambda_usage.py`
Lambda-specific usage patterns and best practices.

**Key concepts:**
- Global initialization pattern (recommended)
- Lazy initialization pattern
- Memory-only cache for read-only environments
- No-cache pattern for security-critical scenarios
- Error handling and fallback strategies
- Model availability validation

**Best for:** AWS Lambda deployments

## Lambda Examples

These examples demonstrate complete Lambda function implementations using different cache modes.

### `lambda_unified_model_manager.py`
Lambda example using FILE cache mode with /tmp directory.

**Cache mode:** FILE  
**Use case:** Standard Lambda with /tmp access  
**Benefits:** Fast warm starts, persistent cache

### `lambda_llm_manager_with_model_cache.py`
Lambda example using MEMORY cache mode for read-only environments.

**Cache mode:** MEMORY  
**Use case:** Read-only Lambda environments  
**Benefits:** No file system access needed, works in restricted environments

### `lambda_complete_serverless_app.py`
Complete serverless application using NONE cache mode.

**Cache mode:** NONE  
**Use case:** Security-critical environments, always-fresh data  
**Benefits:** Always latest model data, bundled fallback for reliability

**Features:**
- Multiple operations (converse, stream, list_models, check_availability)
- Comprehensive error handling
- Model availability checks

## Cache Mode Comparison

| Cache Mode | File I/O | Warm Start | Use Case |
|------------|----------|------------|----------|
| FILE | Yes | Fast | Production, Lambda with /tmp |
| MEMORY | No | Fast | Read-only environments |
| NONE | No | Slow | Security-critical, always fresh |

## Running Examples

### Prerequisites

1. Install the package:
```bash
pip install bestehorn-llmmanager
```

2. Configure AWS credentials:
```bash
aws configure
```

Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### Running Locally

```bash
# Basic examples
python examples/log_level_example.py
python examples/streaming_example.py
python examples/caching_example.py

# Catalog examples
python examples/catalog_basic_usage.py
python examples/catalog_cache_modes.py
python examples/catalog_lambda_usage.py

# Lambda examples (local testing)
python examples/lambda_unified_model_manager.py
python examples/lambda_llm_manager_with_model_cache.py
python examples/lambda_complete_serverless_app.py
```

### Deploying to Lambda

1. Package your Lambda function with dependencies:
```bash
pip install bestehorn-llmmanager -t package/
cp examples/lambda_unified_model_manager.py package/
cd package && zip -r ../lambda_function.zip .
```

2. Create Lambda function:
```bash
aws lambda create-function \
  --function-name bedrock-llm-function \
  --runtime python3.9 \
  --handler lambda_unified_model_manager.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-bedrock-role
```

3. Test the function:
```bash
aws lambda invoke \
  --function-name bedrock-llm-function \
  --payload '{"prompt": "Hello, how are you?"}' \
  response.json
```

## Migration from Old Managers

If you're migrating from the deprecated `UnifiedModelManager`, `ModelManager`, or `CRISManager`:

**Old code:**
```python
from bestehorn_llmmanager.bedrock.UnifiedModelManager import UnifiedModelManager

umm = UnifiedModelManager()
umm.refresh_unified_data()
```

**New code:**
```python
from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog

catalog = BedrockModelCatalog()  # Handles data fetching automatically
```

The new system:
- Automatically fetches and caches data
- Supports multiple cache modes
- Includes bundled fallback data
- Works seamlessly with LLMManager

See the catalog examples for detailed usage patterns.

## Additional Resources

- **Documentation:** See `docs/forLLMConsumption.md` for complete API reference
- **Migration Guide:** See `docs/MIGRATION_GUIDE.md` for detailed migration instructions
- **Project Structure:** See `docs/ProjectStructure.md` for architecture overview

## Support

For issues or questions:
- GitHub Issues: [Repository URL]
- Documentation: `docs/` directory
- Examples: This directory

## License

See LICENSE file in the root directory.
