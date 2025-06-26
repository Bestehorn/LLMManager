# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-01-23

### Added
- Initial release of bestehorn-llmmanager
- Core LLMManager functionality for AWS Bedrock Converse API
- ParallelLLMManager for concurrent processing across regions
- MessageBuilder for fluent message construction with automatic format detection
- Multi-region and multi-model support with automatic failover
- Comprehensive authentication support (profiles, credentials, IAM roles)
- Intelligent retry logic with configurable strategies
- Response validation capabilities
- Full AWS Bedrock Converse API feature support
- Automatic file type detection for images, documents, and videos
- Support for Claude 3 models (Haiku, Sonnet, Opus)
- HTML content downloading and parsing capabilities
- Extensive test coverage with pytest
- Type hints throughout the codebase
- Comprehensive documentation and examples

### Security
- Secure handling of AWS credentials
- Input validation for all user inputs
- Safe file handling with proper error management

[Unreleased]: https://github.com/example/bestehorn-llmmanager/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/example/bestehorn-llmmanager/releases/tag/v1.0.0
