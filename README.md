# Bedrock LLM Manager

A robust wrapper for AWS Bedrock's Converse API with multi-region and Cross-Region Inference Service (CRIS) support by Markus Bestehorn.

## Features

- **Multi-region support** - Automatically try models across different AWS regions
- **Model fallback** - Gracefully handle errors by switching to alternative models
- **Cross-Region Inference Service (CRIS) optimization** - Automatically use CRIS when available
- **Automatic updates** - Fetch the latest model IDs and CRIS profiles directly from AWS documentation
- **Local caching** - Cache model and CRIS data to reduce web requests
- **Comprehensive error handling** - Recover from throttling and other API errors
- **Flexible authentication** - Support for AWS CLI profiles, access keys, or IAM roles
- **Support for all Bedrock features** - Text generation, image handling, system prompts, guardrails, and more

## Installation

```bash
pip install bestehorn-llm-manager
```

Or directly from the repository:

```bash
pip install git+https://github.com/username/bestehorn-llm-manager.git
```

## Quick Start

```python
from src import LLMManager, Fields, Roles

# Initialize with AWS profile using auto-updating model data
llm_manager = LLMManager(
    profile_name="default",  # Your AWS profile
    regions=["us-east-1", "us-west-2"],  # Preferred regions
    model_ids=["anthropic.claude-3-sonnet-20240229-v1:0"]  # Preferred models
)

# Create a message
messages = [llm_manager.create_text_message("What is AWS Bedrock?")]

# Optional system prompt
system = [llm_manager.create_system_message("You are a helpful AI assistant.")]

# Call the converse API
response = llm_manager.converse(messages=messages, system=system)

# Access the response
print(response.get_content_text())
print(f"Model used: {response.model_id}")
print(f"Region used: {response.region}")
print(f"Used CRIS: {response.is_cris}")
print(f"Tokens used: {response.get_total_tokens()}")
```

## Architecture

The package consists of several key components:

1. **LLMManager** - Main class for interacting with AWS Bedrock's Converse API
2. **BedrockResponse** - Class for encapsulating and accessing response data
3. **ModelIDParser** - Utility for parsing model information from AWS documentation
4. **CRISProfileParser** - Utility for parsing CRIS profile information
5. **ModelProfileCollection** - Class for managing and caching model data with timestamps
6. **CRISProfileCollection** - Class for managing and caching CRIS profile data with timestamps

## Advanced Usage

### Automatic Model and CRIS Profile Updates

The LLMManager now supports automatically retrieving and parsing model IDs and CRIS profiles directly from AWS documentation:

```python
# Initialize with auto-updating and web-based sources
llm_manager = LLMManager(
    # Standard authentication parameters
    profile_name="default",
    regions=["us-east-1", "us-west-2"],
    model_ids=["anthropic.claude-3-sonnet-20240229-v1:0"],
    
    # Auto-update configuration
    model_ids_url="https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html",
    cris_profiles_url="https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html",
    model_ids_cache_file="model_ids_cache.json",
    cris_profiles_cache_file="cris_profiles_cache.json",
    max_profile_age=86400,  # 1 day in seconds
    force_model_id_update=True,  # Force update regardless of cache
    force_cris_profile_update=False  # Use cache if available and not expired
)

# Export the current profiles to JSON files
model_success, cris_success = llm_manager.export_profiles_to_json(
    model_file_path="exported_models.json",
    cris_file_path="exported_cris.json"
)

# Access the profile collections
model_collection = llm_manager.get_model_profile_collection()
cris_collection = llm_manager.get_cris_profile_collection()
```

See the Jupyter notebook `notebooks/HelloWorldLLMManager.ipynb` for detailed examples, including:

- Working with system prompts
- Customizing inference parameters
- Using different performance settings
- Handling images (multimodal models)
- Error handling and fallback mechanisms

## Development

To set up the development environment:

```bash
git clone https://github.com/username/bestehorn-llm-manager.git
cd bestehorn-llm-manager
pip install -e .
```

## License

MIT

## Author

[Markus Bestehorn](https://www.linkedin.com/in/markus-bestehorn/)
