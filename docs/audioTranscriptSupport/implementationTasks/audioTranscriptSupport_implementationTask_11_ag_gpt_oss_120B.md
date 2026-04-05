# Implementation Task List for `audioTranscriptSupport`

## Summary Table

| Task ID | Description | Status |
|---------|-------------|--------|
| 1 | Add `audio_transcription` tier to `LLMConfigurations` with defaults and env vars | PENDING |
| 2 | Create `AudioTranscriptionProviderSettings` class inheriting from `BaseModelProviderSettings` | PENDING |
| 3 | Modify `AudioTranscriptionProviderConfig` to extend `BaseModelProviderConfig` and include provider settings | PENDING |
| 4 | Update `ConfigTier` enum to include `"audio_transcription"` | PENDING |
| 5 | Extend `resolve_model_config` to return `AudioTranscriptionProviderConfig` for the new tier | PENDING |
| 6 | Add `audio_transcription` entry to `global_configurations.token_menu` with pricing `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}` | PENDING |
| 7 | Implement Callback Injection pattern in provider creation (token tracking) | PENDING |
| 8 | Refactor `get_configuration_schema` to include the new tier (hard‑coded list update) | PENDING |
| 9 | Move `AudioTranscriptionProcessor` to `media_processors/audio_transcription_processor.py` and delete stub | PENDING |
| 10 | Expand `DEFAULT_POOL_DEFINITIONS` to route additional audio MIME types to the new processor | PENDING |
| 11 | Implement `AudioTranscriptionProcessor.process_media` to call `provider.transcribe_audio` with feature name `"audio_transcription"` | PENDING |
| 12 | Implement full async Soniox transcription flow (upload, create, wait, get transcript) with token tracking and robust cleanup via background tasks | PENDING |
| 13 | Add comprehensive error handling in `AudioTranscriptionProcessor.process_media` (return `ProcessingResult` with `unprocessable_media=True` on failure) | PENDING |
| 14 | Update `ImageVisionProcessor` error paths to set `unprocessable_media=True` | PENDING |
| 15 | Change `ImageVisionProcessor` token tracking calls to use feature names `"image_moderation"` and `"image_transcription"` | PENDING |
| 16 | Update `CorruptMediaProcessor` and `UnsupportedMediaProcessor` to return `ProcessingResult` with `unprocessable_media=True` | PENDING |
| 17 | Modify `BaseMediaProcessor.process_job` timeout handling to set `unprocessable_media=True` | PENDING |
| 18 | Adjust `BaseMediaProcessor._handle_unhandled_exception` to pass `unprocessable_media=True` and `mime_type` to `format_processing_result` | PENDING |
| 19 | Refactor `format_processing_result` signature to require `mime_type: str` and optional `display_media_type: str` | PENDING |
| 20 | Update all call sites of `format_processing_result` to provide the new arguments | PENDING |
| 21 | Add `display_media_type` attribute to `ProcessingResult` dataclass | PENDING |
| 22 | Add a no‑op `initialize` method to `BaseModelProvider` (non‑abstract) | PENDING |
| 23 | Extend `model_factory.create_model_provider` to handle `AudioTranscriptionProvider`, import it, inject token tracker, and `await provider.initialize()` | PENDING |
| 24 | Implement `SonioxAudioTranscriptionProvider` with async `transcribe_audio` and background cleanup tasks | PENDING |
| 25 | Add `soniox` package to `requirements.txt` | PENDING |
| 26 | Create migration script `scripts/audioTranscriptionUpgradeScript.py` to update DB configs and token menu for the new tier | PENDING |
| 27 | Extend `DefaultConfigurations` in `config_models.py` with audio transcription defaults | PENDING |
| 28 | Update `get_bot_defaults` in `routers/bot_management.py` to include the new tier | PENDING |
| 29 | Define `LLMConfigurations.audio_transcription` as a required field (Pydantic `Field(...)`) | PENDING |
| 30 | Update `media_processors/factory.py` import to point to the new processor module | PENDING |
| 31 | Ensure `SONIOX_API_KEY` environment variable is provisioned in deployment environments | PENDING |
| 32 | Add `"audio_transcription"` to `ConfigTier` Literal type in `config_models.py` | PENDING |
| 33 | Update `services/resolver.py` to map the new tier via a registry dictionary and raise on unknown tiers | PENDING |
| 34 | Append `"audio_transcription"` to hard‑coded tier fallback list in `routers/bot_management.py` | PENDING |
| 35 | Add UI entry for `audio_transcription` in `frontend/src/pages/EditPage.js` (uiSchema) | PENDING |
| 36 | Update validation arrays in `EditPage.js` to include the new tier and add explanatory comments | PENDING |
| 37 | Adjust existing unit tests for `format_processing_result` signature and create new `tests/test_audio_transcription_support.py` covering processor behavior | PENDING |
| 38 | Add unit test verifying `BaseMediaProcessor.process_job` handles `asyncio.TimeoutError` with `unprocessable_media=True` | PENDING |
| 39 | Add unit test verifying `_handle_unhandled_exception` sets `unprocessable_media=True` and formats correctly | PENDING |

