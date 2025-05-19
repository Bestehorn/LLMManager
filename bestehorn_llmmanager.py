import boto3
import logging
import threading
import time
import uuid
from typing import Dict, List, Set, Tuple, Union, Optional, Any, Callable, TypeVar, cast
from concurrent.futures import ThreadPoolExecutor
import json
import re
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('LLMManager')

# Type definitions for better type checking
BedrockClient = TypeVar('BedrockClient')
ResponseDict = Dict[str, Any]


class BedrockConverseResponse:
    """
    Encapsulates the response from AWS Bedrock converse API for easier access to data.
    """
    def __init__(self, response_data: Dict[str, Any]):
        self._raw_response = response_data
        self._metadata = response_data.get('metadata', {})
        self._output = response_data.get('output', {})
        self._usage = response_data.get('usage', {})
        self._stop_reason = self._output.get('stopReason', '')
        
    @property
    def raw(self) -> Dict[str, Any]:
        """Get the raw response dictionary"""
        return self._raw_response
    
    @property
    def text(self) -> str:
        """Get the generated text response"""
        try:
            message = self._output.get('message', {})
            content = message.get('content', [])
            for item in content:
                if item.get('type') == 'text' or 'text' in item:
                    return item.get('text', '')
            return ''
        except (AttributeError, KeyError, TypeError):
            return ''
    
    @property
    def model_used(self) -> str:
        """Get the model ID used for this response"""
        return self._metadata.get('model_used', '')
    
    @property
    def region_used(self) -> str:
        """Get the AWS region used for this response"""
        return self._metadata.get('region_used', '')
    
    @property
    def execution_time_ms(self) -> float:
        """Get the execution time in milliseconds"""
        return self._metadata.get('execution_time_ms', 0.0)
    
    @property
    def fallbacks_used(self) -> int:
        """Get the number of fallbacks used"""
        return self._metadata.get('fallbacks_used', 0)
    
    @property
    def region_switches(self) -> int:
        """Get the number of region switches used"""
        return self._metadata.get('region_switches', 0)
    
    @property
    def request_id(self) -> str:
        """Get the request ID"""
        return self._metadata.get('request_id', '')
    
    @property
    def stop_reason(self) -> str:
        """Get the stop reason"""
        return self._stop_reason
    
    @property
    def input_tokens(self) -> int:
        """Get the number of input tokens used"""
        return self._usage.get('inputTokens', 0)
    
    @property
    def output_tokens(self) -> int:
        """Get the number of output tokens used"""
        return self._usage.get('outputTokens', 0)
    
    @property
    def total_tokens(self) -> int:
        """Get the total number of tokens used"""
        return self.input_tokens + self.output_tokens
    
    def get_message_content(self) -> List[Dict[str, Any]]:
        """Get the full message content list"""
        message = self._output.get('message', {})
        return message.get('content', [])
    
    def get_tool_calls(self) -> List[Dict[str, Any]]:
        """Get any tool calls in the response"""
        content = self.get_message_content()
        tool_calls = []
        for item in content:
            if item.get('type') == 'tool_call' or 'tool_call' in item:
                tool_calls.append(item.get('tool_call', {}))
        return tool_calls
    
    def get_images(self) -> List[Dict[str, Any]]:
        """Get any images in the response"""
        content = self.get_message_content()
        images = []
        for item in content:
            if item.get('type') == 'image' or 'image' in item:
                images.append(item.get('image', {}))
        return images
    
    def __str__(self) -> str:
        """Return the text content of the response"""
        return self.text
    
    def __repr__(self) -> str:
        """Return a representation of the response"""
        return f"BedrockConverseResponse(model={self.model_used}, region={self.region_used}, text={self.text[:50]}...)"


