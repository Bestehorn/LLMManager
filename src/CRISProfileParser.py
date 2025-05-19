"""
Parser for AWS Bedrock Cross-Region Inference Service (CRIS) profiles.
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
DEFAULT_CRIS_PROFILES_URL = "https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html"
DEFAULT_CRIS_PROFILES_JSON_CACHE = "cris_profiles_cache.json"

# Constants for JSON fields
FIELD_TIMESTAMP = "timestamp"
FIELD_PROFILES = "profiles"
FIELD_PROFILE_ID = "profile_id"
FIELD_PROFILE_NAME = "profile_name"
FIELD_SOURCE_REGIONS = "source_regions"
FIELD_DESTINATION_REGIONS = "destination_regions"

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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the CRIS profile to a dictionary."""
        return {
            FIELD_PROFILE_ID: self.profile_id,
            FIELD_PROFILE_NAME: self.profile_name,
            FIELD_SOURCE_REGIONS: self.source_regions,
            FIELD_DESTINATION_REGIONS: self.destination_regions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CRISProfile':
        """Create a CRISProfile instance from a dictionary."""
        return cls(
            profile_id=data[FIELD_PROFILE_ID],
            profile_name=data[FIELD_PROFILE_NAME],
            source_regions=data[FIELD_SOURCE_REGIONS],
            destination_regions=data[FIELD_DESTINATION_REGIONS]
        )


class CRISProfileCollection:
    """Collection of CRIS profiles with metadata."""
    
    def __init__(self, timestamp: Optional[int] = None):
        """
        Initialize a CRIS profile collection.
        
        Args:
            timestamp: Unix timestamp when the data was collected, defaults to current time
        """
        self.profiles: Dict[str, CRISProfile] = {}
        self.timestamp = timestamp or int(time.time())
    
    def add_profile(self, profile: CRISProfile) -> None:
        """Add a profile to the collection."""
        self.profiles[profile.profile_id] = profile
    
    def get_profile(self, profile_id: str) -> Optional[CRISProfile]:
        """Get a profile by ID."""
        return self.profiles.get(profile_id)
    
    def get_all_profiles(self) -> Dict[str, CRISProfile]:
        """Get all profiles in the collection."""
        return self.profiles
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the collection to a dictionary."""
        return {
            FIELD_TIMESTAMP: self.timestamp,
            FIELD_PROFILES: {profile_id: profile.to_dict() for profile_id, profile in self.profiles.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CRISProfileCollection':
        """Create a CRISProfileCollection from a dictionary."""
        collection = cls(timestamp=data.get(FIELD_TIMESTAMP))
        
        profiles_data = data.get(FIELD_PROFILES, {})
        for profile_id, profile_data in profiles_data.items():
            collection.add_profile(CRISProfile.from_dict(profile_data))
            
        return collection
    
    def to_json(self, file_path: str) -> None:
        """Save the collection to a JSON file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save CRIS profile collection to {file_path}: {str(e)}")
            raise
    
    @classmethod
    def from_json(cls, file_path: str) -> Optional['CRISProfileCollection']:
        """Load a CRISProfileCollection from a JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load CRIS profile collection from {file_path}: {str(e)}")
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


class CRISProfileParser:
    """
    Parser for AWS Bedrock Cross-Region Inference Service (CRIS) profiles.
    
    This class provides functionality to parse CRIS profile information directly from
    the AWS documentation website or from JSON data.
    """
    
    def __init__(self, log_level: int = logging.INFO):
        """
        Initialize the parser.
        
        Args:
            log_level: Logging level
        """
        self._profile_collection = CRISProfileCollection()
        logging.basicConfig(level=log_level)
    
    @property
    def profiles(self) -> Dict[str, CRISProfile]:
        """Get the parsed CRIS profiles."""
        return self._profile_collection.get_all_profiles()
    
    def clear(self) -> None:
        """Clear all parsed profiles."""
        self._profile_collection = CRISProfileCollection()
    
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
        
        for profile_id, profile_info in profiles.items():
            self._profile_collection.add_profile(profile_info)
            
        return self._profile_collection.get_all_profiles()
    
    def parse_from_url(
        self, 
        url: str = DEFAULT_CRIS_PROFILES_URL,
        cache_file: str = DEFAULT_CRIS_PROFILES_JSON_CACHE,
        save_cache: bool = True
    ) -> Dict[str, CRISProfile]:
        """
        Parse CRIS profile information from a URL and optionally save to cache file.
        
        Args:
            url: URL to fetch CRIS profile information from
            cache_file: Path to save the cached JSON data
            save_cache: Whether to save the parsed data to the cache file
            
        Returns:
            Dictionary of profile IDs to CRISProfile objects
        """
        try:
            import requests
            
            # Fetch HTML content
            logger.info(f"Fetching CRIS profile information from {url}")
            response = requests.get(url)
            response.raise_for_status()
            html_content = response.text
            logger.debug(f"Fetched {len(html_content)} bytes of HTML content")
            
            # Parse HTML content
            profiles = self._parse_cris_profile_table(html_content)
            
            # Update the profile collection
            collection = CRISProfileCollection()
            for profile_id, profile_info in profiles.items():
                collection.add_profile(profile_info)
                
            if save_cache and profiles:
                collection.to_json(cache_file)
                logger.info(f"Saved {len(profiles)} CRIS profiles to {cache_file}")
                
            self._profile_collection = collection
            return self._profile_collection.get_all_profiles()
        except Exception as e:
            logger.error(f"Failed to parse CRIS profile information from URL {url}: {str(e)}")
            return {}
    
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
            
            # Update the profile collection
            for profile_id, profile_info in profiles.items():
                self._profile_collection.add_profile(profile_info)
                
            return self._profile_collection.get_all_profiles()
        except Exception as e:
            logger.error(f"Failed to parse CRIS profile information from JSON: {str(e)}")
            return {}
    
    def _parse_cris_profile_table(self, text: str) -> Dict[str, CRISProfile]:
        """
        Parse CRIS profile information from HTML content.
        
        Args:
            text: HTML content to parse
            
        Returns:
            Dictionary of profile IDs to CRISProfile objects
        """
        profiles: Dict[str, CRISProfile] = {}
        
        try:
            from bs4 import BeautifulSoup, Tag
            soup = BeautifulSoup(text, 'html.parser')
            
            # First, look for all model IDs mentioned anywhere in the document (using a generous regex)
            profile_pattern = r'([a-z]+\.[a-zA-Z0-9\.-]+(?:-[a-zA-Z0-9\.-]+)*(?::[0-9]+)?)'
            all_profile_ids = re.findall(profile_pattern, text)
            unique_profile_ids = set([p for p in all_profile_ids if '.' in p and len(p) > 10])
            logger.debug(f"Found {len(unique_profile_ids)} potential profile IDs in document")
            
            # Region pattern for identification
            region_pattern = r'(us-[a-z]+-[0-9]+|eu-[a-z]+-[0-9]+|ap-[a-z]+-[0-9]+|sa-[a-z]+-[0-9]+|ca-[a-z]+-[0-9]+)'
            
            # Find all code elements which may contain profile IDs
            code_elements = soup.find_all(['code', 'pre'])
            
            # Also find all table rows that have region information
            tables = soup.find_all('table')
            region_tables = []
            
            for table in tables:
                headers_row = table.find('tr')
                if headers_row and isinstance(headers_row, Tag):
                    headers = [th.text.strip().lower() for th in headers_row.find_all('th')]
                    if any(('region' in h for h in headers)):
                        region_tables.append(table)
            
            logger.debug(f"Found {len(region_tables)} tables with region information")
            
            # For each profile ID, try to find associated regions and details
            for profile_id in unique_profile_ids:
                # Skip if it doesn't look like a profile ID
                if not ('.' in profile_id and re.match(r'^[a-z]+\.', profile_id)):
                    continue
                
                logger.debug(f"Analyzing potential profile ID: {profile_id}")
                
                # Find references to this profile ID in the document
                elements = soup.find_all(string=re.compile(re.escape(profile_id)))
                
                if not elements:
                    continue
                
                # Find the profile name by looking for nearby headings
                profile_name = f"Profile for {profile_id}"
                source_regions = []
                destination_regions = {}
                
                # Look for region information in tables near this profile ID
                found_regions = False
                
                for element in elements:
                    if not found_regions:
                        # Find the closest table with region information
                        parent = element.parent
                        if parent:
                            next_table = parent.find_next('table')
                            if next_table:
                                headers_row = next_table.find('tr')
                                if headers_row and isinstance(headers_row, Tag):
                                    headers = [th.text.strip().lower() for th in headers_row.find_all('th')]
                                    
                                    # Check if this looks like a region table
                                    if any(('source' in h for h in headers)) or any(('destination' in h for h in headers)):
                                        source_idx = None
                                        dest_idx = None
                                        
                                        for i, header in enumerate(headers):
                                            if 'source' in header:
                                                source_idx = i
                                            if 'destination' in header:
                                                dest_idx = i
                                        
                                        if source_idx is not None and dest_idx is not None:
                                            rows = next_table.find_all('tr')[1:]  # Skip header row
                                            for row in rows:
                                                if isinstance(row, Tag):
                                                    cells = row.find_all('td')
                                                    if len(cells) > max(source_idx, dest_idx):
                                                        source = cells[source_idx].text.strip()
                                                        dest_text = cells[dest_idx].text.strip()
                                                        
                                                        # Check if these look like AWS regions
                                                        if re.match(region_pattern, source):
                                                            source_regions.append(source)
                                                            dest_regions = re.findall(region_pattern, dest_text)
                                                            destination_regions[source] = dest_regions
                                                            found_regions = True
                
                # If we found region information, create the profile
                if source_regions and destination_regions:
                    # Look for a better profile name near the profile ID
                    for element in elements:
                        current = element.parent
                        heading = None
                        
                        # Look backward for headings
                        while current and not heading:
                            if isinstance(current, Tag):
                                prev_heading = current.find_previous(['h1', 'h2', 'h3', 'h4', 'h5'])
                                if prev_heading and 'profile' in prev_heading.text.lower():
                                    heading = prev_heading
                                    profile_name = heading.text.strip()
                                    break
                            
                            current = current.parent
                    
                    profiles[profile_id] = CRISProfile(
                        profile_id=profile_id,
                        profile_name=profile_name,
                        source_regions=source_regions,
                        destination_regions=destination_regions
                    )
                    logger.info(f"Parsed CRIS profile data for {profile_id}")
            
            # If we still don't have profiles, look more aggressively for data
            if not profiles:
                logger.debug("No profiles found through standard parsing, trying alternative approach")
                
                # Look for any tables with source and destination regions
                for table in region_tables:
                    headers_row = table.find('tr')
                    if headers_row and isinstance(headers_row, Tag):
                        headers = [th.text.strip().lower() for th in headers_row.find_all('th')]
                        source_idx = None
                        dest_idx = None
                        
                        for i, header in enumerate(headers):
                            if 'source' in header:
                                source_idx = i
                            if 'destination' in header:
                                dest_idx = i
                        
                        if source_idx is not None and dest_idx is not None:
                            # Look for the nearest profile ID before this table
                            prev_text = ''
                            current = table.previous_sibling
                            
                            while current and len(prev_text) < 1000:
                                if hasattr(current, 'text'):
                                    prev_text = current.text + prev_text
                                current = current.previous_sibling
                            
                            # Extract profile IDs from this text
                            nearby_ids = re.findall(profile_pattern, prev_text)
                            likely_id = None
                            
                            for pid in nearby_ids:
                                if '.' in pid and len(pid) > 10 and re.match(r'^[a-z]+\.', pid):
                                    likely_id = pid
                                    break
                            
                            if likely_id:
                                # Extract heading for profile name
                                profile_name = f"Profile for {likely_id}"
                                current = table
                                heading = None
                                
                                while current and not heading:
                                    prev_heading = current.find_previous(['h1', 'h2', 'h3', 'h4'])
                                    if prev_heading:
                                        heading = prev_heading
                                        profile_name = heading.text.strip()
                                        break
                                    
                                    if hasattr(current, 'parent'):
                                        current = current.parent
                                    else:
                                        break
                                
                                # Extract region data
                                source_regions = []
                                destination_regions = {}
                                
                                rows = table.find_all('tr')[1:]  # Skip header row
                                for row in rows:
                                    if isinstance(row, Tag):
                                        cells = row.find_all('td')
                                        if len(cells) > max(source_idx, dest_idx):
                                            source = cells[source_idx].text.strip()
                                            dest_text = cells[dest_idx].text.strip()
                                            
                                            if re.match(region_pattern, source):
                                                source_regions.append(source)
                                                dest_regions = re.findall(region_pattern, dest_text)
                                                destination_regions[source] = dest_regions
                                
                                if source_regions and destination_regions and likely_id not in profiles:
                                    profiles[likely_id] = CRISProfile(
                                        profile_id=likely_id,
                                        profile_name=profile_name,
                                        source_regions=source_regions,
                                        destination_regions=destination_regions
                                    )
                                    logger.info(f"Parsed CRIS profile data for {likely_id} using alternative approach")
            
            # Check if we have the proper number of profiles
            if len(profiles) == 0:
                logger.warning("No CRIS profiles found in the HTML content")
            else:
                logger.info(f"Successfully parsed {len(profiles)} CRIS profiles")
                
        except ImportError:
            logger.error("BeautifulSoup is required for HTML parsing")
        except Exception as e:
            logger.error(f"Error parsing CRIS profile table: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
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
            profile_list = data.get(FIELD_PROFILES, {})
            if isinstance(profile_list, list):
                for profile_data in profile_list:
                    profile_id = profile_data.get(FIELD_PROFILE_ID)
                    if not profile_id:
                        logger.warning("Found profile entry without profile_id, skipping")
                        continue
                    
                    profile_name = profile_data.get(FIELD_PROFILE_NAME, "")
                    source_regions = profile_data.get(FIELD_SOURCE_REGIONS, [])
                    destination_regions = profile_data.get(FIELD_DESTINATION_REGIONS, {})
                    
                    profiles[profile_id] = CRISProfile(
                        profile_id=profile_id,
                        profile_name=profile_name,
                        source_regions=source_regions,
                        destination_regions=destination_regions
                    )
                    logger.debug(f"Parsed CRIS profile data for {profile_id}")
            else:
                # Handle case where profiles is a dictionary mapping profile_id to profile data
                for profile_id, profile_data in profile_list.items():
                    profile_name = profile_data.get(FIELD_PROFILE_NAME, "")
                    source_regions = profile_data.get(FIELD_SOURCE_REGIONS, [])
                    destination_regions = profile_data.get(FIELD_DESTINATION_REGIONS, {})
                    
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
    
    def get_cris_profile_collection(self) -> CRISProfileCollection:
        """Get the current CRIS profile collection."""
        return self._profile_collection
    
    def set_cris_profile_collection(self, collection: CRISProfileCollection) -> None:
        """Set the current CRIS profile collection."""
        self._profile_collection = collection
    
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
        
        profiles = self._profile_collection.get_all_profiles()
        
        # Look for matching CRIS profile
        for profile_id, profile_data in profiles.items():
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
        profiles = self._profile_collection.get_all_profiles()
        if profile_id in profiles:
            return profiles[profile_id].can_be_called_from(source_region)
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
        profiles = self._profile_collection.get_all_profiles()
        if profile_id in profiles:
            return profiles[profile_id].get_destination_regions(source_region)
        return []
