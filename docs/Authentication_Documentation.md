# Authentication Documentation

## Overview

The Authentication system in LLMManager provides secure, flexible authentication for AWS Bedrock services. It supports multiple authentication methods including AWS profiles, environment variables, direct credentials, and IAM roles, with automatic detection and fallback mechanisms.

## Table of Contents

- [Architecture](#architecture)
- [Authentication Methods](#authentication-methods)
- [Configuration](#configuration)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Architecture

### Core Components

```
AuthManager
├── AuthConfig           # Authentication configuration
├── CredentialProvider   # Credential resolution
├── SessionManager       # AWS session management
└── RegionManager        # Region-specific clients
```

### Authentication Flow

```
AuthConfig → Credential Resolution → AWS Session → Bedrock Client → API Calls
     ↓              ↓                    ↓             ↓
[Profile/Env] → [Boto3 Session] → [Region Client] → [Bedrock API]
```

### Key Features

- **Multiple Auth Methods**: Profiles, environment variables, direct credentials, IAM roles
- **Automatic Detection**: Intelligent fallback through credential chain
- **Session Management**: Efficient AWS session and client management
- **Region Support**: Multi-region client management
- **Security**: Secure credential handling and validation

## Authentication Methods

### 1. AWS Profile Authentication

Uses AWS CLI profiles stored in `~/.aws/credentials` and `~/.aws/config`.

```python
from src.bedrock.models.llm_manager_structures import AuthConfig, AuthenticationType

auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="my-bedrock-profile"
)
```

**Benefits:**
- Secure credential storage
- Easy switching between environments
- Supports MFA and role assumption
- Integrates with AWS CLI

**Setup:**
```bash
# Configure AWS profile
aws configure --profile my-bedrock-profile

# Or manually edit ~/.aws/credentials
[my-bedrock-profile]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = us-east-1
```

### 2. Environment Variable Authentication

Uses standard AWS environment variables.

```python
auth_config = AuthConfig(
    auth_type=AuthenticationType.ENVIRONMENT
)
```

**Required Environment Variables:**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Optional
export AWS_SESSION_TOKEN=your_session_token  # For temporary credentials
```

**Benefits:**
- Simple deployment
- Container-friendly
- CI/CD integration
- No file dependencies

### 3. Direct Credentials

Programmatically provided credentials (use with caution).

```python
auth_config = AuthConfig(
    auth_type=AuthenticationType.CREDENTIALS,
    access_key="your-access-key",
    secret_key="your-secret-key",
    session_token="your-session-token",  # Optional
    region_override="us-east-1"
)
```

**Benefits:**
- Programmatic control
- Dynamic credential loading
- Integration with secret management systems

**Security Warning:** Never hardcode credentials in source code.

### 4. IAM Role Authentication

Uses IAM roles for cross-account access or service-to-service authentication.

```python
auth_config = AuthConfig(
    auth_type=AuthenticationType.IAM_ROLE,
    role_arn="arn:aws:iam::123456789012:role/BedrockAccessRole",
    external_id="optional-external-id",  # For cross-account roles
    role_session_name="LLMManager-Session"
)
```

**Benefits:**
- No long-term credentials
- Fine-grained permissions
- Cross-account access
- Audit trail

### 5. Auto-Detection (Default)

Automatically detects available credentials using AWS credential chain.

```python
auth_config = AuthConfig(
    auth_type=AuthenticationType.AUTO
)

# Or simply omit auth_config - this is the default
manager = LLMManager(models=["Claude 3.5 Sonnet"], regions=["us-east-1"])
```

**Credential Chain Order:**
1. Environment variables
2. AWS credentials file
3. EC2 instance metadata (IAM roles)
4. ECS container credentials
5. Lambda environment

## Configuration

### AuthConfig Structure

```python
@dataclass
class AuthConfig:
    auth_type: AuthenticationType = AuthenticationType.AUTO
    profile_name: Optional[str] = None
    access_key: Optional[str] = None  
    secret_key: Optional[str] = None
    session_token: Optional[str] = None
    region_override: Optional[str] = None
    role_arn: Optional[str] = None
    external_id: Optional[str] = None
    role_session_name: Optional[str] = None
    assume_role_duration: int = 3600  # 1 hour
```

### Configuration Examples

#### Production Environment with Profiles

```python
# Production configuration
production_auth = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="production-bedrock",
    region_override="us-east-1"
)

# Development configuration  
development_auth = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="development-bedrock",
    region_override="us-west-2"
)
```

#### Container/Lambda Deployment

```python
# Container deployment (uses environment variables or IAM roles)
container_auth = AuthConfig(
    auth_type=AuthenticationType.AUTO,  # Auto-detects container credentials
    region_override="us-east-1"
)
```

#### Cross-Account Access

```python
# Cross-account role assumption
cross_account_auth = AuthConfig(
    auth_type=AuthenticationType.IAM_ROLE,
    role_arn="arn:aws:iam::ACCOUNT-B:role/BedrockCrossAccountRole",
    external_id="unique-external-id",
    role_session_name="LLMManager-CrossAccount",
    assume_role_duration=7200  # 2 hours
)
```

## Basic Usage

### Simple Authentication

```python
from src.LLMManager import LLMManager
from src.bedrock.models.llm_manager_structures import AuthConfig, AuthenticationType

# Using default authentication (auto-detection)
manager = LLMManager(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1"]
)

# Using specific profile
auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="my-profile"
)

