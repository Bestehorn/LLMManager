"""
Tests for CRIS (Cross-Region Inference) data structures.
"""

from datetime import datetime

import pytest

from bestehorn_llmmanager.bedrock.models.cris_structures import (
    CRISCatalog,
    CRISInferenceProfile,
    CRISModelInfo,
)


class TestCRISInferenceProfile:
    """Test CRISInferenceProfile functionality."""

    def test_init_valid_profile(self):
        """Test initialization with valid profile data."""
        profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={
                "us-east-1": ["us-west-2", "us-east-2"],
                "eu-west-1": ["eu-central-1"],
            },
        )

        assert profile.inference_profile_id == "us.amazon.nova-lite-v1:0"
        assert len(profile.region_mappings) == 2
        assert profile.region_mappings["us-east-1"] == ["us-west-2", "us-east-2"]

    def test_init_empty_profile_id(self):
        """Test initialization with empty profile ID."""
        with pytest.raises(ValueError, match="Inference profile ID cannot be empty"):
            CRISInferenceProfile(
                inference_profile_id="", region_mappings={"us-east-1": ["us-west-2"]}
            )

    def test_init_whitespace_profile_id(self):
        """Test initialization with whitespace-only profile ID."""
        with pytest.raises(ValueError, match="Inference profile ID cannot be empty"):
            CRISInferenceProfile(
                inference_profile_id="   ", region_mappings={"us-east-1": ["us-west-2"]}
            )

    def test_init_invalid_profile_id_format(self):
        """Test initialization with invalid profile ID format."""
        with pytest.raises(ValueError, match="Invalid inference profile ID format"):
            CRISInferenceProfile(
                inference_profile_id="Invalid@Format!", region_mappings={"us-east-1": ["us-west-2"]}
            )

    def test_init_empty_region_mappings(self):
        """Test initialization with empty region mappings."""
        with pytest.raises(ValueError, match="Region mappings cannot be empty"):
            CRISInferenceProfile(
                inference_profile_id="us.amazon.nova-lite-v1:0", region_mappings={}
            )

    def test_init_invalid_source_region(self):
        """Test initialization with invalid source region."""
        with pytest.raises(ValueError, match="Invalid region"):
            CRISInferenceProfile(
                inference_profile_id="us.amazon.nova-lite-v1:0",
                region_mappings={"Invalid@Region!": ["us-west-2"]},
            )

    def test_init_empty_destination_regions(self):
        """Test initialization with empty destination regions list."""
        with pytest.raises(ValueError, match="Destination regions list cannot be empty"):
            CRISInferenceProfile(
                inference_profile_id="us.amazon.nova-lite-v1:0", region_mappings={"us-east-1": []}
            )

    def test_init_invalid_destination_region(self):
        """Test initialization with invalid destination region."""
        with pytest.raises(ValueError, match="Invalid region"):
            CRISInferenceProfile(
                inference_profile_id="us.amazon.nova-lite-v1:0",
                region_mappings={"us-east-1": ["Invalid@Region!"]},
            )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )

        result = profile.to_dict()
        assert "region_mappings" in result
        assert result["region_mappings"] == {"us-east-1": ["us-west-2"]}

    def test_get_source_regions(self):
        """Test getting source regions."""
        profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={
                "us-east-1": ["us-west-2"],
                "eu-west-1": ["eu-central-1"],
                "ap-southeast-1": ["ap-northeast-1"],
            },
        )

        sources = profile.get_source_regions()
        assert set(sources) == {"us-east-1", "eu-west-1", "ap-southeast-1"}

    def test_get_destination_regions(self):
        """Test getting destination regions."""
        profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={
                "us-east-1": ["us-west-2", "us-east-2"],
                "eu-west-1": ["eu-central-1", "us-west-2"],  # us-west-2 appears twice
            },
        )

        destinations = profile.get_destination_regions()
        assert set(destinations) == {"us-west-2", "us-east-2", "eu-central-1"}
        assert destinations == sorted(destinations)  # Should be sorted

    def test_can_route_from_source(self):
        """Test source region routing check."""
        profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )

        assert profile.can_route_from_source("us-east-1") is True
        assert profile.can_route_from_source("eu-west-1") is False

    def test_can_route_to_destination(self):
        """Test destination region routing check."""
        profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2", "us-east-2"]},
        )

        assert profile.can_route_to_destination("us-west-2") is True
        assert profile.can_route_to_destination("us-east-2") is True
        assert profile.can_route_to_destination("eu-west-1") is False

    def test_get_destinations_for_source(self):
        """Test getting destinations for specific source region."""
        profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={
                "us-east-1": ["us-west-2", "us-east-2"],
                "eu-west-1": ["eu-central-1"],
            },
        )

        us_destinations = profile.get_destinations_for_source("us-east-1")
        assert us_destinations == ["us-west-2", "us-east-2"]

        eu_destinations = profile.get_destinations_for_source("eu-west-1")
        assert eu_destinations == ["eu-central-1"]

        # Non-existent source should return empty list
        empty_destinations = profile.get_destinations_for_source("ap-southeast-1")
        assert empty_destinations == []


