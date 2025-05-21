"""
ContentBuilder class implementation for building complex multimodal messages.
"""
from typing import List, Dict, Any, Optional

from src.content.ContentItem import ContentItem
from src.content.items.TextContent import TextContent
from src.content.items.ImageContent import ImageContent
from src.content.items.DocumentContent import DocumentContent
from src.content.items.VideoContent import VideoContent
from src.ConverseFieldConstants import Fields, Roles

class ContentBuilder:
    """Builder for creating complex messages with multiple content items."""
    
    def __init__(self):
        """Initialize an empty content builder."""
        self.content_items: List[ContentItem] = []
    
    def add_text(self, text: str) -> 'ContentBuilder':
        """
        Add text content to the message.
        
        Args:
            text: Text content
            
        Returns:
            Self for method chaining
        """
        self.content_items.append(TextContent(text))
        return self
        
    def add_image(
        self,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
        s3_bucket_owner: Optional[str] = None,
        uri: Optional[str] = None
    ) -> 'ContentBuilder':
        """
        Add image content to the message.
        
        Args:
            image_bytes: Raw image bytes
            image_format: Format of the image
            s3_bucket: S3 bucket containing the image
            s3_key: S3 key for the image
            s3_bucket_owner: Owner of the S3 bucket
            uri: URI pointing to the image
            
        Returns:
            Self for method chaining
        """
        self.content_items.append(ImageContent(
            image_bytes=image_bytes,
            image_format=image_format,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            s3_bucket_owner=s3_bucket_owner,
            uri=uri
        ))
        return self
    
    def add_document(
        self,
        document_name: str,
        document_format: str,
        document_bytes: Optional[bytes] = None,
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
        s3_bucket_owner: Optional[str] = None,
        uri: Optional[str] = None
    ) -> 'ContentBuilder':
        """
        Add document content to the message.
        
        Args:
            document_name: Name of the document
            document_format: Format of the document
            document_bytes: Raw document bytes
            s3_bucket: S3 bucket containing the document
            s3_key: S3 key for the document
            s3_bucket_owner: Owner of the S3 bucket
            uri: URI pointing to the document
            
        Returns:
            Self for method chaining
        """
        self.content_items.append(DocumentContent(
            document_name=document_name,
            document_format=document_format,
            document_bytes=document_bytes,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            s3_bucket_owner=s3_bucket_owner,
            uri=uri
        ))
        return self
    
    def add_video(
        self,
        video_format: str,
        video_bytes: Optional[bytes] = None,
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
        s3_bucket_owner: Optional[str] = None,
        uri: Optional[str] = None
    ) -> 'ContentBuilder':
        """
        Add video content to the message.
        
        Args:
            video_format: Format of the video
            video_bytes: Raw video bytes
            s3_bucket: S3 bucket containing the video
            s3_key: S3 key for the video
            s3_bucket_owner: Owner of the S3 bucket
            uri: URI pointing to the video
            
        Returns:
            Self for method chaining
        """
        self.content_items.append(VideoContent(
            video_format=video_format,
            video_bytes=video_bytes,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            s3_bucket_owner=s3_bucket_owner,
            uri=uri
        ))
        return self
    
    def add_content_item(self, content_item: ContentItem) -> 'ContentBuilder':
        """
        Add a pre-configured content item to the message.
        
        Args:
            content_item: A ContentItem instance
            
        Returns:
            Self for method chaining
        """
        self.content_items.append(content_item)
        return self
    
    def build(self, role: str = Roles.USER) -> Dict[str, Any]:
        """
        Build the final message object with all content items.
        
        Args:
            role: Role of the message sender
            
        Returns:
            A message object compatible with the Converse API
        """
        return {
            Fields.ROLE: role,
            Fields.CONTENT: [item.to_dict() for item in self.content_items]
        }
