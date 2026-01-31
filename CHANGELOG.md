# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.2] - 2026-01-31

### Added
- **Automatic Inference Profile Support**: System now automatically detects when models require inference profile access and retries with appropriate profiles
- `ProfileRequirementDetector` class for detecting profile requirement errors from AWS ValidationException messages
- `AccessMethodSelector` class for intelligent selection of access methods (direct → regional CRIS → global CRIS)
- `AccessMethodTracker` singleton for learning and persisting access method preferences across requests
- Profile requirement detection from AWS error patterns ("with on-demand throughput isn't supported", "retry your request with the ID or ARN of an inference profile")
- Automatic profile retry logic that doesn't count as a separate retry attempt
- Access method learning system that optimizes future requests based on successful access patterns
- Response metadata indicating which access method was used (direct, regional_cris, or global_cris)
- Profile usage statistics in ParallelResponse for monitoring profile adoption
- Comprehensive logging for profile detection, selection, and usage at appropriate levels (WARNING, INFO, DEBUG)
- Support for parallel processing with automatic profile handling per request
- Graceful degradation when profile information is unavailable
- Documentation in `docs/INFERENCE_PROFILE_TROUBLESHOOTING.md` for profile-related issues
- Jupyter notebook `notebooks/InferenceProfile_Demo.ipynb` demonstrating profile support

### Changed
- RetryManager now includes profile detection and automatic retry logic
- BedrockResponse includes access method metadata (access_method_used, inference_profile_used, inference_profile_id)
- ParallelResponse aggregates access method statistics across all parallel requests
- Profile-based access is completely transparent to existing users - no code changes required

### Fixed
- Eliminated unnecessary retry attempts for models requiring inference profiles (e.g., Claude Sonnet 4.5)
- Improved user experience by automatically handling profile requirements without manual configuration

### Backward Compatibility
- All existing code continues to work without changes
- Models supporting direct access use it by default
- No breaking changes to existing APIs
- Profile support is additive only

## [0.3.0] - 2025-11-25

### Added
- AWS Bedrock API-based CRIS data fetching (replaces HTML parsing as primary method)
- `BedrockRegionDiscovery` class for dynamic discovery of Bedrock-enabled AWS regions with caching
- `CRISAPIFetcher` class for parallel API calls across regions using ThreadPoolExecutor
- `get_bedrock_control_client()` method in AuthManager for Bedrock control plane operations
- Automatic fallback from API to HTML parsing if API fetching fails
- File-based region caching with 24-hour TTL to minimize AWS API calls
- `use_api` parameter in CRISManager (defaults to True for API-based fetching)
- `force_download` parameter in LLMManager and ParallelLLMManager for forcing fresh data refresh

### Changed
- CRISManager now uses AWS Bedrock API by default instead of HTML parsing
- HTML parsing preserved as automatic fallback for backward compatibility
- Improved reliability of CRIS data retrieval using official AWS APIs
- Better performance through parallel regional API calls (10-20 regions simultaneously)
- CRIS failures no longer fatal in UnifiedModelManager (logs warning, continues with direct model access)
- Model name column updated from "Model name" to "Model" in parser constants
- Fixed href attribute typo in bedrock_parser (was "hre")

### Fixed
- CRIS data fetch failures due to AWS documentation structure changes (JavaScript dynamic content)
- HTML parser now correctly extracts regions from both "Single-Region support" and "Cross-Region support" columns
- Eliminated dependency on fragile HTML table parsing for CRIS data
- Claude Haiku 4.5, Sonnet 4.5, and Opus 4.5 now correctly recognized as CRIS-only models (AWS documentation incorrectly lists them without CRIS markers)
- Pattern-based detection automatically forces CRIS-only access for known models that require inference profiles

### Security
- All AWS API calls use secure boto3 SDK with proper authentication
- No new credentials or permissions required beyond existing Bedrock access
- Required IAM permissions: `bedrock:ListInferenceProfiles`

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
