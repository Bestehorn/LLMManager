"""
Parser for AWS Bedrock model IDs and their supported regions.
"""
import re
import json
import logging
import os
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

# Set up logging
logger = logging.getLogger(__name__)

# Constants for URLs and file paths
DEFAULT_MODEL_IDS_URL = "https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html"
DEFAULT_MODEL_IDS_JSON_CACHE = "model_ids_cache.json"

# Constants for JSON fields
FIELD_TIMESTAMP = "timestamp"
FIELD_MODELS = "models"
FIELD_MODEL_ID = "model_id"
FIELD_REGIONS = "regions"
FIELD_CAPABILITIES = "capabilities"
FIELD_STREAMING_SUPPORTED = "streaming_supported"

@dataclass
class ModelInfo:
    """Information about a model, including its ID and supported regions."""
    model_id: str
    regions: List[str]
    capabilities: List[str] = field(default_factory=list)
    streaming_supported: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model info to a dictionary."""
        return {
            FIELD_MODEL_ID: self.model_id,
            FIELD_REGIONS: self.regions,
            FIELD_CAPABILITIES: self.capabilities,
            FIELD_STREAMING_SUPPORTED: self.streaming_supported
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInfo':
        """Create a ModelInfo instance from a dictionary."""
        return cls(
            model_id=data[FIELD_MODEL_ID],
            regions=data[FIELD_REGIONS],
            capabilities=data.get(FIELD_CAPABILITIES, []),
            streaming_supported=data.get(FIELD_STREAMING_SUPPORTED, False)
        )


class ModelProfileCollection:
    """Collection of model profiles with metadata."""
    
    def __init__(self, timestamp: Optional[int] = None):
        """
        Initialize a model profile collection.
        
        Args:
            timestamp: Unix timestamp when the data was collected, defaults to current time
        """
        self.models: Dict[str, ModelInfo] = {}
        self.timestamp = timestamp or int(time.time())
    
    def add_model(self, model: ModelInfo) -> None:
        """Add a model to the collection."""
        self.models[model.model_id] = model
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get a model by ID."""
        return self.models.get(model_id)
    
    def get_all_models(self) -> Dict[str, ModelInfo]:
        """Get all models in the collection."""
        return self.models
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the collection to a dictionary."""
        return {
            FIELD_TIMESTAMP: self.timestamp,
            FIELD_MODELS: {model_id: model.to_dict() for model_id, model in self.models.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelProfileCollection':
        """Create a ModelProfileCollection from a dictionary."""
        collection = cls(timestamp=data.get(FIELD_TIMESTAMP))
        
        models_data = data.get(FIELD_MODELS, {})
        for model_id, model_data in models_data.items():
            collection.add_model(ModelInfo.from_dict(model_data))
            
        return collection
    
    def to_json(self, file_path: str) -> None:
        """Save the collection to a JSON file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save model collection to {file_path}: {str(e)}")
            raise
    
    @classmethod
    def from_json(cls, file_path: str) -> Optional['ModelProfileCollection']:
        """Load a ModelProfileCollection from a JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load model collection from {file_path}: {str(e)}")
            return None
    
    def is_expired(self, max_age: int) -> bool:
        """
        Check if the collection is expired.
        
        Args:
            max_age: Maximum age in seconds
            
        Returns:
            True if the collection is older than max_age, False otherwise
        """
        current_time = int(time.time())
        return current_time - self.timestamp > max_age


class ModelIDParser:
    """
    Parser for AWS Bedrock model IDs and their supported regions.
    
    This class provides functionality to parse model information from various sources,
    including the model_ids.txt file provided by AWS documentation, or from structured
    data sources like JSON files.
    """
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Initialize the parser.
        
        Args:
            log_level: Logging level
        """
        self._model_collection = ModelProfileCollection()
        logging.basicConfig(level=log_level)
    
    @property
    def models(self) -> Dict[str, ModelInfo]:
        """Get the parsed models."""
        return self._model_collection.get_all_models()
    
    def clear(self) -> None:
        """Clear all parsed models."""
        self._model_collection = ModelProfileCollection()
    
    def parse_from_file(self, file_path: str) -> Dict[str, ModelInfo]:
        """
        Parse model information from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary of model IDs to ModelInfo objects
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            return self.parse_from_text(content)
        except Exception as e:
            logger.error(f"Failed to parse model information from file {file_path}: {str(e)}")
            return {}
    
    def parse_from_text(self, text: str) -> Dict[str, ModelInfo]:
        """
        Parse model information from text content.
        
        Args:
            text: Text content to parse
            
        Returns:
            Dictionary of model IDs to ModelInfo objects
        """
        models = self._parse_model_table(text)
        if not models:
            logger.warning("No models found in the text content")
        
        for model_id, model_info in models.items():
            self._model_collection.add_model(model_info)
            
        return self._model_collection.get_all_models()
    
    def parse_from_url(
        self, 
        url: str = DEFAULT_MODEL_IDS_URL,
        cache_file: str = DEFAULT_MODEL_IDS_JSON_CACHE,
        save_cache: bool = True
    ) -> Dict[str, ModelInfo]:
        """Parse model information from a URL and optionally save to cache file."""
        try:
            import requests
            
            # Fetch HTML content
            response = requests.get(url)
            response.raise_for_status()
            html_content = response.text
            
            # Parse HTML content
            models = self._parse_model_table(html_content)
            
            # Update the model collection
            collection = ModelProfileCollection()
            for model_id, model_info in models.items():
                collection.add_model(model_info)
                
            if save_cache and models:
                collection.to_json(cache_file)
                
            self._model_collection = collection
            return self._model_collection.get_all_models()
        except Exception as e:
            logger.error(f"Failed to parse model information from URL {url}: {str(e)}")
            return {}
    
    def parse_from_json(self, json_str_or_path: str, is_file: bool = True) -> Dict[str, ModelInfo]:
        """
        Parse model information from JSON.
        
        Args:
            json_str_or_path: JSON string or path to JSON file
            is_file: Whether the input is a file path (True) or JSON string (False)
            
        Returns:
            Dictionary of model IDs to ModelInfo objects
        """
        try:
            if is_file:
                with open(json_str_or_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
            else:
                data = json.loads(json_str_or_path)
            
            # Process JSON data
            models = self._parse_json_data(data)
            
            # Update the model collection
            for model_id, model_info in models.items():
                self._model_collection.add_model(model_info)
                
            return self._model_collection.get_all_models()
        except Exception as e:
            logger.error(f"Failed to parse model information from JSON: {str(e)}")
            return {}
    
    def _parse_model_table(self, text: str) -> Dict[str, ModelInfo]:
        """
        Parse model information from HTML content.
        
        This method uses BeautifulSoup when available, falling back to regex
        for compatibility.
        
        Args:
            text: HTML content to parse
            
        Returns:
            Dictionary of model IDs to ModelInfo objects
        """
        models: Dict[str, ModelInfo] = {}
        
        try:
            # Try BeautifulSoup parsing first
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(text, 'html.parser')
                
                # Find tables containing model information
                tables = soup.find_all('table')
                for table in tables:
                    headers = [th.text.strip() for th in table.find_all('th')]
                    
                    # Check if this looks like a model table
                    if 'Model ID' in headers or 'Model' in headers:
                        # Process each row
                        rows = table.find_all('tr')
                        for row in rows[1:]:  # Skip header row
                            cells = row.find_all('td')
                            if cells and len(cells) >= 2:
                                # Extract model ID (usually first column)
                                model_id = cells[0].text.strip()
                                
                                # Make sure this looks like a model ID (contains a dot)
                                if '.' in model_id:
                                    # Find regions column (usually contains us-east-1, etc.)
                                    regions = []
                                    for i, cell in enumerate(cells):
                                        text = cell.text.strip()
                                        region_matches = re.findall(r'(us-[a-z]+-[0-9]+|eu-[a-z]+-[0-9]+|ap-[a-z]+-[0-9]+|sa-[a-z]+-[0-9]+|ca-[a-z]+-[0-9]+|us-gov-[a-z]+-[0-9]+)', text)
                                        if region_matches:
                                            regions.extend(region_matches)
                                    
                                    # Check for streaming support
                                    streaming_supported = False
                                    for cell in cells:
                                        if 'Yes' in cell.text and ('streaming' in cell.text.lower() or 'stream' in cell.text.lower()):
                                            streaming_supported = True
                                    
                                    # Extract capabilities
                                    capabilities = []
                                    for cell in cells:
                                        if 'Text' in cell.text or 'Image' in cell.text or 'Audio' in cell.text:
                                            modalities = re.findall(r'(Text|Image|Audio|Video)', cell.text)
                                            capabilities.extend(modalities)
                                    
                                    # Store model information if we have regions
                                    if regions:
                                        # Remove duplicates and clean regions
                                        clean_regions = set()
                                        for region in regions:
                                            clean_regions.add(region.replace("*", ""))
                                        
                                        models[model_id] = ModelInfo(
                                            model_id=model_id,
                                            regions=list(clean_regions),
                                            capabilities=list(set(capabilities)),
                                            streaming_supported=streaming_supported
                                        )
                                        logger.debug(f"Parsed model data for {model_id}")
                
                if models:
                    logger.info(f"Successfully parsed {len(models)} models using BeautifulSoup")
                    return models
                else:
                    logger.warning("No models found using BeautifulSoup, falling back to regex parsing")
                    
            except ImportError:
                logger.warning("BeautifulSoup not available, falling back to regex parsing")
            
            # Fallback to regex parsing
            # Extract model entries
            model_pattern = r"([a-zA-Z0-9\.-]+\.[a-zA-Z0-9\.-]+(?:-[a-zA-Z0-9\.-]+)*(?::[0-9]+)?)"
            model_ids = re.findall(model_pattern, text)
            
            # For each potential model ID, try to find regions nearby
            for model_id in model_ids:
                # Look for regions near the model ID
                region_pattern = r"(us-[a-z]+-[0-9]+|eu-[a-z]+-[0-9]+|ap-[a-z]+-[0-9]+|sa-[a-z]+-[0-9]+|ca-[a-z]+-[0-9]+|us-gov-[a-z]+-[0-9]+)"
                model_pos = text.find(model_id)
                if model_pos >= 0:
                    # Check 1000 characters after the model ID for regions
                    search_text = text[model_pos:model_pos + 1000]
                    regions = re.findall(region_pattern, search_text)
                    
                    if regions:
                        # Clean regions (remove duplicates and asterisks)
                        clean_regions = set()
                        for region in regions:
                            clean_regions.add(region.replace("*", ""))
                        
                        models[model_id] = ModelInfo(
                            model_id=model_id,
                            regions=list(clean_regions),
                            capabilities=["Text"],  # Default assumption
                            streaming_supported=False  # Default assumption
                        )
                        logger.debug(f"Parsed model data for {model_id} using regex")
            
            logger.info(f"Successfully parsed {len(models)} models using regex")
                
        except Exception as e:
            logger.error(f"Error parsing model table: {str(e)}")
        
        return models
    
    def _parse_json_data(self, data: Dict[str, Any]) -> Dict[str, ModelInfo]:
        """
        Parse model information from JSON data.
        
        Expected format:
        {
            "models": [
                {
                    "model_id": "example.model-v1:0",
                    "regions": ["us-east-1", "us-west-2"],
                    "capabilities": ["Text", "Image"],
                    "streaming_supported": true
                },
                ...
            ]
        }
        
        Args:
            data: JSON data to parse
            
        Returns:
            Dictionary of model IDs to ModelInfo objects
        """
        models: Dict[str, ModelInfo] = {}
        
        try:
            model_list = data.get(FIELD_MODELS, [])
            for model_data in model_list:
                model_id = model_data.get(FIELD_MODEL_ID)
                if not model_id:
                    logger.warning("Found model entry without model_id, skipping")
                    continue
                
                regions = model_data.get(FIELD_REGIONS, [])
                capabilities = model_data.get(FIELD_CAPABILITIES, [])
                streaming_supported = model_data.get(FIELD_STREAMING_SUPPORTED, False)
                
                models[model_id] = ModelInfo(
                    model_id=model_id,
                    regions=regions,
                    capabilities=capabilities,
                    streaming_supported=streaming_supported
                )
                logger.debug(f"Parsed model data for {model_id}: {regions}")
            
            logger.info(f"Successfully parsed {len(models)} models from JSON")
        except Exception as e:
            logger.error(f"Error parsing JSON data: {str(e)}")
        
        return models
    
    def get_model_collection(self) -> ModelProfileCollection:
        """Get the current model collection."""
        return self._model_collection
    
    def set_model_collection(self, collection: ModelProfileCollection) -> None:
        """Set the current model collection."""
        self._model_collection = collection
    
    def get_supported_regions_for_model(self, model_id: str) -> List[str]:
        """
        Get the supported regions for a model.
        
        Args:
            model_id: Model ID to check
            
        Returns:
            List of supported regions
        """
        models = self._model_collection.get_all_models()
        if model_id in models:
            return models[model_id].regions
        return []
    
    def model_supports_streaming(self, model_id: str) -> bool:
        """
        Check if a model supports streaming.
        
        Args:
            model_id: Model ID to check
            
        Returns:
            True if the model supports streaming, False otherwise
        """
        models = self._model_collection.get_all_models()
        if model_id in models:
            return models[model_id].streaming_supported
        return False
    
    def model_supports_capability(self, model_id: str, capability: str) -> bool:
        """
        Check if a model supports a specific capability.
        
        Args:
            model_id: Model ID to check
            capability: Capability to check for (e.g., "Text", "Image")
            
        Returns:
            True if the model supports the capability, False otherwise
        """
        models = self._model_collection.get_all_models()
        if model_id in models:
            return capability in models[model_id].capabilities
        return False

    def is_model_available_in_region(self, model_id: str, region: str) -> bool:
        """
        Check if a model is available in a specific region.
        
        Args:
            model_id: Model ID to check
            region: Region to check
            
        Returns:
            True if the model is available in the region, False otherwise
        """
        return region in self.get_supported_regions_for_model(model_id)
