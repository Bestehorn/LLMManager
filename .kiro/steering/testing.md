---
inclusion: fileMatch
fileMatchPattern: "test/**/*.py"
---

# Testing Standards

1. **Test Location**: 
   - Unit tests in `test/bestehorn_llmmanager/` (mirrors `src/` structure)
   - Integration tests in `test/integration/`

2. **Coverage Target**: 80% minimum, 100% for critical paths

3. **Test Structure**: 
   - Tests for `src/bestehorn_llmmanager/x.py` go in `test/bestehorn_llmmanager/test_x.py`
   - Use pytest fixtures for common setup
   - Use hypothesis for property-based testing

4. **Running Tests**: 
```bash
venv\Scripts\activate & pytest test/ --cov=bestehorn_llmmanager --cov-report=term-missing
```

5. **Test Markers**: Use appropriate markers for test categorization
   - `@pytest.mark.unit`: Unit tests
   - `@pytest.mark.integration`: Integration tests
   - `@pytest.mark.aws`: Tests requiring AWS access
   - `@pytest.mark.aws_integration`: Tests requiring real AWS Bedrock API
   - `@pytest.mark.slow`: Slow running tests
   - `@pytest.mark.network`: Tests requiring network access

6. **AWS Integration Tests**: 
   - May require AWS credentials
   - Use markers to skip in environments without AWS access
   - Consider cost implications (use cost markers)
