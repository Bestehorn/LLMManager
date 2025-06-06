# AWS Bedrock Integration Testing Framework

This document describes the integration testing framework for AWS Bedrock API functionality. These tests make real API calls to AWS services to validate functionality that cannot be adequately tested with mocks.

## Overview

The integration testing framework provides:

- **Real API Testing**: Tests against actual AWS Bedrock services
- **Cost Control**: Built-in cost tracking and limits
- **Performance Monitoring**: Request timing and performance benchmarks
- **Authentication Testing**: Validates AWS credential and authentication scenarios
- **Environment Configuration**: Flexible configuration via environment variables
- **Session Tracking**: Tracks costs and metrics across test sessions

## Quick Start

### 1. Configure AWS Credentials

Set up AWS credentials using one of these methods:

```bash
# Option 1: AWS CLI Profile
aws configure --profile bedrock-testing

# Option 2: Environment Variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 2. Enable Integration Tests

```bash
# Enable integration tests
export AWS_INTEGRATION_TESTS_ENABLED=true

# Optional: Set AWS profile for testing
export AWS_INTEGRATION_TEST_PROFILE=bedrock-testing

# Optional: Configure test regions
export AWS_INTEGRATION_TEST_REGIONS=us-east-1,us-west-2

# Optional: Set cost limit (default: $1.00)
export AWS_INTEGRATION_COST_LIMIT=0.50
```

### 3. Run Integration Tests

```bash
# Run all integration tests
python run_tests.py --aws-integration

# Run with specific AWS profile
python run_tests.py --aws-integration --aws-profile=bedrock-testing

# Run only fast, low-cost tests
python run_tests.py --aws-fast --aws-low-cost

# Run with detailed output
python run_tests.py --aws-integration --verbose
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_INTEGRATION_TESTS_ENABLED` | Enable integration tests | `false` |
| `AWS_INTEGRATION_TEST_PROFILE` | AWS CLI profile name | Auto-detect |
| `AWS_INTEGRATION_TEST_REGIONS` | Comma-separated regions | `us-east-1,us-west-2` |
| `AWS_INTEGRATION_TIMEOUT` | Request timeout (seconds) | `30` |
| `AWS_INTEGRATION_MAX_RETRIES` | Maximum retry attempts | `3` |
| `AWS_INTEGRATION_COST_LIMIT` | Cost limit in USD | `1.0` |
| `AWS_INTEGRATION_SKIP_SLOW` | Skip slow tests | `true` |
| `AWS_INTEGRATION_LOG_LEVEL` | Logging level | `INFO` |

### Model Configuration

Override default test models using environment variables:

```bash
# Anthropic model
export AWS_INTEGRATION_TEST_MODEL_ANTHROPIC=anthropic.claude-3-haiku-20240307-v1:0

# Amazon model
export AWS_INTEGRATION_TEST_MODEL_AMAZON=amazon.titan-text-lite-v1

# Meta model
export AWS_INTEGRATION_TEST_MODEL_META=meta.llama3-8b-instruct-v1:0
```

## Test Categories

### Test Markers

Integration tests use pytest markers for categorization:

- `@pytest.mark.integration` - All integration tests
- `@pytest.mark.aws_integration` - AWS Bedrock integration tests
- `@pytest.mark.aws_fast` - Fast tests (< 30 seconds)
- `@pytest.mark.aws_slow` - Slow tests (> 30 seconds)
- `@pytest.mark.aws_low_cost` - Low-cost tests (< $0.01)
- `@pytest.mark.aws_medium_cost` - Medium-cost tests ($0.01 - $0.10)
- `@pytest.mark.aws_high_cost` - High-cost tests (> $0.10)

### Test Organization

```
test/integration/
├── __init__.py
├── test_integration_auth.py         # Authentication tests
├── test_integration_bedrock_api.py  # Core API tests
└── conftest.py                      # Integration fixtures
```

## Running Tests

### Basic Commands

```bash
# Run all integration tests
python run_tests.py --aws-integration

# Run only authentication tests
pytest test/integration/test_integration_auth.py -v

# Run specific test class
pytest test/integration/test_integration_bedrock_api.py::TestBedrockAPIIntegration -v

# Run with cost and speed filters
python run_tests.py --aws-integration -m "aws_fast and aws_low_cost"
```

### Advanced Usage

```bash
# Run tests with session tracking
pytest test/integration/ -v --tb=short

