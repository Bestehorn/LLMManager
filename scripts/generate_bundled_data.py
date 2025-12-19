#!/usr/bin/env python3
"""
Generate bundled catalog data for the bestehorn-llmmanager package.

This script fetches fresh model and CRIS data from AWS Bedrock APIs and
generates a bundled JSON file to be included in the package distribution.
This bundled data serves as a fallback when API calls fail or in offline scenarios.

Usage:
    python scripts/generate_bundled_data.py [--profile PROFILE_NAME] [--region REGION]

Arguments:
    --profile PROFILE_NAME    AWS CLI profile to use for authentication
    --region REGION          AWS region to use for authentication (default: us-east-1)
    --help                   Show this help message

Requirements:
    - AWS credentials configured (via environment variables, AWS CLI, or --profile)
    - Network access to AWS Bedrock APIs
    - Write permissions to src/bestehorn_llmmanager/bedrock/package_data/

Output:
    - Creates/updates: src/bestehorn_llmmanager/bedrock/package_data/bedrock_catalog_bundled.json
    - Includes generation timestamp and package version metadata
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# flake8: noqa: E402 - imports must come after sys.path modification
from bestehorn_llmmanager._version import __version__
from bestehorn_llmmanager.bedrock.auth.auth_manager import AuthManager
from bestehorn_llmmanager.bedrock.catalog.api_fetcher import BedrockAPIFetcher
from bestehorn_llmmanager.bedrock.catalog.transformer import CatalogTransformer
from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import APIFetchError
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    AuthConfig,
    AuthenticationType,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate bundled catalog data for bestehorn-llmmanager package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default credentials
  python scripts/generate_bundled_data.py

  # Use specific AWS CLI profile
  python scripts/generate_bundled_data.py --profile my-profile

  # Use specific profile and region
  python scripts/generate_bundled_data.py --profile my-profile --region us-west-2
        """,
    )

    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="AWS CLI profile name to use for authentication",
    )

    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="AWS region to use for authentication (default: auto-detect)",
    )

    return parser.parse_args()