class RegionManager:
    """
    Manages AWS regions, their availability, and mapping to CRIS zones.
    """
    # Map AWS regions to CRIS zones
    REGION_TO_CRIS_ZONE = {
        # US regions
        'us-east-1': 'us',
        'us-east-2': 'us',
        'us-west-2': 'us',
        'us-gov-east-1': 'us-gov',
        'us-gov-west-1': 'us-gov',
        # Europe regions
        'eu-central-1': 'eu',
        'eu-central-2': 'eu',
        'eu-west-1': 'eu',
        'eu-west-2': 'eu',
        'eu-west-3': 'eu',
        'eu-north-1': 'eu',
        # Asia Pacific regions
        'ap-northeast-1': 'apac',
        'ap-northeast-2': 'apac',
        'ap-northeast-3': 'apac',
        'ap-south-1': 'apac',
        'ap-south-2': 'apac',
        'ap-southeast-1': 'apac',
        'ap-southeast-2': 'apac',
        # Other regions
        'ca-central-1': 'us',  # Canada is typically mapped to US zone
        'sa-east-1': 'us',     # South America is typically mapped to US zone
    }
    
    # Common Bedrock regions
    US_REGIONS = ['us-east-1', 'us-east-2', 'us-west-2']
    EU_REGIONS = ['eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1']
    APAC_REGIONS = ['ap-northeast-1', 'ap-northeast-2', 'ap-south-1', 'ap-southeast-1', 'ap-southeast-2']
    GOV_REGIONS = ['us-gov-east-1', 'us-gov-west-1']
    
    def __init__(self):
        self.region_status: Dict[str, bool] = {}  # Tracks region availability
        self.region_last_check: Dict[str, float] = {}  # Tracks when a region was last checked
        self.lock = threading.Lock()  # Thread safety for region status updates
        
    def get_zone_for_region(self, region: str) -> str:
        """Return the CRIS zone for a given AWS region."""
        return self.REGION_TO_CRIS_ZONE.get(region, 'us')  # Default to US zone if unknown
    
    def get_regions_for_zone(self, zone: str) -> List[str]:
        """Return all regions for a given CRIS zone."""
        return [region for region, mapped_zone in self.REGION_TO_CRIS_ZONE.items() 
                if mapped_zone == zone]
    
    def mark_region_available(self, region: str) -> None:
        """Mark a region as available."""
        with self.lock:
            self.region_status[region] = True
            self.region_last_check[region] = time.time()
    
    def mark_region_unavailable(self, region: str) -> None:
        """Mark a region as unavailable."""
        with self.lock:
            self.region_status[region] = False
            self.region_last_check[region] = time.time()
    
    def is_region_available(self, region: str) -> Optional[bool]:
        """Check if a region is available."""
        with self.lock:
            if region in self.region_status:
                # If check is older than 5 minutes, return None (unknown)
                if time.time() - self.region_last_check.get(region, 0) > 300:
                    return None
                return self.region_status[region]
            return None  # Status unknown if never checked
    
    def get_available_regions(self) -> List[str]:
        """Get list of known available regions."""
        with self.lock:
            return [region for region, status in self.region_status.items() if status]
    
    def sort_regions_by_preference(self, regions: List[str], preferred_regions: List[str]) -> List[str]:
        """Sort regions by preference and availability."""
        # First filter out any regions known to be unavailable
        available = [r for r in regions if self.is_region_available(r) != False]
        
        # Then sort by preference
        def region_sort_key(region):
            try:
                return preferred_regions.index(region)
            except ValueError:
                return len(preferred_regions)  # Put non-preferred at the end
        
        return sorted(available, key=region_sort_key)


