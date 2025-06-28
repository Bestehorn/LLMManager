"""
Unit tests for bedrock.models.cris_regional_structures module.
Tests for CRISRegionalVariant and CRISMultiRegionalModel classes.
"""

from unittest.mock import patch

import pytest

from bestehorn_llmmanager.bedrock.models.cris_constants import (
    CRISErrorMessages,
    CRISJSONFields,
    CRISRegionPrefixes,
    CRISValidationPatterns,
)
from bestehorn_llmmanager.bedrock.models.cris_regional_structures import (
    CRISMultiRegionalModel,
    CRISMultiRegionalModelDict,
    CRISRegionalVariant,
    CRISRegionalVariantDict,
    CRISRegionPrefix,
    RegionalVariantsMap,
)


class TestCRISRegionalVariant:
    """Test cases for CRISRegionalVariant class."""

    def test_valid_regional_variant_creation(self):
        """Test creation of valid CRISRegionalVariant."""
        region_mappings = {
            "us-east-1": ["us-west-2", "eu-west-1"],
            "us-west-2": ["us-east-1", "eu-central-1"],
        }

        variant = CRISRegionalVariant(
            region_prefix="US",
            inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings=region_mappings,
        )

        assert variant.region_prefix == "US"
        assert variant.inference_profile_id == "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert variant.region_mappings == region_mappings

    def test_invalid_region_prefix_empty(self):
        """Test validation error for empty region prefix."""
        with pytest.raises(ValueError, match="Invalid region prefix"):
            CRISRegionalVariant(
                region_prefix="",
                inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_mappings={"us-east-1": ["us-west-2"]},
            )

    def test_invalid_region_prefix_whitespace(self):
        """Test validation error for whitespace region prefix."""
        with pytest.raises(ValueError, match="Invalid region prefix"):
            CRISRegionalVariant(
                region_prefix="   ",
                inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_mappings={"us-east-1": ["us-west-2"]},
            )

    def test_invalid_region_prefix_pattern(self):
        """Test validation error for invalid region prefix pattern."""
        with pytest.raises(ValueError, match="Invalid region prefix"):
            CRISRegionalVariant(
                region_prefix="INVALID",
                inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_mappings={"us-east-1": ["us-west-2"]},
            )

    def test_invalid_inference_profile_id_empty(self):
        """Test validation error for empty inference profile ID."""
        with pytest.raises(ValueError, match="Inference profile ID cannot be empty"):
            CRISRegionalVariant(
                region_prefix="US",
                inference_profile_id="",
                region_mappings={"us-east-1": ["us-west-2"]},
            )

    def test_invalid_inference_profile_id_whitespace(self):
        """Test validation error for whitespace inference profile ID."""
        with pytest.raises(ValueError, match="Inference profile ID cannot be empty"):
            CRISRegionalVariant(
                region_prefix="US",
                inference_profile_id="   ",
                region_mappings={"us-east-1": ["us-west-2"]},
            )

    def test_invalid_inference_profile_id_pattern(self):
        """Test validation error for invalid inference profile ID pattern."""
        with pytest.raises(ValueError, match="Invalid inference profile ID format"):
            CRISRegionalVariant(
                region_prefix="US",
                inference_profile_id="INVALID_PROFILE_ID",
                region_mappings={"us-east-1": ["us-west-2"]},
            )

    def test_empty_region_mappings(self):
        """Test validation error for empty region mappings."""
        with pytest.raises(ValueError, match="Region mappings cannot be empty"):
            CRISRegionalVariant(
                region_prefix="US",
                inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_mappings={},
            )

    def test_invalid_source_region(self):
        """Test validation error for invalid source region."""
        with pytest.raises(ValueError, match="Invalid region"):
            CRISRegionalVariant(
                region_prefix="US",
                inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_mappings={"INVALID_REGION": ["us-west-2"]},
            )

    def test_empty_destination_regions(self):
        """Test validation error for empty destination regions list."""
        with pytest.raises(ValueError, match="Destination regions list cannot be empty"):
            CRISRegionalVariant(
                region_prefix="US",
                inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_mappings={"us-east-1": []},
            )

    def test_invalid_destination_region(self):
        """Test validation error for invalid destination region."""
        with pytest.raises(ValueError, match="Invalid region"):
            CRISRegionalVariant(
                region_prefix="US",
                inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_mappings={"us-east-1": ["INVALID_REGION"]},
            )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        region_mappings = {"us-east-1": ["us-west-2", "eu-west-1"], "us-west-2": ["us-east-1"]}

        variant = CRISRegionalVariant(
            region_prefix="US",
            inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings=region_mappings,
        )

        result = variant.to_dict()

        expected = {
            CRISJSONFields.REGION_PREFIX: "US",
            CRISJSONFields.INFERENCE_PROFILE_ID: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            CRISJSONFields.REGION_MAPPINGS: region_mappings,
        }

        assert result == expected

    def test_from_dict_valid(self):
        """Test creation from valid dictionary."""
        data = {
            CRISJSONFields.REGION_PREFIX: "EU",
            CRISJSONFields.INFERENCE_PROFILE_ID: "eu.anthropic.claude-3-5-sonnet-20241022-v2:0",
            CRISJSONFields.REGION_MAPPINGS: {
                "eu-west-1": ["eu-central-1", "us-east-1"],
                "eu-central-1": ["eu-west-1"],
            },
        }

        variant = CRISRegionalVariant.from_dict(data=data)

        assert variant.region_prefix == "EU"
        assert variant.inference_profile_id == "eu.anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert variant.region_mappings == data[CRISJSONFields.REGION_MAPPINGS]

    def test_from_dict_missing_field(self):
        """Test error when required field is missing."""
        data = {
            CRISJSONFields.REGION_PREFIX: "US",
            # Missing inference_profile_id
            CRISJSONFields.REGION_MAPPINGS: {"us-east-1": ["us-west-2"]},
        }

        with pytest.raises(ValueError, match="Missing required field"):
            CRISRegionalVariant.from_dict(data=data)

    def test_from_dict_invalid_data_structure(self):
        """Test error when data structure is invalid."""
        from typing import Dict, Union

        data: Dict[str, Union[str, Dict]] = {
            CRISJSONFields.REGION_PREFIX: "US",
            CRISJSONFields.INFERENCE_PROFILE_ID: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            CRISJSONFields.REGION_MAPPINGS: "invalid_mappings",  # Should be dict
        }

        with pytest.raises(ValueError, match="Invalid variant data structure"):
            CRISRegionalVariant.from_dict(data=data)

    def test_get_source_regions(self):
        """Test getting source regions."""
        region_mappings = {
            "us-east-1": ["us-west-2"],
            "us-west-2": ["us-east-1"],
            "eu-west-1": ["eu-central-1"],
        }

        variant = CRISRegionalVariant(
            region_prefix="US",
            inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings=region_mappings,
        )

        source_regions = variant.get_source_regions()

        assert set(source_regions) == {"us-east-1", "us-west-2", "eu-west-1"}

    def test_get_destination_regions(self):
        """Test getting unique destination regions."""
        region_mappings = {
            "us-east-1": ["us-west-2", "eu-west-1"],
            "us-west-2": ["us-east-1", "eu-central-1"],
            "eu-west-1": ["eu-central-1"],
        }

        variant = CRISRegionalVariant(
            region_prefix="US",
            inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings=region_mappings,
        )

        destination_regions = variant.get_destination_regions()

        assert set(destination_regions) == {"us-east-1", "us-west-2", "eu-west-1", "eu-central-1"}
        assert destination_regions == sorted(destination_regions)  # Should be sorted

    def test_can_route_from_source(self):
        """Test checking if variant can route from source region."""
        region_mappings = {"us-east-1": ["us-west-2"], "us-west-2": ["us-east-1"]}

        variant = CRISRegionalVariant(
            region_prefix="US",
            inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings=region_mappings,
        )

        assert variant.can_route_from_source(source_region="us-east-1") is True
        assert variant.can_route_from_source(source_region="us-west-2") is True
        assert variant.can_route_from_source(source_region="eu-west-1") is False

    def test_can_route_to_destination(self):
        """Test checking if variant can route to destination region."""
        region_mappings = {"us-east-1": ["us-west-2", "eu-west-1"], "us-west-2": ["us-east-1"]}

        variant = CRISRegionalVariant(
            region_prefix="US",
            inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings=region_mappings,
        )

        assert variant.can_route_to_destination(destination_region="us-east-1") is True
        assert variant.can_route_to_destination(destination_region="us-west-2") is True
        assert variant.can_route_to_destination(destination_region="eu-west-1") is True
        assert variant.can_route_to_destination(destination_region="eu-central-1") is False

    def test_get_destinations_for_source(self):
        """Test getting destinations for specific source region."""
        region_mappings = {"us-east-1": ["us-west-2", "eu-west-1"], "us-west-2": ["us-east-1"]}

        variant = CRISRegionalVariant(
            region_prefix="US",
            inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings=region_mappings,
        )

        destinations = variant.get_destinations_for_source(source_region="us-east-1")
        assert destinations == ["us-west-2", "eu-west-1"]

        destinations = variant.get_destinations_for_source(source_region="us-west-2")
        assert destinations == ["us-east-1"]

        destinations = variant.get_destinations_for_source(source_region="nonexistent")
        assert destinations == []


