# FastAPI Tests

This package contains tests for the FastAPI application located in `examples/fastapi_app`.

## Running Tests

To run these tests, make sure you have all the required dependencies installed:

```bash
pip install -r tests/fluvius_fastapi/requirements-test.txt
```

Then run the tests using pytest:

```bash
pytest tests/fluvius_fastapi
```

## Test Structure

The tests are organized as follows:

- `test_fastapi_app.py`: Tests for the core FastAPI application endpoints and functionalities
- `test_auth.py`: Tests for the authentication functionality
- `conftest.py`: Common fixtures used by tests

## Mocking

These tests make extensive use of mocking to isolate the FastAPI application from external dependencies:

1. Authentication is mocked to avoid real Keycloak connections
2. JWT verification is mocked
3. Domain contexts are mocked

This allows testing the API behavior without requiring a full environment setup.
