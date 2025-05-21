"""
Text content item implementation for Bedrock Converse API.
"""
from typing import Dict, Any

from src.content.ContentItem import ContentItem
from src.ConverseFieldConstants import Fields

class TextContent(ContentItem):
    """Class representing a text content item."""
    
    # Constants for parameter names to maintain consistency
    PARAM_TEXT = "text"
    
    def __init__(self, text: str):
        """
        Initialize a text content item.
        
        Args:
            text: The text content
        """
        self.text = text
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API requests.
        
        Returns:
            A dictionary representing a text content item
        """
        return {
            Fields.TEXT: self.text
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextContent':
        """
        Create from a dictionary.
        
        Args:
            data: Dictionary containing text content data
            
        Returns:
            A TextContent instance
            
        Raises:
            ValueError: If the dictionary does not contain valid text content data
        """
        if Fields.TEXT not in data:
            raise ValueError(f"Invalid text content: missing '{Fields.TEXT}' field")
        
        return cls(data[Fields.TEXT])
