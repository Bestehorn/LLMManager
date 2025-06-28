"""
BeautifulSoup-based parser for Amazon Bedrock model documentation.
Parses HTML tables containing model information.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup, Tag

from ..models.aws_regions import normalize_region_name
from ..models.constants import BooleanValues, HTMLTableColumns, LogMessages
from ..models.data_structures import BedrockModelInfo
from .base_parser import BaseDocumentationParser, ParsingError


class BedrockHTMLParser(BaseDocumentationParser):
    """
    BeautifulSoup-based parser for Bedrock model documentation.
    Extracts model information from HTML tables in AWS documentation.
    """

    def __init__(self) -> None:
        """Initialize the Bedrock HTML parser."""
        self._logger = logging.getLogger(__name__)
        self._column_indices: Dict[str, int] = {}
        self._parsed_model_names: Set[str] = set()

    def parse(self, file_path: Path) -> Dict[str, BedrockModelInfo]:
        """
        Parse Bedrock documentation HTML file and extract model information.

        Args:
            file_path: Path to the HTML documentation file

        Returns:
            Dictionary mapping model names to model information

        Raises:
            ParsingError: If parsing fails
            FileNotFoundError: If the input file doesn't exist
        """
        self._validate_file_exists(file_path=file_path)
        self._logger.info(LogMessages.PARSING_STARTED)

        try:
            content = self._read_file_content(file_path=file_path)
            soup = BeautifulSoup(content, "html.parser")

            models = self._extract_models_from_soup(soup=soup)

            self._logger.info(LogMessages.PARSING_COMPLETED.format(model_count=len(models)))

            return models

        except Exception as e:
            error_msg = LogMessages.PARSING_ERROR.format(error=str(e))
            self._logger.error(error_msg)
            raise ParsingError(error_msg) from e

    def _read_file_content(self, file_path: Path) -> str:
        """
        Read the content of the HTML file.

        Args:
            file_path: Path to the file to read

        Returns:
            File content as string
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _extract_models_from_soup(self, soup: BeautifulSoup) -> Dict[str, BedrockModelInfo]:
        """
        Extract model information from BeautifulSoup object.

        Args:
            soup: Parsed HTML document

        Returns:
            Dictionary mapping model names to model information

        Raises:
            ParsingError: If no valid model table is found
        """
        tables = soup.find_all("table")

        for table_element in tables:
            # Type check and cast to ensure we have a Tag
            if isinstance(table_element, Tag):
                if self._is_model_table(table=table_element):
                    self._build_column_indices(table=table_element)
                    return self._extract_models_from_table(table=table_element)

        raise ParsingError("No valid model table found in the documentation")

    def _is_model_table(self, table: Tag) -> bool:
        """
        Check if a table contains Bedrock model information.

        Args:
            table: BeautifulSoup table element

        Returns:
            True if this is a model information table
        """
        headers = table.find("thead")
        if not headers or not isinstance(headers, Tag):
            return False

        header_texts = []
        for th in headers.find_all("th"):
            if isinstance(th, Tag):
                header_texts.append(th.get_text(strip=True))

        required_columns = {
            HTMLTableColumns.PROVIDER,
            HTMLTableColumns.MODEL_NAME,
            HTMLTableColumns.MODEL_ID,
        }

        return required_columns.issubset(set(header_texts))

    def _build_column_indices(self, table: Tag) -> None:
        """
        Build mapping of column names to their indices in the table.

        Args:
            table: BeautifulSoup table element
        """
        headers = table.find("thead")
        if not headers or not isinstance(headers, Tag):
            raise ParsingError("Table header not found")

        header_cells = headers.find_all("th")
        self._column_indices = {}

        for index, th in enumerate(header_cells):
            if isinstance(th, Tag):
                column_name = th.get_text(strip=True)
                self._column_indices[column_name] = index

    def _extract_models_from_table(self, table: Tag) -> Dict[str, BedrockModelInfo]:
        """
        Extract all model information from a table.

        Args:
            table: BeautifulSoup table element

        Returns:
            Dictionary mapping model names to model information
        """
        models: Dict[str, BedrockModelInfo] = {}

        # First try to find tbody, but handle tables without explicit tbody
        tbody = table.find("tbody")
        if tbody and isinstance(tbody, Tag):
            rows_container = tbody
        else:
            # Fallback to searching the entire table but skip thead
            rows_container = table

        for row_element in rows_container.find_all("tr"):
            if isinstance(row_element, Tag) and self._is_data_row(row=row_element):
                try:
                    model_name, model_info = self._extract_model_from_row(row=row_element)
                    if model_name and model_info:
                        # Handle duplicate model names by making them unique
                        unique_name = self._get_unique_model_name(model_name=model_name)
                        models[unique_name] = model_info
                except Exception as e:
                    self._logger.warning(f"Failed to parse row: {str(e)}")
                    continue

        return models

    def _is_data_row(self, row: Tag) -> bool:
        """
        Check if a row contains actual model data (not headers).

        Args:
            row: BeautifulSoup row element

        Returns:
            True if this is a data row
        """
        # Skip rows that are inside thead elements
        if row.find_parent("thead"):
            return False

        # Get all cell elements
        all_cells = row.find_all(["td", "th"])
        if not all_cells:
            return False

        # Separate td and th cells with proper type checking
        td_cells = []
        th_cells = []

        for cell in all_cells:
            if isinstance(cell, Tag):
                if cell.name == "td":
                    td_cells.append(cell)
                elif cell.name == "th":
                    th_cells.append(cell)

        # Skip rows that are primarily header cells (th elements)
        if len(th_cells) > len(td_cells):
            return False

        # Skip rows with no td cells (likely header rows)
        if len(td_cells) == 0:
            return False

        # Check if we have enough cells and they contain actual data (not just column names)
        if len(td_cells) >= len(self._column_indices):
            # Additional validation: check if the first cell contains column header text
            if td_cells and isinstance(td_cells[0], Tag):
                first_cell_text = td_cells[0].get_text(strip=True)
                # Skip if the first cell contains typical column header text
                header_indicators = {"Provider", "Model name", "Model ID", "Regions supported"}
                if first_cell_text in header_indicators:
                    return False
            return True

        return False

    def _extract_model_from_row(self, row: Tag) -> Tuple[Optional[str], Optional[BedrockModelInfo]]:
        """
        Extract model information from a single table row.

        Args:
            row: BeautifulSoup row element

        Returns:
            Tuple of (model_name, model_info) or (None, None) if extraction fails
        """
        # Filter to only Tag elements
        cells = [cell for cell in row.find_all(["td", "th"]) if isinstance(cell, Tag)]

        if len(cells) < len(self._column_indices):
            return None, None

        try:
            model_name = self._extract_text_from_cell(
                cells=cells, column=HTMLTableColumns.MODEL_NAME
            )

            if not model_name:
                return None, None

            provider = self._extract_text_from_cell(cells=cells, column=HTMLTableColumns.PROVIDER)

            model_id = self._extract_text_from_cell(cells=cells, column=HTMLTableColumns.MODEL_ID)

            regions = self._extract_regions_from_cell(
                cells=cells, column=HTMLTableColumns.REGIONS_SUPPORTED
            )

            input_modalities = self._extract_modalities_from_cell(
                cells=cells, column=HTMLTableColumns.INPUT_MODALITIES
            )

            output_modalities = self._extract_modalities_from_cell(
                cells=cells, column=HTMLTableColumns.OUTPUT_MODALITIES
            )

            streaming_supported = self._extract_boolean_from_cell(
                cells=cells, column=HTMLTableColumns.STREAMING_SUPPORTED
            )

            inference_params_link = self._extract_link_from_cell(
                cells=cells, column=HTMLTableColumns.INFERENCE_PARAMETERS
            )

            hyperparams_link = self._extract_link_from_cell(
                cells=cells, column=HTMLTableColumns.HYPERPARAMETERS
            )

            model_info = BedrockModelInfo(
                provider=provider,
                model_id=model_id,
                regions_supported=regions,
                input_modalities=input_modalities,
                output_modalities=output_modalities,
                streaming_supported=streaming_supported,
                inference_parameters_link=inference_params_link,
                hyperparameters_link=hyperparams_link,
            )

            return model_name, model_info

        except Exception as e:
            self._logger.warning(f"Failed to extract model from row: {str(e)}")
            return None, None

    def _extract_text_from_cell(self, cells: List[Tag], column: str) -> str:
        """
        Extract plain text content from a table cell.

        Args:
            cells: List of cell elements
            column: Column name to extract from

        Returns:
            Cleaned text content
        """
        if column not in self._column_indices:
            return ""

        cell_index = self._column_indices[column]
        if cell_index >= len(cells):
            return ""

        cell = cells[cell_index]
        return self._clean_text(cell.get_text(strip=True))

    def _extract_regions_from_cell(self, cells: List[Tag], column: str) -> List[str]:
        """
        Extract region list from a table cell.

        Args:
            cells: List of cell elements
            column: Column name to extract from

        Returns:
            List of normalized region names
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
                    normalized_region = normalize_region_name(region_text=region_text)
                    if normalized_region:
                        regions.append(normalized_region)
        else:
            # Fallback to comma-separated text
            text = cell.get_text(strip=True)
            if text:
                parts = [part.strip() for part in text.split(",")]
                for part in parts:
                    normalized_region = normalize_region_name(region_text=part)
                    if normalized_region:
                        regions.append(normalized_region)

        return list(dict.fromkeys(regions))  # Remove duplicates while preserving order

    def _extract_modalities_from_cell(self, cells: List[Tag], column: str) -> List[str]:
        """
        Extract modality list from a table cell.

        Args:
            cells: List of cell elements
            column: Column name to extract from

        Returns:
            List of modality names
        """
        text = self._extract_text_from_cell(cells=cells, column=column)
        if not text:
            return []

        modalities = [modality.strip() for modality in text.split(",") if modality.strip()]

        return list(dict.fromkeys(modalities))  # Remove duplicates while preserving order

    def _extract_boolean_from_cell(self, cells: List[Tag], column: str) -> bool:
        """
        Extract boolean value from a table cell.

        Args:
            cells: List of cell elements
            column: Column name to extract from

        Returns:
            Boolean value (True for 'Yes', False for 'No' or 'N/A')
        """
        text = self._extract_text_from_cell(cells=cells, column=column)
        return text == BooleanValues.YES

    def _extract_link_from_cell(self, cells: List[Tag], column: str) -> Optional[str]:
        """
        Extract URL from a link in a table cell.

        Args:
            cells: List of cell elements
            column: Column name to extract from

        Returns:
            URL if found, None otherwise
        """
        if column not in self._column_indices:
            return None

        cell_index = self._column_indices[column]
        if cell_index >= len(cells):
            return None

        cell = cells[cell_index]
        link = cell.find("a")

        if isinstance(link, Tag):
            href_attr = link.get("hre")
            if href_attr and isinstance(href_attr, str):
                # Handle relative URLs by checking if they need base URL
                if href_attr.startswith("./"):
                    return f"https://docs.aws.amazon.com/bedrock/latest/userguide/{href_attr[2:]}"
                elif href_attr.startswith("http"):
                    return href_attr
                else:
                    return href_attr

        return None

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        return " ".join(text.split())

    def _get_unique_model_name(self, model_name: str) -> str:
        """
        Get a unique model name, handling duplicates by adding suffix.

        Args:
            model_name: Original model name

        Returns:
            Unique model name
        """
        if model_name not in self._parsed_model_names:
            self._parsed_model_names.add(model_name)
            return model_name

        # Handle duplicates by adding version suffix
        counter = 2
        while f"{model_name}_v{counter}" in self._parsed_model_names:
            counter += 1

        unique_name = f"{model_name}_v{counter}"
        self._parsed_model_names.add(unique_name)
        return unique_name
