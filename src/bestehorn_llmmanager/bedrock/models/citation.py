"""
Typed document citation parsed from a Bedrock Converse response.

Defines :class:`Citation`, the typed view of a single ``Citation`` returned inside a
``citationsContent`` block when document citations are enabled, so callers can read the
source title / location / referenced spans without hand-navigating the raw response dict.

References:
- CitationsContentBlock (citations[], content[]):
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_CitationsContentBlock.html
- Citation (title, source, sourceContent[], location):
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Citation.html
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .llm_manager_constants import ConverseAPIFields


@dataclass(frozen=True)
class Citation:
    """
    A single citation referencing a source document.

    Provides traceability between the model's generated content and the source documents
    that informed it.

    Attributes:
        title: The title or identifier of the cited source document, if provided.
        source: The source (from the original search result) that provided the cited
            content, if provided.
        source_content: The specific source spans that were referenced — a list of
            ``CitationSourceContent`` dicts (typically ``{"text": ...}``).
        location: The precise location within the source document (a ``CitationLocation``
            union dict — character positions, page numbers, or chunk identifiers), if
            provided.
    """

    title: Optional[str] = None
    source: Optional[str] = None
    source_content: List[Dict[str, Any]] = field(default_factory=list)
    location: Optional[Dict[str, Any]] = None

    @classmethod
    def from_citation(cls, citation: Dict[str, Any]) -> "Citation":
        """
        Build a :class:`Citation` from a raw ``Citation`` dict.

        Args:
            citation: A single ``Citation`` object from a ``citationsContent`` block.

        Returns:
            The typed :class:`Citation`. Missing fields default to ``None`` / empty list.
        """
        source_content = citation.get(ConverseAPIFields.CITATION_SOURCE_CONTENT) or []
        return cls(
            title=citation.get(ConverseAPIFields.CITATION_TITLE),
            source=citation.get(ConverseAPIFields.CITATION_SOURCE),
            source_content=list(source_content),
            location=citation.get(ConverseAPIFields.CITATION_LOCATION),
        )
