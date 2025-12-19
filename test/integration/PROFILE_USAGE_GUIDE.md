# AWS Profile Usage Guide for Integration Tests

## Overview

Integration tests now support specifying AWS profiles via command-line arguments, making it easy to test with different AWS accounts without modifying environment variables.

## Usage

### Command-Line Option (Recommended)

```bash
# Use a specific AWS profile
pytest test/integration/ --profile my-test-profile

# Use a specific profile and region
pytest test/integration/ --profile my-test-profile --aws-region us-west-2

# Run specific test with profile
pytest test/integration/test_integration_catalog_api.py::TestBedrockAPIFetcherIntegration::test_fetch_foundation_models_single_region --profile my-profile
```

### Environment Variable (Alternative)

```bash
# Set environment variable
export AWS_INTEGRATION_TEST_PROFILE=my-test-profile
pytest test/integration/

# Or inline
AWS_INTEGRATION_TEST_PROFILE=my-test-profile pytest test/integration/
```

### Priority Order

When both are specified, command-line options take precedence:

1. **`--profile` command-line option** (highest priority)
2. **`AWS_INTEGRATION_TEST_PROFILE` environment variable**
3. **Default AWS credentials** (lowest priority - uses boto3 default credential chain)

## Implementation Details

### 1. Pytest Configuration (`test/conftest.py`)

The root conftest.py adds custom pytest options:

```python
def pytest_addoption(parser):
    parser.addoption(
        "--profile",
        action="store",
        default=None,
        help="AWS profile to use for integration tests"
    )
    parser.addoption(
        "--aws-region",
        action="store",
        default=None,
        help="Primary AWS region for integration tests"
    )

def pytest_configure(config):
    # Set environment variable from command-line option
    profile = config.getoption("--profile")
    if profile:
        os.environ["AWS_INTEGRATION_TEST_PROFILE"] = profile
```

### 2. Integration Config (`IntegrationTestConfig`)

The integration config reads the profile from environment:

```python
@dataclass
class IntegrationTestConfig:
    aws_profile: Optional[str] = field(
        default_factory=lambda: os.getenv("AWS_INTEGRATION_TEST_PROFILE")
    )
```

### 3. AuthManager Fixture (`test/integration/conftest.py`)

A session-scoped fixture creates AuthManager with the profile:

```python
@pytest.fixture(scope="session")
def auth_manager_with_profile(integration_config: IntegrationTestConfig) -> AuthManager:
    """Provide AuthManager configured with the integration test profile."""
    if integration_config.aws_profile:
        auth_config = AuthConfig(
            auth_type=AuthenticationType.PROFILE,
            profile_name=integration_config.aws_profile
        )
        return AuthManager(auth_config=auth_config)
    else:
        return AuthManager()  # Use auto-detection
```

### 4. Test Usage

Tests should use the `auth_manager_with_profile` fixture:

```python
def test_something(self, integration_config: Any, auth_manager_with_profile: Any) -> None:
    # Use the profile-configured AuthManager
    fetcher = BedrockAPIFetcher(
        auth_manager=auth_manager_with_profile,
        timeout=integration_config.timeout_seconds,
    )
```

## Benefits

### Multi-Account Testing

Easily test with different AWS accounts:

```bash
# Test with development account
pytest test/integration/ --profile dev-account

# Test with staging account  
pytest test/integration/ --profile staging-account

# Test with production account (be careful!)
pytest test/integration/ --profile prod-account
```

### CI/CD Integration

In CI/CD pipelines, use environment variables:

```yaml
# GitHub Actions example
- name: Run Integration Tests
  env:
    AWS_INTEGRATION_TEST_PROFILE: ci-test-profile
  run: pytest test/integration/
```

### Local Development

Developers can use their personal profiles:

```bash
# Each developer uses their own profile
pytest test/integration/ --profile alice-dev
pytest test/integration/ --profile bob-dev
```

## Troubleshooting

### Profile Not Found

```
Error: The config profile (my-profile) could not be found
```

**Solution:** Check that the profile exists in `~/.aws/credentials` or `~/.aws/config`:

```bash
aws configure list-profiles
```

### No Credentials

```
Error: Unable to locate credentials
```

**Solution:** Either:
1. Specify a profile: `pytest test/integration/ --profile my-profile`
2. Set AWS credentials via environment variables
3. Configure default AWS credentials: `aws configure`

### Permission Denied

```
Error: AccessDeniedException: You don't have access to the model
```

**Solution:** Ensure the AWS account/profile has:
- Bedrock access enabled in the region
- IAM permissions for `bedrock:*` actions
- Model access granted in Bedrock console

## Examples

### Basic Usage

```bash
# Run all integration tests with a profile
pytest test/integration/ --profile my-test-profile

# Run only fast tests
pytest test/integration/ -m "aws_fast" --profile my-test-profile

# Run only low-cost tests
pytest test/integration/ -m "aws_low_cost" --profile my-test-profile
```

### Advanced Usage

```bash
# Verbose output with profile
pytest test/integration/ --profile my-test-profile -v

# Show print statements
pytest test/integration/ --profile my-test-profile -s

# Run specific test class
pytest test/integration/test_integration_catalog_api.py::TestBedrockAPIFetcherIntegration --profile my-test-profile

# Collect tests without running (verify profile is recognized)
pytest test/integration/ --profile my-test-profile --collect-only
```

### Multiple Profiles Testing

```bash
# Test with multiple profiles sequentially
for profile in dev-profile staging-profile; do
    echo "Testing with profile: $profile"
    pytest test/integration/ --profile $profile
done
```

## Best Practices

1. **Use `--profile` for local development** - Keeps your shell environment clean
2. **Use environment variables in CI/CD** - More secure, easier to manage secrets
3. **Document required permissions** - Ensure profiles have necessary Bedrock access
4. **Test with least-privilege profiles** - Use profiles with minimal required permissions
5. **Avoid hardcoding profiles** - Always pass via command-line or environment

## Related Configuration

### Other Integration Test Options

```bash
# Enable integration tests explicitly
export AWS_INTEGRATION_TESTS_ENABLED=true

# Set test regions
export AWS_INTEGRATION_TEST_REGIONS="us-east-1,us-west-2"

# Set timeout
export AWS_INTEGRATION_TIMEOUT=60

# Set cost limit
export AWS_INTEGRATION_COST_LIMIT=5.0

# Skip slow tests
export AWS_INTEGRATION_SKIP_SLOW=true
```

### Combined Example

```bash
# Full configuration via command-line and environment
AWS_INTEGRATION_TESTS_ENABLED=true \
AWS_INTEGRATION_TEST_REGIONS="us-east-1" \
AWS_INTEGRATION_TIMEOUT=30 \
pytest test/integration/ --profile my-test-profile -v
```

## Migration from Environment Variables

If you're currently using environment variables, you can migrate to command-line options:

**Before:**
```bash
export AWS_INTEGRATION_TEST_PROFILE=my-profile
pytest test/integration/
```

**After:**
```bash
pytest test/integration/ --profile my-profile
```

Both approaches work, but command-line options are recommended for better isolation and clarity.