class TestCRISModelInfo:
    """Test CRISModelInfo functionality."""

    def create_sample_profile(self, profile_id: str) -> CRISInferenceProfile:
        """Helper to create sample inference profile."""
        return CRISInferenceProfile(
            inference_profile_id=profile_id, region_mappings={"us-east-1": ["us-west-2"]}
        )

    def test_init_valid_model(self):
        """Test initialization with valid model data."""
        profiles = {
            "us.amazon.nova-lite-v1:0": self.create_sample_profile("us.amazon.nova-lite-v1:0")
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)

        assert model.model_name == "Nova Lite"
        assert len(model.inference_profiles) == 1

    def test_init_empty_model_name(self):
        """Test initialization with empty model name."""
        profiles = {
            "us.amazon.nova-lite-v1:0": self.create_sample_profile("us.amazon.nova-lite-v1:0")
        }

        with pytest.raises(ValueError, match="Empty or invalid model name"):
            CRISModelInfo(model_name="", inference_profiles=profiles)

    def test_init_whitespace_model_name(self):
        """Test initialization with whitespace-only model name."""
        profiles = {
            "us.amazon.nova-lite-v1:0": self.create_sample_profile("us.amazon.nova-lite-v1:0")
        }

        with pytest.raises(ValueError, match="Empty or invalid model name"):
            CRISModelInfo(model_name="   ", inference_profiles=profiles)

    def test_init_invalid_model_name_format(self):
        """Test initialization with invalid model name format."""
        profiles = {
            "us.amazon.nova-lite-v1:0": self.create_sample_profile("us.amazon.nova-lite-v1:0")
        }

        with pytest.raises(ValueError, match="Invalid model name"):
            CRISModelInfo(model_name="Invalid@Name!", inference_profiles=profiles)

    def test_init_no_inference_profiles(self):
        """Test initialization with no inference profiles."""
        with pytest.raises(ValueError, match="Model Nova Lite has no inference profiles"):
            CRISModelInfo(model_name="Nova Lite", inference_profiles={})

    def test_init_profile_id_mismatch(self):
        """Test initialization with mismatched profile ID."""
        wrong_profile = self.create_sample_profile("us.amazon.nova-lite-v1:0")
        profiles = {"different-id": wrong_profile}

        with pytest.raises(ValueError, match="Profile ID mismatch"):
            CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)

    def test_inference_profile_id_property_us_preference(self):
        """Test inference_profile_id property with US preference."""
        profiles = {
            "eu.amazon.nova-lite-v1:0": self.create_sample_profile("eu.amazon.nova-lite-v1:0"),
            "us.amazon.nova-lite-v1:0": self.create_sample_profile("us.amazon.nova-lite-v1:0"),
            "apac.amazon.nova-lite-v1:0": self.create_sample_profile("apac.amazon.nova-lite-v1:0"),
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        assert model.inference_profile_id == "us.amazon.nova-lite-v1:0"

    def test_inference_profile_id_property_eu_fallback(self):
        """Test inference_profile_id property with EU fallback."""
        profiles = {
            "eu.amazon.nova-lite-v1:0": self.create_sample_profile("eu.amazon.nova-lite-v1:0"),
            "apac.amazon.nova-lite-v1:0": self.create_sample_profile("apac.amazon.nova-lite-v1:0"),
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        assert model.inference_profile_id == "eu.amazon.nova-lite-v1:0"

    def test_inference_profile_id_property_apac_fallback(self):
        """Test inference_profile_id property with APAC fallback."""
        profiles = {
            "apac.amazon.nova-lite-v1:0": self.create_sample_profile("apac.amazon.nova-lite-v1:0")
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        assert model.inference_profile_id == "apac.amazon.nova-lite-v1:0"

    def test_inference_profile_id_property_ap_prefix(self):
        """Test inference_profile_id property with ap prefix."""
        profiles = {
            "ap.amazon.nova-lite-v1:0": self.create_sample_profile("ap.amazon.nova-lite-v1:0")
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        assert model.inference_profile_id == "ap.amazon.nova-lite-v1:0"

    def test_inference_profile_id_property_first_available(self):
        """Test inference_profile_id property with first available fallback."""
        profiles = {
            "other.amazon.nova-lite-v1:0": self.create_sample_profile("other.amazon.nova-lite-v1:0")
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        assert model.inference_profile_id == "other.amazon.nova-lite-v1:0"

    def test_region_mappings_property(self):
        """Test region_mappings property merging."""
        profile1 = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )
        profile2 = CRISInferenceProfile(
            inference_profile_id="eu.amazon.nova-lite-v1:0",
            region_mappings={"eu-west-1": ["eu-central-1"], "us-east-1": ["us-east-2"]},
        )

        profiles = {"us.amazon.nova-lite-v1:0": profile1, "eu.amazon.nova-lite-v1:0": profile2}

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        mappings = model.region_mappings

        # Should merge us-east-1 destinations from both profiles
        assert set(mappings["us-east-1"]) == {"us-west-2", "us-east-2"}
        assert mappings["eu-west-1"] == ["eu-central-1"]

    def test_get_inference_profile(self):
        """Test getting specific inference profile."""
        profile = self.create_sample_profile("us.amazon.nova-lite-v1:0")
        profiles = {"us.amazon.nova-lite-v1:0": profile}

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)

        retrieved = model.get_inference_profile("us.amazon.nova-lite-v1:0")
        assert retrieved is profile

        not_found = model.get_inference_profile("non-existent")
        assert not_found is None

    def test_get_all_inference_profile_ids(self):
        """Test getting all inference profile IDs."""
        profiles = {
            "us.amazon.nova-lite-v1:0": self.create_sample_profile("us.amazon.nova-lite-v1:0"),
            "eu.amazon.nova-lite-v1:0": self.create_sample_profile("eu.amazon.nova-lite-v1:0"),
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        ids = model.get_all_inference_profile_ids()

        assert set(ids) == {"us.amazon.nova-lite-v1:0", "eu.amazon.nova-lite-v1:0"}

    def test_has_inference_profile(self):
        """Test checking if model has specific inference profile."""
        profiles = {
            "us.amazon.nova-lite-v1:0": self.create_sample_profile("us.amazon.nova-lite-v1:0")
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)

        assert model.has_inference_profile("us.amazon.nova-lite-v1:0") is True
        assert model.has_inference_profile("non-existent") is False

    def test_get_source_regions(self):
        """Test getting all source regions."""
        profile1 = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )
        profile2 = CRISInferenceProfile(
            inference_profile_id="eu.amazon.nova-lite-v1:0",
            region_mappings={"eu-west-1": ["eu-central-1"]},
        )

        profiles = {"us.amazon.nova-lite-v1:0": profile1, "eu.amazon.nova-lite-v1:0": profile2}

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        sources = model.get_source_regions()

        assert set(sources) == {"us-east-1", "eu-west-1"}
        assert sources == sorted(sources)

    def test_get_destination_regions(self):
        """Test getting all destination regions."""
        profile1 = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2", "us-east-2"]},
        )
        profile2 = CRISInferenceProfile(
            inference_profile_id="eu.amazon.nova-lite-v1:0",
            region_mappings={"eu-west-1": ["eu-central-1", "us-west-2"]},  # us-west-2 duplicate
        )

        profiles = {"us.amazon.nova-lite-v1:0": profile1, "eu.amazon.nova-lite-v1:0": profile2}

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        destinations = model.get_destination_regions()

        assert set(destinations) == {"us-west-2", "us-east-2", "eu-central-1"}
        assert destinations == sorted(destinations)

    def test_can_route_from_source(self):
        """Test checking source region routing."""
        profiles = {
            "us.amazon.nova-lite-v1:0": CRISInferenceProfile(
                inference_profile_id="us.amazon.nova-lite-v1:0",
                region_mappings={"us-east-1": ["us-west-2"]},
            )
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)

        assert model.can_route_from_source("us-east-1") is True
        assert model.can_route_from_source("eu-west-1") is False

    def test_can_route_to_destination(self):
        """Test checking destination region routing."""
        profiles = {
            "us.amazon.nova-lite-v1:0": CRISInferenceProfile(
                inference_profile_id="us.amazon.nova-lite-v1:0",
                region_mappings={"us-east-1": ["us-west-2"]},
            )
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)

        assert model.can_route_to_destination("us-west-2") is True
        assert model.can_route_to_destination("eu-west-1") is False

    def test_get_destinations_for_source(self):
        """Test getting destinations for source region."""
        profile1 = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )
        profile2 = CRISInferenceProfile(
            inference_profile_id="eu.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-east-2"]},  # Same source, different destination
        )

        profiles = {"us.amazon.nova-lite-v1:0": profile1, "eu.amazon.nova-lite-v1:0": profile2}

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        destinations = model.get_destinations_for_source("us-east-1")

        assert set(destinations) == {"us-west-2", "us-east-2"}
        assert destinations == sorted(destinations)

        # Non-existent source
        empty_destinations = model.get_destinations_for_source("non-existent")
        assert empty_destinations == []

    def test_get_profiles_for_source_region(self):
        """Test getting profiles for source region."""
        profiles = {
            "us.amazon.nova-lite-v1:0": CRISInferenceProfile(
                inference_profile_id="us.amazon.nova-lite-v1:0",
                region_mappings={"us-east-1": ["us-west-2"]},
            ),
            "eu.amazon.nova-lite-v1:0": CRISInferenceProfile(
                inference_profile_id="eu.amazon.nova-lite-v1:0",
                region_mappings={"eu-west-1": ["eu-central-1"]},
            ),
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)

        us_profiles = model.get_profiles_for_source_region("us-east-1")
        assert us_profiles == ["us.amazon.nova-lite-v1:0"]

        eu_profiles = model.get_profiles_for_source_region("eu-west-1")
        assert eu_profiles == ["eu.amazon.nova-lite-v1:0"]

        no_profiles = model.get_profiles_for_source_region("non-existent")
        assert no_profiles == []

    def test_get_profiles_for_destination_region(self):
        """Test getting profiles for destination region."""
        profiles = {
            "us.amazon.nova-lite-v1:0": CRISInferenceProfile(
                inference_profile_id="us.amazon.nova-lite-v1:0",
                region_mappings={"us-east-1": ["us-west-2"]},
            ),
            "eu.amazon.nova-lite-v1:0": CRISInferenceProfile(
                inference_profile_id="eu.amazon.nova-lite-v1:0",
                region_mappings={"eu-west-1": ["us-west-2"]},  # Same destination
            ),
        }

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)

        # Both profiles route to us-west-2
        matching_profiles = model.get_profiles_for_destination_region("us-west-2")
        assert set(matching_profiles) == {"us.amazon.nova-lite-v1:0", "eu.amazon.nova-lite-v1:0"}

        no_profiles = model.get_profiles_for_destination_region("non-existent")
        assert no_profiles == []

    def test_to_dict(self):
        """Test conversion to dictionary."""
        profile = self.create_sample_profile("us.amazon.nova-lite-v1:0")
        profiles = {"us.amazon.nova-lite-v1:0": profile}

        model = CRISModelInfo(model_name="Nova Lite", inference_profiles=profiles)
        result = model.to_dict()

        assert result["model_name"] == "Nova Lite"
        assert "inference_profiles" in result
        assert "inference_profile_id" in result  # Backward compatibility
        assert result["inference_profile_id"] == "us.amazon.nova-lite-v1:0"

    def test_from_dict_valid_data(self):
        """Test creation from valid dictionary data."""
        data = {
            "model_name": "Nova Lite",
            "inference_profiles": {
                "us.amazon.nova-lite-v1:0": {"region_mappings": {"us-east-1": ["us-west-2"]}}
            },
        }

        model = CRISModelInfo.from_dict(data)

        assert model.model_name == "Nova Lite"
        assert len(model.inference_profiles) == 1
        assert "us.amazon.nova-lite-v1:0" in model.inference_profiles

    def test_from_dict_missing_model_name(self):
        """Test creation from dict with missing model name."""
        data = {
            "inference_profiles": {
                "us.amazon.nova-lite-v1:0": {"region_mappings": {"us-east-1": ["us-west-2"]}}
            }
        }

        with pytest.raises(ValueError, match="Missing required field"):
            CRISModelInfo.from_dict(data)

    def test_from_dict_invalid_profiles_structure(self):
        """Test creation from dict with invalid profiles structure."""
        data = {"model_name": "Nova Lite", "inference_profiles": "not_a_dict"}

        with pytest.raises(ValueError, match="Inference profiles must be a dictionary"):
            CRISModelInfo.from_dict(data)

    def test_from_dict_invalid_profile_data(self):
        """Test creation from dict with invalid profile data."""
        data = {
            "model_name": "Nova Lite",
            "inference_profiles": {"us.amazon.nova-lite-v1:0": "not_a_dict"},
        }

        with pytest.raises(ValueError, match="Profile data for .* must be a dictionary"):
            CRISModelInfo.from_dict(data)

    def test_from_dict_invalid_region_mappings(self):
        """Test creation from dict with invalid region mappings."""
        data = {
            "model_name": "Nova Lite",
            "inference_profiles": {"us.amazon.nova-lite-v1:0": {"region_mappings": "not_a_dict"}},
        }

        with pytest.raises(ValueError, match="Region mappings for .* must be a dictionary"):
            CRISModelInfo.from_dict(data)


