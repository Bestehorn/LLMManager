"""
Model name resolver for user-friendly model name resolution.

This module provides the ModelNameResolver class that resolves user-provided
model names to canonical model names using multiple strategies including
exact matching, alias matching, legacy name mapping, and fuzzy matching.
"""

import difflib
from typing import Dict, List, Optional, Set

from ...bedrock.models.catalog_structures import UnifiedCatalog
from ...bedrock.models.unified_structures import UnifiedModelInfo
from .alias_generators import (
    AliasGenerator,
    ClaudeAliasGenerator,
    PrefixedModelAliasGenerator,
    VersionedModelAliasGenerator,
    VersionPeriodAliasGenerator,
)
from .legacy_name_mapper import LegacyNameMapper
from .name_normalizer import normalize_model_name
from .name_resolution_structures import (
    AliasGenerationConfig,
    MatchType,
    ModelNameMatch,
)


class ModelNameResolver:
    """
    Resolves user-provided model names to canonical model names.

    This class provides comprehensive model name resolution supporting:
    - Exact matches (API names)
    - Friendly aliases (generated)
    - Legacy UnifiedModelManager names
    - Normalized matching (spacing/punctuation variations)
    - Fuzzy matching (partial names)

    The resolver uses lazy initialization to build indexes on first query,
    minimizing startup cost.

    Attributes:
        _catalog: The unified catalog containing model information
        _config: Configuration for alias generation
        _legacy_mapper: Mapper for legacy UnifiedModelManager names
        _alias_generators: List of alias generation strategies
        _name_index: Index mapping aliases to canonical names (lazy)
        _normalized_index: Index mapping normalized names to canonical names (lazy)
        _indexes_built: Flag indicating if indexes have been built
    """

    def __init__(
        self,
        catalog: UnifiedCatalog,
        config: Optional[AliasGenerationConfig] = None,
    ) -> None:
        """
        Initialize the model name resolver.

        Args:
            catalog: Unified catalog containing model information
            config: Configuration for alias generation (uses defaults if None)
        """
        self._catalog = catalog
        self._config = config if config is not None else AliasGenerationConfig()
        self._legacy_mapper = LegacyNameMapper()

        # Initialize alias generators
        self._alias_generators: List[AliasGenerator] = [
            ClaudeAliasGenerator(config=self._config),
            VersionedModelAliasGenerator(config=self._config),
            PrefixedModelAliasGenerator(config=self._config),
            VersionPeriodAliasGenerator(config=self._config),
        ]

        # Lazy-initialized indexes
        self._name_index: Optional[Dict[str, str]] = None
        self._normalized_index: Optional[Dict[str, List[str]]] = None
        self._indexes_built: bool = False

    def _ensure_indexes_built(self) -> None:
        """
        Ensure indexes are built before use.

        This method is called before any index access to lazily build
        the indexes on first use.
        """
        if not self._indexes_built:
            self._build_indexes()
            self._indexes_built = True

    def _build_indexes(self) -> None:
        """
        Build all indexes for fast name resolution.

        This method is called lazily on first query to build:
        - Name index (alias → canonical)
        - Normalized index (normalized → canonicals)
        - Legacy mapping integration

        The indexes enable fast O(1) lookups for exact and normalized matches.
        """
        # Initialize indexes
        self._name_index = {}
        self._normalized_index = {}

        # Build indexes for all models in catalog
        for canonical_name, model_info in self._catalog.models.items():
            # Add canonical name to indexes
            self._add_to_indexes(
                alias=canonical_name,
                canonical_name=canonical_name,
            )

            # Generate and add aliases
            aliases = self.generate_aliases(model_info=model_info)
            for alias in aliases:
                self._add_to_indexes(
                    alias=alias,
                    canonical_name=canonical_name,
                )

        # Integrate legacy mappings into indexes
        self._integrate_legacy_mappings()

    def _add_to_indexes(self, alias: str, canonical_name: str) -> None:
        """
        Add an alias to the indexes.

        Args:
            alias: Alias to add
            canonical_name: Canonical model name this alias maps to
        """
        if self._name_index is None or self._normalized_index is None:
            return

        # Add to name index (exact match)
        # Only add if not already present to avoid overwriting
        if alias not in self._name_index:
            self._name_index[alias] = canonical_name

        # Add to normalized index (flexible match)
        normalized = normalize_model_name(name=alias)
        if normalized:
            if normalized not in self._normalized_index:
                self._normalized_index[normalized] = []
            # Only add if not already in list
            if canonical_name not in self._normalized_index[normalized]:
                self._normalized_index[normalized].append(canonical_name)

    def resolve_name(
        self,
        user_name: str,
        strict: bool = False,
    ) -> Optional[ModelNameMatch]:
        """
        Resolve user-provided name to canonical model name.

        Resolution is attempted in the following order:
        1. Exact match to canonical name
        2. Alias match (generated aliases)
        3. Legacy match (UnifiedModelManager names)
        4. Normalized match (spacing/punctuation variations)
        5. Fuzzy match (partial names, only if not strict)

        Args:
            user_name: Name provided by user
            strict: If True, only exact/alias/legacy matches (no fuzzy)

        Returns:
            ModelNameMatch if found, None otherwise
        """
        # Ensure indexes are built
        self._ensure_indexes_built()

        if not user_name or not user_name.strip():
            return None

        # Safety check for indexes
        if self._name_index is None or self._normalized_index is None:
            return None

        # 1. Try exact match to canonical name
        if user_name in self._catalog.models:
            return ModelNameMatch(
                canonical_name=user_name,
                match_type=MatchType.EXACT,
                confidence=1.0,
                user_input=user_name,
            )

        # 2. Try alias match (case-sensitive first)
        if user_name in self._name_index:
            canonical_name = self._name_index[user_name]
            return ModelNameMatch(
                canonical_name=canonical_name,
                match_type=MatchType.ALIAS,
                confidence=1.0,
                user_input=user_name,
            )

        # 3. Try legacy match
        legacy_result = self._try_legacy_match(user_name=user_name)
        if legacy_result:
            return legacy_result

        # 4. Try normalized match (case-insensitive, spacing variations)
        normalized_result = self._try_normalized_match(user_name=user_name)
        if normalized_result:
            return normalized_result

        # 5. Try fuzzy match (only if not strict)
        if not strict:
            fuzzy_result = self._try_fuzzy_match(user_name=user_name)
            if fuzzy_result:
                return fuzzy_result

        # No match found
        return None

    def _try_legacy_match(self, user_name: str) -> Optional[ModelNameMatch]:
        """
        Try to match using legacy UnifiedModelManager names.

        Args:
            user_name: User-provided name

        Returns:
            ModelNameMatch if legacy match found, None otherwise
        """
        catalog_name = self._legacy_mapper.resolve_legacy_name(user_name=user_name)

        # Verify the catalog name exists in current catalog
        if catalog_name and catalog_name in self._catalog.models:
            return ModelNameMatch(
                canonical_name=catalog_name,
                match_type=MatchType.LEGACY,
                confidence=1.0,
                user_input=user_name,
            )

        return None

    def _try_normalized_match(self, user_name: str) -> Optional[ModelNameMatch]:
        """
        Try to match using normalized name (case-insensitive, spacing variations).

        This method attempts two types of normalized matching:
        1. Exact normalized match (highest confidence)
        2. Substring match in normalized keys (for partial names like "Claude Sonnet 4.5")

        Args:
            user_name: User-provided name

        Returns:
            ModelNameMatch if normalized match found, None otherwise
        """
        if self._normalized_index is None:
            return None

        normalized = normalize_model_name(name=user_name)
        if not normalized:
            return None

        # Try exact normalized match first
        if normalized in self._normalized_index:
            matches = self._normalized_index[normalized]

            # If exactly one match, return it
            if len(matches) == 1:
                return ModelNameMatch(
                    canonical_name=matches[0],
                    match_type=MatchType.NORMALIZED,
                    confidence=0.95,  # Slightly lower than exact match
                    user_input=user_name,
                )

            # If multiple matches, this is ambiguous - return None
            # The caller should use get_suggestions() to see all options
            return None

        # Try substring matching in normalized index keys
        # This handles cases like "claude sonnet 45" matching "claude sonnet 45 20250929"
        matching_keys: List[str] = []
        for key in self._normalized_index.keys():
            # Check if user input is a substring of the catalog name
            # This allows "Claude Sonnet 4.5" to match "Claude Sonnet 4 5 20250929"
            if normalized in key:
                matching_keys.append(key)

        # If exactly one substring match, use it
        if len(matching_keys) == 1:
            matches = self._normalized_index[matching_keys[0]]

            # If the key maps to exactly one model, return it
            if len(matches) == 1:
                return ModelNameMatch(
                    canonical_name=matches[0],
                    match_type=MatchType.NORMALIZED,
                    confidence=0.90,  # Lower than exact, but still high confidence
                    user_input=user_name,
                )

        # Multiple matches or no matches - return None
        return None

    def _try_fuzzy_match(self, user_name: str) -> Optional[ModelNameMatch]:
        """
        Try to match using fuzzy search (substring and similarity).

        Args:
            user_name: User-provided name

        Returns:
            ModelNameMatch if fuzzy match found with high confidence, None otherwise
        """
        # Get all canonical model names
        all_names = list(self._catalog.models.keys())

        # Try substring matching first (faster)
        user_lower = user_name.lower()
        substring_matches = [
            name for name in all_names if user_lower in name.lower() or name.lower() in user_lower
        ]

        if len(substring_matches) == 1:
            # Single substring match - high confidence
            return ModelNameMatch(
                canonical_name=substring_matches[0],
                match_type=MatchType.FUZZY,
                confidence=0.85,
                user_input=user_name,
            )

        # Try similarity matching using difflib
        # Get close matches with cutoff of 0.6 (60% similarity)
        close_matches = difflib.get_close_matches(
            word=user_name,
            possibilities=all_names,
            n=1,  # Only get the best match
            cutoff=0.6,
        )

        if close_matches:
            # Calculate actual similarity ratio for confidence
            best_match = close_matches[0]
            similarity = difflib.SequenceMatcher(
                a=user_name.lower(),
                b=best_match.lower(),
            ).ratio()

            # Only return if similarity is high enough
            if similarity >= 0.7:
                return ModelNameMatch(
                    canonical_name=best_match,
                    match_type=MatchType.FUZZY,
                    confidence=similarity * 0.9,  # Scale down slightly for fuzzy
                    user_input=user_name,
                )

        return None

    def get_suggestions(
        self,
        user_name: str,
        max_suggestions: int = 5,
    ) -> List[str]:
        """
        Get suggested model names for failed resolution.

        Suggestions are generated using:
        - Edit distance (Levenshtein distance via difflib)
        - Substring matching
        - Ranked by relevance (similarity score)

        Args:
            user_name: Name that failed to resolve
            max_suggestions: Maximum suggestions to return

        Returns:
            List of suggested model names (may be empty)
        """
        # Ensure indexes are built
        self._ensure_indexes_built()

        if not user_name or not user_name.strip():
            return []

        # Get all canonical model names
        all_names = list(self._catalog.models.keys())

        # Calculate similarity scores for all models
        scored_suggestions: List[tuple[str, float]] = []

        user_lower = user_name.lower()
        user_normalized = normalize_model_name(name=user_name)

        # Set minimum threshold based on input length to match test expectations
        # For very short inputs (< 5 chars), use lower threshold (0.2)
        # For longer inputs, use higher threshold (0.3)
        # This ensures suggestions are relevant and filters out noise
        min_length = len(user_name.strip())
        min_threshold = 0.2 if min_length < 5 else 0.3

        for model_name in all_names:
            score = self._calculate_similarity_score(
                user_name=user_name,
                user_lower=user_lower,
                user_normalized=user_normalized,
                model_name=model_name,
            )

            # Only include suggestions above minimum threshold
            if score >= min_threshold:
                scored_suggestions.append((model_name, score))

        # Sort by score (descending) and take top N
        scored_suggestions.sort(key=lambda x: x[1], reverse=True)
        suggestions = [name for name, _ in scored_suggestions[:max_suggestions]]

        return suggestions

    def _calculate_similarity_score(
        self,
        user_name: str,
        user_lower: str,
        user_normalized: str,
        model_name: str,
    ) -> float:
        """
        Calculate similarity score between user input and model name.

        Uses multiple heuristics:
        - Exact substring match: 1.0
        - Normalized match: 0.95
        - Sequence similarity: 0.0-0.9
        - Substring in either direction: bonus

        Args:
            user_name: Original user input
            user_lower: Lowercase user input
            user_normalized: Normalized user input
            model_name: Model name to compare against

        Returns:
            Similarity score (0.0-1.0)
        """
        model_lower = model_name.lower()
        model_normalized = normalize_model_name(name=model_name)

        # Exact match (shouldn't happen in suggestions, but handle it)
        if user_name == model_name:
            return 1.0

        # Exact normalized match
        if user_normalized and model_normalized and user_normalized == model_normalized:
            return 0.95

        # Substring matching (either direction)
        if user_lower in model_lower:
            # User input is substring of model name
            # Give high score for substring matches (0.7-0.9 range)
            # This ensures substring matches pass the threshold
            ratio = len(user_lower) / len(model_lower)
            return 0.7 + (ratio * 0.2)  # Range: 0.7-0.9

        if model_lower in user_lower:
            # Model name is substring of user input
            # Score based on how much of the user input is matched
            return 0.85 * (len(model_lower) / len(user_lower))

        # Sequence similarity using difflib
        similarity = difflib.SequenceMatcher(
            a=user_lower,
            b=model_lower,
        ).ratio()

        # Scale similarity to 0.0-0.8 range (leave room for substring matches)
        return similarity * 0.8

    def generate_aliases(self, model_info: UnifiedModelInfo) -> List[str]:
        """
        Generate friendly aliases for a model.

        Applies all configured alias generation strategies and returns
        a deduplicated list of aliases limited by max_aliases_per_model.

        Args:
            model_info: Model information

        Returns:
            List of friendly alias names (may be empty)
        """
        all_aliases: List[str] = []

        # Apply each alias generator that can handle this model
        for generator in self._alias_generators:
            if generator.can_generate(model_info=model_info):
                aliases = generator.generate(model_info=model_info)
                all_aliases.extend(aliases)

        # Deduplicate aliases (case-insensitive)
        unique_aliases = self._deduplicate_aliases(aliases=all_aliases)

        # Enforce alias limit
        limited_aliases = unique_aliases[: self._config.max_aliases_per_model]

        return limited_aliases

    def _deduplicate_aliases(self, aliases: List[str]) -> List[str]:
        """
        Remove duplicate aliases while preserving order.

        Uses normalized comparison to catch case and spacing variations.

        Args:
            aliases: List of aliases (may contain duplicates)

        Returns:
            List of unique aliases in original order
        """
        seen: Set[str] = set()
        unique_aliases: List[str] = []

        for alias in aliases:
            # Normalize for comparison to catch case/spacing variations
            normalized = normalize_model_name(name=alias)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_aliases.append(alias)

        return unique_aliases

    def _integrate_legacy_mappings(self) -> None:
        """
        Integrate legacy UnifiedModelManager name mappings into indexes.

        This method adds legacy names to the indexes so they can be resolved
        to current catalog names. Only adds mappings for models that exist
        in the current catalog.
        """
        if self._name_index is None or self._normalized_index is None:
            return

        # Get all legacy mappings
        for legacy_name in self._legacy_mapper.get_all_legacy_names():
            # Resolve legacy name to catalog name
            catalog_name = self._legacy_mapper.resolve_legacy_name(user_name=legacy_name)

            # Only add if the catalog name exists in current catalog
            if catalog_name and catalog_name in self._catalog.models:
                # Add legacy name to indexes
                self._add_to_indexes(
                    alias=legacy_name,
                    canonical_name=catalog_name,
                )
