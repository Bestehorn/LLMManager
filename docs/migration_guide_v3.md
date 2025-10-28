# Migration Guide: v2 to v3 - Global CRIS Support & Orthogonal Access Methods

## Table of Contents
1. [Overview](#overview)
2. [What Changed and Why](#what-changed-and-why)
3. [Breaking Changes Timeline](#breaking-changes-timeline)
4. [Migration Steps](#migration-steps)
5. [API Changes](#api-changes)
6. [Code Examples](#code-examples)
7. [All 8 Access Method Combinations](#all-8-access-method-combinations)
8. [FAQ](#faq)
9. [Getting Help](#getting-help)

---

## Overview

Version 3.0.0 introduces significant improvements to how LLMManager handles AWS Bedrock model access methods. The key changes are:

1. **Global CRIS Support**: Recognition and support for AWS's new Global Cross-Region Inference Service profiles
2. **Orthogonal Access Methods**: Refactored from enumerated combinations to independent boolean flags
3. **Enhanced Flexibility**: Models can now have any combination of direct, regional CRIS, and global CRIS access

**Migration Priority**: While the old API is deprecated, it continues to work in v3.x with deprecation warnings. You should migrate before v4.0.0 when the deprecated API will be removed.

---

## What Changed and Why

### The Problem We Solved

#### Issue 1: Global CRIS Profiles Not Recognized
AWS introduced "Global CRIS" profiles (prefixed with `global.`) that:
- Route from any commercial AWS region to any commercial AWS region
- List "Commercial AWS Regions" as their destination (not specific regions)
- Were not being parsed by LLMManager v2.x

This caused models like Claude Sonnet 4.5 and Claude Haiku 4.5 to fail loading with warnings:
```
Model 'anthropic.claude-haiku-4-5-20251001-v1:0' has CRIS-only region 'us-east-1' 
but no CRIS inference profile found
Skipping problematic model 'Claude Haiku 4.5'
```

#### Issue 2: Inadequate Access Method Representation
The old `ModelAccessMethod` enum had only 3 values:
- `DIRECT`: Model available directly
- `CRIS_ONLY`: Model available only via CRIS
- `BOTH`: Model available both directly and via CRIS

**Problem**: This couldn't represent:
- Models with both Regional and Global CRIS
- Models with Direct + Regional CRIS + Global CRIS
- The distinction between Regional CRIS and Global CRIS

### The Solution

#### 1. Global CRIS Parser Support
- Parser now recognizes `global.` prefix in inference profile IDs
- Handles "Commercial AWS Regions" marker by expanding to all 21 commercial AWS regions
- Properly flags profiles as global vs regional

#### 2. Orthogonal Access Method Flags
Instead of one enum, use three independent boolean flags:
- `has_direct_access`: Model accessible via regular model ID
- `has_regional_cris`: Model accessible via regional CRIS profile
- `has_global_cris`: Model accessible via global CRIS profile

This allows all **8 possible combinations** (2³):

| has_direct_access | has_regional_cris | has_global_cris | Description |
|-------------------|-------------------|-----------------|-------------|
| ✓ | ✗ | ✗ | Direct only |
| ✗ | ✓ | ✗ | Regional CRIS only |
| ✗ | ✗ | ✓ | Global CRIS only |
| ✓ | ✓ | ✗ | Direct + Regional CRIS |
| ✓ | ✗ | ✓ | Direct + Global CRIS |
| ✗ | ✓ | ✓ | Regional + Global CRIS |
| ✓ | ✓ | ✓ | All three methods |
| ✗ | ✗ | ✗ | Invalid (not allowed) |

---

## Breaking Changes Timeline

### v3.0.0 (Current) - Deprecation Phase
- ✅ Old API still works but emits `DeprecationWarning`
- ✅ New orthogonal flag API introduced
- ✅ Backward compatibility maintained via deprecated properties
- ✅ `ModelAccessMethod.BOTH` and `ModelAccessMethod.CRIS_ONLY` marked as deprecated

### v4.0.0 (Future) - Removal Phase
- ❌ Deprecated enum values will be removed
- ❌ Deprecated properties (`access_method`, `inference_profile_id`) will be removed
- ❌ Code using old API will break

**Action Required**: Migrate to new API before upgrading to v4.0.0

---

## Migration Steps

### Step 1: Assess Your Current Usage

Search your codebase for these patterns:

```bash
# Find usage of deprecated enum values
grep -r "ModelAccessMethod.BOTH" .
grep -r "ModelAccessMethod.CRIS_ONLY" .

# Find usage of deprecated properties
grep -r "\.access_method" .
grep -r "\.inference_profile_id" .
```

### Step 2: Update Enum Value References

**Old Code:**
```python
from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessMethod

# These are deprecated
if method == ModelAccessMethod.BOTH:
    pass
if method == ModelAccessMethod.CRIS_ONLY:
    pass
```

**New Code:**
```python
from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessMethod

# Use new enum values
if method == ModelAccessMethod.REGIONAL_CRIS:
    pass
if method == ModelAccessMethod.GLOBAL_CRIS:
    pass
```

### Step 3: Replace Property Access with Flags

**Old Code:**
```python
access_info = manager.get_model_access_info("Claude 3 Haiku", "us-east-1")

# Deprecated properties
method = access_info.access_method
profile_id = access_info.inference_profile_id
```

**New Code:**
```python
access_info = manager.get_model_access_info("Claude 3 Haiku", "us-east-1")

# Use orthogonal flags
if access_info.has_direct_access:
    model_id = access_info.model_id
    
if access_info.has_regional_cris:
    profile_id = access_info.regional_cris_profile_id
    
if access_info.has_global_cris:
    profile_id = access_info.global_cris_profile_id
```

### Step 4: Update Conditional Logic

**Old Code:**
```python
if access_info.access_method == ModelAccessMethod.BOTH:
    # Try direct first, fall back to CRIS
    model_id = access_info.model_id
    cris_profile = access_info.inference_profile_id
```

**New Code:**
```python
if access_info.has_direct_access and access_info.has_any_cris_access():
    # Try direct first, fall back to CRIS
    model_id = access_info.model_id
    cris_profiles = access_info.get_cris_profile_ids()
```

### Step 5: Test With Warnings Enabled

Enable all warnings to see deprecation notices:

```python
import warnings
warnings.simplefilter("always", DeprecationWarning)

# Your code here
```

### Step 6: Verify All Scenarios Work

Test your application with various models that have different access methods:
- Direct-only models (e.g., older Claude models in their home regions)
- CRIS-only models (e.g., new Claude 4.5 models in certain regions)
- Models with multiple access methods

---

## API Changes

### ModelAccessMethod Enum

#### Deprecated Values
```python
# ❌ DEPRECATED in v3.0.0, will be REMOVED in v4.0.0
ModelAccessMethod.CRIS_ONLY
ModelAccessMethod.BOTH
```

#### New Values
```python
# ✅ Use these instead
ModelAccessMethod.DIRECT         # Direct model ID access
ModelAccessMethod.REGIONAL_CRIS  # Regional CRIS profile access
ModelAccessMethod.GLOBAL_CRIS    # Global CRIS profile access
```

### ModelAccessInfo Class

#### Deprecated Properties
```python
# ❌ DEPRECATED in v3.0.0, will be REMOVED in v4.0.0
access_info.access_method        # Use flags instead
access_info.inference_profile_id # Use specific profile ID properties
```

#### New Attributes
```python
# ✅ Use these orthogonal flags
access_info.has_direct_access: bool
access_info.has_regional_cris: bool
access_info.has_global_cris: bool

# ✅ Use these specific ID properties
access_info.model_id: Optional[str]
access_info.regional_cris_profile_id: Optional[str]
access_info.global_cris_profile_id: Optional[str]
```

#### New Helper Methods
```python
# ✅ New convenience methods
access_info.get_access_summary() -> str
access_info.has_any_cris_access() -> bool
access_info.get_cris_profile_ids() -> List[str]
```

### Factory Method for Legacy Code
```python
# For gradual migration, use from_legacy()
access_info = ModelAccessInfo.from_legacy(
    access_method=ModelAccessMethod.BOTH,  # Deprecated but still works
    region="us-east-1",
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    inference_profile_id="us.anthropic.claude-3-haiku-20240307-v1:0"
)
```

---

## Code Examples

### Example 1: Simple Model Access Check

**Before (v2.x):**
```python
from bestehorn_llmmanager.bedrock import UnifiedModelManager
from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessMethod

manager = UnifiedModelManager()
catalog = manager.ensure_data_available()

access_info = manager.get_model_access_info("Claude 3 Haiku", "us-east-1")

if access_info.access_method == ModelAccessMethod.DIRECT:
    print(f"Use model ID: {access_info.model_id}")
elif access_info.access_method == ModelAccessMethod.CRIS_ONLY:
    print(f"Use CRIS profile: {access_info.inference_profile_id}")
elif access_info.access_method == ModelAccessMethod.BOTH:
    print(f"Direct: {access_info.model_id}")
    print(f"CRIS: {access_info.inference_profile_id}")
```

**After (v3.0+):**
```python
from bestehorn_llmmanager.bedrock import UnifiedModelManager

manager = UnifiedModelManager()
catalog = manager.ensure_data_available()

access_info = manager.get_model_access_info("Claude 3 Haiku", "us-east-1")

# Check each access method independently
if access_info.has_direct_access:
    print(f"Direct access available: {access_info.model_id}")

if access_info.has_regional_cris:
    print(f"Regional CRIS available: {access_info.regional_cris_profile_id}")

if access_info.has_global_cris:
    print(f"Global CRIS available: {access_info.global_cris_profile_id}")

# Or get a summary
print(f"Access methods: {access_info.get_access_summary()}")
```

### Example 2: Choosing Best Access Method

**Before (v2.x):**
```python
def get_best_model_id(access_info):
    """Get the best model identifier to use."""
    if access_info.access_method == ModelAccessMethod.DIRECT:
        return access_info.model_id
    elif access_info.access_method == ModelAccessMethod.BOTH:
        # Prefer direct access
        return access_info.model_id
    elif access_info.access_method == ModelAccessMethod.CRIS_ONLY:
        return access_info.inference_profile_id
    return None
```

**After (v3.0+):**
```python
def get_best_model_id(access_info):
    """Get the best model identifier to use."""
    # Prefer direct access for lowest latency
    if access_info.has_direct_access:
        return access_info.model_id
    
    # Fall back to regional CRIS (more predictable routing)
    if access_info.has_regional_cris:
        return access_info.regional_cris_profile_id
    
    # Last resort: global CRIS
    if access_info.has_global_cris:
        return access_info.global_cris_profile_id
    
    return None
```

### Example 3: Handling New Claude 4.5 Models

**The Problem (v2.x):**
```python
# Claude Sonnet 4.5 and Haiku 4.5 fail to load
manager = UnifiedModelManager()
catalog = manager.ensure_data_available()

# This would return None in v2.x
access_info = manager.get_model_access_info("Claude Sonnet 4.5", "us-east-1")
if not access_info:
    print("Model not available!")  # ❌ False negative
```

**The Solution (v3.0+):**
```python
# Claude Sonnet 4.5 and Haiku 4.5 work correctly
manager = UnifiedModelManager()
catalog = manager.ensure_data_available()

# This now works!
access_info = manager.get_model_access_info("Claude Sonnet 4.5", "us-east-1")
if access_info:
    print(f"Model available via: {access_info.get_access_summary()}")
    
    if access_info.has_global_cris:
        print(f"Global CRIS profile: {access_info.global_cris_profile_id}")
        # Use: global.anthropic.claude-sonnet-4-5-20250929-v1:0
```

### Example 4: Iterating Over All Access Methods

**Before (v2.x):**
```python
def list_all_access_options(access_info):
    """List all ways to access a model."""
    options = []
    
    if access_info.access_method in [ModelAccessMethod.DIRECT, ModelAccessMethod.BOTH]:
        options.append(f"Direct: {access_info.model_id}")
    
    if access_info.access_method in [ModelAccessMethod.CRIS_ONLY, ModelAccessMethod.BOTH]:
        options.append(f"CRIS: {access_info.inference_profile_id}")
    
    return options
```

**After (v3.0+):**
```python
def list_all_access_options(access_info):
    """List all ways to access a model."""
    options = []
    
    if access_info.has_direct_access:
        options.append(f"Direct: {access_info.model_id}")
    
    if access_info.has_regional_cris:
        options.append(f"Regional CRIS: {access_info.regional_cris_profile_id}")
    
    if access_info.has_global_cris:
        options.append(f"Global CRIS: {access_info.global_cris_profile_id}")
    
    return options
```

---

## All 8 Access Method Combinations

Here are real-world examples of each possible combination:

### Combination 1: Direct Only
```python
# Example: Claude 3 Haiku in us-west-2 (its home region)
has_direct_access = True
has_regional_cris = False
has_global_cris = False
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
```

**Usage:**
```python
access_info = manager.get_model_access_info("Claude 3 Haiku", "us-west-2")
if access_info.has_direct_access:
    # Use direct model ID
    response = client.converse(modelId=access_info.model_id, ...)
```

### Combination 2: Regional CRIS Only
```python
# Example: Claude 3 Haiku in ap-northeast-1 (non-home region, pre-global-CRIS)
has_direct_access = False
has_regional_cris = True
has_global_cris = False
regional_cris_profile_id = "us.anthropic.claude-3-haiku-20240307-v1:0"
```

**Usage:**
```python
access_info = manager.get_model_access_info("Claude 3 Haiku", "ap-northeast-1")
if access_info.has_regional_cris:
    # Use regional CRIS profile
    response = client.converse(modelId=access_info.regional_cris_profile_id, ...)
```

### Combination 3: Global CRIS Only
```python
# Example: Claude Sonnet 4.5 in most regions
has_direct_access = False
has_regional_cris = False
has_global_cris = True
global_cris_profile_id = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

**Usage:**
```python
access_info = manager.get_model_access_info("Claude Sonnet 4.5", "us-east-1")
if access_info.has_global_cris:
    # Use global CRIS profile
    response = client.converse(modelId=access_info.global_cris_profile_id, ...)
```

### Combination 4: Direct + Regional CRIS
```python
# Example: Claude 3 Haiku in eu-west-1
has_direct_access = True
has_regional_cris = True
has_global_cris = False
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
regional_cris_profile_id = "eu.anthropic.claude-3-haiku-20240307-v1:0"
```

**Usage:**
```python
access_info = manager.get_model_access_info("Claude 3 Haiku", "eu-west-1")

# Prefer direct for lowest latency
if access_info.has_direct_access:
    model_id = access_info.model_id
elif access_info.has_regional_cris:
    model_id = access_info.regional_cris_profile_id

response = client.converse(modelId=model_id, ...)
```

### Combination 5: Direct + Global CRIS
```python
# Example: Hypothetical future model with both direct and global CRIS
has_direct_access = True
has_regional_cris = False
has_global_cris = True
model_id = "anthropic.claude-opus-5-20260101-v1:0"
global_cris_profile_id = "global.anthropic.claude-opus-5-20260101-v1:0"
```

**Usage:**
```python
access_info = manager.get_model_access_info("Claude Opus 5", "us-east-1")

# Try direct first, fall back to global CRIS
if access_info.has_direct_access:
    model_id = access_info.model_id
elif access_info.has_global_cris:
    model_id = access_info.global_cris_profile_id

response = client.converse(modelId=model_id, ...)
```

### Combination 6: Regional + Global CRIS
```python
# Example: Model transitioning from regional to global CRIS
has_direct_access = False
has_regional_cris = True
has_global_cris = True
regional_cris_profile_id = "us.anthropic.claude-4-20250601-v1:0"
global_cris_profile_id = "global.anthropic.claude-4-20250601-v1:0"
```

**Usage:**
```python
access_info = manager.get_model_access_info("Claude 4", "ap-south-1")

# Choose based on requirements
# Regional CRIS: More predictable routing, region-specific
# Global CRIS: More flexible, routes globally

if access_info.has_regional_cris:
    # Prefer regional for predictable data locality
    model_id = access_info.regional_cris_profile_id
elif access_info.has_global_cris:
    # Fall back to global
    model_id = access_info.global_cris_profile_id

response = client.converse(modelId=model_id, ...)
```

### Combination 7: All Three (Direct + Regional CRIS + Global CRIS)
```python
# Example: Fully flexible model with all access methods
has_direct_access = True
has_regional_cris = True
has_global_cris = True
model_id = "anthropic.claude-full-access-v1:0"
regional_cris_profile_id = "us.anthropic.claude-full-access-v1:0"
global_cris_profile_id = "global.anthropic.claude-full-access-v1:0"
```

**Usage:**
```python
access_info = manager.get_model_access_info("Claude Full Access", "eu-central-1")

# Implement sophisticated fallback strategy
def get_model_id_with_fallback(access_info):
    # 1st choice: Direct (lowest latency)
    if access_info.has_direct_access:
        return access_info.model_id
    
    # 2nd choice: Regional CRIS (predictable)
    if access_info.has_regional_cris:
        return access_info.regional_cris_profile_id
    
    # 3rd choice: Global CRIS (most flexible)
    if access_info.has_global_cris:
        return access_info.global_cris_profile_id
    
    return None

model_id = get_model_id_with_fallback(access_info)
response = client.converse(modelId=model_id, ...)
```

### Combination 8: None (Invalid)
```python
# This combination is INVALID and will raise ValueError
has_direct_access = False
has_regional_cris = False
has_global_cris = False
# ❌ ValueError: At least one access method must be enabled
```

---

## FAQ

### Q1: Do I need to migrate immediately?

**A:** No, the old API continues to work in v3.x with deprecation warnings. However, you should plan to migrate before v4.0.0 (release date TBD) when the deprecated API will be removed.

### Q2: Will my code break if I upgrade to v3.0.0?

**A:** No, your code will continue to work. You'll see deprecation warnings in your logs, but functionality is preserved through backward-compatible properties.

### Q3: What's the difference between Regional CRIS and Global CRIS?

**A:**
- **Regional CRIS**: Routes within specific region pairs (e.g., us-west-2 → us-east-1)
  - Profile format: `us.anthropic.claude-*`
  - More predictable routing
  - Region-specific compliance
  
- **Global CRIS**: Routes from any commercial region to any commercial region
  - Profile format: `global.anthropic.claude-*`
  - More flexible
  - Newest AWS feature (2024/2025)

### Q4: How do I know if a model uses Global CRIS?

**A:**
```python
access_info = manager.get_model_access_info("Claude Sonnet 4.5", "us-east-1")
if access_info and access_info.has_global_cris:
    print(f"Uses Global CRIS: {access_info.global_cris_profile_id}")
    # Output: Uses Global CRIS: global.anthropic.claude-sonnet-4-5-20250929-v1:0
```

### Q5: Which access method should I prefer?

**A:** Recommended priority order:
1. **Direct** (`has_direct_access`) - Lowest latency, most direct
2. **Regional CRIS** (`has_regional_cris`) - Predictable routing, region-specific
3. **Global CRIS** (`has_global_cris`) - Most flexible, newest feature

### Q6: Can I still use `inference_profile_id` property?

**A:** Yes, but it's deprecated. It returns `regional_cris_profile_id` if available, otherwise `global_cris_profile_id`. Migrate to the specific properties for clarity:
```python
# ❌ Deprecated
profile = access_info.inference_profile_id

# ✅ Preferred
if access_info.has_regional_cris:
    profile = access_info.regional_cris_profile_id
elif access_info.has_global_cris:
    profile = access_info.global_cris_profile_id
```

### Q7: How do deprecation warnings appear?

**A:** You'll see warnings like:
```
DeprecationWarning: ModelAccessInfo.access_method property is deprecated since version 3.0.0 
and will be removed in version 4.0.0. Use orthogonal access flags (has_direct_access, 
has_regional_cris, has_global_cris) instead
```

To see all warnings during development:
```python
import warnings
warnings.simplefilter("always", DeprecationWarning)
```

### Q8: What if I need to support both v2 and v3?

**A:** Use the `from_legacy()` factory method:
```python
# Works in both v2 and v3
from bestehorn_llmmanager.bedrock.models.access_method import (
    ModelAccessInfo,
    ModelAccessMethod
)

# This method handles the conversion
access_info = ModelAccessInfo.from_legacy(
    access_method=ModelAccessMethod.BOTH,
    region="us-east-1",
    model_id="...",
    inference_profile_id="..."
)
```

### Q9: Are there performance implications?

**A:** No performance degradation. The new implementation:
- Uses dataclasses (efficient)
- Deprecated properties only emit warnings when accessed (minimal overhead)
- Core logic is unchanged

### Q10: Where can I see the full implementation plan?

**A:** See `implementation_plan.md` in the repository root for the complete 7-phase, 40-step implementation plan.

---

## Getting Help

### Documentation
- **This Migration Guide**: `docs/migration_guide_v3.md`
- **Implementation Plan**: `implementation_plan.md`
- **API Reference**: See docstrings in source code

### Reporting Issues
If you encounter issues during migration:

1. **Check deprecation warnings** in your logs for guidance
2. **Review the code examples** in this guide
3. **Search existing issues**: https://github.com/Bestehorn/LLMManager/issues
4. **Create a new issue** with:
   - Your migration scenario
   - Current code (v2 API)
   - Expected behavior
   - Error messages or warnings

### Community
- **GitHub Discussions**: For migration questions and best practices
- **Issue Tracker**: For bugs and feature requests

---

## Checklist for Migration

Use this checklist to track your migration progress:

- [ ] Review this migration guide completely
- [ ] Search codebase for deprecated patterns
- [ ] Enable deprecation warnings in development
- [ ] Replace `ModelAccessMethod.BOTH` references
- [ ] Replace `ModelAccessMethod.CRIS_ONLY` references
- [ ] Replace `.access_method` property usage
- [ ] Replace `.inference_profile_id` property usage
- [ ] Update conditional logic for access method checking
- [ ] Test with models that have multiple access methods
- [ ] Verify Claude Sonnet 4.5 and Haiku 4.5 work correctly
- [ ] Test your application end-to-end
- [ ] Update documentation and comments
- [ ] Review and suppress any remaining deprecation warnings
- [ ] Plan for v4.0.0 upgrade (when announced)

---

**Last Updated**: October 22, 2025
**Version**: 3.0.0
**Next Version**: 4.0.0 (TBD - will remove deprecated API)