manager = LLMManager(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1"],
    auth_config=auth_config
)
```

### Authentication Validation

```python
# Validate authentication configuration
validation_result = manager.validate_configuration()

print(f"Authentication Status: {validation_result['auth_status']}")
if not validation_result['valid']:
    print("Authentication Issues:")
    for error in validation_result['errors']:
        print(f"  - {error}")
```

### Getting Authentication Information

```python
# Get current authentication details
auth_info = manager._auth_manager.get_auth_info()

print(f"Auth Type: {auth_info['auth_type']}")
print(f"Region: {auth_info.get('region', 'Not specified')}")
print(f"Profile: {auth_info.get('profile_name', 'Not using profile')}")
```

## Advanced Features

### Multi-Region Client Management

```python
from src.bedrock.auth.auth_manager import AuthManager

# Initialize auth manager
auth_manager = AuthManager(auth_config)

# Get clients for different regions
us_east_client = auth_manager.get_bedrock_client("us-east-1")
us_west_client = auth_manager.get_bedrock_client("us-west-2")
eu_client = auth_manager.get_bedrock_client("eu-west-1")

# Clients are cached and reused for efficiency
same_client = auth_manager.get_bedrock_client("us-east-1")  # Returns cached client
assert us_east_client is same_client
```

### Dynamic Credential Loading

```python
import os
from src.bedrock.models.llm_manager_structures import AuthConfig, AuthenticationType

def get_auth_config_for_environment():
    """Get authentication config based on environment."""
    
    if os.getenv('AWS_EXECUTION_ENV'):  # Lambda environment
        return AuthConfig(auth_type=AuthenticationType.AUTO)
    
    elif os.getenv('ECS_CONTAINER_METADATA_URI'):  # ECS environment
        return AuthConfig(auth_type=AuthenticationType.AUTO)
    
    elif os.getenv('AWS_PROFILE'):  # Local development with profile
        return AuthConfig(
            auth_type=AuthenticationType.PROFILE,
            profile_name=os.getenv('AWS_PROFILE')
        )
    
    else:  # Fallback to environment variables
        return AuthConfig(auth_type=AuthenticationType.ENVIRONMENT)

