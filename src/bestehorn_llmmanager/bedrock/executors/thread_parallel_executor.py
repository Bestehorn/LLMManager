"""
Thread-based parallel execution engine for LLM Manager system.
Handles synchronous execution of requests using ThreadPoolExecutor for concurrency control.
"""

import concurrent.futures
import logging
import threading
from datetime import datetime
from typing import Callable, Dict, List, Optional, cast

from ..exceptions.parallel_exceptions import ParallelExecutionError, RequestTimeoutError
from ..models.bedrock_response import BedrockResponse
from ..models.parallel_constants import ParallelErrorMessages, ParallelLogMessages
from ..models.parallel_structures import (
    BedrockConverseRequest,
    ParallelProcessingConfig,
    RegionAssignment,
)


class ThreadExecutionContext:
    """
    Context information for thread-based parallel execution tracking.

    Attributes:
        start_time: When parallel execution started
        active_requests: Set of currently active request IDs
        completed_requests: Set of completed request IDs
        failed_requests: Set of failed request IDs
        region_load: Current load per region
        lock: Threading lock for thread-safe operations
    """

    def __init__(self) -> None:
        """Initialize the execution context."""
        self.start_time: datetime = datetime.now()
        self.active_requests: set = set()
        self.completed_requests: set = set()
        self.failed_requests: set = set()
        self.region_load: Dict[str, int] = {}
        self.lock: threading.Lock = threading.Lock()

    def add_active_request(self, request_id: str) -> None:
        """Thread-safely add a request to active set."""
        with self.lock:
            self.active_requests.add(request_id)

    def move_to_completed(self, request_id: str) -> None:
        """Thread-safely move a request from active to completed."""
        with self.lock:
            self.active_requests.discard(request_id)
            self.completed_requests.add(request_id)

    def move_to_failed(self, request_id: str) -> None:
        """Thread-safely move a request from active to failed."""
        with self.lock:
            self.active_requests.discard(request_id)
            self.failed_requests.add(request_id)

    def get_active_count(self) -> int:
        """Get count of currently active requests."""
        with self.lock:
            return len(self.active_requests)

    def get_completion_rate(self) -> float:
        """Get completion rate as percentage."""
        with self.lock:
            total = (
                len(self.completed_requests) + len(self.failed_requests) + len(self.active_requests)
            )
            if total == 0:
                return 0.0
            completed = len(self.completed_requests) + len(self.failed_requests)
            return (completed / total) * 100.0

    def get_elapsed_time_ms(self) -> float:
        """Get elapsed time since start in milliseconds."""
        return (datetime.now() - self.start_time).total_seconds() * 1000