class ModelManager:
    """
    Manages model information, availability, and fallback paths.
    """
    # Default model fallback paths
    DEFAULT_MODEL_FALLBACKS = {
        # Claude model fallbacks
        'anthropic.claude-3-5-sonnet-20240620-v1:0': ['anthropic.claude-3-sonnet-20240229-v1:0', 'anthropic.claude-3-haiku-20240307-v1:0'],
        'anthropic.claude-3-5-sonnet-20241022-v2:0': ['anthropic.claude-3-5-sonnet-20240620-v1:0', 'anthropic.claude-3-sonnet-20240229-v1:0'],
        'anthropic.claude-3-7-sonnet-20250219-v1:0': ['anthropic.claude-3-5-sonnet-20241022-v2:0', 'anthropic.claude-3-5-sonnet-20240620-v1:0'],
        'anthropic.claude-3-sonnet-20240229-v1:0': ['anthropic.claude-3-haiku-20240307-v1:0'],
        'anthropic.claude-3-haiku-20240307-v1:0': ['anthropic.claude-3-5-haiku-20241022-v1:0'],
        'anthropic.claude-3-opus-20240229-v1:0': ['anthropic.claude-3-sonnet-20240229-v1:0', 'anthropic.claude-3-haiku-20240307-v1:0'],
        'anthropic.claude-3-5-haiku-20241022-v1:0': ['anthropic.claude-3-haiku-20240307-v1:0'],
        
        # Amazon Nova model fallbacks
        'amazon.nova-premier-v1:0': ['amazon.nova-pro-v1:0', 'amazon.nova-lite-v1:0'],
        'amazon.nova-pro-v1:0': ['amazon.nova-lite-v1:0', 'amazon.nova-micro-v1:0'],
        'amazon.nova-lite-v1:0': ['amazon.nova-micro-v1:0'],
    }
    
    # Map models to model families
    MODEL_FAMILIES = {
        'anthropic': [
            'anthropic.claude-3-7-sonnet-20250219-v1:0',
            'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'anthropic.claude-3-5-sonnet-20240620-v1:0',
            'anthropic.claude-3-sonnet-20240229-v1:0',
            'anthropic.claude-3-haiku-20240307-v1:0',
            'anthropic.claude-3-opus-20240229-v1:0',
            'anthropic.claude-3-5-haiku-20241022-v1:0',
        ],
        'amazon': [
            'amazon.nova-premier-v1:0',
            'amazon.nova-pro-v1:0',
            'amazon.nova-lite-v1:0',
            'amazon.nova-micro-v1:0',
        ],
    }
    
    # Map of model to inference parameter adjustments specific to regions
    # Some regions (like EU) have restrictions
    REGION_SPECIFIC_ADJUSTMENTS = {
        'eu': {
            # Example: EU may have specific guidelines around toxic content filters
            'all_models': {
                'additionalModelRequestFields': {
                    'contentFilterThresholds': {'hate': 0.8, 'sexual': 0.9, 'violence': 0.9}
                }
            },
        }
    }
    
    def __init__(self):
        self.model_availability: Dict[str, Tuple[bool, float]] = {}  # Tracks model availability by region
        self.lock = threading.Lock()  # Thread safety for model status updates
        self.custom_fallbacks: Dict[str, List[str]] = {}    # Custom fallbacks configured by the user
        
    def register_model_fallback_path(self, model_id: str, fallback_models: List[str]) -> None:
        """Register a custom fallback path for a model."""
        with self.lock:
            self.custom_fallbacks[model_id] = fallback_models
    
    def get_fallback_models(self, model_id: str) -> List[str]:
        """Get fallback models for a given model."""
        with self.lock:
            if model_id in self.custom_fallbacks:
                return self.custom_fallbacks[model_id]
            return self.DEFAULT_MODEL_FALLBACKS.get(model_id, [])
    
    def mark_model_available(self, model_id: str, region: str) -> None:
        """Mark a model as available in a region."""
        key = f"{model_id}:{region}"
        with self.lock:
            self.model_availability[key] = (True, time.time())
    
    def mark_model_unavailable(self, model_id: str, region: str) -> None:
        """Mark a model as unavailable in a region."""
        key = f"{model_id}:{region}"
        with self.lock:
            self.model_availability[key] = (False, time.time())
    
    def is_model_available(self, model_id: str, region: str) -> Optional[bool]:
        """Check if a model is available in a region."""
        key = f"{model_id}:{region}"
        with self.lock:
            if key in self.model_availability:
                status, timestamp = self.model_availability[key]
                # If check is older than 5 minutes, return None (unknown)
                if time.time() - timestamp > 300:
                    return None
                return status
            return None  # Status unknown if never checked
    
    def get_model_family(self, model_id: str) -> Optional[str]:
        """Get the family of a given model."""
        for family, models in self.MODEL_FAMILIES.items():
            if model_id in models:
                return family
        # Extract family from model ID if not found in mappings
        match = re.match(r'^([a-z]+)\.', model_id)
        if match:
            return match.group(1)
        return None
    
    def get_region_specific_adjustments(self, model_id: str, region: str, region_manager: 'RegionManager') -> Dict[str, Any]:
        """Get any region-specific parameter adjustments for a model."""
        zone = region_manager.get_zone_for_region(region)
        adjustments: Dict[str, Any] = {}
        
        # Apply zone-specific adjustments if they exist
        if zone in self.REGION_SPECIFIC_ADJUSTMENTS:
            zone_adjustments = self.REGION_SPECIFIC_ADJUSTMENTS[zone]
            # Apply general adjustments for all models in this zone
            if 'all_models' in zone_adjustments:
                adjustments.update(zone_adjustments['all_models'])
            # Apply model-specific adjustments
            if model_id in zone_adjustments:
                adjustments.update(zone_adjustments[model_id])
        
        return adjustments
    
    def get_models_in_family(self, family: str) -> List[str]:
        """Get all models in a given family."""
        return self.MODEL_FAMILIES.get(family, [])


