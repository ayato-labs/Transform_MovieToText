# ADR-0013: Fix setup manager hang in bundled exe

- **Date**: 2026-06-14
- **Status**: Accepted
- **Deciders**: Gemini CLI

## Context
In the bundled executable (`.exe`) environment, the `SetupManager` was attempting to run `pip install` commands even when no dependencies were missing. Since `sys.executable` points to the application itself in a bundled environment, this resulted in the application recursively invoking itself with `pip` arguments, causing a hang/infinite loop during the startup setup phase.

## Decision
We implemented a conditional check to ensure Python dependency installation (via `pip` or `uv`) only executes if there are actual missing dependencies (`if missing_deps:`).

## Consequences
### Positive
- Prevents infinite recursion/hangs on application startup in packaged environments.
- Improves startup reliability for end-users.
### Negative / Risks
- Minimal; ensures that bundled dependencies are not unnecessarily checked or "re-installed" by the application process.

## References
- Issue: #N/A
- PR: N/A