class ThreadParallelExecutor:
    """
    Executes BedrockConverse requests in parallel using ThreadPoolExecutor.

    Provides functionality for:
    - Thread-based execution with concurrency control
    - Request timeout handling
    - Context tracking and monitoring
    - Integration with existing LLMManager retry logic
    """

    def __init__(self, config: ParallelProcessingConfig) -> None:
        """
        Initialize the thread-based parallel executor.

        Args:
            config: Configuration for parallel processing behavior
        """
        self._logger = logging.getLogger(__name__)
        self._config = config

        # Execution context for tracking
        self._execution_context: Optional[ThreadExecutionContext] = None

    def execute_requests_parallel(
        self,
        assignments: List[RegionAssignment],
        request_map: Dict[str, BedrockConverseRequest],
        execute_single_request_func: Callable,
    ) -> Dict[str, BedrockResponse]:
        """
        Execute multiple requests in parallel using ThreadPoolExecutor.

        Args:
            assignments: List of region assignments for requests
            request_map: Dictionary mapping request_id to BedrockConverseRequest
            execute_single_request_func: Function to execute a single request

        Returns:
            Dictionary mapping request_id to BedrockResponse

        Raises:
            ParallelExecutionError: If parallel execution fails
        """
        # Initialize execution context
        self._execution_context = self._create_execution_context(assignments=assignments)

        try:
            # Execute tasks and collect results
            responses = self._execute_with_thread_pool(
                assignments=assignments,
                request_map=request_map,
                execute_single_request_func=execute_single_request_func,
            )

            self._log_execution_completion(responses=responses)

            return responses

        except Exception as e:
            self._logger.error(f"Thread-based parallel execution failed: {e}")
            raise ParallelExecutionError(
                message=f"Parallel execution failed: {str(e)}",
                failed_requests=list(request_map.keys()),
                total_requests=len(request_map),
            ) from e
        finally:
            self._execution_context = None

    def _create_execution_context(
        self, assignments: List[RegionAssignment]
    ) -> ThreadExecutionContext:
        """
        Create execution context for tracking parallel execution.

        Args:
            assignments: List of region assignments

        Returns:
            ThreadExecutionContext for tracking
        """
        context = ThreadExecutionContext()

        # Initialize region load tracking
        for assignment in assignments:
            for region in assignment.assigned_regions:
                if region not in context.region_load:
                    context.region_load[region] = 0
                context.region_load[region] += 1

        return context

    def _execute_with_thread_pool(
        self,
        assignments: List[RegionAssignment],
        request_map: Dict[str, BedrockConverseRequest],
        execute_single_request_func: Callable,
    ) -> Dict[str, BedrockResponse]:
        """
        Execute requests using ThreadPoolExecutor with proper resource management.

        Args:
            assignments: List of region assignments
            request_map: Dictionary of requests
            execute_single_request_func: Function to execute single request

        Returns:
            Dictionary of responses
        """
        self._logger.info(
            ParallelLogMessages.PARALLEL_EXECUTION_STARTED.format(
                request_count=len(assignments),
                concurrent_limit=self._config.max_concurrent_requests,
            )
        )

        responses = {}

        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self._config.max_concurrent_requests, thread_name_prefix="LLMParallel"
        ) as executor:

            # Submit all tasks
            future_to_request_id = self._submit_execution_tasks(
                executor=executor,
                assignments=assignments,
                request_map=request_map,
                execute_single_request_func=execute_single_request_func,
            )

            # Collect results as they complete
            responses = self._collect_execution_results(
                future_to_request_id=future_to_request_id, assignments=assignments
            )

        return responses

    def _submit_execution_tasks(
        self,
        executor: concurrent.futures.ThreadPoolExecutor,
        assignments: List[RegionAssignment],
        request_map: Dict[str, BedrockConverseRequest],
        execute_single_request_func: Callable,
    ) -> Dict[concurrent.futures.Future, str]:
        """
        Submit all execution tasks to the thread pool.

        Args:
            executor: ThreadPoolExecutor instance
            assignments: List of region assignments
            request_map: Dictionary of requests
            execute_single_request_func: Function to execute single request

        Returns:
            Dictionary mapping Future to request_id
        """
        future_to_request_id = {}

        for assignment in assignments:
            request = request_map.get(assignment.request_id)
            if request is None:
                self._logger.warning(f"Request not found for ID: {assignment.request_id}")
                continue

            # Submit task for this request
            future = executor.submit(
                self._execute_single_request_with_context,
                request=request,
                assignment=assignment,
                execute_single_request_func=execute_single_request_func,
            )

            future_to_request_id[future] = assignment.request_id

        return future_to_request_id

    def _collect_execution_results(
        self,
        future_to_request_id: Dict[concurrent.futures.Future, str],
        assignments: List[RegionAssignment],
    ) -> Dict[str, BedrockResponse]:
        """
        Collect results from completed futures with timeout handling.

        Args:
            future_to_request_id: Dictionary mapping Future to request_id
            assignments: Original assignments

        Returns:
            Dictionary of responses
        """
        responses = {}

        # Process completed futures with timeout
        for future in concurrent.futures.as_completed(
            future_to_request_id.keys(),
            timeout=self._config.request_timeout_seconds + 10,  # Add buffer for cleanup
        ):
            request_id = future_to_request_id[future]

            try:
                response = future.result(timeout=1.0)  # Short timeout since future is already done
                responses[request_id] = response

            except concurrent.futures.TimeoutError:
                # This shouldn't happen since future is already done, but handle it
                self._logger.error(f"Unexpected timeout collecting result for request {request_id}")
                responses[request_id] = self._create_timeout_response(request_id=request_id)

            except Exception as e:
                self._logger.error(f"Error collecting result for request {request_id}: {e}")
                responses[request_id] = self._create_error_response(request_id=request_id, error=e)

        # Check for missing responses and handle them
        responses = self._handle_missing_responses(responses=responses, assignments=assignments)

        return responses

    def _execute_single_request_with_context(
        self,
        request: BedrockConverseRequest,
        assignment: RegionAssignment,
        execute_single_request_func: Callable,
    ) -> BedrockResponse:
        """
        Execute a single request with context tracking and timeout.

        Args:
            request: BedrockConverseRequest to execute
            assignment: Region assignment for the request
            execute_single_request_func: Function to execute the request

        Returns:
            BedrockResponse with the result
        """
        request_id = assignment.request_id

        # Update context - request is now active
        if self._execution_context:
            self._execution_context.add_active_request(request_id=request_id)

        try:
            self._logger.debug(f"Starting execution for request {request_id}")

            # Execute with timeout using threading
            response = self._execute_request_with_timeout(
                request=request,
                assignment=assignment,
                execute_single_request_func=execute_single_request_func,
            )

            # Update context on success
            if self._execution_context:
                self._execution_context.move_to_completed(request_id=request_id)

            self._logger.debug(f"Completed execution for request {request_id}")
            return response

        except Exception as e:
            # Handle execution errors
            if self._execution_context:
                self._execution_context.move_to_failed(request_id=request_id)

            self._logger.error(f"Request {request_id} failed with error: {e}")

            if isinstance(e, RequestTimeoutError):
                return self._create_timeout_response(request_id=request_id)
            else:
                return self._create_error_response(request_id=request_id, error=e)

    def _execute_request_with_timeout(
        self,
        request: BedrockConverseRequest,
        assignment: RegionAssignment,
        execute_single_request_func: Callable,
    ) -> BedrockResponse:
        """
        Execute a single request with timeout using threading.

        Args:
            request: BedrockConverseRequest to execute
            assignment: Region assignment for the request
            execute_single_request_func: Function to execute the request

        Returns:
            BedrockResponse from the execution

        Raises:
            RequestTimeoutError: If request times out
        """
        # Convert request to converse arguments
        converse_args = request.to_converse_args()

        # Execute with timeout using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as timeout_executor:
            future = timeout_executor.submit(execute_single_request_func, converse_args)

            try:
                response = future.result(timeout=self._config.request_timeout_seconds)
                return cast(BedrockResponse, response)

            except concurrent.futures.TimeoutError:
                # Request timed out
                elapsed_time = (
                    self._execution_context.get_elapsed_time_ms() / 1000.0
                    if self._execution_context
                    else None
                )

                raise RequestTimeoutError(
                    message=ParallelErrorMessages.REQUEST_TIMEOUT_EXCEEDED.format(
                        request_id=assignment.request_id,
                        timeout_seconds=self._config.request_timeout_seconds,
                    ),
                    request_id=assignment.request_id,
                    timeout_seconds=self._config.request_timeout_seconds,
                    elapsed_seconds=elapsed_time,
                )

    def _create_timeout_response(self, request_id: str) -> BedrockResponse:
        """
        Create a failed response for a timed-out request.

        Args:
            request_id: ID of the request that timed out

        Returns:
            BedrockResponse indicating timeout
        """
        return BedrockResponse(
            success=False,
            warnings=[
                f"Request {request_id} timed out after {self._config.request_timeout_seconds} seconds"
            ],
        )

    def _create_error_response(self, request_id: str, error: Exception) -> BedrockResponse:
        """
        Create a failed response for a request that encountered an error.

        Args:
            request_id: ID of the request that failed
            error: Exception that occurred

        Returns:
            BedrockResponse indicating failure
        """
        return BedrockResponse(
            success=False, warnings=[f"Request {request_id} failed: {str(error)}"]
        )

    def _handle_missing_responses(
        self, responses: Dict[str, BedrockResponse], assignments: List[RegionAssignment]
    ) -> Dict[str, BedrockResponse]:
        """
        Handle any missing responses by creating failed responses.

        Args:
            responses: Dictionary of collected responses
            assignments: Original assignments

        Returns:
            Complete dictionary of responses
        """
        expected_request_ids = {assignment.request_id for assignment in assignments}
        actual_request_ids = set(responses.keys())
        missing_request_ids = expected_request_ids - actual_request_ids

        if missing_request_ids:
            self._logger.warning(f"Missing responses for requests: {missing_request_ids}")

            # Create failed responses for missing requests
            for missing_id in missing_request_ids:
                responses[missing_id] = BedrockResponse(
                    success=False, warnings=["Request execution did not complete"]
                )

        return responses

    def _log_execution_completion(self, responses: Dict[str, BedrockResponse]) -> None:
        """
        Log completion statistics for parallel execution.

        Args:
            responses: Dictionary of responses
        """
        successful_count = sum(1 for response in responses.values() if response.success)
        total_count = len(responses)

        if self._execution_context:
            duration_ms = self._execution_context.get_elapsed_time_ms()

            self._logger.info(
                ParallelLogMessages.PARALLEL_EXECUTION_COMPLETED.format(
                    successful=successful_count, total=total_count, duration_ms=duration_ms
                )
            )
        else:
            self._logger.info(
                f"Thread-based parallel execution completed: {successful_count}/{total_count} successful"
            )

    def get_execution_context(self) -> Optional[ThreadExecutionContext]:
        """
        Get current execution context.

        Returns:
            Current ThreadExecutionContext, None if not executing
        """
        return self._execution_context

    def get_config(self) -> ParallelProcessingConfig:
        """
        Get current parallel processing configuration.

        Returns:
            ParallelProcessingConfig being used
        """
        return self._config
