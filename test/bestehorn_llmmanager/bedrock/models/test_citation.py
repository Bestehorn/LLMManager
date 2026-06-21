"""
Tests for the Citation typed document-citation object (issue #40).
"""

from bestehorn_llmmanager.bedrock.models.citation import Citation


class TestCitationFromCitation:
    """Parse a Citation from a raw Citation dict."""

    def test_full_citation(self):
        raw = {
            "title": "Annual Report",
            "source": "doc-1",
            "sourceContent": [{"text": "Revenue grew 12%."}],
            "location": {"documentChar": {"start": 100, "end": 117}},
        }
        citation = Citation.from_citation(citation=raw)
        assert citation.title == "Annual Report"
        assert citation.source == "doc-1"
        assert citation.source_content == [{"text": "Revenue grew 12%."}]
        assert citation.location == {"documentChar": {"start": 100, "end": 117}}

    def test_minimal_citation(self):
        citation = Citation.from_citation(citation={"title": "Doc"})
        assert citation.title == "Doc"
        assert citation.source is None
        assert citation.source_content == []
        assert citation.location is None

    def test_empty_citation(self):
        citation = Citation.from_citation(citation={})
        assert citation.title is None
        assert citation.source_content == []

    def test_is_frozen(self):
        import dataclasses

        import pytest

        citation = Citation(title="Doc")
        with pytest.raises(dataclasses.FrozenInstanceError):
            citation.title = "Other"  # type: ignore[misc]
