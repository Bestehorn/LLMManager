"""
Streaming Display Utilities for LLM Manager.

Provides utilities for displaying streaming responses with rich formatting,
metadata, and performance metrics in a consistent and user-friendly manner.
"""

import logging
from typing import Any, List, Optional

from ..bedrock.models.bedrock_response import StreamingResponse


class StreamingDisplayFormatter:
    """
    Formatter for displaying streaming responses with rich metadata and formatting.

    This class provides methods to display streaming responses in a consistent,
    user-friendly format with detailed metadata, timing information, and
    comprehensive error handling.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the streaming display formatter.

        Args:
            logger: Optional logger instance for internal logging
        """
        self._logger = logger or logging.getLogger(__name__)

    def display_streaming_response(
        self,
        streaming_response: StreamingResponse,
        title: str = "Streaming Response",
        show_content: bool = True,
        show_metadata: bool = True,
        show_timing: bool = True,
        show_usage: bool = True,
        show_errors: bool = True,
        content_preview_length: Optional[int] = 500,
    ) -> None:
        """
        Display a comprehensive streaming response with formatting.

        Args:
            streaming_response: StreamingResponse object to display
            title: Title for the display section
            show_content: Whether to show response content
            show_metadata: Whether to show response metadata
            show_timing: Whether to show timing information
            show_usage: Whether to show token usage
            show_errors: Whether to show errors and warnings
            content_preview_length: Maximum characters to show in content preview (None for full content)
        """
        self._print_section_header(title=title)

        if streaming_response.success:
            self._display_success_response(
                streaming_response=streaming_response,
                show_content=show_content,
                show_metadata=show_metadata,
                show_timing=show_timing,
                show_usage=show_usage,
                content_preview_length=content_preview_length,
            )
        else:
            self._display_failed_response(
                streaming_response=streaming_response, show_errors=show_errors
            )

        if show_errors and streaming_response.warnings:
            self._display_warnings(warnings=streaming_response.warnings)

    def display_streaming_summary(
        self, streaming_response: StreamingResponse, title: str = "Streaming Summary"
    ) -> None:
        """
        Display a concise summary of streaming response.

        Args:
            streaming_response: StreamingResponse object to summarize
            title: Title for the summary section
        """
        self._print_section_header(title=title)

        # Basic status
        status_icon = "✅" if streaming_response.success else "❌"
        print(f"{status_icon} Success: {streaming_response.success}")

        # Core information
        if streaming_response.model_used:
            print(f"🤖 Model: {streaming_response.model_used}")
        if streaming_response.region_used:
            print(f"🌍 Region: {streaming_response.region_used}")

        # Content summary
        content_length = len(streaming_response.get_full_content())
        print(
            f"📝 Content: {content_length} characters, {len(streaming_response.content_parts)} parts"
        )

        # Duration
        if streaming_response.total_duration_ms:
            print(f"⏱️ Duration: {streaming_response.total_duration_ms:.1f}ms")

    def display_recovery_information(
        self, streaming_response: StreamingResponse, title: str = "Recovery Information"
    ) -> None:
        """
        Display streaming recovery information if available.

        Args:
            streaming_response: StreamingResponse object with recovery info
            title: Title for the recovery information section
        """
        recovery_info = streaming_response.get_recovery_info()

        if not recovery_info.get("recovery_enabled", False):
            return

        self._print_section_header(title=title)

        total_exceptions = recovery_info.get("total_exceptions", 0)
        recovered_exceptions = recovery_info.get("recovered_exceptions", 0)
        target_switches = recovery_info.get("target_switches", 0)

        print(f"   Total exceptions: {total_exceptions}")
        print(f"   Recovered exceptions: {recovered_exceptions}")
        print(f"   Target switches: {target_switches}")

        # Show individual exceptions
        mid_stream_exceptions = streaming_response.get_mid_stream_exceptions()
        if mid_stream_exceptions:
            print("   Mid-stream exceptions handled:")
            for i, exc in enumerate(mid_stream_exceptions, 1):
                status = "✅ recovered" if exc["recovered"] else "❌ failed"
                print(
                    f"     {i}. {exc['error_type']} at position {exc['position']} "
                    f"({exc['model']}, {exc['region']}) - {status}"
                )

        # Show final target if switched
        final_model = recovery_info.get("final_model")
        final_region = recovery_info.get("final_region")
        if final_model and final_region:
            print(f"   🔄 Final target: {final_model} in {final_region}")

    def _display_success_response(
        self,
        streaming_response: StreamingResponse,
        show_content: bool,
        show_metadata: bool,
        show_timing: bool,
        show_usage: bool,
        content_preview_length: Optional[int],
    ) -> None:
        """Display successful streaming response details."""
        print(f"✅ Success: {streaming_response.success}")

        if show_metadata:
            self._display_response_metadata(streaming_response=streaming_response)

        if show_timing:
            self._display_timing_information(streaming_response=streaming_response)

        if show_content:
            self._display_response_content(
                streaming_response=streaming_response, content_preview_length=content_preview_length
            )

        if show_usage:
            self._display_token_usage(streaming_response=streaming_response)

    def _display_failed_response(
        self, streaming_response: StreamingResponse, show_errors: bool
    ) -> None:
        """Display failed streaming response details."""
        print(f"❌ Success: {streaming_response.success}")

        if show_errors and streaming_response.stream_errors:
            print(f"🔄 Stream Errors: {len(streaming_response.stream_errors)}")
            for i, error in enumerate(streaming_response.stream_errors, 1):
                print(f"   {i}. {type(error).__name__}: {str(error)}")

        # Show partial content if any was received
        partial_content = streaming_response.get_full_content()
        if partial_content:
            print(f"📝 Partial content received: {len(partial_content)} characters")
            print(f"📦 Content parts: {len(streaming_response.content_parts)}")

    def _display_response_metadata(self, streaming_response: StreamingResponse) -> None:
        """Display response metadata information."""
        if streaming_response.model_used:
            print(f"🤖 Model: {streaming_response.model_used}")
        else:
            print("🤖 Model: None")

        if streaming_response.region_used:
            print(f"🌍 Region: {streaming_response.region_used}")
        else:
            print("🌍 Region: None")

        if streaming_response.access_method_used:
            print(f"🔗 Access Method: {streaming_response.access_method_used}")
        else:
            print("🔗 Access Method: None")

        # Streaming-specific metadata
        print("\n🌊 Streaming Details:")
        print(f"   📦 Content Parts: {len(streaming_response.content_parts)}")
        print(f"   📏 Stream Position: {streaming_response.stream_position}")
        print(f"   🛑 Stop Reason: {streaming_response.stop_reason or 'N/A'}")
        print(f"   🎭 Message Role: {streaming_response.current_message_role or 'N/A'}")

    def _display_timing_information(self, streaming_response: StreamingResponse) -> None:
        """Display timing and performance information."""
        metrics = streaming_response.get_metrics()
        if not metrics:
            return

        print("\n⏱️ Performance Metrics:")

        if streaming_response.total_duration_ms:
            print(f"   Total Duration: {streaming_response.total_duration_ms:.2f}ms")

        if streaming_response.api_latency_ms:
            print(f"   API Latency: {streaming_response.api_latency_ms:.2f}ms")

        # Streaming-specific timing
        if "time_to_first_token_ms" in metrics:
            print(f"   Time to First Token: {metrics['time_to_first_token_ms']:.2f}ms")

        if "time_to_last_token_ms" in metrics:
            print(f"   Time to Last Token: {metrics['time_to_last_token_ms']:.2f}ms")

        if "token_generation_duration_ms" in metrics:
            print(f"   Token Generation Duration: {metrics['token_generation_duration_ms']:.2f}ms")

    def _display_response_content(
        self, streaming_response: StreamingResponse, content_preview_length: Optional[int]
    ) -> None:
        """Display response content with optional preview length."""
        full_content = streaming_response.get_full_content()
        if not full_content:
            return

        content_length = len(full_content)
        print(f"\n💬 Streamed Content ({content_length} characters):")
        print("-" * 20)

        if content_preview_length and content_length > content_preview_length:
            preview_content = full_content[:content_preview_length]
            print(f"{preview_content}...")
            print(
                f"\n[Content truncated - showing first {content_preview_length} of {content_length} characters]"
            )
        else:
            print(full_content)

    def _display_token_usage(self, streaming_response: StreamingResponse) -> None:
        """Display token usage information."""
        usage = streaming_response.get_usage()
        if not usage:
            return

        print("\n📊 Token Usage:")

        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        print(f"   Input tokens: {input_tokens}")
        print(f"   Output tokens: {output_tokens}")
        print(f"   Total tokens: {total_tokens}")

        # Cache information if available
        cache_read = usage.get("cache_read_tokens", 0)
        cache_write = usage.get("cache_write_tokens", 0)

        if cache_read > 0 or cache_write > 0:
            print(f"   Cache read tokens: {cache_read}")
            print(f"   Cache write tokens: {cache_write}")

    def _display_warnings(self, warnings: List[str]) -> None:
        """Display warning messages."""
        print("\n⚠️ Warnings:")
        for warning in warnings:
            print(f"   - {warning}")

    def _print_section_header(self, title: str) -> None:
        """Print a formatted section header."""
        print(f"\n{title}")
        print("=" * len(title))


