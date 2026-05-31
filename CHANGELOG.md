# [2.46.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.45.0...v2.46.0) (2026-05-31)


### Features

* implement secure local LLM architecture with Ollama and Gemini clients, intent routing, and configuration management ([d2f6da0](https://github.com/ayato-labs/Transform_MovieToText/commit/d2f6da0e4d55a201fa2c4f0387f0a454f5154ebe))

# [2.45.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.44.0...v2.45.0) (2026-05-31)


### Features

* implement settings UI with provider configuration, resource management, and legacy data migration utilities. ([2716dbb](https://github.com/ayato-labs/Transform_MovieToText/commit/2716dbbcbc28eeebcc012987fc2fb0c794dd0c26))

# [2.44.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.43.0...v2.44.0) (2026-05-31)


### Features

* implement WhisperTranscriber with robust GPU/CPU fallback and add soundcard recorder for desktop platforms ([9f7ab8b](https://github.com/ayato-labs/Transform_MovieToText/commit/9f7ab8be47708d617aa266778c7d6e0826aab3ce))

# [2.43.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.42.0...v2.43.0) (2026-05-31)


### Features

* implement robust WhisperTranscriber with cross-platform GPU/CPU fallback and managed memory unloading ([cd3df1d](https://github.com/ayato-labs/Transform_MovieToText/commit/cd3df1dcb690f6f1374e03771d691644b2240c46))
* implement WhisperTranscriber with automated CUDA-to-CPU fallback and memory management ([b0cd537](https://github.com/ayato-labs/Transform_MovieToText/commit/b0cd5373e7d42bc7d9e018f4f8e8095e5bd43f91))

# [2.42.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.41.0...v2.42.0) (2026-05-31)


### Features

* add system audio capture via WASAPI and implement core transcription services ([8dfbfdc](https://github.com/ayato-labs/Transform_MovieToText/commit/8dfbfdc1f5ad8747b2553555b553840e57db07ba))

# [2.41.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.40.0...v2.41.0) (2026-05-31)


### Features

* implement platform directory management and automated background environment setup ([08f67a9](https://github.com/ayato-labs/Transform_MovieToText/commit/08f67a9a9cc31ffa17e29877779ebea4281ea175))

# [2.40.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.39.1...v2.40.0) (2026-05-31)


### Features

* add system resource advisor, Ollama setup utilities, and improve launch.bat process automation ([bfa24a6](https://github.com/ayato-labs/Transform_MovieToText/commit/bfa24a678960935ab50f4f8b2706e819401f2d63))

## [2.39.1](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.39.0...v2.39.1) (2026-05-31)


### Bug Fixes

* robust tag resolution for release distribution ([f67e835](https://github.com/ayato-labs/Transform_MovieToText/commit/f67e835954cb43ed5dbe75b2bfe7f6997e6d6584))

# [2.39.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.38.0...v2.39.0) (2026-05-31)


### Features

* add Gemini API support, implement UI settings management, and introduce dynamic configuration handling ([624e87a](https://github.com/ayato-labs/Transform_MovieToText/commit/624e87af46b407d9121bf3d84880a2fca33909a6))

# [2.38.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.37.0...v2.38.0) (2026-05-31)


### Features

* implement automated environment setup manager and dependency helper with background installation support ([a26c42a](https://github.com/ayato-labs/Transform_MovieToText/commit/a26c42a5bd7bd2d111813b87bc8c5c04a38b9bf8))
* implement structured logging system with Loguru, system diagnostics, and UI buffer support ([5bc6575](https://github.com/ayato-labs/Transform_MovieToText/commit/5bc6575612e285185ee3fd15e52a1929206f6b3b))

# [2.37.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.36.0...v2.37.0) (2026-05-31)


### Features

* add automated CI/CD pipeline for linting, testing, building, and release distribution ([3a8a97d](https://github.com/ayato-labs/Transform_MovieToText/commit/3a8a97d0f5eae438f78b0c2ba049026fb0e76635))

# [2.36.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.35.2...v2.36.0) (2026-05-31)


### Features

* implement ModelManager for VRAM orchestration and replace soundcard recorder with PyAudio WASAPI loopback implementation ([86539e9](https://github.com/ayato-labs/Transform_MovieToText/commit/86539e9fd976af71de48886c00bc29459c034b9f))

## [2.35.2](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.35.1...v2.35.2) (2026-05-31)


### Bug Fixes

* logger initialization for windowed exe ([dd3e029](https://github.com/ayato-labs/Transform_MovieToText/commit/dd3e02950c06864f039d3e02ddb350a0377d5807))

## [2.35.1](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.35.0...v2.35.1) (2026-05-31)


### Bug Fixes

* correct gh cli compatibility ([86dc404](https://github.com/ayato-labs/Transform_MovieToText/commit/86dc404ba84be4ab3b84abcdc4330ee01406ba64))

# [2.35.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.34.0...v2.35.0) (2026-05-31)


### Features

* add CI pipeline for automated testing, semantic versioning, and Windows executable distribution ([dc77421](https://github.com/ayato-labs/Transform_MovieToText/commit/dc77421e3ae8d3a893d45efd600cff90ce423bfa))

# [2.34.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.33.0...v2.34.0) (2026-05-31)


### Features

* implement automated CI/CD pipeline for Windows executable distribution and document strategy in ADR-0007 ([b14e83b](https://github.com/ayato-labs/Transform_MovieToText/commit/b14e83b9afcf4fb5209467a3b52cc73f14631f6a))

# [2.33.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.32.0...v2.33.0) (2026-05-31)


### Features

* implement VRAM model manager and WASAPI loopback audio recorder ([26b69f3](https://github.com/ayato-labs/Transform_MovieToText/commit/26b69f3d5e7d51adfed85efcb0dd382994f45225))

# [2.32.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.31.0...v2.32.0) (2026-05-31)


### Features

* implement MinutesService with map-reduce support and add extensive core infrastructure and unit tests ([56c87e2](https://github.com/ayato-labs/Transform_MovieToText/commit/56c87e2dd488672b6070b70d4a78f782ddce6a21))

# [2.31.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.30.0...v2.31.0) (2026-05-31)


### Features

* implement transcription service and logger utility with updated project dependencies ([de71f5d](https://github.com/ayato-labs/Transform_MovieToText/commit/de71f5df47f40619907e92d7d4090612835a15f5))

# [2.30.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.29.0...v2.30.0) (2026-05-31)


### Features

* standardize data storage in Windows AppData and implement auto-migration ([32a03c1](https://github.com/ayato-labs/Transform_MovieToText/commit/32a03c12b729fb838baffd8aa885e1df2a4d0582))

# [2.29.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.28.0...v2.29.0) (2026-05-31)


### Features

* unify CPU and GPU builds into a single Smart Executable ([a75647f](https://github.com/ayato-labs/Transform_MovieToText/commit/a75647f7cc85b50ea00bec5e09eb636a5e6f9fba))

# [2.28.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.27.3...v2.28.0) (2026-05-31)


### Bug Fixes

* add timeouts to all nvidia-smi calls to prevent test/build hanging ([f33d5d4](https://github.com/ayato-labs/Transform_MovieToText/commit/f33d5d4479fc6d64b4a1b929570c906623e4f56a))


### Features

* completely decouple pytorch and replace with scipy to dramatically reduce footprint ([e36e596](https://github.com/ayato-labs/Transform_MovieToText/commit/e36e5964dfc9277f8ef57e8e7c5933179de0da2e))

## [2.27.3](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.27.2...v2.27.3) (2026-05-31)


### Bug Fixes

* **ci:** use cycjimmy/semantic-release-action to properly export release tag for artifact attachment ([ea35dd3](https://github.com/ayato-labs/Transform_MovieToText/commit/ea35dd3070d58c6b19f4edf07f5ec6f106c361ad))

## [2.27.2](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.27.1...v2.27.2) (2026-05-31)


### Bug Fixes

* **license:** replace pyautogui with PIL.ImageGrab to purge GPLv3 dependencies ([917f410](https://github.com/ayato-labs/Transform_MovieToText/commit/917f4108e29332c108fb6bdbe6bc8715ffc6bbd7))

## [2.27.1](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.27.0...v2.27.1) (2026-05-31)


### Bug Fixes

* aggressively pre-clean venv to ensure --onefile .exe assets stay under 2GB release limit ([c82b073](https://github.com/ayato-labs/Transform_MovieToText/commit/c82b073d6dc605611b801e10ebc88f7ddc460d90))

# [2.27.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.26.0...v2.27.0) (2026-05-31)


### Features

* provide direct .exe assets using pyinstaller --onefile ([c614f29](https://github.com/ayato-labs/Transform_MovieToText/commit/c614f29aee27efb494530d706c036d54f50318f0))

# [2.26.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.25.0...v2.26.0) (2026-05-31)


### Features

* use 7zip with volume splitting for release assets ([280f586](https://github.com/ayato-labs/Transform_MovieToText/commit/280f5864b701d0665752d1d5117dc01bd787bd72))

# [2.25.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.24.0...v2.25.0) (2026-05-31)


### Features

* optimize build size and formalize pytorch decoupling plan ([85408f7](https://github.com/ayato-labs/Transform_MovieToText/commit/85408f7fe46f7a97d6254b6f181547cf691e0d89))

# [2.24.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.23.0...v2.24.0) (2026-05-31)


### Bug Fixes

* optimize build size for 2GB limit and fix CI blocking issues ([2cfb942](https://github.com/ayato-labs/Transform_MovieToText/commit/2cfb9422c6463cef46b2ff9a25bff86aeea5b78c))


### Features

* unify pipeline to Lint -> Test -> Release -> Build ([3bb531f](https://github.com/ayato-labs/Transform_MovieToText/commit/3bb531f06a53ef34037d843649b02e98256df213))

# [2.23.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.22.0...v2.23.0) (2026-05-30)


### Features

* focus CI/CD on Windows and remove macOS/Linux jobs ([59b0d4e](https://github.com/ayato-labs/Transform_MovieToText/commit/59b0d4e1301bf9a5984ccdfeddb1fc44abaeb7eb))

# [2.22.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.21.0...v2.22.0) (2026-05-30)


### Features

* consolidate release and distribution into a single pipeline and fix exe paths ([8f83ff3](https://github.com/ayato-labs/Transform_MovieToText/commit/8f83ff38fb44c07f640f2494e1d42aa661a98afd))

# [2.21.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.20.0...v2.21.0) (2026-05-30)


### Features

* add PyInstaller spec file for GPU-enabled executable build ([210e307](https://github.com/ayato-labs/Transform_MovieToText/commit/210e3075fafda4e42a17217a3acb9509010c87a4))
* automate windows exe build pipeline (cpu/gpu) ([5c0d04e](https://github.com/ayato-labs/Transform_MovieToText/commit/5c0d04e33d4cce61cd07f9e11c667605854daa4e))
* implement automated multi-target build system and add meeting history controller for metadata management ([1cd014d](https://github.com/ayato-labs/Transform_MovieToText/commit/1cd014d291bdfda2990358cb0c7cefed65b037a8))

# [2.20.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.19.0...v2.20.0) (2026-05-30)


### Features

* add GitHub Actions workflow for cross-platform desktop distribution and release automation ([de6259f](https://github.com/ayato-labs/Transform_MovieToText/commit/de6259f15763c64d6544355417987f5ecc46b1bb))
* implement secure local Ollama client with cloud-blocking, resource-based model advising, and comprehensive core services. ([cd49c58](https://github.com/ayato-labs/Transform_MovieToText/commit/cd49c581a33f659c0c97db2218f557d6b7da19c1))

# [2.19.0](https://github.com/ayato-labs/Transform_MovieToText/compare/v2.18.0...v2.19.0) (2026-05-23)


### Bug Fixes

* automatic title generation, test isolation, and UI race conditions ([4bfd43b](https://github.com/ayato-labs/Transform_MovieToText/commit/4bfd43b1e222a9e67c20bc4cd75b51717e301c0e))
* **core:** add missing os import in setup_helper.py ([b4db5ff](https://github.com/ayato-labs/Transform_MovieToText/commit/b4db5ff5c578d6ab48171ba3edf55ac3fca55e26))
* **core:** prevent STATUS_STACK_BUFFER_OVERRUN crash during whisper unload on Windows ([770d35d](https://github.com/ayato-labs/Transform_MovieToText/commit/770d35d9fe7a8f321508debc7f5a73da33d258a8))
* **ui,llm:** handle Flet dialog/button deprecations and improve Ollama error messages ([633706c](https://github.com/ayato-labs/Transform_MovieToText/commit/633706cbd25ad295dc8dd5decab4a61dd304181f))
* **ui:** ensure smart_helper is initialized before initial_load thread in FileTranscriptionView ([2565493](https://github.com/ayato-labs/Transform_MovieToText/commit/2565493b4265a61db2dfc67adde1c6db41c37827))
* **ui:** handle None UI components in LocalSmartController and ensure OLLAMA_HOST is set ([f2c39ee](https://github.com/ayato-labs/Transform_MovieToText/commit/f2c39ee8002394a1baa54cc2cc2e6eb87c27afc5))


### Features

* add progress updates to Map-Reduce and integrate with controller ([ca829a8](https://github.com/ayato-labs/Transform_MovieToText/commit/ca829a842ec387e5410a4542bc4386f1d06491bd))
* implement AI model lifecycle management (view/delete local models) ([22c01f5](https://github.com/ayato-labs/Transform_MovieToText/commit/22c01f5200a6d0bca3ceddf1880ad1e4082ef3af))
* implement Map-Reduce summarization for long transcripts ([f502e21](https://github.com/ayato-labs/Transform_MovieToText/commit/f502e2109621ca3abcc01ac766d1467716c2dda5))
* implement security hardening (Zero-Trust Local API) ([7dfa066](https://github.com/ayato-labs/Transform_MovieToText/commit/7dfa0669dfe8f51d1a0d5078bf703886cfc9d4e4))
* implement setup progress visualization with streaming Ollama pull ([c4a1e11](https://github.com/ayato-labs/Transform_MovieToText/commit/c4a1e11b3bcaf0631584a18e0489258b26b43601))
* **ui:** add Local Smart automatic setup to live transcription view ([d72ab92](https://github.com/ayato-labs/Transform_MovieToText/commit/d72ab92f8ec45bfeb8ed8f5f854ab549b70045d0))

# [2.18.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.17.0...v2.18.0) (2026-04-16)


### Features

* implement KnowledgeScanner for local document indexing and add history management controller and UI views ([9d6b53b](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/9d6b53bc51e887de9d87589ebb9f1b88178e882d))

# [2.17.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.16.0...v2.17.0) (2026-04-15)


### Features

* implement local knowledge base scanner and secure Ollama client with cloud model filtering ([544ff88](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/544ff88dbc9098a8982254fad676894f91f40acb))
* implement meeting history management with FTS5 search, project filtering, and ROI dashboard integration ([f94b10b](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/f94b10b7a185a7b1b7d61750b6b70459e1465a35))

# [2.16.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.15.0...v2.16.0) (2026-04-15)


### Features

* implement QueryAnalyzer for metadata extraction and add ChatBotView UI for RAG-powered queries ([a568ee1](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/a568ee181dc41a862ee759e349d1dd8b5e7b9267))
* implement RAG-powered ChatBotView and add documentation directory to gitignore ([af502ee](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/af502ee1648622ae5fe904bf56b9a9c108b608cc))
* implement RAG-powered ChatBotView with debounced input and local smart integration utilities ([3a7d921](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/3a7d921c6b2b4863198853e248648d2d7a296bbf))
* implement settings view and core configuration management for project and LLM provider settings ([a459c2f](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/a459c2fbd298c567a5cffb450fa86db43977f0ea))

# [2.15.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.14.0...v2.15.0) (2026-04-11)


### Bug Fixes

* **core:** finalize error handling and remove emojis to comply with user rules ([cbe5834](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/cbe58349a130353a759be44aa0c2d36c241f864c))
* **core:** resolve AttributeError in whisper_transcriber and update ui_utils tests ([3ac13f4](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/3ac13f490fcc9d94bb0bf4760b6529674b2b373f))


### Features

* implement core architecture, desktop UI components, and comprehensive test suite for transcription service ([15c8d5c](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/15c8d5c6f368f6826f4ba5c07a024bff553567b2))
* implement edition-based restrictions and migrate to AGPL-3.0 license ([5cddf4d](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/5cddf4d31b78ef7420a8abd31815b4f4fd654671))

# [2.14.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.13.2...v2.14.0) (2026-04-05)


### Features

* unify android native and apk build pipelines ([57084e7](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/57084e7bdc0d86b33e1dc7c5fec7d550429cc123))

## [2.13.2](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.13.1...v2.13.2) (2026-04-05)


### Bug Fixes

* robustly find libwhisper.so in build output ([8971eed](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/8971eeda7a3988dae460e3f08c5a7880c6793b11))

## [2.13.1](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.13.0...v2.13.1) (2026-04-05)


### Bug Fixes

* use nttld/setup-ndk in android build workflow ([82f5ff2](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/82f5ff27024d41b40eb34d9ee29a8173fdaededf))

# [2.13.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.12.0...v2.13.0) (2026-04-05)


### Features

* implement android native edge transcription and mobile ui optimization ([6b438e9](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/6b438e94caf4639ece80bb69ac1de60832cc1c99))

# [2.12.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.11.8...v2.12.0) (2026-04-04)


### Features

* **android:** add log copy button to critical error screen ([db6fd7f](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/db6fd7ff336ba2b19a965aba0c9740a9fe31b6cc))
* **android:** enhance debug capabilities with file logging, boot status UI, and library guards ([e4b666a](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/e4b666aea360f10a025b124f4c3044f03f374f7a))

## [2.11.8](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.11.7...v2.11.8) (2026-04-04)


### Bug Fixes

* **ui:** resolve TypeError in Dropdown initialization by moving on_change to property assignment ([8b57f14](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/8b57f1421f798784d315269a6828bd0970c2e650))

## [2.11.7](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.11.6...v2.11.7) (2026-04-04)


### Bug Fixes

* **ui:** remove direct assignment to self.page in ChatBotView to avoid AttributeError ([9d78c63](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/9d78c632136a3978eaa42786b16d27c42f91b9f2))

## [2.11.6](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.11.5...v2.11.6) (2026-04-04)


### Bug Fixes

* **ci:** add missing dependencies (Pillow, numpy) and include [pc] extras in CI install ([060761c](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/060761cc7a4b874cf1079cec5b07a8c341b44ead))

## [2.11.5](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.11.4...v2.11.5) (2026-04-04)


### Bug Fixes

* **assets:** replace invalid icon.png with a valid high-quality PNG to fix Android build ([d396d28](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/d396d2846a3e1c7069355a6873fe7f978aacd22a))

## [2.11.4](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.11.3...v2.11.4) (2026-04-04)


### Bug Fixes

* **ci:** resolve watchdog dependency issue by separating desktop dependencies ([5e78619](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/5e7861911c8f5a5d8d412f9374b83dd9a17e4a83))

## [2.11.3](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.11.2...v2.11.3) (2026-04-04)


### Bug Fixes

* **ci:** remove deprecated libgconf-2-4 dependency ([785800f](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/785800faab1e83ea57a5793bb572c34d7f3c6323))

## [2.11.2](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.11.1...v2.11.2) (2026-04-04)


### Bug Fixes

* **ci:** fix Flutter version detection by using explicit flutter-version ([6542164](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/65421641b70bbfbcb516c82770f3aac73e75b5a2))

## [2.11.1](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.11.0...v2.11.1) (2026-04-04)


### Bug Fixes

* **ci:** stabilize Android build pipeline ([5f10a78](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/5f10a7827b2e0ae0b4ac8c4b9b6a6fc81e34b4e5))

# [2.11.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.10.0...v2.11.0) (2026-04-04)


### Features

* setup android build via github actions ([3c3e5cb](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/3c3e5cb3968e230c73b525e48ab40184310d9bc6))

# [2.10.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.9.0...v2.10.0) (2026-03-31)


### Bug Fixes

* resolve CI linting errors and merge conflicts to stabilize codebase ([589841b](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/589841b20ba9244463931fc178957e7fc921ea28))
* resolve residual merge conflicts and stabilize main branch ([033023f](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/033023f1940534381e746007bd4ce99448e2dd94))
* restore CI stability and resolve merge conflicts in main ([c5f865f](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/c5f865fdab54178c1feead2933d382fd88bc8984))


### Features

* migrate to Gemma 3 and stabilize transcription pipeline ([3a71ff7](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/3a71ff7e104d7c79055eb8e3e573f99579c67d23))

# [2.10.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.9.0...v2.10.0) (2026-03-31)


### Bug Fixes

* resolve CI linting errors and merge conflicts to stabilize codebase ([589841b](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/589841b20ba9244463931fc178957e7fc921ea28))
* resolve residual merge conflicts and stabilize main branch ([033023f](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/033023f1940534381e746007bd4ce99448e2dd94))
* restore CI stability and resolve merge conflicts in main ([c5f865f](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/c5f865fdab54178c1feead2933d382fd88bc8984))


### Features

* migrate to Gemma 3 and stabilize transcription pipeline ([3a71ff7](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/3a71ff7e104d7c79055eb8e3e573f99579c67d23))

# [2.9.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.8.0...v2.9.0) (2026-03-31)


### Features

<<<<<<< HEAD
* migrate to Gemma 3 and stabilize transcription pipeline ([3a71ff7](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/3a71ff7e104d7c79055eb8e3e573f99579c67d23))
=======
* migrate to Gemma 3 and stabilize transcription pipeline ([3aa7723](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/3aa7723cdc869aff2f4bbbd86b4aa08e579fd843))
>>>>>>> fix/cleanup-final

# [2.8.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.7.1...v2.8.0) (2026-03-30)


### Features

* **rag:** archive embedding logic and harden metadata-aware RAG search ([048f1a2](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/048f1a23c8116e59ae8fec220fa77f9e3ecf1e19))

## [2.7.1](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.7.0...v2.7.1) (2026-03-30)


### Bug Fixes

* resolve ruff linting errors in src and tests for CI compliance ([555c8a3](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/555c8a3b5b421ebd65f175596c86d95b3f27049a))

# [2.7.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.6.0...v2.7.0) (2026-03-30)


### Bug Fixes

* harden desktop distribution build by adding flet.yaml and explicit Flutter paths ([1843557](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/1843557e9d01c4335346162b19d3c0582ce141d7))


### Features

* migrate to hybrid 'Thin Client' distribution model with auto-setup wizard ([509f0ad](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/509f0adaed07a2f6ebddeeb7b030edf4da5ebf5e))

# [2.6.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.5.7...v2.6.0) (2026-03-29)


### Features

* upgrade desktop distribution to standalone flet build for Windows/macOS ([2aa03ef](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/2aa03efdc8a01944c1868d2b7f9938162fe89498))

## [2.5.7](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.5.6...v2.5.7) (2026-03-29)


### Bug Fixes

* update WhisperTranscriber import path in benchmark script ([3c1b70d](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/3c1b70d50bec042f08895fa05765ad494d027f7c))

## [2.5.6](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.5.5...v2.5.6) (2026-03-29)


### Bug Fixes

* pin flet to <0.80.0 to prevent Tab/ElevatedButton API breakage ([6906111](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/6906111d1ae4eca68e6a026fd94f93ffc8ec446f))

## [2.5.5](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.5.4...v2.5.5) (2026-03-29)


### Bug Fixes

* resolve FilePicker TypeError by assigning on_result as attribute ([ad036e6](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/ad036e6002fb2398007b77e761eaf4ceaebcd253))

## [2.5.4](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.5.3...v2.5.4) (2026-03-29)


### Bug Fixes

* resolve ruff E402 by adding noqa: E402 ([e14adb7](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/e14adb7d3b73341c7ee04f17f0f2bf3e5377230a))

## [2.5.3](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.5.2...v2.5.3) (2026-03-29)


### Bug Fixes

* remaining Flet 0.21+ compatibility issues in HistoryView and TranscriptionView ([2d54e4f](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/2d54e4f1a5f77ceeaddd62a8a583eb02d708215c))

## [2.5.2](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.5.1...v2.5.2) (2026-03-29)


### Bug Fixes

* CI tests recovery (Flet API, mock paths, assertions) ([2d0541c](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/2d0541c55f3e5fb82ce0c556d618f99f7f863977))

## [2.5.1](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.5.0...v2.5.1) (2026-03-29)


### Bug Fixes

* resolve CI test collection errors (import paths and encoding) ([45cecfd](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/45cecfda489427879f83d5247e99dd5bac5674f1))

# [2.5.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.4.1...v2.5.0) (2026-03-29)


### Features

* enhance history cockpit and harden codebase ([3c77cef](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/3c77cef1e7b93b45fd3cec2e44b31e7eba493f07))

## [2.4.1](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.4.0...v2.4.1) (2026-03-28)


### Bug Fixes

* remove unused imports in transcription_view.py ([d0cf5ae](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/d0cf5ae08e22642e965f0b2542d221b5fcceaa9e))

# [2.4.0](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/compare/v2.3.0...v2.4.0) (2026-03-28)


### Bug Fixes

* **ci:** explicitly include semantic-release plugins in npx call ([4354ed9](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/4354ed97955f78dcf02b0493295c4439eb8a9b01))
* **ci:** install semantic-release and all plugins via npm before running ([3461326](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/3461326629450f67871af66918676ce5f8799578))


### Features

* integrate python-semantic-release for automated versioning and changelogs ([967241e](https://github.com/Ayato-AI-for-Auto/Transform_MovieToText/commit/967241e01d638081ed2063968a81473949cbf41f))
