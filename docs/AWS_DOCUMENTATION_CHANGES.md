# AWS Bedrock Documentation Structure Changes

## Overview
This document tracks changes to the AWS Bedrock documentation structure that required updates to the LLMManager HTML parser.

## Change Date: November 2025

### Changes Made to AWS Documentation

AWS updated the structure of their Bedrock models documentation page at:
https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html

#### Column Name Changes

1. **Model Column**
   - **Old**: "Model name"
   - **New**: "Model"
   - **Impact**: Primary identifier for table detection and model extraction

#### New Region Columns

The single "Regions supported" column was split into two separate columns:

2. **Single-region model support**
   - Lists AWS regions where the model can be invoked directly in that region
   - Examples: us-east-1, us-west-2, eu-west-1, etc.

3. **Cross-region inference profile support**
   - Lists AWS regions that support cross-region inference for the model
   - Provides geographic redundancy and load balancing capabilities

### Impact on LLMManager

The parser failed with the error:
```
ParsingError: No valid model table found in the documentation
```

This occurred because:
1. The table detection logic looked for "Model name" which no longer existed
2. The region extraction expected a single "Regions supported" column

### Fixes Implemented

#### 1. Updated Constants (`src/bestehorn_llmmanager/bedrock/models/constants.py`)

```python
class HTMLTableColumns:
    MODEL_NAME: Final[str] = "Model"  # Changed from "Model name"
    SINGLE_REGION_SUPPORT: Final[str] = "Single-region model support"  # New
    CROSS_REGION_SUPPORT: Final[str] = "Cross-region inference profile support"  # New
    REGIONS_SUPPORTED: Final[str] = "Regions supported"  # Kept for backward compatibility
```

#### 2. Fixed Link Extraction Typo (`src/bestehorn_llmmanager/bedrock/parsers/bedrock_parser.py`)

**Bug Found**: Line 485 had a typo in the `_extract_link_from_cell` method
```python
href_attr = link.get("hre")  # WRONG - missing 'f'
```

**Fixed to**:
```python
href_attr = link.get("href")  # CORRECT
```

This typo prevented all hyperlinks from being extracted correctly.

#### 3. Enhanced Region Extraction

Added new method `_extract_all_regions_from_row()` that:
- Checks for the new `SINGLE_REGION_SUPPORT` column first
- Checks for the new `CROSS_REGION_SUPPORT` column
- Merges regions from both columns
- Falls back to old `REGIONS_SUPPORTED` column for backward compatibility
- Removes duplicates while preserving order

```python
def _extract_all_regions_from_row(self, cells: List[Tag]) -> List[str]:
    """
    Extract regions from both single-region and cross-region columns.
    Falls back to the old "Regions supported" column if new columns don't exist.
    """
    regions = []
    
    if HTMLTableColumns.SINGLE_REGION_SUPPORT in self._column_indices:
        single_regions = self._extract_regions_from_cell(
            cells=cells, column=HTMLTableColumns.SINGLE_REGION_SUPPORT
        )
        regions.extend(single_regions)
    
    if HTMLTableColumns.CROSS_REGION_SUPPORT in self._column_indices:
        cross_regions = self._extract_regions_from_cell(
            cells=cells, column=HTMLTableColumns.CROSS_REGION_SUPPORT
        )
        regions.extend(cross_regions)
    
    # Fallback for backward compatibility
    if not regions and HTMLTableColumns.REGIONS_SUPPORTED in self._column_indices:
        regions = self._extract_regions_from_cell(
            cells=cells, column=HTMLTableColumns.REGIONS_SUPPORTED
        )
    
    return list(dict.fromkeys(regions))  # Remove duplicates
```

#### 4. Updated Header Detection

Updated the `_is_data_row()` method to recognize both old and new column names:
```python
header_indicators = {"Provider", "Model", "Model name", "Model ID", "Regions supported"}
```

### Backward Compatibility

All changes maintain backward compatibility:
- Old "Model name" column name is still checked in header indicators
- Old "Regions supported" column is used as fallback if new columns aren't present
- Existing model data structures remain unchanged
- No API changes required for client code

### Testing

Updated test file: `test/bestehorn_llmmanager/bedrock/models/test_constants.py`
- Added tests for new column constants
- All 24 tests passing (7 skipped as expected)

### Verification

After implementing the fixes:
```bash
$ python -c "from bestehorn_llmmanager.bedrock.ModelManager import ModelManager; mm = ModelManager(); catalog = mm.refresh_model_data(force_download=True); print(f'Successfully parsed {len(catalog.models)} models')"
Successfully parsed 81 models
```

## Future Considerations

1. **Monitoring**: Watch for additional AWS documentation structure changes
2. **Logging**: Enhanced logging added to track which columns are being used
3. **Flexibility**: Parser now more resilient to column name variations
4. **Region Data**: Now captures both single-region and cross-region support information

## Related Files

- `src/bestehorn_llmmanager/bedrock/models/constants.py` - Column name constants
- `src/bestehorn_llmmanager/bedrock/parsers/bedrock_parser.py` - Main parser logic
- `test/bestehorn_llmmanager/bedrock/models/test_constants.py` - Unit tests

## References

- AWS Bedrock Models Documentation: https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html
- Cross-Region Inference Profiles: https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html