def generate_bundled_data() -> int:
    """
    Generate bundled catalog data from AWS Bedrock APIs.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Parse command-line arguments
    args = parse_arguments()

    logger.info("=" * 80)
    logger.info("Bundled Catalog Data Generation")
    logger.info("=" * 80)
    logger.info(f"Package version: {__version__}")
    logger.info(f"Generation timestamp: {datetime.now().isoformat()}")
    logger.info("")

    try:
        # Step 1: Initialize components
        logger.info("Step 1: Initializing AWS authentication...")

        # Create AuthConfig based on command-line arguments
        if args.profile:
            logger.info(f"Using AWS profile: {args.profile}")
            auth_config = AuthConfig(
                auth_type=AuthenticationType.PROFILE,
                profile_name=args.profile,
                region=args.region,
            )
            auth_manager = AuthManager(auth_config=auth_config)
        else:
            logger.info("Using automatic credential detection")
            if args.region:
                auth_config = AuthConfig(
                    auth_type=AuthenticationType.AUTO,
                    region=args.region,
                )
                auth_manager = AuthManager(auth_config=auth_config)
            else:
                auth_manager = AuthManager()

        logger.info("✓ Authentication initialized")

        logger.info("")
        logger.info("Step 2: Initializing API fetcher...")
        api_fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager,
            timeout=60,  # Longer timeout for bundled data generation
            max_workers=20,  # More workers for faster generation
            max_retries=5,  # More retries for reliability
        )
        logger.info("✓ API fetcher initialized")

        logger.info("")
        logger.info("Step 3: Initializing catalog transformer...")
        transformer = CatalogTransformer(enable_fuzzy_matching=True)
        logger.info("✓ Transformer initialized")

        # Step 2: Fetch data from AWS APIs
        logger.info("")
        logger.info("Step 4: Fetching data from AWS Bedrock APIs...")
        logger.info("This may take 30-60 seconds depending on network and AWS response times...")
        logger.info("")

        try:
            raw_data = api_fetcher.fetch_all_data()
            logger.info("")
            logger.info("✓ API data fetched successfully")
            logger.info(f"  - Successful regions: {len(raw_data.successful_regions)}")
            logger.info(f"  - Failed regions: {len(raw_data.failed_regions)}")
            logger.info(f"  - Total models: {raw_data.total_models}")
            logger.info(f"  - Total profiles: {raw_data.total_profiles}")

            if raw_data.failed_regions:
                logger.warning("")
                logger.warning("Failed regions:")
                for region, error in raw_data.failed_regions.items():
                    logger.warning(f"  - {region}: {error}")

        except APIFetchError as e:
            logger.error(f"✗ Failed to fetch API data: {e}")
            logger.error("")
            logger.error("Possible causes:")
            logger.error("  - AWS credentials not configured")
            logger.error("  - Network connectivity issues")
            logger.error("  - AWS Bedrock service unavailable")
            logger.error("  - Insufficient IAM permissions")
            logger.error("")
            logger.error("Required IAM permissions:")
            logger.error("  - bedrock:ListFoundationModels")
            logger.error("  - bedrock:ListInferenceProfiles")
            return 1

        # Step 3: Transform data to unified catalog
        logger.info("")
        logger.info("Step 5: Transforming data to unified catalog...")
        generation_timestamp = datetime.now()

        try:
            unified_catalog = transformer.transform_api_data(
                raw_data=raw_data,
                retrieval_timestamp=generation_timestamp,
            )
            logger.info("✓ Data transformation completed")
            logger.info(f"  - Total unified models: {unified_catalog.model_count}")
            logger.info(f"  - Unique regions: {len(unified_catalog.get_all_regions())}")
            logger.info(f"  - Unique providers: {len(unified_catalog.get_all_providers())}")

        except Exception as e:
            logger.error(f"✗ Failed to transform data: {e}")
            return 1

        # Step 4: Add bundled data metadata
        logger.info("")
        logger.info("Step 6: Adding bundled data metadata...")

        # Convert to dictionary and add bundled-specific metadata
        catalog_dict = unified_catalog.to_dict()

        # Update metadata to indicate this is bundled data
        catalog_dict["metadata"]["source"] = "bundled"
        catalog_dict["metadata"]["bundled_data_version"] = __version__
        catalog_dict["metadata"]["generation_timestamp"] = generation_timestamp.isoformat()

        logger.info("✓ Metadata added")
        logger.info(f"  - Bundled data version: {__version__}")
        logger.info(f"  - Generation timestamp: {generation_timestamp.isoformat()}")

        # Step 5: Save to package_data directory
        logger.info("")
        logger.info("Step 7: Saving bundled data to package...")

        # Determine output path
        script_dir = Path(__file__).parent
        package_data_dir = (
            script_dir.parent / "src" / "bestehorn_llmmanager" / "bedrock" / "package_data"
        )
        output_file = package_data_dir / "bedrock_catalog_bundled.json"

        # Create directory if it doesn't exist
        package_data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"  - Output directory: {package_data_dir}")

        # Write JSON file with pretty formatting
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(catalog_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Bundled data saved to: {output_file}")

        # Calculate file size
        file_size_bytes = output_file.stat().st_size
        file_size_kb = file_size_bytes / 1024
        logger.info(f"  - File size: {file_size_kb:.2f} KB ({file_size_bytes:,} bytes)")

        # Step 6: Validate the generated file
        logger.info("")
        logger.info("Step 8: Validating generated file...")

        try:
            # Read back and validate
            with open(output_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            # Basic validation
            if "models" not in loaded_data:
                raise ValueError("Missing 'models' key in generated data")
            if "metadata" not in loaded_data:
                raise ValueError("Missing 'metadata' key in generated data")

            model_count = len(loaded_data["models"])
            if model_count == 0:
                raise ValueError("No models in generated data")

            logger.info("✓ File validation passed")
            logger.info(f"  - Models in file: {model_count}")

        except Exception as e:
            logger.error(f"✗ File validation failed: {e}")
            return 1

        # Step 9: Verify package configuration
        logger.info("")
        logger.info("Step 9: Verifying package configuration...")

        config_issues = []

        # Check MANIFEST.in
        manifest_file = Path("MANIFEST.in")
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_content = f.read()

            if "bedrock_catalog_bundled.json" in manifest_content:
                logger.info("✓ MANIFEST.in includes bundled data")
            else:
                logger.warning("✗ MANIFEST.in does NOT include bundled data")
                config_issues.append("MANIFEST.in missing bundled data reference")
        else:
            logger.warning("✗ MANIFEST.in not found")
            config_issues.append("MANIFEST.in file not found")

        # Check pyproject.toml
        pyproject_file = Path("pyproject.toml")
        if pyproject_file.exists():
            with open(pyproject_file, "r", encoding="utf-8") as f:
                pyproject_content = f.read()

            if "bedrock_catalog_bundled.json" in pyproject_content:
                logger.info("✓ pyproject.toml includes package_data configuration")
            else:
                logger.warning("✗ pyproject.toml does NOT include package_data configuration")
                config_issues.append("pyproject.toml missing package_data configuration")
        else:
            logger.warning("✗ pyproject.toml not found")
            config_issues.append("pyproject.toml file not found")

        # Success summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("✓ Bundled data generation completed successfully!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  - Package version: {__version__}")
        logger.info(f"  - Generation timestamp: {generation_timestamp.isoformat()}")
        logger.info(f"  - Total models: {unified_catalog.model_count}")
        logger.info(f"  - Regions queried: {len(raw_data.successful_regions)}")
        logger.info(f"  - Output file: {output_file}")
        logger.info(f"  - File size: {file_size_kb:.2f} KB")
        logger.info("")

        if config_issues:
            logger.warning("Configuration Issues Found:")
            for issue in config_issues:
                logger.warning(f"  - {issue}")
            logger.warning("")
            logger.warning("Please fix these issues before building the package.")
        else:
            logger.info("✓ Package configuration verified - ready to build!")

        logger.info("")

        return 0

    except Exception as e:
        logger.error("")
        logger.error("=" * 80)
        logger.error("✗ Bundled data generation failed!")
        logger.error("=" * 80)
        logger.error(f"Error: {e}")
        logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(generate_bundled_data())
