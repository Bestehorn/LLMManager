"""
AWS Regions constants for Amazon Bedrock.
Contains all AWS region string literals used in Bedrock model availability.
"""

from typing import Final, List


class AWSRegions:
    """AWS Region identifier constants."""

    # US Regions
    US_EAST_1: Final[str] = "us-east-1"
    US_EAST_2: Final[str] = "us-east-2"
    US_WEST_1: Final[str] = "us-west-1"
    US_WEST_2: Final[str] = "us-west-2"

    # US Government Regions
    US_GOV_EAST_1: Final[str] = "us-gov-east-1"
    US_GOV_WEST_1: Final[str] = "us-gov-west-1"

    # Asia Pacific Regions
    AP_NORTHEAST_1: Final[str] = "ap-northeast-1"  # Tokyo
    AP_NORTHEAST_2: Final[str] = "ap-northeast-2"  # Seoul
    AP_NORTHEAST_3: Final[str] = "ap-northeast-3"  # Osaka
    AP_SOUTH_1: Final[str] = "ap-south-1"  # Mumbai
    AP_SOUTH_2: Final[str] = "ap-south-2"  # Hyderabad
    AP_SOUTHEAST_1: Final[str] = "ap-southeast-1"  # Singapore
    AP_SOUTHEAST_2: Final[str] = "ap-southeast-2"  # Sydney

    # Europe Regions
    EU_CENTRAL_1: Final[str] = "eu-central-1"  # Frankfurt
    EU_CENTRAL_2: Final[str] = "eu-central-2"  # Zurich
    EU_NORTH_1: Final[str] = "eu-north-1"  # Stockholm
    EU_WEST_1: Final[str] = "eu-west-1"  # Ireland
    EU_WEST_2: Final[str] = "eu-west-2"  # London
    EU_WEST_3: Final[str] = "eu-west-3"  # Paris

    # Canada Regions
    CA_CENTRAL_1: Final[str] = "ca-central-1"  # Canada Central

    # South America Regions
    SA_EAST_1: Final[str] = "sa-east-1"  # São Paulo


class RegionSuffixes:
    """Region suffix constants for cross-region inference indicators."""

    CROSS_REGION_INDICATOR: Final[str] = "*"


def normalize_region_name(region_text: str) -> str:
    """
    Normalize region name by removing cross-region indicators and whitespace.

    Args:
        region_text: Raw region text from HTML parsing

    Returns:
        Normalized region identifier
    """
    return region_text.strip().rstrip(RegionSuffixes.CROSS_REGION_INDICATOR)


def is_cross_region_inference(region_text: str) -> bool:
    """
    Check if a region supports cross-region inference.

    Args:
        region_text: Raw region text from HTML parsing

    Returns:
        True if region supports cross-region inference, False otherwise
    """
    return region_text.strip().endswith(RegionSuffixes.CROSS_REGION_INDICATOR)


def get_all_regions() -> List[str]:
    """
    Get all AWS region identifiers.

    Returns:
        List of all available AWS region identifiers
    """
    return [
        AWSRegions.US_EAST_1,
        AWSRegions.US_EAST_2,
        AWSRegions.US_WEST_1,
        AWSRegions.US_WEST_2,
        AWSRegions.US_GOV_EAST_1,
        AWSRegions.US_GOV_WEST_1,
        AWSRegions.AP_NORTHEAST_1,
        AWSRegions.AP_NORTHEAST_2,
        AWSRegions.AP_NORTHEAST_3,
        AWSRegions.AP_SOUTH_1,
        AWSRegions.AP_SOUTH_2,
        AWSRegions.AP_SOUTHEAST_1,
        AWSRegions.AP_SOUTHEAST_2,
        AWSRegions.EU_CENTRAL_1,
        AWSRegions.EU_CENTRAL_2,
        AWSRegions.EU_NORTH_1,
        AWSRegions.EU_WEST_1,
        AWSRegions.EU_WEST_2,
        AWSRegions.EU_WEST_3,
        AWSRegions.CA_CENTRAL_1,
        AWSRegions.SA_EAST_1,
    ]
