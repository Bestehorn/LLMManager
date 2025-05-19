"""
Constants used in the Bedrock Converse API LLMManager.
"""
from typing import Dict, List, Set

# Field names in JSON responses and requests
class Fields:
    # Common fields
    ROLE = "role"
    CONTENT = "content"
    TEXT = "text"
    IMAGE = "image"
    FORMAT = "format"
    SOURCE = "source"
    BYTES = "bytes"
    S3_LOCATION = "s3Location"
    URI = "uri"
    BUCKET_OWNER = "bucketOwner"
    DOCUMENT = "document"
    NAME = "name"
    VIDEO = "video"
    TOOL_USE = "toolUse"
    TOOL_RESULT = "toolResult"
    TOOL_USE_ID = "toolUseId"
    INPUT = "input"
    STATUS = "status"
    GUARD_CONTENT = "guardContent"
    QUALIFIERS = "qualifiers"
    CACHE_POINT = "cachePoint"
    TYPE = "type"
    REASONING_CONTENT = "reasoningContent"
    REASONING_TEXT = "reasoningText"
    SIGNATURE = "signature"
    REDACTED_CONTENT = "redactedContent"
    
    # Request fields
    MESSAGES = "messages"
    MODEL_ID = "modelId"
    SYSTEM = "system"
    INFERENCE_CONFIG = "inferenceConfig"
    MAX_TOKENS = "maxTokens"
    TEMPERATURE = "temperature"
    TOP_P = "topP"
    STOP_SEQUENCES = "stopSequences"
    TOOL_CONFIG = "toolConfig"
    TOOLS = "tools"
    TOOL_SPEC = "toolSpec"
    DESCRIPTION = "description"
    INPUT_SCHEMA = "inputSchema"
    JSON = "json"
    TOOL_CHOICE = "toolChoice"
    AUTO = "auto"
    ANY = "any"
    TOOL = "tool"
    GUARDRAIL_CONFIG = "guardrailConfig"
    GUARDRAIL_IDENTIFIER = "guardrailIdentifier"
    GUARDRAIL_VERSION = "guardrailVersion"
    TRACE = "trace"
    ADDITIONAL_MODEL_REQUEST_FIELDS = "additionalModelRequestFields"
    PROMPT_VARIABLES = "promptVariables"
    ADDITIONAL_MODEL_RESPONSE_FIELD_PATHS = "additionalModelResponseFieldPaths"
    REQUEST_METADATA = "requestMetadata"
    PERFORMANCE_CONFIG = "performanceConfig"
    LATENCY = "latency"
    
    # Response fields
    OUTPUT = "output"
    MESSAGE = "message"
    STOP_REASON = "stopReason"
    USAGE = "usage"
    INPUT_TOKENS = "inputTokens"
    OUTPUT_TOKENS = "outputTokens"
    TOTAL_TOKENS = "totalTokens"
    CACHE_READ_INPUT_TOKENS = "cacheReadInputTokens"
    CACHE_WRITE_INPUT_TOKENS = "cacheWriteInputTokens"
    METRICS = "metrics"
    LATENCY_MS = "latencyMs"
    ADDITIONAL_MODEL_RESPONSE_FIELDS = "additionalModelResponseFields"
    TRACE_FIELD = "trace"
    GUARDRAIL = "guardrail"
    MODEL_OUTPUT = "modelOutput"
    INPUT_ASSESSMENT = "inputAssessment"
    OUTPUT_ASSESSMENTS = "outputAssessments"
    ACTION_REASON = "actionReason"
    PROMPT_ROUTER = "promptRouter"
    INVOKED_MODEL_ID = "invokedModelId"

# Role types
class Roles:
    USER = "user"
    ASSISTANT = "assistant"

# Stop reasons
class StopReasons:
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    GUARDRAIL_INTERVENED = "guardrail_intervened"
    CONTENT_FILTERED = "content_filtered"

# Performance config values
class PerformanceConfig:
    STANDARD = "standard"
    OPTIMIZED = "optimized"

# Guardrail trace values
class GuardrailTrace:
    ENABLED = "enabled"
    DISABLED = "disabled"
    ENABLED_FULL = "enabled_full"
