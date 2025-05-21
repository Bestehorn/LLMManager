"""
Image content item implementation for Bedrock Converse API.
"""
from typing import Dict, Any, Optional

from src.content.ContentItem import ContentItem
from src.content.ContentTypes import ContentType, SourceType
from src.ConverseFieldConstants import Fields

class ImageContent(ContentItem):
    """Class representing an image content item."""
    
    # Constants for parameter names to maintain consistency
    PARAM_IMAGE_BYTES = "image_bytes"
    PARAM_IMAGE_FORMAT = "image_format"
    PARAM_S3_BUCKET = "s3_bucket"
    PARAM_S3_KEY = "s3_key"
    PARAM_S3_BUCKET_OWNER = "s3_bucket_owner"
    PARAM_URI = "uri"
    
    def __init__(
        self,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
        s3_bucket_owner: Optional[str] = None,
        uri: Optional[str] = None
    ):
        """
        Initialize an image content item.
        
        Args:
            image_bytes: Raw image bytes
            image_format: Format of the image (jpeg, png, etc.)
            s3_bucket: S3 bucket containing the image
            s3_key: S3 key for the image
            s3_bucket_owner: Owner of the S3 bucket
            uri: URI pointing to the image
            
        Raises:
            ValueError: If no source is provided
        """
        self.image_bytes = image_bytes
        self.image_format = image_format
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.s3_bucket_owner = s3_bucket_owner
        self.uri = uri
        
        # Validate that at least one source is provided
        if not any([image_bytes, (s3_bucket and s3_key), uri]):
            raise ValueError("At least one source (bytes, S3, or URI) must be provided")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API requests.
        
        Returns:
            A dictionary representing an image content item
        """
        result = {
            Fields.IMAGE: {
                Fields.FORMAT: self.image_format
            }
        }
        
        # Set the appropriate source
        source = {}
        if self.image_bytes:
            source[Fields.BYTES] = self.image_bytes
        elif self.s3_bucket and self.s3_key:
            s3_location = {
                Fields.BUCKET: self.s3_bucket,
                Fields.KEY: self.s3_key
            }
            if self.s3_bucket_owner:
                s3_location[Fields.BUCKET_OWNER] = self.s3_bucket_owner
            source[Fields.S3_LOCATION] = s3_location
        elif self.uri:
            source[Fields.URI] = self.uri
            
        result[Fields.IMAGE][Fields.SOURCE] = source
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageContent':
        """
        Create from a dictionary.
        
        Args:
            data: Dictionary containing image content data
            
        Returns:
            An ImageContent instance
            
        Raises:
            ValueError: If the dictionary does not contain valid image content data
        """
        if Fields.IMAGE not in data:
            raise ValueError(f"Invalid image content: missing '{Fields.IMAGE}' field")
            
        image_data = data[Fields.IMAGE]
        image_format = image_data.get(Fields.FORMAT, "jpeg")
        
        if Fields.SOURCE not in image_data:
            raise ValueError(f"Invalid image content: missing '{Fields.SOURCE}' field")
            
        source = image_data[Fields.SOURCE]
        
        kwargs = {
            cls.PARAM_IMAGE_FORMAT: image_format
        }
        
        if Fields.BYTES in source:
            kwargs[cls.PARAM_IMAGE_BYTES] = source[Fields.BYTES]
        elif Fields.S3_LOCATION in source:
            s3 = source[Fields.S3_LOCATION]
            kwargs[cls.PARAM_S3_BUCKET] = s3[Fields.BUCKET]
            kwargs[cls.PARAM_S3_KEY] = s3[Fields.KEY]
            if Fields.BUCKET_OWNER in s3:
                kwargs[cls.PARAM_S3_BUCKET_OWNER] = s3[Fields.BUCKET_OWNER]
        elif Fields.URI in source:
            kwargs[cls.PARAM_URI] = source[Fields.URI]
            
        return cls(**kwargs)