# Run tests in parallel (if safe)
pytest test/integration/ -n 2

# Run with detailed logging
pytest test/integration/ -v -s --log-cli-level=DEBUG

# Generate integration test report
pytest test/integration/ --html=integration_report.html --self-contained-html
```

## Cost Management

### Cost Tracking

The framework automatically tracks estimated costs:

```python
# Costs are tracked per session
session = aws_test_client.start_test_session("my_test_session")

# Make API calls
response = aws_test_client.test_bedrock_converse(...)

# Session summary includes cost information
summary = aws_test_client.end_test_session()
print(f"Total cost: ${summary['total_estimated_cost_usd']:.4f}")
```

### Cost Limits

Tests automatically stop if cost limits are exceeded:

```bash
# Set cost limit to $0.25
export AWS_INTEGRATION_COST_LIMIT=0.25

# Run tests - they will stop if limit is reached
python run_tests.py --aws-integration
```

### Cost Optimization

To minimize costs:

1. Use `--aws-low-cost` flag
2. Set low cost limits
3. Use cheaper models (Haiku instead of Sonnet)
4. Run fast tests only with `--aws-fast`
5. Use minimal token limits in test configurations

## Authentication Testing

### Test Cases

The framework tests various authentication scenarios:

```python
# Test primary region authentication
def test_authentication_with_primary_region(aws_test_client, integration_config):
    result = aws_test_client.test_authentication(region="us-east-1")
    assert result["success"] is True

# Test multiple regions
@pytest.mark.parametrize("region", ["us-east-1", "us-west-2"])
def test_authentication_multiple_regions(aws_test_client, region):
    result = aws_test_client.test_authentication(region=region)
    assert result["success"] is True
```

### Authentication Methods

The framework supports multiple authentication methods:

- **AWS CLI Profiles**: `AWS_INTEGRATION_TEST_PROFILE`
- **Environment Variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- **IAM Roles**: For EC2/ECS environments
- **Auto-detection**: Automatic credential discovery

## API Testing

### Bedrock Converse API

```python
# Basic API test
def test_converse_with_anthropic_model(aws_test_client, integration_config):
    model_id = integration_config.get_test_model_for_provider("anthropic")
    
    response = aws_test_client.test_bedrock_converse(
        model_id=model_id,
        messages=[{
            "role": "user",
            "content": [{"text": "Hello!"}]
        }],
        inferenceConfig={"maxTokens": 100}
    )
    
    assert response.success is True
    assert len(response.get_content()) > 0
```

### Streaming API

```python
# Streaming API test
def test_converse_stream(aws_test_client, integration_config):
    model_id = integration_config.get_test_model_for_provider("anthropic")
    
    response = aws_test_client.test_bedrock_converse_stream(
        model_id=model_id,
        messages=[{
            "role": "user",
            "content": [{"text": "Hello!"}]
        }],
        inferenceConfig={"maxTokens": 100}
    )
    
    assert response.success is True
    assert "stream" in response.response_data
```

## Performance Testing

### Benchmarks

```python
def test_converse_performance_benchmarks(aws_test_client, integration_config):
    model_id = integration_config.get_test_model_for_provider("anthropic")
    
    durations = []
    for _ in range(3):
        response = aws_test_client.test_bedrock_converse(
            model_id=model_id,
            messages=[{"role": "user", "content": [{"text": "Hello!"}]}],
            inferenceConfig={"maxTokens": 50}
        )
        
        metrics = response.get_metrics()
        if metrics and "api_latency_ms" in metrics:
            durations.append(metrics["api_latency_ms"] / 1000)
    
    avg_duration = sum(durations) / len(durations)
    assert avg_duration < 30.0, f"Average latency too slow: {avg_duration}s"
```

## Error Handling

### Testing Error Scenarios

```python
def test_converse_with_invalid_model(aws_test_client):
    with pytest.raises(IntegrationTestError) as exc_info:
        aws_test_client.test_bedrock_converse(
            model_id="invalid.model.id",
            messages=[{"role": "user", "content": [{"text": "Hello!"}]}]
        )
    
    assert "not enabled for testing" in str(exc_info.value)
```

### Common Error Patterns

- **Authentication Failures**: Invalid credentials or permissions
- **Model Availability**: Model not available in region
- **Rate Limiting**: Too many requests too quickly
- **Malformed Requests**: Invalid message structure or parameters

## Fixtures and Utilities

### Core Fixtures

```python
@pytest.fixture
def integration_config():
    """Load integration test configuration."""
    return load_integration_config()

