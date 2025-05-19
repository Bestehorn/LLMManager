"""
Parser for AWS Bedrock Cross-Region Inference Service (CRIS) profiles.
"""
import re
import json
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class CRISProfile:
    """Information about a CRIS profile with source and destination regions."""
    profile_id: str
    profile_name: str
    source_regions: List[str]
    destination_regions: Dict[str, List[str]]
    
    def can_be_called_from(self, region: str) -> bool:
        """Check if this profile can be called from the given region."""
        return region in self.source_regions
    
    def get_destination_regions(self, source_region: str) -> List[str]:
        """
        Get the destination regions for the given source region.
        
        Args:
            source_region: Source region
            
        Returns:
            List of destination regions, empty if source region not supported
        """
        if source_region not in self.source_regions:
            return []
        return self.destination_regions.get(source_region, [])


class CRISProfileParser:
    """
    Parser for AWS Bedrock Cross-Region Inference Service (CRIS) profiles.
    
    This class provides functionality to parse CRIS profile information from various sources,
    including the cris_profile_definitions.txt file provided by AWS documentation,
    or from structured data sources like JSON files.
    """
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Initialize the parser.
        
        Args:
            log_level: Logging level
        """
        self._profiles: Dict[str, CRISProfile] = {}
        logging.basicConfig(level=log_level)
    
    @property
    def profiles(self) -> Dict[str, CRISProfile]:
        """Get the parsed CRIS profiles."""
        return self._profiles
    
    def clear(self) -> None:
        """Clear all parsed profiles."""
        self._profiles = {}
    
    def parse_from_file(self, file_path: str) -> Dict[str, CRISProfile]:
        """
        Parse CRIS profile information from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary of profile IDs to CRISProfile objects
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            return self.parse_from_text(content)
        except Exception as e:
            logger.error(f"Failed to parse CRIS profile information from file {file_path}: {str(e)}")
            return {}
    
    def parse_from_text(self, text: str) -> Dict[str, CRISProfile]:
        """
        Parse CRIS profile information from text content.
        
        Args:
            text: Text content to parse
            
        Returns:
            Dictionary of profile IDs to CRISProfile objects
        """
        profiles = self._parse_cris_profile_table(text)
        if not profiles:
            logger.warning("No CRIS profiles found in the text content")
        self._profiles.update(profiles)
        return self._profiles
    
    def parse_from_json(self, json_str_or_path: str, is_file: bool = True) -> Dict[str, CRISProfile]:
        """
        Parse CRIS profile information from JSON.
        
        Args:
            json_str_or_path: JSON string or path to JSON file
            is_file: Whether the input is a file path (True) or JSON string (False)
            
        Returns:
            Dictionary of profile IDs to CRISProfile objects
        """
        try:
            if is_file:
                with open(json_str_or_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
            else:
                data = json.loads(json_str_or_path)
            
            # Process JSON data
            profiles = self._parse_json_data(data)
            self._profiles.update(profiles)
            return self._profiles
        except Exception as e:
            logger.error(f"Failed to parse CRIS profile information from JSON: {str(e)}")
            return {}
    
    def _parse_cris_profile_table(self, text: str) -> Dict[str, CRISProfile]:
        """
        Parse CRIS profile information from the text content of a profile table.
        
        This method uses regex to extract profile IDs, source regions, and destination regions
        from the AWS documentation format.
        
        Args:
            text: Text content to parse
            
        Returns:
            Dictionary of profile IDs to CRISProfile objects
        """
        profiles: Dict[str, CRISProfile] = {}
        
        try:
            # Extract profile information using regex
            pattern = r'To call the ([^"]*?) inference profile, specify the following inference profile ID in one of the source Regions:\s*\n\s*\n([a-zA-Z0-9\.-]+\.[a-zA-Z0-9\.-]+(?:-[a-zA-Z0-9\.-]+)*(?::[0-9]+)?)\s*\n\s*\n.*?Source Region\s+Destination Regions(.*?)(?=To call|$)'
            profile_blocks = re.findall(pattern, text, re.DOTALL)
            
            for profile_name, profile_id, regions_table in profile_blocks:
                # Parse the source and destination regions
                source_regions: List[str] = []
                destination_regions: Dict[str, List[str]] = {}
                
                # Extract table rows
                rows_pattern = r"([a-z0-9-]+)\s+\n\s*\n((?:[a-z0-9-]+\s*\n\s*\n)+)"
                rows = re.findall(rows_pattern, regions_table)
                
                for source, destinations in rows:
                    source_regions.append(source)
                    destination_list = re.findall(r"([a-z0-9-]+)", destinations)
                    destination_regions[source] = destination_list
                
                if source_regions and destination_regions:
                    profiles[profile_id] = CRISProfile(
                        profile_id=profile_id,
                        profile_name=profile_name.strip(),
                        source_regions=source_regions,
                        destination_regions=destination_regions
                    )
                    logger.debug(f"Parsed CRIS profile data for {profile_id}")
            
            logger.info(f"Successfully parsed {len(profiles)} CRIS profiles")
        except Exception as e:
            logger.error(f"Error parsing CRIS profile table: {str(e)}")
        
        return profiles
    
    def _parse_json_data(self, data: Dict[str, Any]) -> Dict[str, CRISProfile]:
        """
        Parse CRIS profile information from JSON data.
        
        Expected format:
        {
            "profiles": [
                {
                    "profile_id": "us.anthropic.claude-3-sonnet-20240229-v1:0",
                    "profile_name": "US Anthropic Claude 3 Sonnet",
                    "source_regions": ["us-east-1", "us-west-2"],
                    "destination_regions": {
                        "us-east-1": ["us-east-1", "us-west-2"],
                        "us-west-2": ["us-east-1", "us-west-2"]
                    }
                },
                ...
            ]
        }
        
        Args:
            data: JSON data to parse
            
        Returns:
            Dictionary of profile IDs to CRISProfile objects
        """
        profiles: Dict[str, CRISProfile] = {}
        
        try:
            profile_list = data.get("profiles", [])
            for profile_data in profile_list:
                profile_id = profile_data.get("profile_id")
                if not profile_id:
                    logger.warning("Found profile entry without profile_id, skipping")
                    continue
                
                profile_name = profile_data.get("profile_name", "")
                source_regions = profile_data.get("source_regions", [])
                destination_regions = profile_data.get("destination_regions", {})
                
                profiles[profile_id] = CRISProfile(
                    profile_id=profile_id,
                    profile_name=profile_name,
                    source_regions=source_regions,
                    destination_regions=destination_regions
                )
                logger.debug(f"Parsed CRIS profile data for {profile_id}")
            
            logger.info(f"Successfully parsed {len(profiles)} profiles from JSON")
        except Exception as e:
            logger.error(f"Error parsing JSON data: {str(e)}")
        
        return profiles
    
    def get_profile_for_model_region(self, model_id: str, region: str) -> Optional[str]:
        """
        Find a CRIS profile that can be used for the given model and region.
        
        Args:
            model_id: Model ID to check
            region: Source region to check
            
        Returns:
            Profile ID if found, None otherwise
        """
        # Extract model family and version from model ID
        parts = model_id.split('.')
        if len(parts) < 2:
            return None
        
        provider = parts[0]
        model_name_parts = parts[1].split('-')
        if not model_name_parts:
            return None
        
        model_name = model_name_parts[0]
        
        # Look for matching CRIS profile
        for profile_id, profile_data in self._profiles.items():
            if (provider in profile_id and model_name in profile_id and 
                profile_data.can_be_called_from(region)):
                return profile_id
        
        return None
    
    def can_use_cris(self, profile_id: str, source_region: str) -> bool:
        """
        Check if a CRIS profile can be used from a specific region.
        
        Args:
            profile_id: Profile ID to check
            source_region: Source region to check
            
        Returns:
            True if the profile can be used from the region, False otherwise
        """
        if profile_id in self._profiles:
            return self._profiles[profile_id].can_be_called_from(source_region)
        return False
    
    def get_destination_regions(self, profile_id: str, source_region: str) -> List[str]:
        """
        Get the destination regions for a CRIS profile from a specific source region.
        
        Args:
            profile_id: Profile ID to check
            source_region: Source region to check
            
        Returns:
            List of destination regions
        """
        if profile_id in self._profiles:
            return self._profiles[profile_id].get_destination_regions(source_region)
        return []
