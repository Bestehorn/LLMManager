"""
Enhanced BeautifulSoup-based parser for Amazon Bedrock model documentation.
Extends the base parser to detect CRIS-only region markers (*).
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bs4 import Tag

from ..models.aws_regions import normalize_region_name
from ..models.data_structures import BedrockModelInfo
from ..models.unified_constants import RegionMarkers
from .bedrock_parser import BedrockHTMLParser


class EnhancedBedrockHTMLParser(BedrockHTMLParser):
    """
    Enhanced BeautifulSoup-based parser that detects CRIS-only region markers.

    Extends the base BedrockHTMLParser to handle region cells that contain
    asterisk (*) markers indicating CRIS-only availability.
    """

    def __init__(self) -> None:
        """Initialize the enhanced Bedrock HTML parser."""
        super().__init__()
        self._cris_only_regions_detected = 0

    def _extract_regions_from_cell(self, cells: List[Tag], column: str) -> List[str]:
        """
        Extract region list from a table cell, preserving CRIS-only markers.

        Args:
            cells: List of cell elements
            column: Column name to extract from

        Returns:
            List of region names (with * preserved for CRIS-only regions)
        """
        if column not in self._column_indices:
            return []

        cell_index = self._column_indices[column]
        if cell_index >= len(cells):
            return []

        cell = cells[cell_index]
        regions = []

        # Look for paragraph tags first (AWS docs use <p> for each region)
        paragraphs = [p for p in cell.find_all("p") if isinstance(p, Tag)]
        if paragraphs:
            for p in paragraphs:
                region_text = p.get_text(strip=True)
                if region_text:
                    processed_region = self._process_region_text(region_text=region_text)
                    if processed_region:
                        regions.append(processed_region)
        else:
            # Fallback to comma-separated text
            text = cell.get_text(strip=True)
            if text:
                parts = [part.strip() for part in text.split(RegionMarkers.REGION_SEPARATOR)]
                for part in parts:
                    processed_region = self._process_region_text(region_text=part)
                    if processed_region:
                        regions.append(processed_region)

        return list(dict.fromkeys(regions))  # Remove duplicates while preserving order

    def _process_region_text(self, region_text: str) -> Optional[str]:
        """
        Process region text to handle CRIS-only markers and normalization.

        Args:
            region_text: Raw region text from HTML

        Returns:
            Processed region string or None if invalid
        """
        if not region_text:
            return None

        # Check for CRIS-only marker
        is_cris_only = region_text.endswith(RegionMarkers.CRIS_ONLY_MARKER)

        if is_cris_only:
            # Remove the marker for normalization
            clean_text = region_text.rstrip(RegionMarkers.CRIS_ONLY_MARKER).strip()
            self._cris_only_regions_detected += 1

            # Normalize the region name
            normalized_region = normalize_region_name(region_text=clean_text)
            if normalized_region:
                # Add the marker back to indicate CRIS-only
                return f"{normalized_region}{RegionMarkers.CRIS_ONLY_MARKER}"
        else:
            # Regular region normalization
            normalized_region = normalize_region_name(region_text=region_text)
            if normalized_region:
                return normalized_region

        return None

    def _extract_model_from_row(self, row: Tag) -> Tuple[Optional[str], Optional[BedrockModelInfo]]:
        """
        Extract model information from a single table row with CRIS detection.

        Args:
            row: BeautifulSoup row element

        Returns:
            Tuple of (model_name, model_info) or (None, None) if extraction fails
        """
        model_name, model_info = super()._extract_model_from_row(row=row)

        if model_name and model_info:
            # Log if any CRIS-only regions were detected for this model
            cris_only_count = sum(
                1
                for region in model_info.regions_supported
                if region.endswith(RegionMarkers.CRIS_ONLY_MARKER)
            )

            if cris_only_count > 0:
                self._logger.debug(f"Model {model_name} has {cris_only_count} CRIS-only regions")

        return model_name, model_info

    def parse(self, file_path: Path) -> Dict[str, BedrockModelInfo]:
        """
        Parse Bedrock documentation HTML file with enhanced CRIS detection.

        Args:
            file_path: Path to the HTML documentation file

        Returns:
            Dictionary mapping model names to model information

        Raises:
            ParsingError: If parsing fails
            FileNotFoundError: If the input file doesn't exist
        """
        # Reset CRIS detection counter
        self._cris_only_regions_detected = 0

        # Call parent parsing method
        models = super().parse(file_path=file_path)

        # Log CRIS detection statistics
        if self._cris_only_regions_detected > 0:
            self._logger.info(
                f"Detected {self._cris_only_regions_detected} CRIS-only region markers during parsing"
            )

        return models

    def get_cris_detection_stats(self) -> Dict[str, int]:
        """
        Get statistics about CRIS-only region detection.

        Returns:
            Dictionary with detection statistics
        """
        return {"cris_only_regions_detected": self._cris_only_regions_detected}
