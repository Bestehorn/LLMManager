"""
Unit tests for ParallelExecutor.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.exceptions.parallel_exceptions import ParallelExecutionError
from bestehorn_llmmanager.bedrock.executors.parallel_executor import ParallelExecutor
from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse
from bestehorn_llmmanager.bedrock.models.parallel_structures import (
    BedrockConverseRequest,
    FailureHandlingStrategy,
    LoadBalancingStrategy,
    ParallelExecutionContext,
    ParallelProcessingConfig,
    RegionAssignment,
)


@pytest.mark.asyncio
class TestParallelExecutor:
    """Test cases for ParallelExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = ParallelProcessingConfig(
            max_concurrent_requests=2,
            request_timeout_seconds=10,
            failure_handling_strategy=FailureHandlingStrategy.CONTINUE_ON_FAILURE,
            failure_threshold=0.5,
            load_balancing_strategy=LoadBalancingStrategy.ROUND_ROBIN,
            enable_request_prioritization=False,
        )
        self.executor = ParallelExecutor(config=self.config)

        # Sample data
        self.sample_requests = {
            "req-1": BedrockConverseRequest(
                request_id="req-1", messages=[{"role": "user", "content": [{"text": "test1"}]}]
            ),
            "req-2": BedrockConverseRequest(
                request_id="req-2", messages=[{"role": "user", "content": [{"text": "test2"}]}]
            ),
        }

        self.sample_assignments = [
            RegionAssignment(request_id="req-1", assigned_regions=["us-east-1"], priority=0),
            RegionAssignment(request_id="req-2", assigned_regions=["us-west-2"], priority=0),
        ]

        self.successful_response = BedrockResponse(success=True)
        self.failed_response = BedrockResponse(success=False, warnings=["Test failure"])

    def test_init(self):
        """Test ParallelExecutor initialization."""
        executor = ParallelExecutor(config=self.config)
        assert executor.get_config() == self.config
        assert executor.get_execution_context() is None

    def test_get_config(self):
        """Test getting configuration."""
        assert self.executor.get_config() == self.config

    def test_get_execution_context_none(self):
        """Test getting execution context when none exists."""
        assert self.executor.get_execution_context() is None

    async def test_execute_requests_parallel_success(self):
        """Test successful parallel execution."""
        # Mock execute function
        async_execute_func = AsyncMock(return_value=self.successful_response)

        # Execute requests
        responses = await self.executor.execute_requests_parallel(
            assignments=self.sample_assignments,
            request_map=self.sample_requests,
            execute_single_request_func=async_execute_func,
        )

        # Verify results
        assert len(responses) == 2
        assert responses["req-1"].success
        assert responses["req-2"].success
        assert self.executor.get_execution_context() is None  # Should be cleared

    async def test_execute_requests_parallel_with_failures(self):
        """Test parallel execution with some failures."""

        # Mock execute function that fails for req-2
        def mock_execute(args):
            if "test2" in str(args):
                return self.failed_response
            return self.successful_response

        async_execute_func = AsyncMock(side_effect=mock_execute)

        responses = await self.executor.execute_requests_parallel(
            assignments=self.sample_assignments,
            request_map=self.sample_requests,
            execute_single_request_func=async_execute_func,
        )

        assert len(responses) == 2
        assert responses["req-1"].success
        assert not responses["req-2"].success

    async def test_execute_requests_parallel_timeout(self):
        """Test parallel execution with timeout."""

        # Mock execute function that hangs
        async def slow_execute(args):
            await asyncio.sleep(20)  # Longer than timeout
            return self.successful_response

        async_execute_func = AsyncMock(side_effect=slow_execute)

        responses = await self.executor.execute_requests_parallel(
            assignments=self.sample_assignments,
            request_map=self.sample_requests,
            execute_single_request_func=async_execute_func,
        )

        # All responses should exist but failed due to timeout
        assert len(responses) == 2
        for response in responses.values():
            assert not response.success
            assert any("timed out" in warning for warning in response.warnings)

    async def test_execute_requests_parallel_exception(self):
        """Test parallel execution with exceptions."""
        # Mock execute function that raises exception
        async_execute_func = AsyncMock(side_effect=Exception("Test exception"))

        with pytest.raises(ParallelExecutionError) as exc_info:
            await self.executor.execute_requests_parallel(
                assignments=self.sample_assignments,
                request_map=self.sample_requests,
                execute_single_request_func=async_execute_func,
            )

        assert exc_info.value.total_requests == 2
        assert len(exc_info.value.failed_requests) == 2

    def test_create_execution_context(self):
        """Test creation of execution context."""
        context = self.executor._create_execution_context(assignments=self.sample_assignments)

        assert isinstance(context, ParallelExecutionContext)
        assert isinstance(context.start_time, datetime)
        assert context.region_load["us-east-1"] == 1
        assert context.region_load["us-west-2"] == 1

    def test_create_execution_context_multiple_regions(self):
        """Test execution context with multiple regions per request."""
        assignments = [
            RegionAssignment(
                request_id="req-1", assigned_regions=["us-east-1", "us-west-2"], priority=0
            ),
        ]

        context = self.executor._create_execution_context(assignments=assignments)

        assert context.region_load["us-east-1"] == 1
        assert context.region_load["us-west-2"] == 1

    async def test_create_execution_tasks(self):
        """Test creation of execution tasks."""
        mock_func = AsyncMock()
        semaphore = asyncio.Semaphore(2)

        tasks = self.executor._create_execution_tasks(
            assignments=self.sample_assignments,
            request_map=self.sample_requests,
            execute_single_request_func=mock_func,
            semaphore=semaphore,
        )

        assert len(tasks) == 2
        for task in tasks:
            assert isinstance(task, asyncio.Task)
            assert task.get_name().startswith("request_")

    async def test_create_execution_tasks_missing_request(self):
        """Test task creation with missing request in map."""
        mock_func = AsyncMock()
        semaphore = asyncio.Semaphore(2)

        # Assignment for non-existent request
        assignments = [
            RegionAssignment(request_id="missing-req", assigned_regions=["us-east-1"], priority=0)
        ]

        with patch(
            "bestehorn_llmmanager.bedrock.executors.parallel_executor.logging.getLogger"
        ) as mock_logger:
            mock_logger.return_value.warning = Mock()

            tasks = self.executor._create_execution_tasks(
                assignments=assignments,
                request_map=self.sample_requests,
                execute_single_request_func=mock_func,
                semaphore=semaphore,
            )

            assert len(tasks) == 0
            mock_logger.return_value.warning.assert_called_once()

    async def test_execute_single_request_with_context_success(self):
        """Test single request execution with context tracking."""
        mock_func = AsyncMock(return_value=self.successful_response)
        semaphore = asyncio.Semaphore(1)

        # Set up execution context
        self.executor._execution_context = ParallelExecutionContext(start_time=datetime.now())

        result = await self.executor._execute_single_request_with_context(
            request=self.sample_requests["req-1"],
            assignment=self.sample_assignments[0],
            execute_single_request_func=mock_func,
            semaphore=semaphore,
        )

        request_id, response = result
        assert request_id == "req-1"
        assert response.success
        assert "req-1" in self.executor._execution_context.completed_requests

    async def test_execute_single_request_with_context_timeout(self):
        """Test single request execution with timeout."""
        # Create executor with very short timeout
        short_timeout_config = ParallelProcessingConfig(
            max_concurrent_requests=1,
            request_timeout_seconds=1,  # Very short timeout
            failure_handling_strategy=FailureHandlingStrategy.CONTINUE_ON_FAILURE,
        )
        executor = ParallelExecutor(config=short_timeout_config)

        # Mock function that takes too long
        async def slow_func(args):
            await asyncio.sleep(1)
            return self.successful_response

        mock_func = AsyncMock(side_effect=slow_func)
        semaphore = asyncio.Semaphore(1)

        # Set up execution context
        executor._execution_context = ParallelExecutionContext(start_time=datetime.now())

        result = await executor._execute_single_request_with_context(
            request=self.sample_requests["req-1"],
            assignment=self.sample_assignments[0],
            execute_single_request_func=mock_func,
            semaphore=semaphore,
        )

        request_id, response = result
        assert request_id == "req-1"
        assert not response.success
        assert any("timed out" in warning for warning in response.warnings)
        assert "req-1" in executor._execution_context.failed_requests

    async def test_execute_single_request_with_context_exception(self):
        """Test single request execution with exception."""
        mock_func = AsyncMock(side_effect=Exception("Test error"))
        semaphore = asyncio.Semaphore(1)

        # Set up execution context
        self.executor._execution_context = ParallelExecutionContext(start_time=datetime.now())

        result = await self.executor._execute_single_request_with_context(
            request=self.sample_requests["req-1"],
            assignment=self.sample_assignments[0],
            execute_single_request_func=mock_func,
            semaphore=semaphore,
        )

        request_id, response = result
        assert request_id == "req-1"
        assert not response.success
        assert any("Request failed" in warning for warning in response.warnings)
        assert "req-1" in self.executor._execution_context.failed_requests

    async def test_execute_request_async(self):
        """Test async request execution."""
        mock_func = Mock(return_value=self.successful_response)

        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=self.successful_response
            )

            response = await self.executor._execute_request_async(
                request=self.sample_requests["req-1"],
                assignment=self.sample_assignments[0],
                execute_single_request_func=mock_func,
            )

            assert response.success
            mock_loop.return_value.run_in_executor.assert_called_once()

    async def test_execute_tasks_with_monitoring_success(self):
        """Test task execution with monitoring - all success."""
        # Create mock tasks that return successful results
        task1 = AsyncMock()
        task1.get_name.return_value = "request_req1"
        task2 = AsyncMock()
        task2.get_name.return_value = "request_req2"

        # Mock asyncio.gather to return results
        with patch(
            "asyncio.gather",
            return_value=[("req-1", self.successful_response), ("req-2", self.successful_response)],
        ):
            results = await self.executor._execute_tasks_with_monitoring(tasks=[task1, task2])

            assert len(results) == 2
            assert all(isinstance(result, tuple) for result in results)
            assert all(result[1].success for result in results)

    async def test_execute_tasks_with_monitoring_with_exceptions(self):
        """Test task execution with monitoring - some exceptions."""
        task1 = AsyncMock()
        task1.get_name.return_value = "request_req1"
        task2 = AsyncMock()
        task2.get_name.return_value = "request_req2"

        # Mock asyncio.gather to return mixed results
        exception = Exception("Test exception")
        with patch("asyncio.gather", return_value=[("req-1", self.successful_response), exception]):
            with patch(
                "bestehorn_llmmanager.bedrock.executors.parallel_executor.logging.getLogger"
            ) as mock_logger:
                mock_logger.return_value.error = Mock()

                results = await self.executor._execute_tasks_with_monitoring(tasks=[task1, task2])

                assert len(results) == 2
                assert results[0][1].success  # First should be successful
                assert not results[1][1].success  # Second should be failed response
                mock_logger.return_value.error.assert_called_once()

    def test_process_execution_results(self):
        """Test processing of execution results."""
        results = [
            ("req-1", self.successful_response),
            ("req-2", self.failed_response),
        ]

        responses = self.executor._process_execution_results(
            results=results, assignments=self.sample_assignments
        )

        assert len(responses) == 2
        assert responses["req-1"].success
        assert not responses["req-2"].success

    def test_process_execution_results_missing_responses(self):
        """Test processing results with missing responses."""
        # Only provide result for req-1, req-2 is missing
        results = [("req-1", self.successful_response)]

        with patch(
            "bestehorn_llmmanager.bedrock.executors.parallel_executor.logging.getLogger"
        ) as mock_logger:
            mock_logger.return_value.warning = Mock()

            responses = self.executor._process_execution_results(
                results=results, assignments=self.sample_assignments
            )

            assert len(responses) == 2
            assert responses["req-1"].success
            assert not responses["req-2"].success  # Should be created as failed
            mock_logger.return_value.warning.assert_called_once()

    def test_log_execution_completion_with_context(self):
        """Test logging execution completion with context."""
        responses = {
            "req-1": self.successful_response,
            "req-2": self.failed_response,
        }

        # Set up execution context
        self.executor._execution_context = ParallelExecutionContext(start_time=datetime.now())

        with patch(
            "bestehorn_llmmanager.bedrock.executors.parallel_executor.logging.getLogger"
        ) as mock_logger:
            mock_logger.return_value.info = Mock()

            self.executor._log_execution_completion(responses=responses)

            mock_logger.return_value.info.assert_called_once()
            call_args = mock_logger.return_value.info.call_args[0][0]
            assert "1/2 successful" in call_args

    def test_log_execution_completion_without_context(self):
        """Test logging execution completion without context."""
        responses = {
            "req-1": self.successful_response,
            "req-2": self.failed_response,
        }

        with patch(
            "bestehorn_llmmanager.bedrock.executors.parallel_executor.logging.getLogger"
        ) as mock_logger:
            mock_logger.return_value.info = Mock()

            self.executor._log_execution_completion(responses=responses)

            mock_logger.return_value.info.assert_called_once()
            call_args = mock_logger.return_value.info.call_args[0][0]
            assert "1/2 successful" in call_args

    async def test_context_tracking_during_execution(self):
        """Test that execution context is properly tracked during execution."""
        mock_func = AsyncMock(return_value=self.successful_response)

        # Capture context during execution
        captured_context = None

        async def capture_context_func(args):
            nonlocal captured_context
            captured_context = self.executor.get_execution_context()
            return self.successful_response

        mock_func.side_effect = capture_context_func

        await self.executor.execute_requests_parallel(
            assignments=self.sample_assignments,
            request_map=self.sample_requests,
            execute_single_request_func=mock_func,
        )

        # Context should have been available during execution
        assert captured_context is not None
        assert isinstance(captured_context, ParallelExecutionContext)

        # Context should be cleared after execution
        assert self.executor.get_execution_context() is None

    async def test_semaphore_concurrency_control(self):
        """Test that semaphore properly controls concurrency."""
        config = ParallelProcessingConfig(
            max_concurrent_requests=1,  # Only allow 1 concurrent request
            request_timeout_seconds=10,
            failure_handling_strategy=FailureHandlingStrategy.CONTINUE_ON_FAILURE,
        )
        executor = ParallelExecutor(config=config)

        # Track execution order
        execution_order = []
        execution_event = asyncio.Event()

        async def ordered_execute(args):
            execution_order.append(f"start_{len(execution_order)}")
            await execution_event.wait()  # Wait for signal to continue
            execution_order.append(f"end_{len(execution_order)}")
            return self.successful_response

        mock_func = AsyncMock(side_effect=ordered_execute)

        # Start execution (should be non-blocking)
        execution_task = asyncio.create_task(
            executor.execute_requests_parallel(
                assignments=self.sample_assignments,
                request_map=self.sample_requests,
                execute_single_request_func=mock_func,
            )
        )

        # Give time for tasks to start
        await asyncio.sleep(0.1)

        # Only one should have started due to semaphore
        assert len([item for item in execution_order if item.startswith("start")]) <= 1

        # Release all tasks
        execution_event.set()

        # Wait for completion
        await execution_task

    async def test_integration_with_real_asyncio_behavior(self):
        """Test integration with real asyncio behavior."""
        # This test verifies the executor works with real asyncio primitives
        actual_results = []

        async def record_execution(args):
            # Simulate some async work
            await asyncio.sleep(0.01)
            actual_results.append(args)
            return self.successful_response

        mock_func = AsyncMock(side_effect=record_execution)

        responses = await self.executor.execute_requests_parallel(
            assignments=self.sample_assignments,
            request_map=self.sample_requests,
            execute_single_request_func=mock_func,
        )

        assert len(responses) == 2
        assert len(actual_results) == 2
        assert all(response.success for response in responses.values())