class CRISManager:
    """
    Manages Cross-Regional Intelligent Routing System (CRIS) profiles.
    """
    # Default mapping of models to CRIS profiles
    DEFAULT_CRIS_PROFILES = {
        # US zone CRIS profiles
        'us': {
            'anthropic.claude-3-7-sonnet-20250219-v1:0': 'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
            'anthropic.claude-3-5-sonnet-20241022-v2:0': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            'anthropic.claude-3-5-sonnet-20240620-v1:0': 'us.anthropic.claude-3-5-sonnet-20240620-v1:0',
            'anthropic.claude-3-5-haiku-20241022-v1:0': 'us.anthropic.claude-3-5-haiku-20241022-v1:0',
            'anthropic.claude-3-sonnet-20240229-v1:0': 'us.anthropic.claude-3-sonnet-20240229-v1:0',
            'anthropic.claude-3-opus-20240229-v1:0': 'us.anthropic.claude-3-opus-20240229-v1:0',
            'anthropic.claude-3-haiku-20240307-v1:0': 'us.anthropic.claude-3-haiku-20240307-v1:0',
            'amazon.nova-premier-v1:0': 'us.amazon.nova-premier-v1:0',
            'amazon.nova-pro-v1:0': 'us.amazon.nova-pro-v1:0',
            'amazon.nova-lite-v1:0': 'us.amazon.nova-lite-v1:0',
            'amazon.nova-micro-v1:0': 'us.amazon.nova-micro-v1:0',
        },
        # EU zone CRIS profiles
        'eu': {
            'anthropic.claude-3-7-sonnet-20250219-v1:0': 'eu.anthropic.claude-3-7-sonnet-20250219-v1:0',
            'anthropic.claude-3-5-sonnet-20240620-v1:0': 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0',
            'anthropic.claude-3-sonnet-20240229-v1:0': 'eu.anthropic.claude-3-sonnet-20240229-v1:0',
            'anthropic.claude-3-haiku-20240307-v1:0': 'eu.anthropic.claude-3-haiku-20240307-v1:0',
            'amazon.nova-pro-v1:0': 'eu.amazon.nova-pro-v1:0',
            'amazon.nova-lite-v1:0': 'eu.amazon.nova-lite-v1:0',
            'amazon.nova-micro-v1:0': 'eu.amazon.nova-micro-v1:0',
        },
        # APAC zone CRIS profiles
        'apac': {
            'anthropic.claude-3-5-sonnet-20241022-v2:0': 'apac.anthropic.claude-3-5-sonnet-20241022-v2:0',
            'anthropic.claude-3-5-sonnet-20240620-v1:0': 'apac.anthropic.claude-3-5-sonnet-20240620-v1:0',
            'anthropic.claude-3-sonnet-20240229-v1:0': 'apac.anthropic.claude-3-sonnet-20240229-v1:0',
            'anthropic.claude-3-haiku-20240307-v1:0': 'apac.anthropic.claude-3-haiku-20240307-v1:0',
            'amazon.nova-pro-v1:0': 'apac.amazon.nova-pro-v1:0',
            'amazon.nova-lite-v1:0': 'apac.amazon.nova-lite-v1:0',
            'amazon.nova-micro-v1:0': 'apac.amazon.nova-micro-v1:0',
        },
        # US-GOV zone CRIS profiles
        'us-gov': {
            'anthropic.claude-3-5-sonnet-20240620-v1:0': 'us-gov.anthropic.claude-3-5-sonnet-20240620-v1:0',
            'anthropic.claude-3-haiku-20240307-v1:0': 'us-gov.anthropic.claude-3-haiku-20240307-v1:0',
        }
    }
    
    def __init__(self):
        self.custom_cris_profiles: Dict[str, Dict[str, str]] = {}  # Custom CRIS profiles configured by the user
        self.cris_profile_status: Dict[str, Tuple[bool, float]] = {}   # Tracks CRIS profile availability
        self.lock = threading.Lock()     # Thread safety for status updates
        
    def register_cris_profile(self, zone: str, model_id: str, cris_profile_id: str) -> None:
        """Register a custom CRIS profile for a model in a zone."""
        with self.lock:
            if zone not in self.custom_cris_profiles:
                self.custom_cris_profiles[zone] = {}
            self.custom_cris_profiles[zone][model_id] = cris_profile_id
    
    def get_cris_profile(self, zone: str, model_id: str) -> Optional[str]:
        """Get the CRIS profile for a model in a zone."""
        with self.lock:
            # Try custom profiles first
            if zone in self.custom_cris_profiles and model_id in self.custom_cris_profiles[zone]:
                return self.custom_cris_profiles[zone][model_id]
            
            # Fall back to default profiles
            if zone in self.DEFAULT_CRIS_PROFILES and model_id in self.DEFAULT_CRIS_PROFILES[zone]:
                return self.DEFAULT_CRIS_PROFILES[zone][model_id]
            
            return None
    
    def mark_cris_profile_available(self, cris_profile_id: str) -> None:
        """Mark a CRIS profile as available."""
        with self.lock:
            self.cris_profile_status[cris_profile_id] = (True, time.time())
    
    def mark_cris_profile_unavailable(self, cris_profile_id: str) -> None:
        """Mark a CRIS profile as unavailable."""
        with self.lock:
            self.cris_profile_status[cris_profile_id] = (False, time.time())
    
    def is_cris_profile_available(self, cris_profile_id: str) -> Optional[bool]:
        """Check if a CRIS profile is available."""
        with self.lock:
            if cris_profile_id in self.cris_profile_status:
                status, timestamp = self.cris_profile_status[cris_profile_id]
                # If check is older than 5 minutes, return None (unknown)
                if time.time() - timestamp > 300:
                    return None
                return status
            return None  # Status unknown if never checked
    
    def get_models_for_zone(self, zone: str) -> List[str]:
        """Get all model IDs available in a specific CRIS zone."""
        models = []
        
        # Add models from default profiles
        if zone in self.DEFAULT_CRIS_PROFILES:
            models.extend(self.DEFAULT_CRIS_PROFILES[zone].keys())
        
        # Add models from custom profiles
        if zone in self.custom_cris_profiles:
            models.extend(self.custom_cris_profiles[zone].keys())
        
        # Remove duplicates
        return list(set(models))


