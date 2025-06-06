# RetryManager Documentation

## Overview

The `RetryManager` class provides intelligent retry logic, error handling, and failover mechanisms for AWS Bedrock LLM requests. It implements exponential backoff, circuit breaker patterns, and multi-region failover to ensure maximum reliability and optimal performance in production environments.

## Table of Contents

- [Architecture](#architecture)
- [Retry Strategies](#retry-strategies)
- [Configuration](#configuration)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Error Classification](#error-classification)
- [Circuit Breaker](#circuit-breaker)
- [Performance Optimization](#performance-optimization)
- [Monitoring and Metrics](#monitoring-and-metrics)
- [Best Practices](#best-practices)

## Architecture

### Core Components

```
RetryManager
├── RetryConfig          # Retry configuration and strategy
├── RetryExecutor        # Request execution with retry logic
├── ErrorClassifier      # Error type classification
├── CircuitBreaker       # Circuit breaker pattern implementation
├── BackoffCalculator    # Delay calculation algorithms
└── MetricsCollector     # Retry statistics and monitoring
```

### Retry Flow

```
Request → Error Classification → Retry Decision → Backoff Calculation → Retry Attempt → Success/Failure
   ↓            ↓                    ↓                 ↓                   ↓
[API Call] → [Exception    → [Should Retry?] → [Wait Duration] → [Next Attempt] → [Final Result]
             Analysis]
```

### Key Features

- **Multiple Retry Strategies**: Linear, exponential backoff, fixed delay, custom strategies
- **Intelligent Error Classification**: Distinguishes between retryable and non-retryable errors
- **Circuit Breaker Pattern**: Prevents cascading failures in degraded conditions
- **Multi-Region Failover**: Automatic failover across AWS regions and models
- **Performance Monitoring**: Comprehensive metrics and statistics collection
- **Response Validation**: Optional response validation with retry on validation failures

## Retry Strategies

### 1. Exponential Backoff (Default)

Implements exponential backoff with jitter to prevent thundering herd problems.

```python
from src.bedrock.models.llm_manager_structures import RetryConfig, RetryStrategy

retry_config = RetryConfig(
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    max_attempts=5,
    base_delay=1.0,      # Start with 1 second
    max_delay=60.0,      # Cap at 60 seconds
    backoff_multiplier=2.0,  # Double each time
    jitter=True          # Add randomization
)
```

**Delay Calculation:**
```
delay = min(base_delay * (multiplier ^ attempt), max_delay)
with jitter: delay *= random(0.5, 1.5)
```

**Use Cases:**
- Rate limiting errors
- Temporary service unavailability
- Network connectivity issues

### 2. Linear Backoff

Increases delay linearly with each attempt.

```python
retry_config = RetryConfig(
    strategy=RetryStrategy.LINEAR_BACKOFF,
    max_attempts=3,
    base_delay=2.0,      # 2 seconds base
    max_delay=30.0,      # Cap at 30 seconds
    backoff_multiplier=3.0   # Add 3 seconds each attempt
)
```

**Delay Calculation:**
```
delay = min(base_delay + (multiplier * attempt), max_delay)
```

**Use Cases:**
- Predictable resource recovery times
- Conservative retry approaches
- Testing and development

### 3. Fixed Delay

Consistent delay between all retry attempts.

```python
retry_config = RetryConfig(
    strategy=RetryStrategy.FIXED_DELAY,
    max_attempts=4,
    base_delay=5.0,      # Always 5 seconds
    max_delay=5.0        # Same as base_delay
)
```

**Use Cases:**
- Known service recovery patterns
- Simple retry logic
- Legacy system integration

### 4. Custom Strategy

Implement custom retry logic for specific requirements.

```python
class CustomRetryStrategy:
    """Custom retry strategy implementation."""
    
    def calculate_delay(self, attempt: int, base_delay: float, **kwargs) -> float:
        """Calculate delay for custom strategy."""
        if attempt <= 2:
            return 1.0  # Fast retries for first two attempts
        elif attempt <= 4:
            return 5.0  # Medium delay for next attempts
        else:
            return 15.0  # Longer delay for final attempts

# Usage with custom strategy (conceptual)
retry_config = RetryConfig(
    strategy=RetryStrategy.CUSTOM,
    custom_strategy=CustomRetryStrategy(),
    max_attempts=6
)
```

## Configuration

### RetryConfig Structure

```python
@dataclass
class RetryConfig:
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_exceptions: Optional[List[str]] = None
    non_retryable_exceptions: Optional[List[str]] = None
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
```

### Configuration Examples

#### Production Configuration

```python
# Production-ready retry configuration
production_retry = RetryConfig(
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    max_attempts=5,
    base_delay=1.0,
    max_delay=120.0,     # 2 minutes max delay
    backoff_multiplier=2.0,
    jitter=True,
    enable_circuit_breaker=True,
    circuit_breaker_threshold=10,
    circuit_breaker_timeout=300.0  # 5 minutes
)
```

#### Development Configuration

```python
# Development/testing configuration - faster failures
development_retry = RetryConfig(
    strategy=RetryStrategy.LINEAR_BACKOFF,
    max_attempts=3,
    base_delay=0.5,
    max_delay=5.0,
    enable_circuit_breaker=False  # Disable for testing
)
```

#### High-Throughput Configuration

```python
# Optimized for high-throughput scenarios
high_throughput_retry = RetryConfig(
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    max_attempts=3,      # Fewer attempts for faster failure
    base_delay=0.1,      # Start with 100ms
    max_delay=2.0,       # Quick failure detection
    backoff_multiplier=3.0,
    jitter=True
)
```

## Basic Usage

### Simple Retry Usage

```python
from src.LLMManager import LLMManager
from src.bedrock.models.llm_manager_structures import RetryConfig, RetryStrategy

# Configure retry behavior
retry_config = RetryConfig(
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    max_attempts=5,
    base_delay=1.0,
    max_delay=60.0
)

# Initialize LLMManager with retry configuration
manager = LLMManager(
    models=["Claude 3.5 Sonnet", "Claude 3 Haiku"],
    regions=["us-east-1", "us-west-2"],
    retry_config=retry_config
)

# Requests automatically use configured retry logic
response = manager.converse(messages=[message])
```

### Manual Retry Manager Usage

```python
from src.bedrock.retry.retry_manager import RetryManager
from src.bedrock.UnifiedModelManager import UnifiedModelManager

# Initialize retry manager directly
retry_manager = RetryManager(retry_config)
unified_manager = UnifiedModelManager()

# Generate retry targets (model/region combinations)
retry_targets = retry_manager.generate_retry_targets(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1", "us-west-2"],
    unified_model_manager=unified_manager
)

# Execute operation with retry logic
def my_operation(**kwargs):
    # Your operation implementation
    return call_bedrock_api(**kwargs)

result, attempts, warnings = retry_manager.execute_with_retry(
    operation=my_operation,
    operation_args={"modelId": "anthropic.claude-3-5-sonnet-20241022-v2:0"},
    retry_targets=retry_targets
)
```

## Advanced Features

### Response Validation with Retry

Retry requests when responses don't meet validation criteria.

```python
from src.bedrock.models.llm_manager_structures import ResponseValidationConfig

def validate_response_quality(response):
    """Custom response validation function."""
    content = response.get_content()
    
    # Validation criteria
    if not content:
        return False
    
    if len(content) < 10:  # Too short
        return False
    
    if "I cannot" in content:  # Refusal pattern
        return False
    
    return True

# Configure response validation
validation_config = ResponseValidationConfig(
    max_validation_attempts=3,
    validation_function=validate_response_quality,
    validation_retry_delay=2.0,
    fail_on_validation_error=False
)

# Use with LLMManager
response = manager.converse(
    messages=[message],
    response_validation_config=validation_config
)

# Check validation results
if response.had_validation_failures():
    print(f"Response validation failed {response.get_validation_attempt_count()} times")
    print(f"Final response quality: {validate_response_quality(response)}")
```

### Multi-Region Failover

Automatic failover across AWS regions when primary region fails.

```python
# Configure multi-region failover
manager = LLMManager(
    models=["Claude 3.5 Sonnet"],
    regions=["us-east-1", "us-west-2", "eu-west-1"],  # Priority order
    retry_config=RetryConfig(
        max_attempts=2,  # 2 attempts per region
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )
)

# Request automatically fails over to next region if current region fails
response = manager.converse(messages=[message])

# Check which region was used
print(f"Response from region: {response.region_used}")
print(f"Total attempts across regions: {response.get_attempt_count()}")
```

### Model Failover

Failover to alternative models when primary model is unavailable.

```python
# Configure model failover (models in priority order)
manager = LLMManager(
    models=["Claude 3.5 Sonnet", "Claude 3 Haiku", "Nova Pro"],
    regions=["us-east-1"],
    retry_config=RetryConfig(max_attempts=2)
)

# Automatically tries alternative models if primary fails
response = manager.converse(messages=[message])
print(f"Response from model: {response.model_used}")
```

### Custom Error Classification

Define custom logic for determining which errors should be retried.

```python
# Custom retryable exceptions
retry_config = RetryConfig(
    retryable_exceptions=[
        "ThrottlingException",
        "InternalServerException", 
        "ServiceUnavailableException",
        "TimeoutError",
        "CustomRetryableError"
    ],
    non_retryable_exceptions=[
        "ValidationException",
        "AccessDeniedException",
        "ModelNotFoundException",
        "CustomNonRetryableError"
    ]
)
```

## Error Classification

### Built-in Error Categories

#### Retryable Errors (Default)
- `ThrottlingException` - Rate limiting
- `InternalServerException` - AWS service errors
- `ServiceUnavailableException` - Temporary unavailability
- `ModelStreamErrorException` - Streaming errors
- Network timeouts and connection errors

#### Non-Retryable Errors (Default)
- `ValidationException` - Request validation failures
- `AccessDeniedException` - Permission errors
- `ModelNotFoundException` - Model not found
- `ResourceNotFoundException` - Resource not found
- Authentication errors

### Error Classification Logic

```python
class RetryableErrorClassifier:
    """Classifies errors for retry decisions."""
    
    def __init__(self, retry_config):
        self.retry_config = retry_config
    
    def is_retryable(self, exception):
        """Determine if an exception should be retried."""
        exception_name = type(exception).__name__
        
        # Check explicit non-retryable list first
        if (self.retry_config.non_retryable_exceptions and 
            exception_name in self.retry_config.non_retryable_exceptions):
            return False
        
        # Check explicit retryable list
        if (self.retry_config.retryable_exceptions and 
            exception_name in self.retry_config.retryable_exceptions):
            return True
        
        # Default classification
        return self._is_default_retryable(exception)
    
    def _is_default_retryable(self, exception):
        """Default retry classification logic."""
        retryable_patterns = [
            'throttling', 'rate', 'limit',
            'timeout', 'connection', 'network',
            'internal', 'server', 'unavailable',
            'busy', 'overloaded'
        ]
        
        error_message = str(exception).lower()
        return any(pattern in error_message for pattern in retryable_patterns)

# Usage example
classifier = RetryableErrorClassifier(retry_config)
should_retry = classifier.is_retryable(some_exception)
```

## Circuit Breaker

### Circuit Breaker Pattern

Prevents cascading failures by temporarily stopping requests when error rate is high.

```python
# Configure circuit breaker
retry_config = RetryConfig(
    enable_circuit_breaker=True,
    circuit_breaker_threshold=5,      # Open after 5 failures
    circuit_breaker_timeout=60.0,     # Stay open for 60 seconds
    circuit_breaker_half_open_max_requests=3  # Test with 3 requests
)
```

### Circuit Breaker States

#### Closed (Normal Operation)
- All requests pass through
- Failure count tracked
- Opens when threshold exceeded

#### Open (Failing Fast)
- All requests immediately fail
- No actual requests made
- Transitions to half-open after timeout

#### Half-Open (Testing)
- Limited requests allowed through
- Closes if successful
- Opens if failures continue

### Circuit Breaker Monitoring

```python
class CircuitBreakerMonitor:
    """Monitor circuit breaker state and metrics."""
    
    def __init__(self, retry_manager):
        self.retry_manager = retry_manager
    
    def get_circuit_breaker_status(self):
        """Get current circuit breaker status."""
        stats = self.retry_manager.get_retry_stats()
        
        return {
            'state': stats.get('circuit_breaker_state', 'closed'),
            'failure_count': stats.get('circuit_breaker_failures', 0),
            'last_failure_time': stats.get('last_failure_time'),
            'success_count': stats.get('circuit_breaker_successes', 0)
        }
    
    def should_alert(self):
        """Check if circuit breaker status requires alerting."""
        status = self.get_circuit_breaker_status()
        
        # Alert if circuit breaker is open
        if status['state'] == 'open':
            return True
        
        # Alert if failure rate is high
        total_requests = status['failure_count'] + status['success_count']
        if total_requests > 10:
            failure_rate = status['failure_count'] / total_requests
            return failure_rate > 0.5
        
        return False

# Usage
monitor = CircuitBreakerMonitor(retry_manager)
if monitor.should_alert():
    print("🚨 Circuit breaker alert - high failure rate detected!")
```

## Performance Optimization

### Retry Target Generation

Optimize retry targets for better performance and reliability.

```python
def generate_optimized_retry_targets(models, regions, unified_manager):
    """Generate optimized retry targets based on performance metrics."""
    
    targets = []
    
    # Get performance data (mock implementation)
    performance_data = get_historical_performance_data()
    
    for model in models:
        for region in regions:
            access_info = unified_manager.get_model_access_info(model, region)
            if not access_info:
                continue
            
            # Calculate priority based on historical performance
            key = f"{model}_{region}"
            avg_latency = performance_data.get(key, {}).get('avg_latency', 1000)
            success_rate = performance_data.get(key, {}).get('success_rate', 0.9)
            
            priority = success_rate / (avg_latency / 1000)  # Success rate per second
            
            targets.append({
                'model': model,
                'region': region,
                'access_info': access_info,
                'priority': priority
            })
    
    # Sort by priority (highest first)
    targets.sort(key=lambda x: x['priority'], reverse=True)
    
    return targets

# Usage
optimized_targets = generate_optimized_retry_targets(
    ["Claude 3.5 Sonnet", "Claude 3 Haiku"],
    ["us-east-1", "us-west-2"],
    unified_manager
)
```

### Batch Retry Operations

Optimize retry logic for batch operations.

```python
class BatchRetryManager:
    """Optimized retry manager for batch operations."""
    
    def __init__(self, retry_config):
        self.retry_config = retry_config
        self.batch_stats = {}
    
    def execute_batch_with_retry(self, operations, max_concurrent=5):
        """Execute batch operations with optimized retry logic."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        results = []
        failed_operations = []
        
        # Execute operations in batches
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = []
            
            for i, operation in enumerate(operations):
                future = executor.submit(self._execute_with_retry, operation, i)
                futures.append(future)
            
            # Collect results
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    failed_operations.append(e)
        
        return results, failed_operations
    
    def _execute_with_retry(self, operation, operation_id):
        """Execute single operation with retry logic."""
        last_exception = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                return operation()
            except Exception as e:
                last_exception = e
                
                if not self._should_retry(e, attempt):
                    break
                
                # Calculate delay
                delay = self._calculate_delay(attempt)
                time.sleep(delay)
        
        raise last_exception
    
    def _should_retry(self, exception, attempt):
        """Determine if operation should be retried."""
        if attempt >= self.retry_config.max_attempts - 1:
            return False
        
        # Add custom retry logic here
        return True
    
    def _calculate_delay(self, attempt):
        """Calculate delay for next attempt."""
        if self.retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.retry_config.base_delay * (2 ** attempt)
            return min(delay, self.retry_config.max_delay)
        
        return self.retry_config.base_delay
```

## Monitoring and Metrics

### Built-in Metrics

```python
# Get retry statistics
retry_stats = manager.get_retry_stats()

print("Retry Statistics:")
print(f"  Total Requests: {retry_stats['total_requests']}")
print(f"  Successful Requests: {retry_stats['successful_requests']}")
print(f"  Failed Requests: {retry_stats['failed_requests']}")
print(f"  Total Retry Attempts: {retry_stats['total_retry_attempts']}")
print(f"  Average Attempts per Request: {retry_stats['avg_attempts_per_request']:.2f}")
print(f"  Success Rate: {retry_stats['success_rate']:.2%}")

# Circuit breaker metrics
if retry_stats.get('circuit_breaker_enabled'):
    print(f"\nCircuit Breaker:")
    print(f"  State: {retry_stats['circuit_breaker_state']}")
    print(f"  Failures: {retry_stats['circuit_breaker_failures']}")
    print(f"  Last State Change: {retry_stats['last_state_change']}")
```

### Custom Metrics Collection

```python
import time
from collections import defaultdict
from datetime import datetime

class RetryMetricsCollector:
    """Collect and analyze retry metrics."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.request_history = []
    
    def record_request(self, model, region, attempts, success, duration):
        """Record a request with retry information."""
        timestamp = datetime.now()
        
        record = {
            'timestamp': timestamp,
            'model': model,
            'region': region,
            'attempts': attempts,
            'success': success,
            'duration': duration
        }
        
        self.request_history.append(record)
        
        # Update metrics
        key = f"{model}_{region}"
        self.metrics[key].append(record)
    
    def get_performance_summary(self, time_window_minutes=60):
        """Get performance summary for recent time window."""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        recent_requests = [r for r in self.request_history if r['timestamp'] > cutoff_time]
        
        if not recent_requests:
            return {}
        
        summary = {}
        
        # Group by model/region
        for record in recent_requests:
            key = f"{record['model']}_{record['region']}"
            
            if key not in summary:
                summary[key] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'total_attempts': 0,
                    'total_duration': 0
                }
            
            summary[key]['total_requests'] += 1
            summary[key]['total_attempts'] += record['attempts']
            summary[key]['total_duration'] += record['duration']
            
            if record['success']:
                summary[key]['successful_requests'] += 1
        
        # Calculate derived metrics
        for key, data in summary.items():
            data['success_rate'] = data['successful_requests'] / data['total_requests']
            data['avg_attempts'] = data['total_attempts'] / data['total_requests']
            data['avg_duration'] = data['total_duration'] / data['total_requests']
        
        return summary
    
    def get_retry_patterns(self):
        """Analyze retry patterns and identify issues."""
        patterns = {
            'high_retry_models': [],
            'failing_regions': [],
            'slow_endpoints': []
        }
        
        summary = self.get_performance_summary()
        
        for key, data in summary.items():
            model, region = key.split('_', 1)
            
            # High retry rate
            if data['avg_attempts'] > 2.0:
                patterns['high_retry_models'].append({
                    'model': model,
                    'region': region,
                    'avg_attempts': data['avg_attempts']
                })
            
            # Low success rate
            if data['success_rate'] < 0.8:
                patterns['failing_regions'].append({
                    'model': model,
                    'region': region,
                    'success_rate': data['success_rate']
                })
            
            # High latency
            if data['avg_duration'] > 5000:  # 5 seconds
                patterns['slow_endpoints'].append({
                    'model': model,
                    'region': region,
                    'avg_duration': data['avg_duration']
                })
        
        return patterns

# Usage
metrics_collector = RetryMetricsCollector()

# Integrate with retry manager (conceptual)
def monitored_request(model, region):
    start_time = time.time()
    attempts = 0
    success = False
    
    try:
        # Execute request with retry logic
        response = execute_request(model, region)
        success = True
        return response
    except Exception as e:
        raise e
    finally:
        duration = (time.time() - start_time) * 1000
        metrics_collector.record_request(model, region, attempts, success, duration)

# Analyze patterns
patterns = metrics_collector.get_retry_patterns()
if patterns['high_retry_models']:
    print("⚠️  Models with high retry rates:")
    for item in patterns['high_retry_models']:
        print(f"   {item['model']} in {item['region']}: {item['avg_attempts']:.1f} attempts")
```

## Best Practices

### 1. Configuration Guidelines

```python
# ✅ Good: Environment-specific retry configuration
def get_retry_config_for_environment():
    """Get retry config based on deployment environment."""
    
    env = os.getenv('ENVIRONMENT', 'development')
    
    if env == 'production':
        return RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_attempts=5,
            base_delay=1.0,
            max_delay=120.0,
            enable_circuit_breaker=True,
            circuit_breaker_threshold=10
        )
    
    elif env == 'staging':
        return RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_attempts=3,
            base_delay=0.5,
            max_delay=30.0,
            enable_circuit_breaker=True,
            circuit_breaker_threshold=5
        )
    
    else:  # development
        return RetryConfig(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            max_attempts=2,
            base_delay=0.1,
            max_delay=2.0,
            enable_circuit_breaker=False
        )

# ❌ Bad: One-size-fits-all configuration
retry_config = RetryConfig(max_attempts=10, max_delay=300.0)  # Too aggressive
```

### 2. Error Handling Integration

```python
# ✅ Good: Comprehensive error handling with retry context
def robust_llm_request(manager, messages):
    """Make LLM request with comprehensive error handling."""
    
    try:
        response = manager.converse(messages=messages)
        
        # Log successful request with retry info
        if response.get_attempt_count() > 1:
            logger.info(f"Request succeeded after {response.get_attempt_count()} attempts")
        
        return response
        
    except RetryExhaustedError as e:
        # All retry attempts failed
        logger.error(f"Request failed after {e.total_attempts} attempts")
        logger.error(f"Regions tried: {e.regions_attempted}")
        logger.error(f"Models tried: {e.models_attempted}")
        
        # Implement fallback logic
        return fallback_response(messages)
        
    except RequestValidationError as e:
        # Non-retryable validation error
        logger.warning(f"Request validation failed: {e}")
        return None

# ❌ Bad: Generic error handling without retry context
def bad_llm_request(manager, messages):
    try:
        return manager.converse(messages=messages)
    except Exception as e:
        print(f"Error: {e}")  # No context about retry attempts
        return None
```

### 3. Performance Monitoring

```python
# ✅ Good: Proactive performance monitoring
class RetryPerformanceMonitor:
    """Monitor retry performance and alert on issues."""
    
    def __init__(self, alert_threshold=0.3):
        self.alert_threshold = alert_threshold
        self.recent_requests = []
    
    def monitor_request(self, response):
        """Monitor individual request performance."""
        self.recent_requests.append({
            'timestamp': datetime.now(),
            'attempts': response.get_attempt_count(),
            'success': response.was_successful(),
            'duration': response.total_duration_ms
        })
        
        # Keep only recent requests (last hour)
        cutoff = datetime.now() - timedelta(hours=1)
        self.recent_requests = [r for r in self.recent_requests if r['timestamp'] > cutoff]
        
        # Check for performance issues
        self._check_performance_alerts()
    
    def _check_performance_alerts(self):
        """Check for performance issues requiring attention."""
        if len(self.recent_requests) < 10:
            return
        
        # Calculate retry rate
        total_attempts = sum(r['attempts'] for r in self.recent_requests)
        avg_attempts = total_attempts / len(self.recent_requests)
        
        if avg_attempts > 2.0:
            logger.warning(f"High retry rate detected: {avg_attempts:.1f} attempts per request")
        
        # Calculate success rate
        successful_requests = sum(1 for r in self.recent_requests if r['success'])
        success_rate = successful_requests / len(self.recent_requests)
        
        if success_rate < 0.9:
            logger.error(f"Low success rate detected: {success_rate:.2%}")

# Usage
monitor = RetryPerformanceMonitor()

