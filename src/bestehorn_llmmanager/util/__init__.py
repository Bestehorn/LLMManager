"""
Utility modules for LLMManager.

This package contains general-purpose utilities that can be used across
different components of the LLMManager system.
"""

from .file_type_detector import FileTypeDetector, DetectionResult

__all__ = [
    "FileTypeDetector",
    "DetectionResult"
]
