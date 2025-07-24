# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.13] - 2025-07-24

### Added
- Comprehensive streaming functionality for real-time responses
- Stream processing with robust retry mechanisms
- Event-based streaming handlers for different response types
- Streaming constants and configuration management
- Retrying stream iterator for handling connection issues
- Streaming retry manager with exponential backoff
- Integration tests for streaming functionality
- Streaming examples and documentation

### Fixed
- Cross-platform compatibility issues in release script
- Native setuptools-scm integration for version management
- Improved version detection and release automation

### Changed
- Migrated from bump2version to native setuptools-scm approach
- Simplified release process using git tags only
- Enhanced release script with dry-run support

## [0.1.12] - 2025-07-24

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

[Unreleased]: https://github.com/Bestehorn/LLMManager/compare/v0.1.13...HEAD
[0.1.13]: https://github.com/Bestehorn/LLMManager/releases/tag/v0.1.13
[0.1.12]: https://github.com/Bestehorn/LLMManager/releases/tag/v0.1.12
