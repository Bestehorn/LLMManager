"""
File type detection utilities.

This package provides comprehensive file type detection using multiple strategies
including magic bytes analysis and file extension mapping.
"""

from ...message_builder_enums import DetectionMethodEnum
from .base_detector import BaseDetector, DetectionResult
from .file_type_detector import FileTypeDetector

__all__ = ["BaseDetector", "DetectionResult", "DetectionMethodEnum", "FileTypeDetector"]
