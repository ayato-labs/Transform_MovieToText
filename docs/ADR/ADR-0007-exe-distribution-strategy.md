# ADR-0007: Windows Executable Build and GitHub Release Distribution Strategy

- **Date**: 2026-05-31
- **Status**: Accepted
- **Deciders**: Gemini CLI (Agent)

## Context
Our application requires distribution to end-users on Windows systems. To ensure consistency, reproducibility, and security, we have automated the build and distribution process using GitHub Actions. Previously, configuration drift in the CI/CD pipeline led to issues where executable assets were not correctly attached to GitHub Releases. We need a formal record to define the architectural requirement that our distribution MUST include the produced `.exe` as a release asset.

## Decision
We will utilize GitHub Actions (`.github/workflows/desktop_distribution.yml`) to perform the following lifecycle for Windows distribution:
1. **Build**: Use `PyInstaller` (via `scripts/build_exe.py`) in a Windows-hosted runner to generate a standalone executable.
2. **Artifacting**: The build job MUST upload the resulting `.exe` file as a named GitHub Action artifact (e.g., `windows-exe`).
3. **Distribution**: The `distribute` job MUST download the `windows-exe` artifact and attach the `TransformMovieToText.exe` binary directly to the corresponding GitHub Release.

The file path for the release attachment MUST be explicitly verified as `windows-exe/dist/TransformMovieToText.exe` (or the actual path from the downloaded artifact structure).

## Consequences
### Positive
- Ensures end-users can download the latest verified binary directly from GitHub.
- Standardizes the release asset format, making it easier for users to identify and install.
- Provides a clear architectural reference to prevent future pipeline misconfigurations.

### Negative / Risks
- Increases dependency on GitHub Actions runners and storage.
- Requires maintenance of the `PyInstaller` build script to ensure compatibility with Windows security updates.

## References
- Issue: N/A
- PR: N/A
- ADR: ADR-0005 (Unified Smart Executable)