# Usage
auth_config = get_auth_config_for_environment()
manager = LLMManager(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1"],
    auth_config=auth_config
)
```

### Credential Refresh and Session Management

```python
class ManagedAuthLLMManager:
    """LLMManager with automatic credential refresh."""
    
    def __init__(self, models, regions, auth_config):
        self.manager = LLMManager(models, regions, auth_config)
        self.last_refresh = datetime.now()
        self.refresh_interval = timedelta(hours=1)
    
    def converse(self, messages, **kwargs):
        """Converse with automatic credential refresh."""
        # Check if credentials need refresh
        if datetime.now() - self.last_refresh > self.refresh_interval:
            self._refresh_credentials()
        
        return self.manager.converse(messages, **kwargs)
    
    def _refresh_credentials(self):
        """Refresh AWS credentials if needed."""
        try:
            # Force recreation of auth manager and clients
            self.manager._auth_manager = AuthManager(self.manager._auth_config)
            self.last_refresh = datetime.now()
            print("Credentials refreshed successfully")
        except Exception as e:
            print(f"Failed to refresh credentials: {e}")
```

### Secret Manager Integration

```python
import boto3
import json
from src.bedrock.models.llm_manager_structures import AuthConfig, AuthenticationType

def get_auth_from_secrets_manager(secret_arn, region="us-east-1"):
    """Load authentication config from AWS Secrets Manager."""
    
    # Use default credentials to access Secrets Manager
    secrets_client = boto3.client('secretsmanager', region_name=region)
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret_data = json.loads(response['SecretString'])
        
        return AuthConfig(
            auth_type=AuthenticationType.CREDENTIALS,
            access_key=secret_data['access_key'],
            secret_key=secret_data['secret_key'],
            session_token=secret_data.get('session_token'),
            region_override=secret_data.get('region')
        )
    
    except Exception as e:
        raise Exception(f"Failed to load credentials from Secrets Manager: {e}")

# Usage
auth_config = get_auth_from_secrets_manager("arn:aws:secretsmanager:us-east-1:123456789012:secret:bedrock-creds")
manager = LLMManager(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1"],
    auth_config=auth_config
)
```

## Security Considerations

### 1. Credential Storage

```python
# ✅ Good: Secure credential storage
# Use AWS profiles, environment variables, or IAM roles
auth_config = AuthConfig(
    auth_type=AuthenticationType.PROFILE,
    profile_name="secure-profile"
)

# ❌ Bad: Hardcoded credentials
auth_config = AuthConfig(
    auth_type=AuthenticationType.CREDENTIALS,
    access_key="AKIAEXAMPLE123456789",  # Never do this!
    secret_key="secretkey123456789"
)
```

### 2. Least Privilege Access

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-*",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        }
    ]
}
```

### 3. Session Security

```python
# Configure secure session settings
auth_config = AuthConfig(
    auth_type=AuthenticationType.IAM_ROLE,
    role_arn="arn:aws:iam::123456789012:role/BedrockRole",
    role_session_name="LLMManager-SecureSession",
    assume_role_duration=1800  # 30 minutes - shorter duration for security
)
```

### 4. Credential Rotation

```python
import time
from datetime import datetime, timedelta

class RotatingCredentialManager:
    """Manages credential rotation for long-running applications."""
    
    def __init__(self, credential_provider, rotation_interval_hours=6):
        self.credential_provider = credential_provider
        self.rotation_interval = timedelta(hours=rotation_interval_hours)
        self.last_rotation = datetime.now()
        self.current_auth_config = None
        self._rotate_credentials()
    
    def get_current_auth_config(self):
        """Get current auth config, rotating if needed."""
        if datetime.now() - self.last_rotation > self.rotation_interval:
            self._rotate_credentials()
        return self.current_auth_config
    
    def _rotate_credentials(self):
        """Rotate credentials."""
        try:
            self.current_auth_config = self.credential_provider()
            self.last_rotation = datetime.now()
            print("Credentials rotated successfully")
        except Exception as e:
            print(f"Credential rotation failed: {e}")
            # Continue with existing credentials

# Usage
def get_fresh_credentials():
    """Get fresh credentials from your secure source."""
    # Implementation depends on your credential source
    return AuthConfig(auth_type=AuthenticationType.AUTO)

credential_manager = RotatingCredentialManager(get_fresh_credentials)
```

## Troubleshooting

### Common Issues

#### 1. No Credentials Found

**Error:** `NoCredentialsError: Unable to locate credentials`

**Solutions:**
- Set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Configure AWS profile: `aws configure --profile myprofile`
- Check IAM role attachment (for EC2/ECS/Lambda)
- Verify credential file permissions

