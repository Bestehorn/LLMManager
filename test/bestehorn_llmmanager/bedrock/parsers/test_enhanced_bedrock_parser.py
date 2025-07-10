"""
Unit tests for EnhancedBedrockHTMLParser.
Tests enhanced parsing functionality with CRIS-only region detection.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from bs4 import Tag

from bestehorn_llmmanager.bedrock.models.data_structures import BedrockModelInfo
from bestehorn_llmmanager.bedrock.models.unified_constants import RegionMarkers
from bestehorn_llmmanager.bedrock.parsers.enhanced_bedrock_parser import EnhancedBedrockHTMLParser


class TestEnhancedBedrockHTMLParser:
    """Test cases for EnhancedBedrockHTMLParser initialization and basic functionality."""

    def test_initialization(self):
        """Test successful initialization of enhanced parser."""
        parser = EnhancedBedrockHTMLParser()

        assert hasattr(parser, "_cris_only_regions_detected")
        assert parser._cris_only_regions_detected == 0
        assert hasattr(parser, "_logger")

    def test_inheritance(self):
        """Test that enhanced parser properly inherits from base parser."""
        from bestehorn_llmmanager.bedrock.parsers.bedrock_parser import BedrockHTMLParser

        parser = EnhancedBedrockHTMLParser()
        assert isinstance(parser, BedrockHTMLParser)

    def test_get_cris_detection_stats_initial(self):
        """Test initial CRIS detection statistics."""
        parser = EnhancedBedrockHTMLParser()

        stats = parser.get_cris_detection_stats()

        assert isinstance(stats, dict)
        assert "cris_only_regions_detected" in stats
        assert stats["cris_only_regions_detected"] == 0


class TestProcessRegionText:
    """Test cases for _process_region_text method."""

    def test_process_region_text_empty_input(self):
        """Test processing empty region text."""
        parser = EnhancedBedrockHTMLParser()

        result = parser._process_region_text(region_text="")

        assert result is None

    def test_process_region_text_none_input(self):
        """Test processing None region text."""
        parser = EnhancedBedrockHTMLParser()

        # Since the method signature requires str, we'll test empty string behavior instead
        result = parser._process_region_text(region_text="")
        assert result is None

    def test_process_region_text_regular_region(self):
        """Test processing regular region without CRIS marker."""
        parser = EnhancedBedrockHTMLParser()

        with patch(
            "bestehorn_llmmanager.bedrock.parsers.enhanced_bedrock_parser.normalize_region_name"
        ) as mock_normalize:
            mock_normalize.return_value = "us-east-1"

            result = parser._process_region_text(region_text="US East (N. Virginia)")

            assert result == "us-east-1"
            mock_normalize.assert_called_once_with(region_text="US East (N. Virginia)")

    def test_process_region_text_cris_only_region(self):
        """Test processing region with CRIS-only marker."""
        parser = EnhancedBedrockHTMLParser()
        initial_count = parser._cris_only_regions_detected

        with patch(
            "bestehorn_llmmanager.bedrock.parsers.enhanced_bedrock_parser.normalize_region_name"
        ) as mock_normalize:
            mock_normalize.return_value = "us-west-2"

            result = parser._process_region_text(
                region_text=f"US West (Oregon){RegionMarkers.CRIS_ONLY_MARKER}"
            )

            assert result == f"us-west-2{RegionMarkers.CRIS_ONLY_MARKER}"
            assert parser._cris_only_regions_detected == initial_count + 1
            mock_normalize.assert_called_once_with(region_text="US West (Oregon)")

    def test_process_region_text_cris_normalization_failure(self):
        """Test processing CRIS region when normalization fails."""
        parser = EnhancedBedrockHTMLParser()

        with patch(
            "bestehorn_llmmanager.bedrock.parsers.enhanced_bedrock_parser.normalize_region_name"
        ) as mock_normalize:
            mock_normalize.return_value = None

            result = parser._process_region_text(
                region_text=f"Invalid Region{RegionMarkers.CRIS_ONLY_MARKER}"
            )

            assert result is None

    def test_process_region_text_regular_normalization_failure(self):
        """Test processing regular region when normalization fails."""
        parser = EnhancedBedrockHTMLParser()

        with patch(
            "bestehorn_llmmanager.bedrock.parsers.enhanced_bedrock_parser.normalize_region_name"
        ) as mock_normalize:
            mock_normalize.return_value = None

            result = parser._process_region_text(region_text="Invalid Region")

            assert result is None

    def test_process_region_text_whitespace_handling(self):
        """Test processing region text with extra whitespace."""
        parser = EnhancedBedrockHTMLParser()

        with patch(
            "bestehorn_llmmanager.bedrock.parsers.enhanced_bedrock_parser.normalize_region_name"
        ) as mock_normalize:
            mock_normalize.return_value = "eu-west-1"

            result = parser._process_region_text(
                region_text=f"  Europe (Ireland)  {RegionMarkers.CRIS_ONLY_MARKER}"
            )

            assert result == f"eu-west-1{RegionMarkers.CRIS_ONLY_MARKER}"
            mock_normalize.assert_called_once_with(region_text="Europe (Ireland)")


class TestExtractRegionsFromCell:
    """Test cases for _extract_regions_from_cell method."""

    def test_extract_regions_column_not_found(self):
        """Test extraction when column is not in indices."""
        parser = EnhancedBedrockHTMLParser()
        parser._column_indices = {"Model": 0, "Provider": 1}

        cells = [Mock(), Mock()]
        result = parser._extract_regions_from_cell(cells=cells, column="NonExistentColumn")

        assert result == []

    def test_extract_regions_cell_index_out_of_range(self):
        """Test extraction when cell index is out of range."""
        parser = EnhancedBedrockHTMLParser()
        parser._column_indices = {"Regions": 5}

        cells = [Mock(), Mock()]  # Only 2 cells, but we want index 5
        result = parser._extract_regions_from_cell(cells=cells, column="Regions")

        assert result == []

    def test_extract_regions_from_paragraphs(self):
        """Test extraction of regions from paragraph tags."""
        parser = EnhancedBedrockHTMLParser()
        parser._column_indices = {"Regions": 0}

        # Create mock cell with paragraph tags
        mock_cell = Mock(spec=Tag)

        # Create mock paragraph tags
        p1 = Mock(spec=Tag)
        p1.get_text.return_value = "US East (N. Virginia)"

        p2 = Mock(spec=Tag)
        p2.get_text.return_value = f"US West (Oregon){RegionMarkers.CRIS_ONLY_MARKER}"

        mock_cell.find_all.return_value = [p1, p2]
        cells = [mock_cell]

        with patch.object(parser, "_process_region_text") as mock_process:
            mock_process.side_effect = ["us-east-1", f"us-west-2{RegionMarkers.CRIS_ONLY_MARKER}"]

            result = parser._extract_regions_from_cell(cells=cells, column="Regions")

            assert result == ["us-east-1", f"us-west-2{RegionMarkers.CRIS_ONLY_MARKER}"]
            assert mock_process.call_count == 2

    def test_extract_regions_from_text_fallback(self):
        """Test extraction of regions from text when no paragraphs found."""
        parser = EnhancedBedrockHTMLParser()
        parser._column_indices = {"Regions": 0}

        # Create mock cell without paragraph tags
        mock_cell = Mock(spec=Tag)
        mock_cell.find_all.return_value = []  # No paragraphs
        mock_cell.get_text.return_value = (
            f"us-east-1{RegionMarkers.REGION_SEPARATOR}us-west-2{RegionMarkers.CRIS_ONLY_MARKER}"
        )

        cells = [mock_cell]

        with patch.object(parser, "_process_region_text") as mock_process:
            mock_process.side_effect = ["us-east-1", f"us-west-2{RegionMarkers.CRIS_ONLY_MARKER}"]

            result = parser._extract_regions_from_cell(cells=cells, column="Regions")

            assert result == ["us-east-1", f"us-west-2{RegionMarkers.CRIS_ONLY_MARKER}"]
            assert mock_process.call_count == 2

    def test_extract_regions_empty_cell(self):
        """Test extraction from empty cell."""
        parser = EnhancedBedrockHTMLParser()
        parser._column_indices = {"Regions": 0}

        mock_cell = Mock(spec=Tag)
        mock_cell.find_all.return_value = []
        mock_cell.get_text.return_value = ""

        cells = [mock_cell]

        result = parser._extract_regions_from_cell(cells=cells, column="Regions")

        assert result == []

    def test_extract_regions_duplicate_removal(self):
        """Test that duplicate regions are removed while preserving order."""
        parser = EnhancedBedrockHTMLParser()
        parser._column_indices = {"Regions": 0}

        mock_cell = Mock(spec=Tag)
        mock_cell.find_all.return_value = []
        mock_cell.get_text.return_value = f"us-east-1{RegionMarkers.REGION_SEPARATOR}us-west-2{RegionMarkers.REGION_SEPARATOR}us-east-1"

        cells = [mock_cell]

        with patch.object(parser, "_process_region_text") as mock_process:
            mock_process.side_effect = ["us-east-1", "us-west-2", "us-east-1"]

            result = parser._extract_regions_from_cell(cells=cells, column="Regions")

            # Should preserve order and remove duplicates
            assert result == ["us-east-1", "us-west-2"]

    def test_extract_regions_filter_none_results(self):
        """Test that None results from processing are filtered out."""
        parser = EnhancedBedrockHTMLParser()
        parser._column_indices = {"Regions": 0}

        mock_cell = Mock(spec=Tag)
        mock_cell.find_all.return_value = []
        mock_cell.get_text.return_value = f"us-east-1{RegionMarkers.REGION_SEPARATOR}invalid-region"

        cells = [mock_cell]

        with patch.object(parser, "_process_region_text") as mock_process:
            mock_process.side_effect = ["us-east-1", None]  # Second region fails processing

            result = parser._extract_regions_from_cell(cells=cells, column="Regions")

            assert result == ["us-east-1"]


class TestExtractModelFromRow:
    """Test cases for _extract_model_from_row method."""

    def test_extract_model_from_row_no_cris_regions(self):
        """Test extraction when model has no CRIS-only regions."""
        parser = EnhancedBedrockHTMLParser()

        mock_row = Mock(spec=Tag)
        mock_model_info = BedrockModelInfo(
            provider="Amazon",
            model_id="test-model",
            regions_supported=["us-east-1", "us-west-2"],
            input_modalities=["Text"],
            output_modalities=["Text"],
            streaming_supported=True,
        )

        with patch(
            "bestehorn_llmmanager.bedrock.parsers.bedrock_parser.BedrockHTMLParser._extract_model_from_row"
        ) as mock_super:
            mock_super.return_value = ("TestModel", mock_model_info)

            with patch.object(parser._logger, "debug") as mock_debug:
                result = parser._extract_model_from_row(row=mock_row)

                assert result == ("TestModel", mock_model_info)
                mock_debug.assert_not_called()

    def test_extract_model_from_row_with_cris_regions(self):
        """Test extraction when model has CRIS-only regions."""
        parser = EnhancedBedrockHTMLParser()

        mock_row = Mock(spec=Tag)
        mock_model_info = BedrockModelInfo(
            provider="Amazon",
            model_id="test-model",
            regions_supported=[
                "us-east-1",
                f"us-west-2{RegionMarkers.CRIS_ONLY_MARKER}",
                f"eu-west-1{RegionMarkers.CRIS_ONLY_MARKER}",
            ],
            input_modalities=["Text"],
            output_modalities=["Text"],
            streaming_supported=True,
        )

        with patch(
            "bestehorn_llmmanager.bedrock.parsers.bedrock_parser.BedrockHTMLParser._extract_model_from_row"
        ) as mock_super:
            mock_super.return_value = ("TestModel", mock_model_info)

            with patch.object(parser._logger, "debug") as mock_debug:
                result = parser._extract_model_from_row(row=mock_row)

                assert result == ("TestModel", mock_model_info)
                mock_debug.assert_called_once_with("Model TestModel has 2 CRIS-only regions")

    def test_extract_model_from_row_failed_extraction(self):
        """Test extraction when parent method fails."""
        parser = EnhancedBedrockHTMLParser()

        mock_row = Mock(spec=Tag)

        with patch(
            "bestehorn_llmmanager.bedrock.parsers.bedrock_parser.BedrockHTMLParser._extract_model_from_row"
        ) as mock_super:
            mock_super.return_value = (None, None)

            result = parser._extract_model_from_row(row=mock_row)

            assert result == (None, None)


class TestParse:
    """Test cases for parse method."""

    def test_parse_with_cris_detection(self):
        """Test parsing with CRIS-only region detection."""
        parser = EnhancedBedrockHTMLParser()

        # Create a temporary HTML file
        html_content = """
        <html>
        <body>
        <table>
        <tr><th>Model</th><th>Provider</th><th>Regions</th></tr>
        <tr>
        <td>TestModel</td>
        <td>Amazon</td>
        <td>us-east-1, us-west-2*</td>
        </tr>
        </table>
        </body>
        </html>
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as tmp_file:
            tmp_file.write(html_content)
            tmp_file_path = Path(tmp_file.name)

        try:
            mock_models = {
                "TestModel": BedrockModelInfo(
                    provider="Amazon",
                    model_id="test-model",
                    regions_supported=["us-east-1", f"us-west-2{RegionMarkers.CRIS_ONLY_MARKER}"],
                    input_modalities=["Text"],
                    output_modalities=["Text"],
                    streaming_supported=True,
                )
            }

            def mock_super_parse(file_path):
                # Simulate detection during parsing
                parser._cris_only_regions_detected = 2
                return mock_models

            with patch(
                "bestehorn_llmmanager.bedrock.parsers.bedrock_parser.BedrockHTMLParser.parse"
            ) as mock_super:
                mock_super.side_effect = mock_super_parse

                with patch.object(parser._logger, "info") as mock_info:
                    result = parser.parse(file_path=tmp_file_path)

                    assert result == mock_models
                    mock_info.assert_called_once_with(
                        "Detected 2 CRIS-only region markers during parsing"
                    )
        finally:
            # Clean up
            tmp_file_path.unlink()

    def test_parse_no_cris_detection(self):
        """Test parsing when no CRIS-only regions are detected."""
        parser = EnhancedBedrockHTMLParser()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as tmp_file:
            tmp_file.write("<html><body><p>Test</p></body></html>")
            tmp_file_path = Path(tmp_file.name)

        try:
            mock_models = {"TestModel": Mock()}

            with patch(
                "bestehorn_llmmanager.bedrock.parsers.bedrock_parser.BedrockHTMLParser.parse"
            ) as mock_super_parse:
                mock_super_parse.return_value = mock_models

                with patch.object(parser._logger, "info") as mock_info:
                    result = parser.parse(file_path=tmp_file_path)

                    assert result == mock_models
                    assert parser._cris_only_regions_detected == 0
                    mock_info.assert_not_called()
        finally:
            # Clean up
            tmp_file_path.unlink()

    def test_parse_resets_detection_counter(self):
        """Test that parse method resets the detection counter."""
        parser = EnhancedBedrockHTMLParser()
        parser._cris_only_regions_detected = 5  # Set initial value

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as tmp_file:
            tmp_file.write("<html><body><p>Test</p></body></html>")
            tmp_file_path = Path(tmp_file.name)

        try:
            with patch(
                "bestehorn_llmmanager.bedrock.parsers.bedrock_parser.BedrockHTMLParser.parse"
            ) as mock_super_parse:
                mock_super_parse.return_value = {}

                parser.parse(file_path=tmp_file_path)

                # Counter should be reset to 0
                assert parser._cris_only_regions_detected == 0
        finally:
            # Clean up
            tmp_file_path.unlink()


class TestGetCrisDetectionStats:
    """Test cases for get_cris_detection_stats method."""

    def test_get_cris_detection_stats_after_detection(self):
        """Test getting statistics after some detections."""
        parser = EnhancedBedrockHTMLParser()
        parser._cris_only_regions_detected = 10

        stats = parser.get_cris_detection_stats()

        assert isinstance(stats, dict)
        assert stats["cris_only_regions_detected"] == 10

    def test_get_cris_detection_stats_structure(self):
        """Test the structure of the statistics dictionary."""
        parser = EnhancedBedrockHTMLParser()
        parser._cris_only_regions_detected = 42

        stats = parser.get_cris_detection_stats()

        expected_keys = {"cris_only_regions_detected"}
        assert set(stats.keys()) == expected_keys
        assert all(isinstance(v, int) for v in stats.values())
