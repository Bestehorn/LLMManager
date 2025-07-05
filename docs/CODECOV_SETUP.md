# Codecov Integration Setup

This document describes how to set up Codecov integration for the LLMManager project.

## Overview

The GitHub Actions CI workflow includes optional Codecov integration for code coverage reporting. The integration is designed to work gracefully whether or not the Codecov token is available.

## Behavior

- **With CODECOV_TOKEN**: Coverage reports are uploaded to Codecov successfully
- **Without CODECOV_TOKEN**: CI continues to pass, coverage upload is skipped with a warning
- **For Forks**: Contributors don't need to set up Codecov tokens for their CI to work

## Setting Up Codecov Token (Repository Owners)

### 1. Get Codecov Token

1. Go to [codecov.io](https://codecov.io)
2. Sign up/log in with your GitHub account
3. Add your repository to Codecov
4. Copy the repository upload token

### 2. Add Token to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Name: `CODECOV_TOKEN`
5. Value: Paste your Codecov upload token
6. Click **"Add secret"**

### 3. Verify Setup

Once the token is added:
- Push changes or create a pull request
- Check the GitHub Actions workflow
- The "Upload coverage to Codecov" step should now succeed
- Coverage reports will be available on codecov.io

## Security Notes

- Never commit tokens to source code
- Tokens are encrypted in GitHub secrets
- Only repository maintainers can access/modify secrets
- The workflow uses `fail_ci_if_error: false` to ensure CI works without tokens

## Troubleshooting

### Upload Fails with "Token required"
- Verify the CODECOV_TOKEN secret is set correctly
- Check that the token hasn't expired
- Ensure the token is for the correct repository

### Coverage XML Not Found
- Verify tests are running successfully
- Check that coverage.xml is being generated
- Ensure the pytest coverage configuration is correct

## For Contributors

Contributors don't need to set up Codecov integration. The CI workflow will:
1. Run all tests successfully
2. Generate coverage reports locally
3. Skip Codecov upload with a harmless warning
4. Continue with the rest of the CI process

This ensures that all contributors can work on the project without additional setup requirements.
