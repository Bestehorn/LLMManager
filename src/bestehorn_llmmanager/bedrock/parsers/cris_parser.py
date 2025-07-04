"""
HTML parser for Amazon Bedrock CRIS (Cross-Region Inference) documentation.
Extracts model information from AWS documentation HTML using BeautifulSoup.
This parser fixes the regional overwrite bug by properly handling multiple regional variants.
"""

import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from ..models.cris_constants import (
    CRISErrorMessages,
    CRISHTMLAttributes,
    CRISHTMLSelectors,
    CRISLogMessages,
    CRISRegionPrefixes,
    CRISTableColumns,
)
from ..models.cris_structures import CRISInferenceProfile, CRISModelInfo
from .base_parser import ParsingError


class BaseCRISParser(ABC):
    """
    Abstract base class for CRIS documentation parsers.
    Provides common functionality and enforces the CRIS parser interface.
    """

    @abstractmethod
    def parse(self, file_path: Path) -> Dict[str, CRISModelInfo]:
        """
        Parse CRIS documentation file and extract model information.

        Args:
            file_path: Path to the documentation file to parse

        Returns:
            Dictionary mapping model names to CRIS model information

        Raises:
            ParsingError: If parsing fails
            FileNotFoundError: If the input file doesn't exist
        """
        pass

    def _validate_file_exists(self, file_path: Path) -> None:
        """
        Validate that the input file exists and is readable.

        Args:
            file_path: Path to validate

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file isn't readable
        """
        if not file_path.exists():
            raise FileNotFoundError(f"CRIS documentation file not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Just try to read the first byte to check permissions
                f.read(1)
        except PermissionError as e:
            raise PermissionError(f"Cannot read CRIS file: {file_path}") from e
        except UnicodeDecodeError as e:
            raise ValueError(f"CRIS file is not valid UTF-8: {file_path}") from e


class CRISRegionExtractor:
    """
    Helper class for extracting region prefixes from CRIS model headers.

    Provides methods to identify and extract regional information from
    model names while maintaining the clean model name.
    """

    @staticmethod
    def extract_region_and_model_name(header: str) -> Tuple[Optional[str], str]:
        """
        Extract region prefix and clean model name from a header string.

        Args:
            header: The original header string from the expandable section

        Returns:
            Tuple of (region_prefix, clean_model_name)
            - region_prefix: The regional identifier ('US', 'EU', 'APAC') or None
            - clean_model_name: The model name without regional prefix
        """
        if not header:
            return None, ""

        clean_header = header.strip()

        # Check for each known region prefix
        for prefix_constant, identifier in [
            (CRISRegionPrefixes.US_PREFIX, CRISRegionPrefixes.US_IDENTIFIER),
            (CRISRegionPrefixes.EU_PREFIX, CRISRegionPrefixes.EU_IDENTIFIER),
            (CRISRegionPrefixes.APAC_PREFIX, CRISRegionPrefixes.APAC_IDENTIFIER),
        ]:
            if clean_header.startswith(prefix_constant):
                clean_name = clean_header[len(prefix_constant) :].strip()
                return identifier, clean_name

        # No regional prefix found - return None and original name
        return None, clean_header

    @staticmethod
    def is_regional_header(header: str) -> bool:
        """
        Check if a header contains a regional prefix.

        Args:
            header: The header string to check

        Returns:
            True if header contains a known regional prefix
        """
        region_prefix, _ = CRISRegionExtractor.extract_region_and_model_name(header=header)
        return region_prefix is not None


class CRISRegionalVariant:
    """
    Represents a single regional variant of a CRIS model.

    This class stores the region-specific information for a model variant
    including its inference profile ID and region mappings.
    """

    def __init__(
        self, region_prefix: str, inference_profile_id: str, region_mappings: Dict[str, List[str]]
    ) -> None:
        """
        Initialize a regional variant.

        Args:
            region_prefix: Regional identifier (e.g., 'US', 'EU', 'APAC')
            inference_profile_id: The region-specific inference profile ID
            region_mappings: Dictionary mapping source regions to destination regions
        """
        self.region_prefix = region_prefix
        self.inference_profile_id = inference_profile_id
        self.region_mappings = region_mappings


class CRISHTMLParser(BaseCRISParser):
    """
    Parser for CRIS documentation HTML.

    Extracts Cross-Region Inference model information from AWS Bedrock documentation
    by parsing expandable sections containing model details, inference profile IDs,
    and region mapping tables.

    This parser fixes the regional overwrite bug by collecting all regional variants
    and merging them appropriately before creating the final CRISModelInfo objects.
    """

    def __init__(self) -> None:
        """Initialize the CRIS HTML parser with logging."""
        self._logger = logging.getLogger(__name__)

    def parse(self, file_path: Path) -> Dict[str, CRISModelInfo]:
        """
        Parse CRIS HTML documentation and extract model information.

        This method fixes the regional overwrite bug by collecting all regional variants
        first, then creating merged CRISModelInfo objects that preserve all regional data.

        Args:
            file_path: Path to the CRIS HTML file to parse

        Returns:
            Dictionary mapping model names to CRISModelInfo objects

        Raises:
            ParsingError: If parsing fails
            FileNotFoundError: If the input file doesn't exist
        """
        self._validate_file_exists(file_path=file_path)
        self._logger.info(CRISLogMessages.PARSING_STARTED)

        try:
            # Read and parse HTML content
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            soup = BeautifulSoup(markup=html_content, features="html.parser")

            # Find all expandable sections
            expandable_sections = soup.find_all(
                name=CRISHTMLSelectors.EXPANDABLE_SECTION,
                attrs={CRISHTMLAttributes.VARIANT: "container"},
            )

            if not expandable_sections:
                raise ParsingError("No expandable sections found in CRIS documentation")

            # Step 1: Collect all regional variants grouped by model name
            # This is the key fix - we collect all variants before creating final objects
            regional_variants_by_model = self._collect_regional_variants(
                expandable_sections=expandable_sections
            )

            # Step 2: Create merged CRISModelInfo objects from collected variants
            cris_models = self._create_merged_model_info_objects(
                regional_variants_by_model=regional_variants_by_model
            )

            if not cris_models:
                raise ParsingError("No valid CRIS models found in documentation")

            self._logger.info(
                CRISLogMessages.PARSING_COMPLETED.format(model_count=len(cris_models))
            )
            return cris_models

        except Exception as e:
            error_msg = CRISLogMessages.PARSING_ERROR.format(error=str(e))
            self._logger.error(error_msg)
            raise ParsingError(error_msg) from e

    def _collect_regional_variants(
        self, expandable_sections: Any
    ) -> Dict[str, List[CRISRegionalVariant]]:
        """
        Collect all regional variants grouped by clean model name.

        This is the core fix for the regional overwrite bug. Instead of immediately
        creating CRISModelInfo objects that overwrite each other, we collect all
        variants first and then merge them appropriately.

        Args:
            expandable_sections: BeautifulSoup ResultSet of expandable section elements

        Returns:
            Dictionary mapping clean model names to lists of their regional variants
        """
        regional_variants_by_model: Dict[str, List[CRISRegionalVariant]] = {}

        for section_element in expandable_sections:
            if not isinstance(section_element, Tag):
                continue

            try:
                variant = self._parse_section_to_variant(section=section_element)
                if variant:
                    model_name = self._extract_clean_model_name(section=section_element)
                    if model_name:
                        # Initialize model variants list if needed
                        if model_name not in regional_variants_by_model:
                            regional_variants_by_model[model_name] = []

                        # Add variant to model's collection (no overwriting!)
                        regional_variants_by_model[model_name].append(variant)

                        self._logger.debug(
                            CRISLogMessages.INFERENCE_PROFILE_ADDED.format(
                                profile_id=variant.inference_profile_id, model_name=model_name
                            )
                        )

            except Exception as e:
                section_id = section_element.get(CRISHTMLAttributes.ID, "unknown")
                self._logger.warning(CRISLogMessages.SECTION_SKIPPED.format(section_id=section_id))
                self._logger.debug(f"Section parsing error: {str(e)}")

        return regional_variants_by_model

    def _parse_section_to_variant(self, section: Tag) -> Optional[CRISRegionalVariant]:
        """
        Parse an expandable section into a regional variant.

        Args:
            section: BeautifulSoup Tag representing the expandable section

        Returns:
            CRISRegionalVariant if parsing succeeds, None if section should be skipped

        Raises:
            ParsingError: If section is malformed
        """
        section_id = section.get(CRISHTMLAttributes.ID, "unknown")

        # Extract header and determine regional prefix
        header_attr = section.get(CRISHTMLAttributes.HEADER)
        if not header_attr:
            raise ParsingError(CRISErrorMessages.MALFORMED_SECTION.format(section_id=section_id))

        header_str = self._normalize_header_attribute(header_attr=header_attr)
        region_prefix, _ = CRISRegionExtractor.extract_region_and_model_name(header=header_str)

        # Extract inference profile ID
        inference_profile_id = self._extract_inference_profile_id(section=section)
        if not inference_profile_id:
            # Try fallback extraction from section ID
            inference_profile_id = self._extract_profile_from_section_id(section_id=section_id)
            if not inference_profile_id:
                raise ParsingError(
                    CRISErrorMessages.MISSING_INFERENCE_PROFILE.format(section_id=section_id)
                )

        # Parse region mapping table
        region_mappings = self._parse_region_mapping_table(section=section)
        if not region_mappings:
            raise ParsingError(CRISErrorMessages.MISSING_REGION_TABLE.format(section_id=section_id))

        return CRISRegionalVariant(
            region_prefix=region_prefix or "GLOBAL",  # Default for non-regional models
            inference_profile_id=inference_profile_id,
            region_mappings=region_mappings,
        )

    def _create_merged_model_info_objects(
        self, regional_variants_by_model: Dict[str, List[CRISRegionalVariant]]
    ) -> Dict[str, CRISModelInfo]:
        """
        Create CRISModelInfo objects with properly structured inference profiles.

        This method takes the collected regional variants and creates the final
        CRISModelInfo objects with separate inference profiles for each variant.

        Args:
            regional_variants_by_model: Variants grouped by model name

        Returns:
            Dictionary mapping model names to CRISModelInfo objects with structured inference profiles
        """
        cris_models = {}

        for model_name, variants in regional_variants_by_model.items():
            if not variants:  # Skip models with no variants
                continue

            try:
                # Create inference profiles dictionary from variants
                inference_profiles = self._create_inference_profiles_from_variants(
                    variants=variants
                )

                # Create the final CRISModelInfo object with proper structure
                model_info = CRISModelInfo(
                    model_name=model_name, inference_profiles=inference_profiles
                )

                cris_models[model_name] = model_info

                self._logger.debug(CRISLogMessages.SECTION_PARSED.format(model_name=model_name))

            except Exception as e:
                self._logger.warning(f"Failed to create model info for {model_name}: {str(e)}")

        return cris_models

    def _create_inference_profiles_from_variants(
        self, variants: List[CRISRegionalVariant]
    ) -> Dict[str, CRISInferenceProfile]:
        """
        Create inference profiles dictionary from regional variants.

        This method converts CRISRegionalVariant objects into CRISInferenceProfile objects,
        properly structuring them by inference profile ID.

        Args:
            variants: List of regional variants for a model

        Returns:
            Dictionary mapping inference profile IDs to CRISInferenceProfile objects
        """
        inference_profiles = {}

        for variant in variants:
            profile_id = variant.inference_profile_id

            # Check for duplicate profile IDs
            if profile_id in inference_profiles:
                self._logger.warning(
                    CRISLogMessages.DUPLICATE_PROFILE_DETECTED.format(
                        profile_id=profile_id,
                        model_name="unknown",  # Model name not available at this level
                    )
                )
                # Skip duplicate - first one wins
                continue

            # Create CRISInferenceProfile from variant
            inference_profiles[profile_id] = CRISInferenceProfile(
                inference_profile_id=profile_id, region_mappings=variant.region_mappings
            )

        return inference_profiles

    def _select_primary_variant(self, variants: List[CRISRegionalVariant]) -> CRISRegionalVariant:
        """
        Select the primary variant from a list of regional variants.

        Preference order: US > EU > APAC > first available

        Args:
            variants: List of regional variants for a model

        Returns:
            The selected primary variant
        """
        if not variants:
            raise ValueError("Cannot select primary variant from empty list")

        # Define preference order
        preference_order = [
            CRISRegionPrefixes.US_IDENTIFIER,
            CRISRegionPrefixes.EU_IDENTIFIER,
            CRISRegionPrefixes.APAC_IDENTIFIER,
        ]

        # Try to find variant in preference order
        for preferred_prefix in preference_order:
            for variant in variants:
                if variant.region_prefix == preferred_prefix:
                    return variant

        # If no preferred variant found, return the first one
        return variants[0]

    def _merge_region_mappings(self, variants: List[CRISRegionalVariant]) -> Dict[str, List[str]]:
        """
        Merge region mappings from all variants into a comprehensive mapping.

        Args:
            variants: List of regional variants to merge

        Returns:
            Dictionary with merged region mappings from all variants
        """
        merged_mappings: Dict[str, List[str]] = {}

        for variant in variants:
            for source_region, destination_regions in variant.region_mappings.items():
                if source_region in merged_mappings:
                    # Merge destination regions, avoiding duplicates
                    existing_destinations = set(merged_mappings[source_region])
                    new_destinations = set(destination_regions)
                    merged_mappings[source_region] = sorted(
                        list(existing_destinations | new_destinations)
                    )
                else:
                    merged_mappings[source_region] = destination_regions.copy()

        return merged_mappings

    def _extract_clean_model_name(self, section: Tag) -> Optional[str]:
        """
        Extract the clean model name from a section header.

        Args:
            section: BeautifulSoup Tag representing the expandable section

        Returns:
            Clean model name without regional prefix, None if extraction fails
        """
        header_attr = section.get(CRISHTMLAttributes.HEADER)
        if not header_attr:
            return None

        header_str = self._normalize_header_attribute(header_attr=header_attr)
        _, clean_name = CRISRegionExtractor.extract_region_and_model_name(header=header_str)

        return clean_name if clean_name else None

    def _normalize_header_attribute(self, header_attr: Any) -> str:
        """
        Normalize header attribute to string format.

        Args:
            header_attr: Header attribute from BeautifulSoup (can be string or list)

        Returns:
            Normalized header string
        """
        if isinstance(header_attr, list):
            return " ".join(str(item) for item in header_attr)
        else:
            return str(header_attr)

    def _extract_inference_profile_id(self, section: Tag) -> str:
        """
        Extract inference profile ID from code block within the section.

        Args:
            section: BeautifulSoup Tag representing the expandable section

        Returns:
            Inference profile ID string, empty if not found
        """
        # Find code blocks within this section
        code_blocks = section.find_all(name=CRISHTMLSelectors.CODE_BLOCK)

        for code_element in code_blocks:
            if isinstance(code_element, Tag):
                # Get text content from code block
                profile_id = code_element.get_text(strip=True)
                if profile_id:
                    # Validate format (basic check for inference profile pattern)
                    if ":" in profile_id and not profile_id.startswith("http"):
                        return profile_id

        return ""

    def _extract_profile_from_section_id(self, section_id: Any) -> str:
        """
        Fallback method to extract inference profile from section ID.

        Args:
            section_id: The section ID attribute

        Returns:
            Extracted inference profile ID, empty if not extractable
        """
        section_id_str = str(section_id) if section_id else ""
        if section_id_str and section_id_str.startswith("cross-region-ip-"):
            return section_id_str.replace("cross-region-ip-", "")
        return ""

    def _parse_region_mapping_table(self, section: Tag) -> Dict[str, List[str]]:
        """
        Parse the region mapping table within the expandable section.

        Args:
            section: BeautifulSoup Tag representing the expandable section

        Returns:
            Dictionary mapping source regions to lists of destination regions
        """
        region_mappings: Dict[str, List[str]] = {}

        # Find table container within this section - try multiple selectors
        table_container = section.find(class_="table-container")
        if not table_container or not isinstance(table_container, Tag):
            # Try alternative selector
            table_container = section.find("div", class_="table-contents")
            if not table_container or not isinstance(table_container, Tag):
                return region_mappings

        # Find the table - it might be nested in table-contents
        table = table_container.find("table")
        if not table or not isinstance(table, Tag):
            # Try looking in nested table-contents div
            table_contents = table_container.find(class_="table-contents")
            if table_contents and isinstance(table_contents, Tag):
                table = table_contents.find("table")
                if not table or not isinstance(table, Tag):
                    return region_mappings
            else:
                return region_mappings

        # Find table rows
        rows = table.find_all(CRISHTMLSelectors.TABLE_ROW)
        if len(rows) < 2:  # Need at least header + one data row
            return region_mappings

        # Parse header to determine column indices
        header_row = rows[0]
        if not isinstance(header_row, Tag):
            return region_mappings

        header_cells = header_row.find_all(CRISHTMLSelectors.TABLE_HEADER)

        source_col_idx = None
        dest_col_idx = None

        for idx, cell in enumerate(header_cells):
            if isinstance(cell, Tag):
                cell_text = cell.get_text(strip=True)
                if cell_text == CRISTableColumns.SOURCE_REGION:
                    source_col_idx = idx
                elif cell_text == CRISTableColumns.DESTINATION_REGIONS:
                    dest_col_idx = idx

        if source_col_idx is None or dest_col_idx is None:
            return region_mappings

        # Parse data rows
        for row in rows[1:]:  # Skip header row
            if not isinstance(row, Tag):
                continue

            cells = row.find_all(CRISHTMLSelectors.TABLE_CELL)
            if len(cells) <= max(source_col_idx, dest_col_idx):
                continue

            # Extract source region
            source_cell = cells[source_col_idx]
            if not isinstance(source_cell, Tag):
                continue

            source_region = source_cell.get_text(strip=True)
            if not source_region:
                continue

            # Extract destination regions
            dest_cell = cells[dest_col_idx]
            if isinstance(dest_cell, Tag):
                destination_regions = self._extract_destination_regions(cell=dest_cell)
                if destination_regions:
                    region_mappings[source_region] = destination_regions

        return region_mappings

    def _extract_destination_regions(self, cell: Tag) -> List[str]:
        """
        Extract destination regions from a table cell.

        Args:
            cell: BeautifulSoup Tag representing a table cell

        Returns:
            List of destination region names
        """
        destinations = []

        # Look for paragraph elements within the cell
        paragraphs = cell.find_all(CRISHTMLSelectors.PARAGRAPH)

        if paragraphs:
            # Extract text from each paragraph
            for para in paragraphs:
                if isinstance(para, Tag):
                    region = para.get_text(strip=True)
                    if region and self._is_valid_region_name(region=region):
                        destinations.append(region)
        else:
            # Fallback: try to extract all text and split by common delimiters
            cell_text = cell.get_text(strip=True)
            if cell_text:
                # Split by common delimiters and clean up
                potential_regions = re.split(r"[,;\n\r]+", cell_text)
                for region in potential_regions:
                    region = region.strip()
                    if region and self._is_valid_region_name(region=region):
                        destinations.append(region)

        return destinations

    def _is_valid_region_name(self, region: str) -> bool:
        """
        Validate if a string looks like a valid AWS region name.

        Args:
            region: The region string to validate

        Returns:
            True if the string looks like a valid AWS region
        """
        if not region:
            return False

        # Basic validation: AWS regions typically follow pattern like "us-east-1"
        region_pattern = r"^[a-z]{2,}-[a-z]+-[0-9]+$"
        return bool(re.match(region_pattern, region))
