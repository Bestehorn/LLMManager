"""
LLMManager class for AWS Bedrock Converse API.
"""
import time
import logging
import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

import boto3
from botocore.exceptions import ClientError

from src.BedrockResponse import BedrockResponse
from src.ConverseFieldConstants import Fields, Roles, StopReasons, PerformanceConfig, GuardrailTrace
from src.ModelIDParser import ModelIDParser, ModelInfo, ModelProfileCollection, DEFAULT_MODEL_IDS_URL, DEFAULT_MODEL_IDS_JSON_CACHE
from src.CRISProfileParser import CRISProfileParser, CRISProfile, CRISProfileCollection, DEFAULT_CRIS_PROFILES_URL, DEFAULT_CRIS_PROFILES_JSON_CACHE

# Set up logging
logger = logging.getLogger(__name__)

class LLMManager:
    """
    Manager class for AWS Bedrock LLM interactions.
    
    This class provides an easy-to-use interface for interacting with AWS Bedrock's
    Converse API, with support for multiple regions, models, and authentication methods.
    It also prioritizes the use of Cross Region Inference (CRIS) when available.
    """
    
    def __init__(
        self,
        regions: Optional[List[str]] = None,
        model_ids: Optional[List[str]] = None,
        profile_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        model_data_path: str = "model_ids.txt",
        cris_profile_data_path: str = "cris_profile_definitions.txt",
        model_ids_url: str = DEFAULT_MODEL_IDS_URL,
        cris_profiles_url: str = DEFAULT_CRIS_PROFILES_URL,
        model_ids_cache_file: str = DEFAULT_MODEL_IDS_JSON_CACHE,
        cris_profiles_cache_file: str = DEFAULT_CRIS_PROFILES_JSON_CACHE,
        max_profile_age: int = 86400,  # 1 day in seconds
        force_model_id_update: bool = False,
        force_cris_profile_update: bool = False,
        log_level: int = logging.INFO
    ):
        """
        Initialize the LLMManager.
        
        Args:
            regions: List of AWS regions to use for inference
            model_ids: List of model IDs to use for inference
            profile_name: AWS CLI profile name for authentication
            aws_access_key_id: AWS access key ID for authentication
            aws_secret_access_key: AWS secret access key for authentication
            aws_session_token: AWS session token for authentication
            model_data_path: Path to the model data file (legacy parameter, kept for API compatibility)
            cris_profile_data_path: Path to the CRIS profile data file (legacy parameter, kept for API compatibility)
            model_ids_url: URL to fetch model IDs from
            cris_profiles_url: URL to fetch CRIS profiles from
            model_ids_cache_file: Path to the model IDs cache file
            cris_profiles_cache_file: Path to the CRIS profiles cache file
            max_profile_age: Maximum age of cache files in seconds
            force_model_id_update: Force update of model IDs from URL
            force_cris_profile_update: Force update of CRIS profiles from URL
            log_level: Logging level
        """
        # Configure logging
        logging.basicConfig(level=log_level)
        
        # Set default regions if not provided
        self.regions = regions or ["us-east-1", "us-west-2"]
        
        # Set default model IDs if not provided
        self.model_ids = model_ids or []
        
        # Authentication parameters
        self.profile_name = profile_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        
        # Initialize Bedrock Runtime clients for each region
        self.clients: Dict[str, Any] = {}
        self._initialize_clients()
        
        # Initialize parsers
        self.model_parser = ModelIDParser(log_level=log_level)
        self.cris_parser = CRISProfileParser(log_level=log_level)
        
        # Load model and CRIS data
        self._load_model_data(
            model_data_path=model_data_path,
            model_ids_url=model_ids_url,
            model_ids_cache_file=model_ids_cache_file,
            max_profile_age=max_profile_age,
            force_update=force_model_id_update
        )
        self._load_cris_profile_data(
            cris_profile_data_path=cris_profile_data_path,
            cris_profiles_url=cris_profiles_url,
            cris_profiles_cache_file=cris_profiles_cache_file,
            max_profile_age=max_profile_age,
            force_update=force_cris_profile_update
        )

    def _create_session(self) -> boto3.Session:
        """
        Create an AWS session using the provided authentication parameters.
        
        Returns:
            AWS session object
        """
        # If profile name is provided, use that
        if self.profile_name:
            return boto3.Session(profile_name=self.profile_name)
        
        # If access key and secret are provided, use those
        if self.aws_access_key_id and self.aws_secret_access_key:
            return boto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                aws_session_token=self.aws_session_token
            )
        
        # Otherwise, use the default credentials provider chain
        return boto3.Session()

    def _initialize_clients(self) -> None:
        """Initialize Bedrock Runtime clients for each region."""
        session = self._create_session()
        
        for region in self.regions:
            try:
                self.clients[region] = session.client(
                    service_name="bedrock-runtime",
                    region_name=region
                )
                logger.debug(f"Initialized client for region {region}")
            except Exception as e:
                logger.warning(f"Failed to initialize client for region {region}: {str(e)}")

    def _load_model_data(
        self, 
        model_data_path: str, 
        model_ids_url: str,
        model_ids_cache_file: str,
        max_profile_age: int,
        force_update: bool
    ) -> None:
        """
        Load model data from various sources based on availability and settings.
        
        Priority:
        1. URL source if forced update is requested
        2. Cache file if available and not expired
        3. URL source as fallback
        
        Args:
            model_data_path: Path to the legacy model data file (unused, kept for API compatibility)
            model_ids_url: URL to fetch model IDs from
            model_ids_cache_file: Path to the model IDs cache file
            max_profile_age: Maximum age of cache files in seconds
            force_update: Force update from URL regardless of cache status
        """
        try:
            # Try to load from URL if forced update requested
            if force_update:
                logger.info("Forced update of model data from URL")
                self.model_parser.parse_from_url(
                    url=model_ids_url,
                    cache_file=model_ids_cache_file,
                    save_cache=True
                )
                logger.info(f"Loaded data for {len(self.model_parser.models)} models from URL")
                return
            
            # Try to load from cache if not expired
            cache_loaded = False
            if os.path.exists(model_ids_cache_file):
                collection = ModelProfileCollection.from_json(model_ids_cache_file)
                if collection and not collection.is_expired(max_profile_age):
                    self.model_parser.set_model_collection(collection)
                    logger.info(f"Loaded model collection from cache (age: {int(time.time()) - collection.timestamp} seconds)")
                    cache_loaded = True
                else:
                    logger.info("Model cache file is expired or invalid")
            
            if cache_loaded:
                return
            
            # Try to load from URL as fallback
            try:
                self.model_parser.parse_from_url(
                    url=model_ids_url,
                    cache_file=model_ids_cache_file,
                    save_cache=True
                )
                logger.info(f"Loaded data for {len(self.model_parser.models)} models from URL")
            except Exception as e:
                logger.warning(f"Failed to load model data from URL: {str(e)}")
                logger.warning("Using empty model profile data")
                
        except Exception as e:
            logger.error(f"Failed to load model data: {str(e)}")
            # Proceed with empty model data

    def _load_cris_profile_data(
        self, 
        cris_profile_data_path: str, 
        cris_profiles_url: str,
        cris_profiles_cache_file: str,
        max_profile_age: int,
        force_update: bool
    ) -> None:
        """
        Load CRIS profile data from various sources based on availability and settings.
        
        Priority:
        1. URL source if forced update is requested
        2. Cache file if available and not expired
        3. URL source as fallback
        
        Args:
            cris_profile_data_path: Path to the legacy CRIS profile data file (unused, kept for API compatibility)
            cris_profiles_url: URL to fetch CRIS profiles from
            cris_profiles_cache_file: Path to the CRIS profiles cache file
            max_profile_age: Maximum age of cache files in seconds
            force_update: Force update from URL regardless of cache status
        """
        try:
            # Try to load from URL if forced update requested
            if force_update:
                logger.info("Forced update of CRIS profile data from URL")
                self.cris_parser.parse_from_url(
                    url=cris_profiles_url,
                    cache_file=cris_profiles_cache_file,
                    save_cache=True
                )
                logger.info(f"Loaded data for {len(self.cris_parser.profiles)} CRIS profiles from URL")
                return
            
            # Try to load from cache if not expired
            cache_loaded = False
            if os.path.exists(cris_profiles_cache_file):
                collection = CRISProfileCollection.from_json(cris_profiles_cache_file)
                if collection and not collection.is_expired(max_profile_age):
                    self.cris_parser.set_cris_profile_collection(collection)
                    logger.info(f"Loaded CRIS profile collection from cache (age: {int(time.time()) - collection.timestamp} seconds)")
                    cache_loaded = True
                else:
                    logger.info("CRIS profile cache file is expired or invalid")
            
            if cache_loaded:
                return
            
            # Try to load from URL as fallback
            try:
                self.cris_parser.parse_from_url(
                    url=cris_profiles_url,
                    cache_file=cris_profiles_cache_file,
                    save_cache=True
                )
                logger.info(f"Loaded data for {len(self.cris_parser.profiles)} CRIS profiles from URL")
            except Exception as e:
                logger.warning(f"Failed to load CRIS profile data from URL: {str(e)}")
                logger.warning("Using empty CRIS profile data")
                
        except Exception as e:
            logger.error(f"Failed to load CRIS profile data: {str(e)}")
            # Proceed with empty CRIS profile data

    def _get_model_region_combinations(
        self, 
        model_ids: List[str], 
        regions: List[str]
    ) -> List[Tuple[str, str, bool, Optional[str]]]:
        """
        Generate model-region combinations, prioritizing CRIS when available.
        
        Args:
            model_ids: List of model IDs
            regions: List of regions
            
        Returns:
            List of tuples (model_id, region, is_cris, cris_profile_id)
        """
        combinations = []
        
        # First, try CRIS profiles
        for model_id in model_ids:
            for region in regions:
                cris_profile_id = self.cris_parser.get_profile_for_model_region(model_id, region)
                if cris_profile_id:
                    combinations.append((model_id, region, True, cris_profile_id))
        
        # Then, try direct model-region combinations
        for model_id in model_ids:
            supported_regions = set(self.model_parser.get_supported_regions_for_model(model_id))
            for region in regions:
                if region in supported_regions:
                    # Check if this combination wasn't already added as CRIS
                    if not any(c[0] == model_id and c[1] == region and c[2] for c in combinations):
                        combinations.append((model_id, region, False, None))
        
        return combinations

    def converse(
        self,
        messages: List[Dict[str, Any]],
        model_ids: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        system: Optional[List[Dict[str, Any]]] = None,
        inference_config: Optional[Dict[str, Any]] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        guardrail_config: Optional[Dict[str, Any]] = None,
        additional_model_request_fields: Optional[Dict[str, Any]] = None,
        prompt_variables: Optional[Dict[str, Dict[str, str]]] = None,
        additional_model_response_field_paths: Optional[List[str]] = None,
        request_metadata: Optional[Dict[str, str]] = None,
        performance_config: Optional[Dict[str, str]] = None
    ) -> BedrockResponse:
        """
        Invoke the Converse API with the provided parameters.
        
        Args:
            messages: List of messages to send to the model
            model_ids: Model IDs to use (default: all configured models)
            regions: Regions to use (default: all configured regions)
            system: System prompt for the model
            inference_config: Configuration for model inference
            tool_config: Configuration for tool usage
            guardrail_config: Configuration for guardrails
            additional_model_request_fields: Additional model-specific request fields
            prompt_variables: Variables for prompt templates
            additional_model_response_field_paths: Additional response fields to return
            request_metadata: Metadata for the request
            performance_config: Performance configuration
            
        Returns:
            BedrockResponse object with the results
        """
        # Use specified model IDs or fall back to configured ones
        model_ids_to_try = model_ids or self.model_ids
        if not model_ids_to_try:
            logger.error("No model IDs provided")
            return BedrockResponse(
                exceptions=[ValueError("No model IDs provided")],
                prompts=messages
            )
        
        # Use specified regions or fall back to configured ones
        regions_to_try = regions or self.regions
        if not regions_to_try:
            logger.error("No regions provided")
            return BedrockResponse(
                exceptions=[ValueError("No regions provided")],
                prompts=messages
            )
        
        # Get all model-region combinations, prioritizing CRIS
        combinations = self._get_model_region_combinations(model_ids_to_try, regions_to_try)
        if not combinations:
            logger.error("No valid model-region combinations found")
            return BedrockResponse(
                exceptions=[ValueError("No valid model-region combinations found")],
                prompts=messages
            )
        
        # Prepare request parameters
        request_params: Dict[str, Any] = {
            Fields.MESSAGES: messages
        }
        
        # Add optional parameters if provided
        if system:
            request_params[Fields.SYSTEM] = system
        if inference_config:
            request_params[Fields.INFERENCE_CONFIG] = inference_config
        if tool_config:
            request_params[Fields.TOOL_CONFIG] = tool_config
        if guardrail_config:
            request_params[Fields.GUARDRAIL_CONFIG] = guardrail_config
        if additional_model_request_fields:
            request_params[Fields.ADDITIONAL_MODEL_REQUEST_FIELDS] = additional_model_request_fields
        if prompt_variables:
            request_params[Fields.PROMPT_VARIABLES] = prompt_variables
        if additional_model_response_field_paths:
            request_params[Fields.ADDITIONAL_MODEL_RESPONSE_FIELD_PATHS] = additional_model_response_field_paths
        if request_metadata:
            request_params[Fields.REQUEST_METADATA] = request_metadata
        if performance_config:
            request_params[Fields.PERFORMANCE_CONFIG] = performance_config
        
        # Try each combination until one succeeds
        exceptions = []
        for model_id, region, is_cris, cris_profile_id in combinations:
            try:
                # Get client for the region
                client = self.clients.get(region)
                if not client:
                    logger.warning(f"No client for region {region}, skipping")
                    exceptions.append(ValueError(f"No client for region {region}"))
                    continue
                
                # Set the model ID (either direct or CRIS profile)
                if is_cris and cris_profile_id:
                    request_params[Fields.MODEL_ID] = cris_profile_id
                    logger.info(f"Trying CRIS profile {cris_profile_id} from region {region}")
                else:
                    request_params[Fields.MODEL_ID] = model_id
                    logger.info(f"Trying model {model_id} in region {region}")
                
                # Make the API call
                start_time = time.time()
                response = client.converse(**request_params)
                execution_time = time.time() - start_time
                
                # Return successful response
                logger.info(f"Successfully invoked model {model_id} in region {region}")
                return BedrockResponse(
                    response=response,
                    model_id=model_id,
                    region=region,
                    prompts=messages,
                    execution_time=execution_time,
                    is_cris=is_cris
                )
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_msg = e.response['Error']['Message']
                logger.warning(f"Error invoking model {model_id} in region {region}: {error_code} - {error_msg}")
                
                # Try to adapt request parameters based on error
                if error_code == 'ValidationException' and 'guardrail' in error_msg.lower():
                    # Turn off guardrails for the next attempt
                    logger.info("Turning off guardrails and trying again")
                    if Fields.GUARDRAIL_CONFIG in request_params:
                        del request_params[Fields.GUARDRAIL_CONFIG]
                
                exceptions.append(e)
                
            except Exception as e:
                logger.warning(f"Error invoking model {model_id} in region {region}: {str(e)}")
                exceptions.append(e)
        
        # If all combinations failed, return response with exceptions
        logger.error("All model-region combinations failed")
        return BedrockResponse(
            exceptions=exceptions,
            prompts=messages
        )
    
    def create_text_message(self, text: str, role: str = Roles.USER) -> Dict[str, Any]:
        """
        Create a text message for the Converse API.
        
        Args:
            text: The text content of the message
            role: The role of the message sender (user or assistant)
            
        Returns:
            A message object compatible with the Converse API
        """
        return {
            Fields.ROLE: role,
            Fields.CONTENT: [
                {
                    Fields.TEXT: text
                }
            ]
        }
    
    def create_image_message(
        self, 
        image_bytes: bytes, 
        text: Optional[str] = None,
        image_format: str = "jpeg",
        role: str = Roles.USER
    ) -> Dict[str, Any]:
        """
        Create an image message for the Converse API.
        
        Args:
            image_bytes: Raw image bytes
            text: Optional text to include with the image
            image_format: Format of the image (jpeg, png, etc.)
            role: The role of the message sender (user)
            
        Returns:
            A message object compatible with the Converse API
        """
        content = []
        
        # Add image content
        content.append({
            Fields.IMAGE: {
                Fields.FORMAT: image_format,
                Fields.SOURCE: {
                    Fields.BYTES: image_bytes
                }
            }
        })
        
        # Add text content if provided
        if text:
            content.append({
                Fields.TEXT: text
            })
        
        return {
            Fields.ROLE: role,
            Fields.CONTENT: content
        }
    
    def get_model_profile_collection(self) -> ModelProfileCollection:
        """
        Get the current model profile collection.
        
        Returns:
            ModelProfileCollection object containing model profile data
        """
        return self.model_parser.get_model_collection()
    
    def get_cris_profile_collection(self) -> CRISProfileCollection:
        """
        Get the current CRIS profile collection.
        
        Returns:
            CRISProfileCollection object containing CRIS profile data
        """
        return self.cris_parser.get_cris_profile_collection()
    
    def export_profiles_to_json(
        self, 
        model_file_path: str = "model_profiles_export.json", 
        cris_file_path: str = "cris_profiles_export.json"
    ) -> Tuple[bool, bool]:
        """
        Export the current profile collections to JSON files.
        
        Args:
            model_file_path: Path to save the model profiles JSON
            cris_file_path: Path to save the CRIS profiles JSON
            
        Returns:
            Tuple of (model_success, cris_success) indicating if each export succeeded
        """
        model_success = False
        cris_success = False
        
        try:
            self.get_model_profile_collection().to_json(model_file_path)
            model_success = True
            logger.info(f"Exported model profiles to {model_file_path}")
        except Exception as e:
            logger.error(f"Failed to export model profiles: {str(e)}")
        
        try:
            self.get_cris_profile_collection().to_json(cris_file_path)
            cris_success = True
            logger.info(f"Exported CRIS profiles to {cris_file_path}")
        except Exception as e:
            logger.error(f"Failed to export CRIS profiles: {str(e)}")
            
        return model_success, cris_success

    def create_system_message(self, text: str) -> Dict[str, Any]:
        """
        Create a system message for the Converse API.
        
        Args:
            text: The system prompt text
            
        Returns:
            A system message object compatible with the Converse API
        """
        return {
            Fields.TEXT: text
        }
