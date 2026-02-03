"""
Unit tests for documentation Python version references.

This module validates that documentation files have been correctly updated to:
- Reference Python 3.10+ as the minimum version
- Remove references to Python 3.9 as supported
- Update Lambda runtime specifications to Python 3.10+

**Validates: Requirements 1.4, 1.5, 2.5, 2.6, 3.5, 3.6, 5.1, 5.2, 5.3, 5.4**
"""

from pathlib import Path


class TestREADMEDocumentation:
    """Test suite for README.md Python version references."""

    def test_readme_contains_python_310_plus_in_prerequisites(self) -> None:
        """
        Verify README.md states "Python 3.10+" in prerequisites section.

        **Validates: Requirements 1.5, 5.1**
        """
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        with open(readme_path, encoding="utf-8") as f:
            content = f.read()

        # Check for "Python 3.10+" in prerequisites section
        assert "Python 3.10+" in content, "README.md should contain 'Python 3.10+' in prerequisites"

    def test_readme_does_not_reference_python_39_as_supported(self) -> None:
        """
        Verify README.md does not reference Python 3.9 as a supported version.

        This test checks that Python 3.9 is not mentioned in contexts that
        would indicate it's a supported version (e.g., "Python 3.9+").

        **Validates: Requirements 1.5, 5.2**
        """
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        with open(readme_path, encoding="utf-8") as f:
            content = f.read()

        # Check that "Python 3.9+" is not present (indicating support)
        assert (
            "Python 3.9+" not in content
        ), "README.md should not reference 'Python 3.9+' as supported"

        # Also check for other patterns that might indicate 3.9 support
        assert (
            "python 3.9+" not in content.lower()
        ), "README.md should not reference 'python 3.9+' (case-insensitive)"

    def test_readme_prerequisites_section_has_correct_version(self) -> None:
        """
        Verify the Prerequisites section specifically mentions Python 3.10+.

        **Validates: Requirements 5.1**
        """
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        with open(readme_path, encoding="utf-8") as f:
            content = f.read()

        # Find the Prerequisites section
        lines = content.split("\n")
        in_prerequisites = False
        found_python_version = False

        for line in lines:
            if "### Prerequisites" in line or "## Prerequisites" in line:
                in_prerequisites = True
            elif in_prerequisites and line.startswith("#"):
                # Reached next section
                break
            elif in_prerequisites and "Python 3.10+" in line:
                found_python_version = True
                break

        assert (
            found_python_version
        ), "Prerequisites section should explicitly mention 'Python 3.10+'"


class TestExamplesDocumentation:
    """Test suite for examples/README.md Python version references."""

    def test_examples_readme_does_not_use_python39_runtime(self) -> None:
        """
        Verify examples/README.md does not reference python3.9 runtime.

        This checks Lambda runtime specifications and other runtime references
        to ensure they don't use Python 3.9.

        **Validates: Requirements 5.3**
        """
        examples_readme_path = Path(__file__).parent.parent.parent / "examples" / "README.md"
        with open(examples_readme_path, encoding="utf-8") as f:
            content = f.read()

        # Check for python3.9 runtime references
        assert (
            "python3.9" not in content.lower()
        ), "examples/README.md should not reference 'python3.9' runtime"

        # Check for Python 3.9 version references
        assert (
            "python 3.9" not in content.lower()
        ), "examples/README.md should not reference 'Python 3.9'"

    def test_examples_readme_uses_python310_or_later_runtime(self) -> None:
        """
        Verify examples/README.md uses Python 3.10 or later for Lambda runtime.

        **Validates: Requirements 2.5, 3.5, 5.3**
        """
        examples_readme_path = Path(__file__).parent.parent.parent / "examples" / "README.md"
        with open(examples_readme_path, encoding="utf-8") as f:
            content = f.read()

        # Check for python3.10 or later runtime references
        has_valid_runtime = (
            "python3.10" in content.lower()
            or "python3.11" in content.lower()
            or "python3.12" in content.lower()
            or "python3.13" in content.lower()
            or "python3.14" in content.lower()
        )

        assert (
            has_valid_runtime
        ), "examples/README.md should reference Python 3.10+ runtime (e.g., python3.10)"


