"""
Alias generation strategies for model name resolution.

This module provides strategies for generating user-friendly aliases from
API-based model names. Each generator implements a specific strategy for
a particular model naming pattern.
"""

import re
from abc import ABC, abstractmethod
from typing import List, Set

from ...bedrock.models.unified_structures import UnifiedModelInfo
from .name_normalizer import normalize_model_name
from .name_resolution_structures import AliasGenerationConfig


class AliasGenerator(ABC):
    """
    Base class for alias generation strategies.

    This abstract class defines the interface for alias generators and provides
    common utility methods for alias manipulation.

    Attributes:
        config: Configuration controlling alias generation behavior
    """

    def __init__(self, config: AliasGenerationConfig) -> None:
        """
        Initialize the alias generator.

        Args:
            config: Configuration for alias generation
        """
        self.config = config

    @abstractmethod
    def can_generate(self, model_info: UnifiedModelInfo) -> bool:
        """
        Check if this generator can generate aliases for the given model.

        Args:
            model_info: Model information

        Returns:
            True if this generator can handle the model
        """
        pass

    @abstractmethod
    def generate(self, model_info: UnifiedModelInfo) -> List[str]:
        """
        Generate aliases for the given model.

        Args:
            model_info: Model information

        Returns:
            List of generated aliases (may be empty)
        """
        pass

    def _deduplicate_aliases(self, aliases: List[str]) -> List[str]:
        """
        Remove duplicate aliases while preserving order.

        Args:
            aliases: List of aliases (may contain duplicates)

        Returns:
            List of unique aliases in original order
        """
        seen: Set[str] = set()
        unique_aliases: List[str] = []

        for alias in aliases:
            # Normalize for comparison to catch case variations
            normalized = normalize_model_name(name=alias)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_aliases.append(alias)

        return unique_aliases

    def _enforce_alias_limit(self, aliases: List[str]) -> List[str]:
        """
        Enforce the maximum alias limit from configuration.

        Args:
            aliases: List of aliases

        Returns:
            List of aliases limited to max_aliases_per_model
        """
        return aliases[: self.config.max_aliases_per_model]

    def _remove_prefix(self, name: str, prefixes: List[str]) -> str:
        """
        Remove known prefixes from a model name.

        Args:
            name: Model name
            prefixes: List of prefixes to remove (e.g., ["APAC", "EU"])

        Returns:
            Model name with prefix removed (or original if no prefix found)
        """
        for prefix in prefixes:
            # Match prefix at start of string followed by space or hyphen
            pattern = rf"^{re.escape(prefix)}\s+"
            if re.match(pattern=pattern, string=name, flags=re.IGNORECASE):
                return re.sub(pattern=pattern, repl="", string=name, flags=re.IGNORECASE).strip()

        return name

    def _extract_version_number(self, text: str) -> str:
        """
        Extract version number from text.

        Looks for patterns like "3.5", "3 5", "4.5", etc.

        Args:
            text: Text containing version number

        Returns:
            Extracted version number (e.g., "3.5") or empty string if not found
        """
        # Match patterns like "3.5", "3 5", "4.5", "4 5"
        match = re.search(pattern=r"(\d+)[.\s]+(\d+)", string=text)
        if match:
            return f"{match.group(1)}.{match.group(2)}"

        # Match single digit version like "3"
        match = re.search(pattern=r"\b(\d+)\b", string=text)
        if match:
            return match.group(1)

        return ""

    def _normalize_version_in_name(self, name: str) -> str:
        """
        Normalize version numbers in a model name.

        Converts patterns like "4 5 20251001" to "4.5 20251001".

        Args:
            name: Model name with version numbers

        Returns:
            Model name with normalized version numbers
        """
        # Replace patterns like "4 5" with "4.5" (but not "4 5 20251001" → "4.5.20251001")
        # Only normalize the first two adjacent single digits
        normalized = re.sub(pattern=r"\b(\d)\s+(\d)\b", repl=r"\1.\2", string=name, count=1)
        return normalized


class ClaudeAliasGenerator(AliasGenerator):
    """
    Alias generator for Claude models.

    Generates aliases for Claude models following patterns like:
    - "Claude Haiku 4 5 20251001" → ["Claude 4.5 Haiku", "Claude Haiku 4.5", "Claude 4 Haiku"]

    This generator handles version number variations and different orderings
    of model variant names (Haiku, Sonnet, Opus).
    """

    # Known Claude model variants
    CLAUDE_VARIANTS = ["Haiku", "Sonnet", "Opus"]

    def can_generate(self, model_info: UnifiedModelInfo) -> bool:
        """
        Check if this is a Claude model.

        Args:
            model_info: Model information

        Returns:
            True if model name contains "Claude"
        """
        return "claude" in model_info.model_name.lower()

    def generate(self, model_info: UnifiedModelInfo) -> List[str]:
        """
        Generate aliases for Claude models.

        Args:
            model_info: Model information

        Returns:
            List of generated aliases
        """
        aliases: List[str] = []
        model_name = model_info.model_name

        # Extract variant (Haiku, Sonnet, Opus)
        variant = self._extract_variant(name=model_name)

        # Extract version number
        version = self._extract_version_number(text=model_name)

        if not variant or not version:
            # Can't generate meaningful aliases without variant and version
            return []

        # Generate version variants if configured
        if self.config.generate_version_variants:
            # Full version: "Claude 4.5 Haiku"
            # This is the primary alias format
            aliases.append(f"Claude {version} {variant}")

            # Only generate major version alias if it's different from full version
            # AND if the full version has a minor component (e.g., "3.5" → "3")
            # This avoids ambiguity with models that only have major versions
            major_version = version.split(".")[0]
            if "." in version and major_version != version:
                # Only add major version if it provides value
                # We skip this to avoid ambiguity
                pass

        # Generate spacing variants if configured
        if self.config.generate_spacing_variants:
            # No space between Claude and version: "Claude4.5 Haiku"
            aliases.append(f"Claude{version} {variant}")

        # Remove duplicates and enforce limit
        aliases = self._deduplicate_aliases(aliases=aliases)
        aliases = self._enforce_alias_limit(aliases=aliases)

        return aliases

    def _extract_variant(self, name: str) -> str:
        """
        Extract Claude variant from model name.

        Args:
            name: Model name

        Returns:
            Variant name (Haiku, Sonnet, Opus) or empty string if not found
        """
        name_lower = name.lower()
        for variant in self.CLAUDE_VARIANTS:
            if variant.lower() in name_lower:
                return variant
        return ""


