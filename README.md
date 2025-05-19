# Bedrock LLM Manager

A robust wrapper for AWS Bedrock's Converse API with multi-region and Cross-Region Inference Service (CRIS) support by Markus Bestehorn.

## Features

- **Multi-region support** - Automatically try models across different AWS regions
- **Model fallback** - Gracefully handle errors by switching to alternative models
- **Cross-Region Inference Service (CRIS) optimization** - Automatically use CRIS when available
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

# Initialize with AWS profile
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

## Advanced Usage

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
