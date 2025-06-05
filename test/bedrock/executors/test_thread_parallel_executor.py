"""
Tests for ThreadParallelExecutor class.
"""

import pytest
import time
from unittest.mock import Mock, patch
from concurrent.futures import TimeoutError as FutureTimeoutError

from bedrock.executors.thread_parallel_executor import ThreadParallelExecutor, ThreadExecutionContext
from bedrock.models.parallel_structures import (
    BedrockConverseRequest, RegionAssignment, ParallelProcessingConfig
)
from bedrock.models.bedrock_response import BedrockResponse
from bedrock.exceptions.parallel_exceptions import RequestTimeoutError, ParallelExecutionError


class TestThreadExecutionContext:
    """Test cases for ThreadExecutionContext."""
    
    def test_initialization(self):
        """Test ThreadExecutionContext initialization."""
        context = ThreadExecutionContext()
        
        assert context.start_time is not None
        assert len(context.active_requests) == 0
        assert len(context.completed_requests) == 0
        assert len(context.failed_requests) == 0
        assert len(context.region_load) == 0
        assert context.lock is not None
    
    def test_add_active_request(self):
        """Test adding a request to active set."""
        context = ThreadExecutionContext()
        request_id = "test_request_123"
        
        context.add_active_request(request_id=request_id)
        
        assert request_id in context.active_requests
        assert len(context.active_requests) == 1
    
    def test_move_to_completed(self):
        """Test moving a request from active to completed."""
        context = ThreadExecutionContext()
        request_id = "test_request_123"
        
        context.add_active_request(request_id=request_id)
        context.move_to_completed(request_id=request_id)
        
        assert request_id not in context.active_requests
        assert request_id in context.completed_requests
        assert len(context.active_requests) == 0
        assert len(context.completed_requests) == 1
    
    def test_move_to_failed(self):
        """Test moving a request from active to failed."""
        context = ThreadExecutionContext()
        request_id = "test_request_123"
        
        context.add_active_request(request_id=request_id)
        context.move_to_failed(request_id=request_id)
        
        assert request_id not in context.active_requests
        assert request_id in context.failed_requests
        assert len(context.active_requests) == 0
        assert len(context.failed_requests) == 1
    
    def test_get_active_count(self):
        """Test getting active request count."""
        context = ThreadExecutionContext()
        
        assert context.get_active_count() == 0
        
        context.add_active_request(request_id="req1")
        context.add_active_request(request_id="req2")
        
        assert context.get_active_count() == 2
    
    def test_get_completion_rate(self):
        """Test calculating completion rate."""
        context = ThreadExecutionContext()
        
        # Initially, no requests - should return 0
        assert context.get_completion_rate() == 0.0
        
        # Add some requests and complete some
        context.add_active_request(request_id="req1")
        context.add_active_request(request_id="req2")
        context.add_active_request(request_id="req3")
        
        context.move_to_completed(request_id="req1")
        context.move_to_failed(request_id="req2")
        
        # 2 completed (1 success + 1 failed), 1 active = 2/3 = 66.67%
        completion_rate = context.get_completion_rate()
        assert abs(completion_rate - 66.67) < 0.1
    
    def test_get_elapsed_time_ms(self):
        """Test calculating elapsed time."""
        context = ThreadExecutionContext()
        
        # Should be very small elapsed time
        elapsed = context.get_elapsed_time_ms()
        assert elapsed >= 0
        assert elapsed < 100  # Should be less than 100ms


