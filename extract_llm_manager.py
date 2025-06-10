#!/usr/bin/env python3
"""
LLMManager Package Extraction Script

Extracts the essential components of the LLMManager project into a distributable
ZIP file that can be used in other projects without modification.

Usage:
    python extract_llm_manager.py [options]

Examples:
    # Basic extraction with defaults
    python extract_llm_manager.py
    
    # Extract with custom package name and version
    python extract_llm_manager.py --package-name mypackage --version 2.0.0
    
    # Extract to specific output directory
    python extract_llm_manager.py --output-dir /path/to/output
    
    # Extract without cleaning up temporary files (for debugging)
    python extract_llm_manager.py --no-cleanup
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# Add workspace to path for imports
sys.path.insert(0, str(Path(__file__).parent / "workspace"))

from llm_manager_extractor import LLMManagerExtractor
from extraction_exceptions import ExtractionError


def setup_logging(log_level: str = "INFO") -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Extract LLMManager package for distribution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Source directory containing LLMManager project (default: current directory)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for extracted package (default: ./dist)"
    )
    
    parser.add_argument(
        "--package-name",
        type=str,
        default="bestehorn",
        help="Name for the extracted package (default: bestehorn)"
    )
    
    parser.add_argument(
        "--version",
        type=str,
        default="1.0.0",
        help="Version string for the package (default: 1.0.0)"
    )
    
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not clean up temporary files after extraction"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the extraction environment without extracting"
    )
    
    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate command line arguments.
    
    Args:
        args: Parsed arguments
        
    Raises:
        ValueError: If arguments are invalid
    """
    if args.source_dir and not args.source_dir.exists():
        raise ValueError(f"Source directory does not exist: {args.source_dir}")
    
    if args.package_name and not args.package_name.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"Invalid package name: {args.package_name}")
    
    if not args.version or not args.version.replace(".", "").replace("-", "").isalnum():
        raise ValueError(f"Invalid version string: {args.version}")


def print_extraction_summary(results: dict) -> None:
    """
    Print a summary of the extraction results.
    
    Args:
        results: Extraction results dictionary
    """
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    print(f"Success: {results['success']}")
    print(f"Package Name: {results['package_name']}")
    print(f"Version: {results['version']}")
    print(f"Files Extracted: {results['extracted_file_count']}")
    print(f"Duration: {results['extraction_duration_seconds']:.2f} seconds")
    print(f"ZIP File: {results['zip_file_path']}")
    
    if 'zip_info' in results and 'error' not in results['zip_info']:
        zip_info = results['zip_info']
        print(f"ZIP Size: {zip_info['zip_file_size_bytes']:,} bytes")
        print(f"Compression: {zip_info['compression_ratio_percent']}%")
    
    print("="*60)


def main() -> int:
    """
    Main entry point for the extraction script.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger = None
    
    try:
        # Parse and validate arguments
        args = parse_arguments()
        validate_arguments(args=args)
        
        # Set up logging
        setup_logging(log_level=args.log_level)
        logger = logging.getLogger(__name__)
        
        logger.info("Starting LLMManager package extraction")
        
        # Initialize extractor
        extractor = LLMManagerExtractor(output_directory=args.output_dir)
        
        # Validate extraction environment if requested
        if args.validate_only:
            logger.info("Validating extraction environment")
            validation_results = extractor.validate_extraction_environment()
            
            if validation_results["valid"]:
                print("✓ Extraction environment validation passed")
                return 0
            else:
                print("✗ Extraction environment validation failed")
                for error in validation_results["errors"]:
                    print(f"  Error: {error}")
                for warning in validation_results["warnings"]:
                    print(f"  Warning: {warning}")
                return 1
        
        # Perform extraction
        results = extractor.extract_package(
            source_root=args.source_dir,
            package_name=args.package_name,
            version=args.version,
            cleanup_temp_files=not args.no_cleanup
        )
        
        # Print results
        print_extraction_summary(results=results)
        
        logger.info("LLMManager package extraction completed successfully")
        return 0
        
    except ExtractionError as e:
        if logger:
            logger.error(f"Extraction failed: {e}")
            if e.details:
                logger.debug(f"Error details: {e.details}")
        print(f"\n✗ Extraction failed: {e}")
        return 1
        
    except ValueError as e:
        if logger:
            logger.error(f"Invalid arguments: {e}")
        print(f"\n✗ Invalid arguments: {e}")
        return 1
        
    except KeyboardInterrupt:
        if logger:
            logger.info("Extraction cancelled by user")
        print("\n⚠ Extraction cancelled by user")
        return 1
        
    except Exception as e:
        if logger:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n✗ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
