"""
Tests for parallel processing data structures.
"""

import pytest
import json
import time
from unittest.mock import patch

from bedrock.models.parallel_structures import (
    BedrockConverseRequest, ParallelResponse, ParallelProcessingConfig,
    ParallelExecutionStats, FailureHandlingStrategy, LoadBalancingStrategy,
    RegionAssignment, ParallelExecutionContext
)
from bedrock.models.bedrock_response import BedrockResponse


class TestBedrockConverseRequest:
    """Test cases for BedrockConverseRequest."""
    
    def test_initialization_with_auto_generated_id(self):
        """Test request creation with auto-generated ID."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        request = BedrockConverseRequest(messages=messages)
        
        assert request.messages == messages
        assert request.request_id is not None
        assert request.request_id.startswith("req_")
        assert len(request.request_id.split("_")) == 3  # req_hash_timestamp
    
    def test_initialization_with_provided_id(self):
        """Test request creation with provided ID."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        custom_id = "custom_request_123"
        
        request = BedrockConverseRequest(
            messages=messages,
            request_id=custom_id
        )
        
        assert request.request_id == custom_id
    
    def test_initialization_with_all_parameters(self):
        """Test request creation with all parameters."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        system = [{"text": "You are a helpful assistant"}]
        inference_config = {"maxTokens": 100, "temperature": 0.7}
        
        request = BedrockConverseRequest(
            messages=messages,
            system=system,
            inference_config=inference_config,
            request_id="test_123"
        )
        
        assert request.messages == messages
        assert request.system == system
        assert request.inference_config == inference_config
        assert request.request_id == "test_123"
    
    def test_to_converse_args(self):
        """Test conversion to converse API arguments."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        system = [{"text": "You are helpful"}]
        inference_config = {"maxTokens": 100}
        
        request = BedrockConverseRequest(
            messages=messages,
            system=system,
            inference_config=inference_config
        )
        
        args = request.to_converse_args()
        
        assert args["messages"] == messages
        assert args["system"] == system
        assert args["inferenceConfig"] == inference_config
        assert "request_id" not in args  # Should not be in converse args
    
    def test_to_converse_args_with_optional_fields(self):
        """Test conversion with only required fields."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        request = BedrockConverseRequest(messages=messages)
        
        args = request.to_converse_args()
        
        assert args["messages"] == messages
        assert len(args) == 1  # Only messages should be present
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        request = BedrockConverseRequest(messages=messages, request_id="test_123")
        
        result_dict = request.to_dict()
        
        assert result_dict["request_id"] == "test_123"
        assert result_dict["messages"] == messages
        assert result_dict["system"] is None
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "request_id": "test_123",
            "messages": [{"role": "user", "content": [{"text": "Hello"}]}],
            "system": [{"text": "You are helpful"}],
            "inference_config": {"maxTokens": 100}
        }
        
        request = BedrockConverseRequest.from_dict(data)
        
        assert request.request_id == "test_123"
        assert request.messages == data["messages"]
        assert request.system == data["system"]
        assert request.inference_config == data["inference_config"]
    
    def test_unique_id_generation(self):
        """Test that multiple requests generate unique IDs."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        
        request1 = BedrockConverseRequest(messages=messages)
        time.sleep(0.001)  # Small delay to ensure different timestamps
        request2 = BedrockConverseRequest(messages=messages)
        
        assert request1.request_id != request2.request_id
    
    def test_repr(self):
        """Test string representation."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        request = BedrockConverseRequest(messages=messages, request_id="test_123")
        
        repr_str = repr(request)
        
        assert "BedrockConverseRequest" in repr_str
        assert "test_123" in repr_str
        assert "messages=1" in repr_str


class TestParallelProcessingConfig:
    """Test cases for ParallelProcessingConfig."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ParallelProcessingConfig()
        
        assert config.max_concurrent_requests == 5
        assert config.request_timeout_seconds == 300
        assert config.enable_request_prioritization == True
        assert config.failure_handling_strategy == FailureHandlingStrategy.CONTINUE_ON_FAILURE
        assert config.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN
        assert config.failure_threshold == 0.5
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = ParallelProcessingConfig(
            max_concurrent_requests=10,
            request_timeout_seconds=120,
            enable_request_prioritization=False,
            failure_handling_strategy=FailureHandlingStrategy.STOP_ON_THRESHOLD,
            load_balancing_strategy=LoadBalancingStrategy.RANDOM,
            failure_threshold=0.3
        )
        
        assert config.max_concurrent_requests == 10
        assert config.request_timeout_seconds == 120
        assert config.enable_request_prioritization == False
        assert config.failure_handling_strategy == FailureHandlingStrategy.STOP_ON_THRESHOLD
        assert config.load_balancing_strategy == LoadBalancingStrategy.RANDOM
        assert config.failure_threshold == 0.3
    
    def test_invalid_max_concurrent_requests(self):
        """Test validation of max_concurrent_requests."""
        with pytest.raises(ValueError) as exc_info:
            ParallelProcessingConfig(max_concurrent_requests=0)
        
        assert "max_concurrent_requests must be positive" in str(exc_info.value)
    
    def test_invalid_request_timeout(self):
        """Test validation of request_timeout_seconds."""
        with pytest.raises(ValueError) as exc_info:
            ParallelProcessingConfig(request_timeout_seconds=-1)
        
        assert "request_timeout_seconds must be positive" in str(exc_info.value)
    
    def test_invalid_failure_threshold(self):
        """Test validation of failure_threshold."""
        with pytest.raises(ValueError) as exc_info:
            ParallelProcessingConfig(failure_threshold=1.5)
        
        assert "failure_threshold must be between 0.0 and 1.0" in str(exc_info.value)


