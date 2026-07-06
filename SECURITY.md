# Security Policy

## Supported Versions

CodexLens is currently an early prototype. Security fixes target the latest version on the main branch.

## API Keys

Do not put API keys in source files, README files, issue comments, pull requests, screenshots, or Codex configuration files.

CodexLens reads the visual model API key from:

```text
CODEX_LENS_API_KEY
```

If a key is exposed, revoke or reset it in the provider console immediately, then set a new `CODEX_LENS_API_KEY`.

## Reporting a Vulnerability

Please do not open a public issue containing secrets, logs with secrets, or private document content.

If this repository is public, report vulnerabilities through GitHub private vulnerability reporting when enabled. Otherwise, contact the repository owner privately.

## Data Handling

CodexLens sends images to the configured vision model provider when image analysis is enabled. Users should avoid processing confidential documents unless their provider account and policy allow that use.
