# SnowScrape Backend Tests

This directory contains unit and integration tests for the SnowScrape backend.

## Test Structure

```
tests/
├── __init__.py
├── README.md
├── unit/                    # Unit tests for individual functions
│   ├── __init__.py
│   ├── test_crawler.py      # Tests for crawler.py functions
│   ├── test_job_manager.py  # Tests for job_manager.py functions
│   └── test_utils.py        # Tests for utils.py functions
└── integration/             # Integration tests for Lambda handlers
    ├── __init__.py
    └── test_handlers.py     # Tests for handler.py Lambda functions
```

## Setup

### Install Dependencies

Install test dependencies from requirements.txt:

```bash
pip install -r requirements.txt
```

This will install:
- pytest - Testing framework
- pytest-cov - Coverage reporting
- pytest-mock - Mocking utilities
- pytest-env - Environment variable management
- moto - AWS service mocking
- responses - HTTP request mocking

### Environment Variables

Test environment variables are configured in `pytest.ini`. The tests use separate DynamoDB tables, S3 buckets, and SQS queues with "-test" suffixes to avoid conflicts with production resources.

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Only Unit Tests

```bash
pytest tests/unit/
```

### Run Only Integration Tests

```bash
pytest tests/integration/
```

### Run Tests by Marker

Run only AWS-related tests:
```bash
pytest -m aws
```

Run only slow tests:
```bash
pytest -m slow
```

Skip slow tests:
```bash
pytest -m "not slow"
```

### Run Tests with Coverage

```bash
pytest --cov=. --cov-report=html --cov-report=term
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run Specific Test File

```bash
pytest tests/unit/test_crawler.py
```

### Run Specific Test Function

```bash
pytest tests/unit/test_crawler.py::TestExecuteQuery::test_xpath_query_single_result
```

### Verbose Output

```bash
pytest -v
```

### Show Print Statements

```bash
pytest -s
```

## Test Markers

Tests are organized with the following markers:

- `@pytest.mark.unit` - Unit tests for individual functions
- `@pytest.mark.integration` - Integration tests for Lambda handlers
- `@pytest.mark.aws` - Tests that use AWS service mocks (DynamoDB, S3, SQS)
- `@pytest.mark.slow` - Tests that take longer to run (e.g., HTTP requests)

## Fixtures

Common test fixtures are defined in `conftest.py`:

- `aws_credentials` - Mock AWS credentials for moto
- `mock_env_vars` - Mock environment variables
- `dynamodb_client` - Mocked DynamoDB client with test tables
- `s3_client` - Mocked S3 client with test bucket
- `sqs_client` - Mocked SQS client with test queue
- `sample_job_data` - Sample job data for testing
- `sample_url_data` - Sample URL data for testing
- `sample_html_content` - Sample HTML content for query testing
- `sample_json_content` - Sample JSON content for query testing
- `lambda_context` - Mock Lambda context object

## Writing New Tests

### Unit Test Example

```python
import pytest
from my_module import my_function

class TestMyFunction:
    """Unit tests for my_function."""

    def test_basic_functionality(self):
        """Test basic function behavior."""
        result = my_function("input")
        assert result == "expected output"

    def test_edge_case(self):
        """Test edge case handling."""
        with pytest.raises(ValueError):
            my_function(None)
```

### Integration Test Example

```python
import pytest
from moto import mock_aws

@pytest.mark.integration
@pytest.mark.aws
class TestMyHandler:
    """Integration tests for my_handler."""

    @mock_aws
    def test_handler_success(self, dynamodb_client, mock_env_vars, lambda_context):
        """Test successful handler execution."""
        from handler import my_handler

        event = {
            'headers': {'Authorization': 'Bearer test-token'},
            'body': '{"key": "value"}'
        }

        response = my_handler(event, lambda_context)

        assert response['statusCode'] == 200
```

## Test Coverage Goals

- Unit tests should cover critical business logic functions
- Integration tests should cover all Lambda handler endpoints
- Aim for >80% code coverage overall
- All edge cases and error conditions should be tested

## Continuous Integration

Tests should be run automatically in CI/CD pipelines before deployment:

```bash
# Run tests with coverage check
pytest --cov=. --cov-report=term --cov-fail-under=80
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure you're running pytest from the backend directory:

```bash
cd backend
pytest
```

### AWS Service Mocking Issues

If moto mocks aren't working properly:
1. Ensure moto is installed: `pip install moto[all]>=5.0.24`
2. Check that `@mock_aws` decorator is applied
3. Verify environment variables are set correctly

### Test Isolation Issues

If tests are interfering with each other:
1. Use `scope='function'` in fixtures to ensure fresh instances
2. Clear any global state in teardown methods
3. Use separate test table/bucket names for each test

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [moto documentation](http://docs.getmoto.org/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)
