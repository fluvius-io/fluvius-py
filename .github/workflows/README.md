# GitHub Workflows for Fluvius

This directory contains GitHub Actions workflows for testing and building the Fluvius Python library.

## Available Workflows

### CI Workflow (`ci.yml`)

The main continuous integration workflow that runs on every push to the main branch and pull requests.

Features:
- Runs tests on multiple Python versions (3.9, 3.10, 3.11)
- Uses PostgreSQL service container for database tests
- Runs linting with ruff
- Performs type checking with mypy
- Runs all tests with pytest
- Builds package on successful tests (only for main branch)
- Uploads test reports as artifacts

To run manually:
1. Go to Actions → CI
2. Click "Run workflow"
3. Select the branch and click "Run workflow"

### Advanced Tests Workflow (`advanced-tests.yml`)

A more comprehensive testing workflow that runs weekly and can be triggered manually.

Features:
- Tests each module separately
- Runs performance tests with pyinstrument
- Uploads detailed test reports for each module
- Uploads performance profiles

To run manually:
1. Go to Actions → Advanced Tests
2. Click "Run workflow"
3. Select the branch and click "Run workflow"

## PostgreSQL Configuration

Both workflows use a PostgreSQL service container with the following configuration:
- **User**: fluvius_test
- **Password**: iyHu5WBQxiVXyLLJaYO0XJec
- **Database**: fluvius_test
- **Port**: 5432

## Dependencies Management

The workflows use [uv](https://github.com/astral-sh/uv) for Python package management, which provides faster installation times than pip.

## Artifacts

The following artifacts are generated and stored for 7 days:
- Test reports (HTML format)
- Performance profiles (HTML format)
- Built packages (wheel and sdist)