# Convenience functions for direct usage
def display_streaming_response(
    streaming_response: StreamingResponse, title: str = "Streaming Response", **kwargs: Any
) -> None:
    """
    Convenience function to display a streaming response.

    Args:
        streaming_response: StreamingResponse object to display
        title: Title for the display section
        **kwargs: Additional arguments passed to StreamingDisplayFormatter.display_streaming_response()
    """
    formatter = StreamingDisplayFormatter()
    formatter.display_streaming_response(
        streaming_response=streaming_response, title=title, **kwargs
    )


def display_streaming_summary(
    streaming_response: StreamingResponse, title: str = "Streaming Summary"
) -> None:
    """
    Convenience function to display a streaming response summary.

    Args:
        streaming_response: StreamingResponse object to summarize
        title: Title for the summary section
    """
    formatter = StreamingDisplayFormatter()
    formatter.display_streaming_summary(streaming_response=streaming_response, title=title)


def display_recovery_information(
    streaming_response: StreamingResponse, title: str = "Recovery Information"
) -> None:
    """
    Convenience function to display streaming recovery information.

    Args:
        streaming_response: StreamingResponse object with recovery info
        title: Title for the recovery information section
    """
    formatter = StreamingDisplayFormatter()
    formatter.display_recovery_information(streaming_response=streaming_response, title=title)