class TestCRISCatalog:
    """Test CRISCatalog functionality."""

    def create_sample_model(self, model_name: str) -> CRISModelInfo:
        """Helper to create sample CRIS model."""
        profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )
        return CRISModelInfo(
            model_name=model_name, inference_profiles={"us.amazon.nova-lite-v1:0": profile}
        )

    def test_init_valid_catalog(self):
        """Test initialization with valid catalog data."""
        timestamp = datetime.now()
        models = {"Nova Lite": self.create_sample_model("Nova Lite")}

        catalog = CRISCatalog(retrieval_timestamp=timestamp, cris_models=models)

        assert catalog.retrieval_timestamp == timestamp
        assert len(catalog.cris_models) == 1
        assert "Nova Lite" in catalog.cris_models

    def test_model_count_property(self):
        """Test model_count property."""
        models = {
            "Nova Lite": self.create_sample_model("Nova Lite"),
            "Claude": self.create_sample_model("Claude"),
        }

        catalog = CRISCatalog(retrieval_timestamp=datetime.now(), cris_models=models)

        assert catalog.model_count == 2

    def test_get_models_by_source_region(self):
        """Test filtering models by source region."""
        # Create models with different source regions
        nova_profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )
        nova_model = CRISModelInfo(
            model_name="Nova Lite", inference_profiles={"us.amazon.nova-lite-v1:0": nova_profile}
        )

        claude_profile = CRISInferenceProfile(
            inference_profile_id="us.anthropic.claude-v1:0",
            region_mappings={"eu-west-1": ["eu-central-1"]},
        )
        claude_model = CRISModelInfo(
            model_name="Claude", inference_profiles={"us.anthropic.claude-v1:0": claude_profile}
        )

        catalog = CRISCatalog(
            retrieval_timestamp=datetime.now(),
            cris_models={"Nova Lite": nova_model, "Claude": claude_model},
        )

        us_models = catalog.get_models_by_source_region("us-east-1")
        assert "Nova Lite" in us_models
        assert "Claude" not in us_models

        eu_models = catalog.get_models_by_source_region("eu-west-1")
        assert "Claude" in eu_models
        assert "Nova Lite" not in eu_models

    def test_get_models_by_destination_region(self):
        """Test filtering models by destination region."""
        nova_profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )
        nova_model = CRISModelInfo(
            model_name="Nova Lite", inference_profiles={"us.amazon.nova-lite-v1:0": nova_profile}
        )

        catalog = CRISCatalog(
            retrieval_timestamp=datetime.now(), cris_models={"Nova Lite": nova_model}
        )

        us_west_models = catalog.get_models_by_destination_region("us-west-2")
        assert "Nova Lite" in us_west_models

        eu_models = catalog.get_models_by_destination_region("eu-central-1")
        assert len(eu_models) == 0

    def test_get_inference_profile_for_model(self):
        """Test getting inference profile for specific model."""
        model = self.create_sample_model("Nova Lite")
        catalog = CRISCatalog(retrieval_timestamp=datetime.now(), cris_models={"Nova Lite": model})

        profile_id = catalog.get_inference_profile_for_model("Nova Lite")
        assert profile_id == "us.amazon.nova-lite-v1:0"

        not_found = catalog.get_inference_profile_for_model("Non Existent")
        assert not_found is None

    def test_get_all_source_regions(self):
        """Test getting all source regions."""
        nova_profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )
        nova_model = CRISModelInfo(
            model_name="Nova Lite", inference_profiles={"us.amazon.nova-lite-v1:0": nova_profile}
        )

        claude_profile = CRISInferenceProfile(
            inference_profile_id="us.anthropic.claude-v1:0",
            region_mappings={"eu-west-1": ["eu-central-1"]},
        )
        claude_model = CRISModelInfo(
            model_name="Claude", inference_profiles={"us.anthropic.claude-v1:0": claude_profile}
        )

        catalog = CRISCatalog(
            retrieval_timestamp=datetime.now(),
            cris_models={"Nova Lite": nova_model, "Claude": claude_model},
        )

        sources = catalog.get_all_source_regions()
        assert set(sources) == {"us-east-1", "eu-west-1"}
        assert sources == sorted(sources)

    def test_get_all_destination_regions(self):
        """Test getting all destination regions."""
        nova_profile = CRISInferenceProfile(
            inference_profile_id="us.amazon.nova-lite-v1:0",
            region_mappings={"us-east-1": ["us-west-2"]},
        )
        nova_model = CRISModelInfo(
            model_name="Nova Lite", inference_profiles={"us.amazon.nova-lite-v1:0": nova_profile}
        )

        catalog = CRISCatalog(
            retrieval_timestamp=datetime.now(), cris_models={"Nova Lite": nova_model}
        )

        destinations = catalog.get_all_destination_regions()
        assert destinations == ["us-west-2"]

    def test_get_model_names(self):
        """Test getting model names."""
        models = {
            "Nova Lite": self.create_sample_model("Nova Lite"),
            "Claude": self.create_sample_model("Claude"),
        }

        catalog = CRISCatalog(retrieval_timestamp=datetime.now(), cris_models=models)

        names = catalog.get_model_names()
        assert set(names) == {"Nova Lite", "Claude"}
        assert names == sorted(names)

    def test_has_model(self):
        """Test checking if model exists."""
        model = self.create_sample_model("Nova Lite")
        catalog = CRISCatalog(retrieval_timestamp=datetime.now(), cris_models={"Nova Lite": model})

        assert catalog.has_model("Nova Lite") is True
        assert catalog.has_model("Non Existent") is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        model = self.create_sample_model("Nova Lite")

        catalog = CRISCatalog(retrieval_timestamp=timestamp, cris_models={"Nova Lite": model})

        result = catalog.to_dict()

        assert result["retrieval_timestamp"] == "2023-01-01T12:00:00"
        assert "CRIS" in result
        assert "Nova Lite" in result["CRIS"]

    def test_from_dict_valid_data(self):
        """Test creation from valid dictionary data."""
        data = {
            "retrieval_timestamp": "2023-01-01T12:00:00",
            "CRIS": {
                "Nova Lite": {
                    "model_name": "Nova Lite",
                    "inference_profiles": {
                        "us.amazon.nova-lite-v1:0": {
                            "region_mappings": {"us-east-1": ["us-west-2"]}
                        }
                    },
                }
            },
        }

        catalog = CRISCatalog.from_dict(data)

        assert catalog.retrieval_timestamp == datetime(2023, 1, 1, 12, 0, 0)
        assert len(catalog.cris_models) == 1
        assert "Nova Lite" in catalog.cris_models

    def test_from_dict_invalid_timestamp(self):
        """Test creation from dict with invalid timestamp."""
        data = {"retrieval_timestamp": 12345, "cris": {}}  # Not a string

        with pytest.raises(ValueError, match="Invalid timestamp format"):
            CRISCatalog.from_dict(data)

    def test_from_dict_missing_timestamp(self):
        """Test creation from dict with missing timestamp."""
        data = {"CRIS": {}}

        with pytest.raises(ValueError, match="Missing required field"):
            CRISCatalog.from_dict(data)

    def test_from_dict_invalid_cris_structure(self):
        """Test creation from dict with invalid CRIS structure."""
        data = {"retrieval_timestamp": "2023-01-01T12:00:00", "CRIS": "not_a_dict"}

        with pytest.raises(ValueError, match="CRIS data must be a dictionary"):
            CRISCatalog.from_dict(data)

    def test_from_dict_invalid_model_data(self):
        """Test creation from dict with invalid model data."""
        data = {"retrieval_timestamp": "2023-01-01T12:00:00", "CRIS": {"Nova Lite": "not_a_dict"}}

        with pytest.raises(ValueError, match="Model data for .* must be a dictionary"):
            CRISCatalog.from_dict(data)