class RetryManager:
    """
    Manages retry logic with exponential backoff.
    """
    def __init__(self):
        self.max_retries: int = 3
        self.base_delay: float = 0.5  # Base delay in seconds
        self.max_delay: float = 10.0    # Maximum delay in seconds
        self.throttle_delay: float = 2.0  # Default delay for throttling errors
        
    def set_retry_parameters(self, 
                            max_retries: Optional[int] = None, 
                            base_delay: Optional[float] = None,
                            max_delay: Optional[float] = None, 
                            throttle_delay: Optional[float] = None) -> None:
        """Configure retry parameters."""
        if max_retries is not None:
            self.max_retries = max_retries
        if base_delay is not None:
            self.base_delay = base_delay
        if max_delay is not None:
            self.max_delay = max_delay
        if throttle_delay is not None:
            self.throttle_delay = throttle_delay
    
    def calculate_delay(self, attempt: int, error_type: Optional[str] = None) -> float:
        """
        Calculate the delay for a retry based on the attempt number and error type.
        
        Args:
            attempt: The current attempt number (0-based)
            error_type: The type of error that occurred
            
        Returns:
            The delay in seconds
        """
        if error_type == 'ThrottlingException':
            # For throttling, use a higher base delay
            return min(self.throttle_delay * (2 ** attempt), self.max_delay)
        
        # Standard exponential backoff with jitter
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        # Add some randomness (jitter) to prevent synchronized retries
        jitter = delay * 0.2  # 20% jitter
        return delay + (jitter * (2 * (0.5 - (hash(str(time.time())) % 1000) / 1000)))


