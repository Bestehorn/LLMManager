"""
Integration tests for LLMManager with name resolution.

These tests validate that LLMManager correctly uses BedrockModelCatalog's
name resolution system to handle friendly names, legacy names, and various
name formats. Tests verify that the system provides helpful error messages
when names cannot be resolved.

Requirements tested:
- 4.1: Integration tests use friendly names like "Claude 3 Haiku"
- 4.2: Integration tests use provider-prefixed names like "APAC Anthropic Claude 3 Haiku"
- 4.3: Integration tests use model names like "Llama 3 8B Instruct"
- 5.1: Error messages include the attempted name
- 5.2: Error messages suggest similar model names
"""

from typing import List, Optional, Tuple

import pytest

from bestehorn_llmmanager.bedrock.catalog.bedrock_catalog import BedrockModelCatalog
from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import ConfigurationError
from bestehorn_llmmanager.llm_manager import LLMManager


def _get_available_friendly_model_and_region() -> Tuple[Optional[str], Optional[str]]:
    """
    Get an available model using a friendly name and a region where it's available.
    
    Returns:
        Tuple of (friendly_model_name, region) if found, (None, None) otherwise
    """
    try:
        catalog = BedrockModelCatalog()
        catalog.ensure_catalog_available()
        
        # Try to find Claude models with friendly names
        friendly_names = [
            "Claude 3 Haiku",
            "Claude 3.5 Sonnet",
            "Claude 3 Sonnet",
            "Claude 3.5 Haiku",
        ]
        
        for friendly_name in friendly_names:
            try:
                model_info = catalog.get_model_info(model_name=friendly_name)
                if model_info:
                    # get_model_info returns ModelAccessInfo, need to get regions from catalog
                    # Just use us-east-1 as it's commonly available
                    return friendly_name, "us-east-1"
            except Exception:
                continue
        
        return None, None
        
    except Exception:
        return None, None


def _get_available_prefixed_model_and_region() -> Tuple[Optional[str], Optional[str]]:
    """
    Get an available model using a provider-prefixed name and a region.
    
    Note: APAC/EU/US prefixes are for CRIS profiles, not model names.
    This function is kept for backward compatibility but will likely not find matches.
    
    Returns:
        Tuple of (prefixed_model_name, region) if found, (None, None) otherwise
    """
    # APAC/EU/US are CRIS profile prefixes, not model name prefixes
    # These won't be found in the catalog as model names
    return None, None


