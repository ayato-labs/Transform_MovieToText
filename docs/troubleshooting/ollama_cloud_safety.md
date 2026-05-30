# Troubleshooting: Ollama Cloud Model Mixing

## Issue: Private Data Leakage Risk via Ollama Cloud Models

### Problem Description
Ollama introduced a "Cloud Models" feature that allows running large parameter models on Ollama's infrastructure. While Ollama is primarily a local LLM runner, its local API daemon (`localhost:11434`) can seamlessly proxy requests to these cloud-hosted models if the user has authenticated via `ollama signin`.

This creates a "Deceptive Locality" trap:
1. The application connects to `localhost`.
2. The user sees a model in the list.
3. The user selects the model.
4. **Data (meeting transcripts, private documents) is sent to external servers.**

This completely violates our **"100% Local & Privacy-First"** guarantee.

### Solution: 4-Layer Defense System
We have implemented a rigorous multi-layer defense in `src/llm/providers/ollama_client.py` to ensure only truly local models are ever used.

#### Layer 0: Loopback Enforcement
The client strictly validates its `base_url`. If any non-loopback address is detected, it is forcefully reset to `http://localhost:11434`.

#### Layer 1: Name-Based Filtering
All models returned by `ollama list` are scanned for cloud-related keywords. Any model containing the following is hidden from the UI:
- `:cloud`
- `remote`
- `hosted`
- `online`

#### Layer 2: Metadata Validation (`show` API)
For the remaining models, we call the Ollama `show` API to inspect their metadata. A truly local model must have disk-related traits (e.g., `parameter_size`, `quantization_level`). Models lacking these or having cloud indicators in their metadata are blocked.

#### Layer 3: Runtime Guard (Final Gate)
As a final safety measure, every inference call (`chat`, `generate`, etc.) performs a model name check immediately before sending the request. If a cloud model name is passed, a `CloudModelBlockedError` is raised, and **no network request is ever sent**.

### Verification
If you suspect cloud models are still appearing or want to verify the protection:
1. Run the specialized security test suite:
   ```bash
   uv run pytest tests/common/unit/llm/test_ollama_clients.py
   ```
2. Check the logs. Blocked models will trigger a `WARNING` or `CRITICAL` log entry:
   `SECURITY: Blocked cloud/remote model(s) from appearing in UI: [...]`

### Recommendation for Users
To be 100% certain, you can also set the following environment variable on your system to disable Ollama's cloud features entirely:
```bash
OLLAMA_REMOTES="!"
```
or create `~/.ollama/server.json`:
```json
{ "disable_ollama_cloud": true }
```
