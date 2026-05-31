# ADR-0008: Elimination of .env Dependency and Hybrid AI Provider Strategy

- **Date**: 2026-05-31
- **Status**: Accepted
- **Deciders**: Gemini CLI (Agent)

## Context
As the application transitions to a standalone Windows executable (`.exe`) for end-users, relying on external `.env` files for critical configuration (like `OLLAMA_HOST` or API keys) is unsustainable. It breaks the "portable" nature of the app and poses security risks. Furthermore, users require the flexibility to choose between high-privacy local inference (Ollama) and high-performance cloud inference (Gemini API) without manual file editing.

## Decision
1. **Eliminate .env Dependency**:
   - The production `.exe` MUST NOT require a `.env` file to function.
   - All critical settings MUST have sensible defaults hardcoded within the application.
   - User-specific configuration MUST be managed by `ConfigManager` and persisted in standard system locations (`%APPDATA%`).
2. **Hybrid AI Provider Strategy**:
   - **Ollama (Local)**: Set as the default provider to ensure maximum privacy and offline capability out-of-the-box.
   - **Gemini API (Cloud)**: Provide an optional toggle in the Settings GUI. Enabling Gemini will require the user to provide an API key via the UI.
   - **Model Selection**: The GUI MUST allow users to select from available Ollama models or Gemini models.
3. **Standalone EXE Setup Optimization**:
   - The `SetupManager` MUST detect if it is running in a bundled environment (e.g., PyInstaller `sys.frozen`).
   - In a bundled environment, the manager MUST skip attempts to install Python dependencies via `pip` or `uv`, as these are already provided in the immutable bundle.
   - The setup process in production MUST focus exclusively on external prerequisites: ensuring Ollama is installed and the target AI model (`gemma4:e2b`) is pulled.
4. **Deferred Features**:
   - **Automated Model Selection (Local Smart)**: Logic for automatic model optimization based on hardware (VRAM/RAM) is deferred to prioritize core configuration and provider switching infrastructure.

## Consequences
### Positive
- **Improved UX**: "Double-click to run" experience for end-users without manual environment setup.
- **Security**: Reduces risk of leaking sensitive API keys via unencrypted `.env` files on disk (migrating to managed config).
- **Flexibility**: Empowers users to choose their preferred balance of privacy and performance.

### Negative / Risks
- Increased complexity in `ConfigManager` to handle default merging and UI-driven updates.
- Migration effort required to refactor existing `os.environ.get` calls throughout the codebase.

## References
- ADR-0006: Standard App Data Locations
- ADR-0007: Windows Executable Build and Distribution Strategy
