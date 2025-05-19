"""
BedrockResponse class for handling responses from AWS Bedrock Converse API.
"""
from typing import Any, Dict, List, Optional, Union
import time
from src.ConverseFieldConstants import Fields, Roles, StopReasons

class BedrockResponse:
    """
    Class to handle responses from AWS Bedrock Converse API and provide convenient access to the response data.
    
    This class encapsulates the response from the Converse API and provides methods to access different parts
    of the response data including execution metrics, exceptions encountered, and the actual response content.
    """
    
    def __init__(self, 
                 response: Optional[Dict[str, Any]] = None, 
                 exceptions: Optional[List[Exception]] = None,
                 model_id: str = "", 
                 region: str = "",
                 prompts: Optional[List[Dict[str, Any]]] = None,
                 execution_time: float = 0.0,
                 is_cris: bool = False):
        """
        Initialize a BedrockResponse object.
        
        Args:
            response: The raw response from the Converse API
            exceptions: List of exceptions that occurred during the request
            model_id: The model ID used for the request
            region: The AWS region where the request was executed
            prompts: The prompt(s) used in the request
            execution_time: The time (in seconds) it took to execute the request
            is_cris: Whether the response came from a CRIS (Cross Region Inference) endpoint
        """
        self._response = response or {}
        self._exceptions = exceptions or []
        self._model_id = model_id
        self._region = region
        self._prompts = prompts or []
        self._execution_time = execution_time
        self._is_cris = is_cris
        
    @property
    def raw_response(self) -> Dict[str, Any]:
        """Get the raw response from the Converse API."""
        return self._response
    
    @property
    def successful(self) -> bool:
        """Check if the request was successful (no exceptions)."""
        return len(self._exceptions) == 0
    
    @property
    def exception_count(self) -> int:
        """Get the number of exceptions that occurred during the request."""
        return len(self._exceptions)
    
    @property
    def exceptions(self) -> List[Exception]:
        """Get the list of exceptions that occurred during the request."""
        return self._exceptions
    
    @property
    def execution_time(self) -> float:
        """Get the time it took to execute the request (in seconds)."""
        return self._execution_time
    
    @property
    def model_id(self) -> str:
        """Get the model ID used for the request."""
        return self._model_id
    
    @property
    def region(self) -> str:
        """Get the AWS region where the request was executed."""
        return self._region
    
    @property
    def is_cris(self) -> bool:
        """Check if the response came from a CRIS (Cross Region Inference) endpoint."""
        return self._is_cris
    
    @property
    def prompts(self) -> List[Dict[str, Any]]:
        """Get the prompt(s) used in the request."""
        return self._prompts
    
    def get_content_text(self) -> str:
        """
        Extract the text content from the response.
        
        Returns:
            The text content from the response, or an empty string if not found.
        """
        try:
            # Navigate through the response structure to get the text content
            if Fields.OUTPUT in self._response and Fields.MESSAGE in self._response[Fields.OUTPUT]:
                message = self._response[Fields.OUTPUT][Fields.MESSAGE]
                if Fields.CONTENT in message:
                    for content_block in message[Fields.CONTENT]:
                        if Fields.TEXT in content_block:
                            return content_block[Fields.TEXT]
        except Exception:
            pass
        return ""
    
    def get_stop_reason(self) -> str:
        """Get the reason why the model stopped generating content."""
        return self._response.get(Fields.STOP_REASON, "")
    
    def get_usage(self) -> Dict[str, int]:
        """
        Get the token usage information from the response.
        
        Returns:
            A dictionary with token usage information, including input tokens,
            output tokens, total tokens, and cached tokens.
        """
        if Fields.USAGE in self._response:
            return self._response[Fields.USAGE]
        return {}
    
    def get_input_tokens(self) -> int:
        """Get the number of input tokens used."""
        usage = self.get_usage()
        return usage.get(Fields.INPUT_TOKENS, 0)
    
    def get_output_tokens(self) -> int:
        """Get the number of output tokens generated."""
        usage = self.get_usage()
        return usage.get(Fields.OUTPUT_TOKENS, 0)
    
    def get_total_tokens(self) -> int:
        """Get the total number of tokens used (input + output)."""
        usage = self.get_usage()
        return usage.get(Fields.TOTAL_TOKENS, 0)
    
    def get_cached_read_tokens(self) -> int:
        """Get the number of tokens read from cache."""
        usage = self.get_usage()
        return usage.get(Fields.CACHE_READ_INPUT_TOKENS, 0)
    
    def get_cached_write_tokens(self) -> int:
        """Get the number of tokens written to cache."""
        usage = self.get_usage()
        return usage.get(Fields.CACHE_WRITE_INPUT_TOKENS, 0)
    
    def get_latency_ms(self) -> int:
        """Get the latency of the request in milliseconds."""
        if Fields.METRICS in self._response:
            return self._response[Fields.METRICS].get(Fields.LATENCY_MS, 0)
        return 0
    
    def get_additional_model_response_fields(self) -> Dict[str, Any]:
        """Get any additional model-specific response fields."""
        return self._response.get(Fields.ADDITIONAL_MODEL_RESPONSE_FIELDS, {})
    
    def get_trace(self) -> Dict[str, Any]:
        """Get trace information, including guardrail behavior."""
        return self._response.get(Fields.TRACE_FIELD, {})
    
    def get_guardrail_trace(self) -> Dict[str, Any]:
        """Get guardrail trace information."""
        trace = self.get_trace()
        return trace.get(Fields.GUARDRAIL, {})
    
    def get_invoked_model_id(self) -> str:
        """Get the model ID that was actually invoked (useful for prompt router responses)."""
        trace = self.get_trace()
        if Fields.PROMPT_ROUTER in trace:
            return trace[Fields.PROMPT_ROUTER].get(Fields.INVOKED_MODEL_ID, "")
        return ""
    
    def get_response_message(self) -> Dict[str, Any]:
        """Get the full response message."""
        if Fields.OUTPUT in self._response and Fields.MESSAGE in self._response[Fields.OUTPUT]:
            return self._response[Fields.OUTPUT][Fields.MESSAGE]
        return {}
    
    def get_response_content(self) -> List[Dict[str, Any]]:
        """Get the content blocks from the response message."""
        message = self.get_response_message()
        return message.get(Fields.CONTENT, [])
    
    def get_text_contents(self) -> List[str]:
        """
        Get all text content blocks from the response.
        
        Returns:
            A list of text strings from all text content blocks.
        """
        result = []
        for content_block in self.get_response_content():
            if Fields.TEXT in content_block:
                result.append(content_block[Fields.TEXT])
        return result
    
    def get_image_contents(self) -> List[Dict[str, Any]]:
        """
        Get all image content blocks from the response.
        
        Returns:
            A list of image content blocks.
        """
        result = []
        for content_block in self.get_response_content():
            if Fields.IMAGE in content_block:
                result.append(content_block[Fields.IMAGE])
        return result
    
    def get_tool_use_contents(self) -> List[Dict[str, Any]]:
        """
        Get all tool use content blocks from the response.
        
        Returns:
            A list of tool use content blocks.
        """
        result = []
        for content_block in self.get_response_content():
            if Fields.TOOL_USE in content_block:
                result.append(content_block[Fields.TOOL_USE])
        return result
    
    def __str__(self) -> str:
        """Get a string representation of the response."""
        return (
            f"BedrockResponse(model_id='{self._model_id}', region='{self._region}', "
            f"is_cris={self._is_cris}, successful={self.successful}, "
            f"exception_count={self.exception_count}, execution_time={self._execution_time:.3f}s)"
        )
    
    def __repr__(self) -> str:
        """Get a detailed string representation of the response."""
        return (
            f"BedrockResponse(\n"
            f"  model_id='{self._model_id}',\n"
            f"  region='{self._region}',\n"
            f"  is_cris={self._is_cris},\n"
            f"  successful={self.successful},\n"
            f"  exception_count={self.exception_count},\n"
            f"  execution_time={self._execution_time:.3f}s,\n"
            f"  input_tokens={self.get_input_tokens()},\n"
            f"  output_tokens={self.get_output_tokens()},\n"
            f"  total_tokens={self.get_total_tokens()},\n"
            f"  stop_reason='{self.get_stop_reason()}'\n"
            f")"
        )