@pytest.fixture
def aws_test_client(integration_config):
    """Create AWS test client."""
    return AWSTestClient(config=integration_config)

@pytest.fixture
def integration_test_session(aws_test_client):
    """Create test session with automatic cleanup."""
    session = aws_test_client.start_test_session("test_session")
    yield session
    aws_test_client.end_test_session()
```

### Test Data

```python
@pytest.fixture
def sample_test_messages():
    """Sample messages for API testing."""
    return [{
        "role": "user",
        "content": [{"text": "Hello! This is a test message."}]
    }]

@pytest.fixture
def simple_inference_config():
    """Simple inference configuration."""
    return {
        "maxTokens": 100,
        "temperature": 0.1,
        "topP": 0.9
    }
```

## Troubleshooting

### Common Issues

#### 1. Tests Not Running

```bash
# Check if integration tests are enabled
echo $AWS_INTEGRATION_TESTS_ENABLED

# Enable them if not set
export AWS_INTEGRATION_TESTS_ENABLED=true
```

#### 2. Authentication Errors

```bash
# Test AWS credentials
aws sts get-caller-identity

# Check Bedrock permissions
aws bedrock list-foundation-models
```

#### 3. Model Not Available

```bash
# List available models in region
aws bedrock list-foundation-models --region us-east-1

# Check if model supports converse API
aws bedrock get-foundation-model --model-identifier anthropic.claude-3-haiku-20240307-v1:0
```

#### 4. Cost Limit Exceeded

```bash
# Increase cost limit
export AWS_INTEGRATION_COST_LIMIT=2.0

# Or run only low-cost tests
python run_tests.py --aws-low-cost
```

#### 5. Slow Tests

```bash
# Run only fast tests
python run_tests.py --aws-fast

# Skip slow tests
python run_tests.py --aws-integration -m "not aws_slow"
```

### Debug Mode

```bash
# Enable debug logging
export AWS_INTEGRATION_LOG_LEVEL=DEBUG

# Run with verbose output
python run_tests.py --aws-integration --verbose -s

# Use pytest debugging
pytest test/integration/test_integration_auth.py::TestAuthenticationIntegration::test_authentication_with_primary_region -v -s --pdb
```

## Best Practices

### Test Design

1. **Keep Tests Focused**: Each test should validate one specific behavior
2. **Use Appropriate Markers**: Mark tests with cost and speed classifications
3. **Handle Failures Gracefully**: Expect and handle API failures appropriately
4. **Minimize Costs**: Use small token limits and cheaper models
5. **Test Edge Cases**: Include error scenarios and boundary conditions

### Configuration

1. **Use Environment Variables**: Keep configuration external to code
2. **Set Reasonable Limits**: Balance thoroughness with cost control
3. **Profile-Specific Settings**: Use different profiles for different environments
4. **Document Requirements**: Clearly document what permissions are needed

### Maintenance

1. **Monitor Costs**: Regularly review test execution costs
2. **Update Models**: Keep test models current with AWS offerings
3. **Review Performance**: Monitor test execution times
4. **Clean Up Resources**: Ensure tests don't leave persistent resources

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements-test.txt
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Run integration tests
      run: |
        export AWS_INTEGRATION_TESTS_ENABLED=true
        export AWS_INTEGRATION_COST_LIMIT=0.50
        python run_tests.py --aws-integration --aws-low-cost
      env:
        AWS_INTEGRATION_TESTS_ENABLED: true
        AWS_INTEGRATION_COST_LIMIT: 0.50
```

### Cost Control in CI

```yaml
    - name: Run cost-controlled integration tests
      run: |
        python run_tests.py --aws-integration --aws-low-cost --aws-fast
      env:
        AWS_INTEGRATION_TESTS_ENABLED: true
        AWS_INTEGRATION_COST_LIMIT: 0.25
        AWS_INTEGRATION_SKIP_SLOW: true
```

## Conclusion

The AWS Bedrock integration testing framework provides comprehensive testing capabilities while maintaining cost control and performance awareness. It enables testing of real-world scenarios that cannot be adequately covered by unit tests alone.

For questions or issues, refer to the troubleshooting section or check the test logs for detailed error information.