class TestThreadParallelExecutor:
    """Test cases for ThreadParallelExecutor."""
    
    def test_initialization(self):
        """Test ThreadParallelExecutor initialization."""
        config = ParallelProcessingConfig(
            max_concurrent_requests=10,
            request_timeout_seconds=30
        )
        
        executor = ThreadParallelExecutor(config=config)
        
        assert executor.get_config() == config
        assert executor.get_execution_context() is None
    
    def test_execute_requests_parallel_success(self):
        """Test successful parallel execution."""
        config = ParallelProcessingConfig(max_concurrent_requests=2)
        executor = ThreadParallelExecutor(config=config)
        
        # Create test data
        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 1"}]}],
                request_id="req1"
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 2"}]}],
                request_id="req2"
            )
        ]
        
        assignments = [
            RegionAssignment(request_id="req1", assigned_regions=["us-east-1"]),
            RegionAssignment(request_id="req2", assigned_regions=["us-west-2"])
        ]
        
        request_map = {req.request_id: req for req in requests if req.request_id is not None}
        
        # Mock successful responses
        def mock_execute_func(converse_args):
            return BedrockResponse(success=True)
        
        # Execute
        responses = executor.execute_requests_parallel(
            assignments=assignments,
            request_map=request_map,
            execute_single_request_func=mock_execute_func
        )
        
        # Verify results
        assert len(responses) == 2
        assert "req1" in responses
        assert "req2" in responses
        assert responses["req1"].success
        assert responses["req2"].success
    
    def test_execute_requests_parallel_with_failure(self):
        """Test parallel execution with some failures."""
        config = ParallelProcessingConfig(max_concurrent_requests=2)
        executor = ThreadParallelExecutor(config=config)
        
        # Create test data
        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 1"}]}],
                request_id="req1"
            ),
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello 2"}]}],
                request_id="req2"
            )
        ]
        
        assignments = [
            RegionAssignment(request_id="req1", assigned_regions=["us-east-1"]),
            RegionAssignment(request_id="req2", assigned_regions=["us-west-2"])
        ]
        
        request_map = {req.request_id: req for req in requests if req.request_id is not None}
        
        # Mock execute function that fails for req2
        def mock_execute_func(converse_args):
            # Check message content to determine which request this is
            message_text = converse_args["messages"][0]["content"][0]["text"]
            if "Hello 2" in message_text:
                raise Exception("Simulated failure")
            return BedrockResponse(success=True)
        
        # Execute
        responses = executor.execute_requests_parallel(
            assignments=assignments,
            request_map=request_map,
            execute_single_request_func=mock_execute_func
        )
        
        # Verify results
        assert len(responses) == 2
        assert "req1" in responses
        assert "req2" in responses
        assert responses["req1"].success
        assert not responses["req2"].success
    
    def test_execute_requests_parallel_timeout(self):
        """Test parallel execution with timeout."""
        config = ParallelProcessingConfig(
            max_concurrent_requests=1,
            request_timeout_seconds=1  # Short timeout
        )
        executor = ThreadParallelExecutor(config=config)
        
        # Create test data
        requests = [
            BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello"}]}],
                request_id="req1"
            )
        ]
        
        assignments = [
            RegionAssignment(request_id="req1", assigned_regions=["us-east-1"])
        ]
        
        request_map = {req.request_id: req for req in requests if req.request_id is not None}
        
        # Mock execute function that takes too long
        def mock_execute_func(converse_args):
            time.sleep(2)  # Sleep longer than timeout
            return BedrockResponse(success=True)
        
        # Execute
        responses = executor.execute_requests_parallel(
            assignments=assignments,
            request_map=request_map,
            execute_single_request_func=mock_execute_func
        )
        
        # Verify timeout handled correctly
        assert len(responses) == 1
        assert "req1" in responses
        assert not responses["req1"].success
        assert any("timed out" in warning.lower() for warning in responses["req1"].get_warnings())
    
    def test_execute_requests_parallel_missing_request(self):
        """Test handling of missing request in request_map."""
        config = ParallelProcessingConfig(max_concurrent_requests=1)
        executor = ThreadParallelExecutor(config=config)
        
        # Create assignments but incomplete request_map
        assignments = [
            RegionAssignment(request_id="req1", assigned_regions=["us-east-1"]),
            RegionAssignment(request_id="req2", assigned_regions=["us-west-2"])
        ]
        
        request_map = {
            "req1": BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello"}]}],
                request_id="req1"
            )
            # req2 is missing
        }
        
        def mock_execute_func(converse_args):
            return BedrockResponse(success=True)
        
        # Execute
        responses = executor.execute_requests_parallel(
            assignments=assignments,
            request_map=request_map,
            execute_single_request_func=mock_execute_func
        )
        
        # Should handle missing request gracefully
        assert len(responses) == 2
        assert "req1" in responses
        assert "req2" in responses
        assert responses["req1"].success
        assert not responses["req2"].success  # Missing request should fail
    
    def test_create_timeout_response(self):
        """Test creating timeout response."""
        config = ParallelProcessingConfig()
        executor = ThreadParallelExecutor(config=config)
        
        response = executor._create_timeout_response(request_id="test_req")
        
        assert not response.success
        assert len(response.get_warnings()) > 0
        assert "timed out" in response.get_warnings()[0].lower()
    
    def test_create_error_response(self):
        """Test creating error response."""
        config = ParallelProcessingConfig()
        executor = ThreadParallelExecutor(config=config)
        
        test_error = Exception("Test error message")
        response = executor._create_error_response(request_id="test_req", error=test_error)
        
        assert not response.success
        assert len(response.get_warnings()) > 0
        assert "Test error message" in response.get_warnings()[0]
    
    def test_execute_request_with_timeout_success(self):
        """Test single request execution with timeout - success case."""
        config = ParallelProcessingConfig(request_timeout_seconds=5)
        executor = ThreadParallelExecutor(config=config)
        
        # Set up execution context
        executor._execution_context = ThreadExecutionContext()
        
        request = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello"}]}],
            request_id="test_req"
        )
        
        assignment = RegionAssignment(request_id="test_req", assigned_regions=["us-east-1"])
        
        def mock_execute_func(converse_args):
            return BedrockResponse(success=True)
        
        # Execute
        response = executor._execute_request_with_timeout(
            request=request,
            assignment=assignment,
            execute_single_request_func=mock_execute_func
        )
        
        assert response.success
    
    def test_execute_request_with_timeout_timeout_error(self):
        """Test single request execution with timeout - timeout case."""
        config = ParallelProcessingConfig(request_timeout_seconds=1)
        executor = ThreadParallelExecutor(config=config)
        
        # Set up execution context
        executor._execution_context = ThreadExecutionContext()
        
        request = BedrockConverseRequest(
            messages=[{"role": "user", "content": [{"text": "Hello"}]}],
            request_id="test_req"
        )
        
        assignment = RegionAssignment(request_id="test_req", assigned_regions=["us-east-1"])
        
        def mock_execute_func(converse_args):
            time.sleep(2)  # Sleep longer than timeout
            return BedrockResponse(success=True)
        
        # Execute - should raise RequestTimeoutError
        with pytest.raises(RequestTimeoutError) as exc_info:
            executor._execute_request_with_timeout(
                request=request,
                assignment=assignment,
                execute_single_request_func=mock_execute_func
            )
        
        assert "test_req" in str(exc_info.value)
        assert "timeout" in str(exc_info.value).lower()
    
    def test_handle_missing_responses(self):
        """Test handling missing responses."""
        config = ParallelProcessingConfig()
        executor = ThreadParallelExecutor(config=config)
        
        assignments = [
            RegionAssignment(request_id="req1", assigned_regions=["us-east-1"]),
            RegionAssignment(request_id="req2", assigned_regions=["us-west-2"]),
            RegionAssignment(request_id="req3", assigned_regions=["eu-west-1"])
        ]
        
        # Only req1 and req2 have responses
        responses = {
            "req1": BedrockResponse(success=True),
            "req2": BedrockResponse(success=False)
        }
        
        # Handle missing responses
        complete_responses = executor._handle_missing_responses(
            responses=responses,
            assignments=assignments
        )
        
        # Should now have all 3 responses
        assert len(complete_responses) == 3
        assert "req1" in complete_responses
        assert "req2" in complete_responses
        assert "req3" in complete_responses
        
        # req3 should be a failed response
        assert complete_responses["req1"].success
        assert not complete_responses["req2"].success
        assert not complete_responses["req3"].success
        assert "did not complete" in complete_responses["req3"].get_warnings()[0]
