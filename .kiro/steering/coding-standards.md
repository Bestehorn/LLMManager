---
inclusion: always
---

# Coding Standards (NO EXCEPTIONS)

1. **Type Safety & Constants**: 
   - Comprehensive type hints for all functions and methods
   - Use string constants for JSON field access, not literals
   - Example: `FIELD_CONTENT = "content"; obj[FIELD_CONTENT]`

2. **Clean Code Structure**:
   - One class per file with matching filename
   - Relative imports within `src/`
   - Named parameters at all call sites: `f(a=5, b="abc")`
   - Maximum 100 character line length

3. **Error Handling**:
   - Throw exceptions for errors (not empty lists/zero values)
   - Return `None` for expected failures
   - Custom exceptions with `details=None` default
   - Group similar exceptions into hierarchies

4. **Modular Design**:
   - Break down into reusable library-style functions
   - Use abstractions and interfaces to avoid duplication
   - Inheritance visible from class/file names

5. **Logging**: Use `logging` library, minimal logging for success cases
