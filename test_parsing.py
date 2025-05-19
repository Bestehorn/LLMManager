"""
Test script for HTML parsing in ModelIDParser and CRISProfileParser.
"""
import logging
import os
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the parsers
from src.ModelIDParser import ModelIDParser, DEFAULT_MODEL_IDS_URL, DEFAULT_MODEL_IDS_JSON_CACHE
from src.CRISProfileParser import CRISProfileParser, DEFAULT_CRIS_PROFILES_URL, DEFAULT_CRIS_PROFILES_JSON_CACHE

def test_model_parser():
    """Test the ModelIDParser with web content."""
    print("\n=== Testing ModelIDParser ===")
    
    try:
        # Initialize the parser
        parser = ModelIDParser(log_level=logging.INFO)
        
        # Parse from URL
        print(f"Parsing models from {DEFAULT_MODEL_IDS_URL}")
        models = parser.parse_from_url(
            url=DEFAULT_MODEL_IDS_URL,
            cache_file=DEFAULT_MODEL_IDS_JSON_CACHE,
            save_cache=True
        )
        
        # Check results
        print(f"Found {len(models)} models")
        if models:
            print("\nSample models:")
            for i, (model_id, model_info) in enumerate(models.items()):
                if i >= 3:  # Show just a few examples
                    break
                print(f"\nModel: {model_id}")
                print(f"  Regions: {', '.join(model_info.regions[:3])}" + 
                      ("..." if len(model_info.regions) > 3 else ""))
                print(f"  Capabilities: {', '.join(model_info.capabilities)}")
                print(f"  Streaming supported: {model_info.streaming_supported}")
                
            # Export to JSON for inspection
            export_path = "models_test_export.json"
            parser.get_model_collection().to_json(export_path)
            print(f"\nExported models to {export_path}")
            
            return True
        else:
            print("❌ No models found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing model parser: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_cris_parser():
    """Test the CRISProfileParser with web content."""
    print("\n=== Testing CRISProfileParser ===")
    
    try:
        # Initialize the parser
        parser = CRISProfileParser(log_level=logging.INFO)
        
        # Parse from URL
        print(f"Parsing CRIS profiles from {DEFAULT_CRIS_PROFILES_URL}")
        profiles = parser.parse_from_url(
            url=DEFAULT_CRIS_PROFILES_URL,
            cache_file=DEFAULT_CRIS_PROFILES_JSON_CACHE,
            save_cache=True
        )
        
        # Check results
        print(f"Found {len(profiles)} CRIS profiles")
        if profiles:
            print("\nSample profiles:")
            for i, (profile_id, profile_info) in enumerate(profiles.items()):
                if i >= 3:  # Show just a few examples
                    break
                print(f"\nProfile: {profile_id}")
                print(f"  Name: {profile_info.profile_name}")
                print(f"  Source Regions: {', '.join(profile_info.source_regions)}")
                if profile_info.source_regions:
                    first_source = profile_info.source_regions[0]
                    destinations = profile_info.get_destination_regions(first_source)
                    print(f"  Destinations from {first_source}: {', '.join(destinations)}")
            
            # Export to JSON for inspection
            export_path = "cris_profiles_test_export.json"
            parser.get_cris_profile_collection().to_json(export_path)
            print(f"\nExported CRIS profiles to {export_path}")
            
            return True
        else:
            print("❌ No CRIS profiles found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing CRIS parser: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    model_success = test_model_parser()
    cris_success = test_cris_parser()
    
    print("\n=== Test Results ===")
    print(f"ModelIDParser: {'✅ PASSED' if model_success else '❌ FAILED'}")
    print(f"CRISProfileParser: {'✅ PASSED' if cris_success else '❌ FAILED'}")
    print(f"Overall: {'✅ PASSED' if model_success and cris_success else '❌ FAILED'}")

if __name__ == "__main__":
    main()