class LLMManager:
    """
    Manager for AWS Bedrock LLMs with multi-region failover, model flexibility, and CRIS integration.
    """
    def __init__(self, 
                 aws_region: Optional[str] = None,
                 preferred_regions: Optional[List[str]] = None,
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 aws_session_token: Optional[str] = None,
                 profile_name: Optional[str] = None,
                 max_parallel_requests: int = 5):
        """
        Initialize the LLM Manager.
        
        Args:
            aws_region: The primary AWS region to use
            preferred_regions: List of preferred regions in order of preference
            aws_access_key_id: Optional AWS access key
            aws_secret_access_key: Optional AWS secret key
            aws_session_token: Optional AWS session token
            profile_name: Optional AWS CLI profile name to use for authentication
            max_parallel_requests: Maximum number of parallel requests to process
        """
        # Initialize AWS session parameters
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.profile_name = profile_name
        
        # Initialize managers
        self.region_manager = RegionManager()
        self.model_manager = ModelManager()
        self.cris_manager = CRISManager()
        self.retry_manager = RetryManager()
        
        # Set up primary region and preferences
        self.primary_region = aws_region or 'us-east-1'  # Default to us-east-1 if not specified
        self.preferred_regions = preferred_regions or [
            self.primary_region,
            *[r for r in self.region_manager.US_REGIONS if r != self.primary_region],
        ]
        
        # Client caching to avoid redundant creation
        self.clients: Dict[str, Any] = {}
        self.client_lock = threading.Lock()
        
        # Tracking for tried model-region combinations to prevent redundant retries
        self.tried_combinations: Set[str] = set()
        
        # Threading control
        self.max_parallel_requests = max_parallel_requests
        self.executor = ThreadPoolExecutor(max_workers=max_parallel_requests)
        
        # Statistics and monitoring
        self.stats: Dict[str, Union[int, float]] = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "region_switches": 0,
            "model_fallbacks": 0,
            "avg_latency": 0.0,
        }
        
        # Store original model for each request
        self.original_model_id = ""
        
    def set_preferred_regions(self, regions: List[str]) -> None:
        """
        Update the preferred AWS regions in order of preference.
        
        Args:
            regions: List of AWS region codes in order of preference
        """
        if not regions:
            logger.warning("Empty regions list provided, keeping current preferred regions")
            return
        
        logger.info(f"Updating preferred regions to {regions}")
        self.preferred_regions = regions
        
    def get_bedrock_client(self, region: str) -> Any:
        """
        Get or create a Bedrock client for the specified region.
        
        Args:
            region: The AWS region to create a client for
            
        Returns:
            A boto3 Bedrock client
        """
        with self.client_lock:
            if region not in self.clients:
                # Create a new session with the appropriate credentials or profile
                if self.profile_name:
                    # Use AWS profile for authentication
                    session = boto3.Session(
                        region_name=region,
                        profile_name=self.profile_name
                    )
                else:
                    # Use explicit credentials if provided
                    session = boto3.Session(
                        region_name=region,
                        aws_access_key_id=self.aws_access_key_id,
                        aws_secret_access_key=self.aws_secret_access_key,
                        aws_session_token=self.aws_session_token
                    )
                self.clients[region] = session.client('bedrock-runtime')
            return self.clients[region]
    
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """
        Get current performance statistics.
        
        Returns:
            Dictionary of statistics including requests, successes, failures,
            region switches, model fallbacks, and average latency.
        """
        return self.stats.copy()
        
    def converse(self, 
                 modelId: str,
                 messages: List[Dict[str, Any]],
                 system: Optional[List[Dict[str, Any]]] = None,
                 inferenceConfig: Optional[Dict[str, Any]] = None,
                 toolConfig: Optional[Dict[str, Any]] = None,
                 guardrailConfig: Optional[Dict[str, Any]] = None,
                 additionalModelRequestFields: Optional[Dict[str, Any]] = None,
                 promptVariables: Optional[Dict[str, Dict[str, str]]] = None,
                 additionalModelResponseFieldPaths: Optional[List[str]] = None,
                 requestMetadata: Optional[Dict[str, str]] = None,
                 performanceConfig: Optional[Dict[str, str]] = None,
                 preferredRegions: Optional[List[str]] = None,
                 validation_function: Optional[Callable[[Dict[str, Any]], bool]] = None,
                 parallel: bool = True,
                 use_cris: bool = True,
                 prompt_caching: bool = False,
                 max_retries: Optional[int] = None,
                 aws_session: Optional[Any] = None,
                 update_stats: bool = True) -> BedrockConverseResponse:
        """
        Send a request to AWS Bedrock with automatic retries, fallbacks, and region switching.
        
        Args:
            modelId: The model ID to use
            messages: The messages to send to the model
            system: Optional system messages
            inferenceConfig: Optional inference configuration
            toolConfig: Optional tool configuration
            guardrailConfig: Optional guardrail configuration
            additionalModelRequestFields: Optional additional fields for the model request
            promptVariables: Optional variables for the prompt
            additionalModelResponseFieldPaths: Optional field paths to retrieve from the response
            requestMetadata: Optional metadata for the request
            performanceConfig: Optional performance configuration
            preferredRegions: Optional list of preferred regions
            validation_function: Optional function to validate the response
            parallel: Whether to try different regions in parallel
            use_cris: Whether to use CRIS for region-specific profiles
            prompt_caching: Whether to use prompt caching
            max_retries: Maximum number of retries
            aws_session: Optional custom AWS session to use
            update_stats: Whether to update statistics
            
        Returns:
            A BedrockConverseResponse object
        """
        # Save the original model ID for reference
        self.original_model_id = modelId
        current_model_id = modelId
        
        # Clear any previous tried combinations
        self.tried_combinations = set()
        
        # Generate a request ID for tracking
        request_id = f"req-{uuid.uuid4().hex[:8]}"
        logger.info(f"Request {request_id}: Starting with model {modelId}")
        
        # Set up retry counter
        retry_count = 0
        max_retries_to_use = max_retries if max_retries is not None else self.retry_manager.max_retries
        
        # Start time for measuring latency
        start_time = time.time()
        
        # Track metrics for this request
        region_switches = 0
        model_fallbacks = 0
        
        # Update the request counter immediately
        if update_stats:
            self.stats["requests"] += 1
        
        # Use provided preferred regions or the default
        actual_preferred_regions = preferredRegions if preferredRegions else self.preferred_regions
        
        # Get the models to try, starting with the requested one
        models_to_try = [current_model_id]
        fallback_models = self.model_manager.get_fallback_models(current_model_id)
        if fallback_models:
            models_to_try.extend(fallback_models)
        
        # Try each model until success or we run out of options
        success = False
        response = None
        regions_to_try = []  # Initialize to avoid 'possibly unbound' error
        
        for model_index, current_model_id in enumerate(models_to_try):
            if model_index > 0:
                model_fallbacks += 1
                logger.info(f"Request {request_id}: Falling back to model {current_model_id}")
            
            # Get regions to try for this model
            regions_to_try = self.region_manager.sort_regions_by_preference(
                actual_preferred_regions, actual_preferred_regions
            )
            
            # Try each region until success or we run out of options
            for region_index, region in enumerate(regions_to_try):
                if region_index > 0:
                    region_switches += 1
                    logger.info(f"Request {request_id}: Switching to region {region}")
                
                # Skip if we've already tried this model-region combination
                combo_key = f"{current_model_id}:{region}"
                if combo_key in self.tried_combinations:
                    logger.debug(f"Request {request_id}: Already tried {combo_key}, skipping")
                    continue
                
                # Mark this combination as tried
                self.tried_combinations.add(combo_key)
                
                # Check if model is known to be unavailable in this region
                if self.model_manager.is_model_available(current_model_id, region) is False:
                    logger.debug(f"Request {request_id}: Model {current_model_id} is known to be unavailable in {region}, skipping")
                    continue
                
                # Try CRIS profile if using CRIS
                cris_profile_id = None
                if use_cris:
                    zone = self.region_manager.get_zone_for_region(region)
                    cris_profile_id = self.cris_manager.get_cris_profile(zone, current_model_id)
                    
                    # If we have a CRIS profile, check if it's known to be unavailable
                    if cris_profile_id:
                        if self.cris_manager.is_cris_profile_available(cris_profile_id) is False:
                            logger.debug(f"Request {request_id}: CRIS profile {cris_profile_id} is known to be unavailable, skipping")
                            continue
                        
                        logger.info(f"Request {request_id}: Using CRIS profile {cris_profile_id}")
                
                # Try to get a bedrock client for this region
                try:
                    client = self.get_bedrock_client(region)
                except Exception as e:
                    logger.warning(f"Request {request_id}: Failed to create client for {region}: {str(e)}")
                    self.region_manager.mark_region_unavailable(region)
                    continue
                
                # Apply any region-specific adjustments to the request
                adjusted_request = {}
                if additionalModelRequestFields:
                    adjusted_request["additionalModelRequestFields"] = additionalModelRequestFields.copy()
                
                region_adjustments = self.model_manager.get_region_specific_adjustments(
                    current_model_id, region, self.region_manager
                )
                for key, value in region_adjustments.items():
                    if key in adjusted_request:
                        if isinstance(adjusted_request[key], dict) and isinstance(value, dict):
                            adjusted_request[key].update(value)
                        else:
                            adjusted_request[key] = value
                    else:
                        adjusted_request[key] = value
                
                # Mark the beginning of this attempt
                attempt_start_time = time.time()
                retry_count += 1
                
                try:
                    # Prepare the request parameters
                    converse_args = {
                        "modelId": cris_profile_id or current_model_id,
                        "messages": messages,
                    }
                    
                    # Add optional parameters if provided
                    if system:
                        converse_args["system"] = system
                    if inferenceConfig:
                        converse_args["inferenceConfig"] = inferenceConfig
                    if toolConfig:
                        converse_args["toolConfig"] = toolConfig
                    if guardrailConfig:
                        converse_args["guardrailConfig"] = guardrailConfig
                    if adjusted_request.get("additionalModelRequestFields"):
                        converse_args["additionalModelRequestFields"] = adjusted_request["additionalModelRequestFields"]
                    if promptVariables:
                        converse_args["promptVariables"] = promptVariables
                    if additionalModelResponseFieldPaths:
                        converse_args["additionalModelResponseFieldPaths"] = additionalModelResponseFieldPaths
                    if requestMetadata:
                        # Ensure requestMetadata is not empty to avoid API error
                        if requestMetadata:
                            converse_args["requestMetadata"] = requestMetadata
                    
                    # Make the request
                    logger.debug(f"Request {request_id}: Sending request to {region} with model {converse_args['modelId']}")
                    api_response = client.converse(**converse_args)
                    
                    # Check if response body exists before trying to read it
                    if api_response is None or api_response.get("body") is None:
                        raise Exception(f"Empty response received from model {converse_args['modelId']} in region {region}")
                    
                    response = json.loads(api_response["body"].read())
                    
                    # Validate the response if a validation function is provided
                    if validation_function and not validation_function(response):
                        logger.warning(f"Request {request_id}: Response validation failed")
                        raise Exception("Response validation failed")
                    
                    # Mark this model and region as available
                    self.model_manager.mark_model_available(current_model_id, region)
                    self.region_manager.mark_region_available(region)
                    if cris_profile_id:
                        self.cris_manager.mark_cris_profile_available(cris_profile_id)
                    
                    # We got a successful response
                    success = True
                    logger.info(f"Request {request_id}: Successfully received response from {region}")
                    break
                    
                except Exception as e:
                    error_type = type(e).__name__
                    error_message = str(e)
                    logger.warning(f"Request {request_id}: Error with {current_model_id} in {region}: {error_type}: {error_message}")
                    
                    # Mark resources as unavailable based on the error
                    if "ResourceNotFoundException" in error_type or "ModelNotFound" in error_message:
                        self.model_manager.mark_model_unavailable(current_model_id, region)
                    elif "ThrottlingException" in error_type:
                        # Don't mark the region as unavailable for throttling, just wait longer
                        pass
                    elif "AccessDeniedException" in error_type or "ValidationException" in error_type:
                        # These are usually configuration errors, not transient ones
                        self.model_manager.mark_model_unavailable(current_model_id, region)
                    else:
                        # For other errors, mark the region as potentially having issues
                        self.region_manager.mark_region_unavailable(region)
                    
                    if cris_profile_id and ("ResourceNotFoundException" in error_type or "ModelNotFound" in error_message):
                        self.cris_manager.mark_cris_profile_unavailable(cris_profile_id)
                    
                    # If we've tried all options or reached max retries, don't wait
                    if retry_count >= max_retries_to_use:
                        logger.warning(f"Request {request_id}: Reached maximum retry count ({max_retries_to_use})")
                        continue
                    
                    # Calculate backoff delay
                    delay = self.retry_manager.calculate_delay(retry_count, error_type)
                    logger.info(f"Request {request_id}: Retrying in {delay:.2f} seconds")
                    time.sleep(delay)
            
            # If we succeeded with this model, no need to try fallbacks
            if success:
                break
        
        # After trying all models, check if we succeeded
        if success:
            # Find the last region used (the one that succeeded)
            last_used_region = None
            for r in regions_to_try:
                combo_key = f"{current_model_id}:{r}"
                if combo_key in self.tried_combinations:
                    last_used_region = r
            
            # Use the last region or a default
            last_region = last_used_region or self.primary_region
            execution_time_ms = (time.time() - start_time) * 1000
            response_with_metadata = response.copy() if response else {}
            response_with_metadata['metadata'] = {
                'model_used': current_model_id,
                'region_used': last_region,
                'execution_time_ms': execution_time_ms,
                'fallbacks_used': model_fallbacks,
                'region_switches': region_switches,
                'request_id': request_id
            }
            logger.info(f"Request {request_id}: Success with model {current_model_id} in region {last_region} after {retry_count} retries")
            
            # Update statistics immediately
            if update_stats:
                self.stats["successes"] += 1
                
                # Update average latency
                current_avg = self.stats["avg_latency"]
                request_count = self.stats["successes"]
                if request_count > 1:  # If we've had more than one success
                    self.stats["avg_latency"] = (current_avg * (request_count - 1) + execution_time_ms) / request_count
                else:
                    self.stats["avg_latency"] = execution_time_ms
                
                # Update region switches and model fallbacks
                self.stats["region_switches"] += region_switches
                self.stats["model_fallbacks"] += model_fallbacks
                
            return BedrockConverseResponse(response_with_metadata)
        else:
            # Create error response
            error_response = {
                'error': {
                    'message': f"Failed to complete request after {retry_count} retries",
                    'tried_combinations': list(self.tried_combinations)
                },
                'metadata': {
                    'model_used': self.original_model_id,
                    'execution_time_ms': (time.time() - start_time) * 1000,
                    'fallbacks_used': model_fallbacks,
                    'region_switches': region_switches,
                    'request_id': request_id
                }
            }
            
            # Update statistics if enabled
            if update_stats:
                self.stats["failures"] += 1
                logger.error(f"Request {request_id}: Failed after {retry_count} retries")
                
                # Update region switches and model fallbacks stats
                self.stats["region_switches"] += region_switches
                self.stats["model_fallbacks"] += model_fallbacks
            
            return BedrockConverseResponse(error_response)
