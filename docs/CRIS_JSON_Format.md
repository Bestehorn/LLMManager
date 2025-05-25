# CRIS JSON Format Specification

## Overview

This document defines the JSON format used by the CRISManager for storing Amazon Bedrock Cross-Region Inference (CRIS) model information. The format is designed to be both human-readable and machine-parseable, with comprehensive metadata for each CRIS model.

**Version 2.0** introduces support for multiple regional inference profiles per model, fixing the regional overwrite bug while maintaining backward compatibility.

## Table of Contents

- [Schema Overview](#schema-overview)
- [Root Structure](#root-structure)
- [Field Definitions](#field-definitions)
- [Data Types](#data-types)
- [Validation Rules](#validation-rules)
- [Examples](#examples)
- [Versioning](#versioning)
- [Field Constants](#field-constants)
- [Migration Guide](#migration-guide)

## Schema Overview

The CRIS JSON format follows a hierarchical structure with the following characteristics:

- **Root Level**: Contains metadata and the main CRIS data collection
- **CRIS Level**: Contains individual model entries indexed by model name
- **Model Level**: Contains detailed information about each CRIS model with multiple inference profiles
- **Inference Profile Level**: Contains region-specific inference profile information
- **Region Mappings**: Contains source-to-destination region relationships for each profile

### JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CRIS Model Catalog",
  "type": "object",
  "required": ["retrieval_timestamp", "CRIS"],
  "properties": {
    "retrieval_timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of when the data was retrieved"
    },
    "CRIS": {
      "type": "object",
      "description": "Collection of CRIS models indexed by model name",
      "patternProperties": {
        "^[A-Za-z0-9\\s\\-\\.]+$": {
          "$ref": "#/definitions/CRISModel"
        }
      }
    }
  },
  "definitions": {
    "CRISModel": {
      "type": "object",
      "required": ["model_name", "inference_profiles"],
      "properties": {
        "model_name": {
          "type": "string",
          "pattern": "^[A-Za-z0-9\\s\\-\\.]+$",
          "description": "Clean model name without region prefixes"
        },
        "inference_profiles": {
          "type": "object",
          "description": "Collection of inference profiles for this model",
          "patternProperties": {
            "^[a-z0-9\\-\\.]+:[0-9]+$": {
              "$ref": "#/definitions/InferenceProfile"
            }
          },
          "minProperties": 1
        },
        "inference_profile_id": {
          "type": "string",
          "pattern": "^[a-z0-9\\-\\.]+:[0-9]+$",
          "description": "Primary inference profile ID for backward compatibility"
        }
      }
    },
    "InferenceProfile": {
      "type": "object",
      "required": ["region_mappings"],
      "properties": {
        "region_mappings": {
          "type": "object",
          "description": "Source regions mapped to destination regions for this profile",
          "patternProperties": {
            "^[a-z]{2,}-[a-z]+-[0-9]+$": {
              "type": "array",
              "items": {
                "type": "string",
                "pattern": "^[a-z]{2,}-[a-z]+-[0-9]+$"
              },
              "minItems": 1,
              "uniqueItems": true
            }
          },
          "minProperties": 1
        }
      }
    }
  }
}
```

## Root Structure

The JSON document has the following top-level structure:

```json
{
  "retrieval_timestamp": "2025-01-23T20:45:59+02:00",
  "CRIS": {
    "Model Name 1": { /* Model details with multiple inference profiles */ },
    "Model Name 2": { /* Model details with multiple inference profiles */ },
    ...
  }
}
```

### Root Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `retrieval_timestamp` | `string` | Yes | ISO 8601 timestamp indicating when the data was retrieved from AWS |
| `CRIS` | `object` | Yes | Collection of CRIS models indexed by model name |

## Field Definitions

### retrieval_timestamp

**Type**: `string` (ISO 8601 format)  
**Required**: Yes  
**Description**: Timestamp indicating when the CRIS documentation was downloaded and parsed.

**Format**: `YYYY-MM-DDTHH:MM:SS±HH:MM`

**Examples**:
- `"2025-01-23T20:45:59+02:00"` (with timezone)
- `"2025-01-23T18:45:59Z"` (UTC)

### CRIS

**Type**: `object`  
**Required**: Yes  
**Description**: Root container for all CRIS model information. Each property key is a model name, and the value is a model object.

**Key Pattern**: Model names must match `^[A-Za-z0-9\s\-\.]+$`

### Model Object Structure

Each model within the CRIS object has the following structure:

```json
{
  "model_name": "Nova Lite",
  "inference_profiles": {
    "us.amazon.nova-lite-v1:0": {
      "region_mappings": {
        "us-west-2": ["us-east-1", "us-east-2", "us-west-2"],
        "us-east-2": ["us-east-1", "us-east-2", "us-west-2"],
        "us-east-1": ["us-east-1", "us-east-2", "us-west-2"]
      }
    },
    "eu.amazon.nova-lite-v1:0": {
      "region_mappings": {
        "eu-west-1": ["eu-central-1", "eu-west-1", "eu-west-3"],
        "eu-central-1": ["eu-central-1", "eu-west-1", "eu-west-3"]
      }
    }
  },
  "inference_profile_id": "us.amazon.nova-lite-v1:0"
}
```

#### model_name

**Type**: `string`  
**Required**: Yes  
**Pattern**: `^[A-Za-z0-9\s\-\.]+$`  
**Description**: Clean model name without region prefixes (e.g., "US ", "EU ").

**Examples**:
- `"Nova Lite"`
- `"Claude 3.5 Sonnet"`
- `"Llama 3.1 405B"`

#### inference_profiles

**Type**: `object`  
**Required**: Yes  
**Description**: Collection of inference profiles for this model, indexed by inference profile ID.

**Key Pattern**: `^[a-z0-9\-\.]+:[0-9]+$` (inference profile ID format)  
**Value Type**: `InferenceProfile` object  
**Constraints**: Must contain at least one inference profile

**Structure**:
- **Keys**: Inference profile IDs (e.g., `"us.amazon.nova-lite-v1:0"`)
- **Values**: Inference profile objects containing region mappings

#### inference_profile_id

**Type**: `string`  
**Required**: No (but recommended for backward compatibility)  
**Pattern**: `^[a-z0-9\-\.]+:[0-9]+$`  
**Description**: Primary inference profile ID for backward compatibility. Typically the US variant if available, otherwise the first available profile.

**Format**: `{region}.{provider}.{model-identifier}:{version}`

**Examples**:
- `"us.amazon.nova-lite-v1:0"`
- `"us.anthropic.claude-3-5-sonnet-20241022-v2:0"`
- `"us.meta.llama3-1-405b-instruct-v1:0"`

### Inference Profile Object Structure

Each inference profile object contains region mapping information specific to that profile:

```json
{
  "region_mappings": {
    "us-west-2": ["us-east-1", "us-east-2", "us-west-2"],
    "us-east-1": ["us-east-1", "us-west-2"]
  }
}
```

#### region_mappings

**Type**: `object`  
**Required**: Yes  
**Description**: Maps source regions to arrays of destination regions where requests can be routed for this specific inference profile.

**Structure**:
- **Keys**: Source region identifiers (pattern: `^[a-z]{2,}-[a-z]+-[0-9]+$`)
- **Values**: Arrays of destination region identifiers

**Constraints**:
- Each source region must map to at least one destination region
- Destination region arrays must contain unique values
- All region identifiers must follow AWS region naming conventions
- Region mappings are specific to each inference profile

## Data Types

### String Types

| Type | Pattern/Format | Description | Examples |
|------|----------------|-------------|----------|
| `model_name` | `^[A-Za-z0-9\s\-\.]+$` | Alphanumeric with spaces, hyphens, dots | `"Nova Lite"`, `"Claude 3.5"` |
| `inference_profile_id` | `^[a-z0-9\-\.]+:[0-9]+$` | Lowercase with colon separator | `"us.amazon.nova-lite-v1:0"` |
| `region_identifier` | `^[a-z]{2,}-[a-z]+-[0-9]+$` | AWS region format | `"us-east-1"`, `"eu-west-1"` |
| `timestamp` | ISO 8601 | Date-time with timezone | `"2025-01-23T20:45:59+02:00"` |

### Array Types

| Type | Element Type | Constraints |
|------|--------------|-------------|
| `destination_regions` | `region_identifier` | Min 1 item, unique values |

### Object Types

| Type | Properties | Description |
|------|------------|-------------|
| `CRISModel` | `model_name`, `inference_profiles`, `inference_profile_id` | Complete model information with multiple profiles |
| `InferenceProfile` | `region_mappings` | Region mappings for a specific inference profile |
| `region_mappings` | Dynamic keys (source regions) | Source-to-destination mappings for a profile |

## Validation Rules

### Schema Validation

1. **Required Fields**: All required fields must be present
2. **Type Compliance**: All fields must match their specified types
3. **Pattern Matching**: String fields must match their regex patterns
4. **Array Constraints**: Arrays must meet minimum length and uniqueness requirements
5. **Object Constraints**: Objects must meet minimum property requirements

### Business Logic Validation

1. **Model Name Consistency**: The model name in the object must match the key in the CRIS collection
2. **Region Validation**: All region identifiers must be valid AWS regions
3. **Profile ID Consistency**: Inference profile object keys must match the inference profile ID format
4. **Backward Compatibility**: If `inference_profile_id` is present, it must exist in the `inference_profiles` collection
5. **Regional Segregation**: Inference profiles should contain region mappings appropriate to their regional prefix

### Example Validation Code

```python
import re
from datetime import datetime
from typing import Dict, Any, List

def validate_cris_json(data: dict) -> bool:
    """Validate CRIS JSON format v2.0."""
    
    # Check root structure
    if not isinstance(data, dict):
        return False
    
    if "retrieval_timestamp" not in data or "CRIS" not in data:
        return False
    
    # Validate timestamp
    try:
        datetime.fromisoformat(data["retrieval_timestamp"])
    except ValueError:
        return False
    
    # Validate CRIS models
    cris_data = data["CRIS"]
    if not isinstance(cris_data, dict):
        return False
    
    for model_name, model_info in cris_data.items():
        if not validate_model(model_name, model_info):
            return False
    
    return True

def validate_model(model_name: str, model_info: dict) -> bool:
    """Validate individual model information."""
    
    # Check required fields
    required_fields = ["model_name", "inference_profiles"]
    if not all(field in model_info for field in required_fields):
        return False
    
    # Validate model name consistency
    if model_info["model_name"] != model_name:
        return False
    
    # Validate inference profiles
    inference_profiles = model_info["inference_profiles"]
    if not isinstance(inference_profiles, dict) or len(inference_profiles) == 0:
        return False
    
    profile_pattern = r"^[a-z0-9\-\.]+:[0-9]+$"
    
    for profile_id, profile_info in inference_profiles.items():
        # Validate profile ID format
        if not re.match(profile_pattern, profile_id):
            return False
        
        # Validate profile structure
        if not validate_inference_profile(profile_info):
            return False
    
    # Validate backward compatibility field if present
    if "inference_profile_id" in model_info:
        primary_id = model_info["inference_profile_id"]
        if not re.match(profile_pattern, primary_id):
            return False
        if primary_id not in inference_profiles:
            return False
    
    return True

def validate_inference_profile(profile_info: dict) -> bool:
    """Validate inference profile structure."""
    
    if not isinstance(profile_info, dict):
        return False
    
    if "region_mappings" not in profile_info:
        return False
    
    region_mappings = profile_info["region_mappings"]
    if not isinstance(region_mappings, dict) or len(region_mappings) == 0:
        return False
    
    region_pattern = r"^[a-z]{2,}-[a-z]+-[0-9]+$"
    
    for source_region, destinations in region_mappings.items():
        # Validate source region format
        if not re.match(region_pattern, source_region):
            return False
        
        # Validate destinations
        if not isinstance(destinations, list) or len(destinations) == 0:
            return False
        
        # Check destination format and uniqueness
        if len(destinations) != len(set(destinations)):
            return False
        
        for dest in destinations:
            if not re.match(region_pattern, dest):
                return False
    
    return True
```

## Examples

### Minimal Example

```json
{
  "retrieval_timestamp": "2025-01-23T20:45:59+02:00",
  "CRIS": {
    "Nova Lite": {
      "model_name": "Nova Lite",
      "inference_profiles": {
        "us.amazon.nova-lite-v1:0": {
          "region_mappings": {
            "us-east-1": ["us-east-1", "us-west-2"]
          }
        }
      },
      "inference_profile_id": "us.amazon.nova-lite-v1:0"
    }
  }
}
```

### Multi-Profile Example

```json
{
  "retrieval_timestamp": "2025-01-23T20:45:59+02:00",
  "CRIS": {
    "Nova Lite": {
      "model_name": "Nova Lite",
      "inference_profiles": {
        "us.amazon.nova-lite-v1:0": {
          "region_mappings": {
            "us-west-2": ["us-east-1", "us-east-2", "us-west-2"],
            "us-east-2": ["us-east-1", "us-east-2", "us-west-2"],
            "us-east-1": ["us-east-1", "us-east-2", "us-west-2"]
          }
        },
        "eu.amazon.nova-lite-v1:0": {
          "region_mappings": {
            "eu-west-1": ["eu-central-1", "eu-west-1", "eu-west-3"],
            "eu-central-1": ["eu-central-1", "eu-west-1", "eu-west-3"]
          }
        },
        "apac.amazon.nova-lite-v1:0": {
          "region_mappings": {
            "ap-southeast-1": ["ap-southeast-1", "ap-northeast-1"],
            "ap-northeast-1": ["ap-southeast-1", "ap-northeast-1"]
          }
        }
      },
      "inference_profile_id": "us.amazon.nova-lite-v1:0"
    }
  }
}
```

### Complete Multi-Model Example

```json
{
  "retrieval_timestamp": "2025-01-23T20:45:59+02:00",
  "CRIS": {
    "Nova Lite": {
      "model_name": "Nova Lite",
      "inference_profiles": {
        "us.amazon.nova-lite-v1:0": {
          "region_mappings": {
            "us-west-2": ["us-east-1", "us-east-2", "us-west-2"],
            "us-east-1": ["us-east-1", "us-east-2", "us-west-2"]
          }
        },
        "eu.amazon.nova-lite-v1:0": {
          "region_mappings": {
            "eu-west-1": ["eu-central-1", "eu-west-1"],
            "eu-central-1": ["eu-central-1", "eu-west-1"]
          }
        }
      },
      "inference_profile_id": "us.amazon.nova-lite-v1:0"
    },
    "Claude 3.5 Sonnet": {
      "model_name": "Claude 3.5 Sonnet",
      "inference_profiles": {
        "us.anthropic.claude-3-5-sonnet-20241022-v2:0": {
          "region_mappings": {
            "us-west-2": ["us-east-1", "us-west-2"],
            "us-east-1": ["us-east-1", "us-west-2"]
          }
        },
        "eu.anthropic.claude-3-5-sonnet-20241022-v2:0": {
          "region_mappings": {
            "eu-west-1": ["eu-central-1", "eu-west-1"]
          }
        }
      },
      "inference_profile_id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    }
  }
}
```

## Versioning

### Current Version

- **Format Version**: 2.0
- **Schema Version**: 2025-01-25
- **Compatibility**: CRISManager v2.0+

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-23 | Initial format specification |
| 2.0 | 2025-01-25 | Added support for multiple inference profiles per model, fixed regional overwrite bug |

### Version 2.0 Changes

**Breaking Changes**:
- `region_mappings` moved from model level to inference profile level
- New `inference_profiles` field containing multiple profiles per model

**Backward Compatibility**:
- `inference_profile_id` field maintained for compatibility
- Legacy parsers can still access primary profile via backward compatibility field
- New `region_mappings` property on model provides merged view of all profiles

**Migration Benefits**:
- Fixes regional overwrite bug where US profiles contained EU region mappings
- Proper separation of regional inference profiles
- Support for multiple geographic deployments per model
- Enhanced querying capabilities by specific inference profile

### Future Considerations

Potential future enhancements to the format:

1. **Model Metadata**: Additional fields like cost, latency, capacity per profile
2. **Regional Preferences**: Priority ordering for destination regions
3. **Availability Windows**: Time-based availability information per profile
4. **Performance Metrics**: Historical performance data per inference profile
5. **Profile Metadata**: Additional metadata for each inference profile

## Field Constants

To maintain code consistency, all JSON field names are defined as constants:

### Python Constants

```python
class CRISJSONFields:
    """JSON field name constants for CRIS output structure."""
    
    RETRIEVAL_TIMESTAMP: Final[str] = "retrieval_timestamp"
    CRIS: Final[str] = "CRIS"
    MODEL_NAME: Final[str] = "model_name"
    INFERENCE_PROFILES: Final[str] = "inference_profiles"
    REGION_MAPPINGS: Final[str] = "region_mappings"
    
    # Backward compatibility field
    INFERENCE_PROFILE_ID: Final[str] = "inference_profile_id"
```

### Usage Example

```python
from src.bedrock.models.cris_constants import CRISJSONFields

# Accessing JSON data using constants
timestamp = data[CRISJSONFields.RETRIEVAL_TIMESTAMP]
cris_models = data[CRISJSONFields.CRIS]

for model_name, model_info in cris_models.items():
    # Access new inference profiles structure
    profiles = model_info[CRISJSONFields.INFERENCE_PROFILES]
    
    for profile_id, profile_info in profiles.items():
        mappings = profile_info[CRISJSONFields.REGION_MAPPINGS]
        print(f"Profile {profile_id} mappings: {mappings}")
    
    # Backward compatibility access
    primary_id = model_info[CRISJSONFields.INFERENCE_PROFILE_ID]
```

## Migration Guide

### From Version 1.0 to 2.0

#### Old Structure (v1.0)
```json
{
  "retrieval_timestamp": "2025-01-23T20:45:59+02:00",
  "CRIS": {
    "Nova Lite": {
      "model_name": "Nova Lite",
      "inference_profile_id": "us.amazon.nova-lite-v1:0",
      "region_mappings": {
        "us-west-2": ["us-east-1", "us-east-2", "us-west-2"]
      }
    }
  }
}
```

#### New Structure (v2.0)
```json
{
  "retrieval_timestamp": "2025-01-23T20:45:59+02:00",
  "CRIS": {
    "Nova Lite": {
      "model_name": "Nova Lite",
      "inference_profiles": {
        "us.amazon.nova-lite-v1:0": {
          "region_mappings": {
            "us-west-2": ["us-east-1", "us-east-2", "us-west-2"]
          }
        }
      },
      "inference_profile_id": "us.amazon.nova-lite-v1:0"
    }
  }
}
```

#### Migration Code

```python
def migrate_v1_to_v2(v1_data: dict) -> dict:
    """Migrate CRIS JSON from v1.0 to v2.0 format."""
    
    v2_data = {
        CRISJSONFields.RETRIEVAL_TIMESTAMP: v1_data[CRISJSONFields.RETRIEVAL_TIMESTAMP],
        CRISJSONFields.CRIS: {}
    }
    
    for model_name, model_info in v1_data[CRISJSONFields.CRIS].items():
        profile_id = model_info[CRISJSONFields.INFERENCE_PROFILE_ID]
        region_mappings = model_info[CRISJSONFields.REGION_MAPPINGS]
        
        v2_model = {
            CRISJSONFields.MODEL_NAME: model_name,
            CRISJSONFields.INFERENCE_PROFILES: {
                profile_id: {
                    CRISJSONFields.REGION_MAPPINGS: region_mappings
                }
            },
            CRISJSONFields.INFERENCE_PROFILE_ID: profile_id
        }
        
        v2_data[CRISJSONFields.CRIS][model_name] = v2_model
    
    return v2_data
```

### Integration Guidelines

#### Reading CRIS JSON v2.0

```python
import json
from pathlib import Path
from src.bedrock.models.cris_structures import CRISCatalog

def load_cris_data(json_path: Path) -> CRISCatalog:
    """Load CRIS data from JSON file (v2.0 format)."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Validate format version
    if not validate_cris_json(data):
        raise ValueError("Invalid CRIS JSON v2.0 format")
    
    return CRISCatalog.from_dict(data)
```

#### Writing CRIS JSON v2.0

```python
import json
from pathlib import Path
from src.bedrock.models.cris_structures import CRISCatalog

def save_cris_data(catalog: CRISCatalog, json_path: Path) -> None:
    """Save CRIS data to JSON file (v2.0 format)."""
    data = catalog.to_dict()
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
```

#### Querying Multiple Inference Profiles

```python
def query_profiles_by_region(catalog: CRISCatalog, source_region: str) -> dict:
    """Query inference profiles that support a specific source region."""
    
    results = {}
    
    for model_name, model_info in catalog.cris_models.items():
        supporting_profiles = []
        
        for profile_id, profile_info in model_info.inference_profiles.items():
            if profile_info.can_route_from_source(source_region):
                supporting_profiles.append({
                    'profile_id': profile_id,
                    'destinations': profile_info.get_destinations_for_source(source_region)
                })
        
        if supporting_profiles:
            results[model_name] = supporting_profiles
    
    return results
```

---

**Note**: Version 2.0 of this format specification fixes the critical regional overwrite bug by properly separating inference profiles by region. This ensures that US inference profiles only contain US region mappings, EU profiles only contain EU mappings, etc. The format maintains backward compatibility through the `inference_profile_id` field while providing enhanced capabilities through the new `inference_profiles` structure.
