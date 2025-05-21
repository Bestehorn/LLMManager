"""
Video content item implementation for Bedrock Converse API.
"""
from typing import Dict, Any, Optional

from src.content.ContentItem import ContentItem
from src.content.ContentTypes import ContentType, SourceType
from src.ConverseFieldConstants import Fields

class VideoContent(ContentItem):
    """Class representing a video content item."""
    
    # Constants for parameter names to maintain consistency
    PARAM_VIDEO_FORMAT = "video_format"
    PARAM_VIDEO_BYTES = "video_bytes"
    PARAM_S3_BUCKET = "s3_bucket"
    PARAM_S3_KEY = "s3_key"
    PARAM_S3_BUCKET_OWNER = "s3_bucket_owner"
    PARAM_URI = "uri"
    
    def __init__(
        self,
        video_format: str,
        video_bytes: Optional[bytes] = None,
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
        s3_bucket_owner: Optional[str] = None,
        uri: Optional[str] = None
    ):
        """
        Initialize a video content item.
        
        Args:
            video_format: Format of the video (mp4, mov, etc.)
            video_bytes: Raw video bytes
            s3_bucket: S3 bucket containing the video
            s3_key: S3 key for the video
            s3_bucket_owner: Owner of the S3 bucket
            uri: URI pointing to the video
            
        Raises:
            ValueError: If no source is provided
        """
        self.video_format = video_format
        self.video_bytes = video_bytes
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.s3_bucket_owner = s3_bucket_owner
        self.uri = uri
        
        # Validate that at least one source is provided
        if not any([video_bytes, (s3_bucket and s3_key), uri]):
            raise ValueError("At least one source (bytes, S3, or URI) must be provided")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API requests.
        
        Returns:
            A dictionary representing a video content item
        """
        result = {
            Fields.VIDEO: {
                Fields.FORMAT: self.video_format
            }
        }
        
        # Set the appropriate source
        source = {}
        if self.video_bytes:
            source[Fields.BYTES] = self.video_bytes
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
            
        result[Fields.VIDEO][Fields.SOURCE] = source
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoContent':
        """
        Create from a dictionary.
        
        Args:
            data: Dictionary containing video content data
            
        Returns:
            A VideoContent instance
            
        Raises:
            ValueError: If the dictionary does not contain valid video content data
        """
        if Fields.VIDEO not in data:
            raise ValueError(f"Invalid video content: missing '{Fields.VIDEO}' field")
            
        video_data = data[Fields.VIDEO]
        
        if Fields.FORMAT not in video_data:
            raise ValueError(f"Invalid video content: missing '{Fields.FORMAT}' field")
            
        if Fields.SOURCE not in video_data:
            raise ValueError(f"Invalid video content: missing '{Fields.SOURCE}' field")
            
        video_format = video_data[Fields.FORMAT]
        source = video_data[Fields.SOURCE]
        
        kwargs = {
            cls.PARAM_VIDEO_FORMAT: video_format
        }
        
        if Fields.BYTES in source:
            kwargs[cls.PARAM_VIDEO_BYTES] = source[Fields.BYTES]
        elif Fields.S3_LOCATION in source:
            s3 = source[Fields.S3_LOCATION]
            kwargs[cls.PARAM_S3_BUCKET] = s3[Fields.BUCKET]
            kwargs[cls.PARAM_S3_KEY] = s3[Fields.KEY]
            if Fields.BUCKET_OWNER in s3:
                kwargs[cls.PARAM_S3_BUCKET_OWNER] = s3[Fields.BUCKET_OWNER]
        elif Fields.URI in source:
            kwargs[cls.PARAM_URI] = source[Fields.URI]
            
        return cls(**kwargs)