#### 2. Access Denied

**Error:** `AccessDenied: User is not authorized to perform: bedrock:InvokeModel`

**Solutions:**
- Check IAM policy permissions
- Verify resource ARNs in policy
- Ensure Bedrock service is available in the region
- Check if model access is enabled in AWS Console

#### 3. Invalid Profile

**Error:** `ProfileNotFound: The config profile (myprofile) could not be found`

**Solutions:**
- Verify profile exists: `aws configure list-profiles`
- Check profile name spelling
- Ensure `~/.aws/credentials` and `~/.aws/config` files exist
- Set correct profile: `export AWS_PROFILE=myprofile`

#### 4. Region Mismatch

**Error:** Model not available in specified region

**Solutions:**
- Check model availability per region
- Use correct region in auth config
- Verify region in profile/environment variables

### Debugging Authentication

```python
import boto3
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)

def debug_authentication():
    """Debug current authentication setup."""
    
    try:
        # Check current AWS identity
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        
        print("Current AWS Identity:")
        print(f"  Account: {identity['Account']}")
        print(f"  User/Role ARN: {identity['Arn']}")
        print(f"  User ID: {identity['UserId']}")
        
        # Check available regions
        ec2_client = boto3.client('ec2')
        regions = ec2_client.describe_regions()
        print(f"\nAvailable Regions: {len(regions['Regions'])}")
        
        # Test Bedrock access
        bedrock_client = boto3.client('bedrock', region_name='us-east-1')
        models = bedrock_client.list_foundation_models()
        print(f"Bedrock Models Available: {len(models['modelSummaries'])}")
        
        return True
        
    except Exception as e:
        print(f"Authentication Debug Failed: {e}")
        return False

# Run debug
debug_authentication()
```

### Environment-Specific Debugging

```python
import os

def diagnose_environment():
    """Diagnose authentication environment."""
    
    print("Environment Diagnosis:")
    print("=" * 40)
    
    # Check environment variables
    env_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 
                'AWS_PROFILE', 'AWS_DEFAULT_REGION', 'AWS_REGION']
    
    print("Environment Variables:")
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'TOKEN' in var:
                display_value = value[:4] + "*" * (len(value) - 4)
            else:
                display_value = value
            print(f"  {var}: {display_value}")
        else:
            print(f"  {var}: Not set")
    
    # Check AWS config files
    aws_dir = os.path.expanduser("~/.aws")
    credentials_file = os.path.join(aws_dir, "credentials")
    config_file = os.path.join(aws_dir, "config")
    
    print(f"\nAWS Configuration Files:")
    print(f"  Credentials file exists: {os.path.exists(credentials_file)}")
    print(f"  Config file exists: {os.path.exists(config_file)}")
    
    # Check execution environment
    print(f"\nExecution Environment:")
    print(f"  Lambda: {'AWS_LAMBDA_FUNCTION_NAME' in os.environ}")
    print(f"  ECS: {'ECS_CONTAINER_METADATA_URI' in os.environ}")
    print(f"  EC2: {os.path.exists('/opt/aws/bin/ec2-metadata')}")

diagnose_environment()
```

## Best Practices

### 1. Environment-Based Configuration

```python
import os
from src.bedrock.models.llm_manager_structures import AuthConfig, AuthenticationType

def get_production_auth_config():
    """Get authentication config for production environment."""
    
    # Production should use IAM roles or profiles, never direct credentials
    if os.getenv('AWS_EXECUTION_ENV'):  # Lambda
        return AuthConfig(auth_type=AuthenticationType.AUTO)
    
    elif os.getenv('ECS_CONTAINER_METADATA_URI'):  # ECS
        return AuthConfig(auth_type=AuthenticationType.AUTO)
    
    else:  # EC2 or other compute
        return AuthConfig(
            auth_type=AuthenticationType.PROFILE,
            profile_name="production-bedrock"
        )

def get_development_auth_config():
    """Get authentication config for development."""
    
    # Development can use profiles or environment variables
    profile = os.getenv('AWS_PROFILE', 'default')
    return AuthConfig(
        auth_type=AuthenticationType.PROFILE,
        profile_name=profile
    )

# Usage
if os.getenv('ENVIRONMENT') == 'production':
    auth_config = get_production_auth_config()
else:
    auth_config = get_development_auth_config()
```

