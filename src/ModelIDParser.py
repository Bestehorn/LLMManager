"""
Parser for AWS Bedrock model IDs and their supported regions.
"""
import re
import json
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    """Information about a model, including its ID and supported regions."""
    model_id: str
    regions: List[str]
    capabilities: List[str] = field(default_factory=list)
    streaming_supported: bool = False


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
        self._models: Dict[str, ModelInfo] = {}
        logging.basicConfig(level=log_level)
    
    @property
    def models(self) -> Dict[str, ModelInfo]:
        """Get the parsed models."""
        return self._models
    
    def clear(self) -> None:
        """Clear all parsed models."""
        self._models = {}
    
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
        self._models.update(models)
        return self._models
    
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
            self._models.update(models)
            return self._models
        except Exception as e:
            logger.error(f"Failed to parse model information from JSON: {str(e)}")
            return {}
    
    def _parse_model_table(self, text: str) -> Dict[str, ModelInfo]:
        """
        Parse model information from the text content of a model table.
        
        This method uses regex to extract model IDs and their supported regions
        from the AWS documentation format.
        
        Args:
            text: Text content to parse
            
        Returns:
            Dictionary of model IDs to ModelInfo objects
        """
        models: Dict[str, ModelInfo] = {}
        
        try:
            # Extract model entries
            # This regex looks for model ID and the text block that follows it until the next provider or EOF
            model_pattern = r"([a-zA-Z0-9\.-]+\.[a-zA-Z0-9\.-]+(?:-[a-zA-Z0-9\.-]+)*(?::[0-9]+)?)\s+\n\s*\n([^]*?)(?=Provider\s|$)"
            model_blocks = re.findall(model_pattern, text, re.MULTILINE)
            
            for model_id, details_block in model_blocks:
                # Extract regions
                region_pattern = r"(us-[a-z]+-[0-9]+|eu-[a-z]+-[0-9]+|ap-[a-z]+-[0-9]+|sa-[a-z]+-[0-9]+|ca-[a-z]+-[0-9]+|us-gov-[a-z]+-[0-9]+)"
                regions = re.findall(region_pattern, details_block)
                
                # Extract streaming supported
                streaming_supported = "Yes" in re.findall(r"Streaming supported\s+([A-Za-z]+)", details_block)
                
                # Extract capabilities (input/output modalities)
                input_modalities = re.findall(r"Input modalities\s+([^|]+)", details_block)
                output_modalities = re.findall(r"Output modalities\s+([^|]+)", details_block)
                
                capabilities: List[str] = []
                if input_modalities:
                    capabilities.extend([mod.strip() for mod in input_modalities[0].split(",")])
                if output_modalities:
                    capabilities.extend([mod.strip() for mod in output_modalities[0].split(",")])
                
                # Clean regions (remove duplicates and asterisks)
                clean_regions: Set[str] = set()
                for region in regions:
                    clean_regions.add(region.replace("*", ""))
                
                if clean_regions:
                    models[model_id] = ModelInfo(
                        model_id=model_id,
                        regions=list(clean_regions),
                        capabilities=capabilities,
                        streaming_supported=streaming_supported
                    )
                    logger.debug(f"Parsed model data for {model_id}: {clean_regions}")
            
            logger.info(f"Successfully parsed {len(models)} models")
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
            model_list = data.get("models", [])
            for model_data in model_list:
                model_id = model_data.get("model_id")
                if not model_id:
                    logger.warning("Found model entry without model_id, skipping")
                    continue
                
                regions = model_data.get("regions", [])
                capabilities = model_data.get("capabilities", [])
                streaming_supported = model_data.get("streaming_supported", False)
                
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
    
    def get_supported_regions_for_model(self, model_id: str) -> List[str]:
        """
        Get the supported regions for a model.
        
        Args:
            model_id: Model ID to check
            
        Returns:
            List of supported regions
        """
        if model_id in self._models:
            return self._models[model_id].regions
        return []
    
    def model_supports_streaming(self, model_id: str) -> bool:
        """
        Check if a model supports streaming.
        
        Args:
            model_id: Model ID to check
            
        Returns:
            True if the model supports streaming, False otherwise
        """
        if model_id in self._models:
            return self._models[model_id].streaming_supported
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
        if model_id in self._models:
            return capability in self._models[model_id].capabilities
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
