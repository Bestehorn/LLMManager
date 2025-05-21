"""
Document content item implementation for Bedrock Converse API.
"""
from typing import Dict, Any, Optional

from src.content.ContentItem import ContentItem
from src.content.ContentTypes import ContentType, SourceType
from src.ConverseFieldConstants import Fields

class DocumentContent(ContentItem):
    """Class representing a document content item."""
    
    # Constants for parameter names to maintain consistency
    PARAM_DOCUMENT_NAME = "document_name"
    PARAM_DOCUMENT_FORMAT = "document_format"
    PARAM_DOCUMENT_BYTES = "document_bytes"
    PARAM_S3_BUCKET = "s3_bucket"
    PARAM_S3_KEY = "s3_key"
    PARAM_S3_BUCKET_OWNER = "s3_bucket_owner"
    PARAM_URI = "uri"
    
    def __init__(
        self,
        document_name: str,
        document_format: str,
        document_bytes: Optional[bytes] = None,
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
        s3_bucket_owner: Optional[str] = None,
        uri: Optional[str] = None
    ):
        """
        Initialize a document content item.
        
        Args:
            document_name: Name of the document
            document_format: Format of the document (pdf, docx, etc.)
            document_bytes: Raw document bytes
            s3_bucket: S3 bucket containing the document
            s3_key: S3 key for the document
            s3_bucket_owner: Owner of the S3 bucket
            uri: URI pointing to the document
            
        Raises:
            ValueError: If no source is provided
        """
        self.document_name = document_name
        self.document_format = document_format
        self.document_bytes = document_bytes
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.s3_bucket_owner = s3_bucket_owner
        self.uri = uri
        
        # Validate that at least one source is provided
        if not any([document_bytes, (s3_bucket and s3_key), uri]):
            raise ValueError("At least one source (bytes, S3, or URI) must be provided")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API requests.
        
        Returns:
            A dictionary representing a document content item
        """
        result = {
            Fields.DOCUMENT: {
                Fields.NAME: self.document_name,
                Fields.FORMAT: self.document_format
            }
        }
        
        # Set the appropriate source
        source = {}
        if self.document_bytes:
            source[Fields.BYTES] = self.document_bytes
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
            
        result[Fields.DOCUMENT][Fields.SOURCE] = source
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentContent':
        """
        Create from a dictionary.
        
        Args:
            data: Dictionary containing document content data
            
        Returns:
            A DocumentContent instance
            
        Raises:
            ValueError: If the dictionary does not contain valid document content data
        """
        if Fields.DOCUMENT not in data:
            raise ValueError(f"Invalid document content: missing '{Fields.DOCUMENT}' field")
            
        doc_data = data[Fields.DOCUMENT]
        
        if Fields.NAME not in doc_data:
            raise ValueError(f"Invalid document content: missing '{Fields.NAME}' field")
            
        if Fields.FORMAT not in doc_data:
            raise ValueError(f"Invalid document content: missing '{Fields.FORMAT}' field")
            
        if Fields.SOURCE not in doc_data:
            raise ValueError(f"Invalid document content: missing '{Fields.SOURCE}' field")
            
        document_name = doc_data[Fields.NAME]
        document_format = doc_data[Fields.FORMAT]
        source = doc_data[Fields.SOURCE]
        
        kwargs = {
            cls.PARAM_DOCUMENT_NAME: document_name,
            cls.PARAM_DOCUMENT_FORMAT: document_format
        }
        
        if Fields.BYTES in source:
            kwargs[cls.PARAM_DOCUMENT_BYTES] = source[Fields.BYTES]
        elif Fields.S3_LOCATION in source:
            s3 = source[Fields.S3_LOCATION]
            kwargs[cls.PARAM_S3_BUCKET] = s3[Fields.BUCKET]
            kwargs[cls.PARAM_S3_KEY] = s3[Fields.KEY]
            if Fields.BUCKET_OWNER in s3:
                kwargs[cls.PARAM_S3_BUCKET_OWNER] = s3[Fields.BUCKET_OWNER]
        elif Fields.URI in source:
            kwargs[cls.PARAM_URI] = source[Fields.URI]
            
        return cls(**kwargs)
