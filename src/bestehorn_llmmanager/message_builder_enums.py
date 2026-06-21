"""
Enums for the ConverseMessageBuilder system.
Contains all enumerated values used in message construction.
"""

from enum import Enum

from .bedrock.models.llm_manager_constants import ConverseAPIFields


class RolesEnum(str, Enum):
    """
    Enumeration of valid message roles for the Converse API.

    Values map directly to the ConverseAPIFields constants to ensure consistency.
    """

    USER = ConverseAPIFields.ROLE_USER
    ASSISTANT = ConverseAPIFields.ROLE_ASSISTANT

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value


class ImageFormatEnum(str, Enum):
    """
    Enumeration of supported image formats for the Converse API.

    These formats are compatible with AWS Bedrock image processing capabilities.
    """

    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"


class DocumentFormatEnum(str, Enum):
    """
    Enumeration of supported document formats for the Converse API.

    These formats are compatible with AWS Bedrock document processing capabilities.
    """

    PDF = "pdf"
    CSV = "csv"
    DOC = "doc"
    DOCX = "docx"
    XLS = "xls"
    XLSX = "xlsx"
    HTML = "html"
    TXT = "txt"
    MD = "md"


class VideoFormatEnum(str, Enum):
    """
    Enumeration of supported video formats for the Converse API.

    These values match the AWS Bedrock Converse ``VideoBlock`` ``format`` enum exactly
    (mkv, mov, mp4, webm, flv, mpeg, mpg, wmv, three_gp). ``avi`` is intentionally absent:
    Bedrock does not accept it, so sending it always produced a rejected request.
    """

    MP4 = "mp4"
    MOV = "mov"
    WEBM = "webm"
    MKV = "mkv"
    FLV = "flv"
    MPEG = "mpeg"
    MPG = "mpg"
    WMV = "wmv"
    THREE_GP = "three_gp"


class DetectionMethodEnum(str, Enum):
    """
    Enumeration of file type detection methods used by FileTypeDetector.

    Used for logging and debugging purposes to indicate how format was determined.
    """

    EXTENSION = "extension"
    CONTENT = "content"
    COMBINED = "combined"
    MANUAL = "manual"


class ToolResultStatusEnum(str, Enum):
    """
    Enumeration of valid tool-result statuses for the Converse API.

    Set on a ``toolResult`` block to tell the model whether the tool call succeeded or
    failed. Values map directly to the Converse ``ToolResultBlock.status`` valid values
    (``success`` | ``error``). Supported by Amazon Nova and Anthropic Claude 3/4 models.
    """

    SUCCESS = ConverseAPIFields.TOOL_RESULT_STATUS_SUCCESS
    ERROR = ConverseAPIFields.TOOL_RESULT_STATUS_ERROR

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value
