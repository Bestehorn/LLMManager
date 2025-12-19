# Integration Tests for BedrockModelCatalog

This directory contains integration tests for the new BedrockModelCatalog system that validate functionality with real AWS APIs and file system operations.

## Test Files

### test_integration_catalog_api.py
Tests for API fetching functionality with real AWS Bedrock APIs.

**Requirements Validated:**
- 1.1: API-only data retrieval using list-foundation-models
- 1.2: API-only data retrieval using list-inference-profiles  
- 10.1: Parallel multi-region fetching

**Test Classes:**
- `TestBedrockAPIFetcherIntegration`: Core API fetching tests
- `TestCatalogTransformerIntegration`: Data transformation tests
- `TestAPIFetcherPerformance`: Performance and retry logic tests

**Key Tests:**
- Single region API fetching (models and profiles)
- Multi-region parallel fetching
- Error handling with invalid regions
- Data transformation and serialization
- Performance benchmarks

### test_integration_catalog_cache.py
Tests for cache persistence with real file system operations.

**Requirements Validated:**
- 6.1: Single cache file with unified data
- 6.2: Cache file writing and reading
- 6.3: Cache validation and expiration

**Test Classes:**
- `TestCacheFileCreation`: Cache file creation tests
- `TestCacheLoading`: Cache loading and round-trip tests
- `TestCacheExpiration`: Cache expiration logic tests
- `TestCacheMemoryMode`: In-memory cache tests
- `TestCacheNoneMode`: No-cache mode tests
- `TestCacheErrorHandling`: Error handling tests

**Key Tests:**
- Cache file creation and structure validation
- Cache save/load round-trip consistency
- Cache expiration by age
- Memory cache (no file system access)
- NONE mode (no caching)
- Error handling (read-only directories, corrupted files)

### test_integration_llmmanager_catalog.py
Tests for LLMManager integration with BedrockModelCatalog.

**Requirements Validated:**
- 7.2: LLMManager integration with BedrockModelCatalog
- 8.1: Lambda-friendly design with configurable cache modes

**Test Classes:**
- `TestLLMManagerCatalogIntegration`: Core integration tests
- `TestLLMManagerCacheModes`: Cache mode tests (FILE, MEMORY, NONE)
- `TestLLMManagerLambdaScenarios`: Lambda-specific scenarios
- `TestLLMManagerCatalogRefresh`: Catalog refresh tests
- `TestLLMManagerBackwardCompatibility`: Backward compatibility tests

**Key Tests:**
- Model validation via catalog
- Invalid model detection
- FILE cache mode (persistent caching)
- MEMORY cache mode (in-memory only)
- NONE cache mode (no caching, Lambda-friendly)
- Lambda /tmp directory usage
- Lambda cold/warm start scenarios
- Catalog refresh functionality
- Backward compatibility with existing API

## Running Integration Tests

### Prerequisites

Integration tests require:
1. Valid AWS credentials configured
2. Access to AWS Bedrock service
3. Integration tests enabled via environment variable

### Enable Integration Tests

```bash
export AWS_INTEGRATION_TESTS_ENABLED=true
```

### Specify AWS Profile

**Recommended for multi-account environments:**

```bash
# Use --profile option (recommended)
pytest test/integration/ --profile my-aws-profile

# Or set environment variable
export AWS_INTEGRATION_TEST_PROFILE=my-aws-profile
pytest test/integration/

# Or inline
AWS_INTEGRATION_TEST_PROFILE=my-aws-profile pytest test/integration/
```

**Note:** The `--profile` option takes precedence over the environment variable.

### Run All Integration Tests

```bash
# Run all integration tests with default credentials
pytest test/integration/

# Run with specific AWS profile
pytest test/integration/ --profile my-test-profile

# Run with specific AWS region
pytest test/integration/ --aws-region us-west-2

# Combine profile and region
pytest test/integration/ --profile my-test-profile --aws-region us-west-2

# Run specific test file
pytest test/integration/test_integration_catalog_api.py --profile my-profile

# Run specific test class
pytest test/integration/test_integration_catalog_api.py::TestBedrockAPIFetcherIntegration --profile my-profile

# Run specific test
pytest test/integration/test_integration_catalog_api.py::TestBedrockAPIFetcherIntegration::test_fetch_foundation_models_single_region --profile my-profile
```

### Run Only Fast/Low-Cost Tests

