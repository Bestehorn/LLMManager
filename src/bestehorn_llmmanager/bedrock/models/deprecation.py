"""
Deprecation utilities for managing API transitions in LLMManager.
Provides helpers for gracefully deprecating old APIs while maintaining backward compatibility.
"""

import warnings
from functools import wraps
from typing import Any, Callable, Optional


def deprecated(
    since: str,
    removal: Optional[str] = None,
    alternative: Optional[str] = None,
    category: type[Warning] = DeprecationWarning,
) -> Callable:
    """
    Decorator to mark functions, methods, or properties as deprecated.

    Args:
        since: Version when the feature was deprecated
        removal: Version when the feature will be removed (optional)
        alternative: Suggested alternative to use instead (optional)
        category: Warning category to use (default: DeprecationWarning)

    Returns:
        Decorated function that emits a deprecation warning when called

    Example:
        @deprecated(since="3.0.0", removal="4.0.0", alternative="new_function()")
        def old_function():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            message = f"{func.__name__} is deprecated since version {since}"

            if removal:
                message += f" and will be removed in version {removal}"

            if alternative:
                message += f". Use {alternative} instead"

            warnings.warn(message, category=category, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def emit_deprecation_warning(
    feature: str,
    since: str,
    removal: Optional[str] = None,
    alternative: Optional[str] = None,
    category: type[Warning] = DeprecationWarning,
    stacklevel: int = 2,
) -> None:
    """
    Emit a deprecation warning for a feature.

    Args:
        feature: Name of the deprecated feature
        since: Version when the feature was deprecated
        removal: Version when the feature will be removed (optional)
        alternative: Suggested alternative to use instead (optional)
        category: Warning category to use (default: DeprecationWarning)
        stacklevel: Stack level for warning (default: 2)

    Example:
        emit_deprecation_warning(
            "ModelAccessMethod.BOTH",
            since="3.0.0",
            removal="4.0.0",
            alternative="orthogonal access flags"
        )
    """
    message = f"{feature} is deprecated since version {since}"

    if removal:
        message += f" and will be removed in version {removal}"

    if alternative:
        message += f". Use {alternative} instead"

    warnings.warn(message, category=category, stacklevel=stacklevel)


class DeprecatedEnumValueWarning(DeprecationWarning):
    """Warning for deprecated enum values."""

    pass


class DeprecatedAPIWarning(DeprecationWarning):
    """Warning for deprecated API usage."""

    pass