class TestCRISMultiRegionalModel:
    """Test cases for CRISMultiRegionalModel class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.us_variant = CRISRegionalVariant(
            region_prefix="US",
            inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings={"us-east-1": ["us-west-2", "eu-west-1"], "us-west-2": ["us-east-1"]},
        )

        self.eu_variant = CRISRegionalVariant(
            region_prefix="EU",
            inference_profile_id="eu.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings={
                "eu-west-1": ["eu-central-1", "us-east-1"],
                "eu-central-1": ["eu-west-1"],
            },
        )

    def test_valid_multi_regional_model_creation(self):
        """Test creation of valid CRISMultiRegionalModel."""
        regional_variants = {"US": self.us_variant, "EU": self.eu_variant}

        model = CRISMultiRegionalModel(
            model_name="Claude 3.5 Sonnet", regional_variants=regional_variants
        )

        assert model.model_name == "Claude 3.5 Sonnet"
        assert model.regional_variants == regional_variants

    def test_invalid_model_name_empty(self):
        """Test validation error for empty model name."""
        with pytest.raises(ValueError, match="Empty or invalid model name"):
            CRISMultiRegionalModel(model_name="", regional_variants={"US": self.us_variant})

    def test_invalid_model_name_whitespace(self):
        """Test validation error for whitespace model name."""
        with pytest.raises(ValueError, match="Empty or invalid model name"):
            CRISMultiRegionalModel(model_name="   ", regional_variants={"US": self.us_variant})

    def test_invalid_model_name_pattern(self):
        """Test validation error for invalid model name pattern."""
        with pytest.raises(ValueError, match="Invalid model name"):
            CRISMultiRegionalModel(
                model_name="Invalid@Model#Name", regional_variants={"US": self.us_variant}
            )

    def test_empty_regional_variants(self):
        """Test validation error for empty regional variants."""
        with pytest.raises(ValueError, match="Model .* has no regional variants"):
            CRISMultiRegionalModel(model_name="Test Model", regional_variants={})

    def test_region_prefix_mismatch(self):
        """Test validation error for region prefix mismatch."""
        # Create variant with mismatched prefix
        mismatched_variant = CRISRegionalVariant(
            region_prefix="EU",
            inference_profile_id="eu.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings={"eu-west-1": ["eu-central-1"]},
        )

        with pytest.raises(ValueError, match="Region prefix mismatch"):
            CRISMultiRegionalModel(
                model_name="Test Model",
                regional_variants={"US": mismatched_variant},  # Key doesn't match variant prefix
            )

    def test_inference_profile_id_property_us_preferred(self):
        """Test inference_profile_id property returns US variant when available."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        assert model.inference_profile_id == self.us_variant.inference_profile_id

    def test_inference_profile_id_property_fallback(self):
        """Test inference_profile_id property fallback when US not available."""
        model = CRISMultiRegionalModel(
            model_name="Test Model", regional_variants={"EU": self.eu_variant}
        )

        assert model.inference_profile_id == self.eu_variant.inference_profile_id

    def test_region_mappings_property_merged(self):
        """Test region_mappings property merges all variants."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        merged_mappings = model.region_mappings

        # Should contain mappings from both variants
        assert "us-east-1" in merged_mappings
        assert "us-west-2" in merged_mappings
        assert "eu-west-1" in merged_mappings
        assert "eu-central-1" in merged_mappings

        # Check specific mappings
        assert set(merged_mappings["us-east-1"]) == {"us-west-2", "eu-west-1"}
        assert set(merged_mappings["eu-west-1"]) == {"eu-central-1", "us-east-1"}

    def test_region_mappings_property_overlapping_sources(self):
        """Test region_mappings property handles overlapping source regions."""
        # Create variants with overlapping source regions
        variant1 = CRISRegionalVariant(
            region_prefix="US",
            inference_profile_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )

        variant2 = CRISRegionalVariant(
            region_prefix="EU",
            inference_profile_id="eu.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_mappings={"us-east-1": ["eu-west-1"]},  # Same source region
        )

        model = CRISMultiRegionalModel(
            model_name="Test Model", regional_variants={"US": variant1, "EU": variant2}
        )

        merged_mappings = model.region_mappings

        # Should merge destinations for overlapping source
        assert set(merged_mappings["us-east-1"]) == {"us-west-2", "eu-west-1"}

    def test_get_variant_by_prefix(self):
        """Test getting variant by region prefix."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        assert model.get_variant_by_prefix(region_prefix="US") == self.us_variant
        assert model.get_variant_by_prefix(region_prefix="EU") == self.eu_variant
        assert model.get_variant_by_prefix(region_prefix="APAC") is None

    def test_get_all_inference_profiles(self):
        """Test getting all inference profiles."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        profiles = model.get_all_inference_profiles()

        expected = {
            "US": self.us_variant.inference_profile_id,
            "EU": self.eu_variant.inference_profile_id,
        }

        assert profiles == expected

    def test_get_regional_prefixes(self):
        """Test getting regional prefixes."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        prefixes = model.get_regional_prefixes()

        assert prefixes == ["EU", "US"]  # Should be sorted

    def test_has_regional_variant(self):
        """Test checking if model has regional variant."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        assert model.has_regional_variant(region_prefix="US") is True
        assert model.has_regional_variant(region_prefix="EU") is True
        assert model.has_regional_variant(region_prefix="APAC") is False

    def test_get_source_regions(self):
        """Test getting all source regions."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        source_regions = model.get_source_regions()

        expected = ["eu-central-1", "eu-west-1", "us-east-1", "us-west-2"]
        assert source_regions == expected

    def test_get_destination_regions(self):
        """Test getting all destination regions."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        destination_regions = model.get_destination_regions()

        expected = ["eu-central-1", "eu-west-1", "us-east-1", "us-west-2"]
        assert destination_regions == expected

    def test_can_route_from_source(self):
        """Test checking if any variant can route from source."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        assert model.can_route_from_source(source_region="us-east-1") is True
        assert model.can_route_from_source(source_region="eu-west-1") is True
        assert model.can_route_from_source(source_region="ap-southeast-1") is False

    def test_can_route_to_destination(self):
        """Test checking if any variant can route to destination."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        assert model.can_route_to_destination(destination_region="us-west-2") is True
        assert model.can_route_to_destination(destination_region="eu-central-1") is True
        assert model.can_route_to_destination(destination_region="ap-southeast-1") is False

    def test_get_destinations_for_source(self):
        """Test getting destinations for source across all variants."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        destinations = model.get_destinations_for_source(source_region="us-east-1")
        expected = ["eu-west-1", "us-west-2"]  # From US variant
        assert destinations == expected

        destinations = model.get_destinations_for_source(source_region="nonexistent")
        assert destinations == []

    def test_to_dict(self):
        """Test conversion to dictionary."""
        model = CRISMultiRegionalModel(
            model_name="Test Model",
            regional_variants={"US": self.us_variant, "EU": self.eu_variant},
        )

        result = model.to_dict()

        assert result[CRISJSONFields.MODEL_NAME] == "Test Model"
        assert CRISJSONFields.REGIONAL_VARIANTS in result
        assert CRISJSONFields.INFERENCE_PROFILE_ID in result
        assert CRISJSONFields.REGION_MAPPINGS in result
        assert CRISJSONFields.ALL_INFERENCE_PROFILES in result

        # Check backward compatibility fields
        assert result[CRISJSONFields.INFERENCE_PROFILE_ID] == self.us_variant.inference_profile_id
        assert result[CRISJSONFields.ALL_INFERENCE_PROFILES] == {
            "US": self.us_variant.inference_profile_id,
            "EU": self.eu_variant.inference_profile_id,
        }

    def test_from_dict_valid(self):
        """Test creation from valid dictionary."""
        from typing import Dict, Union

        data: Dict[str, Union[str, Dict]] = {
            CRISJSONFields.MODEL_NAME: "Test Model",
            CRISJSONFields.REGIONAL_VARIANTS: {
                "US": {
                    CRISJSONFields.REGION_PREFIX: "US",
                    CRISJSONFields.INFERENCE_PROFILE_ID: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                    CRISJSONFields.REGION_MAPPINGS: {"us-east-1": ["us-west-2"]},
                },
                "EU": {
                    CRISJSONFields.REGION_PREFIX: "EU",
                    CRISJSONFields.INFERENCE_PROFILE_ID: "eu.anthropic.claude-3-5-sonnet-20241022-v2:0",
                    CRISJSONFields.REGION_MAPPINGS: {"eu-west-1": ["eu-central-1"]},
                },
            },
        }

        model = CRISMultiRegionalModel.from_dict(data=data)

        assert model.model_name == "Test Model"
        assert len(model.regional_variants) == 2
        assert "US" in model.regional_variants
        assert "EU" in model.regional_variants

    def test_from_dict_missing_field(self):
        """Test error when required field is missing."""
        from typing import Dict, Union

        data: Dict[str, Union[str, Dict]] = {
            # Missing MODEL_NAME
            CRISJSONFields.REGIONAL_VARIANTS: {
                "US": {
                    CRISJSONFields.REGION_PREFIX: "US",
                    CRISJSONFields.INFERENCE_PROFILE_ID: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                    CRISJSONFields.REGION_MAPPINGS: {"us-east-1": ["us-west-2"]},
                }
            }
        }

        with pytest.raises(ValueError, match="Missing required field"):
            CRISMultiRegionalModel.from_dict(data=data)

    def test_from_dict_invalid_variants_structure(self):
        """Test error when variants structure is invalid."""
        from typing import Dict, Union

        data: Dict[str, Union[str, Dict]] = {
            CRISJSONFields.MODEL_NAME: "Test Model",
            CRISJSONFields.REGIONAL_VARIANTS: "invalid_variants",  # Should be dict
        }

        with pytest.raises(ValueError, match="Regional variants must be a dictionary"):
            CRISMultiRegionalModel.from_dict(data=data)

    def test_from_dict_invalid_variant_data(self):
        """Test error when variant data is invalid."""
        from typing import Dict, Union

        data: Dict[str, Union[str, Dict]] = {
            CRISJSONFields.MODEL_NAME: "Test Model",
            CRISJSONFields.REGIONAL_VARIANTS: {"US": "invalid_variant_data"},  # Should be dict
        }

        with pytest.raises(ValueError, match="Variant data for US must be a dictionary"):
            CRISMultiRegionalModel.from_dict(data=data)


class TestTypeAliases:
    """Test type aliases are properly defined."""

    def test_type_aliases_exist(self):
        """Test that type aliases are defined."""
        # These should not raise errors if properly imported
        prefix: CRISRegionPrefix = "US"
        variant_dict: CRISRegionalVariantDict = {}
        model_dict: CRISMultiRegionalModelDict = {}
        variants_map: RegionalVariantsMap = {}

        # Basic type checks
        assert isinstance(prefix, str)
        assert isinstance(variant_dict, dict)
        assert isinstance(model_dict, dict)
        assert isinstance(variants_map, dict)
