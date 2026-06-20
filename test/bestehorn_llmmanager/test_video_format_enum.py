"""
Tests for VideoFormatEnum ↔ Bedrock alignment (issue #33).

`VideoFormatEnum` must match the authoritative Bedrock Converse VideoBlock ``format``
enum exactly: mkv, mov, mp4, webm, flv, mpeg, mpg, wmv, three_gp — with NO ``avi`` (which
Bedrock rejects). The file-type detector extension mappings and the
``SupportedFormats.VIDEO_FORMATS`` list must stay in lockstep.
"""

from bestehorn_llmmanager.message_builder_constants import SupportedFormats
from bestehorn_llmmanager.message_builder_enums import VideoFormatEnum
from bestehorn_llmmanager.util.file_type_detector.detector_constants import (
    FileExtensionConstants,
)

# The authoritative Bedrock VideoFormat enum (boto3 bedrock-runtime service model).
BEDROCK_VIDEO_FORMATS = {"mkv", "mov", "mp4", "webm", "flv", "mpeg", "mpg", "wmv", "three_gp"}


class TestVideoFormatEnumMatchesBedrock:
    """The enum value set equals the Bedrock-supported set exactly."""

    def test_enum_values_equal_bedrock_set(self):
        """VideoFormatEnum values == the Bedrock VideoFormat enum, exactly."""
        assert {fmt.value for fmt in VideoFormatEnum} == BEDROCK_VIDEO_FORMATS

    def test_avi_removed(self):
        """avi is not a valid Bedrock video format and must not be in the enum."""
        assert "avi" not in {fmt.value for fmt in VideoFormatEnum}
        assert not hasattr(VideoFormatEnum, "AVI")

    def test_newly_supported_formats_present(self):
        """The five formats Bedrock supports that were previously missing are present."""
        values = {fmt.value for fmt in VideoFormatEnum}
        for fmt in ("flv", "mpeg", "mpg", "wmv", "three_gp"):
            assert fmt in values

    def test_three_gp_member_value(self):
        """three_gp uses the Bedrock token value 'three_gp' (not '3gp')."""
        assert VideoFormatEnum.THREE_GP.value == "three_gp"


class TestSupportedVideoFormatsInLockstep:
    """SupportedFormats.VIDEO_FORMATS matches the enum (no avi, includes the new five)."""

    def test_supported_video_formats_equal_bedrock_set(self):
        assert set(SupportedFormats.VIDEO_FORMATS) == BEDROCK_VIDEO_FORMATS

    def test_supported_video_formats_have_no_avi(self):
        assert "avi" not in SupportedFormats.VIDEO_FORMATS


class TestVideoExtensionMappingsInLockstep:
    """File-type detector video extension mappings match the supported set."""

    def test_avi_extension_removed(self):
        assert ".avi" not in FileExtensionConstants.VIDEO_EXTENSIONS

    def test_new_extensions_present_and_map_to_bedrock_values(self):
        ext_map = FileExtensionConstants.VIDEO_EXTENSIONS
        assert ext_map.get(".flv") == "flv"
        assert ext_map.get(".mpeg") == "mpeg"
        assert ext_map.get(".mpg") == "mpg"
        assert ext_map.get(".wmv") == "wmv"
        # .3gp is the conventional extension; it must map to the Bedrock token "three_gp".
        assert ext_map.get(".3gp") == "three_gp"

    def test_all_mapped_video_values_are_valid_bedrock_formats(self):
        """Every value the detector maps an extension to is a valid VideoFormatEnum value."""
        valid = {fmt.value for fmt in VideoFormatEnum}
        for ext, value in FileExtensionConstants.VIDEO_EXTENSIONS.items():
            assert value in valid, f"{ext} maps to non-Bedrock video format {value!r}"
