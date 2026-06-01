# ADR-0009: Automatic Model Management and Lazy Loading

- **Date**: 2026-06-01
- **Status**: Accepted
- **Deciders**: ayato-labs, Gemini CLI

## Context
To adhere to the "Unified Smart EXE" (ADR-0005) strategy and avoid excessive binary bloat, AI model files (CAM++, VAD, etc.) must not be bundled within the installer. Initially, manual placement was considered, but this introduces unnecessary friction for the end-user and hinders automated maintenance.

## Decision
Implement a **ModelManager** service to handle automatic, lazy-loading of AI models.

1.  **Lazy Downloading**: Models MUST be downloaded on-demand (e.g., at first application launch or when the diarization feature is first triggered) rather than bundled.
2.  **Storage Standard**: Downloaded models MUST be stored in `%LOCALAPPDATA%/TransformMovieToText/models/` (ADR-0006).
3.  **Integrity Verification**: The `ModelManager` MUST verify the SHA-256 hash of downloaded files to ensure integrity and prevent corruption.
4.  **UI Feedback**: The application UI MUST indicate the downloading progress to the user, ensuring transparency and preventing a perceived "frozen" application state.
5.  **Versioning/Updates**: The `ModelManager` will check a remote JSON manifest for model updates, enabling seamless versioning without requiring a full application re-installation.

## Consequences

### Positive
- **Optimal EXE Size**: Keeps the application installer lightweight (< 100MB).
- **Seamless UX**: "Double-click to run" experience; the application self-configures its AI capabilities.
- **Maintainability**: Models can be updated independently of the core application binary.
- **Robustness**: SHA-256 validation prevents runtime crashes caused by corrupted model files.

### Negative / Risks
- **Network Dependency**: Requires the user to be online for the first-time setup. (Mitigation: Provide clear error messages if offline).
- **Implementation Complexity**: Requires building a robust downloader, hash-checker, and progress-tracking UI.

## References
- ADR-0005 (Unified Smart Executable)
- ADR-0006 (Standard App Data Locations)