class TestParallelExecutionStats:
    """Test cases for ParallelExecutionStats."""
    
    def test_initialization(self):
        """Test stats initialization."""
        stats = ParallelExecutionStats(
            total_requests=10,
            successful_requests=8,
            failed_requests_count=2,
            average_request_duration_ms=150.5,
            max_request_duration_ms=300.0,
            min_request_duration_ms=50.0,
            concurrent_executions=5
        )
        
        assert stats.total_requests == 10
        assert stats.successful_requests == 8
        assert stats.failed_requests_count == 2
        assert stats.average_request_duration_ms == 150.5
        assert stats.max_request_duration_ms == 300.0
        assert stats.min_request_duration_ms == 50.0
        assert stats.concurrent_executions == 5
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = ParallelExecutionStats(
            total_requests=10,
            successful_requests=8,
            failed_requests_count=2,
            average_request_duration_ms=100.0,
            max_request_duration_ms=200.0,
            min_request_duration_ms=50.0,
            concurrent_executions=5
        )
        
        assert stats.success_rate == 80.0
        assert stats.failure_rate == 20.0
    
    def test_success_rate_zero_requests(self):
        """Test success rate with zero requests."""
        stats = ParallelExecutionStats(
            total_requests=0,
            successful_requests=0,
            failed_requests_count=0,
            average_request_duration_ms=0.0,
            max_request_duration_ms=0.0,
            min_request_duration_ms=0.0,
            concurrent_executions=0
        )
        
        assert stats.success_rate == 0.0
        assert stats.failure_rate == 100.0
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        region_dist = {"us-east-1": 5, "us-west-2": 3}
        stats = ParallelExecutionStats(
            total_requests=8,
            successful_requests=6,
            failed_requests_count=2,
            average_request_duration_ms=120.0,
            max_request_duration_ms=250.0,
            min_request_duration_ms=75.0,
            concurrent_executions=4,
            region_distribution=region_dist
        )
        
        result_dict = stats.to_dict()
        
        assert result_dict["total_requests"] == 8
        assert result_dict["successful_requests"] == 6
        assert result_dict["failed_requests_count"] == 2
        assert result_dict["region_distribution"] == region_dist


