"""
Parallel execution engine for LLM Manager system.
Handles asynchronous execution of requests across multiple regions with concurrency control.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, cast

from ..exceptions.parallel_exceptions import ParallelExecutionError
from ..models.bedrock_response import BedrockResponse
from ..models.parallel_constants import ParallelErrorMessages, ParallelLogMessages
from ..models.parallel_structures import (
    BedrockConverseRequest,
    ParallelExecutionContext,
    ParallelProcessingConfig,
    RegionAssignment,
)


class ParallelExecutor:
    """
    Executes BedrockConverse requests in parallel across multiple regions.

    Provides functionality for:
    - Asynchronous execution with concurrency control
    - Request timeout handling
    - Context tracking and monitoring
    - Integration with existing LLMManager retry logic
    """

    def __init__(self, config: ParallelProcessingConfig) -> None:
        """
        Initialize the parallel executor.

        Args:
            config: Configuration for parallel processing behavior
        """
        self._logger = logging.getLogger(__name__)
        self._config = config

        # Execution context for tracking
        self._execution_context: Optional[ParallelExecutionContext] = None

    async def execute_requests_parallel(
        self,
        assignments: List[RegionAssignment],
        request_map: Dict[str, BedrockConverseRequest],
        execute_single_request_func: Callable[..., Any],
    ) -> Dict[str, BedrockResponse]:
        """
        Execute multiple requests in parallel according to their region assignments.

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
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(self._config.max_concurrent_requests)
            self._execution_context.semaphore = semaphore

            # Create tasks for all request executions
            tasks = self._create_execution_tasks(
                assignments=assignments,
                request_map=request_map,
                execute_single_request_func=execute_single_request_func,
                semaphore=semaphore,
            )

            self._logger.info(
                ParallelLogMessages.PARALLEL_EXECUTION_STARTED.format(
                    request_count=len(assignments),
                    concurrent_limit=self._config.max_concurrent_requests,
                )
            )

            # Execute tasks and collect results
            results = await self._execute_tasks_with_monitoring(tasks=tasks)

            # Process results and handle failures
            responses = self._process_execution_results(results=results, assignments=assignments)

            self._log_execution_completion(responses=responses)

            return responses

        except Exception as e:
            self._logger.error(f"Parallel execution failed: {e}")
            raise ParallelExecutionError(
                message=f"Parallel execution failed: {str(e)}",
                failed_requests=list(request_map.keys()),
                total_requests=len(request_map),
            ) from e
        finally:
            self._execution_context = None

    def _create_execution_context(
        self, assignments: List[RegionAssignment]
    ) -> ParallelExecutionContext:
        """
        Create execution context for tracking parallel execution.

        Args:
            assignments: List of region assignments

        Returns:
            ParallelExecutionContext for tracking
        """
        context = ParallelExecutionContext(start_time=datetime.now())

        # Initialize region load tracking
        for assignment in assignments:
            for region in assignment.assigned_regions:
                if region not in context.region_load:
                    context.region_load[region] = 0
                context.region_load[region] += 1

        return context

    def _create_execution_tasks(
        self,
        assignments: List[RegionAssignment],
        request_map: Dict[str, BedrockConverseRequest],
        execute_single_request_func: Callable[..., Any],
        semaphore: asyncio.Semaphore,
    ) -> List[asyncio.Task]:
        """
        Create async tasks for all request executions.

        Args:
            assignments: List of region assignments
            request_map: Dictionary of requests
            execute_single_request_func: Function to execute single request
            semaphore: Semaphore for concurrency control

        Returns:
            List of async tasks
        """
        tasks = []

        for assignment in assignments:
            request = request_map.get(assignment.request_id)
            if request is None:
                self._logger.warning(f"Request not found for ID: {assignment.request_id}")
                continue

            # Create task for this request
            task = asyncio.create_task(
                self._execute_single_request_with_context(
                    request=request,
                    assignment=assignment,
                    execute_single_request_func=execute_single_request_func,
                    semaphore=semaphore,
                ),
                name=f"request_{assignment.request_id}",
            )
            tasks.append(task)

        return tasks

    async def _execute_single_request_with_context(
        self,
        request: BedrockConverseRequest,
        assignment: RegionAssignment,
        execute_single_request_func: Callable[..., Any],
        semaphore: asyncio.Semaphore,
    ) -> Tuple[str, BedrockResponse]:
        """
        Execute a single request with context tracking and timeout.

        Args:
            request: BedrockConverseRequest to execute
            assignment: Region assignment for the request
            execute_single_request_func: Function to execute the request
            semaphore: Semaphore for concurrency control

        Returns:
            Tuple of (request_id, BedrockResponse)

        Raises:
            RequestTimeoutError: If request times out
        """
        request_id = assignment.request_id

        async with semaphore:
            # Update context
            if self._execution_context:
                self._execution_context.active_requests.add(request_id)

            try:
                self._logger.debug(f"Starting execution for request {request_id}")

                # Execute with timeout
                response = await asyncio.wait_for(
                    self._execute_request_async(
                        request=request,
                        assignment=assignment,
                        execute_single_request_func=execute_single_request_func,
                    ),
                    timeout=self._config.request_timeout_seconds,
                )

                # Update context on success
                if self._execution_context:
                    self._execution_context.active_requests.discard(request_id)
                    self._execution_context.completed_requests.add(request_id)

                self._logger.debug(f"Completed execution for request {request_id}")
                return request_id, response

            except asyncio.TimeoutError:
                # Handle request timeout
                if self._execution_context:
                    self._execution_context.active_requests.discard(request_id)
                    self._execution_context.failed_requests.add(request_id)

                # Log timeout error with details
                self._logger.warning(
                    ParallelErrorMessages.REQUEST_TIMEOUT_EXCEEDED.format(
                        request_id=request_id, timeout_seconds=self._config.request_timeout_seconds
                    )
                )

                # Create failed response
                failed_response = BedrockResponse(
                    success=False,
                    warnings=[
                        f"Request timed out after {self._config.request_timeout_seconds} seconds"
                    ],
                )

                return request_id, failed_response

            except Exception as e:
                # Handle general execution errors
                if self._execution_context:
                    self._execution_context.active_requests.discard(request_id)
                    self._execution_context.failed_requests.add(request_id)

                self._logger.error(f"Request {request_id} failed with error: {e}")

                # Create failed response
                failed_response = BedrockResponse(
                    success=False, warnings=[f"Request failed: {str(e)}"]
                )

                return request_id, failed_response

    async def _execute_request_async(
        self,
        request: BedrockConverseRequest,
        assignment: RegionAssignment,
        execute_single_request_func: Callable[..., Any],
    ) -> BedrockResponse:
        """
        Execute a single request asynchronously.

        Args:
            request: BedrockConverseRequest to execute
            assignment: Region assignment for the request
            execute_single_request_func: Function to execute the request

        Returns:
            BedrockResponse from the execution
        """
        # Convert the synchronous execution function to async
        # This is a wrapper around the existing LLMManager.converse() method
        loop = asyncio.get_running_loop()

        # Convert request to converse arguments
        converse_args = request.to_converse_args()

        # Execute in thread pool to avoid blocking the event loop
        response = await loop.run_in_executor(
            None, execute_single_request_func, converse_args  # Use default thread pool executor
        )

        return cast(BedrockResponse, response)

    async def _execute_tasks_with_monitoring(
        self, tasks: List[asyncio.Task]
    ) -> List[Tuple[str, BedrockResponse]]:
        """
        Execute tasks with progress monitoring.

        Args:
            tasks: List of async tasks to execute

        Returns:
            List of (request_id, BedrockResponse) tuples
        """
        # Execute all tasks concurrently
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for i, result in enumerate(completed_tasks):
            if isinstance(result, Exception):
                # Handle task that raised an exception
                task_name = tasks[i].get_name()
                request_id = (
                    task_name.replace("request_", "")
                    if task_name.startswith("request_")
                    else f"task_{i}"
                )

                self._logger.error(f"Task for request {request_id} raised exception: {result}")

                # Create failed response
                failed_response = BedrockResponse(
                    success=False, warnings=[f"Task execution failed: {str(result)}"]
                )
                results.append((request_id, failed_response))
            else:
                # Normal result
                results.append(cast(Tuple[str, BedrockResponse], result))

        return results

    def _process_execution_results(
        self, results: List[Tuple[str, BedrockResponse]], assignments: List[RegionAssignment]
    ) -> Dict[str, BedrockResponse]:
        """
        Process execution results and create response dictionary.

        Args:
            results: List of (request_id, BedrockResponse) tuples
            assignments: Original region assignments

        Returns:
            Dictionary mapping request_id to BedrockResponse
        """
        responses = {}

        for request_id, response in results:
            responses[request_id] = response

        # Check for missing responses
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
                f"Parallel execution completed: {successful_count}/{total_count} successful"
            )

    def get_execution_context(self) -> Optional[ParallelExecutionContext]:
        """
        Get current execution context.

        Returns:
            Current ParallelExecutionContext, None if not executing
        """
        return self._execution_context

    def get_config(self) -> ParallelProcessingConfig:
        """
        Get current parallel processing configuration.

        Returns:
            ParallelProcessingConfig being used
        """
        return self._config
