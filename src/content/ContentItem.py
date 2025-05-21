"""
Base class for content items in Bedrock Converse API.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ContentItem(ABC):
    """Base class for all content items that can be included in messages."""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the content item to a dictionary for API requests.
        
        Returns:
            A dictionary representation of the content item
        """
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentItem':
        """
        Create a content item from a dictionary.
        
        Args:
            data: Dictionary containing content item data
            
        Returns:
            A ContentItem instance
            
        Raises:
            ValueError: If the dictionary does not contain valid content item data
        """
        pass
