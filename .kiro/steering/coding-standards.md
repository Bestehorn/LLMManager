---
inclusion: always
---

# Coding Standards (NO EXCEPTIONS)

1. **JSON Field Access**: Use string constants, not literals
   - BAD: `obj["content"]`
   - GOOD: `FIELD_CONTENT = "content"; obj[FIELD_CONTENT]`

2. **OOP Design**: Use abstractions and interfaces to avoid duplication
   - One class per file with matching filename
   - Inheritance visible from class/file names

3. **Modular Functions**: Break down into reusable library-style functions

4. **Relative Imports**: All imports within `src/` must be relative

5. **Logging**: Use `logging` library, minimal logging for success cases

6. **Named Parameters**: Always use named parameters at call sites
   - BAD: `f(5, "abc")`
   - GOOD: `f(a=5, b="abc")`

7. **Error Handling**: 
   - Throw exceptions for errors (not empty lists/zero values)
   - Return `None` for expected failures
   - Custom exceptions with `details=None` default

8. **Exception Hierarchy**: Group similar exceptions into classes inheriting from base

9. **Line Length**: Maximum 100 characters (project-specific)

10. **Type Hints**: Comprehensive type hints for all functions and methods