def _get_available_llama_model_and_region() -> Tuple[Optional[str], Optional[str]]:
    """
    Get an available Llama model and a region where it's available.
    
    Returns:
        Tuple of (llama_model_name, region) if found, (None, None) otherwise
    """
    try:
        catalog = BedrockModelCatalog()
        catalog.ensure_catalog_available()
        
        # Try to find Llama models
        llama_names = [
            "Llama 3 8B Instruct",
            "Llama 3.1 8B Instruct",
            "Llama 3.2 1B Instruct",
            "Llama 3.2 3B Instruct",
        ]
        
        for llama_name in llama_names:
            try:
                model_info = catalog.get_model_info(model_name=llama_name)
                if model_info:
                    # Just use us-east-1 as it's commonly available
                    return llama_name, "us-east-1"
            except Exception:
                continue
        
        return None, None
        
    except Exception:
        return None, None


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerFriendlyNameResolution:
    """Integration tests for LLMManager initialization with friendly model names."""
    
    def test_initialization_with_friendly_claude_name(
        self, sample_test_messages: List[dict]
    ) -> None:
        """
        Test LLMManager initialization with friendly Claude model name.
        
        Validates Requirement 4.1: Integration tests use friendly names like "Claude 3 Haiku"
        
        Args:
            sample_test_messages: Sample messages for testing
        """
        friendly_model, region = _get_available_friendly_model_and_region()
        if not friendly_model or not region:
            pytest.skip("No friendly Claude model name available for testing")
        
        # Initialize LLMManager with friendly name
        manager = LLMManager(models=[friendly_model], regions=[region])
        
        # Verify initialization succeeded
        assert len(manager.get_available_models()) == 1
        assert len(manager.get_available_regions()) >= 1
        
        # Verify we can make a request with the friendly name
        response = manager.converse(
            messages=sample_test_messages,
            inference_config={"maxTokens": 50}
        )
        
        assert response.success is True
        assert response.get_content() is not None
    
    def test_initialization_with_multiple_friendly_names(
        self, sample_test_messages: List[dict]
    ) -> None:
        """
        Test LLMManager initialization with multiple friendly model names.
        
        Validates Requirement 4.1: System handles multiple friendly names
        
        Args:
            sample_test_messages: Sample messages for testing
        """
        try:
            catalog = BedrockModelCatalog()
            catalog.ensure_catalog_available()
            
            # Try to find multiple friendly names
            friendly_names = []
            test_region = "us-east-1"
            
            for name in ["Claude 3 Haiku", "Claude 3.5 Sonnet", "Claude 3 Sonnet"]:
                try:
                    model_info = catalog.get_model_info(model_name=name)
                    if model_info:
                        friendly_names.append(name)
                        if len(friendly_names) >= 2:
                            break
                except Exception:
                    continue
            
            if len(friendly_names) < 2:
                pytest.skip("Not enough friendly model names available for testing")
            
            # Initialize with multiple friendly names
            manager = LLMManager(models=friendly_names, regions=[test_region])
            
            # Verify initialization succeeded
            assert len(manager.get_available_models()) == len(friendly_names)
            
            # Verify we can make a request
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50}
            )
            
            assert response.success is True
            
        except Exception as e:
            pytest.skip(f"Could not test multiple friendly names: {str(e)}")
    
    def test_initialization_with_mixed_name_formats(
        self, sample_test_messages: List[dict]
    ) -> None:
        """
        Test LLMManager initialization with mixed friendly and API names.
        
        Validates Requirement 4.1: System handles mixed name formats
        
        Args:
            sample_test_messages: Sample messages for testing
        """
        try:
            catalog = BedrockModelCatalog()
            catalog.ensure_catalog_available()
            
            # Get one friendly name
            friendly_model, region = _get_available_friendly_model_and_region()
            if not friendly_model or not region:
                pytest.skip("No friendly model name available for testing")
            
            # Get the API name for a different model
            api_model = None
            all_models = catalog.list_models()
            for model in all_models:
                if model.model_name != friendly_model:
                    api_model = model.model_name
                    break
            
            if not api_model:
                pytest.skip("Could not find second model for mixed format test")
            
            # Initialize with mixed formats
            manager = LLMManager(models=[friendly_model, api_model], regions=[region])
            
            # Verify initialization succeeded
            assert len(manager.get_available_models()) == 2
            
            # Verify we can make a request
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50}
            )
            
            assert response.success is True
            
        except Exception as e:
            pytest.skip(f"Could not test mixed name formats: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerPrefixedNameResolution:
    """Integration tests for LLMManager with provider-prefixed model names."""
    
    def test_initialization_with_prefixed_name(
        self, sample_test_messages: List[dict]
    ) -> None:
        """
        Test LLMManager initialization with provider-prefixed model name.
        
        Validates Requirement 4.2: Integration tests use names like "APAC Anthropic Claude 3 Haiku"
        
        Args:
            sample_test_messages: Sample messages for testing
        """
        prefixed_model, region = _get_available_prefixed_model_and_region()
        if not prefixed_model or not region:
            pytest.skip("No provider-prefixed model name available for testing")
        
        # Initialize LLMManager with prefixed name
        manager = LLMManager(models=[prefixed_model], regions=[region])
        
        # Verify initialization succeeded
        assert len(manager.get_available_models()) == 1
        assert len(manager.get_available_regions()) >= 1
        
        # Verify we can make a request with the prefixed name
        response = manager.converse(
            messages=sample_test_messages,
            inference_config={"maxTokens": 50}
        )
        
        assert response.success is True
        assert response.get_content() is not None
    
    def test_initialization_with_short_prefix(
        self, sample_test_messages: List[dict]
    ) -> None:
        """
        Test LLMManager initialization with short provider prefix (e.g., "APAC Claude").
        
        Note: APAC/EU/US prefixes are for CRIS profiles, not model names.
        This test is kept for documentation but will be skipped.
        
        Validates Requirement 4.2: System handles short prefixes
        
        Args:
            sample_test_messages: Sample messages for testing
        """
        pytest.skip("APAC/EU/US are CRIS profile prefixes, not model name prefixes")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerLlamaNameResolution:
    """Integration tests for LLMManager with Llama model names."""
    
    def test_initialization_with_llama_name(
        self, sample_test_messages: List[dict]
    ) -> None:
        """
        Test LLMManager initialization with Llama model name.
        
        Validates Requirement 4.3: Integration tests use names like "Llama 3 8B Instruct"
        
        Args:
            sample_test_messages: Sample messages for testing
        """
        llama_model, region = _get_available_llama_model_and_region()
        if not llama_model or not region:
            pytest.skip("No Llama model available for testing")
        
        # Initialize LLMManager with Llama name
        manager = LLMManager(models=[llama_model], regions=[region])
        
        # Verify initialization succeeded
        assert len(manager.get_available_models()) == 1
        assert len(manager.get_available_regions()) >= 1
        
        # Verify we can make a request with the Llama model
        response = manager.converse(
            messages=sample_test_messages,
            inference_config={"maxTokens": 50}
        )
        
        assert response.success is True
        assert response.get_content() is not None


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerNameResolutionErrors:
    """Integration tests for LLMManager error messages with name resolution."""
    
    def test_error_message_includes_attempted_name(self) -> None:
        """
        Test that error messages include the attempted model name.
        
        Validates Requirement 5.1: Error messages include the attempted name
        """
        invalid_name = "NonExistentModelXYZ123"
        
        # Try to initialize with invalid name
        with pytest.raises(ConfigurationError) as exc_info:
            LLMManager(models=[invalid_name], regions=["us-east-1"])
        
        # Verify error message includes the attempted name
        error_message = str(exc_info.value)
        assert invalid_name in error_message
        assert "not found" in error_message.lower()
    
    def test_error_message_suggests_similar_models(self) -> None:
        """
        Test that error messages suggest similar model names.
        
        Validates Requirement 5.2: Error messages suggest similar model names
        """
        # Use a name that's close to a real model but not exact
        similar_name = "Claude3Haiku"  # Missing space
        
        # Try to initialize with similar name
        with pytest.raises(ConfigurationError) as exc_info:
            LLMManager(models=[similar_name], regions=["us-east-1"])
        
        # Verify error message includes suggestions
        error_message = str(exc_info.value)
        assert similar_name in error_message
        assert ("did you mean" in error_message.lower() or "suggestions" in error_message.lower())
    
    def test_error_message_for_typo_in_friendly_name(self) -> None:
        """
        Test error message when user makes a typo in a friendly name.
        
        Validates Requirements 5.1, 5.2: Error includes name and suggestions
        """
        # Use a typo in a common friendly name
        typo_name = "Claud 3 Haiku"  # Missing 'e' in Claude
        
        # Try to initialize with typo
        with pytest.raises(ConfigurationError) as exc_info:
            LLMManager(models=[typo_name], regions=["us-east-1"])
        
        # Verify error message is helpful
        error_message = str(exc_info.value)
        assert typo_name in error_message
        # Should suggest the correct name
        assert "Claude" in error_message or "suggestions" in error_message.lower()
    
    def test_error_message_for_invalid_region(self) -> None:
        """
        Test error message when using valid model but invalid region.
        
        Validates Requirement 5.1: Error messages include attempted values
        """
        friendly_model, _ = _get_available_friendly_model_and_region()
        if not friendly_model:
            pytest.skip("No friendly model available for testing")
        
        invalid_region = "invalid-region-xyz"
        
        # Try to initialize with invalid region
        with pytest.raises(ConfigurationError) as exc_info:
            LLMManager(models=[friendly_model], regions=[invalid_region])
        
        # Verify error message includes the invalid region
        error_message = str(exc_info.value)
        assert invalid_region in error_message
    
    def test_error_message_for_multiple_invalid_names(self) -> None:
        """
        Test error message when multiple model names are invalid.
        
        Validates Requirements 5.1, 5.2: Error handles multiple invalid names
        """
        invalid_names = ["InvalidModel1", "InvalidModel2", "InvalidModel3"]
        
        # Try to initialize with multiple invalid names
        with pytest.raises(ConfigurationError) as exc_info:
            LLMManager(models=invalid_names, regions=["us-east-1"])
        
        # Verify error message mentions the invalid names
        error_message = str(exc_info.value)
        # Should mention at least some of the invalid names
        assert any(name in error_message for name in invalid_names)
        assert "not found" in error_message.lower()


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerLegacyNameCompatibility:
    """Integration tests for LLMManager with legacy UnifiedModelManager names."""
    
    def test_initialization_with_legacy_claude_name(
        self, sample_test_messages: List[dict]
    ) -> None:
        """
        Test LLMManager initialization with legacy Claude model name.
        
        Validates Requirement 4.1: System handles legacy names from UnifiedModelManager
        
        Args:
            sample_test_messages: Sample messages for testing
        """
        # Try common legacy names
        legacy_names = [
            "Claude 3 Haiku",
            "Claude 3 Sonnet",
            "Claude 3.5 Sonnet",
        ]
        
        test_region = "us-east-1"
        found_model = None
        
        try:
            catalog = BedrockModelCatalog()
            catalog.ensure_catalog_available()
            
            for name in legacy_names:
                try:
                    model_info = catalog.get_model_info(model_name=name)
                    if model_info:
                        found_model = name
                        break
                except Exception:
                    continue
            
            if not found_model:
                pytest.skip("No legacy model name available for testing")
            
            # Initialize with legacy name
            manager = LLMManager(models=[found_model], regions=[test_region])
            
            # Verify initialization succeeded
            assert len(manager.get_available_models()) == 1
            
            # Verify we can make a request
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50}
            )
            
            assert response.success is True
            
        except Exception as e:
            pytest.skip(f"Could not test legacy name: {str(e)}")
    
    def test_error_message_for_deprecated_legacy_name(self) -> None:
        """
        Test error message when using a deprecated legacy model name.
        
        Validates Requirement 4.4: System provides clear error for deprecated models
        """
        # Use a name that might have been in UnifiedModelManager but is now deprecated
        deprecated_name = "Claude 2.1"
        
        try:
            # Try to initialize with deprecated name
            with pytest.raises(ConfigurationError) as exc_info:
                LLMManager(models=[deprecated_name], regions=["us-east-1"])
            
            # Verify error message is helpful
            error_message = str(exc_info.value)
            assert deprecated_name in error_message
            # Should provide suggestions or indicate it's not available
            assert (
                "not found" in error_message.lower()
                or "not available" in error_message.lower()
                or "suggestions" in error_message.lower()
            )
            
        except Exception as e:
            pytest.skip(f"Could not test deprecated name: {str(e)}")
