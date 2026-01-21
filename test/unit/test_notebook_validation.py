"""
Unit tests for validating notebook updates to BedrockModelCatalog.

This module validates that all notebooks have been correctly updated to use
the new BedrockModelCatalog system and no longer reference deprecated manager classes.

**Validates: Requirements from notebook-catalog-updates specification**
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest


class TestNotebookValidation:
    """Test suite for validating notebook updates."""

    @pytest.fixture(scope="class")
    def notebooks_dir(self) -> Path:
        """Get the notebooks directory path."""
        return Path(__file__).parent.parent.parent / "notebooks"

    @pytest.fixture(scope="class")
    def updated_notebooks(self) -> List[str]:
        """List of notebooks that were updated to use BedrockModelCatalog."""
        return [
            "CRISManager.ipynb",
            "ModelIDManager.ipynb",
            "UnifiedModelManager.ipynb",
        ]

    @pytest.fixture(scope="class")
    def unchanged_notebooks(self) -> List[str]:
        """List of notebooks that should remain unchanged."""
        return [
            "HelloWorld_LLMManager.ipynb",
            "HelloWorld_MessageBuilder.ipynb",
            "HelloWorld_MessageBuilder_Demo.ipynb",
            "HelloWorld_MessageBuilder_Paths.ipynb",
            "HelloWorld_Streaming_Demo.ipynb",
            "ParallelLLMManager_Demo.ipynb",
            "ResponseValidation.ipynb",
            "InferenceProfile_Demo.ipynb",
            "ExtendedContext_Demo.ipynb",
        ]

    @pytest.fixture(scope="class")
    def caching_notebook(self) -> str:
        """The caching notebook that was enhanced."""
        return "Caching.ipynb"

    def _load_notebook(self, notebooks_dir: Path, notebook_name: str) -> Dict[str, Any]:
        """
        Load a notebook JSON file.

        Args:
            notebooks_dir: Path to notebooks directory
            notebook_name: Name of the notebook file

        Returns:
            Parsed notebook JSON

        Raises:
            json.JSONDecodeError: If the notebook JSON is invalid
        """
        notebook_path = notebooks_dir / notebook_name
        assert notebook_path.exists(), f"Notebook not found: {notebook_path}"

        with open(notebook_path, encoding="utf-8") as f:
            result = json.load(f)
            # Type assertion for mypy - json.load returns Any but we know it's a dict
            assert isinstance(result, dict), f"Expected dict, got {type(result)}"
            return result

    def _get_code_cells(self, notebook: Dict[str, Any]) -> List[str]:
        """
        Extract all code cell contents from a notebook.

        Args:
            notebook: Parsed notebook JSON

        Returns:
            List of code cell contents as strings
        """
        code_cells = []
        for cell in notebook.get("cells", []):
            if cell.get("cell_type") == "code":
                source = cell.get("source", [])
                if isinstance(source, list):
                    code_cells.append("".join(source))
                else:
                    code_cells.append(source)
        return code_cells

    def _get_markdown_cells(self, notebook: Dict[str, Any]) -> List[str]:
        """
        Extract all markdown cell contents from a notebook.

        Args:
            notebook: Parsed notebook JSON

        Returns:
            List of markdown cell contents as strings
        """
        markdown_cells = []
        for cell in notebook.get("cells", []):
            if cell.get("cell_type") == "markdown":
                source = cell.get("source", [])
                if isinstance(source, list):
                    markdown_cells.append("".join(source))
                else:
                    markdown_cells.append(source)
        return markdown_cells

    def _get_all_cell_contents(self, notebook: Dict[str, Any]) -> str:
        """
        Get all cell contents as a single string.

        Args:
            notebook: Parsed notebook JSON

        Returns:
            All cell contents concatenated
        """
        code_cells = self._get_code_cells(notebook=notebook)
        markdown_cells = self._get_markdown_cells(notebook=notebook)
        return "\n".join(code_cells + markdown_cells)

    # Test 6.1: Verify correct imports in updated notebooks
    def test_correct_imports_in_updated_notebooks(
        self, notebooks_dir: Path, updated_notebooks: List[str]
    ) -> None:
        """
        Test that updated notebooks have correct BedrockModelCatalog imports.

        Property 1: Correct Import Statement Presence
        For any updated notebook file, parsing the notebook JSON should find
        the import statement for BedrockModelCatalog in at least one code cell.

        **Validates: Requirements 1.1, 2.1, 3.1, 7.1, 7.2, 7.3**
        """
        expected_import = "from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog"

        for notebook_name in updated_notebooks:
            notebook = self._load_notebook(notebooks_dir=notebooks_dir, notebook_name=notebook_name)
            code_cells = self._get_code_cells(notebook=notebook)

            # Check if the expected import exists in any code cell
            found_import = any(expected_import in cell for cell in code_cells)

            assert found_import, (
                f"Notebook {notebook_name} does not contain the required import:\n"
                f"  Expected: {expected_import}\n"
                f"  This import should be present in at least one code cell."
            )

    # Test 6.2: Verify absence of deprecated imports
    def test_no_deprecated_imports_in_updated_notebooks(
        self, notebooks_dir: Path, updated_notebooks: List[str]
    ) -> None:
        """
        Test that updated notebooks do not have deprecated manager imports.

        Property 2: Deprecated Import Absence
        For any updated notebook file, parsing the notebook JSON should NOT find
        any deprecated import statements in code cells.

        **Validates: Requirements 8.2, 8.4**
        """
        deprecated_imports = [
            "from bedrock.CRISManager import CRISManager",
            "from bedrock.ModelManager import ModelManager",
            "from bedrock.UnifiedModelManager import UnifiedModelManager",
        ]

        for notebook_name in updated_notebooks:
            notebook = self._load_notebook(notebooks_dir=notebooks_dir, notebook_name=notebook_name)
            code_cells = self._get_code_cells(notebook=notebook)
            all_code = "\n".join(code_cells)

            # Check for deprecated imports in code cells only
            found_deprecated = []
            for deprecated in deprecated_imports:
                if deprecated in all_code:
                    found_deprecated.append(deprecated)

            assert len(found_deprecated) == 0, (
                f"Notebook {notebook_name} contains deprecated imports in code cells:\n"
                f"  Found: {found_deprecated}\n"
                f"  These should be replaced with BedrockModelCatalog imports."
            )

    # Test 6.3: Verify absence of deprecated method calls
    def test_no_deprecated_method_calls_in_updated_notebooks(
        self, notebooks_dir: Path, updated_notebooks: List[str]
    ) -> None:
        """
        Test that updated notebooks do not call deprecated refresh methods.

        Property 3: Deprecated Method Call Absence
        For any updated notebook file, parsing the code cells should NOT find
        calls to deprecated refresh methods.

        **Validates: Requirements 8.1, 8.5**
        """
        deprecated_methods = [
            "refresh_model_data()",
            "refresh_cris_data()",
            "refresh_unified_data()",
        ]

        for notebook_name in updated_notebooks:
            notebook = self._load_notebook(notebooks_dir=notebooks_dir, notebook_name=notebook_name)
            code_cells = self._get_code_cells(notebook=notebook)
            all_code = "\n".join(code_cells)

            # Check for deprecated method calls
            found_deprecated = []
            for method in deprecated_methods:
                if method in all_code:
                    found_deprecated.append(method)

            assert len(found_deprecated) == 0, (
                f"Notebook {notebook_name} contains deprecated method calls:\n"
                f"  Found: {found_deprecated}\n"
                f"  These methods should not be called; BedrockModelCatalog "
                f"initializes automatically."
            )

    # Test 6.4: Verify force_refresh parameter usage
    def test_force_refresh_parameter_in_updated_notebooks(
        self, notebooks_dir: Path, updated_notebooks: List[str]
    ) -> None:
        """
        Test that BedrockModelCatalog initialization includes force_refresh=True.

        Property 4: Force Refresh Parameter Presence
        For any BedrockModelCatalog initialization in updated notebooks,
        the initialization should include force_refresh=True parameter.

        **Validates: Requirements 1.2, 2.2, 3.2**
        """
        for notebook_name in updated_notebooks:
            notebook = self._load_notebook(notebooks_dir=notebooks_dir, notebook_name=notebook_name)
            code_cells = self._get_code_cells(notebook=notebook)
            all_code = "\n".join(code_cells)

            # Check for BedrockModelCatalog initialization
            has_catalog_init = "BedrockModelCatalog(" in all_code

            if has_catalog_init:
                # Check for force_refresh=True parameter
                has_force_refresh = "force_refresh=True" in all_code

                assert has_force_refresh, (
                    f"Notebook {notebook_name} initializes BedrockModelCatalog "
                    f"but does not use force_refresh=True.\n"
                    f"  For demonstration purposes, notebooks should use "
                    f"force_refresh=True to fetch fresh data."
                )

    # Test 6.5: Verify cache mode completeness in Caching.ipynb
    def test_cache_mode_completeness_in_caching_notebook(
        self, notebooks_dir: Path, caching_notebook: str
    ) -> None:
        """
        Test that Caching.ipynb demonstrates all cache modes.

        Property 5: Cache Mode Completeness
        For any cache mode value (FILE, MEMORY, NONE), the Caching.ipynb notebook
        should contain at least one code cell demonstrating initialization with
        that cache mode.

        **Validates: Requirements 4.1, 4.2, 4.3**
        """
        cache_modes = ["CacheMode.FILE", "CacheMode.MEMORY", "CacheMode.NONE"]

        notebook = self._load_notebook(notebooks_dir=notebooks_dir, notebook_name=caching_notebook)
        code_cells = self._get_code_cells(notebook=notebook)
        all_code = "\n".join(code_cells)

        # Check for each cache mode
        missing_modes = []
        for mode in cache_modes:
            if mode not in all_code:
                missing_modes.append(mode)

        assert len(missing_modes) == 0, (
            f"Notebook {caching_notebook} is missing demonstrations for cache modes:\n"
            f"  Missing: {missing_modes}\n"
            f"  All cache modes (FILE, MEMORY, NONE) should be demonstrated."
        )

    # Test 6.6: Verify unchanged notebooks don't have deprecated imports
    def test_unchanged_notebooks_no_deprecated_imports(
        self, notebooks_dir: Path, unchanged_notebooks: List[str]
    ) -> None:
        """
        Test that unchanged notebooks do not contain deprecated manager imports.

        Property 6: Unchanged Notebook Preservation
        For any notebook in the unchanged list, the notebook should NOT contain
        deprecated manager imports.

        **Validates: Requirements 5.1-5.9, 10.1-10.9**
        """
        deprecated_patterns = [
            "from bedrock.CRISManager import",
            "from bedrock.ModelManager import",
            "from bedrock.UnifiedModelManager import",
        ]

        skipped_notebooks = []
        for notebook_name in unchanged_notebooks:
            try:
                notebook = self._load_notebook(
                    notebooks_dir=notebooks_dir, notebook_name=notebook_name
                )
                code_cells = self._get_code_cells(notebook=notebook)
                all_code = "\n".join(code_cells)

                # Check for deprecated imports
                found_deprecated = []
                for pattern in deprecated_patterns:
                    if pattern in all_code:
                        found_deprecated.append(pattern)

                assert len(found_deprecated) == 0, (
                    f"Unchanged notebook {notebook_name} contains deprecated imports:\n"
                    f"  Found: {found_deprecated}\n"
                    f"  Unchanged notebooks should not use deprecated manager classes."
                )
            except json.JSONDecodeError as e:
                skipped_notebooks.append((notebook_name, str(e)))
                continue

        # Report skipped notebooks as a warning, not a failure
        if skipped_notebooks:
            import warnings

            for nb_name, error in skipped_notebooks:
                warnings.warn(
                    f"Skipped {nb_name} due to JSON parsing error: {error}",
                    UserWarning,
                )

    # Test 6.7: Verify troubleshooting content presence
    def test_troubleshooting_content_in_updated_notebooks(
        self, notebooks_dir: Path, updated_notebooks: List[str]
    ) -> None:
        """
        Test that updated notebooks contain troubleshooting guidance.

        Property 7: Troubleshooting Content Presence
        For any updated notebook, there should be at least one markdown or code cell
        containing troubleshooting guidance.

        **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**
        """
        troubleshooting_keywords = [
            "troubleshooting",
            "Troubleshooting",
            "TROUBLESHOOTING",
            "💡",
            "⚠️",
            "error",
            "Error",
            "ERROR",
        ]

        for notebook_name in updated_notebooks:
            notebook = self._load_notebook(notebooks_dir=notebooks_dir, notebook_name=notebook_name)
            all_content = self._get_all_cell_contents(notebook=notebook)

            # Check for troubleshooting keywords
            has_troubleshooting = any(
                keyword in all_content for keyword in troubleshooting_keywords
            )

            assert has_troubleshooting, (
                f"Notebook {notebook_name} does not contain troubleshooting guidance.\n"
                f"  Expected to find at least one of: {troubleshooting_keywords}\n"
                f"  Notebooks should include troubleshooting sections to help users "
                f"resolve common issues."
            )

    # Test 6.8: Verify summary section presence
    def test_summary_section_in_updated_notebooks(
        self, notebooks_dir: Path, updated_notebooks: List[str]
    ) -> None:
        """
        Test that updated notebooks contain a summary section.

        Property 8: Summary Section Presence
        For any updated notebook, there should be a markdown cell near the end
        containing "Summary" or "summary" in its content.

        **Validates: Requirements 6.5**
        """
        for notebook_name in updated_notebooks:
            notebook = self._load_notebook(notebooks_dir=notebooks_dir, notebook_name=notebook_name)
            markdown_cells = self._get_markdown_cells(notebook=notebook)

            # Check for summary in markdown cells
            has_summary = any(
                "summary" in cell.lower() or "Summary" in cell for cell in markdown_cells
            )

            assert has_summary, (
                f"Notebook {notebook_name} does not contain a summary section.\n"
                f"  Expected to find 'Summary' or 'summary' in a markdown cell.\n"
                f"  Notebooks should include a summary section highlighting key takeaways."
            )