class VersionedModelAliasGenerator(AliasGenerator):
    """
    Alias generator for versioned models (non-Claude).

    Generates aliases for models with version numbers like:
    - "Llama 3 8B Instruct" → ["Llama 3 8B Instruct", "Llama3 8B Instruct"]

    This generator handles spacing variations in version numbers.
    """

    def can_generate(self, model_info: UnifiedModelInfo) -> bool:
        """
        Check if this is a versioned model (non-Claude).

        Args:
            model_info: Model information

        Returns:
            True if model has version number and is not Claude
        """
        model_name = model_info.model_name
        has_version = bool(re.search(pattern=r"\d+", string=model_name))
        is_claude = "claude" in model_name.lower()
        return has_version and not is_claude

    def generate(self, model_info: UnifiedModelInfo) -> List[str]:
        """
        Generate aliases for versioned models.

        Args:
            model_info: Model information

        Returns:
            List of generated aliases
        """
        aliases: List[str] = []
        model_name = model_info.model_name

        # Generate spacing variants if configured
        if self.config.generate_spacing_variants:
            # Remove spaces between name and first number: "Llama 3" → "Llama3"
            no_space_variant = re.sub(
                pattern=r"([A-Za-z]+)\s+(\d+)", repl=r"\1\2", string=model_name, count=1
            )
            if no_space_variant != model_name:
                aliases.append(no_space_variant)

            # Also add the original name as an alias
            aliases.append(model_name)

        # Normalize version numbers if configured
        if self.config.generate_version_variants:
            normalized = self._normalize_version_in_name(name=model_name)
            if normalized != model_name:
                aliases.append(normalized)

        # Remove duplicates and enforce limit
        aliases = self._deduplicate_aliases(aliases=aliases)
        aliases = self._enforce_alias_limit(aliases=aliases)

        return aliases


class PrefixedModelAliasGenerator(AliasGenerator):
    """
    Alias generator for provider-prefixed models.

    Generates aliases for models with regional or provider prefixes like:
    - "APAC Anthropic Claude 3 Haiku" → ["APAC Claude 3 Haiku", "Claude 3 Haiku"]

    This generator creates both prefixed and unprefixed variants.
    """

    # Known prefixes to remove
    KNOWN_PREFIXES = [
        "APAC",
        "EU",
        "US",
        "Anthropic",
        "Amazon",
        "Meta",
        "Cohere",
        "AI21",
        "Mistral",
        "Stability",
    ]

    def can_generate(self, model_info: UnifiedModelInfo) -> bool:
        """
        Check if this model has a known prefix.

        Args:
            model_info: Model information

        Returns:
            True if model name starts with a known prefix
        """
        model_name = model_info.model_name
        for prefix in self.KNOWN_PREFIXES:
            pattern = rf"^{re.escape(prefix)}\s+"
            if re.match(pattern=pattern, string=model_name, flags=re.IGNORECASE):
                return True
        return False

    def generate(self, model_info: UnifiedModelInfo) -> List[str]:
        """
        Generate aliases for prefixed models.

        Args:
            model_info: Model information

        Returns:
            List of generated aliases
        """
        aliases: List[str] = []
        model_name = model_info.model_name

        # Generate no-prefix variants if configured
        if self.config.generate_no_prefix_variants:
            # Remove regional prefixes (APAC, EU, US)
            regional_prefixes = ["APAC", "EU", "US"]
            no_regional = self._remove_prefix(name=model_name, prefixes=regional_prefixes)
            if no_regional != model_name:
                aliases.append(no_regional)

            # Remove provider prefixes (Anthropic, Amazon, etc.)
            provider_prefixes = [
                "Anthropic",
                "Amazon",
                "Meta",
                "Cohere",
                "AI21",
                "Mistral",
                "Stability",
            ]
            no_provider = self._remove_prefix(name=no_regional, prefixes=provider_prefixes)
            if no_provider != no_regional:
                aliases.append(no_provider)

            # Also try removing provider from original name
            no_provider_original = self._remove_prefix(name=model_name, prefixes=provider_prefixes)
            if no_provider_original != model_name:
                aliases.append(no_provider_original)

        # Remove duplicates and enforce limit
        aliases = self._deduplicate_aliases(aliases=aliases)
        aliases = self._enforce_alias_limit(aliases=aliases)

        return aliases