class TestParallelResponse:
    """Test cases for ParallelResponse."""
    
    def test_initialization(self):
        """Test parallel response initialization."""
        responses = {
            "req1": BedrockResponse(success=True),
            "req2": BedrockResponse(success=False)
        }
        
        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
            total_duration_ms=1500.0
        )
        
        assert parallel_response.success == True
        assert len(parallel_response.request_responses) == 2
        assert parallel_response.total_duration_ms == 1500.0
    
    def test_get_successful_responses(self):
        """Test getting only successful responses."""
        responses = {
            "req1": BedrockResponse(success=True),
            "req2": BedrockResponse(success=False),
            "req3": BedrockResponse(success=True)
        }
        
        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses
        )
        
        successful = parallel_response.get_successful_responses()
        
        assert len(successful) == 2
        assert "req1" in successful
        assert "req3" in successful
        assert "req2" not in successful
    
    def test_get_failed_responses(self):
        """Test getting only failed responses."""
        responses = {
            "req1": BedrockResponse(success=True),
            "req2": BedrockResponse(success=False),
            "req3": BedrockResponse(success=True)
        }
        
        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses
        )
        
        failed = parallel_response.get_failed_responses()
        
        assert len(failed) == 1
        assert "req2" in failed
        assert "req1" not in failed
        assert "req3" not in failed
    
    def test_get_response_by_id(self):
        """Test getting response by ID."""
        response1 = BedrockResponse(success=True)
        responses = {"req1": response1}
        
        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses
        )
        
        assert parallel_response.get_response_by_id("req1") == response1
        assert parallel_response.get_response_by_id("nonexistent") is None
    
    def test_get_success_rate(self):
        """Test success rate calculation."""
        responses = {
            "req1": BedrockResponse(success=True),
            "req2": BedrockResponse(success=False),
            "req3": BedrockResponse(success=True),
            "req4": BedrockResponse(success=True)
        }
        
        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses
        )
        
        assert parallel_response.get_success_rate() == 75.0
    
    def test_get_success_rate_empty(self):
        """Test success rate with no responses."""
        parallel_response = ParallelResponse(success=False)
        
        assert parallel_response.get_success_rate() == 0.0
    
    def test_repr(self):
        """Test string representation."""
        responses = {
            "req1": BedrockResponse(success=True),
            "req2": BedrockResponse(success=False)
        }
        
        parallel_response = ParallelResponse(
            success=True,
            request_responses=responses,
            total_duration_ms=1234.5
        )
        
        repr_str = repr(parallel_response)
        
        assert "ParallelResponse" in repr_str
        assert "success=True" in repr_str
        assert "responses=1/2" in repr_str  # 1 successful out of 2 total
        assert "1234.5ms" in repr_str


class TestRegionAssignment:
    """Test cases for RegionAssignment."""
    
    def test_initialization(self):
        """Test region assignment initialization."""
        assignment = RegionAssignment(
            request_id="req_123",
            assigned_regions=["us-east-1", "us-west-2"],
            priority=5
        )
        
        assert assignment.request_id == "req_123"
        assert assignment.assigned_regions == ["us-east-1", "us-west-2"]
        assert assignment.priority == 5
    
    def test_default_priority(self):
        """Test default priority value."""
        assignment = RegionAssignment(
            request_id="req_123",
            assigned_regions=["us-east-1"]
        )
        
        assert assignment.priority == 0
    
    def test_repr(self):
        """Test string representation."""
        assignment = RegionAssignment(
            request_id="req_123",
            assigned_regions=["us-east-1", "us-west-2"],
            priority=3
        )
        
        repr_str = repr(assignment)
        
        assert "RegionAssignment" in repr_str
        assert "req_123" in repr_str
        assert "us-east-1" in repr_str
        assert "priority=3" in repr_str


class TestParallelExecutionContext:
    """Test cases for ParallelExecutionContext."""
    
    def test_initialization(self):
        """Test execution context initialization."""
        from datetime import datetime
        start_time = datetime.now()
        
        context = ParallelExecutionContext(start_time=start_time)
        
        assert context.start_time == start_time
        assert len(context.active_requests) == 0
        assert len(context.completed_requests) == 0
        assert len(context.failed_requests) == 0
        assert len(context.region_load) == 0
    
    def test_get_active_count(self):
        """Test active request count."""
        from datetime import datetime
        context = ParallelExecutionContext(start_time=datetime.now())
        
        context.active_requests.add("req1")
        context.active_requests.add("req2")
        
        assert context.get_active_count() == 2
    
    def test_get_completion_rate(self):
        """Test completion rate calculation."""
        from datetime import datetime
        context = ParallelExecutionContext(start_time=datetime.now())
        
        context.active_requests.add("req1")
        context.completed_requests.add("req2")
        context.failed_requests.add("req3")
        
        # 2 completed (completed + failed) out of 3 total
        assert context.get_completion_rate() == (2/3) * 100
    
    def test_get_completion_rate_empty(self):
        """Test completion rate with no requests."""
        from datetime import datetime
        context = ParallelExecutionContext(start_time=datetime.now())
        
        assert context.get_completion_rate() == 0.0
    
    def test_get_elapsed_time_ms(self):
        """Test elapsed time calculation."""
        from datetime import datetime, timedelta
        start_time = datetime.now()
        
        with patch('bedrock.models.parallel_structures.datetime') as mock_datetime:
            # Mock current time to be 1 second after start time
            mock_datetime.now.return_value = start_time + timedelta(seconds=1)
            
            context = ParallelExecutionContext(start_time=start_time)
            elapsed = context.get_elapsed_time_ms()
            
            # Should be approximately 1000ms (1 second)
            assert abs(elapsed - 1000.0) < 10  # Allow small tolerance
