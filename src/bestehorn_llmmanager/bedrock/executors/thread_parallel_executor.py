"""
Thread-based parallel execution engine for LLM Manager system.
Handles synchronous execution of requests using ThreadPoolExecutor for concurrency control.
"""

import collections
import concurrent.futures
import logging
import math
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, cast

from ..exceptions.parallel_exceptions import ParallelExecutionError, RequestTimeoutError
from ..models.bedrock_response import BedrockResponse
from ..models.llm_manager_structures import RetryConfig
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

    def _calculate_total_timeout(
        self, total_requests: int, max_concurrent: int, per_request_timeout: int
    ) -> float:
        """
        Calculate proper timeout for parallel execution accounting for sequential batches.

        When requests exceed max_concurrent workers, they process in sequential batches.
        This method calculates total time needed: batches * timeout + buffer.

        Formula: ceil(total_requests / max_concurrent) * per_request_timeout + buffer

        Args:
            total_requests: Total number of requests to process
            max_concurrent: Maximum concurrent requests
            per_request_timeout: Timeout per individual request in seconds

        Returns:
            Total timeout in seconds with 10% buffer for cleanup/overhead
        """
        if total_requests == 0 or max_concurrent == 0:
            return float(per_request_timeout)

        # Calculate number of sequential batches needed
        num_batches = math.ceil(total_requests / max_concurrent)

        # Total time = batches * per_request_timeout + 10% buffer
        total_time = num_batches * per_request_timeout
        buffer = total_time * 0.1  # 10% buffer for overhead

        return total_time + buffer

    def _handle_timeout(
        self,
        responses: Dict[str, BedrockResponse],
        in_flight_futures: Dict[concurrent.futures.Future, str],
        pending_assignments: List[RegionAssignment],
    ) -> Dict[str, BedrockResponse]:
        """
        Handle timeout by collecting completed responses and creating failed responses for unfinished.

        This method preserves partial results by returning all successfully completed responses
        and creating timeout responses for requests that didn't complete.

        Args:
            responses: Already completed responses
            in_flight_futures: Futures currently being processed
            pending_assignments: Assignments that haven't been started yet

        Returns:
            Complete response dictionary with all request IDs
        """
        self._logger.warning(
            f"Parallel execution timeout - preserving {len(responses)} completed responses"
        )

        # Create timeout responses for in-flight requests
        for future, request_id in in_flight_futures.items():
            if request_id not in responses:
                responses[request_id] = self._create_timeout_response(request_id=request_id)

        # Create timeout responses for pending requests that never started
        for assignment in pending_assignments:
            if assignment.request_id not in responses:
                responses[assignment.request_id] = self._create_timeout_response(
                    request_id=assignment.request_id
                )

        return responses

    def _redistribute_to_new_region(
        self,
        request: BedrockConverseRequest,
        previous_assignment: RegionAssignment,
        available_regions: List[str],
    ) -> RegionAssignment:
        """
        Create new region assignment for a failed request, avoiding previously failed regions.

        Args:
            request: The request that failed
            previous_assignment: Previous assignment that failed
            available_regions: All available regions

        Returns:
            New RegionAssignment with different regions
        """
        # Extract regions that failed from failure history
        exclude_regions = []
        for failure in request.failure_history:
            if failure.region and failure.region not in exclude_regions:
                exclude_regions.append(failure.region)

        # Try to get new regions excluding failed ones
        eligible_regions = [r for r in available_regions if r not in exclude_regions]

        if not eligible_regions:
            # All regions have been tried, use any available region
            self._logger.warning(
                f"All regions have been tried for request {request.request_id}, reusing regions"
            )
            eligible_regions = available_regions

        # Simple round-robin selection from eligible regions
        # Take the first eligible region (can be enhanced with load balancing)
        assigned_region = eligible_regions[0] if eligible_regions else available_regions[0]

        return RegionAssignment(
            request_id=request.request_id or "unknown",
            assigned_regions=[assigned_region],
            priority=previous_assignment.priority,
        )

    def execute_requests_parallel(
        self,
        assignments: List[RegionAssignment],
        request_map: Dict[str, BedrockConverseRequest],
        execute_single_request_func: Callable,
        retry_config: Optional[RetryConfig] = None,
        available_regions: Optional[List[str]] = None,
    ) -> Dict[str, BedrockResponse]:
        """
        Execute multiple requests in parallel using ThreadPoolExecutor with automatic retry.

        Args:
            assignments: List of region assignments for requests
            request_map: Dictionary mapping request_id to BedrockConverseRequest
            execute_single_request_func: Function to execute a single request
            retry_config: Configuration for retry behavior (optional)
            available_regions: List of all available regions for redistribution (optional)

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
                retry_config=retry_config,
                available_regions=available_regions,
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
        retry_config: Optional[RetryConfig] = None,
        available_regions: Optional[List[str]] = None,
    ) -> Dict[str, BedrockResponse]:
        """
        Execute requests using ThreadPoolExecutor with retry queue and exponential backoff.

        This method implements a retry queue pattern that processes requests iteratively.
        Failed requests are automatically retried with exponential backoff if retry is
        enabled and the request hasn't exceeded its retry limit.

        Args:
            assignments: List of region assignments
            request_map: Dictionary of requests
            execute_single_request_func: Function to execute single request
            retry_config: Configuration for retry behavior (optional)
            available_regions: List of all available regions for redistribution (optional)

        Returns:
            Dictionary of responses
        """
        self._logger.info(
            ParallelLogMessages.PARALLEL_EXECUTION_STARTED.format(
                request_count=len(assignments),
                concurrent_limit=self._config.max_concurrent_requests,
            )
        )

        # Initialize retry queue with all initial assignments
        retry_queue = collections.deque(assignments)
        responses: Dict[str, BedrockResponse] = {}

        # Get retry configuration parameters with safe defaults
        if retry_config is None:
            enable_retry = self._config.enable_automatic_retry
            max_retries = (
                self._config.max_retries_per_request
                if self._config.max_retries_per_request is not None
                else 3
            )
            retry_delay = 1.0
            backoff_multiplier = 2.0
        else:
            enable_retry = (
                retry_config.enable_retry if hasattr(retry_config, "enable_retry") else True
            )
            max_retries = (
                retry_config.max_retries
                if hasattr(retry_config, "max_retries") and retry_config.max_retries is not None
                else 3
            )
            retry_delay = (
                retry_config.retry_delay
                if hasattr(retry_config, "retry_delay") and retry_config.retry_delay is not None
                else 1.0
            )
            backoff_multiplier = (
                retry_config.backoff_multiplier
                if hasattr(retry_config, "backoff_multiplier")
                and retry_config.backoff_multiplier is not None
                else 2.0
            )

        # Track assignments currently being processed
        in_flight_assignments: Dict[str, Dict[str, Any]] = {}

        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self._config.max_concurrent_requests, thread_name_prefix="LLMParallel"
        ) as executor:

            # Process retry queue until empty
            while retry_queue or in_flight_assignments:

                # Submit new tasks up to max_concurrent limit
                while (
                    retry_queue
                    and len(in_flight_assignments) < self._config.max_concurrent_requests
                ):
                    assignment = retry_queue.popleft()
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

                    in_flight_assignments[assignment.request_id] = {
                        "future": future,
                        "assignment": assignment,
                        "request": request,
                    }

                # Wait for at least one future to complete
                if in_flight_assignments:
                    # Get all in-flight futures
                    future_to_request_id = {
                        info["future"]: request_id
                        for request_id, info in in_flight_assignments.items()
                    }

                    # Wait for first completion
                    done, _ = concurrent.futures.wait(
                        future_to_request_id.keys(),
                        timeout=self._config.request_timeout_seconds + 10,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )

                    # Process completed futures
                    for future in done:
                        request_id = future_to_request_id[future]
                        info = in_flight_assignments.pop(request_id)
                        assignment = info["assignment"]
                        request = info["request"]

                        try:
                            response = future.result(timeout=1.0)

                            # Check if request failed and can be retried
                            if not response.success and enable_retry:
                                # Determine max_retries (request-specific or global)
                                effective_max_retries = (
                                    request.max_retries
                                    if request.max_retries is not None
                                    else max_retries
                                )

                                if request.can_retry(effective_max_retries):
                                    # Extract error information from response
                                    error_message = (
                                        response.warnings[0]
                                        if response.warnings
                                        else "Unknown error"
                                    )
                                    exception = Exception(error_message)

                                    # Get region from assignment
                                    region = (
                                        assignment.assigned_regions[0]
                                        if assignment.assigned_regions
                                        else None
                                    )

                                    # Record failure in request
                                    request.record_failure(
                                        exception=exception,
                                        model=None,  # Model info not available in response
                                        region=region,
                                    )

                                    # Apply exponential backoff
                                    backoff_delay = retry_delay * (
                                        backoff_multiplier**request.retry_count
                                    )
                                    self._logger.info(
                                        f"Request {request_id} failed (attempt {request.retry_count}), "
                                        f"retrying after {backoff_delay:.2f}s delay"
                                    )
                                    time.sleep(backoff_delay)

                                    # Redistribute to new region if available
                                    if available_regions:
                                        new_assignment = self._redistribute_to_new_region(
                                            request=request,
                                            previous_assignment=assignment,
                                            available_regions=available_regions,
                                        )
                                        self._logger.debug(
                                            f"Redistributed request {request_id} to region: "
                                            f"{new_assignment.assigned_regions}"
                                        )
                                    else:
                                        # Reuse same assignment if no redistribution available
                                        new_assignment = assignment

                                    # Add back to retry queue
                                    retry_queue.append(new_assignment)
                                    continue  # Don't store response yet, will retry
                                else:
                                    self._logger.warning(
                                        f"Request {request_id} exceeded max retries "
                                        f"({effective_max_retries}), marking as failed"
                                    )

                            # Store final response (either successful or max retries exceeded)
                            responses[request_id] = response

                        except concurrent.futures.TimeoutError:
                            self._logger.error(
                                f"Timeout collecting result for request {request_id}"
                            )
                            responses[request_id] = self._create_timeout_response(
                                request_id=request_id
                            )

                        except Exception as e:
                            self._logger.error(
                                f"Error collecting result for request {request_id}: {e}"
                            )
                            responses[request_id] = self._create_error_response(
                                request_id=request_id, error=e
                            )

                    # If no futures completed (shouldn't happen but handle defensively)
                    if not done and in_flight_assignments:
                        self._logger.warning("No futures completed in wait cycle")
                        time.sleep(0.1)  # Small delay to prevent busy loop

        # Ensure all requests have responses
        for assignment in assignments:
            if assignment.request_id not in responses:
                self._logger.warning(
                    f"Missing response for request {assignment.request_id}, creating error response"
                )
                responses[assignment.request_id] = BedrockResponse(
                    success=False, warnings=["Request execution did not complete"]
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
