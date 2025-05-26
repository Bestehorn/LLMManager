"""
Demonstration script for the Unified Bedrock Model Manager.

This script shows how to use the UnifiedModelManager to get comprehensive
model access information that integrates regular Bedrock models with CRIS data.

This is a workspace file for demonstration purposes.
"""

import logging
from pathlib import Path
import sys

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent / "src"))

from bedrock.UnifiedModelManager import UnifiedModelManager
from bedrock.models.access_method import ModelAccessMethod

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Demonstrate the unified model manager functionality."""
    print("🚀 Unified Bedrock Model Manager Demo")
    print("=" * 50)
    
    # Initialize the unified manager
    print("\n1. Initializing UnifiedModelManager...")
    manager = UnifiedModelManager(
        force_download=False,  # Set to True to always download fresh data
        download_timeout=30
    )
    
    try:
        # Refresh unified data (this will download and correlate both sources)
        print("\n2. Refreshing unified model data...")
        print("   This will:")
        print("   - Download regular Bedrock model documentation")
        print("   - Download CRIS model documentation")
        print("   - Correlate and merge the data")
        print("   - Create unified catalog with comprehensive access info")
        
        catalog = manager.refresh_unified_data()
        
        print(f"\n✅ Successfully created unified catalog with {catalog.model_count} models")
        
        # Get correlation statistics
        stats = manager.get_correlation_stats()
        print(f"   📊 Correlation stats: {stats}")
        
        # Demonstrate key functionality
        print("\n3. Demonstrating key functionality...")
        
        # Show all model names
        model_names = manager.get_model_names()
        print(f"\n📋 Available models ({len(model_names)}):")
        for i, name in enumerate(model_names[:10]):  # Show first 10
            print(f"   {i+1}. {name}")
        if len(model_names) > 10:
            print(f"   ... and {len(model_names) - 10} more")
        
        # Show all supported regions
        regions = manager.get_all_supported_regions()
        print(f"\n🌍 Supported regions ({len(regions)}):")
        for region in regions[:15]:  # Show first 15
            print(f"   - {region}")
        if len(regions) > 15:
            print(f"   ... and {len(regions) - 15} more")
        
        # Demonstrate access information queries
        print("\n4. Model access information examples...")
        
        # Example 1: Check a model that should have both direct and CRIS access
        test_cases = [
            ("Claude 3 Haiku", "us-east-1"),
            ("Nova Lite", "us-east-1"),
            ("Nova Pro", "eu-west-1"),
            ("Meta Llama 3.1 70B Instruct", "us-west-2"),
        ]
        
        for model_name, region in test_cases:
            if manager.has_model(model_name):
                print(f"\n🔍 Checking access for '{model_name}' in '{region}':")
                
                # Check if available
                available = manager.is_model_available_in_region(model_name=model_name, region=region)
                print(f"   Available: {available}")
                
                if available:
                    # Get access info
                    access_info = manager.get_model_access_info(model_name=model_name, region=region)
                    if access_info:
                        print(f"   Access method: {access_info.access_method.value}")
                        if access_info.model_id:
                            print(f"   Model ID: {access_info.model_id}")
                        if access_info.inference_profile_id:
                            print(f"   Inference Profile: {access_info.inference_profile_id}")
                        
                        # Get recommendation
                        recommendation = manager.get_recommended_access(model_name=model_name, region=region)
                        if recommendation:
                            print(f"   Recommended: {recommendation.recommended_access.access_method.value}")
                            print(f"   Rationale: {recommendation.rationale}")
                            if recommendation.alternatives:
                                print(f"   Alternatives: {len(recommendation.alternatives)}")
            else:
                print(f"\n❌ Model '{model_name}' not found in catalog")
        
        # Show regional breakdown
        print(f"\n5. Regional analysis for us-east-1...")
        us_east_models = manager.get_models_by_region(region="us-east-1")
        direct_models = manager.get_direct_access_models_by_region(region="us-east-1")
        cris_models = manager.get_cris_only_models_by_region(region="us-east-1")
        
        print(f"   Total models in us-east-1: {len(us_east_models)}")
        print(f"   Direct access models: {len(direct_models)}")
        print(f"   CRIS-only models: {len(cris_models)}")
        
        # Show provider breakdown
        print(f"\n6. Provider analysis...")
        providers = ["Amazon", "Anthropic", "Meta", "Mistral"]
        for provider in providers:
            provider_models = manager.get_models_by_provider(provider=provider)
            if provider_models:
                print(f"   {provider}: {len(provider_models)} models")
        
        print(f"\n✅ Demo completed successfully!")
        print(f"   Unified catalog saved to: {manager.json_output_path}")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        logging.exception("Demo failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