### 2. Error Handling and Fallback

```python
def create_resilient_manager(models, regions):
    """Create LLMManager with resilient authentication."""
    
    auth_configs = [
        # Try profile first
        AuthConfig(auth_type=AuthenticationType.PROFILE, profile_name="bedrock"),
        # Fallback to environment variables
        AuthConfig(auth_type=AuthenticationType.ENVIRONMENT),
        # Final fallback to auto-detection
        AuthConfig(auth_type=AuthenticationType.AUTO)
    ]
    
    for auth_config in auth_configs:
        try:
            manager = LLMManager(models, regions, auth_config=auth_config)
            
            # Validate the configuration
            validation = manager.validate_configuration()
            if validation['valid']:
                print(f"Successfully authenticated using: {validation['auth_status']}")
                return manager
            
        except Exception as e:
            print(f"Authentication method {auth_config.auth_type} failed: {e}")
            continue
    
    raise Exception("All authentication methods failed")

# Usage
manager = create_resilient_manager(["Claude 3.5 Sonnet"], ["us-east-1"])
```

### 3. Security Monitoring

```python
import time
from datetime import datetime

class SecureAuthManager:
    """Authentication manager with security monitoring."""
    
    def __init__(self, auth_config):
        self.auth_config = auth_config
        self.failed_attempts = 0
        self.last_success = None
        self.max_failed_attempts = 5
    
    def authenticate(self):
        """Authenticate with security monitoring."""
        try:
            manager = LLMManager(
                models=["Claude 3.5 Sonnet"],
                regions=["us-east-1"],
                auth_config=self.auth_config
            )
            
            # Test authentication with a simple validation
            validation = manager.validate_configuration()
            if not validation['valid']:
                raise Exception("Authentication validation failed")
            
            # Reset failure count on success
            self.failed_attempts = 0
            self.last_success = datetime.now()
            
            return manager
            
        except Exception as e:
            self.failed_attempts += 1
            
            if self.failed_attempts >= self.max_failed_attempts:
                raise Exception(f"Authentication failed {self.max_failed_attempts} times. Possible security issue.")
            
            raise e

# Usage
secure_auth = SecureAuthManager(auth_config)
manager = secure_auth.authenticate()
```

### 4. Testing Authentication

```python
import pytest
from unittest.mock import patch, MagicMock

def test_authentication_methods():
    """Test different authentication methods."""
    
    # Mock AWS credentials for testing
    with patch('boto3.Session') as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        # Test profile authentication
        auth_config = AuthConfig(
            auth_type=AuthenticationType.PROFILE,
            profile_name="test-profile"
        )
        
        auth_manager = AuthManager(auth_config)
        client = auth_manager.get_bedrock_client("us-east-1")
        
        # Verify session was created with correct profile
        mock_session.assert_called_with(profile_name="test-profile")
        assert client is not None

def test_authentication_fallback():
    """Test authentication fallback mechanisms."""
    
    # Test that fallback works when primary method fails
    with patch('boto3.Session') as mock_session:
        # First call fails, second succeeds
        mock_session.side_effect = [Exception("Profile not found"), MagicMock()]
        
        auth_configs = [
            AuthConfig(auth_type=AuthenticationType.PROFILE, profile_name="nonexistent"),
            AuthConfig(auth_type=AuthenticationType.AUTO)
        ]
        
        manager = None
        for auth_config in auth_configs:
            try:
                auth_manager = AuthManager(auth_config)
                client = auth_manager.get_bedrock_client("us-east-1")
                manager = LLMManager(["Claude 3.5 Sonnet"], ["us-east-1"], auth_config=auth_config)
                break
            except:
                continue
        
        assert manager is not None
```

---

This comprehensive authentication documentation ensures secure, reliable access to AWS Bedrock services across different deployment environments while following AWS security best practices.