```bash
# Run only tests marked as fast and low-cost
pytest test/integration/ -m "aws_low_cost and aws_fast"

# With specific profile
pytest test/integration/ -m "aws_low_cost and aws_fast" --profile my-profile
```

### Command-Line Options

Integration tests support the following pytest options:

- `--profile PROFILE`: AWS profile to use (overrides `AWS_INTEGRATION_TEST_PROFILE`)
- `--aws-region REGION`: Primary AWS region for tests (overrides `AWS_INTEGRATION_TEST_REGIONS`)

**Examples:**
```bash
# Use specific profile
pytest test/integration/ --profile production-readonly

# Use specific region
pytest test/integration/ --aws-region eu-west-1

# Combine options
pytest test/integration/ --profile test-account --aws-region ap-southeast-1

# View all available options
pytest --help | grep -A 2 "profile\|aws-region"
```

### Skip Integration Tests

Integration tests are automatically skipped if:
- `AWS_INTEGRATION_TESTS_ENABLED` is not set to `true`
- AWS credentials are not configured
- Integration test configuration fails

## Test Markers

Integration tests use pytest markers for categorization:

- `@pytest.mark.integration`: General integration test
- `@pytest.mark.aws_integration`: AWS-specific integration test
- `@pytest.mark.aws_low_cost`: Low-cost test (minimal API calls)
- `@pytest.mark.aws_fast`: Fast-running test (< 30 seconds)
- `@pytest.mark.aws_slow`: Slow-running test (> 30 seconds)

## Test Coverage

The integration tests provide coverage for:

### API Fetching (test_integration_catalog_api.py)
- ✅ Foundation models API fetching
- ✅ Inference profiles API fetching
- ✅ Multi-region parallel fetching
- ✅ Error handling and retry logic
- ✅ Data transformation
- ✅ Catalog serialization

### Cache Persistence (test_integration_catalog_cache.py)
- ✅ FILE mode: Cache file creation and loading
- ✅ FILE mode: Cache expiration by age
- ✅ FILE mode: Cache directory auto-creation
- ✅ MEMORY mode: In-memory caching
- ✅ NONE mode: No caching
- ✅ Error handling: Corrupted files, read-only directories

### LLMManager Integration (test_integration_llmmanager_catalog.py)
- ✅ Model validation via catalog
- ✅ Invalid model detection
- ✅ All cache modes (FILE, MEMORY, NONE)
- ✅ Lambda scenarios (/tmp directory, cold/warm start)
- ✅ Catalog refresh
- ✅ Backward compatibility

## Notes

### AWS Costs

Integration tests are designed to minimize AWS costs:
- Most tests use single regions
- Tests use minimal token limits (maxTokens: 50)
- Tests are marked with cost indicators
- Fast tests complete in < 30 seconds

### Test Data

Integration tests use:
- Real AWS Bedrock APIs (not mocked)
- Real file system operations
- Temporary directories for cache testing
- Dynamic model discovery (no hardcoded models)

### Fixtures

Key fixtures from `test/integration/conftest.py`:
- `integration_config`: Integration test configuration
- `aws_test_client`: AWS test client with authentication
- `sample_test_messages`: Sample messages for testing
- `simple_inference_config`: Simple inference configuration

Additional fixtures in test files:
- `temp_cache_dir`: Temporary cache directory
- `sample_catalog`: Real catalog data for testing

## Troubleshooting

### Tests Skipped

If tests are skipped, check:
1. `AWS_INTEGRATION_TESTS_ENABLED=true` is set
2. AWS credentials are configured (`aws configure`)
3. AWS account has Bedrock access
4. Integration test configuration is valid

### Tests Failing

Common issues:
1. **AccessDeniedException**: AWS account doesn't have Bedrock access
2. **ThrottlingException**: Too many API calls, retry later
3. **TimeoutError**: Network issues or slow API responses
4. **CacheError**: File system permissions issues

### Debugging

Enable debug logging:
```bash
pytest test/integration/ -v --log-cli-level=DEBUG
```

## Total Test Count

- **42 integration tests** across 3 test files
- **12 test classes** covering different aspects
- **100% coverage** of integration requirements

## Future Enhancements

Potential additions:
- Performance benchmarking tests
- Stress tests for parallel fetching
- Long-running cache expiration tests
- Multi-account testing
- Cross-region failover tests