## Detailed Tasks

1. **Add `audio_transcription` tier to `LLMConfigurations`**
   - Update `config_models.py` to include a new field `audio_transcription: AudioTranscriptionProviderConfig = Field(...)` with defaults matching the `low` tier.
   - Use environment variables `DEFAULT_MODEL_AUDIO_TRANSCRIPTION` and `DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE` with fallback values `"stt-async-v4"` and `0.0`.

2. **Create `AudioTranscriptionProviderSettings`**
   - Inherit from `BaseModelProviderSettings` and add a `temperature: float = 0.0` field.

3. **Modify `AudioTranscriptionProviderConfig`**
   - Extend `BaseModelProviderConfig` and set `provider_config: AudioTranscriptionProviderSettings`.

4. **Update `ConfigTier` enum**
   - Add the literal value `"audio_transcription"`.

5. **Extend `resolve_model_config`**
   - Return `AudioTranscriptionProviderConfig` when `config_tier == "audio_transcription"`.

6. **Update token pricing**
   - Extend `global_configurations.token_menu` with the specified pricing JSON.

7. **Callback Injection**
   - Ensure `create_model_provider` creates a token‑tracking closure and injects it via `set_token_tracker()` on the provider.

8. **`get_configuration_schema` adjustment**
   - Append `"audio_transcription"` to the hard‑coded tier list used for schema generation.

9. **Processor relocation**
   - Move the stub implementation from `media_processors/stub_processors.py` to a new file `media_processors/audio_transcription_processor.py` inheriting `BaseMediaProcessor`.
   - Remove the old stub class.

10. **MIME type routing**
    - Add the extensive list of audio MIME types to `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py`.

11. **Processor implementation**
    - In `AudioTranscriptionProcessor.process_media`, resolve the provider for the bot's `audio_transcription` tier and call `await provider.transcribe_audio(file_path, mime_type)`.
    - Pass `feature_name="audio_transcription"` to `create_model_provider`.

12. **Soniox provider flow**
    - Implement the 4‑step async workflow (upload, create, wait, get transcript) in `SonioxAudioTranscriptionProvider.transcribe_audio`.
    - Estimate token usage and invoke the injected token tracker.
    - Ensure cleanup of both transcription job and uploaded file inside a `try/finally` block using background async tasks (`_background_tasks` set).

13. **Error handling in processor**
    - Wrap the transcription call in `try/except Exception as e` and return `ProcessingResult(content="Unable to transcribe audio content", failed_reason=f"Transcription error: {e}", unprocessable_media=True)`.

14‑18. **Cross‑processor updates**
    - Apply `unprocessable_media=True` to error paths in `ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, and timeout handling in `BaseMediaProcessor`.
    - Adjust token tracking feature names for image processors.
    - Update `_handle_unhandled_exception` to forward `mime_type` and set `unprocessable_media=True`.

19‑20. **Format processing result refactor**
    - Change signature to `format_processing_result(content: str, mime_type: str, display_media_type: str = None, ...)`.
    - Update all callers accordingly, passing `job.mime_type` and any `display_media_type` from `ProcessingResult`.

21. **ProcessingResult dataclass**
    - Add optional `display_media_type: Optional[str] = None` field.

22. **BaseModelProvider initialization**
    - Add a concrete async `initialize(self)` method that does nothing (pass).

23. **Factory enhancements**
    - Import `AudioTranscriptionProvider`.
    - Add an `elif isinstance(provider, AudioTranscriptionProvider):` branch that injects the token tracker and awaits `provider.initialize()` before returning.

24. **Soniox provider implementation**
    - Create `model_providers/sonioxAudioTranscription.py` with the async logic from the spec snippet.

25. **Dependency**
    - Append `soniox==<pinned_version>` to `requirements.txt`.

26. **Migration script**
    - Implement `scripts/audioTranscriptionUpgradeScript.py` to update MongoDB bot configs and token menu as described.

27‑31. **Configuration and deployment**
    - Extend `DefaultConfigurations` with audio transcription defaults.
    - Update bot defaults, required field, import handling, and ensure `SONIOX_API_KEY` is set.

32‑34. **Resolver and router updates**
    - Add the tier to `ConfigTier` literal, update resolver registry, and adjust router fallback lists.

35‑36. **Frontend UI**
    - Add UI schema entry for `audio_transcription` in `EditPage.js` and update validation arrays with comments.

37‑39. **Testing**
    - Adjust existing tests for the new `format_processing_result` signature.
    - Create `tests/test_audio_transcription_support.py` covering the new processor and provider.
    - Add unit tests for timeout handling and unhandled exception behavior.

---

All tasks are listed in logical implementation order, each directly derived from a section of the specification.
