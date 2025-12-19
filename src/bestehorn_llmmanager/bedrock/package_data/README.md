# Package Data Directory

This directory contains bundled fallback data for the bestehorn-llmmanager package.

## Contents

- `bedrock_catalog_bundled.json`: Pre-generated catalog of AWS Bedrock models and CRIS profiles

## Purpose

The bundled data serves as a fallback when:
- AWS API calls fail
- Network connectivity is unavailable
- AWS credentials are not configured
- Operating in offline/air-gapped environments

## Generation

The bundled data is generated using:
```bash
python scripts/generate_bundled_data.py
```

This script should be run before each package release to ensure the bundled data is up-to-date.

## Package Distribution

This data is included in the package distribution via:
- `MANIFEST.in`: Explicitly includes the JSON file
- `pyproject.toml`: Configures package_data to include this directory

## Version Information

The bundled data includes metadata about:
- Package version at generation time
- Generation timestamp
- AWS regions queried
- Number of models and profiles included
