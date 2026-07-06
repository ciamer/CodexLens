# Contributing

Thanks for helping improve CodexLens.

## Development Setup

```powershell
python -m pip install -e .
python -m unittest discover -s tests
python -m compileall .
```

## Guidelines

- Keep API keys and private documents out of the repository.
- Prefer small, focused changes.
- Add or update tests for protocol, proxy, install, or parsing behavior.
- Keep README and `docs/` aligned with code changes.
- Use `CODEX_LENS_API_KEY` for this project, not provider-specific generic key names.

## Pull Requests

Before opening a PR, run:

```powershell
python -m unittest discover -s tests
python -m compileall .
```