class TestTechStackDocumentation:
    """Test suite for .kiro/steering/tech-stack.md Python version references."""

    def test_tech_stack_specifies_python_310_plus(self) -> None:
        """
        Verify tech-stack.md specifies "Python 3.10+" in Core Technologies.

        **Validates: Requirements 1.4, 2.6, 3.6, 5.4**
        """
        tech_stack_path = (
            Path(__file__).parent.parent.parent / ".kiro" / "steering" / "tech-stack.md"
        )
        with open(tech_stack_path, encoding="utf-8") as f:
            content = f.read()

        # Check for "Python 3.10+" in the document
        assert (
            "Python 3.10+" in content
        ), "tech-stack.md should specify 'Python 3.10+' in Core Technologies"

    def test_tech_stack_does_not_reference_python_39(self) -> None:
        """
        Verify tech-stack.md does not reference Python 3.9 as supported.

        **Validates: Requirements 1.4, 5.4**
        """
        tech_stack_path = (
            Path(__file__).parent.parent.parent / ".kiro" / "steering" / "tech-stack.md"
        )
        with open(tech_stack_path, encoding="utf-8") as f:
            content = f.read()

        # Check that Python 3.9 is not mentioned as a supported version
        assert (
            "Python 3.9+" not in content
        ), "tech-stack.md should not reference 'Python 3.9+' as supported"

        assert (
            "python 3.9+" not in content.lower()
        ), "tech-stack.md should not reference 'python 3.9+' (case-insensitive)"

    def test_tech_stack_core_technologies_section_has_correct_version(self) -> None:
        """
        Verify the Core Technologies section specifically mentions Python 3.10+.

        **Validates: Requirements 5.4**
        """
        tech_stack_path = (
            Path(__file__).parent.parent.parent / ".kiro" / "steering" / "tech-stack.md"
        )
        with open(tech_stack_path, encoding="utf-8") as f:
            content = f.read()

        # Find the Core Technologies section
        lines = content.split("\n")
        in_core_technologies = False
        found_python_version = False

        for line in lines:
            if "## Core Technologies" in line:
                in_core_technologies = True
            elif in_core_technologies and line.startswith("##"):
                # Reached next section
                break
            elif in_core_technologies and "Python 3.10+" in line:
                found_python_version = True
                break

        assert (
            found_python_version
        ), "Core Technologies section should explicitly mention 'Python 3.10+'"


class TestDocumentationConsistency:
    """Test suite for cross-document consistency."""

    def test_all_documentation_files_consistent_on_python_version(self) -> None:
        """
        Verify all documentation files consistently reference Python 3.10+.

        This test ensures that README.md, examples/README.md, and tech-stack.md
        all reference the same minimum Python version.

        **Validates: Requirements 1.4, 1.5, 2.5, 2.6, 3.5, 3.6, 5.1, 5.2, 5.3, 5.4**
        """
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        examples_readme_path = Path(__file__).parent.parent.parent / "examples" / "README.md"
        tech_stack_path = (
            Path(__file__).parent.parent.parent / ".kiro" / "steering" / "tech-stack.md"
        )

        # Read all documentation files
        with open(readme_path, encoding="utf-8") as f:
            readme_content = f.read()

        with open(examples_readme_path, encoding="utf-8") as f:
            examples_content = f.read()

        with open(tech_stack_path, encoding="utf-8") as f:
            tech_stack_content = f.read()

        # All should reference Python 3.10+
        assert "Python 3.10+" in readme_content, "README.md should reference 'Python 3.10+'"

        assert "Python 3.10+" in tech_stack_content, "tech-stack.md should reference 'Python 3.10+'"

        # None should reference Python 3.9+ as supported
        assert "Python 3.9+" not in readme_content, "README.md should not reference 'Python 3.9+'"

        assert (
            "python3.9" not in examples_content.lower()
        ), "examples/README.md should not reference 'python3.9'"

        assert (
            "Python 3.9+" not in tech_stack_content
        ), "tech-stack.md should not reference 'Python 3.9+'"
